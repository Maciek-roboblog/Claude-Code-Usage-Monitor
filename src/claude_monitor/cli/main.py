"""Simplified CLI entry point using pydantic-settings."""

import logging
import sys
import traceback
from pathlib import Path
from typing import List, Optional

from claude_monitor import __version__
from claude_monitor.cli.bootstrap import (
    ensure_directories,
    init_timezone,
    setup_environment,
    setup_logging,
)
from claude_monitor.core.plans import Plans, PlanType, get_token_limit
from claude_monitor.core.settings import Settings
from claude_monitor.data.analysis import analyze_usage
from claude_monitor.error_handling import report_error
from claude_monitor.monitoring.orchestrator import MonitoringOrchestrator
from claude_monitor.terminal.manager import (
    enter_alternate_screen,
    handle_cleanup_and_exit,
    handle_error_and_exit,
    restore_terminal,
    setup_terminal,
)
from claude_monitor.terminal.themes import get_themed_console, print_themed
from claude_monitor.ui.display_controller import DisplayController


def get_standard_claude_paths() -> List[str]:
    """Get list of standard Claude data directory paths to check."""
    return ["~/.claude/projects", "~/.config/claude/projects"]


def discover_claude_data_paths(custom_paths: List[str] = None) -> List[Path]:
    """Discover all available Claude data directories.

    Args:
        custom_paths: Optional list of custom paths to check instead of standard ones

    Returns:
        List of Path objects for existing Claude data directories
    """
    if custom_paths:
        paths_to_check = custom_paths
    else:
        paths_to_check = get_standard_claude_paths()

    discovered_paths = []

    for path_str in paths_to_check:
        path = Path(path_str).expanduser().resolve()
        if path.exists() and path.is_dir():
            discovered_paths.append(path)

    return discovered_paths


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point with direct pydantic-settings integration."""
    if argv is None:
        argv = sys.argv[1:]

    if "--version" in argv or "-v" in argv:
        print(f"claude-monitor {__version__}")
        return 0

    try:
        settings = Settings.load_with_last_used(argv)

        setup_environment()
        ensure_directories()

        if settings.log_file:
            setup_logging(settings.log_level, settings.log_file, disable_console=True)
        else:
            setup_logging(settings.log_level, disable_console=True)

        init_timezone(settings.timezone)

        args = settings.to_namespace()

        _run_monitoring(args)

        return 0

    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user.")
        return 0
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Monitor failed: {e}", exc_info=True)
        traceback.print_exc()
        return 1


def _run_monitoring(args):
    """Main monitoring implementation without facade."""
    if hasattr(args, "theme") and args.theme:
        console = get_themed_console(force_theme=args.theme.lower())
    else:
        console = get_themed_console()

    old_terminal_settings = setup_terminal()
    live_display_active = False

    try:
        data_paths = discover_claude_data_paths()
        if not data_paths:
            print_themed("No Claude data directory found", style="error")
            return

        data_path = data_paths[0]
        logger = logging.getLogger(__name__)
        logger.info(f"Using data path: {data_path}")

        token_limit = _get_initial_token_limit(args, data_path)

        display_controller = DisplayController()
        display_controller.live_manager._console = console

        refresh_per_second = getattr(args, "refresh_per_second", 0.75)
        logger.info(
            f"Display refresh rate: {refresh_per_second} Hz ({1000 / refresh_per_second:.0f}ms)"
        )
        logger.info(f"Data refresh rate: {args.refresh_rate} seconds")

        live_display = display_controller.live_manager.create_live_display(
            auto_refresh=True, console=console, refresh_per_second=refresh_per_second
        )

        loading_display = display_controller.create_loading_display(
            args.plan, args.timezone
        )

        enter_alternate_screen()

        live_display_active = False

        try:
            # Enter live context and show loading screen immediately
            live_display.__enter__()
            live_display_active = True
            live_display.update(loading_display)

            orchestrator = MonitoringOrchestrator(
                update_interval=args.refresh_rate
                if hasattr(args, "refresh_rate")
                else 10,
                data_path=str(data_path),
            )
            orchestrator.set_args(args)

            # Setup monitoring callback
            def on_data_update(monitoring_data):
                """Handle data updates from orchestrator."""
                try:
                    data = monitoring_data.get("data", {})

                    logger.debug(
                        f"Display data has {len(data.get('blocks', []))} blocks"
                    )
                    if data.get("blocks"):
                        active_blocks = [b for b in data["blocks"] if b.get("isActive")]
                        logger.debug(f"Active blocks: {len(active_blocks)}")
                        if active_blocks:
                            logger.debug(
                                f"Active block tokens: {active_blocks[0].get('totalTokens', 0)}"
                            )

                    renderable = display_controller.create_data_display(
                        data, args, monitoring_data.get("token_limit", token_limit)
                    )

                    if live_display:
                        live_display.update(renderable)

                except Exception as e:
                    logger.error(f"Display update error: {e}", exc_info=True)
                    report_error(
                        exception=e,
                        component="cli_main",
                        context_name="display_update_error",
                    )

            # Register callbacks
            orchestrator.register_update_callback(on_data_update)

            # Optional: Register session change callback
            def on_session_change(event_type, session_id, session_data):
                """Handle session changes."""
                if event_type == "session_start":
                    logger.info(f"New session detected: {session_id}")
                elif event_type == "session_end":
                    logger.info(f"Session ended: {session_id}")

            orchestrator.register_session_callback(on_session_change)

            # Start monitoring
            orchestrator.start()

            # Wait for initial data
            logger.info("Waiting for initial data...")
            if not orchestrator.wait_for_initial_data(timeout=10.0):
                logger.warning("Timeout waiting for initial data")

            # Main loop - live display is already active
            while True:
                import time

                time.sleep(1)
        finally:
            # Stop monitoring first
            if "orchestrator" in locals():
                orchestrator.stop()

            # Exit live display context if it was activated
            if live_display_active:
                try:
                    live_display.__exit__(None, None, None)
                except Exception:
                    pass

    except KeyboardInterrupt:
        # Clean exit from live display if it's active
        if "live_display" in locals():
            try:
                live_display.__exit__(None, None, None)
            except Exception:
                pass
        handle_cleanup_and_exit(old_terminal_settings)
    except Exception as e:
        # Clean exit from live display if it's active
        if "live_display" in locals():
            try:
                live_display.__exit__(None, None, None)
            except Exception:
                pass
        handle_error_and_exit(old_terminal_settings, e)
    finally:
        restore_terminal(old_terminal_settings)


def _get_initial_token_limit(args, data_path: str) -> int:
    """Get initial token limit for the plan."""
    logger = logging.getLogger(__name__)
    plan = getattr(args, "plan", PlanType.PRO.value)

    # For custom plans, check if custom_limit_tokens is provided first
    if plan == "custom":
        # If custom_limit_tokens is explicitly set, use it
        if hasattr(args, "custom_limit_tokens") and args.custom_limit_tokens:
            print_themed(
                f"Using custom token limit: {args.custom_limit_tokens:,} tokens",
                style="info",
            )
            return args.custom_limit_tokens

        # Otherwise, analyze usage data to calculate P90
        print_themed("Analyzing usage data to determine cost limits...", style="info")

        try:
            # Use quick start mode for faster initial load
            usage_data = analyze_usage(
                hours_back=24,
                quick_start=True,
                use_cache=False,
                data_path=str(data_path),
            )

            if usage_data and "blocks" in usage_data:
                token_limit = get_token_limit(plan, usage_data["blocks"])

                print_themed(
                    f"P90 session limit calculated: {token_limit:,} tokens",
                    style="info",
                )

                return token_limit

        except Exception as e:
            logger.warning(f"Failed to analyze usage data: {e}")

        # Fallback to default limit
        print_themed("Using default limit as fallback", style="warning")
        return Plans.DEFAULT_TOKEN_LIMIT

    # For standard plans, just get the limit
    return get_token_limit(plan)


if __name__ == "__main__":
    sys.exit(main())
