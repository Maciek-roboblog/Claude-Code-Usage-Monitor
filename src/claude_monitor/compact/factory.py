"""Factory pattern for creating compact display components.

Provides a centralized way to create and configure compact display components
with consistent default settings and dependency injection.
"""

from typing import Optional

from claude_monitor.compact.color_manager import CompactColorManager
from claude_monitor.compact.field_selector import CompactFieldSelector
from claude_monitor.compact.formatter import EnhancedCompactFormatter
from claude_monitor.compact.refresh_manager import CompactRefreshManager
from claude_monitor.core.models import CompactColorThresholds


class CompactComponentFactory:
    """Factory for creating compact display components with consistent configuration."""

    @staticmethod
    def create_field_selector(
        selected_fields: Optional[list[str]] = None,
    ) -> CompactFieldSelector:
        """Create a field selector with optional custom fields.

        Args:
            selected_fields: Custom field selection, uses defaults if None

        Returns:
            Configured CompactFieldSelector instance
        """
        return CompactFieldSelector(selected_fields)

    @staticmethod
    def create_color_manager(
        thresholds: Optional[CompactColorThresholds] = None, no_color: bool = False
    ) -> CompactColorManager:
        """Create a color manager with thresholds and color settings.

        Args:
            thresholds: Color threshold configuration, uses defaults if None
            no_color: Whether to disable all coloring

        Returns:
            Configured CompactColorManager instance
        """
        if thresholds is None:
            thresholds = CompactColorThresholds()
        return CompactColorManager(thresholds, no_color)

    @staticmethod
    def create_refresh_manager(refresh_rate: float = 2.0) -> CompactRefreshManager:
        """Create a refresh manager with specified refresh rate.

        Args:
            refresh_rate: Refresh interval in seconds

        Returns:
            Configured CompactRefreshManager instance
        """
        return CompactRefreshManager(refresh_rate)

    @staticmethod
    def create_formatter(
        field_selector: Optional[CompactFieldSelector] = None,
        color_manager: Optional[CompactColorManager] = None,
    ) -> EnhancedCompactFormatter:
        """Create an enhanced formatter with optional custom components.

        Args:
            field_selector: Custom field selector, creates default if None
            color_manager: Custom color manager, creates default if None

        Returns:
            Configured EnhancedCompactFormatter instance
        """
        if field_selector is None:
            field_selector = CompactComponentFactory.create_field_selector()
        if color_manager is None:
            color_manager = CompactComponentFactory.create_color_manager()

        return EnhancedCompactFormatter(field_selector, color_manager)

    @classmethod
    def create_complete_setup(
        cls,
        selected_fields: Optional[list[str]] = None,
        color_thresholds: Optional[CompactColorThresholds] = None,
        no_color: bool = False,
        refresh_rate: float = 10.0,
    ) -> dict[str, object]:
        """Create a complete compact display setup with all components.

        Args:
            selected_fields: Custom field selection
            color_thresholds: Color threshold configuration
            no_color: Whether to disable coloring
            refresh_rate: Refresh interval in seconds

        Returns:
            Dictionary containing all configured components
        """
        field_selector = cls.create_field_selector(selected_fields)
        color_manager = cls.create_color_manager(color_thresholds, no_color)
        refresh_manager = cls.create_refresh_manager(refresh_rate)
        formatter = cls.create_formatter(field_selector, color_manager)

        return {
            "field_selector": field_selector,
            "color_manager": color_manager,
            "refresh_manager": refresh_manager,
            "formatter": formatter,
        }
