"""
Utility functions for dynamic text alignment in multilingual interfaces.

This module provides tools to create properly aligned text displays
that work across different languages with varying text lengths.
"""

import re
from typing import Dict, List, Tuple

from ..i18n import _


def calculate_max_label_width(labels: List[str]) -> int:
    """
    Calculate the maximum width needed for a list of translated labels.

    Args:
        labels: List of message keys to translate and measure

    Returns:
        Maximum width in characters needed for alignment
    """
    max_width = 0
    for label_key in labels:
        translated = _(label_key)
        # Remove Rich markup for accurate length calculation
        clean_text = _strip_rich_markup(translated)
        max_width = max(max_width, len(clean_text))

    return max_width


def create_aligned_line(
    label_key: str, value: str, target_width: int, emoji: str = "", separator: str = ":"
) -> str:
    """
    Create a properly aligned line with translated label and value.

    Args:
        label_key: Message key for the label to translate
        value: The value to display after alignment
        target_width: Target width for alignment (from calculate_max_label_width)
        emoji: Optional emoji prefix
        separator: Separator between label and value (default ":")

    Returns:
        Formatted string with proper alignment

    Example:
        >>> create_aligned_line("status.token_usage", "50%", 15, "📊")
        "📊 Token Usage:    50%"
        >>> # In French: "📊 Utilisation:    50%"
    """
    translated_label = _(label_key)
    clean_label = _strip_rich_markup(translated_label)

    # Calculate padding needed
    padding_needed = target_width - len(clean_label)
    padding = " " * max(0, padding_needed)

    # Build the line
    parts = []
    if emoji:
        parts.append(emoji)

    parts.append(f"[value]{translated_label}{separator}[/]")
    parts.append(padding)
    parts.append(value)

    return " ".join(parts)


def _strip_rich_markup(text: str) -> str:
    """
    Remove Rich markup tags from text for accurate length calculation.

    Args:
        text: Text potentially containing Rich markup

    Returns:
        Clean text without markup
    """

    # Remove Rich markup tags like [value], [/], [warning], etc.
    clean = re.sub(r"\[/?[a-zA-Z0-9_.]+\]", "", text)
    return clean


class AlignedFormatter:
    """
    A formatter class for creating consistently aligned multilingual displays.

    This class pre-calculates alignment widths and provides methods for
    creating aligned output lines.
    """

    def __init__(self, label_keys: List[str]):
        """
        Initialize the formatter with a list of label keys.

        Args:
            label_keys: List of message keys that will be used for labels
        """
        self.label_keys = label_keys
        self.target_width = calculate_max_label_width(label_keys)

    def format_line(
        self, label_key: str, value: str, emoji: str = "", separator: str = ":"
    ) -> str:
        """
        Format a line with proper alignment.

        Args:
            label_key: Message key for the label
            value: Value to display
            emoji: Optional emoji prefix
            separator: Separator between label and value

        Returns:
            Formatted and aligned line
        """
        return create_aligned_line(
            label_key, value, self.target_width, emoji, separator
        )

    def get_alignment_info(self) -> Dict[str, Tuple[str, int]]:
        """
        Get alignment information for debugging.

        Returns:
            Dict mapping label keys to (translated_text, length) tuples
        """
        info = {}
        for key in self.label_keys:
            translated = _(key)
            clean = _strip_rich_markup(translated)
            info[key] = (translated, len(clean))
        return info


# Pre-defined formatters for common use cases
STATUS_LABELS = [
    "status.token_usage",
    "status.time_to_reset",
    "status.tokens",
    "status.burn_rate",
    "status.predicted_end",
    "status.token_reset",
]


def get_status_formatter() -> AlignedFormatter:
    """Get a formatter pre-configured for status display lines."""
    return AlignedFormatter(STATUS_LABELS)
