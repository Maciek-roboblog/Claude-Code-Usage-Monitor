"""Timezone utilities for Claude Monitor.

This module provides timezone handling functionality, re-exporting from time_utils
for backward compatibility.
"""

import logging
from datetime import datetime
from typing import Any, Optional

from claude_monitor.utils.time_utils import TimezoneHandler, get_time_format_preference

logger: logging.Logger = logging.getLogger(__name__)


def _detect_timezone_time_preference(args: Any = None) -> bool:
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
    handler: TimezoneHandler = TimezoneHandler(default_tz)
    return handler.parse_timestamp(timestamp_str)


def ensure_utc(dt: datetime, default_tz: str = "UTC") -> datetime:
    """Convert datetime to UTC.

    Args:
        dt: Datetime object to convert
        default_tz: Default timezone for naive datetime objects

    Returns:
        UTC datetime object
    """
    handler: TimezoneHandler = TimezoneHandler(default_tz)
    return handler.ensure_utc(dt)


def validate_timezone(tz_name: str) -> bool:
    """Check if timezone name is valid.

    Args:
        tz_name: Timezone name to validate

    Returns:
        True if valid, False otherwise
    """
    handler: TimezoneHandler = TimezoneHandler()
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
    handler: TimezoneHandler = TimezoneHandler(default_tz)
    return handler.convert_to_timezone(dt, tz_name)
