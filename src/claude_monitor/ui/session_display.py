"""Session display components for Claude Monitor.

Handles formatting of active session screens and session data display.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

import pytz
from rich.table import Table

from claude_monitor.i18n import _
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


@dataclass
class SessionDisplayData:
    """Data container for session display information.

    This replaces the 21 parameters in format_active_session_screen method.
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
    per_model_stats: dict[str, Any]
    sent_messages: int
    entries: list[dict]
    predicted_end_str: str
    reset_time_str: str
    current_time_str: str
    show_switch_notification: bool = False
    show_exceed_notification: bool = False
    show_tokens_will_run_out: bool = False
    original_limit: int = 0


class SessionDisplayComponent:
    """Main component for displaying active session information."""

    def __init__(self):
        """Initialize session display component with sub-components."""
        self.token_progress = TokenProgressBar()
        self.time_progress = TimeProgressBar()
        self.model_usage = ModelUsageBar()

    def _render_wide_progress_bar(self, percentage: float) -> str:
        """Render a wide progress bar (50 chars) using centralized progress bar logic.

        Args:
            percentage: Progress percentage (can be > 100)

        Returns:
            Formatted progress bar string
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

    def _create_aligned_stats_grid(self, stats_data: list[tuple[str, str]]) -> Table:
        """Create an aligned grid for displaying statistics.

        Args:
            stats_data: List of tuples (label, value) for each statistic

        Returns:
            Configured Table with aligned statistics
        """
        table = Table(
            show_header=False, show_lines=False, show_edge=False, padding=(0, 1)
        )
        table.add_column(justify="left")  # Column for labels
        table.add_column(justify="left")  # Column for values

        for label, value in stats_data:
            table.add_row(label, value)

        return table

    def _format_aligned_stats(self, stats_data: list[tuple[str, str]]) -> list[str]:
        """Format statistics with dynamic alignment based on translated labels.

        Args:
            stats_data: List of tuples (label, value) for each statistic

        Returns:
            List of formatted strings with proper alignment
        """
        from rich.text import Text

        # Calculate the maximum display width of all labels
        max_label_width = 0
        for label, value in stats_data:
            label_display_width = Text.from_markup(label).cell_len
            max_label_width = max(max_label_width, label_display_width)

        # Add some padding for better visual spacing
        padding_width = max_label_width + 4

        # Format each statistic with consistent alignment
        formatted_stats = []
        for label, value in stats_data:
            label_display_width = Text.from_markup(label).cell_len
            padding_needed = max(0, padding_width - label_display_width)
            formatted_line = f"{label}{' ' * padding_needed}{value}"
            formatted_stats.append(formatted_line)

        return formatted_stats

    def format_active_session_screen_v2(self, data: SessionDisplayData) -> list[str]:
        """Format complete active session screen using data class.

        This is the refactored version using SessionDisplayData.

        Args:
            data: SessionDisplayData object containing all display information

        Returns:
            List of formatted lines for display
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
        per_model_stats: dict[str, Any],
        sent_messages: int,
        entries: list[dict],
        predicted_end_str: str,
        reset_time_str: str,
        current_time_str: str,
        show_switch_notification: bool = False,
        show_exceed_notification: bool = False,
        show_tokens_will_run_out: bool = False,
        original_limit: int = 0,
        **kwargs,
    ) -> list[str]:
        """Format complete active session screen.

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
            per_model_stats: Model usage statistics
            sent_messages: Number of messages sent
            entries: Session entries
            predicted_end_str: Predicted end time string
            reset_time_str: Reset time string
            current_time_str: Current time string
            show_switch_notification: Show plan switch notification
            show_exceed_notification: Show exceed limit notification
            show_tokens_will_run_out: Show token depletion warning
            original_limit: Original plan limit

        Returns:
            List of formatted screen lines
        """

        screen_buffer = []

        header_manager = HeaderManager()
        screen_buffer.extend(header_manager.create_header(plan, timezone))

        if plan in ["custom", "pro", "max5", "max20"]:
            from claude_monitor.core.plans import DEFAULT_COST_LIMIT

            cost_limit_p90 = kwargs.get("cost_limit_p90", DEFAULT_COST_LIMIT)
            messages_limit_p90 = kwargs.get("messages_limit_p90", 1500)

            screen_buffer.append("")
            if plan == "custom":
                screen_buffer.append(
                    f"[bold]📊 {_('Session-Based Dynamic Limits')}[/bold]"
                )
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
                f"💰 [value]{_('Cost Usage')}:[/]           {cost_bar} {cost_percentage:4.1f}%    [value]${session_cost:.2f}[/] / [dim]${cost_limit_p90:.2f}[/]"
            )
            screen_buffer.append("")

            token_bar = self._render_wide_progress_bar(usage_percentage)
            screen_buffer.append(
                f"📊 [value]{_('Token Usage')}:[/]          {token_bar} {usage_percentage:4.1f}%    [value]{tokens_used:,}[/] / [dim]{token_limit:,}[/]"
            )
            screen_buffer.append("")

            messages_percentage = (
                min(100, percentage(sent_messages, messages_limit_p90))
                if messages_limit_p90 > 0
                else 0
            )
            messages_bar = self._render_wide_progress_bar(messages_percentage)
            screen_buffer.append(
                f"📨 [value]{_('Messages Usage')}:[/]       {messages_bar} {messages_percentage:4.1f}%    [value]{sent_messages}[/] / [dim]{messages_limit_p90:,}[/]"
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
                f"⏱️  [value]{_('Time to Reset')}:[/]       {time_bar} {time_left_hours}h {time_left_mins}m"
            )
            screen_buffer.append("")

            if per_model_stats:
                model_bar = self.model_usage.render(per_model_stats)
                screen_buffer.append(
                    f"🤖 [value]{_('Model Distribution')}:[/]   {model_bar}"
                )
            else:
                model_bar = self.model_usage.render({})
                screen_buffer.append(
                    f"🤖 [value]{_('Model Distribution')}:[/]   {model_bar}"
                )
            screen_buffer.append(f"[separator]{'─' * 60}[/]")

            velocity_emoji = VelocityIndicator.get_velocity_emoji(burn_rate)
            screen_buffer.append(
                f"🔥 [value]{_('Burn Rate')}:[/]              [warning]{burn_rate:.1f}[/] [dim]tokens/min[/] {velocity_emoji}"
            )

            cost_per_min = (
                session_cost / max(1, elapsed_session_minutes)
                if elapsed_session_minutes > 0
                else 0
            )
            cost_per_min_display = CostIndicator.render(cost_per_min)
            screen_buffer.append(
                f"💲 [value]{_('Cost Rate')}:[/]              {cost_per_min_display} [dim]$/min[/]"
            )
        else:
            cost_display = CostIndicator.render(session_cost)
            cost_per_min = (
                session_cost / max(1, elapsed_session_minutes)
                if elapsed_session_minutes > 0
                else 0
            )
            cost_per_min_display = CostIndicator.render(cost_per_min)
            token_bar = self.token_progress.render(usage_percentage)
            velocity_emoji = VelocityIndicator.get_velocity_emoji(burn_rate)

            # Regrouper les statistiques pour la table
            stats_data = [
                (f"💲 [value]{_('Session Cost')}:[/]", cost_display),
                (
                    f"💲 [value]{_('Cost Rate')}:[/]",
                    f"{cost_per_min_display} [dim]$/min[/]",
                ),
                (f"📊 [value]{_('Token Usage')}:[/]", token_bar),
                (
                    f"🎯 [value]{_('Tokens')}:[/]",
                    f"[value]{tokens_used:,}[/] / [dim]~{token_limit:,}[/] "
                    f"([info]{tokens_left:,} {_('left')}[/])",
                ),
                (
                    f"🔥 [value]{_('Burn Rate')}:[/]",
                    f"[warning]{burn_rate:.1f}[/] [dim]tokens/min[/] {velocity_emoji}",
                ),
                (
                    f"📨 [value]{_('Sent Messages')}:[/]",
                    f"[info]{sent_messages}[/] [dim]messages[/]",
                ),
            ]

            if per_model_stats:
                model_bar = self.model_usage.render(per_model_stats)
                stats_data.append((f"🤖 [value]{_('Model Usage')}:[/]", model_bar))

            # Formater les statistiques avec alignement dynamique
            formatted_stats = self._format_aligned_stats(stats_data)
            screen_buffer.extend(formatted_stats)
            screen_buffer.append("")

            time_bar = self.time_progress.render(
                elapsed_session_minutes, total_session_minutes
            )
            screen_buffer.append(f"⏱️  [value]{_('Time to Reset')}:[/]  {time_bar}")
            screen_buffer.append("")

        screen_buffer.append("")
        screen_buffer.append(f"🔮 [value]{_('Predictions')}:[/]")
        screen_buffer.append(
            f"   [info]{_('Tokens will run out')}:[/] [warning]{predicted_end_str}[/]"
        )
        screen_buffer.append(
            f"   [info]{_('Limit resets at')}:[/]     [success]{reset_time_str}[/]"
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
            f"⏰ [dim]{current_time_str}[/] 📝 [success]Active session[/] | "
            f"[dim]{_('Ctrl+C to exit')}[/] 🟢"
        )

        return screen_buffer

    def _add_notifications(
        self,
        screen_buffer: list[str],
        show_switch_notification: bool,
        show_exceed_notification: bool,
        show_tokens_will_run_out: bool,
        original_limit: int,
        token_limit: int,
    ) -> None:
        """Add notification messages to screen buffer.

        Args:
            screen_buffer: Screen buffer to append to
            show_switch_notification: Show plan switch notification
            show_exceed_notification: Show exceed limit notification
            show_tokens_will_run_out: Show token depletion warning
            original_limit: Original plan limit
            token_limit: Current token limit
        """
        notifications_added = False

        if show_switch_notification and token_limit > original_limit:
            screen_buffer.append(
                f"🔄 [warning]{_('Token limit exceeded')}: {token_limit:,} {_('tokens')}[/]"
            )
            notifications_added = True

        if show_exceed_notification:
            screen_buffer.append(
                f"⚠️  [error]{_('You have exceeded the maximum cost limit!')}[/]"
            )
            notifications_added = True

        if show_tokens_will_run_out:
            screen_buffer.append(
                f"⏰ [warning]{_('Cost limit will be exceeded before reset!')}[/]"
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
    ) -> list[str]:
        """Format screen for no active session state.

        Args:
            plan: Current plan name
            timezone: Display timezone
            token_limit: Token limit for the plan
            current_time: Current datetime
            args: Command line arguments

        Returns:
            List of formatted screen lines
        """

        screen_buffer = []

        header_manager = HeaderManager()
        screen_buffer.extend(header_manager.create_header(plan, timezone))

        empty_token_bar = self.token_progress.render(0.0)

        # Regrouper les statistiques pour la table
        stats_data = [
            (f"📊 [value]{_('Token Usage')}:[/]", empty_token_bar),
            (
                f"🎯 [value]{_('Tokens')}:[/]",
                f"[value]0[/] / [dim]~{token_limit:,}[/] ([info]0 {_('left')}[/])",
            ),
            (f"🔥 [value]{_('Burn Rate')}:[/]", "[warning]0.0[/] [dim]tokens/min[/]"),
            (f"💲 [value]{_('Cost Rate')}:[/]", "[cost.low]$0.00[/] [dim]$/min[/]"),
            (f"📨 [value]{_('Sent Messages')}:[/]", "[info]0[/] [dim]messages[/]"),
        ]

        # Créer et rendre les statistiques avec alignement dynamique
        formatted_stats = self._format_aligned_stats(stats_data)
        screen_buffer.extend(formatted_stats)
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
                    f"⏰ [dim]{current_time_str}[/] 📝 "
                    f"[info]{_('No active session')}[/] | "
                    f"[dim]{_('Ctrl+C to exit')}[/] 🟨"
                )
            except (pytz.exceptions.UnknownTimeZoneError, AttributeError):
                screen_buffer.append(
                    f"⏰ [dim]--:--:--[/] 📝 "
                    f"[info]{_('No active session')}[/] | "
                    f"[dim]{_('Ctrl+C to exit')}[/] 🟨"
                )
        else:
            screen_buffer.append(
                f"⏰ [dim]--:--:--[/] 📝 [info]{_('No active session')}[/] | "
                f"[dim]{_('Ctrl+C to exit')}[/] 🟨"
            )

        return screen_buffer
