"""Burn rate and cost calculations for Claude Monitor."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from claude_monitor.core.models import BurnRate, UsageProjection
from claude_monitor.core.p90_calculator import P90Calculator
from claude_monitor.error_handling import report_error
from claude_monitor.utils.time_utils import TimezoneHandler

logger = logging.getLogger(__name__)

_p90_calculator = P90Calculator()


class BurnRateCalculator:
    """Calculates burn rates and usage projections for session blocks."""

    def calculate_burn_rate(self, block: Any) -> Optional["BurnRate"]:
        """
        Calculates the current token consumption rate and cost per hour for an active session block.
        
        Returns:
            BurnRate: An object containing the tokens consumed per minute and the projected cost per hour, or None if the block is inactive, too short, or has zero tokens.
        """
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

    def project_block_usage(self, block: Any) -> Optional["UsageProjection"]:
        """
        Projects the total token usage and cost for a session block if the current burn rate continues until the block's scheduled end time.
        
        Returns:
            UsageProjection: An object containing the projected total tokens, projected total cost, and remaining minutes, or None if the burn rate cannot be determined or the block has already ended.
        """
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


def calculate_hourly_burn_rate(blocks: Any, current_time: datetime) -> float:
    """
    Calculates the average token burn rate per minute over the last hour across multiple session blocks.
    
    Parameters:
        blocks: A collection of session blocks to analyze.
        current_time (datetime): The reference time for calculating the last hour window.
    
    Returns:
        float: The average number of tokens consumed per minute in the last hour, or 0.0 if no tokens were used.
    """
    if not blocks:
        return 0.0

    one_hour_ago = current_time - timedelta(hours=1)
    total_tokens = _calculate_total_tokens_in_hour(blocks, one_hour_ago, current_time)

    return total_tokens / 60.0 if total_tokens > 0 else 0.0


def _calculate_total_tokens_in_hour(
    blocks: Any, one_hour_ago: datetime, current_time: datetime
) -> float:
    """
    Calculates the total number of tokens consumed across all session blocks within the last hour.
    
    Parameters:
        blocks: An iterable of session block objects to process.
        one_hour_ago (datetime): The start of the one-hour window.
        current_time (datetime): The current time used as the end of the window.
    
    Returns:
        float: The sum of tokens used in all blocks during the last hour.
    """
    total_tokens = 0.0
    for block in blocks:
        total_tokens += _process_block_for_burn_rate(block, one_hour_ago, current_time)
    return total_tokens


def _process_block_for_burn_rate(
    block: Any, one_hour_ago: datetime, current_time: datetime
) -> float:
    """
    Calculates the number of tokens used by a single session block within the last hour.
    
    Returns:
        The number of tokens attributed to the block during the last hour window. Returns 0 if the block is a gap, has an invalid start time, or ended before the last hour.
    """
    start_time = _parse_block_start_time(block)
    if not start_time or block.get("isGap", False):
        return 0

    session_actual_end = _determine_session_end_time(block, current_time)
    if session_actual_end < one_hour_ago:
        return 0

    return _calculate_tokens_in_hour(
        block, start_time, session_actual_end, one_hour_ago, current_time
    )


def _parse_block_start_time(block: Any) -> Optional[datetime]:
    """
    Parses the start time from a session block and converts it to UTC.
    
    Returns:
        A UTC datetime object representing the block's start time, or None if parsing fails or the start time is missing.
    """
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


def _determine_session_end_time(block: Any, current_time: datetime) -> datetime:
    """
    Determines the session end time for a block, returning the current time if the block is active or if the actual end time is missing or invalid.
    
    If the block is inactive and a valid actual end time is provided, returns the parsed UTC end time. Otherwise, defaults to the current time.
    """
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
    block: Any,
    start_time: datetime,
    session_actual_end: datetime,
    one_hour_ago: datetime,
    current_time: datetime,
) -> float:
    """
    Calculates the proportion of tokens from a session block that were used within the last hour.
    
    Parameters:
        block (Any): The session block containing token usage data.
        start_time (datetime): The UTC start time of the session.
        session_actual_end (datetime): The UTC end time of the session.
        one_hour_ago (datetime): The UTC timestamp representing one hour before the current time.
        current_time (datetime): The current UTC time.
    
    Returns:
        float: The estimated number of tokens used by the session within the last hour. Returns 0 if the session does not overlap with the last hour or has zero duration.
    """
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
    exception: Exception, timestamp_str: str, block_id: str, timestamp_type: str
) -> None:
    """
    Logs and reports errors encountered during timestamp parsing for a session block, including contextual information such as the timestamp string, block ID, and type of timestamp.
    """
    logging.debug(f"Failed to parse {timestamp_type} '{timestamp_str}': {exception}")
    report_error(
        exception=exception,
        component="burn_rate_calculator",
        context_name="timestamp_error",
        context_data={f"{timestamp_type}_str": timestamp_str, "block_id": block_id},
    )
