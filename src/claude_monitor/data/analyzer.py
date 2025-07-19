"""Session analyzer for Claude Monitor.

Combines session block creation and limit detection functionality.
"""

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

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
        """Initialize analyzer with session duration.

        Args:
            session_duration_hours: Duration of each session block in hours
        """
        self.session_duration_hours = session_duration_hours
        self.session_duration = timedelta(hours=session_duration_hours)
        self.timezone_handler = TimezoneHandler()

    def transform_to_blocks(self, entries: List[UsageEntry]) -> List[SessionBlock]:
        """Process entries and create session blocks.

        Args:
            entries: List of usage entries to transform

        Returns:
            List of session blocks
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
        """Detect token limit messages from raw JSONL entries.

        Args:
            raw_entries: List of raw JSONL entries

        Returns:
            List of detected limit information
        """
        limits: List[Dict[str, Any]] = []

        for raw_data in raw_entries:
            limit_info = self._detect_single_limit(raw_data)
            if limit_info:
                limits.append(limit_info)

        return limits

    def _should_create_new_block(self, block: SessionBlock, entry: UsageEntry) -> bool:
        """Check if new block is needed."""
        if entry.timestamp >= block.end_time:
            return True

        return (
            block.entries
            and (entry.timestamp - block.entries[-1].timestamp) >= self.session_duration
        )

    def _round_to_hour(self, timestamp: datetime) -> datetime:
        """Round timestamp to the nearest full hour in UTC."""
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        elif timestamp.tzinfo != timezone.utc:
            timestamp = timestamp.astimezone(timezone.utc)

        return timestamp.replace(minute=0, second=0, microsecond=0)

    def _create_new_block(self, entry: UsageEntry) -> SessionBlock:
        """Create a new session block."""
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
        """Add entry to block and aggregate data per model."""
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

        model_stats: Dict[str, Union[int, float]] = block.per_model_stats[model]
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
        """Set actual end time and calculate totals."""
        if block.entries:
            block.actual_end_time = block.entries[-1].timestamp

        # Update sent_messages_count
        block.sent_messages_count = len(block.entries)

    def _check_for_gap(
        self, last_block: SessionBlock, next_entry: UsageEntry
    ) -> Optional[SessionBlock]:
        """Check for inactivity gap between blocks."""
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
        """Mark blocks as active if they're still ongoing."""
        current_time = datetime.now(timezone.utc)

        for block in blocks:
            if not block.is_gap and block.end_time > current_time:
                block.is_active = True

    # Limit detection methods

    def _detect_single_limit(
        self, raw_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Detect token limit messages from a single JSONL entry."""
        entry_type = raw_data.get("type")

        if entry_type == "system":
            return self._process_system_message(raw_data)
        if entry_type == "user":
            return self._process_user_message(raw_data)

        return None

    def _process_system_message(
        self, raw_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Process system messages for limit detection."""
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
        """Process user messages for tool result limit detection."""
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
        """Process a single tool result item for limit detection."""
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
        self, raw_data: Dict[str, Any], message: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Extract block context from raw data."""
        context: Dict[str, Any] = {
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
        """Check if content indicates an Opus-specific limit."""
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
        """Extract wait time and calculate reset time from content."""
        wait_match = re.search(r"wait\s+(\d+)\s+minutes?", content.lower())
        if wait_match:
            wait_minutes = int(wait_match.group(1))
            reset_time = timestamp + timedelta(minutes=wait_minutes)
            return reset_time, wait_minutes
        return None, None

    def _parse_reset_timestamp(self, text: str) -> Optional[datetime]:
        """Parse reset timestamp from limit message using centralized processor."""
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
