"""
Compact display mode module for Claude Monitor.

This module provides enhanced compact display functionality with:
- Customizable field selection
- Contextual coloring
- Performance-optimized refresh management
- Advanced formatting options
"""

from .color_manager import CompactColorManager
from .factory import CompactComponentFactory
from .field_selector import CompactFieldSelector
from .formatter import EnhancedCompactFormatter
from .refresh_manager import CompactRefreshManager

__all__ = [
    "CompactColorManager",
    "CompactComponentFactory",
    "CompactFieldSelector",
    "EnhancedCompactFormatter",
    "CompactRefreshManager",
]
