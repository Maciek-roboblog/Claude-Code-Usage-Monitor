"""Simplified data reader for Claude Monitor.

Combines functionality from file_reader, filter, mapper, and processor
into a single cohesive module. Supports both Claude Code and OpenCode data sources.
"""

import json
import logging
from datetime import datetime, timedelta
from datetime import timezone as tz
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from claude_monitor.core.data_processors import (
    DataConverter,
    TimestampProcessor,
    TokenExtractor,
)
from claude_monitor.core.models import CostMode, UsageEntry
from claude_monitor.core.pricing import PricingCalculator
from claude_monitor.data.opencode_reader import OPENCODE_STORAGE_PATH
from claude_monitor.error_handling import report_file_error
from claude_monitor.utils.time_utils import TimezoneHandler

FIELD_COST_USD = "cost_usd"
FIELD_MODEL = "model"
TOKEN_INPUT = "input_tokens"
TOKEN_OUTPUT = "output_tokens"

# Default data path for Claude Code
CLAUDE_CODE_PATH = "~/.claude/projects"

logger = logging.getLogger(__name__)


class DataSource(Enum):
    """Data source types for usage data."""

    AUTO = "auto"  # Auto-detect and combine all available sources
    ALL = "all"  # Explicitly use all available sources (same as AUTO)
    CLAUDE = "claude"  # Claude Code only (~/.claude/projects)
    OPENCODE = "opencode"  # OpenCode only (~/.local/share/opencode/storage)


def load_usage_entries(
    data_path: Optional[str] = None,
    hours_back: Optional[int] = None,
    mode: CostMode = CostMode.AUTO,
    include_raw: bool = False,
) -> Tuple[List[UsageEntry], Optional[List[Dict[str, Any]]]]:
    """Load and convert JSONL files to UsageEntry objects.

    Args:
        data_path: Path to Claude data directory (defaults to ~/.claude/projects)
        hours_back: Only include entries from last N hours
        mode: Cost calculation mode
        include_raw: Whether to return raw JSON data alongside entries

    Returns:
        Tuple of (usage_entries, raw_data) where raw_data is None unless include_raw=True
    """
    data_path = Path(data_path if data_path else "~/.claude/projects").expanduser()
    timezone_handler = TimezoneHandler()
    pricing_calculator = PricingCalculator()

    cutoff_time = None
    if hours_back:
        cutoff_time = datetime.now(tz.utc) - timedelta(hours=hours_back)

    jsonl_files = _find_jsonl_files(data_path)
    if not jsonl_files:
        logger.warning("No JSONL files found in %s", data_path)
        return [], None

    all_entries: List[UsageEntry] = []
    raw_entries: Optional[List[Dict[str, Any]]] = [] if include_raw else None
    processed_hashes: Set[str] = set()

    for file_path in jsonl_files:
        entries, raw_data = _process_single_file(
            file_path,
            mode,
            cutoff_time,
            processed_hashes,
            include_raw,
            timezone_handler,
            pricing_calculator,
        )
        all_entries.extend(entries)
        if include_raw and raw_data:
            raw_entries.extend(raw_data)

    all_entries.sort(key=lambda e: e.timestamp)

    logger.info(f"Processed {len(all_entries)} entries from {len(jsonl_files)} files")

    return all_entries, raw_entries


def load_all_raw_entries(data_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Load all raw JSONL entries without processing.

    Args:
        data_path: Path to Claude data directory

    Returns:
        List of raw JSON dictionaries
    """
    data_path = Path(data_path if data_path else "~/.claude/projects").expanduser()
    jsonl_files = _find_jsonl_files(data_path)

    all_raw_entries: List[Dict[str, Any]] = []
    for file_path in jsonl_files:
        try:
            with open(file_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        all_raw_entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.exception(f"Error loading raw entries from {file_path}: {e}")

    return all_raw_entries


def _find_jsonl_files(data_path: Path) -> List[Path]:
    """Find all .jsonl files in the data directory."""
    if not data_path.exists():
        logger.warning("Data path does not exist: %s", data_path)
        return []
    return list(data_path.rglob("*.jsonl"))


def _process_single_file(
    file_path: Path,
    mode: CostMode,
    cutoff_time: Optional[datetime],
    processed_hashes: Set[str],
    include_raw: bool,
    timezone_handler: TimezoneHandler,
    pricing_calculator: PricingCalculator,
) -> Tuple[List[UsageEntry], Optional[List[Dict[str, Any]]]]:
    """Process a single JSONL file."""
    entries: List[UsageEntry] = []
    raw_data: Optional[List[Dict[str, Any]]] = [] if include_raw else None

    try:
        entries_read = 0
        entries_filtered = 0
        entries_mapped = 0

        with open(file_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)
                    entries_read += 1

                    if not _should_process_entry(
                        data, cutoff_time, processed_hashes, timezone_handler
                    ):
                        entries_filtered += 1
                        continue

                    entry = _map_to_usage_entry(
                        data, mode, timezone_handler, pricing_calculator
                    )
                    if entry:
                        entries_mapped += 1
                        entries.append(entry)
                        _update_processed_hashes(data, processed_hashes)

                    if include_raw:
                        raw_data.append(data)

                except json.JSONDecodeError as e:
                    logger.debug(f"Failed to parse JSON line in {file_path}: {e}")
                    continue

        logger.debug(
            f"File {file_path.name}: {entries_read} read, "
            f"{entries_filtered} filtered out, {entries_mapped} successfully mapped"
        )

    except Exception as e:
        logger.warning("Failed to read file %s: %s", file_path, e)
        report_file_error(
            exception=e,
            file_path=str(file_path),
            operation="read",
            additional_context={"file_exists": file_path.exists()},
        )
        return [], None

    return entries, raw_data


def _should_process_entry(
    data: Dict[str, Any],
    cutoff_time: Optional[datetime],
    processed_hashes: Set[str],
    timezone_handler: TimezoneHandler,
) -> bool:
    """Check if entry should be processed based on time and uniqueness."""
    if cutoff_time:
        timestamp_str = data.get("timestamp")
        if timestamp_str:
            processor = TimestampProcessor(timezone_handler)
            timestamp = processor.parse_timestamp(timestamp_str)
            if timestamp and timestamp < cutoff_time:
                return False

    unique_hash = _create_unique_hash(data)
    return not (unique_hash and unique_hash in processed_hashes)


def _create_unique_hash(data: Dict[str, Any]) -> Optional[str]:
    """Create unique hash for deduplication."""
    message_id = data.get("message_id") or (
        data.get("message", {}).get("id")
        if isinstance(data.get("message"), dict)
        else None
    )
    request_id = data.get("requestId") or data.get("request_id")

    return f"{message_id}:{request_id}" if message_id and request_id else None


def _update_processed_hashes(data: Dict[str, Any], processed_hashes: Set[str]) -> None:
    """Update the processed hashes set with current entry's hash."""
    unique_hash = _create_unique_hash(data)
    if unique_hash:
        processed_hashes.add(unique_hash)


def _map_to_usage_entry(
    data: Dict[str, Any],
    mode: CostMode,
    timezone_handler: TimezoneHandler,
    pricing_calculator: PricingCalculator,
) -> Optional[UsageEntry]:
    """Map raw data to UsageEntry with proper cost calculation."""
    try:
        timestamp_processor = TimestampProcessor(timezone_handler)
        timestamp = timestamp_processor.parse_timestamp(data.get("timestamp", ""))
        if not timestamp:
            return None

        token_data = TokenExtractor.extract_tokens(data)
        if not any(v for k, v in token_data.items() if k != "total_tokens"):
            return None

        model = DataConverter.extract_model_name(data, default="unknown")

        entry_data: Dict[str, Any] = {
            FIELD_MODEL: model,
            TOKEN_INPUT: token_data["input_tokens"],
            TOKEN_OUTPUT: token_data["output_tokens"],
            "cache_creation_tokens": token_data.get("cache_creation_tokens", 0),
            "cache_read_tokens": token_data.get("cache_read_tokens", 0),
            FIELD_COST_USD: data.get("cost") or data.get(FIELD_COST_USD),
        }
        cost_usd = pricing_calculator.calculate_cost_for_entry(entry_data, mode)

        message = data.get("message", {})
        message_id = data.get("message_id") or message.get("id") or ""
        request_id = data.get("request_id") or data.get("requestId") or "unknown"

        return UsageEntry(
            timestamp=timestamp,
            input_tokens=token_data["input_tokens"],
            output_tokens=token_data["output_tokens"],
            cache_creation_tokens=token_data.get("cache_creation_tokens", 0),
            cache_read_tokens=token_data.get("cache_read_tokens", 0),
            cost_usd=cost_usd,
            model=model,
            message_id=message_id,
            request_id=request_id,
        )

    except (KeyError, ValueError, TypeError, AttributeError) as e:
        logger.debug(f"Failed to map entry: {type(e).__name__}: {e}")
        return None


class UsageEntryMapper:
    """Compatibility wrapper for legacy UsageEntryMapper interface.

    This class provides backward compatibility for tests that expect
    the old UsageEntryMapper interface, wrapping the new functional
    approach in _map_to_usage_entry.
    """

    def __init__(
        self, pricing_calculator: PricingCalculator, timezone_handler: TimezoneHandler
    ):
        """Initialize with required components."""
        self.pricing_calculator = pricing_calculator
        self.timezone_handler = timezone_handler

    def map(self, data: Dict[str, Any], mode: CostMode) -> Optional[UsageEntry]:
        """Map raw data to UsageEntry - compatibility interface."""
        return _map_to_usage_entry(
            data, mode, self.timezone_handler, self.pricing_calculator
        )

    def _has_valid_tokens(self, tokens: Dict[str, int]) -> bool:
        """Check if tokens are valid (for test compatibility)."""
        return any(v > 0 for v in tokens.values())

    def _extract_timestamp(self, data: Dict[str, Any]) -> Optional[datetime]:
        """Extract timestamp (for test compatibility)."""
        if "timestamp" not in data:
            return None
        processor = TimestampProcessor(self.timezone_handler)
        return processor.parse_timestamp(data["timestamp"])

    def _extract_model(self, data: Dict[str, Any]) -> str:
        """Extract model name (for test compatibility)."""
        return DataConverter.extract_model_name(data, default="unknown")

    def _extract_metadata(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Extract metadata (for test compatibility)."""
        message = data.get("message", {})
        return {
            "message_id": data.get("message_id") or message.get("id", ""),
            "request_id": data.get("request_id") or data.get("requestId", "unknown"),
        }


# =============================================================================
# Unified Data Loading with Multi-Source Support
# =============================================================================


def detect_available_sources() -> List[DataSource]:
    """Detect which data sources are available.

    Returns:
        List of available DataSource enums
    """
    available: List[DataSource] = []

    # Check for Claude Code installation
    claude_path = Path(CLAUDE_CODE_PATH).expanduser()
    if claude_path.exists() and any(claude_path.rglob("*.jsonl")):
        logger.info("Detected Claude Code data source")
        available.append(DataSource.CLAUDE)

    # Check for OpenCode installation
    opencode_path = Path(OPENCODE_STORAGE_PATH).expanduser() / "message"
    if opencode_path.exists():
        try:
            if any(opencode_path.iterdir()):
                logger.info("Detected OpenCode data source")
                available.append(DataSource.OPENCODE)
        except (PermissionError, OSError):
            pass

    return available


def detect_data_source() -> DataSource:
    """Detect which data source is available (legacy compatibility).

    For backward compatibility, returns a single source.
    Prefers OpenCode if available, otherwise Claude Code.

    Returns:
        DataSource enum indicating the detected source
    """
    available = detect_available_sources()

    if DataSource.OPENCODE in available:
        return DataSource.OPENCODE
    if DataSource.CLAUDE in available:
        return DataSource.CLAUDE

    # Default to Claude Code path (legacy behavior)
    logger.warning("No data source detected, defaulting to Claude Code")
    return DataSource.CLAUDE


def load_usage_entries_unified(
    data_path: Optional[str] = None,
    hours_back: Optional[int] = None,
    mode: CostMode = CostMode.AUTO,
    include_raw: bool = False,
    source: DataSource = DataSource.AUTO,
) -> Tuple[List[UsageEntry], Optional[List[Dict[str, Any]]], DataSource]:
    """Load usage entries from Claude Code, OpenCode, or both.

    This is the unified entry point that supports multiple data sources
    with automatic detection and merging.

    Args:
        data_path: Optional custom data path (overrides auto-detection)
        hours_back: Only include entries from last N hours
        mode: Cost calculation mode
        include_raw: Whether to return raw JSON data alongside entries
        source: Data source to use (AUTO/ALL combines all available sources)

    Returns:
        Tuple of (usage_entries, raw_data, primary_source)
        When multiple sources are combined, primary_source indicates the first source used.
    """
    from claude_monitor.data.opencode_reader import load_opencode_entries

    all_entries: List[UsageEntry] = []
    all_raw: Optional[List[Dict[str, Any]]] = [] if include_raw else None
    primary_source: DataSource = DataSource.CLAUDE

    # Handle AUTO/ALL - combine all available sources
    if source in (DataSource.AUTO, DataSource.ALL):
        available = detect_available_sources()

        if not available:
            logger.warning("No data sources available")
            return [], None, DataSource.CLAUDE

        # Set primary source (first available)
        primary_source = available[0]

        # Load from Claude Code if available
        if DataSource.CLAUDE in available:
            entries, raw_data = load_usage_entries(
                data_path=data_path,
                hours_back=hours_back,
                mode=mode,
                include_raw=include_raw,
            )
            all_entries.extend(entries)
            if include_raw and raw_data and all_raw is not None:
                all_raw.extend(raw_data)
            logger.info(f"Loaded {len(entries)} entries from Claude Code")

        # Load from OpenCode if available
        # Note: OpenCode always uses its own default path (~/.local/share/opencode/storage)
        # in AUTO mode. The data_path parameter only applies to Claude Code.
        if DataSource.OPENCODE in available:
            entries, raw_data = load_opencode_entries(
                data_path=None,  # OpenCode uses its own default path in AUTO mode
                hours_back=hours_back,
                mode=mode,
                include_raw=include_raw,
            )
            all_entries.extend(entries)
            if include_raw and raw_data and all_raw is not None:
                all_raw.extend(raw_data)
            logger.info(f"Loaded {len(entries)} entries from OpenCode")

    # Handle single source selection
    elif source == DataSource.OPENCODE:
        entries, raw_data = load_opencode_entries(
            data_path=data_path,
            hours_back=hours_back,
            mode=mode,
            include_raw=include_raw,
        )
        all_entries.extend(entries)
        if include_raw and raw_data and all_raw is not None:
            all_raw.extend(raw_data)
        primary_source = DataSource.OPENCODE

    else:  # DataSource.CLAUDE
        entries, raw_data = load_usage_entries(
            data_path=data_path,
            hours_back=hours_back,
            mode=mode,
            include_raw=include_raw,
        )
        all_entries.extend(entries)
        if include_raw and raw_data and all_raw is not None:
            all_raw.extend(raw_data)
        primary_source = DataSource.CLAUDE

    # Sort combined entries by timestamp
    all_entries.sort(key=lambda e: e.timestamp)

    logger.info(f"Total entries loaded: {len(all_entries)}")
    return all_entries, all_raw, primary_source


def get_data_source_info(source: DataSource) -> Dict[str, Any]:
    """Get information about a data source.

    Args:
        source: The data source to get info for

    Returns:
        Dictionary with path, exists, and description
    """
    if source in (DataSource.AUTO, DataSource.ALL):
        available = detect_available_sources()
        return {
            "path": "multiple",
            "exists": len(available) > 0,
            "description": f"Auto-detected sources: {[s.value for s in available]}",
            "source": "auto",
        }
    if source == DataSource.OPENCODE:
        path = Path(OPENCODE_STORAGE_PATH).expanduser()
        return {
            "path": str(path),
            "exists": (path / "message").exists(),
            "description": "OpenCode (~/.local/share/opencode/storage)",
            "source": "opencode",
        }
    else:
        path = Path(CLAUDE_CODE_PATH).expanduser()
        return {
            "path": str(path),
            "exists": path.exists(),
            "description": "Claude Code (~/.claude/projects)",
            "source": "claude",
        }
