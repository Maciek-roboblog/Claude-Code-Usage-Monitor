"""Progress bar components for Claude Monitor.

Provides token usage, time progress, and model usage progress bars with Rich integration.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol, Tuple, TypedDict, Union

from rich.console import RenderableType
from rich.text import Text

from claude_monitor.terminal.themes import (
    RichStyleDefinition,
    ThemeStyleName,
)
from claude_monitor.utils.time_utils import percentage

# Advanced typing definitions for progress bar components
ProgressPercentage = float
ProgressSegments = int
ProgressWidth = int
ProgressValue = Union[int, float]


class ProgressBarThreshold(TypedDict):
    """Typed dictionary for progress bar color thresholds."""

    threshold: float
    style: ThemeStyleName


class ModelStatistics(TypedDict, total=False):
    """Typed dictionary for model usage statistics."""

    input_tokens: int
    output_tokens: int
    requests: int
    cost: float


class ProgressBarConfig(TypedDict, total=False):
    """Configuration for progress bar rendering."""

    width: ProgressWidth
    filled_char: str
    empty_char: str
    show_percentage: bool
    show_icon: bool
    precision: int


class ProgressBarRenderer(Protocol):
    """Protocol for progress bar rendering engines."""

    def render_segments(
        self,
        filled: ProgressSegments,
        total: ProgressSegments,
        style: Optional[RichStyleDefinition] = None,
    ) -> RenderableType:
        """Render progress bar segments."""
        ...

    def format_display(
        self,
        bar: RenderableType,
        percentage: ProgressPercentage,
        label: str = "",
    ) -> str:
        """Format complete progress bar display."""
        ...


class BaseProgressBar(ABC):
    """Abstract base class for progress bar components with Rich integration."""

    def __init__(self, width: ProgressWidth = 50) -> None:
        """Initialize base progress bar.

        Args:
            width: Width of the progress bar in characters
        """
        self.width: ProgressWidth = width
        self._validate_width()

        # Progress bar rendering configuration
        self._config: ProgressBarConfig = {
            "width": width,
            "filled_char": "█",
            "empty_char": "░",
            "show_percentage": True,
            "show_icon": True,
            "precision": 1,
        }

    def _validate_width(self) -> None:
        """Validate width parameter."""
        if self.width < 10:
            raise ValueError("Progress bar width must be at least 10 characters")
        if self.width > 200:
            raise ValueError("Progress bar width must not exceed 200 characters")

    def _calculate_filled_segments(
        self, percentage: ProgressPercentage, max_value: ProgressPercentage = 100.0
    ) -> ProgressSegments:
        """Calculate number of filled segments based on percentage.

        Args:
            percentage: Current percentage value
            max_value: Maximum percentage value (default 100)

        Returns:
            Number of filled segments
        """
        bounded_percentage: ProgressPercentage = max(0, min(percentage, max_value))
        return int(self.width * bounded_percentage / max_value)

    def _render_bar(
        self,
        filled: ProgressSegments,
        filled_char: str = "█",
        empty_char: str = "░",
        filled_style: Optional[Union[ThemeStyleName, RichStyleDefinition]] = None,
        empty_style: Optional[Union[ThemeStyleName, RichStyleDefinition]] = None,
    ) -> str:
        """Render the actual progress bar with Rich styling.

        Args:
            filled: Number of filled segments
            filled_char: Character for filled segments
            empty_char: Character for empty segments
            filled_style: Optional Rich style for filled segments
            empty_style: Optional Rich style for empty segments

        Returns:
            Formatted bar string with Rich markup
        """
        filled_bar: str = filled_char * filled
        empty_bar: str = empty_char * (self.width - filled)

        if filled_style:
            filled_bar = f"[{filled_style}]{filled_bar}[/]"
        if empty_style:
            empty_bar = f"[{empty_style}]{empty_bar}[/]"

        return f"{filled_bar}{empty_bar}"

    def _format_percentage(
        self, percentage: ProgressPercentage, precision: int = 1
    ) -> str:
        """Format percentage value for display.

        Args:
            percentage: Percentage value to format
            precision: Number of decimal places

        Returns:
            Formatted percentage string with proper precision
        """
        return f"{percentage:.{precision}f}%"

    def _get_color_style_by_threshold(
        self,
        value: ProgressValue,
        thresholds: List[Tuple[ProgressValue, ThemeStyleName]],
    ) -> ThemeStyleName:
        """Get color style based on value thresholds.

        Args:
            value: Current value to check
            thresholds: List of (threshold, style) tuples in descending order

        Returns:
            Theme style name for the current value
        """
        for threshold, style in thresholds:
            if value >= threshold:
                return style
        return thresholds[-1][1] if thresholds else "dim"

    def _create_rich_text(
        self,
        content: str,
        style: Optional[Union[ThemeStyleName, RichStyleDefinition]] = None,
    ) -> Text:
        """Create Rich Text object with optional styling.

        Args:
            content: Text content
            style: Optional Rich style

        Returns:
            Styled Rich Text object
        """
        return Text(content, style=style) if style else Text(content)

    def _get_status_icon(self, percentage: ProgressPercentage) -> str:
        """Get status icon based on percentage thresholds.

        Args:
            percentage: Current percentage value

        Returns:
            Status icon string
        """
        if percentage >= 90:
            return "🔴"
        elif percentage >= 50:
            return "🟡"
        else:
            return "🟢"

    @abstractmethod
    def render(self, *args: Any, **kwargs: Any) -> str:
        """Render the progress bar.

        This method must be implemented by subclasses to provide
        specific rendering logic for different progress bar types.

        Returns:
            Formatted progress bar string with Rich markup
        """


class TokenProgressBar(BaseProgressBar):
    """Token usage progress bar component with advanced cost visualization."""

    def __init__(self, width: ProgressWidth = 50) -> None:
        """Initialize token progress bar.

        Args:
            width: Width of the progress bar in characters
        """
        super().__init__(width)

        # Token-specific thresholds for cost visualization
        self._cost_thresholds: List[Tuple[ProgressPercentage, ThemeStyleName]] = [
            (90.0, "cost.high"),
            (50.0, "cost.medium"),
            (0.0, "cost.low"),
        ]

    def render(self, percentage: ProgressPercentage) -> str:
        """Render token usage progress bar with cost visualization.

        Args:
            percentage: Usage percentage (can exceed 100 for overages)

        Returns:
            Formatted progress bar string with Rich markup
        """
        # Calculate filled segments, capped at 100% for visual display
        filled: ProgressSegments = self._calculate_filled_segments(
            min(percentage, 100.0)
        )

        # Determine style based on usage thresholds
        filled_style: ThemeStyleName = self._get_color_style_by_threshold(
            percentage, self._cost_thresholds
        )

        # Select empty style based on urgency
        empty_style: ThemeStyleName = (
            "cost.medium" if percentage >= 90 else "table.border"
        )

        # Render the progress bar with appropriate styling
        bar: str = self._render_bar(
            filled,
            filled_style=filled_style,
            empty_style=empty_style,
        )

        # Get status icon based on usage level
        icon: str = self._get_status_icon(percentage)

        # Format percentage with configured precision
        percentage_str: str = self._format_percentage(
            percentage, self._config["precision"]
        )

        return f"{icon} [{bar}] {percentage_str}"


class TimeProgressBar(BaseProgressBar):
    """Time progress bar component for session duration visualization."""

    def __init__(self, width: ProgressWidth = 50) -> None:
        """Initialize time progress bar.

        Args:
            width: Width of the progress bar in characters
        """
        super().__init__(width)

        # Time-specific styling configuration
        self._time_styles: Dict[str, ThemeStyleName] = {
            "filled": "progress.bar.fill",
            "empty": "table.border",
            "icon": "time.elapsed",
        }

    def render(
        self, elapsed_minutes: ProgressValue, total_minutes: ProgressValue
    ) -> str:
        """Render time progress bar with remaining time display.

        Args:
            elapsed_minutes: Minutes elapsed in current session
            total_minutes: Total session duration in minutes

        Returns:
            Formatted time progress bar string with remaining time
        """
        from claude_monitor.utils.time_utils import format_time

        # Calculate progress percentage with bounds checking
        if total_minutes <= 0:
            progress_percentage: ProgressPercentage = 0.0
        else:
            progress_percentage = min(100.0, percentage(elapsed_minutes, total_minutes))

        # Calculate filled segments for visual representation
        filled: ProgressSegments = self._calculate_filled_segments(progress_percentage)

        # Render bar with time-specific styling
        bar: str = self._render_bar(
            filled,
            filled_style=self._time_styles["filled"],
            empty_style=self._time_styles["empty"],
        )

        # Calculate and format remaining time
        remaining_minutes: ProgressValue = max(0, total_minutes - elapsed_minutes)
        remaining_time: str = format_time(remaining_minutes)

        return f"⏰ [{bar}] {remaining_time}"


class ModelUsageBar(BaseProgressBar):
    """Model usage progress bar showing advanced model distribution visualization."""

    def __init__(self, width: ProgressWidth = 50) -> None:
        """Initialize model usage bar.

        Args:
            width: Width of the progress bar in characters
        """
        super().__init__(width)

        # Model-specific styling configuration
        self._model_styles: Dict[str, ThemeStyleName] = {
            "sonnet": "model.sonnet",
            "opus": "model.opus",
            "haiku": "model.haiku",
            "unknown": "model.unknown",
            "empty": "table.border",
        }

    def _aggregate_model_tokens(
        self, per_model_stats: Dict[str, ModelStatistics]
    ) -> Tuple[int, int, int]:
        """Aggregate token usage by model family.

        Args:
            per_model_stats: Dictionary of model statistics

        Returns:
            Tuple of (sonnet_tokens, opus_tokens, other_tokens)
        """
        sonnet_tokens: int = 0
        opus_tokens: int = 0
        other_tokens: int = 0

        for model_name, stats in per_model_stats.items():
            model_tokens: int = stats.get("input_tokens", 0) + stats.get(
                "output_tokens", 0
            )

            model_name_lower: str = model_name.lower()
            if "sonnet" in model_name_lower:
                sonnet_tokens += model_tokens
            elif "opus" in model_name_lower:
                opus_tokens += model_tokens
            else:
                other_tokens += model_tokens

        return sonnet_tokens, opus_tokens, other_tokens

    def _calculate_segment_distribution(
        self, sonnet_tokens: int, opus_tokens: int, total_tokens: int
    ) -> Tuple[ProgressSegments, ProgressSegments]:
        """Calculate bar segment distribution for models.

        Args:
            sonnet_tokens: Number of Sonnet tokens
            opus_tokens: Number of Opus tokens
            total_tokens: Total token count

        Returns:
            Tuple of (sonnet_filled, opus_filled) segments
        """
        if total_tokens == 0:
            return 0, 0

        sonnet_filled: ProgressSegments = int(self.width * sonnet_tokens / total_tokens)
        opus_filled: ProgressSegments = int(self.width * opus_tokens / total_tokens)

        # Adjust for rounding errors to fill the entire bar
        total_filled: ProgressSegments = sonnet_filled + opus_filled
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

        return max(0, sonnet_filled), max(0, opus_filled)

    def _create_model_summary(
        self,
        sonnet_tokens: int,
        opus_tokens: int,
        other_tokens: int,
        total_tokens: int,
        model_names: List[str],
    ) -> str:
        """Create summary text for model usage.

        Args:
            sonnet_tokens: Sonnet token count
            opus_tokens: Opus token count
            other_tokens: Other model token count
            total_tokens: Total token count
            model_names: List of model names

        Returns:
            Formatted summary string
        """
        if total_tokens == 0:
            return "No tokens used"

        # Calculate percentages
        sonnet_percentage: ProgressPercentage = percentage(sonnet_tokens, total_tokens)
        opus_percentage: ProgressPercentage = percentage(opus_tokens, total_tokens)
        other_percentage: ProgressPercentage = percentage(other_tokens, total_tokens)

        # Create summary based on which models are used
        if opus_tokens > 0 and sonnet_tokens > 0:
            summary = f"Sonnet {sonnet_percentage:.1f}% | Opus {opus_percentage:.1f}%"
        elif sonnet_tokens > 0:
            summary = f"Sonnet {sonnet_percentage:.1f}%"
        elif opus_tokens > 0:
            summary = f"Opus {opus_percentage:.1f}%"
        else:
            summary = f"Other {other_percentage:.1f}%"

        # Add model list for debugging (limit to 3 models)
        if model_names:
            model_list: str = ", ".join(model_names[:3])
            if len(model_names) > 3:
                model_list += f" +{len(model_names) - 3} more"
            debug_info = f" ({model_list})"
        else:
            debug_info = ""

        return f"{summary}{debug_info}"

    def render(self, per_model_stats: Dict[str, ModelStatistics]) -> str:
        """Render model usage progress bar with distribution visualization.

        Args:
            per_model_stats: Dictionary of model statistics with proper typing

        Returns:
            Formatted model usage bar string with Rich markup
        """
        if not per_model_stats:
            empty_bar: str = self._render_bar(
                0, empty_style=self._model_styles["empty"]
            )
            return f"🤖 [{empty_bar}] No model data"

        model_names: List[str] = list(per_model_stats.keys())
        if not model_names:
            empty_bar = self._render_bar(0, empty_style=self._model_styles["empty"])
            return f"🤖 [{empty_bar}] Empty model stats"

        # Aggregate tokens by model family
        sonnet_tokens, opus_tokens, other_tokens = self._aggregate_model_tokens(
            per_model_stats
        )
        total_tokens: int = sonnet_tokens + opus_tokens + other_tokens

        if total_tokens == 0:
            empty_bar = self._render_bar(0, empty_style=self._model_styles["empty"])
            return f"🤖 [{empty_bar}] No tokens used"

        # Calculate segment distribution
        sonnet_filled, opus_filled = self._calculate_segment_distribution(
            sonnet_tokens, opus_tokens, total_tokens
        )

        # Create model-specific bar segments
        sonnet_bar: str = "█" * sonnet_filled
        opus_bar: str = "█" * opus_filled

        bar_segments: List[str] = []
        if sonnet_filled > 0:
            bar_segments.append(f"[{self._model_styles['sonnet']}]{sonnet_bar}[/]")
        if opus_filled > 0:
            bar_segments.append(f"[{self._model_styles['opus']}]{opus_bar}[/]")

        bar_display: str = "".join(bar_segments)

        # Create summary text
        summary: str = self._create_model_summary(
            sonnet_tokens, opus_tokens, other_tokens, total_tokens, model_names
        )

        return f"🤖 [{bar_display}] {summary}"
