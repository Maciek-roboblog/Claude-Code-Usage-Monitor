"""Burn rate and cost calculations for Claude Monitor."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Protocol

from claude_monitor.core.models import (
    BurnRate,
    TokenCounts,
    UsageProjection,
)
from claude_monitor.core.p90_calculator import P90Calculator
from claude_monitor.error_handling import report_error
from claude_monitor.utils.time_utils import TimezoneHandler

logger: logging.Logger = logging.getLogger(__name__)

_p90_calculator: P90Calculator = P90Calculator()


class BlockLike(Protocol):
    """Protocol for objects that behave like session blocks."""

    is_active: bool
    duration_minutes: float
    token_counts: TokenCounts
    cost_usd: float
    end_time: datetime


class BurnRateCalculator:
    """Calculates burn rates and usage projections for session blocks."""

    def calculate_burn_rate(self, block: BlockLike) -> Optional[BurnRate]:
        """Calculate current consumption rate for active blocks."""
        if not block.is_active or block.duration_minutes < 1:
            return None

        total_tokens = (
            block.token_counts.input_tokens
            + block.token_counts.output_tokens
            + block.token_counts.cache_creation_tokens
            + block.token_counts.cache_read_tokens
        )
        if total_tokens == 0:
            return None

        tokens_per_minute = total_tokens / block.duration_minutes
        cost_per_hour = (
            (block.cost_usd / block.duration_minutes) * 60
            if block.duration_minutes > 0
            else 0
        )

        return BurnRate(
            tokens_per_minute=tokens_per_minute, cost_per_hour=cost_per_hour
        )

    def project_block_usage(self, block: BlockLike) -> Optional[UsageProjection]:
        """Project total usage if current rate continues."""
        burn_rate = self.calculate_burn_rate(block)
        if not burn_rate:
            return None

        now = datetime.now(timezone.utc)
        remaining_seconds = (block.end_time - now).total_seconds()
        if remaining_seconds <= 0:
            return None

        remaining_minutes = remaining_seconds / 60
        remaining_hours = remaining_minutes / 60

        current_tokens = (
            block.token_counts.input_tokens
            + block.token_counts.output_tokens
            + block.token_counts.cache_creation_tokens
            + block.token_counts.cache_read_tokens
        )
        current_cost = block.cost_usd

        projected_additional_tokens = burn_rate.tokens_per_minute * remaining_minutes
        projected_total_tokens = current_tokens + projected_additional_tokens

        projected_additional_cost = burn_rate.cost_per_hour * remaining_hours
        projected_total_cost = current_cost + projected_additional_cost

        return UsageProjection(
            projected_total_tokens=int(projected_total_tokens),
            projected_total_cost=projected_total_cost,
            remaining_minutes=int(remaining_minutes),
        )


def calculate_hourly_burn_rate(
    blocks: List[Dict[str, Any]], current_time: datetime
) -> float:
    """Calculate burn rate based on all sessions in the last hour."""
    if not blocks:
        return 0.0

    one_hour_ago = current_time - timedelta(hours=1)
    total_tokens = _calculate_total_tokens_in_hour(blocks, one_hour_ago, current_time)

    return total_tokens / 60.0 if total_tokens > 0 else 0.0


def _calculate_total_tokens_in_hour(
    blocks: List[Dict[str, Any]], one_hour_ago: datetime, current_time: datetime
) -> float:
    """Calculate total tokens for all blocks in the last hour."""
    total_tokens = 0.0
    for block in blocks:
        total_tokens += _process_block_for_burn_rate(block, one_hour_ago, current_time)
    return total_tokens


def _process_block_for_burn_rate(
    block: Dict[str, Any], one_hour_ago: datetime, current_time: datetime
) -> float:
    """Process a single block for burn rate calculation."""
    start_time = _parse_block_start_time(block)
    if not start_time or block.get("isGap", False):
        return 0

    session_actual_end = _determine_session_end_time(block, current_time)
    if session_actual_end < one_hour_ago:
        return 0

    return _calculate_tokens_in_hour(
        block, start_time, session_actual_end, one_hour_ago, current_time
    )


def _parse_block_start_time(block: Dict[str, Any]) -> Optional[datetime]:
    """Parse start time from block with error handling."""
    start_time_str = block.get("startTime")
    if not start_time_str:
        return None

    tz_handler = TimezoneHandler()
    try:
        start_time = tz_handler.parse_timestamp(start_time_str)
        return tz_handler.ensure_utc(start_time)
    except (ValueError, TypeError, AttributeError) as e:
        _log_timestamp_error(e, start_time_str, block.get("id"), "start_time")
        return None


def _determine_session_end_time(
    block: Dict[str, Any], current_time: datetime
) -> datetime:
    """Determine session end time based on block status."""
    if block.get("isActive", False):
        return current_time

    actual_end_str = block.get("actualEndTime")
    if actual_end_str:
        tz_handler = TimezoneHandler()
        try:
            session_actual_end = tz_handler.parse_timestamp(actual_end_str)
            return tz_handler.ensure_utc(session_actual_end)
        except (ValueError, TypeError, AttributeError) as e:
            _log_timestamp_error(e, actual_end_str, block.get("id"), "actual_end_time")
    return current_time


def _calculate_tokens_in_hour(
    block: Dict[str, Any],
    start_time: datetime,
    session_actual_end: datetime,
    one_hour_ago: datetime,
    current_time: datetime,
) -> float:
    """Calculate tokens used within the last hour for this session."""
    session_start_in_hour = max(start_time, one_hour_ago)
    session_end_in_hour = min(session_actual_end, current_time)

    if session_end_in_hour <= session_start_in_hour:
        return 0

    total_session_duration = (session_actual_end - start_time).total_seconds() / 60
    hour_duration = (session_end_in_hour - session_start_in_hour).total_seconds() / 60

    if total_session_duration > 0:
        session_tokens = block.get("totalTokens", 0)
        return session_tokens * (hour_duration / total_session_duration)
    return 0


def _log_timestamp_error(
    exception: Exception,
    timestamp_str: str,
    block_id: Optional[str],
    timestamp_type: str,
) -> None:
    """Log timestamp parsing errors with context."""
    logging.debug(f"Failed to parse {timestamp_type} '{timestamp_str}': {exception}")
    report_error(
        exception=exception,
        component="burn_rate_calculator",
        context_name="timestamp_error",
        context_data={f"{timestamp_type}_str": timestamp_str, "block_id": block_id},
    )
