"""Simplified data reader for Claude Monitor.

Combines functionality from file_reader, filter, mapper, and processor
into a single cohesive module.
"""

import json
import logging
from datetime import datetime, timedelta
from datetime import timezone as tz
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from claude_monitor.core.data_processors import (
    DataConverter,
    TimestampProcessor,
    TokenExtractor,
)
from claude_monitor.core.models import CostMode, UsageEntry
from claude_monitor.core.pricing import PricingCalculator
from claude_monitor.error_handling import report_file_error
from claude_monitor.utils.time_utils import TimezoneHandler

FIELD_COST_USD = "cost_usd"
FIELD_MODEL = "model"
TOKEN_INPUT = "input_tokens"
TOKEN_OUTPUT = "output_tokens"

logger = logging.getLogger(__name__)


def load_usage_entries(
    data_path: Optional[str] = None,
    hours_back: Optional[int] = None,
    mode: CostMode = CostMode.AUTO,
    include_raw: bool = False,
) -> Tuple[List[UsageEntry], Optional[List[Dict[str, Any]]]]:
    """
    Loads and processes Claude Monitor JSONL usage files, returning structured usage entries and optionally raw JSON data.
    
    Scans the specified data directory for JSONL files, filters entries by recency if `hours_back` is set, deduplicates entries, maps them to `UsageEntry` objects with cost calculation according to the specified mode, and sorts them by timestamp. If `include_raw` is True, also returns the corresponding raw JSON entries.
    
    Parameters:
        data_path (str, optional): Path to the directory containing Claude usage data. Defaults to `~/.claude/projects` if not specified.
        hours_back (int, optional): If provided, only includes entries from the last N hours.
        mode (CostMode): Determines how costs are calculated for each entry.
        include_raw (bool): If True, returns the raw JSON data alongside processed entries.
    
    Returns:
        Tuple[List[UsageEntry], Optional[List[Dict[str, Any]]]]: A tuple containing the list of processed usage entries and, if requested, the list of raw JSON entries.
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

    all_entries = []
    raw_entries = [] if include_raw else None
    processed_hashes = set()

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
    """
    Load all raw JSON entries from JSONL files in the specified directory.
    
    Reads every line from all `.jsonl` files found under the given directory (defaulting to `~/.claude/projects`), parses each line as JSON, and returns a list of raw dictionaries. Malformed lines and file read errors are skipped.
     
    Returns:
        List[Dict[str, Any]]: A list of raw JSON objects from all discovered JSONL files.
    """
    data_path = Path(data_path if data_path else "~/.claude/projects").expanduser()
    jsonl_files = _find_jsonl_files(data_path)

    all_raw_entries = []
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
            logger.error(f"Error loading raw entries from {file_path}: {e}")

    return all_raw_entries


def _find_jsonl_files(data_path: Path) -> List[Path]:
    """
    Recursively finds all `.jsonl` files under the specified data directory.
    
    Returns:
        List of paths to `.jsonl` files found. Returns an empty list if the directory does not exist.
    """
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
    """
    Processes a single JSONL file, filtering and deduplicating entries, mapping valid entries to `UsageEntry` objects, and optionally collecting raw data.
    
    Parameters:
        file_path (Path): Path to the JSONL file to process.
        mode (CostMode): Cost calculation mode for usage entries.
        cutoff_time (Optional[datetime]): Only entries after this timestamp are processed; if None, all entries are considered.
        processed_hashes (Set[str]): Set of unique hashes for deduplication across files.
        include_raw (bool): If True, collects and returns raw JSON data for each processed entry.
        timezone_handler (TimezoneHandler): Handles timezone conversion for timestamps.
        pricing_calculator (PricingCalculator): Calculates cost for each usage entry.
    
    Returns:
        Tuple[List[UsageEntry], Optional[List[Dict[str, Any]]]]: A tuple containing the list of processed `UsageEntry` objects and, if requested, the corresponding raw JSON data.
    """
    entries = []
    raw_data = [] if include_raw else None

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
    """
    Determine whether a data entry should be processed based on its timestamp and uniqueness.
    
    Returns:
        bool: True if the entry's timestamp is after the cutoff time (if specified) and its unique hash has not been processed; otherwise, False.
    """
    if cutoff_time:
        timestamp_str = data.get("timestamp")
        if timestamp_str:
            processor = TimestampProcessor(timezone_handler)
            timestamp = processor.parse_timestamp(timestamp_str)
            if timestamp and timestamp < cutoff_time:
                return False

    unique_hash = _create_unique_hash(data)
    if unique_hash and unique_hash in processed_hashes:
        return False

    return True


def _create_unique_hash(data: dict) -> Optional[str]:
    """
    Generate a unique hash string for an entry by combining its message ID and request ID.
    
    Returns:
        A string in the format "message_id:request_id" if both identifiers are present; otherwise, None.
    """
    message_id = data.get("message_id") or (
        data.get("message", {}).get("id")
        if isinstance(data.get("message"), dict)
        else None
    )
    request_id = data.get("requestId") or data.get("request_id")

    return f"{message_id}:{request_id}" if message_id and request_id else None


def _update_processed_hashes(data: Dict[str, Any], processed_hashes: Set[str]) -> None:
    """
    Adds the unique hash of the given entry to the set of processed hashes for deduplication.
    
    If the entry's unique hash can be generated, it is added to the provided set to track processed entries and prevent duplicates.
    """
    unique_hash = _create_unique_hash(data)
    if unique_hash:
        processed_hashes.add(unique_hash)


def _map_to_usage_entry(
    data: dict,
    mode: CostMode,
    timezone_handler: TimezoneHandler,
    pricing_calculator: PricingCalculator,
) -> Optional[UsageEntry]:
    """
    Converts a raw data dictionary into a UsageEntry object with calculated cost.
    
    Attempts to extract timestamp, token counts, model name, and identifiers from the input data. Calculates the usage cost using the provided pricing calculator and mode. Returns None if required fields are missing or invalid.
     
    Returns:
        UsageEntry if mapping and cost calculation succeed; otherwise, None.
    """
    try:
        timestamp_processor = TimestampProcessor(timezone_handler)
        timestamp = timestamp_processor.parse_timestamp(data.get("timestamp", ""))
        if not timestamp:
            return None

        token_data = TokenExtractor.extract_tokens(data)
        if not any(v for k, v in token_data.items() if k != "total_tokens"):
            return None

        model = DataConverter.extract_model_name(data, default="unknown")

        entry_data = {
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
        """
        Initialize a UsageEntryMapper with a pricing calculator and timezone handler.
        
        The provided components are used for cost calculation and timestamp processing when mapping raw data to UsageEntry objects.
        """
        self.pricing_calculator = pricing_calculator
        self.timezone_handler = timezone_handler

    def map(self, data: dict, mode: CostMode) -> Optional[UsageEntry]:
        """
        Converts a raw data dictionary into a UsageEntry object using the specified cost calculation mode.
        
        Parameters:
            data (dict): The raw usage entry data to be mapped.
            mode (CostMode): The cost calculation mode to use.
        
        Returns:
            UsageEntry or None: The mapped UsageEntry object, or None if the data is invalid or incomplete.
        """
        return _map_to_usage_entry(
            data, mode, self.timezone_handler, self.pricing_calculator
        )

    def _has_valid_tokens(self, tokens: Dict[str, int]) -> bool:
        """
        Determine whether the provided token counts contain any positive values.
        
        Returns:
            bool: True if at least one token count is greater than zero; otherwise, False.
        """
        return any(v > 0 for v in tokens.values())

    def _extract_timestamp(self, data: dict) -> Optional[datetime]:
        """
        Extracts the timestamp from the given data dictionary using the configured timezone handler.
        
        Returns:
            The parsed datetime object if the "timestamp" field exists and is valid; otherwise, None.
        """
        if "timestamp" not in data:
            return None
        processor = TimestampProcessor(self.timezone_handler)
        return processor.parse_timestamp(data["timestamp"])

    def _extract_model(self, data: dict) -> str:
        """
        Extracts the model name from the provided data dictionary, returning "unknown" if not found.
        """
        return DataConverter.extract_model_name(data, default="unknown")

    def _extract_metadata(self, data: dict) -> Dict[str, str]:
        """
        Extracts the message and request identifiers from the entry data for compatibility with legacy tests.
        
        Returns:
            A dictionary containing 'message_id' and 'request_id' extracted from the input data.
        """
        message = data.get("message", {})
        return {
            "message_id": data.get("message_id") or message.get("id", ""),
            "request_id": data.get("request_id") or data.get("requestId", "unknown"),
        }
