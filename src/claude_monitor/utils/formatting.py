"""Formatting utilities for Claude Monitor.

This module provides formatting functions for currency, time, and display output.
"""

import logging
from datetime import datetime
from typing import Any, Optional

from claude_monitor.utils.time_utils import format_display_time as _format_display_time
from claude_monitor.utils.time_utils import get_time_format_preference

logger = logging.getLogger(__name__)


def format_currency(amount: float, currency: str = "USD") -> str:
    """Format currency amount with appropriate symbol and formatting.

    Args:
        amount: The amount to format
        currency: Currency code (default: USD)

    Returns:
        Formatted currency string
    """
    amount: float = round(amount, 2)

    if currency == "USD":
        if amount >= 0:
            return f"${amount:,.2f}"
        return f"$-{abs(amount):,.2f}"
    return f"{amount:,.2f} {currency}"


def format_time(minutes: float) -> str:
    """Format minutes into human-readable time (e.g., '3h 45m').

    This is a re-export from time_utils for backward compatibility.

    Args:
        minutes: Duration in minutes

    Returns:
        Formatted time string
    """
    from claude_monitor.utils.time_utils import format_time as _format_time

    return _format_time(minutes)


def format_display_time(
    dt_obj: datetime,
    use_12h_format: Optional[bool] = None,
    include_seconds: bool = True,
) -> str:
    """Format datetime for display with 12h/24h support.

    This is a re-export from time_utils for backward compatibility.

    Args:
        dt_obj: Datetime object to format
        use_12h_format: Whether to use 12-hour format (None for auto-detect)
        include_seconds: Whether to include seconds in output

    Returns:
        Formatted time string
    """
    return _format_display_time(dt_obj, use_12h_format, include_seconds)


def _get_pref(args: Any) -> bool:
    """Internal helper function for getting time format preference.

    Args:
        args: Arguments object or None

    Returns:
        True for 12-hour format, False for 24-hour format
    """
    return get_time_format_preference(args)
