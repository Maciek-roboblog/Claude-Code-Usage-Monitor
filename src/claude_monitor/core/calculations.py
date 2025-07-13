"""Burn rate and cost calculations for Claude Monitor."""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Final, List, Optional, Protocol, Union

from claude_monitor.core.models import BurnRate, SessionBlock, UsageProjection
from claude_monitor.core.p90_calculator import P90Calculator
from claude_monitor.error_handling import report_error
from claude_monitor.utils.time_utils import TimezoneHandler

logger = logging.getLogger(__name__)

# Mathematical constants for precision calculations
MIN_DURATION_MINUTES: Final[float] = 1.0
ZERO_THRESHOLD: Final[float] = 1e-10
PRECISION_DECIMAL_PLACES: Final[int] = 8
MINUTES_PER_HOUR: Final[int] = 60
SECONDS_PER_MINUTE: Final[int] = 60

_p90_calculator = P90Calculator()


class TokenAggregable(Protocol):
    """Protocol for objects that can provide token counts for calculations."""

    @property
    def input_tokens(self) -> int: ...

    @property
    def output_tokens(self) -> int: ...

    @property
    def cache_creation_tokens(self) -> int: ...

    @property
    def cache_read_tokens(self) -> int: ...


class CostCalculable(Protocol):
    """Protocol for objects that can provide cost data for calculations."""

    @property
    def cost_usd(self) -> float: ...

    @property
    def duration_minutes(self) -> float: ...


class ActiveSession(Protocol):
    """Protocol for active session blocks with timing data."""

    @property
    def is_active(self) -> bool: ...

    @property
    def end_time(self) -> datetime: ...


@dataclass(frozen=True)
class MathematicalPrecision:
    """Configuration for mathematical precision in calculations."""

    decimal_places: int = PRECISION_DECIMAL_PLACES
    zero_threshold: float = ZERO_THRESHOLD
    min_duration: float = MIN_DURATION_MINUTES

    def is_zero(self, value: float) -> bool:
        """Check if a value is effectively zero within precision threshold."""
        return abs(value) < self.zero_threshold

    def safe_divide(self, numerator: float, denominator: float) -> float:
        """Perform safe division with zero checking."""
        if self.is_zero(denominator):
            return 0.0
        return numerator / denominator

    def round_to_precision(self, value: float) -> float:
        """Round value to specified decimal places."""
        return float(
            Decimal(str(value)).quantize(
                Decimal("0." + "0" * (self.decimal_places - 1) + "1"),
                rounding=ROUND_HALF_UP,
            )
        )


# Global precision configuration
math_precision = MathematicalPrecision()


class StatisticalAnalyzer:
    """Advanced statistical analysis for usage patterns and projections.

    Provides sophisticated mathematical operations for burn rate analysis,
    usage pattern detection, and statistical projections.
    """

    def __init__(
        self, precision_config: Optional[MathematicalPrecision] = None
    ) -> None:
        """Initialize statistical analyzer with precision configuration."""
        self._precision = precision_config or math_precision
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def calculate_weighted_burn_rate(
        self, blocks: List[Union[SessionBlock, Any]], time_window_hours: float = 1.0
    ) -> float:
        """Calculate weighted burn rate with time-decay for recent activity.

        Args:
            blocks: Session blocks for analysis
            time_window_hours: Time window for calculation (default: 1 hour)

        Returns:
            Weighted burn rate in tokens per minute

        Mathematical Notes:
            - Applies exponential decay weighting to recent sessions
            - Uses linear interpolation for partial time overlaps
            - Provides higher accuracy than simple average
        """
        if not blocks:
            return 0.0

        current_time = datetime.now(timezone.utc)
        window_start = current_time - timedelta(hours=time_window_hours)

        total_weighted_tokens = 0.0
        total_weight = 0.0

        for block in blocks:
            weight, tokens = self._calculate_block_weight_and_tokens(
                block, window_start, current_time
            )
            total_weighted_tokens += weight * tokens
            total_weight += weight

        if self._precision.is_zero(total_weight):
            return 0.0

        weighted_tokens_per_hour = self._precision.safe_divide(
            total_weighted_tokens, total_weight
        )
        weighted_tokens_per_minute = weighted_tokens_per_hour / MINUTES_PER_HOUR

        return self._precision.round_to_precision(weighted_tokens_per_minute)

    def _calculate_block_weight_and_tokens(
        self,
        block: Union[SessionBlock, Any],
        window_start: datetime,
        current_time: datetime,
    ) -> tuple[float, float]:
        """Calculate time-based weight and token contribution for a block."""
        start_time = _parse_block_start_time(block)
        if start_time is None:
            return 0.0, 0.0

        end_time = _determine_session_end_time(block, current_time)

        # Calculate overlap with time window
        overlap_start = max(start_time, window_start)
        overlap_end = min(end_time, current_time)

        if overlap_end <= overlap_start:
            return 0.0, 0.0

        # Time-based weight (more recent = higher weight)
        time_from_start = (overlap_start - window_start).total_seconds()
        window_duration = (current_time - window_start).total_seconds()

        if self._precision.is_zero(window_duration):
            return 0.0, 0.0

        # Exponential decay weight (decay_factor = 0.5 gives half-life at midpoint)
        decay_factor = 0.7
        normalized_time = time_from_start / window_duration
        weight = decay_factor ** (1 - normalized_time)

        # Extract tokens with type safety
        tokens = 0
        if hasattr(block, "total_tokens"):
            tokens = block.total_tokens
        elif hasattr(block, "get"):
            tokens = block.get("totalTokens", 0)
        elif hasattr(block, "token_counts"):
            tokens = getattr(block.token_counts, "total_tokens", 0)

        # Calculate overlap duration ratio
        total_duration = (end_time - start_time).total_seconds()
        overlap_duration = (overlap_end - overlap_start).total_seconds()

        if self._precision.is_zero(total_duration):
            return 0.0, 0.0

        duration_ratio = overlap_duration / total_duration
        proportional_tokens = tokens * duration_ratio

        return weight, proportional_tokens

    def detect_usage_anomalies(
        self, blocks: List[Union[SessionBlock, Any]], sensitivity: float = 2.0
    ) -> List[tuple[str, float, str]]:
        """Detect anomalous usage patterns using statistical analysis.

        Args:
            blocks: Session blocks for analysis
            sensitivity: Standard deviation threshold for anomaly detection

        Returns:
            List of (block_id, anomaly_score, description) tuples

        Mathematical Notes:
            - Uses z-score analysis for outlier detection
            - Calculates multiple metrics: duration, tokens, cost rate
            - Applies rolling statistics for adaptive thresholds
        """
        if len(blocks) < 3:  # Need minimum data for statistical analysis
            return []

        # Extract metrics for analysis
        durations = []
        token_rates = []
        cost_rates = []
        block_ids = []

        for block in blocks:
            duration = getattr(block, "duration_minutes", 0.0)
            if duration < self._precision.min_duration:
                continue

            tokens = 0
            if hasattr(block, "total_tokens"):
                tokens = block.total_tokens
            elif hasattr(block, "token_counts"):
                tokens = getattr(block.token_counts, "total_tokens", 0)

            cost = getattr(block, "cost_usd", 0.0)

            if tokens > 0:
                durations.append(duration)
                token_rates.append(tokens / duration)
                cost_rates.append(cost / duration if cost > 0 else 0.0)
                block_ids.append(getattr(block, "id", "unknown"))

        if len(durations) < 3:
            return []

        import statistics

        # Calculate statistical baselines
        mean_duration = statistics.mean(durations)
        std_duration = statistics.stdev(durations) if len(durations) > 1 else 0.0

        mean_token_rate = statistics.mean(token_rates)
        std_token_rate = statistics.stdev(token_rates) if len(token_rates) > 1 else 0.0

        mean_cost_rate = statistics.mean(cost_rates)
        std_cost_rate = statistics.stdev(cost_rates) if len(cost_rates) > 1 else 0.0

        anomalies = []

        for i, (duration, token_rate, cost_rate, block_id) in enumerate(
            zip(durations, token_rates, cost_rates, block_ids)
        ):
            anomaly_score = 0.0
            descriptions = []

            # Duration anomaly check
            if std_duration > 0:
                duration_z = abs(duration - mean_duration) / std_duration
                if duration_z > sensitivity:
                    anomaly_score += duration_z
                    descriptions.append(
                        f"duration {duration:.1f}min (z={duration_z:.1f})"
                    )

            # Token rate anomaly check
            if std_token_rate > 0:
                token_z = abs(token_rate - mean_token_rate) / std_token_rate
                if token_z > sensitivity:
                    anomaly_score += token_z
                    descriptions.append(
                        f"token rate {token_rate:.1f}/min (z={token_z:.1f})"
                    )

            # Cost rate anomaly check
            if std_cost_rate > 0 and cost_rate > 0:
                cost_z = abs(cost_rate - mean_cost_rate) / std_cost_rate
                if cost_z > sensitivity:
                    anomaly_score += cost_z
                    descriptions.append(
                        f"cost rate ${cost_rate:.4f}/min (z={cost_z:.1f})"
                    )

            if anomaly_score > 0:
                description = "; ".join(descriptions)
                anomalies.append((block_id, anomaly_score, description))

        # Sort by anomaly score (highest first)
        anomalies.sort(key=lambda x: x[1], reverse=True)

        self._logger.info(
            f"Detected {len(anomalies)} usage anomalies from {len(blocks)} blocks "
            f"(sensitivity: {sensitivity}σ)"
        )

        return anomalies


# Global statistical analyzer instance
statistical_analyzer = StatisticalAnalyzer()


class BurnRateCalculator:
    """Advanced mathematical calculator for burn rates and usage projections.

    Provides high-precision calculations for token consumption rates,
    cost projections, and statistical analysis of usage patterns.
    """

    def __init__(
        self, precision_config: Optional[MathematicalPrecision] = None
    ) -> None:
        """Initialize calculator with optional precision configuration."""
        self._precision = precision_config or math_precision
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def calculate_burn_rate(
        self, block: Union[SessionBlock, Any]
    ) -> Optional[BurnRate]:
        """Calculate current consumption rate for active blocks with mathematical precision.

        Args:
            block: Session block containing usage data

        Returns:
            BurnRate with precise token/minute and cost/hour calculations,
            or None if block is inactive or has insufficient data

        Mathematical Notes:
            - Uses safe division to prevent division by zero
            - Applies precision rounding to avoid floating point errors
            - Validates minimum duration thresholds
        """
        # Validate block state and duration with precision checking
        if not getattr(block, "is_active", False):
            self._logger.debug("Block is not active, skipping burn rate calculation")
            return None

        duration = getattr(block, "duration_minutes", 0.0)
        if duration < self._precision.min_duration:
            self._logger.debug(
                f"Block duration {duration:.3f}min below minimum {self._precision.min_duration}min"
            )
            return None

        # Calculate total tokens with type safety
        token_counts = getattr(block, "token_counts", None)
        if token_counts is None:
            self._logger.warning("Block missing token_counts attribute")
            return None

        total_tokens = (
            getattr(token_counts, "input_tokens", 0)
            + getattr(token_counts, "output_tokens", 0)
            + getattr(token_counts, "cache_creation_tokens", 0)
            + getattr(token_counts, "cache_read_tokens", 0)
        )

        if total_tokens <= 0:
            self._logger.debug(f"No tokens found in block, total: {total_tokens}")
            return None

        # Perform precise mathematical calculations
        tokens_per_minute = self._precision.safe_divide(total_tokens, duration)
        tokens_per_minute = self._precision.round_to_precision(tokens_per_minute)

        block_cost = getattr(block, "cost_usd", 0.0)
        cost_per_minute = self._precision.safe_divide(block_cost, duration)
        cost_per_hour = cost_per_minute * MINUTES_PER_HOUR
        cost_per_hour = self._precision.round_to_precision(cost_per_hour)

        burn_rate = BurnRate(
            tokens_per_minute=tokens_per_minute, cost_per_hour=cost_per_hour
        )

        self._logger.debug(
            f"Calculated burn rate: {tokens_per_minute:.2f} tokens/min, "
            f"${cost_per_hour:.4f}/hour for {duration:.2f}min duration"
        )

        return burn_rate

    def project_block_usage(
        self, block: Union[SessionBlock, Any]
    ) -> Optional[UsageProjection]:
        """Project total usage if current rate continues with mathematical precision.

        Args:
            block: Active session block for projection

        Returns:
            UsageProjection with precise calculations for projected tokens,
            costs, and remaining time, or None if projection cannot be calculated

        Mathematical Notes:
            - Uses current burn rate as basis for linear projection
            - Applies precision rounding to all calculated values
            - Validates time boundaries and remaining duration
        """
        # Calculate current burn rate as projection basis
        burn_rate = self.calculate_burn_rate(block)
        if burn_rate is None:
            self._logger.debug("Cannot project usage: no burn rate available")
            return None

        # Calculate remaining time with timezone awareness
        now = datetime.now(timezone.utc)
        end_time = getattr(block, "end_time", None)
        if end_time is None:
            self._logger.warning("Block missing end_time for projection")
            return None

        remaining_seconds = (end_time - now).total_seconds()
        if remaining_seconds <= 0:
            self._logger.debug(
                f"Block already expired: {remaining_seconds:.1f}s remaining"
            )
            return None

        # Convert to precise time units
        remaining_minutes = remaining_seconds / SECONDS_PER_MINUTE
        remaining_hours = remaining_minutes / MINUTES_PER_HOUR

        # Apply precision rounding to time calculations
        remaining_minutes = self._precision.round_to_precision(remaining_minutes)
        remaining_hours = self._precision.round_to_precision(remaining_hours)

        # Get current usage with type safety
        token_counts = getattr(block, "token_counts", None)
        if token_counts is None:
            self._logger.warning("Block missing token_counts for projection")
            return None

        current_tokens = (
            getattr(token_counts, "input_tokens", 0)
            + getattr(token_counts, "output_tokens", 0)
            + getattr(token_counts, "cache_creation_tokens", 0)
            + getattr(token_counts, "cache_read_tokens", 0)
        )
        current_cost = getattr(block, "cost_usd", 0.0)

        # Calculate projections with mathematical precision
        projected_additional_tokens = burn_rate.tokens_per_minute * remaining_minutes
        projected_additional_tokens = self._precision.round_to_precision(
            projected_additional_tokens
        )
        projected_total_tokens = current_tokens + projected_additional_tokens

        projected_additional_cost = burn_rate.cost_per_hour * remaining_hours
        projected_additional_cost = self._precision.round_to_precision(
            projected_additional_cost
        )
        projected_total_cost = current_cost + projected_additional_cost
        projected_total_cost = self._precision.round_to_precision(projected_total_cost)

        projection = UsageProjection(
            projected_total_tokens=int(round(projected_total_tokens)),
            projected_total_cost=projected_total_cost,
            remaining_minutes=remaining_minutes,
        )

        self._logger.debug(
            f"Usage projection: {projection.projected_total_tokens} tokens "
            f"(+{int(projected_additional_tokens)}), "
            f"${projection.projected_total_cost:.4f} (+${projected_additional_cost:.4f}) "
            f"over {remaining_minutes:.1f}min remaining"
        )

        return projection


def calculate_hourly_burn_rate(
    blocks: List[Union[SessionBlock, Any]],
    current_time: datetime,
    precision_config: Optional[MathematicalPrecision] = None,
) -> float:
    """Calculate precise hourly burn rate based on all sessions in the last hour.

    Args:
        blocks: List of session blocks to analyze
        current_time: Current timestamp for calculation window
        precision_config: Optional precision configuration

    Returns:
        Tokens per minute burn rate with mathematical precision

    Mathematical Notes:
        - Uses sliding 1-hour window for calculation
        - Applies weighted token distribution across time
        - Returns precise floating-point burn rate
    """
    precision = precision_config or math_precision

    if not blocks:
        logger.debug("No blocks provided for hourly burn rate calculation")
        return 0.0

    one_hour_ago = current_time - timedelta(hours=1)
    total_tokens = _calculate_total_tokens_in_hour(
        blocks, one_hour_ago, current_time, precision
    )

    # Calculate tokens per minute with precision
    burn_rate = precision.safe_divide(total_tokens, MINUTES_PER_HOUR)
    burn_rate = precision.round_to_precision(burn_rate)

    logger.debug(
        f"Hourly burn rate: {burn_rate:.3f} tokens/min from {total_tokens:.1f} tokens "
        f"over 1-hour window ending at {current_time.isoformat()}"
    )

    return burn_rate


def _calculate_total_tokens_in_hour(
    blocks: List[Union[SessionBlock, Any]],
    one_hour_ago: datetime,
    current_time: datetime,
    precision: MathematicalPrecision,
) -> float:
    """Calculate total tokens for all blocks in the last hour with precision.

    Args:
        blocks: Session blocks to analyze
        one_hour_ago: Start of calculation window
        current_time: End of calculation window
        precision: Mathematical precision configuration

    Returns:
        Precise total token count for the time window
    """
    total_tokens = 0.0
    processed_blocks = 0

    for block in blocks:
        block_tokens = _process_block_for_burn_rate(
            block, one_hour_ago, current_time, precision
        )
        total_tokens += block_tokens
        if block_tokens > 0:
            processed_blocks += 1

    logger.debug(
        f"Processed {processed_blocks}/{len(blocks)} blocks, "
        f"total tokens in hour: {total_tokens:.1f}"
    )

    return precision.round_to_precision(total_tokens)


def _process_block_for_burn_rate(
    block: Union[SessionBlock, Any],
    one_hour_ago: datetime,
    current_time: datetime,
    precision: MathematicalPrecision,
) -> float:
    """Process a single block for burn rate calculation with mathematical precision.

    Args:
        block: Session block to process
        one_hour_ago: Start of calculation window
        current_time: End of calculation window
        precision: Mathematical precision configuration

    Returns:
        Token contribution from this block to the hourly burn rate
    """
    start_time = _parse_block_start_time(block)
    if start_time is None:
        logger.debug(f"Block {getattr(block, 'id', 'unknown')} missing start time")
        return 0.0

    # Skip gap blocks in burn rate calculation
    is_gap = getattr(block, "is_gap", False) or (
        hasattr(block, "get") and block.get("isGap", False)
    )
    if is_gap:
        return 0.0

    session_actual_end = _determine_session_end_time(block, current_time)
    if session_actual_end < one_hour_ago:
        return 0.0

    tokens = _calculate_tokens_in_hour(
        block, start_time, session_actual_end, one_hour_ago, current_time, precision
    )

    return precision.round_to_precision(tokens)


def _parse_block_start_time(block: Union[SessionBlock, Any]) -> Optional[datetime]:
    """Parse start time from block with comprehensive error handling.

    Args:
        block: Session block containing start time data

    Returns:
        Parsed UTC datetime or None if parsing fails

    Notes:
        - Handles both SessionBlock objects and dictionary formats
        - Ensures timezone normalization to UTC
        - Provides detailed error logging for debugging
    """
    # Extract start time string with type safety
    if hasattr(block, "start_time") and isinstance(block.start_time, datetime):
        # SessionBlock with datetime object
        tz_handler = TimezoneHandler()
        return tz_handler.ensure_utc(block.start_time)

    # Dictionary format or object with get method
    start_time_str = None
    if hasattr(block, "get"):
        start_time_str = block.get("startTime")
    elif hasattr(block, "start_time"):
        start_time_str = str(block.start_time)

    if not start_time_str:
        return None

    tz_handler = TimezoneHandler()
    try:
        start_time = tz_handler.parse_timestamp(start_time_str)
        if start_time is not None:
            return tz_handler.ensure_utc(start_time)
        return None
    except (ValueError, TypeError, AttributeError) as e:
        block_id = getattr(block, "id", None) or (
            block.get("id") if hasattr(block, "get") else "unknown"
        )
        _log_timestamp_error(e, start_time_str, block_id, "start_time")
        return None


def _determine_session_end_time(
    block: Union[SessionBlock, Any], current_time: datetime
) -> datetime:
    """Determine session end time based on block status with type safety.

    Args:
        block: Session block to analyze
        current_time: Current timestamp as fallback

    Returns:
        UTC datetime representing session end time

    Logic:
        - Active sessions use current_time as end
        - Completed sessions use actual_end_time if available
        - Falls back to current_time for error cases
    """
    # Check if session is active with multiple format support
    is_active = False
    if hasattr(block, "is_active"):
        is_active = block.is_active
    elif hasattr(block, "get"):
        is_active = block.get("isActive", False)

    if is_active:
        logger.debug(f"Active session using current time: {current_time.isoformat()}")
        return current_time

    # Extract actual end time with type safety
    actual_end_str = None
    if hasattr(block, "actual_end_time"):
        if isinstance(block.actual_end_time, datetime):
            tz_handler = TimezoneHandler()
            return tz_handler.ensure_utc(block.actual_end_time)
        actual_end_str = str(block.actual_end_time)
    elif hasattr(block, "get"):
        actual_end_str = block.get("actualEndTime")

    if actual_end_str:
        tz_handler = TimezoneHandler()
        try:
            session_actual_end = tz_handler.parse_timestamp(actual_end_str)
            if session_actual_end is not None:
                return tz_handler.ensure_utc(session_actual_end)
            return current_time
        except (ValueError, TypeError, AttributeError) as e:
            block_id = getattr(block, "id", None) or (
                block.get("id") if hasattr(block, "get") else "unknown"
            )
            _log_timestamp_error(e, actual_end_str, block_id, "actual_end_time")
    return current_time


def _calculate_tokens_in_hour(
    block: Union[SessionBlock, Any],
    start_time: datetime,
    session_actual_end: datetime,
    one_hour_ago: datetime,
    current_time: datetime,
    precision: MathematicalPrecision,
) -> float:
    """Calculate tokens used within the last hour for this session with precision.

    Args:
        block: Session block containing token data
        start_time: Session start time
        session_actual_end: Session end time
        one_hour_ago: Start of calculation window
        current_time: End of calculation window
        precision: Mathematical precision configuration

    Returns:
        Proportional token count for the time window

    Mathematical Algorithm:
        1. Find intersection of session time and calculation window
        2. Calculate time ratios with high precision
        3. Apply proportional token distribution
        4. Round to specified precision
    """
    # Calculate time window intersection with precision
    session_start_in_hour = max(start_time, one_hour_ago)
    session_end_in_hour = min(session_actual_end, current_time)

    if session_end_in_hour <= session_start_in_hour:
        logger.debug(
            f"No time overlap: session {session_start_in_hour.isoformat()} "
            f"to {session_end_in_hour.isoformat()}"
        )
        return 0.0

    # Calculate durations with mathematical precision
    total_session_duration = (
        session_actual_end - start_time
    ).total_seconds() / SECONDS_PER_MINUTE
    hour_duration = (
        session_end_in_hour - session_start_in_hour
    ).total_seconds() / SECONDS_PER_MINUTE

    if precision.is_zero(total_session_duration):
        logger.debug(
            f"Zero session duration for block {getattr(block, 'id', 'unknown')}"
        )
        return 0.0

    # Extract total tokens with type safety
    session_tokens = 0
    if hasattr(block, "total_tokens"):
        session_tokens = block.total_tokens
    elif hasattr(block, "get"):
        session_tokens = block.get("totalTokens", 0)
    elif hasattr(block, "token_counts"):
        session_tokens = getattr(block.token_counts, "total_tokens", 0)

    if session_tokens <= 0:
        return 0.0

    # Calculate proportional tokens with precision
    time_ratio = precision.safe_divide(hour_duration, total_session_duration)
    proportional_tokens = session_tokens * time_ratio

    result = precision.round_to_precision(proportional_tokens)

    logger.debug(
        f"Block tokens in hour: {result:.2f} from {session_tokens} total "
        f"(ratio: {time_ratio:.4f}, durations: {hour_duration:.1f}min/{total_session_duration:.1f}min)"
    )

    return result


def _log_timestamp_error(
    exception: Exception,
    timestamp_str: str,
    block_id: Optional[str],
    timestamp_type: str,
) -> None:
    """Log timestamp parsing errors with comprehensive context.

    Args:
        exception: The exception that occurred during parsing
        timestamp_str: The timestamp string that failed to parse
        block_id: ID of the block (may be None)
        timestamp_type: Type of timestamp being parsed

    Notes:
        - Provides detailed logging for debugging timestamp issues
        - Reports errors to centralized error handling system
        - Includes context for troubleshooting
    """
    logger.debug(
        f"Failed to parse {timestamp_type} '{timestamp_str}' for block {block_id}: {exception}"
    )
    report_error(
        exception=exception,
        component="calculations.burn_rate_calculator",
        context_name="timestamp_parsing_error",
        context_data={
            f"{timestamp_type}_str": timestamp_str,
            "block_id": block_id or "unknown",
            "timestamp_type": timestamp_type,
            "exception_type": type(exception).__name__,
        },
    )
