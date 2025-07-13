"""Session display components for Claude Monitor.

Handles formatting of active session screens and session data display.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Protocol, Union

import pytz  # type: ignore[import-untyped]
from rich.console import RenderableType
from rich.text import Text

from claude_monitor.ui.components import CostIndicator, VelocityIndicator
from claude_monitor.ui.layouts import HeaderManager
from claude_monitor.ui.progress_bars import (
    ModelUsageBar,
    TimeProgressBar,
    TokenProgressBar,
)
from claude_monitor.utils.time_utils import (
    format_display_time,
    get_time_format_preference,
    percentage,
)

# Type aliases for Rich rendering and display components
DisplayLine = Union[str, Text, RenderableType]
ProgressBarStyle = str
ModelStats = Dict[str, Dict[str, Union[int, float]]]
SessionEntries = List[Dict[str, Any]]


class DisplayComponentProtocol(Protocol):
    """Protocol for display components that render UI elements."""

    def render(self, *args: Any, **kwargs: Any) -> str:
        """Render the component to a string representation."""
        ...


class ProgressBarProtocol(Protocol):
    """Protocol for progress bar components."""

    def render(self, *args: Any, **kwargs: Any) -> str:
        """Render the progress bar."""
        ...

    def _render_bar(
        self,
        filled: int,
        filled_char: str = "█",
        empty_char: str = "░",
        filled_style: Optional[str] = None,
        empty_style: Optional[str] = None,
    ) -> str:
        """Render the actual progress bar."""
        ...


@dataclass
class SessionDisplayData:
    """Strongly typed data container for session display information.

    This replaces the 21 parameters in format_active_session_screen method
    with proper Rich-aware typing for UI components.
    """

    plan: str
    timezone: str
    tokens_used: int
    token_limit: int
    usage_percentage: float
    tokens_left: int
    elapsed_session_minutes: float
    total_session_minutes: float
    burn_rate: float
    session_cost: float
    per_model_stats: ModelStats
    sent_messages: int
    entries: SessionEntries
    predicted_end_str: str
    reset_time_str: str
    current_time_str: str
    show_switch_notification: bool = False
    show_exceed_notification: bool = False
    show_tokens_will_run_out: bool = False
    original_limit: int = 0


class SessionDisplayComponent:
    """Main component for displaying active session information.

    Implements advanced Rich UI patterns for real-time session monitoring
    with type-safe display rendering and dynamic content updates.
    """

    def __init__(self) -> None:
        """Initialize session display component with typed sub-components."""
        self.token_progress: ProgressBarProtocol = TokenProgressBar()
        self.time_progress: ProgressBarProtocol = TimeProgressBar()
        self.model_usage: ProgressBarProtocol = ModelUsageBar()
        self._style_cache: Dict[str, str] = {}
        self._component_cache: Dict[str, DisplayLine] = {}

    def _render_wide_progress_bar(self, percentage: float) -> str:
        """Render a wide progress bar (50 chars) with Rich-aware styling.

        Args:
            percentage: Progress percentage (can be > 100)

        Returns:
            Formatted progress bar string with Rich markup
        """
        from claude_monitor.terminal.themes import get_cost_style

        if percentage < 50:
            color = "🟢"
        elif percentage < 80:
            color = "🟡"
        else:
            color = "🔴"

        progress_bar = TokenProgressBar(width=50)
        bar_style = get_cost_style(percentage)

        capped_percentage = min(percentage, 100.0)
        filled = progress_bar._calculate_filled_segments(capped_percentage, 100.0)

        if percentage >= 100:
            filled_bar = progress_bar._render_bar(50, filled_style=bar_style)
        else:
            filled_bar = progress_bar._render_bar(
                filled, filled_style=bar_style, empty_style="table.border"
            )

        return f"{color} [{filled_bar}]"

    def format_active_session_screen_v2(
        self, data: SessionDisplayData
    ) -> List[DisplayLine]:
        """Format complete active session screen using strongly typed data class.

        This is the refactored version using SessionDisplayData with Rich-aware typing.

        Args:
            data: SessionDisplayData object containing all display information

        Returns:
            List of formatted lines for Rich display rendering
        """
        return self.format_active_session_screen(
            plan=data.plan,
            timezone=data.timezone,
            tokens_used=data.tokens_used,
            token_limit=data.token_limit,
            usage_percentage=data.usage_percentage,
            tokens_left=data.tokens_left,
            elapsed_session_minutes=data.elapsed_session_minutes,
            total_session_minutes=data.total_session_minutes,
            burn_rate=data.burn_rate,
            session_cost=data.session_cost,
            per_model_stats=data.per_model_stats,
            sent_messages=data.sent_messages,
            entries=data.entries,
            predicted_end_str=data.predicted_end_str,
            reset_time_str=data.reset_time_str,
            current_time_str=data.current_time_str,
            show_switch_notification=data.show_switch_notification,
            show_exceed_notification=data.show_exceed_notification,
            show_tokens_will_run_out=data.show_tokens_will_run_out,
            original_limit=data.original_limit,
        )

    def format_active_session_screen(
        self,
        plan: str,
        timezone: str,
        tokens_used: int,
        token_limit: int,
        usage_percentage: float,
        tokens_left: int,
        elapsed_session_minutes: float,
        total_session_minutes: float,
        burn_rate: float,
        session_cost: float,
        per_model_stats: ModelStats,
        sent_messages: int,
        entries: SessionEntries,
        predicted_end_str: str,
        reset_time_str: str,
        current_time_str: str,
        show_switch_notification: bool = False,
        show_exceed_notification: bool = False,
        show_tokens_will_run_out: bool = False,
        original_limit: int = 0,
        **kwargs: Any,
    ) -> List[DisplayLine]:
        """Format complete active session screen with Rich-aware display components.

        Args:
            plan: Current plan name
            timezone: Display timezone
            tokens_used: Number of tokens used
            token_limit: Token limit for the plan
            usage_percentage: Usage percentage
            tokens_left: Remaining tokens
            elapsed_session_minutes: Minutes elapsed in session
            total_session_minutes: Total session duration
            burn_rate: Current burn rate
            session_cost: Session cost in USD
            per_model_stats: Strongly typed model usage statistics
            sent_messages: Number of messages sent
            entries: Strongly typed session entries
            predicted_end_str: Predicted end time string
            reset_time_str: Reset time string
            current_time_str: Current time string
            show_switch_notification: Show plan switch notification
            show_exceed_notification: Show exceed limit notification
            show_tokens_will_run_out: Show token depletion warning
            original_limit: Original plan limit

        Returns:
            List of formatted screen lines for Rich rendering
        """

        screen_buffer: List[DisplayLine] = []

        header_manager = HeaderManager()
        screen_buffer.extend(header_manager.create_header(plan, timezone))

        if plan in ["custom", "pro", "max5", "max20"]:
            from claude_monitor.core.plans import DEFAULT_COST_LIMIT

            cost_limit_p90 = kwargs.get("cost_limit_p90", DEFAULT_COST_LIMIT)
            messages_limit_p90 = kwargs.get("messages_limit_p90", 1500)

            screen_buffer.append("")
            if plan == "custom":
                screen_buffer.append("[bold]📊 Session-Based Dynamic Limits[/bold]")
                screen_buffer.append(
                    "[dim]Based on your historical usage patterns when hitting limits (P90)[/dim]"
                )
                screen_buffer.append(f"[separator]{'─' * 60}[/]")
            else:
                screen_buffer.append("")

            cost_percentage = (
                min(100, percentage(session_cost, cost_limit_p90))
                if cost_limit_p90 > 0
                else 0
            )
            cost_bar = self._render_wide_progress_bar(cost_percentage)
            screen_buffer.append(
                f"💰 [value]Cost Usage:[/]           {cost_bar} {cost_percentage:4.1f}%    [value]${session_cost:.2f}[/] / [dim]${cost_limit_p90:.2f}[/]"
            )
            screen_buffer.append("")

            token_bar = self._render_wide_progress_bar(usage_percentage)
            screen_buffer.append(
                f"📊 [value]Token Usage:[/]          {token_bar} {usage_percentage:4.1f}%    [value]{tokens_used:,}[/] / [dim]{token_limit:,}[/]"
            )
            screen_buffer.append("")

            messages_percentage = (
                min(100, percentage(sent_messages, messages_limit_p90))
                if messages_limit_p90 > 0
                else 0
            )
            messages_bar = self._render_wide_progress_bar(messages_percentage)
            screen_buffer.append(
                f"📨 [value]Messages Usage:[/]       {messages_bar} {messages_percentage:4.1f}%    [value]{sent_messages}[/] / [dim]{messages_limit_p90:,}[/]"
            )
            screen_buffer.append(f"[separator]{'─' * 60}[/]")

            time_percentage = (
                percentage(elapsed_session_minutes, total_session_minutes)
                if total_session_minutes > 0
                else 0
            )
            time_bar = self._render_wide_progress_bar(time_percentage)
            time_remaining = max(0, total_session_minutes - elapsed_session_minutes)
            time_left_hours = int(time_remaining // 60)
            time_left_mins = int(time_remaining % 60)
            screen_buffer.append(
                f"⏱️  [value]Time to Reset:[/]       {time_bar} {time_left_hours}h {time_left_mins}m"
            )
            screen_buffer.append("")

            if per_model_stats:
                model_bar = self.model_usage.render(per_model_stats)
                screen_buffer.append(f"🤖 [value]Model Distribution:[/]   {model_bar}")
            else:
                model_bar = self.model_usage.render({})
                screen_buffer.append(f"🤖 [value]Model Distribution:[/]   {model_bar}")
            screen_buffer.append(f"[separator]{'─' * 60}[/]")

            velocity_emoji = VelocityIndicator.get_velocity_emoji(burn_rate)
            screen_buffer.append(
                f"🔥 [value]Burn Rate:[/]              [warning]{burn_rate:.1f}[/] [dim]tokens/min[/] {velocity_emoji}"
            )

            cost_per_min = (
                session_cost / max(1, elapsed_session_minutes)
                if elapsed_session_minutes > 0
                else 0
            )
            cost_per_min_display = CostIndicator.render(cost_per_min)
            screen_buffer.append(
                f"💲 [value]Cost Rate:[/]              {cost_per_min_display} [dim]$/min[/]"
            )
        else:
            cost_display = CostIndicator.render(session_cost)
            cost_per_min = (
                session_cost / max(1, elapsed_session_minutes)
                if elapsed_session_minutes > 0
                else 0
            )
            cost_per_min_display = CostIndicator.render(cost_per_min)
            screen_buffer.append(f"💲 [value]Session Cost:[/]   {cost_display}")
            screen_buffer.append(
                f"💲 [value]Cost Rate:[/]      {cost_per_min_display} [dim]$/min[/]"
            )
            screen_buffer.append("")

            token_bar = self.token_progress.render(usage_percentage)
            screen_buffer.append(f"📊 [value]Token Usage:[/]    {token_bar}")
            screen_buffer.append("")

            screen_buffer.append(
                f"🎯 [value]Tokens:[/]         [value]{tokens_used:,}[/] / [dim]~{token_limit:,}[/] ([info]{tokens_left:,} left[/])"
            )

            velocity_emoji = VelocityIndicator.get_velocity_emoji(burn_rate)
            screen_buffer.append(
                f"🔥 [value]Burn Rate:[/]      [warning]{burn_rate:.1f}[/] [dim]tokens/min[/] {velocity_emoji}"
            )

            screen_buffer.append(
                f"📨 [value]Sent Messages:[/]  [info]{sent_messages}[/] [dim]messages[/]"
            )

            if per_model_stats:
                model_bar = self.model_usage.render(per_model_stats)
                screen_buffer.append(f"🤖 [value]Model Usage:[/]    {model_bar}")

            screen_buffer.append("")

            time_bar = self.time_progress.render(
                elapsed_session_minutes, total_session_minutes
            )
            screen_buffer.append(f"⏱️  [value]Time to Reset:[/]  {time_bar}")
            screen_buffer.append("")

        screen_buffer.append("")
        screen_buffer.append("🔮 [value]Predictions:[/]")
        screen_buffer.append(
            f"   [info]Tokens will run out:[/] [warning]{predicted_end_str}[/]"
        )
        screen_buffer.append(
            f"   [info]Limit resets at:[/]     [success]{reset_time_str}[/]"
        )
        screen_buffer.append("")

        self._add_notifications(
            screen_buffer,
            show_switch_notification,
            show_exceed_notification,
            show_tokens_will_run_out,
            original_limit,
            token_limit,
        )

        screen_buffer.append(
            f"⏰ [dim]{current_time_str}[/] 📝 [success]Active session[/] | [dim]Ctrl+C to exit[/] 🟢"
        )

        return screen_buffer

    def _add_notifications(
        self,
        screen_buffer: List[DisplayLine],
        show_switch_notification: bool,
        show_exceed_notification: bool,
        show_tokens_will_run_out: bool,
        original_limit: int,
        token_limit: int,
    ) -> None:
        """Add notification messages to screen buffer with Rich formatting.

        Args:
            screen_buffer: Typed screen buffer to append to
            show_switch_notification: Show plan switch notification
            show_exceed_notification: Show exceed limit notification
            show_tokens_will_run_out: Show token depletion warning
            original_limit: Original plan limit
            token_limit: Current token limit
        """
        notifications_added = False

        if show_switch_notification and token_limit > original_limit:
            screen_buffer.append(
                f"🔄 [warning]Token limit exceeded ({token_limit:,} tokens)[/]"
            )
            notifications_added = True

        if show_exceed_notification:
            screen_buffer.append(
                "⚠️  [error]You have exceeded the maximum cost limit![/]"
            )
            notifications_added = True

        if show_tokens_will_run_out:
            screen_buffer.append(
                "⏰ [warning]Cost limit will be exceeded before reset![/]"
            )
            notifications_added = True

        if notifications_added:
            screen_buffer.append("")

    def format_no_active_session_screen(
        self,
        plan: str,
        timezone: str,
        token_limit: int,
        current_time: Optional[datetime] = None,
        args: Optional[Any] = None,
    ) -> List[DisplayLine]:
        """Format screen for no active session state with Rich components.

        Args:
            plan: Current plan name
            timezone: Display timezone
            token_limit: Token limit for the plan
            current_time: Current datetime
            args: Command line arguments

        Returns:
            List of Rich-formatted screen lines
        """

        screen_buffer: List[DisplayLine] = []

        header_manager = HeaderManager()
        screen_buffer.extend(header_manager.create_header(plan, timezone))

        empty_token_bar = self.token_progress.render(0.0)
        screen_buffer.append(f"📊 [value]Token Usage:[/]    {empty_token_bar}")
        screen_buffer.append("")

        screen_buffer.append(
            f"🎯 [value]Tokens:[/]         [value]0[/] / [dim]~{token_limit:,}[/] ([info]0 left[/])"
        )
        screen_buffer.append(
            "🔥 [value]Burn Rate:[/]      [warning]0.0[/] [dim]tokens/min[/]"
        )
        screen_buffer.append(
            "💲 [value]Cost Rate:[/]      [cost.low]$0.00[/] [dim]$/min[/]"
        )
        screen_buffer.append("📨 [value]Sent Messages:[/]  [info]0[/] [dim]messages[/]")
        screen_buffer.append("")

        if current_time and args:
            try:
                display_tz = pytz.timezone(args.timezone)
                current_time_display = current_time.astimezone(display_tz)
                current_time_str = format_display_time(
                    current_time_display,
                    get_time_format_preference(args),
                    include_seconds=True,
                )
                screen_buffer.append(
                    f"⏰ [dim]{current_time_str}[/] 📝 [info]No active session[/] | [dim]Ctrl+C to exit[/] 🟨"
                )
            except (pytz.exceptions.UnknownTimeZoneError, AttributeError):
                screen_buffer.append(
                    "⏰ [dim]--:--:--[/] 📝 [info]No active session[/] | [dim]Ctrl+C to exit[/] 🟨"
                )
        else:
            screen_buffer.append(
                "⏰ [dim]--:--:--[/] 📝 [info]No active session[/] | [dim]Ctrl+C to exit[/] 🟨"
            )

        return screen_buffer

    def _create_styled_line(
        self, content: str, style: Optional[str] = None, use_markup: bool = True
    ) -> DisplayLine:
        """Create a styled display line with Rich formatting.

        Args:
            content: The text content to display
            style: Optional Rich style to apply
            use_markup: Whether to parse Rich markup in content

        Returns:
            Properly typed display line for Rich rendering
        """
        if use_markup:
            text_obj = Text.from_markup(content)
        else:
            text_obj = Text(content)

        if style:
            text_obj.stylize(style)

        return text_obj

    def _cache_component_render(
        self,
        component_key: str,
        render_func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> DisplayLine:
        """Cache component rendering for performance optimization.

        Args:
            component_key: Unique key for caching
            render_func: Function to call for rendering
            *args: Arguments for render function
            **kwargs: Keyword arguments for render function

        Returns:
            Cached or freshly rendered display line
        """
        cache_key = f"{component_key}_{hash((args, tuple(kwargs.items())))}"

        if cache_key not in self._component_cache:
            result = render_func(*args, **kwargs)
            self._component_cache[cache_key] = result

        return self._component_cache[cache_key]

    def clear_component_cache(self) -> None:
        """Clear the component rendering cache for memory management."""
        self._component_cache.clear()
        self._style_cache.clear()
