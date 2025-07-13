"""Formatting utilities for Claude Monitor.

This module provides formatting functions for currency, time, and display output.
"""

import logging
from datetime import datetime
from typing import Optional

from claude_monitor.utils.time_utils import format_display_time as _format_display_time
from claude_monitor.utils.time_utils import get_time_format_preference

logger = logging.getLogger(__name__)


def format_currency(amount: float, currency: str = "USD") -> str:
    """
    Format a numeric amount as a currency string, using appropriate symbols and conventions.
    
    For USD, prepends a dollar sign and places the minus sign before the dollar sign for negative values. For other currencies, appends the currency code after the formatted amount.
    
    Parameters:
        amount (float): The numeric amount to format.
        currency (str, optional): The currency code (default is "USD").
    
    Returns:
        str: The formatted currency string.
    """
    amount = round(amount, 2)

    if currency == "USD":
        if amount >= 0:
            return f"${amount:,.2f}"
        else:
            return f"$-{abs(amount):,.2f}"
    else:
        return f"{amount:,.2f} {currency}"


def format_time(minutes: float) -> str:
    """
    Convert a duration in minutes to a human-readable string (e.g., "3h 45m").
    
    Parameters:
        minutes (float): Duration in minutes to format.
    
    Returns:
        str: Formatted time string.
    """
    from claude_monitor.utils.time_utils import format_time as _format_time

    return _format_time(minutes)


def format_display_time(
    dt_obj: datetime,
    use_12h_format: Optional[bool] = None,
    include_seconds: bool = True,
) -> str:
    """
    Format a datetime object as a display string with optional 12-hour or 24-hour format and optional seconds.
    
    Parameters:
    	dt_obj (datetime): The datetime object to format.
    	use_12h_format (Optional[bool]): If True, use 12-hour format; if False, use 24-hour format; if None, auto-detects preference.
    	include_seconds (bool): If True, includes seconds in the output.
    
    Returns:
    	str: The formatted time string.
    """
    return _format_display_time(dt_obj, use_12h_format, include_seconds)


def _get_pref(args) -> bool:
    """
    Return the user's preferred time format as a boolean.
    
    Returns:
        True if the user prefers 12-hour time format, False for 24-hour format.
    """
    return get_time_format_preference(args)
