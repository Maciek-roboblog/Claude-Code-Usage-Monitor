"""Theme system for Claude Code Usage Monitor.

This module provides automatic theme detection and Rich-based theming
for optimal terminal display across light and dark terminals.
"""

from .console import get_themed_console, print_themed
from .detector import ThemeDetector
from .themes import ThemeType, get_theme

__all__ = [
    "ThemeDetector",
    "get_theme",
    "ThemeType",
    "get_themed_console",
    "print_themed",
]
