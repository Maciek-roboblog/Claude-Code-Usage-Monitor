"""Timezone utilities for Claude Monitor.

This module provides timezone handling functionality, re-exporting from time_utils
for backward compatibility.
"""

import logging
from datetime import datetime
from typing import Optional

from claude_monitor.utils.time_utils import TimezoneHandler, get_time_format_preference

logger = logging.getLogger(__name__)


def _detect_timezone_time_preference(args=None) -> bool:
    """
    Determine whether the preferred time format is 12-hour or 24-hour based on the provided arguments.
    
    Parameters:
        args: Optional arguments object used to infer the user's time format preference.
    
    Returns:
        bool: True if 12-hour format is preferred, False if 24-hour format is preferred.
    """
    return get_time_format_preference(args)


def parse_timestamp(timestamp_str: str, default_tz: str = "UTC") -> Optional[datetime]:
    """
    Parses a timestamp string into a timezone-aware datetime object.
    
    If the timestamp string does not include timezone information, the specified default timezone is assumed. Returns `None` if parsing fails.
    
    Parameters:
        timestamp_str (str): The timestamp string to parse.
        default_tz (str): The timezone to assume if the timestamp is naive. Defaults to "UTC".
    
    Returns:
        Optional[datetime]: The parsed datetime object with timezone information, or `None` if parsing fails.
    """
    handler = TimezoneHandler(default_tz)
    return handler.parse_timestamp(timestamp_str)


def ensure_utc(dt: datetime, default_tz: str = "UTC") -> datetime:
    """
    Converts a datetime object to UTC, assuming a default timezone if the input is naive.
    
    Parameters:
    	dt (datetime): The datetime object to convert.
    	default_tz (str): Timezone to assume if `dt` is naive. Defaults to "UTC".
    
    Returns:
    	datetime: The converted UTC datetime object.
    """
    handler = TimezoneHandler(default_tz)
    return handler.ensure_utc(dt)


def validate_timezone(tz_name: str) -> bool:
    """
    Validate whether the given timezone name is recognized.
    
    Parameters:
    	tz_name (str): The name of the timezone to validate.
    
    Returns:
    	bool: True if the timezone name is valid, False otherwise.
    """
    handler = TimezoneHandler()
    return handler.validate_timezone(tz_name)


def convert_to_timezone(
    dt: datetime, tz_name: str, default_tz: str = "UTC"
) -> datetime:
    """
    Convert a datetime object to the specified timezone.
    
    If the input datetime is naive, it is first localized to the default timezone before conversion.
    
    Parameters:
        dt (datetime): The datetime object to convert.
        tz_name (str): The target timezone name.
        default_tz (str): The timezone to assume for naive datetime objects.
    
    Returns:
        datetime: The converted datetime object in the specified timezone.
    """
    handler = TimezoneHandler(default_tz)
    return handler.convert_to_timezone(dt, tz_name)
