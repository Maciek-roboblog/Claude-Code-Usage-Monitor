"""Timezone utilities for Claude Monitor.

This module provides timezone handling functionality, re-exporting from time_utils
for backward compatibility.
"""

import logging
from datetime import datetime
from typing import Any, Optional

from claude_monitor.utils.time_utils import (
    TimezoneHandler,
    create_timezone_aware_datetime,
    get_time_format_preference,
)

logger = logging.getLogger(__name__)


def _detect_timezone_time_preference(args: Optional[Any] = None) -> bool:
    """Detect timezone and time preference.

    This is a backward compatibility function that delegates to the new
    time format detection system.

    Args:
        args: Arguments object or None

    Returns:
        True for 12-hour format, False for 24-hour format
    """
    return get_time_format_preference(args)


def parse_timestamp(timestamp_str: str, default_tz: str = "UTC") -> Optional[datetime]:
    """Parse timestamp string with timezone handling.

    Args:
        timestamp_str: Timestamp string to parse
        default_tz: Default timezone if not specified in timestamp

    Returns:
        Parsed datetime object or None if parsing fails
    """
    handler = TimezoneHandler(default_tz)
    return handler.parse_timestamp(timestamp_str)


def ensure_utc(dt: datetime, default_tz: str = "UTC") -> datetime:
    """Convert datetime to UTC.

    Args:
        dt: Datetime object to convert
        default_tz: Default timezone for naive datetime objects

    Returns:
        UTC datetime object
    """
    handler = TimezoneHandler(default_tz)
    return handler.ensure_utc(dt)


def validate_timezone(tz_name: str) -> bool:
    """Check if timezone name is valid.

    Args:
        tz_name: Timezone name to validate

    Returns:
        True if valid, False otherwise
    """
    handler = TimezoneHandler()
    return handler.validate_timezone(tz_name)


def convert_to_timezone(
    dt: datetime, tz_name: str, default_tz: str = "UTC"
) -> datetime:
    """Convert datetime to specific timezone.

    Args:
        dt: Datetime object to convert
        tz_name: Target timezone name
        default_tz: Default timezone for naive datetime objects

    Returns:
        Converted datetime object
    """
    handler = TimezoneHandler(default_tz)
    return handler.convert_to_timezone(dt, tz_name)


def safe_create_datetime(
    year: int,
    month: int,
    day: int,
    hour: int = 0,
    minute: int = 0,
    second: int = 0,
    microsecond: int = 0,
    tz_name: str = "UTC",
) -> datetime:
    """Create timezone-aware datetime with DST handling.

    This is a convenience wrapper around create_timezone_aware_datetime
    that provides safe timezone-aware datetime creation.

    Args:
        year, month, day, hour, minute, second, microsecond: Datetime components
        tz_name: Timezone name (defaults to UTC)

    Returns:
        Safely created timezone-aware datetime
    """
    return create_timezone_aware_datetime(
        year, month, day, hour, minute, second, microsecond, tz_name, handle_dst=True
    )


def get_dst_status(dt: datetime, tz_name: str = "UTC") -> bool:
    """Check if datetime is during daylight saving time.

    Args:
        dt: Datetime to check
        tz_name: Timezone name

    Returns:
        True if during DST, False otherwise
    """
    handler = TimezoneHandler(tz_name)
    return handler.is_dst(dt, tz_name)


def handle_timezone_edge_cases(dt: datetime, tz_name: str = "UTC") -> datetime:
    """Handle timezone edge cases like DST transitions.

    Args:
        dt: Datetime that may have timezone edge cases
        tz_name: Target timezone name

    Returns:
        Datetime with edge cases resolved
    """
    handler = TimezoneHandler(tz_name)
    if dt.tzinfo is None:
        return handler.safe_localize(dt, tz_name)
    else:
        return handler.convert_to_timezone(dt, tz_name)
