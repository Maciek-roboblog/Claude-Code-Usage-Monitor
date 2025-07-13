"""Session analyzer for Claude Monitor.

Combines session block creation and limit detection functionality.
"""

import logging
import re
import sys
from datetime import datetime, timedelta, timezone
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Protocol,
    Tuple,
    TypeVar,
    Union,
)

# Type alias handling for Python version compatibility
try:
    from typing_extensions import TypeAlias
except ImportError:
    # For older environments, we'll use simple type definitions
    pass

if sys.version_info >= (3, 8):
    from typing import Literal
else:
    try:
        from typing_extensions import Literal
    except ImportError:
        # Fallback for environments without typing_extensions
        Literal = Any

import numpy as np
from numpy.typing import NDArray

from claude_monitor.core.models import (
    SessionBlock,
    TokenCounts,
    UsageEntry,
    normalize_model_name,
)
from claude_monitor.utils.time_utils import TimezoneHandler

logger = logging.getLogger(__name__)

# Advanced Type Aliases for Data Science Patterns
TimeSeries: TypeAlias = NDArray[np.datetime64]
TokenArray: TypeAlias = NDArray[np.int64]
CostArray: TypeAlias = NDArray[np.float64]
AnalysisMetrics: TypeAlias = Dict[str, Union[int, float, str]]
ModelStatsDict: TypeAlias = Dict[str, Dict[str, Union[int, float]]]
LimitDetectionResult: TypeAlias = Dict[str, Any]
TimestampValue: TypeAlias = Union[str, int, float, datetime]
StatisticalResult: TypeAlias = Tuple[float, float, int]  # mean, std, count

# Generic Type Variables for Enhanced Type Safety
T = TypeVar("T")
DataPointT = TypeVar("DataPointT", bound=Union[int, float])
AnalysisT = TypeVar("AnalysisT", bound="SessionBlock")

# Literal Types for Analysis Categories
LimitType = Literal["opus_limit", "system_limit", "general_limit"]
AnalysisMode = Literal["real_time", "historical", "predictive"]
AggregationMethod = Literal["sum", "mean", "median", "max", "min"]


class DataAnalysisProtocol(Protocol):
    """Protocol defining the interface for data analysis operations."""

    def compute_statistics(self, data: TokenArray) -> StatisticalResult:
        """Compute statistical measures for token data."""
        ...

    def detect_anomalies(
        self, values: TokenArray, threshold: float = 2.0
    ) -> NDArray[np.bool_]:
        """Detect statistical anomalies in data using z-score method."""
        ...

    def calculate_trends(
        self, timestamps: TimeSeries, values: TokenArray
    ) -> Tuple[float, float]:
        """Calculate trend analysis (slope, correlation) for time series data."""
        ...


class TokenAnalysisEngine:
    """Advanced token analysis engine with scientific computing patterns."""

    @staticmethod
    def compute_statistics(data: TokenArray) -> StatisticalResult:
        """Compute comprehensive statistical measures for token data.

        Args:
            data: Array of token counts

        Returns:
            Tuple of (mean, standard_deviation, count)
        """
        if len(data) == 0:
            return (0.0, 0.0, 0)

        mean_val = float(np.mean(data))
        std_val = float(np.std(data, ddof=1) if len(data) > 1 else 0.0)
        count_val = int(len(data))

        return (mean_val, std_val, count_val)

    @staticmethod
    def detect_anomalies(
        values: Union[TokenArray, CostArray], threshold: float = 2.0
    ) -> NDArray[np.bool_]:
        """Detect statistical anomalies using z-score method.

        Args:
            values: Array of values to analyze
            threshold: Z-score threshold for anomaly detection

        Returns:
            Boolean array indicating anomalous values
        """
        if len(values) < 2:
            empty_result: NDArray[np.bool_] = np.array([], dtype=bool)
            return empty_result

        mean_val = np.mean(values)
        std_val = np.std(values, ddof=1)

        if std_val == 0:
            zero_result: NDArray[np.bool_] = np.zeros(len(values), dtype=bool)
            return zero_result

        z_scores = np.abs((values - mean_val) / std_val)
        result: NDArray[np.bool_] = z_scores > threshold
        return result

    @staticmethod
    def calculate_trends(
        timestamps: TimeSeries, values: TokenArray
    ) -> Tuple[float, float]:
        """Calculate trend analysis for time series data.

        Args:
            timestamps: Array of timestamps
            values: Array of corresponding values

        Returns:
            Tuple of (slope, correlation_coefficient)
        """
        if len(timestamps) < 2 or len(values) < 2:
            return (0.0, 0.0)

        # Convert timestamps to numerical values (seconds since epoch)
        time_numeric = np.array([ts.timestamp() for ts in timestamps])

        # Calculate linear regression slope
        correlation_matrix = np.corrcoef(time_numeric, values)
        correlation = (
            float(correlation_matrix[0, 1])
            if not np.isnan(correlation_matrix[0, 1])
            else 0.0
        )

        # Calculate slope using least squares
        n = len(time_numeric)
        sum_x = np.sum(time_numeric)
        sum_y = np.sum(values)
        sum_xy = np.sum(time_numeric * values)
        sum_x2 = np.sum(time_numeric**2)

        denominator = n * sum_x2 - sum_x**2
        slope = (
            float((n * sum_xy - sum_x * sum_y) / denominator)
            if denominator != 0
            else 0.0
        )

        return (slope, correlation)


class SessionAnalyzer:
    """Advanced session analyzer with data science capabilities.

    Combines session block creation, limit detection, and statistical analysis
    with scientific computing patterns for enhanced data insights.
    """

    def __init__(
        self, session_duration_hours: int = 5, analysis_mode: AnalysisMode = "real_time"
    ) -> None:
        """Initialize analyzer with session duration and analysis configuration.

        Args:
            session_duration_hours: Duration of each session block in hours
            analysis_mode: Analysis mode for data processing strategy
        """
        self.session_duration_hours = session_duration_hours
        self.session_duration = timedelta(hours=session_duration_hours)
        self.timezone_handler = TimezoneHandler()
        self.analysis_mode: AnalysisMode = analysis_mode
        self.analysis_engine = TokenAnalysisEngine()

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

    def detect_limits(
        self, raw_entries: List[Dict[str, Any]]
    ) -> List[LimitDetectionResult]:
        """Detect token limit messages from raw JSONL entries with enhanced typing.

        Args:
            raw_entries: List of raw JSONL entries

        Returns:
            List of detected limit information with structured typing
        """
        limits = []

        for raw_data in raw_entries:
            limit_info = self._detect_single_limit(raw_data)
            if limit_info:
                limits.append(limit_info)

        return limits

    def _should_create_new_block(self, block: SessionBlock, entry: UsageEntry) -> bool:
        """Check if new block is needed."""
        if entry.timestamp >= block.end_time:
            return True

        return bool(
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
        """Add entry to block and aggregate data per model with enhanced analytics."""
        block.entries.append(entry)

        raw_model = entry.model or "unknown"
        model = normalize_model_name(raw_model) if raw_model != "unknown" else "unknown"

        # Initialize model stats with proper typing
        if model not in block.per_model_stats:
            block.per_model_stats[model] = {
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_creation_tokens": 0,
                "cache_read_tokens": 0,
                "cost_usd": 0.0,
                "entries_count": 0,
            }

        # Type-safe model stats updating
        model_stats: Dict[str, Union[int, float]] = block.per_model_stats[model]
        model_stats["input_tokens"] = (
            int(model_stats["input_tokens"]) + entry.input_tokens
        )
        model_stats["output_tokens"] = (
            int(model_stats["output_tokens"]) + entry.output_tokens
        )
        model_stats["cache_creation_tokens"] = (
            int(model_stats["cache_creation_tokens"]) + entry.cache_creation_tokens
        )
        model_stats["cache_read_tokens"] = (
            int(model_stats["cache_read_tokens"]) + entry.cache_read_tokens
        )
        model_stats["cost_usd"] = float(model_stats["cost_usd"]) + (
            entry.cost_usd or 0.0
        )
        model_stats["entries_count"] = int(model_stats["entries_count"]) + 1

        # Update aggregated token counts
        block.token_counts.input_tokens += entry.input_tokens
        block.token_counts.output_tokens += entry.output_tokens
        block.token_counts.cache_creation_tokens += entry.cache_creation_tokens
        block.token_counts.cache_read_tokens += entry.cache_read_tokens

        # Update aggregated cost (sum across all models)
        if entry.cost_usd:
            from decimal import Decimal

            block.cost_usd += Decimal(str(entry.cost_usd))

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
    ) -> Optional[LimitDetectionResult]:
        """Detect token limit messages from a single JSONL entry with enhanced typing."""
        entry_type = raw_data.get("type")

        if entry_type == "system":
            return self._process_system_message(raw_data)
        if entry_type == "user":
            return self._process_user_message(raw_data)

        return None

    def _process_system_message(
        self, raw_data: Dict[str, Any]
    ) -> Optional[LimitDetectionResult]:
        """Process system messages for limit detection with enhanced typing."""
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
            if timestamp is None:
                return None

            block_context = self._extract_block_context(raw_data)

            # Check for Opus-specific limit
            if self._is_opus_limit(content_lower):
                reset_time, wait_minutes = self._extract_wait_time(content, timestamp)
                limit_result: LimitDetectionResult = {
                    "type": "opus_limit",
                    "timestamp": timestamp,
                    "content": content,
                    "reset_time": reset_time,
                    "wait_minutes": wait_minutes,
                    "raw_data": raw_data,
                    "block_context": block_context,
                }
                return limit_result

            # General system limit
            system_limit_result: LimitDetectionResult = {
                "type": "system_limit",
                "timestamp": timestamp,
                "content": content,
                "reset_time": None,
                "raw_data": raw_data,
                "block_context": block_context,
            }
            return system_limit_result

        except (ValueError, TypeError):
            return None

    def _process_user_message(
        self, raw_data: Dict[str, Any]
    ) -> Optional[LimitDetectionResult]:
        """Process user messages for tool result limit detection with enhanced typing."""
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
    ) -> Optional[LimitDetectionResult]:
        """Process a single tool result item for limit detection with enhanced typing."""
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
                general_limit_result: LimitDetectionResult = {
                    "type": "general_limit",
                    "timestamp": timestamp,
                    "content": text,
                    "reset_time": self._parse_reset_timestamp(text),
                    "raw_data": raw_data,
                    "block_context": self._extract_block_context(raw_data, message),
                }
                return general_limit_result
            except (ValueError, TypeError):
                continue

        return None

    def _extract_block_context(
        self, raw_data: Dict[str, Any], message: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Extract block context from raw data."""
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

    def compute_block_analytics(self, block: SessionBlock) -> AnalysisMetrics:
        """Compute advanced analytics for a session block.

        Args:
            block: Session block to analyze

        Returns:
            Dictionary of computed analytics metrics
        """
        if not block.entries:
            return {
                "mean_tokens_per_entry": 0.0,
                "std_tokens_per_entry": 0.0,
                "total_entries": 0,
                "token_efficiency": 0.0,
                "cost_per_token": 0.0,
            }

        # Extract token arrays for analysis
        input_tokens = np.array(
            [entry.input_tokens for entry in block.entries], dtype=np.int64
        )
        output_tokens = np.array(
            [entry.output_tokens for entry in block.entries], dtype=np.int64
        )
        total_tokens_per_entry = input_tokens + output_tokens

        # Compute statistics using the analysis engine
        mean_tokens, std_tokens, entry_count = self.analysis_engine.compute_statistics(
            total_tokens_per_entry
        )

        # Calculate efficiency metrics
        total_input = int(np.sum(input_tokens))
        total_output = int(np.sum(output_tokens))
        token_efficiency = float(total_output / max(total_input, 1))

        # Calculate cost efficiency
        total_cost = block.cost_usd
        total_tokens = total_input + total_output
        cost_per_token = float(total_cost / max(total_tokens, 1))

        analytics: AnalysisMetrics = {
            "mean_tokens_per_entry": mean_tokens,
            "std_tokens_per_entry": std_tokens,
            "total_entries": entry_count,
            "token_efficiency": token_efficiency,
            "cost_per_token": cost_per_token,
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "input_output_ratio": token_efficiency,
        }

        return analytics

    def detect_usage_anomalies(
        self, blocks: List[SessionBlock]
    ) -> List[Tuple[int, str]]:
        """Detect anomalous usage patterns across session blocks.

        Args:
            blocks: List of session blocks to analyze

        Returns:
            List of (block_index, anomaly_description) tuples
        """
        if len(blocks) < 3:  # Need minimum data for anomaly detection
            return []

        # Extract metrics for anomaly detection
        token_totals = np.array(
            [block.token_counts.total_tokens for block in blocks if not block.is_gap],
            dtype=np.int64,
        )

        costs = np.array(
            [block.cost_usd for block in blocks if not block.is_gap], dtype=np.float64
        )

        anomalies: List[Tuple[int, str]] = []

        # Detect token usage anomalies
        if len(token_totals) > 0:
            token_anomalies = self.analysis_engine.detect_anomalies(
                token_totals, threshold=2.5
            )
            for i, is_anomaly in enumerate(token_anomalies):
                if is_anomaly:
                    anomalies.append(
                        (i, f"Unusual token usage: {token_totals[i]:,} tokens")
                    )

        # Detect cost anomalies
        if len(costs) > 0:
            cost_anomalies = self.analysis_engine.detect_anomalies(costs, threshold=2.5)
            for i, is_anomaly in enumerate(cost_anomalies):
                if is_anomaly:
                    anomalies.append((i, f"Unusual cost pattern: ${costs[i]:.2f}"))

        return anomalies
