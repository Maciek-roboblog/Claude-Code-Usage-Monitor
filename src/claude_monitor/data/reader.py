"""Simplified data reader for Claude Monitor.

Combines functionality from file_reader, filter, mapper, and processor
into a single cohesive module.
"""

import json
import logging
from datetime import datetime, timedelta
from datetime import timezone as tz
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union

from claude_monitor.core.data_processors import (
    DataConverter,
    TimestampProcessor,
    TokenExtractor,
)
from claude_monitor.core.models import CostMode, UsageEntry, is_anthropic_model
from claude_monitor.core.pricing import PricingCalculator
from claude_monitor.error_handling import report_file_error
from claude_monitor.utils.time_utils import TimezoneHandler

FIELD_COST_USD = "cost_usd"
FIELD_MODEL = "model"
TOKEN_INPUT = "input_tokens"
TOKEN_OUTPUT = "output_tokens"

logger = logging.getLogger(__name__)

DataPathInput = Optional[Union[str, Path, Sequence[Union[str, Path]]]]
SOURCE_KIND_CLAUDE_JSONL = "claude_code_jsonl"


def _normalize_data_paths(data_path: DataPathInput) -> List[Path]:
    if data_path is None:
        return [Path("~/.claude/projects").expanduser()]
    if isinstance(data_path, (str, Path)):
        raw_paths: Sequence[Union[str, Path]] = [data_path]
    else:
        raw_paths = data_path

    paths: List[Path] = []
    seen: Set[Path] = set()
    for raw_path in raw_paths:
        path = Path(raw_path).expanduser()
        key = path.resolve() if path.exists() else path
        if key in seen:
            continue
        seen.add(key)
        paths.append(path)
    return paths


def _source_for_path(path: Path) -> Dict[str, Any]:
    return {"kind": SOURCE_KIND_CLAUDE_JSONL, "account": str(path)}


def load_usage_entries(
    data_path: DataPathInput = None,
    hours_back: Optional[int] = None,
    mode: CostMode = CostMode.AUTO,
    include_raw: bool = False,
    filter_models: str = "all",
) -> Tuple[List[UsageEntry], Optional[List[Dict[str, Any]]]]:
    """Load and convert JSONL files to UsageEntry objects.

    Args:
        data_path: Path or paths to Claude data directories
            (defaults to ~/.claude/projects)
        hours_back: Only include entries from last N hours
        mode: Cost calculation mode
        include_raw: Whether to return raw JSON data alongside entries
        filter_models: ``"anthropic"`` drops entries for non-Anthropic models
            (e.g. routed via Claude Code Router) so they do not count toward the
            Claude limit/cost; ``"all"`` (default) keeps everything. Raw entries
            are never filtered (limit detection is model-agnostic).

    Returns:
        Tuple of (usage_entries, raw_data) where raw_data is None unless include_raw=True
    """
    data_paths = _normalize_data_paths(data_path)
    timezone_handler = TimezoneHandler()
    pricing_calculator = PricingCalculator()

    cutoff_time = None
    if hours_back:
        cutoff_time = datetime.now(tz.utc) - timedelta(hours=hours_back)

    files_by_source: List[Tuple[Path, Dict[str, Any]]] = []
    for path in data_paths:
        files_by_source.extend(
            (file_path, _source_for_path(path)) for file_path in _find_jsonl_files(path)
        )

    jsonl_files = [file_path for file_path, _source in files_by_source]
    if not jsonl_files:
        logger.warning("No JSONL files found in %s", data_paths)
        return [], None

    all_entries: List[UsageEntry] = []
    raw_entries: Optional[List[Dict[str, Any]]] = [] if include_raw else None
    deduped: Dict[str, UsageEntry] = {}

    for file_path, source in files_by_source:
        entries, raw_data = _process_single_file(
            file_path,
            mode,
            cutoff_time,
            deduped,
            include_raw,
            timezone_handler,
            pricing_calculator,
            source,
        )
        all_entries.extend(entries)
        if include_raw and raw_data:
            raw_entries.extend(raw_data)

    all_entries.extend(deduped.values())

    if filter_models == "anthropic":
        before = len(all_entries)
        all_entries = [e for e in all_entries if is_anthropic_model(e.model)]
        dropped = before - len(all_entries)
        if dropped:
            logger.info(f"Filtered out {dropped} non-Anthropic entries")

    all_entries.sort(key=lambda e: e.timestamp)

    logger.info(f"Processed {len(all_entries)} entries from {len(jsonl_files)} files")

    return all_entries, raw_entries


def load_all_raw_entries(data_path: DataPathInput = None) -> List[Dict[str, Any]]:
    """Load all raw JSONL entries without processing.

    Args:
        data_path: Path to Claude data directory

    Returns:
        List of raw JSON dictionaries
    """
    jsonl_files: List[Path] = []
    for path in _normalize_data_paths(data_path):
        jsonl_files.extend(_find_jsonl_files(path))

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
    deduped: Dict[str, UsageEntry],
    include_raw: bool,
    timezone_handler: TimezoneHandler,
    pricing_calculator: PricingCalculator,
    source: Optional[Dict[str, Any]] = None,
) -> Tuple[List[UsageEntry], Optional[List[Dict[str, Any]]]]:
    """Process a single JSONL file.

    ``deduped`` is shared across every file of the scan and holds the winning
    record for each dedup key, so a key restated in a later file is resolved
    against the earlier one instead of being dropped. Records without a key are
    returned directly, since they were never deduplicated.
    """
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

                    if not _should_process_entry(data, cutoff_time, timezone_handler):
                        entries_filtered += 1
                        continue

                    entry = _map_to_usage_entry(
                        data, mode, timezone_handler, pricing_calculator, source
                    )

                    unique_hash = _create_unique_hash(data)
                    first_sighting = unique_hash is None or unique_hash not in deduped

                    if entry:
                        if unique_hash is None:
                            entries_mapped += 1
                            entries.append(entry)
                        elif first_sighting:
                            entries_mapped += 1
                            deduped[unique_hash] = entry
                        else:
                            entries_filtered += 1
                            if _replaces_existing(entry, deduped[unique_hash]):
                                deduped[unique_hash] = entry

                    if include_raw and first_sighting:
                        raw_entry = dict(data)
                        if source is not None:
                            raw_entry["source"] = source
                        raw_data.append(raw_entry)

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
    timezone_handler: TimezoneHandler,
) -> bool:
    """Check whether an entry falls inside the requested time window.

    Records sharing a dedup key are no longer rejected here. A streaming
    message is written as several records under one key and the earlier ones
    carry a partial usage snapshot, so skipping everything after the first
    would keep the partial record. Selection among records that share a key
    happens in :func:`_replaces_existing`, after both have been mapped.
    """
    if cutoff_time:
        timestamp_str = data.get("timestamp")
        if timestamp_str:
            processor = TimestampProcessor(timezone_handler)
            timestamp = processor.parse_timestamp(timestamp_str)
            if timestamp and timestamp < cutoff_time:
                return False

    return True


def _create_unique_hash(data: Dict[str, Any]) -> Optional[str]:
    """Create unique hash for deduplication."""
    message_id = data.get("message_id") or (
        data.get("message", {}).get("id")
        if isinstance(data.get("message"), dict)
        else None
    )
    request_id = data.get("requestId") or data.get("request_id")

    return f"{message_id}:{request_id}" if message_id and request_id else None


def _replaces_existing(candidate: UsageEntry, incumbent: UsageEntry) -> bool:
    """Decide which of two records sharing a dedup key is the complete one.

    Streaming writes several records per message under one key, each carrying
    the usage observed so far, so the counters are monotone within a key and
    the largest record is the finished one. Selecting on the maximum rather
    than on the last record read matters because files are discovered through
    an unordered traversal: a key restated across two files after a session
    resume would otherwise resolve to whichever file the filesystem happened
    to hand over first.

    The winning record is kept whole. Taking a per-field maximum could
    assemble a record that was never written, and ``cost_usd`` is derived from
    those fields, so the resulting cost would correspond to no observation.
    """
    if candidate.output_tokens != incumbent.output_tokens:
        return candidate.output_tokens > incumbent.output_tokens

    def _total(entry: UsageEntry) -> int:
        return (
            entry.input_tokens
            + entry.output_tokens
            + entry.cache_creation_tokens
            + entry.cache_read_tokens
        )

    return _total(candidate) > _total(incumbent)


def _extract_project(data: Dict[str, Any]) -> str:
    """Extract the project/workspace dimension without changing time bucketing."""
    for key in ("cwd", "project", "project_path", "projectPath"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    workspace = data.get("workspace")
    if isinstance(workspace, dict):
        for key in ("cwd", "project", "path"):
            value = workspace.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    return "unknown"


def _map_to_usage_entry(
    data: Dict[str, Any],
    mode: CostMode,
    timezone_handler: TimezoneHandler,
    pricing_calculator: PricingCalculator,
    source: Optional[Dict[str, Any]] = None,
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
            project=_extract_project(data),
            source=source or {"kind": SOURCE_KIND_CLAUDE_JSONL, "account": None},
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
