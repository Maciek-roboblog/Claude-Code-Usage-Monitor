"""UI layout managers for Claude Monitor.

This module consolidates layout management functionality including:
- Header formatting and styling
- Screen layout and organization
"""

from typing import List


class HeaderManager:
    """Manager for header layout and formatting."""

    def __init__(self):
        """Initialize header manager."""
        self.separator_char = "="
        self.separator_length = 60

    def create_header(
        self, plan: str = "pro", timezone: str = "Europe/Warsaw"
    ) -> List[str]:
        """Create stylized header with sparkles.

        Args:
            plan: Current plan name
            timezone: Display timezone

        Returns:
            List of formatted header lines
        """
        sparkles = "✦ ✧ ✦ ✧"
        title = "CLAUDE CODE USAGE MONITOR"
        separator = self.separator_char * self.separator_length

        return [
            f"[header]{sparkles}[/] [header]{title}[/] [header]{sparkles}[/]",
            f"[table.border]{separator}[/]",
            f"[ {plan.lower()} | {timezone.lower()} ]",
            "",
        ]


class ScreenManager:
    """Manager for overall screen layout and organization."""

    def __init__(self):
        """Initialize screen manager."""
        self.screen_width = 80
        self.screen_height = 24
        self.margin_left = 0
        self.margin_right = 0
        self.margin_top = 0
        self.margin_bottom = 0

    def set_screen_dimensions(self, width: int, height: int) -> None:
        """Set screen dimensions for layout calculations.

        Args:
            width: Screen width in characters
            height: Screen height in lines
        """
        self.screen_width = width
        self.screen_height = height

    def set_margins(
        self, left: int = 0, right: int = 0, top: int = 0, bottom: int = 0
    ) -> None:
        """Set screen margins.

        Args:
            left: Left margin in characters
            right: Right margin in characters
            top: Top margin in lines
            bottom: Bottom margin in lines
        """
        self.margin_left = left
        self.margin_right = right
        self.margin_top = top
        self.margin_bottom = bottom

    def create_full_screen_layout(self, content_sections: List[List[str]]) -> List[str]:
        """Create full screen layout with multiple content sections.

        Args:
            content_sections: List of content sections, each being a list of lines

        Returns:
            Combined screen layout as list of lines
        """
        screen_buffer = []

        screen_buffer.extend([""] * self.margin_top)

        for i, section in enumerate(content_sections):
            if i > 0:
                screen_buffer.append("")

            for line in section:
                padded_line = " " * self.margin_left + line
                screen_buffer.append(padded_line)

        screen_buffer.extend([""] * self.margin_bottom)

        return screen_buffer


__all__ = ["HeaderManager", "ScreenManager"]
