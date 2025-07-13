"""UI components for Claude Monitor.

Consolidates display indicators, error/loading screens, and advanced custom display.
"""

from typing import Any, Dict, List, Optional

from rich.console import Console

from claude_monitor.terminal.themes import (
    get_cost_style,
    get_velocity_indicator,
)
from claude_monitor.ui.layouts import HeaderManager


class VelocityIndicator:
    """Velocity indicator component for burn rate visualization."""

    @staticmethod
    def get_velocity_emoji(burn_rate: float) -> str:
        """Get velocity emoji based on burn rate.

        Args:
            burn_rate: Token burn rate per minute

        Returns:
            Emoji representing velocity level
        """
        indicator = get_velocity_indicator(burn_rate)
        return indicator["emoji"]

    @staticmethod
    def get_velocity_description(burn_rate: float) -> str:
        """Get velocity description based on burn rate.

        Args:
            burn_rate: Token burn rate per minute

        Returns:
            Text description of velocity level
        """
        indicator = get_velocity_indicator(burn_rate)
        return indicator["label"]

    @staticmethod
    def render(burn_rate: float, include_description: bool = False) -> str:
        """Render velocity indicator.

        Args:
            burn_rate: Token burn rate per minute
            include_description: Whether to include text description

        Returns:
            Formatted velocity indicator
        """
        emoji = VelocityIndicator.get_velocity_emoji(burn_rate)
        if include_description:
            description = VelocityIndicator.get_velocity_description(burn_rate)
            return f"{emoji} {description}"
        return emoji


class CostIndicator:
    """Cost indicator component for cost visualization."""

    @staticmethod
    def render(cost: float, currency: str = "USD") -> str:
        """Render cost indicator with appropriate styling.

        Args:
            cost: Cost amount
            currency: Currency symbol/code

        Returns:
            Formatted cost indicator
        """
        style = get_cost_style(cost)
        symbol = "$" if currency == "USD" else currency
        return f"[{style}]{symbol}{cost:.4f}[/]"


class ErrorDisplayComponent:
    """Error display component for handling error states."""

    def __init__(self):
        """Initialize error display component."""

    def format_error_screen(
        self, plan: str = "pro", timezone: str = "Europe/Warsaw"
    ) -> List[str]:
        """Format error screen for failed data fetch.

        Args:
            plan: Current plan name
            timezone: Display timezone

        Returns:
            List of formatted error screen lines
        """
        screen_buffer = []

        header_manager = HeaderManager()
        screen_buffer.extend(header_manager.create_header(plan, timezone))

        screen_buffer.append("[error]Failed to get usage data[/]")
        screen_buffer.append("")
        screen_buffer.append("[warning]Possible causes:[/]")
        screen_buffer.append("  • You're not logged into Claude")
        screen_buffer.append("  • Network connection issues")
        screen_buffer.append("")
        screen_buffer.append("[dim]Retrying in 3 seconds... (Ctrl+C to exit)[/]")

        return screen_buffer


class LoadingScreenComponent:
    """Loading screen component for displaying loading states."""

    def __init__(self):
        """Initialize loading screen component."""

    def create_loading_screen(
        self,
        plan: str = "pro",
        timezone: str = "Europe/Warsaw",
        custom_message: str = None,
    ) -> List[str]:
        """Create loading screen content.

        Args:
            plan: Current plan name
            timezone: Display timezone

        Returns:
            List of loading screen lines
        """
        screen_buffer = []

        header_manager = HeaderManager()
        screen_buffer.extend(header_manager.create_header(plan, timezone))

        screen_buffer.append("")
        screen_buffer.append("[info]⏳ Loading...[/]")
        screen_buffer.append("")

        if custom_message:
            screen_buffer.append(f"[warning]{custom_message}[/]")
        else:
            screen_buffer.append("[warning]Fetching Claude usage data...[/]")

        screen_buffer.append("")

        if plan == "custom" and not custom_message:
            screen_buffer.append(
                "[info]Calculating your P90 session limits from usage history...[/]"
            )
            screen_buffer.append("")

        screen_buffer.append("[dim]This may take a few seconds[/]")

        return screen_buffer

    def create_loading_screen_renderable(
        self,
        plan: str = "pro",
        timezone: str = "Europe/Warsaw",
        custom_message: str = None,
    ):
        """Create Rich renderable for loading screen.

        Args:
            plan: Current plan name
            timezone: Display timezone

        Returns:
            Rich renderable for loading screen
        """
        screen_buffer = self.create_loading_screen(plan, timezone, custom_message)

        from claude_monitor.ui.display_controller import ScreenBufferManager

        buffer_manager = ScreenBufferManager()
        return buffer_manager.create_screen_renderable(screen_buffer)


class AdvancedCustomLimitDisplay:
    """Display component for session-based P90 limits from general_limit sessions."""

    def __init__(self, console: Console):
        self.console = console

    def _collect_session_data(
        self, blocks: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Collect session data and identify limit sessions."""
        if not blocks:
            return {
                "all_sessions": [],
                "limit_sessions": [],
                "current_session": {"tokens": 0, "cost": 0.0, "messages": 0},
                "total_sessions": 0,
                "active_sessions": 0,
            }

        all_sessions = []
        limit_sessions = []
        current_session = {"tokens": 0, "cost": 0.0, "messages": 0}
        active_sessions = 0

        for block in blocks:
            if block.get("isGap", False):
                continue

            session = {
                "tokens": block.get("totalTokens", 0),
                "cost": block.get("costUSD", 0.0),
                "messages": block.get("sentMessagesCount", 0),
            }

            if block.get("isActive", False):
                active_sessions += 1
                current_session = session
            elif session["tokens"] > 0:
                all_sessions.append(session)

                if self._is_limit_session(session):
                    limit_sessions.append(session)

        return {
            "all_sessions": all_sessions,
            "limit_sessions": limit_sessions,
            "current_session": current_session,
            "total_sessions": len(all_sessions) + active_sessions,
            "active_sessions": active_sessions,
        }

    def _is_limit_session(self, session: Dict[str, Any]) -> bool:
        """Check if session hit a general limit."""
        tokens = session["tokens"]

        from claude_monitor.core.plans import (
            COMMON_TOKEN_LIMITS,
            LIMIT_DETECTION_THRESHOLD,
        )

        for limit in COMMON_TOKEN_LIMITS:
            if tokens >= limit * LIMIT_DETECTION_THRESHOLD:
                return True

        return False

    def _calculate_session_percentiles(
        self, sessions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate percentiles from session data."""
        if not sessions:
            return {
                "tokens": {"p50": 44000, "p75": 66000, "p90": 88000, "p95": 110000},
                "costs": {"p50": 100.0, "p75": 150.0, "p90": 200.0, "p95": 250.0},
                "messages": {"p50": 150, "p75": 200, "p90": 250, "p95": 300},
                "averages": {"tokens": 44000, "cost": 100.0, "messages": 150},
                "count": 0,
            }

        import numpy as np

        tokens = [s["tokens"] for s in sessions]
        costs = [s["cost"] for s in sessions]
        messages = [s["messages"] for s in sessions]

        return {
            "tokens": {
                "p50": int(np.percentile(tokens, 50)),
                "p75": int(np.percentile(tokens, 75)),
                "p90": int(np.percentile(tokens, 90)),
                "p95": int(np.percentile(tokens, 95)),
            },
            "costs": {
                "p50": float(np.percentile(costs, 50)),
                "p75": float(np.percentile(costs, 75)),
                "p90": float(np.percentile(costs, 90)),
                "p95": float(np.percentile(costs, 95)),
            },
            "messages": {
                "p50": int(np.percentile(messages, 50)),
                "p75": int(np.percentile(messages, 75)),
                "p90": int(np.percentile(messages, 90)),
                "p95": int(np.percentile(messages, 95)),
            },
            "averages": {
                "tokens": float(np.mean(tokens)),
                "cost": float(np.mean(costs)),
                "messages": float(np.mean(messages)),
            },
            "count": len(sessions),
        }


def format_error_screen(
    plan: str = "pro", timezone: str = "Europe/Warsaw"
) -> List[str]:
    """Legacy function - format error screen.

    Maintained for backward compatibility.
    """
    component = ErrorDisplayComponent()
    return component.format_error_screen(plan, timezone)
