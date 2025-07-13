"""Progress bar components for Claude Monitor.

Provides token usage, time progress, and model usage progress bars.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from claude_monitor.utils.time_utils import percentage


class BaseProgressBar(ABC):
    """Abstract base class for progress bar components."""

    def __init__(self, width: int = 50):
        """
        Initialize the base progress bar with a specified width.
        
        Parameters:
            width (int): The width of the progress bar in characters. Must be between 10 and 200.
        """
        self.width = width
        self._validate_width()

    def _validate_width(self) -> None:
        """
        Ensures the progress bar width is within the allowed range of 10 to 200 characters.
        
        Raises:
            ValueError: If the width is less than 10 or greater than 200.
        """
        if self.width < 10:
            raise ValueError("Progress bar width must be at least 10 characters")
        if self.width > 200:
            raise ValueError("Progress bar width must not exceed 200 characters")

    def _calculate_filled_segments(
        self, percentage: float, max_value: float = 100.0
    ) -> int:
        """
        Calculate the number of filled segments in the progress bar based on a bounded percentage.
        
        Parameters:
            percentage (float): The current progress value as a percentage.
            max_value (float, optional): The maximum percentage value to consider. Defaults to 100.0.
        
        Returns:
            int: The number of filled segments corresponding to the bounded percentage.
        """
        bounded_percentage = max(0, min(percentage, max_value))
        return int(self.width * bounded_percentage / max_value)

    def _render_bar(
        self,
        filled: int,
        filled_char: str = "█",
        empty_char: str = "░",
        filled_style: Optional[str] = None,
        empty_style: Optional[str] = None,
    ) -> str:
        """
        Constructs a progress bar string with a specified number of filled and empty segments, optionally applying styles to each segment type.
        
        Parameters:
        	filled (int): Number of filled segments in the bar.
        	filled_char (str, optional): Character used for filled segments. Defaults to "█".
        	empty_char (str, optional): Character used for empty segments. Defaults to "░".
        	filled_style (str, optional): Style tag to apply to filled segments.
        	empty_style (str, optional): Style tag to apply to empty segments.
        
        Returns:
        	str: The formatted progress bar string with applied styles.
        """
        filled_bar = filled_char * filled
        empty_bar = empty_char * (self.width - filled)

        if filled_style:
            filled_bar = f"[{filled_style}]{filled_bar}[/]"
        if empty_style:
            empty_bar = f"[{empty_style}]{empty_bar}[/]"

        return f"{filled_bar}{empty_bar}"

    def _format_percentage(self, percentage: float, precision: int = 1) -> str:
        """
        Format a float percentage value as a string with a specified number of decimal places, followed by a percent sign.
        
        Parameters:
        	percentage (float): The percentage value to format.
        	precision (int): The number of decimal places to include.
        
        Returns:
        	str: The formatted percentage string.
        """
        return f"{percentage:.{precision}f}%"

    def _get_color_style_by_threshold(
        self, value: float, thresholds: List[Tuple[float, str]]
    ) -> str:
        """
        Return the style string corresponding to the first threshold that the value meets or exceeds.
        
        Parameters:
            value (float): The value to compare against thresholds.
            thresholds (List[Tuple[float, str]]): List of (threshold, style) pairs in descending order.
        
        Returns:
            str: The style string associated with the matched threshold, or the last style if none match.
        """
        for threshold, style in thresholds:
            if value >= threshold:
                return style
        return thresholds[-1][1] if thresholds else ""

    @abstractmethod
    def render(self, *args, **kwargs) -> str:
        """
        Render the progress bar as a formatted string.
        
        This abstract method must be implemented by subclasses to generate the specific progress bar display.
        """


class TokenProgressBar(BaseProgressBar):
    """Token usage progress bar component."""

    def render(self, percentage: float) -> str:
        """
        Render a token usage progress bar with color-coded segments and an icon indicating usage level.
        
        Parameters:
            percentage (float): The token usage percentage, which may exceed 100.
        
        Returns:
            str: A formatted string displaying the progress bar, usage icon, and percentage.
        """
        filled = self._calculate_filled_segments(min(percentage, 100.0))

        color_thresholds = [(90, "cost.high"), (50, "cost.medium"), (0, "cost.low")]

        filled_style = self._get_color_style_by_threshold(percentage, color_thresholds)
        bar = self._render_bar(
            filled,
            filled_style=filled_style,
            empty_style="table.border" if percentage < 90 else "cost.medium",
        )

        if percentage >= 90:
            icon = "🔴"
        elif percentage >= 50:
            icon = "🟡"
        else:
            icon = "🟢"

        percentage_str = self._format_percentage(percentage)
        return f"{icon} [{bar}] {percentage_str}"


class TimeProgressBar(BaseProgressBar):
    """Time progress bar component for session duration."""

    def render(self, elapsed_minutes: float, total_minutes: float) -> str:
        """
        Render a progress bar representing elapsed time relative to a total session duration.
        
        Parameters:
            elapsed_minutes (float): The number of minutes that have elapsed in the session.
            total_minutes (float): The total duration of the session in minutes.
        
        Returns:
            str: A formatted string displaying a clock icon, the progress bar, and the remaining time.
        """
        from claude_monitor.utils.time_utils import format_time

        if total_minutes <= 0:
            progress_percentage = 0
        else:
            progress_percentage = min(100, percentage(elapsed_minutes, total_minutes))

        filled = self._calculate_filled_segments(progress_percentage)
        bar = self._render_bar(
            filled, filled_style="progress.bar", empty_style="table.border"
        )

        remaining_time = format_time(max(0, total_minutes - elapsed_minutes))
        return f"⏰ [{bar}] {remaining_time}"


class ModelUsageBar(BaseProgressBar):
    """Model usage progress bar showing Sonnet vs Opus distribution."""

    def render(self, per_model_stats: Dict[str, Any]) -> str:
        """
        Render a progress bar visualizing the distribution of token usage across different models.
        
        Displays the proportion of tokens attributed to Sonnet and Opus models, with colored segments representing each. If no data or tokens are present, shows an empty bar with an appropriate message. Includes a summary of usage percentages and a debug string listing up to three model names.
        
        Parameters:
            per_model_stats (Dict[str, Any]): Dictionary mapping model names to their token usage statistics.
        
        Returns:
            str: Formatted string containing the model usage progress bar, summary percentages, and model names.
        """
        if not per_model_stats:
            empty_bar = self._render_bar(0, empty_style="table.border")
            return f"🤖 [{empty_bar}] No model data"

        model_names = list(per_model_stats.keys())
        if not model_names:
            empty_bar = self._render_bar(0, empty_style="table.border")
            return f"🤖 [{empty_bar}] Empty model stats"

        sonnet_tokens = 0
        opus_tokens = 0
        other_tokens = 0

        for model_name, stats in per_model_stats.items():
            model_tokens = stats.get("input_tokens", 0) + stats.get("output_tokens", 0)

            if "sonnet" in model_name.lower():
                sonnet_tokens += model_tokens
            elif "opus" in model_name.lower():
                opus_tokens += model_tokens
            else:
                other_tokens += model_tokens

        total_tokens = sonnet_tokens + opus_tokens + other_tokens

        if total_tokens == 0:
            empty_bar = self._render_bar(0, empty_style="table.border")
            return f"🤖 [{empty_bar}] No tokens used"

        sonnet_percentage = percentage(sonnet_tokens, total_tokens)
        opus_percentage = percentage(opus_tokens, total_tokens)
        other_percentage = percentage(other_tokens, total_tokens)

        sonnet_filled = int(self.width * sonnet_tokens / total_tokens)
        opus_filled = int(self.width * opus_tokens / total_tokens)

        total_filled = sonnet_filled + opus_filled
        if total_filled < self.width:
            if sonnet_tokens >= opus_tokens:
                sonnet_filled += self.width - total_filled
            else:
                opus_filled += self.width - total_filled
        elif total_filled > self.width:
            if sonnet_tokens >= opus_tokens:
                sonnet_filled -= total_filled - self.width
            else:
                opus_filled -= total_filled - self.width

        sonnet_bar = "█" * sonnet_filled
        opus_bar = "█" * opus_filled

        bar_segments = []
        if sonnet_filled > 0:
            bar_segments.append(f"[info]{sonnet_bar}[/]")
        if opus_filled > 0:
            bar_segments.append(f"[warning]{opus_bar}[/]")

        bar_display = "".join(bar_segments)

        if opus_tokens > 0 and sonnet_tokens > 0:
            summary = f"Sonnet {sonnet_percentage:.1f}% | Opus {opus_percentage:.1f}%"
        elif sonnet_tokens > 0:
            summary = f"Sonnet {sonnet_percentage:.1f}%"
        elif opus_tokens > 0:
            summary = f"Opus {opus_percentage:.1f}%"
        else:
            summary = f"Other {other_percentage:.1f}%"

        if len(model_names) > 0:
            model_list = ", ".join(model_names[:3])
            if len(model_names) > 3:
                model_list += f" +{len(model_names) - 3} more"
            debug_info = f" ({model_list})"
        else:
            debug_info = ""

        return f"🤖 [{bar_display}] {summary}{debug_info}"
