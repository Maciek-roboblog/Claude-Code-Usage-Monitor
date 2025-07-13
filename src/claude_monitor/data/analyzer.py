"""Session analyzer for Claude Monitor.

Combines session block creation and limit detection functionality.
"""

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from claude_monitor.core.models import (
    SessionBlock,
    TokenCounts,
    UsageEntry,
    normalize_model_name,
)
from claude_monitor.utils.time_utils import TimezoneHandler

logger = logging.getLogger(__name__)


class SessionAnalyzer:
    """Creates session blocks and detects limits."""

    def __init__(self, session_duration_hours: int = 5):
        """
        Initialize the SessionAnalyzer with a specified session duration in hours.
        
        The session duration determines the length of each session block when processing usage entries.
        """
        self.session_duration_hours = session_duration_hours
        self.session_duration = timedelta(hours=session_duration_hours)
        self.timezone_handler = TimezoneHandler()

    def transform_to_blocks(self, entries: List[UsageEntry]) -> List[SessionBlock]:
        """
        Groups usage entries into session blocks based on session duration and inactivity gaps.
        
        Entries are assigned to blocks such that each block covers a contiguous period up to the configured session duration. If a gap between entries exceeds the session duration, a special gap block is inserted. Each block aggregates token and cost statistics, and blocks with end times in the future are marked as active.
        
        Parameters:
            entries (List[UsageEntry]): Usage entries to be grouped into session blocks.
        
        Returns:
            List[SessionBlock]: List of session and gap blocks representing contiguous usage periods.
        """
        if not entries:
            return []

        blocks = []
        current_block = None

        for entry in entries:
            # Check if we need a new block
            if current_block is None or self._should_create_new_block(
                current_block, entry
            ):
                # Close current block
                if current_block:
                    self._finalize_block(current_block)
                    blocks.append(current_block)

                    # Check for gap
                    gap = self._check_for_gap(current_block, entry)
                    if gap:
                        blocks.append(gap)

                # Create new block
                current_block = self._create_new_block(entry)

            # Add entry to current block
            self._add_entry_to_block(current_block, entry)

        # Finalize last block
        if current_block:
            self._finalize_block(current_block)
            blocks.append(current_block)

        # Mark active blocks
        self._mark_active_blocks(blocks)

        return blocks

    def detect_limits(self, raw_entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Detects and extracts token limit messages from a list of raw JSONL entries.
        
        Each entry is analyzed for system or user messages indicating token or rate limits. Returns a list of dictionaries containing detected limit information, including relevant metadata and timing details.
         
        Returns:
            List[Dict[str, Any]]: A list of detected limit information dictionaries, one for each identified limit message.
        """
        limits = []

        for raw_data in raw_entries:
            limit_info = self._detect_single_limit(raw_data)
            if limit_info:
                limits.append(limit_info)

        return limits

    def _should_create_new_block(self, block: SessionBlock, entry: UsageEntry) -> bool:
        """
        Determine whether a new session block should be created based on the entry's timestamp.
        
        Returns:
            bool: True if the entry falls outside the current block's end time or if the gap since the last entry exceeds the session duration; otherwise, False.
        """
        if entry.timestamp >= block.end_time:
            return True

        return (
            block.entries
            and (entry.timestamp - block.entries[-1].timestamp) >= self.session_duration
        )

    def _round_to_hour(self, timestamp: datetime) -> datetime:
        """
        Rounds a timestamp to the nearest full hour in UTC.
        
        If the input timestamp is naive, it is assumed to be in UTC.
        Returns a new datetime object with minutes, seconds, and microseconds set to zero.
        """
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        elif timestamp.tzinfo != timezone.utc:
            timestamp = timestamp.astimezone(timezone.utc)

        return timestamp.replace(minute=0, second=0, microsecond=0)

    def _create_new_block(self, entry: UsageEntry) -> SessionBlock:
        """
        Create a new session block starting at the rounded hour of the given entry's timestamp.
        
        Returns:
            SessionBlock: A new session block with initialized fields and a duration equal to the configured session duration.
        """
        start_time = self._round_to_hour(entry.timestamp)
        end_time = start_time + self.session_duration
        block_id = start_time.isoformat()

        return SessionBlock(
            id=block_id,
            start_time=start_time,
            end_time=end_time,
            entries=[],
            token_counts=TokenCounts(),
            cost_usd=0.0,
        )

    def _add_entry_to_block(self, block: SessionBlock, entry: UsageEntry) -> None:
        """
        Adds a usage entry to a session block, updating per-model statistics, total token counts, cost, and message count.
        """
        block.entries.append(entry)

        raw_model = entry.model or "unknown"
        model = normalize_model_name(raw_model) if raw_model != "unknown" else "unknown"

        if model not in block.per_model_stats:
            block.per_model_stats[model] = {
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_creation_tokens": 0,
                "cache_read_tokens": 0,
                "cost_usd": 0.0,
                "entries_count": 0,
            }

        model_stats = block.per_model_stats[model]
        model_stats["input_tokens"] += entry.input_tokens
        model_stats["output_tokens"] += entry.output_tokens
        model_stats["cache_creation_tokens"] += entry.cache_creation_tokens
        model_stats["cache_read_tokens"] += entry.cache_read_tokens
        model_stats["cost_usd"] += entry.cost_usd or 0.0
        model_stats["entries_count"] += 1

        block.token_counts.input_tokens += entry.input_tokens
        block.token_counts.output_tokens += entry.output_tokens
        block.token_counts.cache_creation_tokens += entry.cache_creation_tokens
        block.token_counts.cache_read_tokens += entry.cache_read_tokens

        # Update aggregated cost (sum across all models)
        if entry.cost_usd:
            block.cost_usd += entry.cost_usd

        # Model tracking (prevent duplicates)
        if model and model not in block.models:
            block.models.append(model)

        # Increment sent messages count
        block.sent_messages_count += 1

    def _finalize_block(self, block: SessionBlock) -> None:
        """
        Finalize a session block by setting its actual end time and updating the sent messages count.
        
        The block's actual end time is set to the timestamp of its last entry, and the sent messages count is updated to reflect the total number of entries in the block.
        """
        if block.entries:
            block.actual_end_time = block.entries[-1].timestamp

        # Update sent_messages_count
        block.sent_messages_count = len(block.entries)

    def _check_for_gap(
        self, last_block: SessionBlock, next_entry: UsageEntry
    ) -> Optional[SessionBlock]:
        """
        Detects and creates a gap session block if the time between the last block's end and the next entry exceeds the session duration.
        
        Returns:
            SessionBlock or None: A gap block representing the inactivity period, or None if no gap is detected.
        """
        if not last_block.actual_end_time:
            return None

        gap_duration = next_entry.timestamp - last_block.actual_end_time

        if gap_duration >= self.session_duration:
            gap_time_str = last_block.actual_end_time.isoformat()
            gap_id = f"gap-{gap_time_str}"

            return SessionBlock(
                id=gap_id,
                start_time=last_block.actual_end_time,
                end_time=next_entry.timestamp,
                actual_end_time=None,
                is_gap=True,
                entries=[],
                token_counts=TokenCounts(),
                cost_usd=0.0,
                models=[],
            )

        return None

    def _mark_active_blocks(self, blocks: List[SessionBlock]) -> None:
        """
        Mark session blocks as active if their end time is in the future and they are not gap blocks.
        """
        current_time = datetime.now(timezone.utc)

        for block in blocks:
            if not block.is_gap and block.end_time > current_time:
                block.is_active = True

    # Limit detection methods

    def _detect_single_limit(
        self, raw_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Detects token limit information from a single raw JSONL entry.
        
        Dispatches processing based on the entry type, handling system and user messages to identify limit-related content. Returns a dictionary with detected limit details if found, or None otherwise.
        """
        entry_type = raw_data.get("type")

        if entry_type == "system":
            return self._process_system_message(raw_data)
        if entry_type == "user":
            return self._process_user_message(raw_data)

        return None

    def _process_system_message(
        self, raw_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Analyzes a system message to detect and extract token or rate limit information.
        
        If the message content indicates a limit or rate restriction, returns a dictionary with details such as type, timestamp, content, reset time (if applicable), and contextual metadata. Distinguishes between general system limits and Opus-specific limits, extracting wait time and reset time for the latter. Returns `None` if no relevant limit information is found.
        """
        content = raw_data.get("content", "")
        if not isinstance(content, str):
            return None

        content_lower = content.lower()
        if "limit" not in content_lower and "rate" not in content_lower:
            return None

        timestamp_str = raw_data.get("timestamp")
        if not timestamp_str:
            return None

        try:
            timestamp = self.timezone_handler.parse_timestamp(timestamp_str)
            block_context = self._extract_block_context(raw_data)

            # Check for Opus-specific limit
            if self._is_opus_limit(content_lower):
                reset_time, wait_minutes = self._extract_wait_time(content, timestamp)
                return {
                    "type": "opus_limit",
                    "timestamp": timestamp,
                    "content": content,
                    "reset_time": reset_time,
                    "wait_minutes": wait_minutes,
                    "raw_data": raw_data,
                    "block_context": block_context,
                }

            # General system limit
            return {
                "type": "system_limit",
                "timestamp": timestamp,
                "content": content,
                "reset_time": None,
                "raw_data": raw_data,
                "block_context": block_context,
            }

        except (ValueError, TypeError):
            return None

    def _process_user_message(
        self, raw_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Detects token limit messages within user messages by scanning for tool result items indicating a limit has been reached.
        
        Parameters:
            raw_data (Dict[str, Any]): The raw JSONL entry representing a user message.
        
        Returns:
            Optional[Dict[str, Any]]: A dictionary with detected limit information if a limit is found, otherwise None.
        """
        message = raw_data.get("message", {})
        content_list = message.get("content", [])

        if not isinstance(content_list, list):
            return None

        for item in content_list:
            if isinstance(item, dict) and item.get("type") == "tool_result":
                limit_info = self._process_tool_result(item, raw_data, message)
                if limit_info:
                    return limit_info

        return None

    def _process_tool_result(
        self, item: Dict[str, Any], raw_data: Dict[str, Any], message: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Detects and extracts limit information from a single tool result item within a user message.
        
        Scans the tool result content for messages indicating a limit has been reached. If found, parses the timestamp, attempts to extract a reset time from the message text, and gathers contextual metadata.
        
        Returns:
            A dictionary containing limit details if a limit is detected, or None otherwise.
        """
        tool_content = item.get("content", [])
        if not isinstance(tool_content, list):
            return None

        for tool_item in tool_content:
            if not isinstance(tool_item, dict):
                continue

            text = tool_item.get("text", "")
            if not isinstance(text, str) or "limit reached" not in text.lower():
                continue

            timestamp_str = raw_data.get("timestamp")
            if not timestamp_str:
                continue

            try:
                timestamp = self.timezone_handler.parse_timestamp(timestamp_str)
                return {
                    "type": "general_limit",
                    "timestamp": timestamp,
                    "content": text,
                    "reset_time": self._parse_reset_timestamp(text),
                    "raw_data": raw_data,
                    "block_context": self._extract_block_context(raw_data, message),
                }
            except (ValueError, TypeError):
                continue

        return None

    def _extract_block_context(
        self, raw_data: Dict[str, Any], message: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Extracts contextual identifiers and metadata from raw data and an optional message dictionary.
        
        Returns a dictionary containing message ID, request ID, session ID, version, model, and, if provided, usage and stop reason from the message.
        """
        context = {
            "message_id": raw_data.get("messageId") or raw_data.get("message_id"),
            "request_id": raw_data.get("requestId") or raw_data.get("request_id"),
            "session_id": raw_data.get("sessionId") or raw_data.get("session_id"),
            "version": raw_data.get("version"),
            "model": raw_data.get("model"),
        }

        if message:
            context["message_id"] = message.get("id") or context["message_id"]
            context["model"] = message.get("model") or context["model"]
            context["usage"] = message.get("usage", {})
            context["stop_reason"] = message.get("stop_reason")

        return context

    def _is_opus_limit(self, content_lower: str) -> bool:
        """
        Determine whether the provided content string indicates an Opus-specific limit message.
        
        Returns:
            bool: True if the content references "opus" and contains limit-related phrases; otherwise, False.
        """
        if "opus" not in content_lower:
            return False

        limit_phrases = ["rate limit", "limit exceeded", "limit reached", "limit hit"]
        return (
            any(phrase in content_lower for phrase in limit_phrases)
            or "limit" in content_lower
        )

    def _extract_wait_time(
        self, content: str, timestamp: datetime
    ) -> Tuple[Optional[datetime], Optional[int]]:
        """
        Extracts the wait time in minutes from the provided content and calculates the corresponding reset time.
        
        Parameters:
            content (str): The message content potentially containing a wait time.
            timestamp (datetime): The reference timestamp to calculate the reset time from.
        
        Returns:
            Tuple[Optional[datetime], Optional[int]]: A tuple containing the reset time as a datetime object and the wait duration in minutes, or (None, None) if no wait time is found.
        """
        wait_match = re.search(r"wait\s+(\d+)\s+minutes?", content.lower())
        if wait_match:
            wait_minutes = int(wait_match.group(1))
            reset_time = timestamp + timedelta(minutes=wait_minutes)
            return reset_time, wait_minutes
        return None, None

    def _parse_reset_timestamp(self, text: str) -> Optional[datetime]:
        """
        Extracts and parses a reset timestamp from a limit message string.
        
        Searches for a numeric timestamp following the pattern "limit reached|<timestamp>" in the provided text and converts it to a datetime using the centralized TimestampProcessor. Returns None if no valid timestamp is found or parsing fails.
        
        Parameters:
            text (str): The message text potentially containing a reset timestamp.
        
        Returns:
            Optional[datetime]: The parsed reset time as a datetime object, or None if not found or invalid.
        """
        from claude_monitor.core.data_processors import TimestampProcessor

        match = re.search(r"limit reached\|(\d+)", text)
        if match:
            try:
                timestamp_value = int(match.group(1))
                processor = TimestampProcessor()
                return processor.parse_timestamp(timestamp_value)
            except (ValueError, OSError):
                pass
        return None
