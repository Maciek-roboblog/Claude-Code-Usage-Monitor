"""OpenCode data reader for Claude Monitor.

Reads usage data from OpenCode's storage format at ~/.local/share/opencode/storage/.
OpenCode stores data in a hierarchical JSON structure:
- sessions/{projectHash}/{sessionID}.json - Session metadata
- message/{sessionID}/{msgID}.json - Individual messages with token data
"""

import json
import logging
from datetime import datetime, timedelta
from datetime import timezone as tz
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from claude_monitor.core.models import CostMode, UsageEntry
from claude_monitor.core.pricing import PricingCalculator

logger = logging.getLogger(__name__)

# Default OpenCode storage path
OPENCODE_STORAGE_PATH = "~/.local/share/opencode/storage"
OPENCODE_MESSAGE_DIR = "message"


def load_opencode_entries(
    data_path: Optional[str] = None,
    hours_back: Optional[int] = None,
    mode: CostMode = CostMode.AUTO,
    include_raw: bool = False,
) -> Tuple[List[UsageEntry], Optional[List[Dict[str, Any]]]]:
    """Load and convert OpenCode message files to UsageEntry objects.

    Args:
        data_path: Path to OpenCode storage directory
                   (defaults to ~/.local/share/opencode/storage)
        hours_back: Only include entries from last N hours
        mode: Cost calculation mode
        include_raw: Whether to return raw JSON data alongside entries

    Returns:
        Tuple of (usage_entries, raw_data) where raw_data is None unless include_raw=True
    """
    storage_path = Path(data_path if data_path else OPENCODE_STORAGE_PATH).expanduser()
    message_path = storage_path / OPENCODE_MESSAGE_DIR

    if not message_path.exists():
        logger.warning("OpenCode message path does not exist: %s", message_path)
        return [], None

    pricing_calculator = PricingCalculator()

    if hours_back:
        cutoff_dt = datetime.now(tz.utc) - timedelta(hours=hours_back)
        cutoff_ms = int(cutoff_dt.timestamp() * 1000)
    else:
        cutoff_ms = None

    # Find all message JSON files
    message_files = _find_message_files(message_path)
    if not message_files:
        logger.warning("No message files found in %s", message_path)
        return [], None

    all_entries: List[UsageEntry] = []
    raw_entries: Optional[List[Dict[str, Any]]] = [] if include_raw else None
    processed_ids: Set[str] = set()

    for file_path in message_files:
        entry, raw_data = _process_message_file(
            file_path,
            mode,
            cutoff_ms,
            processed_ids,
            include_raw,
            pricing_calculator,
        )
        if entry:
            all_entries.append(entry)
        if include_raw and raw_data and raw_entries is not None:
            raw_entries.append(raw_data)

    all_entries.sort(key=lambda e: e.timestamp)

    logger.info(
        f"Processed {len(all_entries)} OpenCode entries from {len(message_files)} files"
    )

    return all_entries, raw_entries


def load_opencode_raw_entries(
    data_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Load all raw OpenCode message entries without processing.

    Args:
        data_path: Path to OpenCode storage directory

    Returns:
        List of raw JSON dictionaries
    """
    storage_path = Path(data_path if data_path else OPENCODE_STORAGE_PATH).expanduser()
    message_path = storage_path / OPENCODE_MESSAGE_DIR

    if not message_path.exists():
        return []

    message_files = _find_message_files(message_path)
    all_raw_entries: List[Dict[str, Any]] = []

    for file_path in message_files:
        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
                # Only include messages with token data (assistant messages)
                if data.get("tokens"):
                    all_raw_entries.append(data)
        except (json.JSONDecodeError, IOError) as e:
            logger.debug(f"Failed to read {file_path}: {e}")
            continue

    return all_raw_entries


def _find_message_files(message_path: Path) -> List[Path]:
    """Find all message JSON files in the message directory.

    OpenCode stores messages in: message/{sessionID}/{msgID}.json
    """
    if not message_path.exists():
        return []

    # Find all .json files in session subdirectories
    return list(message_path.rglob("msg_*.json"))


def _process_message_file(
    file_path: Path,
    mode: CostMode,
    cutoff_ms: Optional[int],
    processed_ids: Set[str],
    include_raw: bool,
    pricing_calculator: PricingCalculator,
) -> Tuple[Optional[UsageEntry], Optional[Dict[str, Any]]]:
    """Process a single OpenCode message JSON file.

    Args:
        file_path: Path to the message JSON file
        mode: Cost calculation mode
        cutoff_ms: Cutoff timestamp in milliseconds (None = no filter)
        processed_ids: Set of already processed message IDs
        include_raw: Whether to include raw data
        pricing_calculator: Pricing calculator instance

    Returns:
        Tuple of (UsageEntry or None, raw_data or None)
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.debug(f"Failed to read message file {file_path}: {e}")
        return None, None

    # Only process assistant messages with token data
    if data.get("role") != "assistant":
        return None, None

    tokens = data.get("tokens")
    if not tokens:
        return None, None

    # Check for duplicate
    msg_id = data.get("id", "")
    if not msg_id:
        # Generate a unique ID from file path if missing
        msg_id = str(file_path)
    if msg_id in processed_ids:
        return None, None

    # Check time filter
    time_data = data.get("time", {})
    created_ms = time_data.get("created")
    if created_ms and cutoff_ms and created_ms < cutoff_ms:
        return None, None

    # Extract token counts
    input_tokens = tokens.get("input", 0)
    output_tokens = tokens.get("output", 0)
    reasoning_tokens = tokens.get("reasoning", 0)
    cache_data = tokens.get("cache", {})
    cache_read_tokens = cache_data.get("read", 0)
    cache_write_tokens = cache_data.get("write", 0)

    # Skip if no meaningful token usage
    total_tokens = (
        input_tokens
        + output_tokens
        + reasoning_tokens
        + cache_read_tokens
        + cache_write_tokens
    )
    if total_tokens == 0:
        return None, None

    # Parse timestamp
    if created_ms:
        timestamp = datetime.fromtimestamp(created_ms / 1000, tz=tz.utc)
    else:
        return None, None

    # Get model info
    model_id = data.get("modelID", "unknown")

    # Calculate cost
    # Note: OpenCode uses "cache.write" which maps to cache_creation_tokens
    # and "cache.read" which maps to cache_read_tokens
    cost_usd = pricing_calculator.calculate_cost(
        model=model_id,
        input_tokens=input_tokens,
        output_tokens=output_tokens + reasoning_tokens,  # Include reasoning in output
        cache_creation_tokens=cache_write_tokens,
        cache_read_tokens=cache_read_tokens,
    )

    # Mark as processed
    processed_ids.add(msg_id)

    entry = UsageEntry(
        timestamp=timestamp,
        input_tokens=input_tokens,
        output_tokens=output_tokens + reasoning_tokens,
        cache_creation_tokens=cache_write_tokens,
        cache_read_tokens=cache_read_tokens,
        cost_usd=cost_usd,
        model=model_id,
        message_id=msg_id,
        request_id=data.get("sessionID", "unknown"),
    )

    raw_data = data if include_raw else None
    return entry, raw_data


def detect_opencode_installation() -> bool:
    """Check if OpenCode data storage exists.

    Returns:
        True if OpenCode storage directory exists
    """
    storage_path = Path(OPENCODE_STORAGE_PATH).expanduser()
    message_path = storage_path / OPENCODE_MESSAGE_DIR
    return message_path.exists()


def get_opencode_storage_path() -> Path:
    """Get the OpenCode storage path.

    Returns:
        Path to OpenCode storage directory
    """
    return Path(OPENCODE_STORAGE_PATH).expanduser()
