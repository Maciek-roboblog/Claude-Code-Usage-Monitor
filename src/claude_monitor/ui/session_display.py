"""Session display components for Claude Monitor.

Handles formatting of active session screens and session data display.
"""

import math
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

import pytz

from claude_monitor.ui.components import CostIndicator, VelocityIndicator
from claude_monitor.ui.layouts import HeaderManager
from claude_monitor.ui.progress_bars import (
    ModelUsageBar,
    TimeProgressBar,
    TokenProgressBar,
)
from claude_monitor.utils.display_width import (
    ascii_fallback_enabled,
    pad_to_display_width,
)
from claude_monitor.utils.time_utils import (
    format_display_time,
    get_time_format_preference,
    percentage,
)

_EMOJI_RE = re.compile(
    "["
    "\U0001f300-\U0001faff"  # emoji & pictographs
    "\U00002600-\U000027bf"  # misc symbols, dingbats
    "\U0001f1e6-\U0001f1ff"  # regional indicators
    "\u2b00-\u2bff"  # misc symbols and arrows
    "\u2300-\u23ff"  # misc technical (clocks, etc.)
    "\ufe0f"  # variation selector-16
    "]"
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

    WIDE_BAR_COLUMN: int = 25

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

        if ascii_fallback_enabled():
            color = "!"

        return f"{color} [{filled_bar}]"

    def _metric_prefix(self, icon: str, label: str) -> str:
        """Return a Rich prefix padded by terminal display cells."""
        return pad_to_display_width(f"{icon} [value]{label}:[/]", self.WIDE_BAR_COLUMN)

    @staticmethod
    def _limit_confidence_suffix(confidence: Optional[str], stale: bool = False) -> str:
        labels = {
            "official": "official",
            "experimental": "experimental",
            "local_estimate": "local estimate",
            "unknown": "unknown",
        }
        label = labels.get(confidence or "")
        if not label:
            return ""
        if stale:
            label = f"{label}, stale"
        return f" [dim]({label})[/]"

    @staticmethod
    def _p90_limit_suffix(
        plan: str, limit_is_p90: bool = True, confidence: Optional[str] = None
    ) -> str:
        """Mark a custom-plan limit as an auto-estimate from local usage history.

        The custom limit is the P90 of the user's own past sessions, so it moves
        as usage grows. Fixed plans and official/experimental limits are never
        annotated.
        """
        if plan != "custom" or not limit_is_p90:
            return ""
        if confidence in {"official", "experimental"}:
            return ""
        return " [dim](auto P90)[/]"

    @staticmethod
    def _token_detail_suffix(label: Optional[str]) -> str:
        if not label:
            return ""
        return f" [dim]({label})[/]"

    @staticmethod
    def _finite_float(value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if math.isfinite(number) else None

    def _snapshot_limit_overlay(self, snapshot: Optional[dict]) -> dict[str, Any]:
        if not snapshot:
            return {}

        five_hour = (snapshot.get("limits") or {}).get("five_hour") or {}
        pct = self._finite_float(five_hour.get("used_percentage"))
        if pct is None:
            return {}

        confidence = five_hour.get("confidence") or "unknown"
        tokens_used = self._finite_float(five_hour.get("tokens_used"))
        token_limit = self._finite_float(five_hour.get("token_limit"))
        overlay: dict[str, Any] = {
            "usage_percentage": pct,
            "limit_confidence": confidence,
            "limit_stale": bool(snapshot.get("stale"))
            and confidence in {"official", "experimental"},
        }
        if tokens_used is not None:
            overlay["tokens_used"] = int(tokens_used)
        if token_limit is not None and token_limit > 0:
            overlay["token_limit"] = int(token_limit)
        if tokens_used is None and confidence != "local_estimate":
            overlay["limit_tokens_label"] = "local estimate unavailable"
        return overlay

    @staticmethod
    def _separator_line(width: int = 60) -> str:
        char = "-" if ascii_fallback_enabled() else "─"
        return f"[separator]{char * width}[/]"

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
        limit_suffix = self._limit_confidence_suffix(
            kwargs.get("limit_confidence"), kwargs.get("limit_stale", False)
        )
        token_detail_suffix = self._token_detail_suffix(
            kwargs.get("limit_tokens_label")
        )
        p90_suffix = self._p90_limit_suffix(
            plan,
            kwargs.get("limit_is_p90", True),
            kwargs.get("limit_confidence"),
        )
        # Cost and message limits for the custom plan are always P90-derived
        # (no explicit-override flag and no official source for them).
        p90_estimate_suffix = self._p90_limit_suffix(plan)

        if not kwargs.get("no_header", False):
            header_manager = HeaderManager()
            screen_buffer.extend(header_manager.create_header(plan, timezone))

        if plan in ["custom", "pro", "max5", "max20", "team"]:
            from claude_monitor.core.plans import DEFAULT_COST_LIMIT, Plans

            cost_limit_p90 = kwargs.get("cost_limit_p90", DEFAULT_COST_LIMIT)
            messages_limit_p90 = kwargs.get("messages_limit_p90", 1500)

            screen_buffer.append("")
            if plan == "custom":
                screen_buffer.append("[bold]📊 Session-Based Dynamic Limits[/bold]")
                screen_buffer.append(
                    "[dim]Auto-estimated from your own usage history (P90) - it adapts as you use more[/dim]"
                )
                screen_buffer.append(self._separator_line())
            else:
                screen_buffer.append("")
                plan_info = Plans.get_plan_info(plan)
                if plan_info["unverified"] and plan_info["guidance"]:
                    screen_buffer.append(f"[warning]{plan_info['guidance']}[/]")
                    screen_buffer.append(self._separator_line())

            cost_percentage = (
                min(100, percentage(session_cost, cost_limit_p90))
                if cost_limit_p90 > 0
                else 0
            )
            cost_bar = self._render_wide_progress_bar(cost_percentage)
            screen_buffer.append(
                f"{self._metric_prefix('💰', 'Cost Usage')}{cost_bar} {cost_percentage:4.1f}%    [value]${session_cost:.2f}[/] / [dim]${cost_limit_p90:.2f}[/]{p90_estimate_suffix}"
            )
            screen_buffer.append("")

            token_bar = self._render_wide_progress_bar(usage_percentage)
            screen_buffer.append(
                f"{self._metric_prefix('📊', 'Token Usage')}{token_bar} {usage_percentage:4.1f}%{limit_suffix}    [value]{tokens_used:,}[/] / [dim]{token_limit:,}[/]{p90_suffix}{token_detail_suffix}"
            )
            screen_buffer.append("")

            messages_percentage = (
                min(100, percentage(sent_messages, messages_limit_p90))
                if messages_limit_p90 > 0
                else 0
            )
            messages_bar = self._render_wide_progress_bar(messages_percentage)
            screen_buffer.append(
                f"{self._metric_prefix('📨', 'Messages Usage')}{messages_bar} {messages_percentage:4.1f}%    [value]{sent_messages}[/] / [dim]{messages_limit_p90:,}[/]{p90_estimate_suffix}"
            )
            screen_buffer.append(self._separator_line())

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
                f"{self._metric_prefix('⏳', 'Time to Reset')}{time_bar} {time_left_hours}h {time_left_mins}m"
            )
            screen_buffer.append("")

            if not kwargs.get("hide_model_distribution", False):
                model_bar = self.model_usage.render(per_model_stats or {})
                screen_buffer.append(f"🤖 [value]Model Distribution:[/]   {model_bar}")
            screen_buffer.append(self._separator_line())

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
            screen_buffer.append(
                f"📊 [value]Token Usage:[/]    {token_bar}{limit_suffix}"
            )
            screen_buffer.append("")

            screen_buffer.append(
                f"🎯 [value]Tokens:[/]         [value]{tokens_used:,}[/] / [dim]~{token_limit:,}[/] ([info]{tokens_left:,} left[/]){token_detail_suffix}"
            )

            velocity_emoji = VelocityIndicator.get_velocity_emoji(burn_rate)
            screen_buffer.append(
                f"🔥 [value]Burn Rate:[/]      [warning]{burn_rate:.1f}[/] [dim]tokens/min[/] {velocity_emoji}"
            )

            screen_buffer.append(
                f"📨 [value]Sent Messages:[/]  [info]{sent_messages}[/] [dim]messages[/]"
            )

            if per_model_stats and not kwargs.get("hide_model_distribution", False):
                model_bar = self.model_usage.render(per_model_stats)
                screen_buffer.append(f"🤖 [value]Model Usage:[/]    {model_bar}")

            screen_buffer.append("")

            time_bar = self.time_progress.render(
                elapsed_session_minutes, total_session_minutes
            )
            screen_buffer.append(f"⏳ [value]Time to Reset:[/]  {time_bar}")
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

        if kwargs.get("no_emoji", False) or ascii_fallback_enabled():
            screen_buffer = [_EMOJI_RE.sub("", line) for line in screen_buffer]

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
        snapshot: Optional[dict] = None,
    ) -> list[str]:
        """Format screen for no active session state.

        Args:
            plan: Current plan name
            timezone: Display timezone
            token_limit: Token limit for the plan
            current_time: Current datetime
            args: Command line arguments
            snapshot: Optional official-aware snapshot for limit overlays

        Returns:
            List of formatted screen lines
        """

        screen_buffer = []

        if not (args and getattr(args, "no_header", False)):
            header_manager = HeaderManager()
            screen_buffer.extend(header_manager.create_header(plan, timezone))

        overlay = self._snapshot_limit_overlay(snapshot)
        usage_percentage = overlay.get("usage_percentage", 0.0)
        display_token_limit = overlay.get("token_limit", token_limit)
        tokens_used = overlay.get("tokens_used")
        tokens_left = (
            max(0, display_token_limit - tokens_used)
            if tokens_used is not None and display_token_limit > 0
            else None
        )
        limit_suffix = self._limit_confidence_suffix(
            overlay.get("limit_confidence"), overlay.get("limit_stale", False)
        )
        token_detail_suffix = self._token_detail_suffix(
            overlay.get("limit_tokens_label")
        )
        p90_suffix = self._p90_limit_suffix(
            plan,
            not getattr(args, "custom_limit_tokens", None),
            overlay.get("limit_confidence"),
        )

        empty_token_bar = self.token_progress.render(usage_percentage)
        screen_buffer.append(f"📊 [value]Token Usage:[/]    {empty_token_bar}")
        if limit_suffix:
            screen_buffer[-1] = f"{screen_buffer[-1]}{limit_suffix}"
        screen_buffer.append("")

        tokens_used_text = f"{tokens_used:,}" if tokens_used is not None else "--"
        tokens_left_text = f"{tokens_left:,}" if tokens_left is not None else "--"
        screen_buffer.append(
            f"🎯 [value]Tokens:[/]         [value]{tokens_used_text}[/] / [dim]~{display_token_limit:,}[/]{p90_suffix} ([info]{tokens_left_text} left[/]){token_detail_suffix}"
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

        if (args and getattr(args, "no_emoji", False)) or ascii_fallback_enabled():
            screen_buffer = [_EMOJI_RE.sub("", line) for line in screen_buffer]

        return screen_buffer
