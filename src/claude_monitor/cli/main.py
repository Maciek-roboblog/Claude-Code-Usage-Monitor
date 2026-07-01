"""Simplified CLI entry point using pydantic-settings."""

import argparse
import contextlib
import json
import logging
import os
import signal
import sys
import time
import traceback
from pathlib import Path
from typing import Any, Callable, Dict, List, NoReturn, Optional, Union

from rich.console import Console

from claude_monitor import __version__
from claude_monitor.cli.bootstrap import (
    ensure_directories,
    init_timezone,
    setup_environment,
    setup_logging,
)
from claude_monitor.core.plans import Plans, PlanType, get_token_limit
from claude_monitor.core.settings import Settings
from claude_monitor.data.aggregator import UsageAggregator
from claude_monitor.data.analysis import analyze_usage
from claude_monitor.data.reports import build_warehouse_report, format_report_csv
from claude_monitor.data.warehouse import UsageWarehouse, default_warehouse_path
from claude_monitor.error_handling import report_error
from claude_monitor.monitoring.orchestrator import MonitoringOrchestrator
from claude_monitor.output import (
    build_snapshot,
    format_compact,
    format_json,
    format_terminal_title,
    format_text,
)
from claude_monitor.output.api_usage import read_api_limits
from claude_monitor.output.official import (
    capture_statusline,
    format_statusline,
    read_official_limits,
)
from claude_monitor.output.state import default_state_path, write_state_file
from claude_monitor.terminal.manager import (
    enter_alternate_screen,
    handle_cleanup_and_exit,
    handle_error_and_exit,
    restore_terminal,
    set_terminal_title,
    setup_terminal,
)
from claude_monitor.terminal.themes import get_themed_console, print_themed
from claude_monitor.ui.display_controller import DisplayController
from claude_monitor.ui.table_views import TableViewsController
from claude_monitor.utils.wsl import WSLDetector

# Type aliases for CLI callbacks
DataUpdateCallback = Callable[[Dict[str, Any]], None]
SessionChangeCallback = Callable[[str, str, Optional[Dict[str, Any]]], None]
WAREHOUSE_REPORT_VIEWS = {"entries", "sessions", "burn-rate"}


def get_standard_claude_paths() -> List[str]:
    """Get list of standard Claude data directory paths to check."""
    return ["~/.claude/projects", "~/.config/claude/projects"]


def _env_claude_paths() -> List[str]:
    """Data paths derived from CLAUDE_CONFIG_DIR (comma-separated dirs allowed)."""
    raw = os.environ.get("CLAUDE_CONFIG_DIR", "")
    return [
        str(Path(part.strip()) / "projects") for part in raw.split(",") if part.strip()
    ]


_WSL_DETECTOR: Optional[WSLDetector] = None


def _get_wsl_detector() -> WSLDetector:
    global _WSL_DETECTOR
    if _WSL_DETECTOR is None:
        _WSL_DETECTOR = WSLDetector()
    return _WSL_DETECTOR


def _wsl_claude_paths() -> List[str]:
    return _get_wsl_detector().data_paths()


def _candidate_claude_paths(custom_paths: Optional[List[str]] = None) -> List[str]:
    if custom_paths:
        return [str(path) for path in custom_paths]
    return _env_claude_paths() + get_standard_claude_paths() + _wsl_claude_paths()


def discover_claude_data_paths(custom_paths: Optional[List[str]] = None) -> List[Path]:
    """Discover all available Claude data directories.

    When no custom paths are given, CLAUDE_CONFIG_DIR (if set) is checked before the
    standard locations, so a configured directory takes precedence.

    Args:
        custom_paths: Optional list of custom paths to check instead of standard ones

    Returns:
        List of Path objects for existing Claude data directories
    """
    paths_to_check = _candidate_claude_paths(custom_paths)

    discovered_paths: List[Path] = []
    seen: set[Path] = set()

    for path_str in paths_to_check:
        path = Path(path_str).expanduser().resolve()
        if path in seen:
            continue
        seen.add(path)
        if path.exists() and path.is_dir():
            discovered_paths.append(path)

    return discovered_paths


def _no_data_diagnostic(searched_paths: List[str]) -> str:
    """Build a clear 'no data' message that names where we looked (issue #110)."""
    locations = "\n".join(f"  - {Path(p).expanduser()}" for p in searched_paths)
    return (
        "No Claude data directory found.\n\n"
        f"Searched:\n{locations}\n\n"
        "Make sure you have used Claude Code at least once so it has written "
        "usage logs (JSONL), then run claude-monitor again."
    )


def _maybe_write_state(args: argparse.Namespace, snapshot: dict) -> bool:
    """Write the snapshot to the state file if --write-state is set (issue #184).

    Returns True on success (or when not requested); False if the write failed.
    The live loop ignores the result (a transient write error must not break
    monitoring); one-shot mode surfaces it so a requested write isn't silently
    dropped.
    """
    if not getattr(args, "write_state", False):
        return True
    try:
        path = (
            Path(args.state_file)
            if getattr(args, "state_file", None)
            else default_state_path()
        )
        write_state_file(snapshot, path)
        return True
    except Exception as e:
        logging.getLogger(__name__).warning(f"Failed to write state file: {e}")
        return False


def _maybe_set_terminal_title(args: argparse.Namespace, snapshot: dict) -> None:
    if not getattr(args, "set_terminal_title", False):
        return
    template = getattr(args, "title_format", "{pct}% {plan}")
    set_terminal_title(format_terminal_title(snapshot, template))


def _has_fresh_limit_percentage(limits: Optional[dict]) -> bool:
    if not limits or limits.get("stale"):
        return False
    for key in ("five_hour", "seven_day"):
        window = limits.get(key)
        if isinstance(window, dict) and window.get("used_percentage") is not None:
            return True
    return False


def _read_optional_api_limits(
    args: argparse.Namespace, official: Optional[dict], now_epoch: int
) -> Optional[dict]:
    if not getattr(args, "api", False):
        return None
    if _has_fresh_limit_percentage(official):
        return None

    cache_file = getattr(args, "api_cache_file", None)
    ttl_seconds = getattr(args, "api_ttl_seconds", 180)
    return read_api_limits(
        enabled=True,
        cache_path=Path(cache_file) if cache_file else None,
        now_epoch=now_epoch,
        ttl_seconds=ttl_seconds,
    )


def _effective_token_limit(args: argparse.Namespace, base_limit: int) -> int:
    """Resolve the token limit to display.

    An explicit ``--custom-limit-tokens`` always wins over a computed base
    (the orchestrator recomputes a P90 estimate for custom plans and would
    otherwise mask the user's chosen limit). Shared by the one-shot and live
    paths so ``--compact`` shows the same denominator either way.
    """
    if getattr(args, "plan", None) == "custom" and getattr(
        args, "custom_limit_tokens", None
    ):
        return int(args.custom_limit_tokens)
    return base_limit


def _run_once(args: argparse.Namespace) -> int:
    """One-shot mode: pull usage once, print a snapshot, and exit (issue #126).

    Returns an automation-friendly exit code: 0 ok, 10 near limit, 11 limit hit,
    20 no active session, 30 no data / config error.
    """
    configured_paths = getattr(args, "data_paths", [])
    data_paths = discover_claude_data_paths(configured_paths)
    if not data_paths:
        print(
            _no_data_diagnostic(_candidate_claude_paths(configured_paths)),
            file=sys.stderr,
        )
        return 30

    data_path_values = [str(path) for path in data_paths]
    args.data_paths = data_path_values
    args.data_path = data_path_values[0]

    orchestrator = MonitoringOrchestrator(
        update_interval=getattr(args, "refresh_rate", 10), data_path=data_path_values
    )
    orchestrator.set_args(args)
    try:
        monitoring_data = orchestrator.force_refresh()
    finally:
        orchestrator.stop()

    if monitoring_data is None:
        print("No usage data available yet.", file=sys.stderr)
        return 30

    data = monitoring_data.get("data", {}) or {}
    blocks = data.get("blocks", []) or []
    # Honor an explicit --custom-limit-tokens, mirroring the live path; otherwise
    # use the orchestrator's token_limit or a P90 estimate.
    token_limit = _effective_token_limit(
        args, monitoring_data.get("token_limit") or get_token_limit(args.plan, blocks)
    )

    now_epoch = int(time.time())
    official = read_official_limits(now_epoch=now_epoch)
    api_limits = _read_optional_api_limits(args, official, now_epoch)
    snapshot = build_snapshot(
        data, args, token_limit, official=official, api_limits=api_limits
    )
    _maybe_set_terminal_title(args, snapshot)
    output = getattr(args, "output", "rich")
    if output == "json":
        print(format_json(snapshot))
    elif output == "text":
        print(format_text(snapshot))
    elif output == "csv":
        print(
            "CSV output is available for warehouse report views "
            "(--view entries|sessions|burn-rate).",
            file=sys.stderr,
        )
        return 30
    elif getattr(args, "compact", False):
        print(format_compact(snapshot))
    else:
        console = get_themed_console(
            force_theme=args.theme.lower() if getattr(args, "theme", None) else None
        )
        console.print(
            DisplayController().create_data_display(
                data, args, token_limit, snapshot=snapshot
            )
        )

    if not _maybe_write_state(args, snapshot):
        print("Failed to write state file (see logs)", file=sys.stderr)
        return 30
    return snapshot["status"]["code"]


def _run_statusline() -> int:
    """Capture official ``rate_limits`` from Claude Code's statusline stdin and
    print the status bar line (trust keystone producer).

    Wire it up in Claude Code ``settings.json``::

        "statusLine": {"type": "command", "command": "claude-monitor --statusline"}

    Must be fast and never raise — a crash here would blank the user's status bar.
    """
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except Exception:  # unreadable stdin or non-JSON: degrade, don't crash
        payload = {}
    if not isinstance(payload, dict):
        payload = {}

    capture = None
    try:
        capture = capture_statusline(payload, now_epoch=int(time.time()))
    except Exception as e:  # a write error must not blank the status bar
        logging.getLogger(__name__).debug(f"statusline capture failed: {e}")

    try:
        line = format_statusline(payload, capture)
    except Exception:  # never let a formatting edge case blank the bar
        line = "claude-monitor"
    print(line)
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point with direct pydantic-settings integration."""
    if argv is None:
        argv = sys.argv[1:]

    if "--version" in argv or "-v" in argv:
        print(f"claude-monitor {__version__}")
        return 0

    # The statusline hook runs on every Claude Code refresh (sub-second), so it
    # short-circuits before the heavy settings/logging/timezone setup.
    if "--statusline" in argv:
        return _run_statusline()

    once_mode = "--once" in argv

    env_error = validate_cli_environment()
    if env_error:
        print(env_error, file=sys.stderr)
        return 30 if once_mode else 1

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

        if settings.view in WAREHOUSE_REPORT_VIEWS:
            return _run_warehouse_report(args)

        if settings.once:
            return _run_once(args)

        _run_monitoring(args)

        return 0

    except KeyboardInterrupt:
        print("\n\nMonitoring stopped by user.")
        return 0
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Monitor failed: {e}", exc_info=True)
        traceback.print_exc()
        return 30 if once_mode else 1


def _run_warehouse_report(args: argparse.Namespace) -> int:
    """Run a warehouse-backed report/export view."""
    output = getattr(args, "output", "json")
    if output not in {"json", "csv"}:
        print(
            "Warehouse report views require --output json or --output csv.",
            file=sys.stderr,
        )
        return 30

    warehouse_path = (
        Path(args.warehouse_file)
        if getattr(args, "warehouse_file", None)
        else default_warehouse_path()
    )
    try:
        report = build_warehouse_report(
            UsageWarehouse(warehouse_path),
            getattr(args, "view", "entries"),
            plan=getattr(args, "plan", "custom"),
        )
    except (OSError, ValueError, TypeError) as e:
        print(f"Failed to build warehouse report: {e}", file=sys.stderr)
        return 30

    if output == "csv":
        print(format_report_csv(report), end="")
    else:
        print(format_json(report))
    return 0


def _run_monitoring(args: argparse.Namespace) -> None:
    """Main monitoring implementation without facade."""
    view_mode = getattr(args, "view", "realtime")

    if hasattr(args, "theme") and args.theme:
        console = get_themed_console(force_theme=args.theme.lower())
    else:
        console = get_themed_console()

    old_terminal_settings = setup_terminal()
    live_display_active: bool = False

    try:
        configured_paths = getattr(args, "data_paths", [])
        data_paths: List[Path] = discover_claude_data_paths(configured_paths)
        if not data_paths:
            print_themed(
                _no_data_diagnostic(_candidate_claude_paths(configured_paths)),
                style="error",
            )
            return

        data_path_values = [str(path) for path in data_paths]
        args.data_paths = data_path_values
        args.data_path = data_path_values[0]
        data_path: Union[Path, List[str]] = data_path_values
        logger = logging.getLogger(__name__)
        logger.info(f"Using data paths: {data_path_values}")

        # Handle different view modes
        if view_mode in ["daily", "monthly"]:
            _run_table_view(args, data_path, view_mode, console)
            return

        token_limit: int = _get_initial_token_limit(args, data_path)

        display_controller = DisplayController()
        display_controller.live_manager._console = console

        refresh_per_second: float = getattr(args, "refresh_per_second", 0.75)
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
                update_interval=(
                    args.refresh_rate if hasattr(args, "refresh_rate") else 10
                ),
                data_path=data_path_values,
            )
            orchestrator.set_args(args)

            # Setup monitoring callback
            def on_data_update(monitoring_data: Dict[str, Any]) -> None:
                """Handle data updates from orchestrator."""
                try:
                    data: Dict[str, Any] = monitoring_data.get("data", {})
                    blocks: List[Dict[str, Any]] = data.get("blocks", [])

                    logger.debug(f"Display data has {len(blocks)} blocks")
                    if blocks:
                        active_blocks: List[Dict[str, Any]] = [
                            b for b in blocks if b.get("isActive")
                        ]
                        logger.debug(f"Active blocks: {len(active_blocks)}")
                        if active_blocks:
                            total_tokens: int = active_blocks[0].get("totalTokens", 0)
                            logger.debug(f"Active block tokens: {total_tokens}")

                    # `.get(key, default)` returns None if the key is present but
                    # None, so fall back explicitly to the last known good limit.
                    reported_limit = monitoring_data.get("token_limit")
                    token_limit_now = _effective_token_limit(
                        args, reported_limit if reported_limit else token_limit
                    )
                    now_epoch = int(time.time())
                    official = read_official_limits(now_epoch=now_epoch)
                    api_limits = _read_optional_api_limits(args, official, now_epoch)
                    snapshot = build_snapshot(
                        data,
                        args,
                        token_limit_now,
                        official=official,
                        api_limits=api_limits,
                    )

                    _maybe_set_terminal_title(args, snapshot)

                    if getattr(args, "compact", False):
                        renderable = format_compact(snapshot)
                    else:
                        renderable = display_controller.create_data_display(
                            data, args, token_limit_now, snapshot=snapshot
                        )

                    if live_display:
                        live_display.update(renderable)

                    if getattr(args, "write_state", False):
                        _maybe_write_state(args, snapshot)

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
            def on_session_change(
                event_type: str, session_id: str, session_data: Optional[Dict[str, Any]]
            ) -> None:
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
            # Use signal.pause() for more efficient waiting
            try:
                signal.pause()
            except AttributeError:
                # Fallback for Windows which doesn't support signal.pause()
                while True:
                    time.sleep(1)
        finally:
            # Stop monitoring first
            if "orchestrator" in locals():
                orchestrator.stop()

            # Exit live display context if it was activated
            if live_display_active:
                with contextlib.suppress(Exception):
                    live_display.__exit__(None, None, None)

    except KeyboardInterrupt:
        # Clean exit from live display if it's active
        if "live_display" in locals():
            with contextlib.suppress(Exception):
                live_display.__exit__(None, None, None)
        handle_cleanup_and_exit(old_terminal_settings)
    except Exception as e:
        # Clean exit from live display if it's active
        if "live_display" in locals():
            with contextlib.suppress(Exception):
                live_display.__exit__(None, None, None)
        handle_error_and_exit(old_terminal_settings, e)
    finally:
        restore_terminal(old_terminal_settings)


def _get_initial_token_limit(
    args: argparse.Namespace, data_path: Union[str, Path, List[str]]
) -> int:
    """Get initial token limit for the plan."""
    logger = logging.getLogger(__name__)
    plan: str = getattr(args, "plan", PlanType.PRO.value)

    # For custom plans, check if custom_limit_tokens is provided first
    if plan == "custom":
        # If custom_limit_tokens is explicitly set, use it
        if hasattr(args, "custom_limit_tokens") and args.custom_limit_tokens:
            custom_limit = int(args.custom_limit_tokens)
            print_themed(
                f"Using custom token limit: {custom_limit:,} tokens",
                style="info",
            )
            return custom_limit

        # Otherwise, analyze usage data to calculate P90
        print_themed("Analyzing usage data to determine cost limits...", style="info")

        try:
            # Use quick start mode for faster initial load
            usage_data: Optional[Dict[str, Any]] = analyze_usage(
                hours_back=96 * 2,
                quick_start=False,
                use_cache=False,
                data_path=data_path,
                filter_models=getattr(args, "filter_models", "all"),
            )

            if usage_data and "blocks" in usage_data:
                blocks: List[Dict[str, Any]] = usage_data["blocks"]
                token_limit: int = get_token_limit(plan, blocks)

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


def handle_application_error(
    exception: Exception,
    component: str = "cli_main",
    exit_code: int = 1,
) -> NoReturn:
    """Handle application-level errors with proper logging and exit.

    Args:
        exception: The exception that occurred
        component: Component where the error occurred
        exit_code: Exit code to use when terminating
    """
    logger = logging.getLogger(__name__)

    # Log the error with traceback
    logger.error(f"Application error in {component}: {exception}", exc_info=True)

    # Report to error handling system
    from claude_monitor.error_handling import report_application_startup_error

    report_application_startup_error(
        exception=exception,
        component=component,
        additional_context={
            "exit_code": exit_code,
            "args": sys.argv,
        },
    )

    # Print user-friendly error message
    print(f"\nError: {exception}", file=sys.stderr)
    print("For more details, check the log files.", file=sys.stderr)

    sys.exit(exit_code)


def validate_cli_environment() -> Optional[str]:
    """Validate the runtime environment, returning an error message if unsupported.

    Returns:
        A user-facing message if the environment is unsupported, otherwise None.
    """
    if sys.version_info < (3, 9):
        return (
            "Python 3.9+ is required, but you are running "
            f"{sys.version_info[0]}.{sys.version_info[1]}. "
            "Install a newer Python, e.g.: uv tool install claude-monitor --python 3.12"
        )
    return None


def _run_table_view(
    args: argparse.Namespace,
    data_path: Union[Path, List[str]],
    view_mode: str,
    console: Console,
) -> None:
    """Run table view mode (daily/monthly)."""
    logger = logging.getLogger(__name__)

    try:
        # Create aggregator with appropriate mode
        aggregator = UsageAggregator(
            data_path=data_path,
            aggregation_mode=view_mode,
            timezone=args.timezone,
            reset_hour=getattr(args, "reset_hour", None),
            filter_models=getattr(args, "filter_models", "all"),
            date_from=getattr(args, "date_from", None),
            date_to=getattr(args, "date_to", None),
        )

        # Create table controller
        controller = TableViewsController(console=console)

        # Get aggregated data
        logger.info(f"Loading {view_mode} usage data...")
        aggregated_data = aggregator.aggregate()

        if not aggregated_data:
            print_themed(f"No usage data found for {view_mode} view", style="warning")
            return

        # Display the table
        controller.display_aggregated_view(
            data=aggregated_data,
            view_mode=view_mode,
            timezone=args.timezone,
            plan=args.plan,
            token_limit=_get_initial_token_limit(args, data_path),
            date_format=getattr(args, "date_format", None),
            abbreviate_tokens=getattr(args, "abbreviate_tokens", False),
            sparklines=getattr(args, "sparklines", False),
        )

        # Wait for user to press Ctrl+C
        print_themed("\nPress Ctrl+C to exit", style="info")
        try:
            # Use signal.pause() for more efficient waiting
            try:
                signal.pause()
            except AttributeError:
                # Fallback for Windows which doesn't support signal.pause()
                while True:
                    time.sleep(1)
        except KeyboardInterrupt:
            print_themed("\nExiting...", style="info")

    except Exception as e:
        logger.error(f"Error in table view: {e}", exc_info=True)
        print_themed(f"Error displaying {view_mode} view: {e}", style="error")


if __name__ == "__main__":
    sys.exit(main())
