"""UI layout managers for Claude Monitor.

This module consolidates layout management functionality including:
- Header formatting and styling
- Screen layout and organization
"""

from typing import List


class HeaderManager:
    """Manager for header layout and formatting."""

    def __init__(self):
        """
        Initialize the HeaderManager with default separator character and length for header formatting.
        """
        self.separator_char = "="
        self.separator_length = 60

    def create_header(
        self, plan: str = "pro", timezone: str = "Europe/Warsaw"
    ) -> List[str]:
        """
        Generate a stylized header for the Claude Monitor UI.
        
        Parameters:
        	plan (str): The subscription plan name to display.
        	timezone (str): The timezone to display.
        
        Returns:
        	List[str]: A list of formatted strings representing the header lines.
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
        """
        Initialize the screen manager with default dimensions and zero margins.
        """
        self.screen_width = 80
        self.screen_height = 24
        self.margin_left = 0
        self.margin_right = 0
        self.margin_top = 0
        self.margin_bottom = 0

    def set_screen_dimensions(self, width: int, height: int) -> None:
        """
        Set the screen width and height for layout calculations.
        
        Parameters:
            width (int): The width of the screen in characters.
            height (int): The height of the screen in lines.
        """
        self.screen_width = width
        self.screen_height = height

    def set_margins(
        self, left: int = 0, right: int = 0, top: int = 0, bottom: int = 0
    ) -> None:
        """
        Set the margins for all sides of the screen layout.
        
        Parameters:
            left (int): Number of characters for the left margin.
            right (int): Number of characters for the right margin.
            top (int): Number of lines for the top margin.
            bottom (int): Number of lines for the bottom margin.
        """
        self.margin_left = left
        self.margin_right = right
        self.margin_top = top
        self.margin_bottom = bottom

    def create_full_screen_layout(self, content_sections: List[List[str]]) -> List[str]:
        """
        Combine multiple content sections into a single screen layout, applying top, bottom, and left margins.
        
        Parameters:
            content_sections (List[List[str]]): Content sections to be arranged, each as a list of lines.
        
        Returns:
            List[str]: The combined screen layout as a list of lines with margins applied.
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
