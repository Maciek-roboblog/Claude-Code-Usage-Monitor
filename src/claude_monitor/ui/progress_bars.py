"""Progress bar components for Claude Monitor.

Provides token usage, time progress, and model usage progress bars.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Final, Protocol, TypedDict

from claude_monitor.core.models import is_anthropic_model
from claude_monitor.utils.display_width import ascii_fallback_enabled
from claude_monitor.utils.time_utils import percentage


# Type definitions for progress bar components
class ModelStatsDict(TypedDict, total=False):
    """Type definition for model statistics dictionary."""

    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost: float


class ProgressBarStyleConfig(TypedDict, total=False):
    """Configuration for progress bar styling."""

    filled_char: str
    empty_char: str
    filled_style: str | None
    empty_style: str | None


class ThresholdConfig(TypedDict):
    """Configuration for color thresholds."""

    threshold: float
    style: str


class ProgressBarRenderer(Protocol):
    """Protocol for progress bar rendering."""

    def render(self, *args: Any, **kwargs: Any) -> str:
        """Render the progress bar."""
        ...


class BaseProgressBar(ABC):
    """Abstract base class for progress bar components."""

    # Type constants for validation
    MIN_WIDTH: Final[int] = 10
    MAX_WIDTH: Final[int] = 200
    DEFAULT_WIDTH: Final[int] = 50

    # Default styling constants
    DEFAULT_FILLED_CHAR: Final[str] = "█"
    DEFAULT_EMPTY_CHAR: Final[str] = "░"
    ASCII_FILLED_CHAR: Final[str] = "#"
    ASCII_EMPTY_CHAR: Final[str] = "-"
    DEFAULT_MAX_PERCENTAGE: Final[float] = 100.0

    def __init__(self, width: int = 50) -> None:
        """Initialize base progress bar.

        Args:
            width: Width of the progress bar in characters
        """
        self.width: int = width
        self._validate_width()

    def _validate_width(self) -> None:
        """Validate width parameter."""
        if self.width < self.MIN_WIDTH:
            raise ValueError(
                f"Progress bar width must be at least {self.MIN_WIDTH} characters"
            )
        if self.width > self.MAX_WIDTH:
            raise ValueError(
                f"Progress bar width must not exceed {self.MAX_WIDTH} characters"
            )

    def _calculate_filled_segments(
        self, percentage: float, max_value: float = 100.0
    ) -> int:
        """Calculate number of filled segments based on percentage.

        Args:
            percentage: Current percentage value
            max_value: Maximum percentage value (default 100)

        Returns:
            Number of filled segments
        """
        bounded_percentage: float = max(0, min(percentage, max_value))
        return int(self.width * bounded_percentage / max_value)

    def _render_bar(
        self,
        filled: int,
        filled_char: str = "█",
        empty_char: str = "░",
        filled_style: str | None = None,
        empty_style: str | None = None,
    ) -> str:
        """Render the actual progress bar.

        Args:
            filled: Number of filled segments
            filled_char: Character for filled segments
            empty_char: Character for empty segments
            filled_style: Optional style tag for filled segments
            empty_style: Optional style tag for empty segments

        Returns:
            Formatted bar string
        """
        if ascii_fallback_enabled():
            filled_char = self.ASCII_FILLED_CHAR
            empty_char = self.ASCII_EMPTY_CHAR

        filled_bar: str = filled_char * filled
        empty_bar: str = empty_char * (self.width - filled)

        if filled_style:
            filled_bar = f"[{filled_style}]{filled_bar}[/]"
        if empty_style:
            empty_bar = f"[{empty_style}]{empty_bar}[/]"

        return f"{filled_bar}{empty_bar}"

    def _format_percentage(self, percentage: float, precision: int = 1) -> str:
        """Format percentage value for display.

        Args:
            percentage: Percentage value to format
            precision: Number of decimal places

        Returns:
            Formatted percentage string
        """
        return f"{percentage:.{precision}f}%"

    def _get_color_style_by_threshold(
        self, value: float, thresholds: list[tuple[float, str]]
    ) -> str:
        """Get color style based on value thresholds.

        Args:
            value: Current value to check
            thresholds: List of (threshold, style) tuples in descending order

        Returns:
            Style string for the current value
        """
        for threshold, style in thresholds:
            if value >= threshold:
                return style
        return thresholds[-1][1] if thresholds else ""

    @abstractmethod
    def render(self, *args, **kwargs) -> str:
        """Render the progress bar.

        This method must be implemented by subclasses.

        Returns:
            Formatted progress bar string
        """


class TokenProgressBar(BaseProgressBar):
    """Token usage progress bar component."""

    # Color threshold constants
    HIGH_USAGE_THRESHOLD: Final[float] = 90.0
    MEDIUM_USAGE_THRESHOLD: Final[float] = 50.0
    LOW_USAGE_THRESHOLD: Final[float] = 0.0

    # Style constants
    HIGH_USAGE_STYLE: Final[str] = "cost.high"
    MEDIUM_USAGE_STYLE: Final[str] = "cost.medium"
    LOW_USAGE_STYLE: Final[str] = "cost.low"
    BORDER_STYLE: Final[str] = "table.border"

    # Icon constants
    HIGH_USAGE_ICON: Final[str] = "🔴"
    MEDIUM_USAGE_ICON: Final[str] = "🟡"
    LOW_USAGE_ICON: Final[str] = "🟢"

    def render(self, percentage: float) -> str:
        """Render token usage progress bar.

        Args:
            percentage: Usage percentage (can be > 100)

        Returns:
            Formatted progress bar string
        """
        filled: int = self._calculate_filled_segments(min(percentage, 100.0))

        color_thresholds: list[tuple[float, str]] = [
            (self.HIGH_USAGE_THRESHOLD, self.HIGH_USAGE_STYLE),
            (self.MEDIUM_USAGE_THRESHOLD, self.MEDIUM_USAGE_STYLE),
            (self.LOW_USAGE_THRESHOLD, self.LOW_USAGE_STYLE),
        ]

        filled_style: str = self._get_color_style_by_threshold(
            percentage, color_thresholds
        )
        bar: str = self._render_bar(
            filled,
            filled_style=filled_style,
            empty_style=self.BORDER_STYLE
            if percentage < self.HIGH_USAGE_THRESHOLD
            else self.MEDIUM_USAGE_STYLE,
        )

        if ascii_fallback_enabled():
            icon = "!"
        elif percentage >= self.HIGH_USAGE_THRESHOLD:
            icon = self.HIGH_USAGE_ICON
        elif percentage >= self.MEDIUM_USAGE_THRESHOLD:
            icon = self.MEDIUM_USAGE_ICON
        else:
            icon = self.LOW_USAGE_ICON

        percentage_str: str = self._format_percentage(percentage)
        return f"{icon} [{bar}] {percentage_str}"


class TimeProgressBar(BaseProgressBar):
    """Time progress bar component for session duration."""

    def render(self, elapsed_minutes: float, total_minutes: float) -> str:
        """Render time progress bar.

        Args:
            elapsed_minutes: Minutes elapsed in session
            total_minutes: Total session duration in minutes

        Returns:
            Formatted time progress bar string
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
        icon = "time" if ascii_fallback_enabled() else "⏰"
        return f"{icon} [{bar}] {remaining_time}"


class ModelUsageBar(BaseProgressBar):
    """Model usage progress bar showing token distribution across model families."""

    # Known families in display order; anything unmatched falls back to "Other"
    # so no usage is ever silently dropped (issues #124, #164).
    _FAMILY_STYLES: Final[dict[str, str]] = {
        "Sonnet": "info",
        "Opus": "warning",
        "Fable": "highlight",
        "Mythos": "value",
        "Haiku": "success",
        "Other": "dim",
    }

    @staticmethod
    def _family_for(model_name: str) -> str:
        if not is_anthropic_model(model_name):
            return "Other"

        name = model_name.lower()
        if "sonnet" in name:
            return "Sonnet"
        if "opus" in name:
            return "Opus"
        if "fable" in name:
            return "Fable"
        if "mythos" in name:
            return "Mythos"
        if "haiku" in name:
            return "Haiku"
        return "Other"

    def render(self, per_model_stats: dict[str, Any]) -> str:
        """Render model usage progress bar.

        Args:
            per_model_stats: Dictionary of model statistics

        Returns:
            Formatted model usage bar string
        """
        if not per_model_stats:
            empty_bar = self._render_bar(0, empty_style="table.border")
            icon = "model" if ascii_fallback_enabled() else "🤖"
            return f"{icon} [{empty_bar}] No model data"

        family_tokens: dict[str, int] = {}
        for model_name, stats in per_model_stats.items():
            model_tokens = stats.get("input_tokens", 0) + stats.get("output_tokens", 0)
            family = self._family_for(model_name)
            family_tokens[family] = family_tokens.get(family, 0) + model_tokens

        total_tokens = sum(family_tokens.values())
        if total_tokens == 0:
            empty_bar = self._render_bar(0, empty_style="table.border")
            icon = "model" if ascii_fallback_enabled() else "🤖"
            return f"{icon} [{empty_bar}] No tokens used"

        # Families with usage, in canonical display order.
        families = [f for f in self._FAMILY_STYLES if family_tokens.get(f)]

        # Largest-remainder apportionment so segments sum exactly to the bar width.
        exact = {f: self.width * family_tokens[f] / total_tokens for f in families}
        filled = {f: int(v) for f, v in exact.items()}
        order = sorted(families, key=lambda f: exact[f] - filled[f], reverse=True)
        for f in order[: self.width - sum(filled.values())]:
            filled[f] += 1

        filled_char = self.ASCII_FILLED_CHAR if ascii_fallback_enabled() else "█"
        segments = [
            f"[{self._FAMILY_STYLES[f]}]{filled_char * filled[f]}[/]"
            for f in families
            if filled[f] > 0
        ]
        summary = " | ".join(
            f"{f} {percentage(family_tokens[f], total_tokens):.1f}%" for f in families
        )

        icon = "model" if ascii_fallback_enabled() else "🤖"
        return f"{icon} [{''.join(segments)}] {summary}"
