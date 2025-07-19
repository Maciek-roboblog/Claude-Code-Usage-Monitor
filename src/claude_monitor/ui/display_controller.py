"""Main display controller for Claude Monitor.

Orchestrates UI components and coordinates display updates.
"""

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytz
from rich.console import Console, Group, RenderableType
from rich.live import Live
from rich.text import Text

from claude_monitor.core.calculations import calculate_hourly_burn_rate
from claude_monitor.core.models import normalize_model_name
from claude_monitor.core.plans import Plans
from claude_monitor.ui.components import (
    AdvancedCustomLimitDisplay,
    ErrorDisplayComponent,
    LoadingScreenComponent,
)
from claude_monitor.ui.layouts import ScreenManager
from claude_monitor.ui.session_display import SessionDisplayComponent
from claude_monitor.utils.notifications import NotificationManager
from claude_monitor.utils.time_utils import (
    TimezoneHandler,
    format_display_time,
    get_time_format_preference,
    percentage,
)


class DisplayController:
    """Main controller for coordinating UI display operations."""

    def __init__(self) -> None:
        """Initialize display controller with components."""
        self.session_display = SessionDisplayComponent()
        self.loading_screen = LoadingScreenComponent()
        self.error_display = ErrorDisplayComponent()
        self.screen_manager = ScreenManager()
        self.live_manager = LiveDisplayManager()
        self.advanced_custom_display = None
        self.buffer_manager = ScreenBufferManager()
        self.session_calculator = SessionCalculator()
        config_dir = Path.home() / ".claude" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        self.notification_manager = NotificationManager(config_dir)

    def _extract_session_data(self, active_block: Dict[str, Any]) -> Dict[str, Any]:
        """Extract basic session data from active block."""
        return {
            "tokens_used": active_block.get("totalTokens", 0),
            "session_cost": active_block.get("costUSD", 0.0),
            "raw_per_model_stats": active_block.get("perModelStats", {}),
            "sent_messages": active_block.get("sentMessagesCount", 0),
            "entries": active_block.get("entries", []),
            "start_time_str": active_block.get("startTime"),
            "end_time_str": active_block.get("endTime"),
        }

    def _calculate_token_limits(self, args: Any, token_limit: int) -> Tuple[int, int]:
        """Calculate token limits based on plan and arguments."""
        if (
            args.plan == "custom"
            and hasattr(args, "custom_limit_tokens")
            and args.custom_limit_tokens
        ):
            return args.custom_limit_tokens, args.custom_limit_tokens
        return token_limit, token_limit

    def _calculate_time_data(
        self, session_data: Dict[str, Any], current_time: datetime
    ) -> Dict[str, Any]:
        """Calculate time-related data for the session."""
        return self.session_calculator.calculate_time_data(session_data, current_time)

    def _calculate_cost_predictions(
        self,
        session_data: Dict[str, Any],
        time_data: Dict[str, Any],
        args: Any,
        cost_limit_p90: Optional[float],
    ) -> Dict[str, Any]:
        """Calculate cost-related predictions."""
        # Determine cost limit based on plan
        if Plans.is_valid_plan(args.plan) and cost_limit_p90 is not None:
            cost_limit = cost_limit_p90
        else:
            cost_limit = 100.0  # Default

        return self.session_calculator.calculate_cost_predictions(
            session_data, time_data, cost_limit
        )

    def _check_notifications(
        self,
        token_limit: int,
        original_limit: int,
        session_cost: float,
        cost_limit: float,
        predicted_end_time: datetime,
        reset_time: datetime,
    ) -> Dict[str, bool]:
        """Check and update notification states."""
        notifications = {}

        # Switch to custom notification
        switch_condition = token_limit > original_limit
        if switch_condition and self.notification_manager.should_notify(
            "switch_to_custom"
        ):
            self.notification_manager.mark_notified("switch_to_custom")
            notifications["show_switch_notification"] = True
        else:
            notifications["show_switch_notification"] = (
                switch_condition
                and self.notification_manager.is_notification_active("switch_to_custom")
            )

        # Exceed limit notification
        exceed_condition = session_cost > cost_limit
        if exceed_condition and self.notification_manager.should_notify(
            "exceed_max_limit"
        ):
            self.notification_manager.mark_notified("exceed_max_limit")
            notifications["show_exceed_notification"] = True
        else:
            notifications["show_exceed_notification"] = (
                exceed_condition
                and self.notification_manager.is_notification_active("exceed_max_limit")
            )

        # Cost will exceed notification
        run_out_condition = predicted_end_time < reset_time
        if run_out_condition and self.notification_manager.should_notify(
            "cost_will_exceed"
        ):
            self.notification_manager.mark_notified("cost_will_exceed")
            notifications["show_cost_will_exceed"] = True
        else:
            notifications["show_cost_will_exceed"] = (
                run_out_condition
                and self.notification_manager.is_notification_active("cost_will_exceed")
            )

        return notifications

    def _format_display_times(
        self,
        args: Any,
        current_time: datetime,
        predicted_end_time: datetime,
        reset_time: datetime,
    ) -> Dict[str, str]:
        """Format times for display."""
        tz_handler = TimezoneHandler(default_tz="Europe/Warsaw")
        timezone_to_use = (
            args.timezone
            if tz_handler.validate_timezone(args.timezone)
            else "Europe/Warsaw"
        )

        # Convert times to display timezone
        predicted_end_local = tz_handler.convert_to_timezone(
            predicted_end_time, timezone_to_use
        )
        reset_time_local = tz_handler.convert_to_timezone(reset_time, timezone_to_use)

        # Format times
        time_format = get_time_format_preference(args)
        predicted_end_str = format_display_time(
            predicted_end_local, time_format, include_seconds=False
        )
        reset_time_str = format_display_time(
            reset_time_local, time_format, include_seconds=False
        )

        # Current time display
        try:
            display_tz = pytz.timezone(args.timezone)
        except pytz.exceptions.UnknownTimeZoneError:
            display_tz = pytz.timezone("Europe/Warsaw")

        current_time_display = current_time.astimezone(display_tz)
        current_time_str = format_display_time(
            current_time_display, time_format, include_seconds=True
        )

        return {
            "predicted_end_str": predicted_end_str,
            "reset_time_str": reset_time_str,
            "current_time_str": current_time_str,
        }

    def create_data_display(
        self, data: Dict[str, Any], args: Any, token_limit: int
    ) -> RenderableType:
        """Create display renderable from data.

        Args:
            data: Usage data dictionary
            args: Command line arguments
            token_limit: Current token limit

        Returns:
            Rich renderable for display
        """
        if not data or "blocks" not in data:
            screen_buffer = self.error_display.format_error_screen(
                args.plan, args.timezone
            )
            return self.buffer_manager.create_screen_renderable(screen_buffer)

        # Find the active block
        active_block = None
        for block in data["blocks"]:
            if isinstance(block, dict) and block.get("isActive", False):
                active_block = block
                break

        # Use UTC timezone for time calculations
        current_time = datetime.now(pytz.UTC)

        if not active_block:
            screen_buffer = self.session_display.format_no_active_session_screen(
                args.plan, args.timezone, token_limit, current_time, args
            )
            return self.buffer_manager.create_screen_renderable(screen_buffer)

        cost_limit_p90 = None
        messages_limit_p90 = None

        if args.plan == "custom":
            temp_display = AdvancedCustomLimitDisplay(None)
            session_data = temp_display._collect_session_data(data["blocks"])
            percentiles = temp_display._calculate_session_percentiles(
                session_data["limit_sessions"]
            )
            cost_limit_p90 = percentiles["costs"]["p90"]
            messages_limit_p90 = percentiles["messages"]["p90"]
        else:
            # Use centralized cost limits
            from claude_monitor.core.plans import get_cost_limit

            cost_limit_p90 = get_cost_limit(args.plan)

            messages_limit_p90 = Plans.get_message_limit(args.plan)

        # Process active session data with cost limit
        try:
            processed_data = self._process_active_session_data(
                active_block, data, args, token_limit, current_time, cost_limit_p90
            )
        except Exception as e:
            # Log the error and show error screen
            logger = logging.getLogger(__name__)
            logger.error(f"Error processing active session data: {e}", exc_info=True)
            screen_buffer = self.error_display.format_error_screen(
                args.plan, args.timezone
            )
            return self.buffer_manager.create_screen_renderable(screen_buffer)

        # Add P90 limits to processed data for display
        if Plans.is_valid_plan(args.plan):
            processed_data["cost_limit_p90"] = cost_limit_p90
            processed_data["messages_limit_p90"] = messages_limit_p90

        try:
            screen_buffer = self.session_display.format_active_session_screen(
                **processed_data
            )
        except Exception as e:
            # Log the error with more details
            logger = logging.getLogger(__name__)
            logger.error(f"Error in format_active_session_screen: {e}", exc_info=True)
            logger.exception(f"processed_data type: {type(processed_data)}")
            if isinstance(processed_data, dict):
                for key, value in processed_data.items():
                    if key == "per_model_stats":
                        logger.exception(f"  {key}: {type(value).__name__}")
                        if isinstance(value, dict):
                            for model, stats in value.items():
                                logger.exception(
                                    f"    {model}: {type(stats).__name__} = {stats}"
                                )
                        else:
                            logger.exception(f"    value = {value}")
                    elif key == "entries":
                        logger.exception(
                            f"  {key}: {type(value).__name__} with {len(value) if isinstance(value, list) else 'N/A'} items"
                        )
                    else:
                        logger.exception(f"  {key}: {type(value).__name__} = {value}")
            screen_buffer = self.error_display.format_error_screen(
                args.plan, args.timezone
            )
            return self.buffer_manager.create_screen_renderable(screen_buffer)

        return self.buffer_manager.create_screen_renderable(screen_buffer)

    def _process_active_session_data(
        self,
        active_block: Dict[str, Any],
        data: Dict[str, Any],
        args: Any,
        token_limit: int,
        current_time: datetime,
        cost_limit_p90: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Process active session data for display.

        Args:
            active_block: Active session block data
            data: Full usage data
            args: Command line arguments
            token_limit: Current token limit
            current_time: Current UTC time
            cost_limit_p90: Optional cost limit

        Returns:
            Processed data dictionary for display
        """
        # Extract session data
        session_data = self._extract_session_data(active_block)

        # Calculate model distribution
        model_distribution = self._calculate_model_distribution(
            session_data["raw_per_model_stats"]
        )

        # Calculate token limits
        token_limit, original_limit = self._calculate_token_limits(args, token_limit)

        # Calculate usage metrics
        tokens_used = session_data["tokens_used"]
        usage_percentage = (
            percentage(tokens_used, token_limit) if token_limit > 0 else 0
        )
        tokens_left = token_limit - tokens_used

        # Calculate time data
        time_data = self._calculate_time_data(session_data, current_time)

        # Calculate burn rate
        burn_rate = calculate_hourly_burn_rate(data["blocks"], current_time)

        # Calculate cost predictions
        cost_data = self._calculate_cost_predictions(
            session_data, time_data, args, cost_limit_p90
        )

        # Check notifications
        notifications = self._check_notifications(
            token_limit,
            original_limit,
            session_data["session_cost"],
            cost_data["cost_limit"],
            cost_data["predicted_end_time"],
            time_data["reset_time"],
        )

        # Format display times
        display_times = self._format_display_times(
            args, current_time, cost_data["predicted_end_time"], time_data["reset_time"]
        )

        # Build result dictionary
        return {
            "plan": args.plan,
            "timezone": args.timezone,
            "tokens_used": tokens_used,
            "token_limit": token_limit,
            "usage_percentage": usage_percentage,
            "tokens_left": tokens_left,
            "elapsed_session_minutes": time_data["elapsed_session_minutes"],
            "total_session_minutes": time_data["total_session_minutes"],
            "burn_rate": burn_rate,
            "session_cost": session_data["session_cost"],
            "per_model_stats": session_data["raw_per_model_stats"],
            "model_distribution": model_distribution,
            "sent_messages": session_data["sent_messages"],
            "entries": session_data["entries"],
            "predicted_end_str": display_times["predicted_end_str"],
            "reset_time_str": display_times["reset_time_str"],
            "current_time_str": display_times["current_time_str"],
            "show_switch_notification": notifications["show_switch_notification"],
            "show_exceed_notification": notifications["show_exceed_notification"],
            "show_tokens_will_run_out": notifications["show_cost_will_exceed"],
            "original_limit": original_limit,
        }

    def _calculate_model_distribution(
        self, raw_per_model_stats: Dict[str, Any]
    ) -> Dict[str, float]:
        """Calculate model distribution percentages from current active session only.

        Args:
            raw_per_model_stats: Raw per-model token statistics from the active session block

        Returns:
            Dictionary mapping model names to usage percentages for the current session
        """
        if not raw_per_model_stats:
            return {}

        # Calculate total tokens per model for THIS SESSION ONLY
        model_tokens = {}
        for model, stats in raw_per_model_stats.items():
            if isinstance(stats, dict):
                # Normalize model name
                normalized_model = normalize_model_name(model)
                if normalized_model and normalized_model != "unknown":
                    # Sum all token types for this model in current session
                    total_tokens = stats.get("input_tokens", 0) + stats.get(
                        "output_tokens", 0
                    )
                    if total_tokens > 0:
                        if normalized_model in model_tokens:
                            model_tokens[normalized_model] += total_tokens
                        else:
                            model_tokens[normalized_model] = total_tokens

        # Calculate percentages based on current session total only
        session_total_tokens = sum(model_tokens.values())
        if session_total_tokens == 0:
            return {}

        model_distribution = {}
        for model, tokens in model_tokens.items():
            model_percentage = percentage(tokens, session_total_tokens)
            model_distribution[model] = model_percentage

        return model_distribution

    def create_loading_display(
        self,
        plan: str = "pro",
        timezone: str = "Europe/Warsaw",
        custom_message: Optional[str] = None,
    ) -> RenderableType:
        """Create loading screen display.

        Args:
            plan: Current plan name
            timezone: Display timezone

        Returns:
            Rich renderable for loading screen
        """
        return self.loading_screen.create_loading_screen_renderable(
            plan, timezone, custom_message
        )

    def create_error_display(
        self, plan: str = "pro", timezone: str = "Europe/Warsaw"
    ) -> RenderableType:
        """Create error screen display.

        Args:
            plan: Current plan name
            timezone: Display timezone

        Returns:
            Rich renderable for error screen
        """
        screen_buffer = self.error_display.format_error_screen(plan, timezone)
        return self.buffer_manager.create_screen_renderable(screen_buffer)

    def create_live_context(self) -> Live:
        """Create live display context manager.

        Returns:
            Live display context manager
        """
        return self.live_manager.create_live_display()

    def set_screen_dimensions(self, width: int, height: int) -> None:
        """Set screen dimensions for responsive layouts.

        Args:
            width: Screen width
            height: Screen height
        """
        self.screen_manager.set_screen_dimensions(width, height)


class LiveDisplayManager:
    """Manager for Rich Live display operations."""

    def __init__(self, console: Optional[Console] = None) -> None:
        """Initialize live display manager.

        Args:
            console: Optional Rich console instance
        """
        self._console = console
        self._live_context: Optional[Live] = None
        self._current_renderable: Optional[RenderableType] = None

    def create_live_display(
        self,
        auto_refresh: bool = True,
        console: Optional[Console] = None,
        refresh_per_second: float = 0.75,
    ) -> Live:
        """Create Rich Live display context.

        Args:
            auto_refresh: Whether to auto-refresh
            console: Optional console instance
            refresh_per_second: Display refresh rate (0.1-20 Hz)

        Returns:
            Rich Live context manager
        """
        display_console = console or self._console

        self._live_context = Live(
            console=display_console,
            refresh_per_second=refresh_per_second,
            auto_refresh=auto_refresh,
            vertical_overflow="visible",  # Prevent screen scrolling
        )

        return self._live_context


class ScreenBufferManager:
    """Manager for screen buffer operations and rendering."""

    def __init__(self) -> None:
        """Initialize screen buffer manager."""
        self.console: Optional[Console] = None

    def create_screen_renderable(self, screen_buffer: List[str]) -> Group:
        """Create Rich renderable from screen buffer.

        Args:
            screen_buffer: List of screen lines with Rich markup

        Returns:
            Rich Group renderable
        """
        from claude_monitor.terminal.themes import get_themed_console

        if self.console is None:
            self.console = get_themed_console()

        text_objects = []
        for line in screen_buffer:
            if isinstance(line, str):
                # Use console to render markup properly
                text_obj = Text.from_markup(line)
                text_objects.append(text_obj)
            else:
                text_objects.append(line)

        return Group(*text_objects)


# Legacy functions for backward compatibility
def create_screen_renderable(screen_buffer: List[str]) -> Group:
    """Legacy function - create screen renderable.

    Maintained for backward compatibility.
    """
    manager = ScreenBufferManager()
    return manager.create_screen_renderable(screen_buffer)


class SessionCalculator:
    """Handles session-related calculations for display purposes.
    (Moved from ui/calculators.py)"""

    def __init__(self) -> None:
        """Initialize session calculator."""
        self.tz_handler = TimezoneHandler()

    def calculate_time_data(
        self, session_data: Dict[str, Any], current_time: datetime
    ) -> Dict[str, Any]:
        """Calculate time-related data for the session.

        Args:
            session_data: Dictionary containing session information
            current_time: Current UTC time

        Returns:
            Dictionary with calculated time data
        """
        # Parse start time
        start_time = None
        if session_data.get("start_time_str"):
            start_time = self.tz_handler.parse_timestamp(session_data["start_time_str"])
            start_time = self.tz_handler.ensure_utc(start_time)

        # Calculate reset time
        if session_data.get("end_time_str"):
            reset_time = self.tz_handler.parse_timestamp(session_data["end_time_str"])
            reset_time = self.tz_handler.ensure_utc(reset_time)
        else:
            reset_time = (
                start_time + timedelta(hours=5)  # Default session duration
                if start_time
                else current_time + timedelta(hours=5)  # Default session duration
            )

        # Calculate session times
        time_to_reset = reset_time - current_time
        minutes_to_reset = time_to_reset.total_seconds() / 60

        if start_time and session_data.get("end_time_str"):
            total_session_minutes = (reset_time - start_time).total_seconds() / 60
            elapsed_session_minutes = (current_time - start_time).total_seconds() / 60
            elapsed_session_minutes = max(0, elapsed_session_minutes)
        else:
            total_session_minutes = 5 * 60  # Default session duration in minutes
            elapsed_session_minutes = max(0, total_session_minutes - minutes_to_reset)

        return {
            "start_time": start_time,
            "reset_time": reset_time,
            "minutes_to_reset": minutes_to_reset,
            "total_session_minutes": total_session_minutes,
            "elapsed_session_minutes": elapsed_session_minutes,
        }

    def calculate_cost_predictions(
        self,
        session_data: Dict[str, Any],
        time_data: Dict[str, Any],
        cost_limit: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Calculate cost-related predictions.

        Args:
            session_data: Dictionary containing session cost information
            time_data: Time data from calculate_time_data
            cost_limit: Optional cost limit (defaults to 100.0)

        Returns:
            Dictionary with cost predictions
        """
        elapsed_minutes = time_data["elapsed_session_minutes"]
        session_cost = session_data.get("session_cost", 0.0)
        current_time = datetime.now(timezone.utc)

        # Calculate cost per minute
        cost_per_minute = (
            session_cost / max(1, elapsed_minutes) if elapsed_minutes > 0 else 0
        )

        # Use provided cost limit or default
        if cost_limit is None:
            cost_limit = 100.0

        cost_remaining = max(0, cost_limit - session_cost)

        # Calculate predicted end time
        if cost_per_minute > 0 and cost_remaining > 0:
            minutes_to_cost_depletion = cost_remaining / cost_per_minute
            predicted_end_time = current_time + timedelta(
                minutes=minutes_to_cost_depletion
            )
        else:
            predicted_end_time = time_data["reset_time"]

        return {
            "cost_per_minute": cost_per_minute,
            "cost_limit": cost_limit,
            "cost_remaining": cost_remaining,
            "predicted_end_time": predicted_end_time,
        }
