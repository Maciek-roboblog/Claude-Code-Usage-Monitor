"""Terminal management for Claude Monitor.
Raw mode setup, input handling, and terminal control.
"""

import logging
import sys
from typing import Any, List, Optional, Union

from claude_monitor.error_handling import report_error
from claude_monitor.terminal.themes import print_themed

logger: logging.Logger = logging.getLogger(__name__)

try:
    import termios

    HAS_TERMIOS: bool = True
except ImportError:
    HAS_TERMIOS: bool = False


def setup_terminal() -> Optional[List[Any]]:
    """Setup terminal for raw mode to prevent input interference.

    Returns:
        Terminal settings list that can be used to restore terminal state,
        or None if terminal setup is not supported or fails.
    """
    if not HAS_TERMIOS or not sys.stdin.isatty():
        return None

    try:
        old_settings: List[Any] = termios.tcgetattr(sys.stdin)
        new_settings: List[Any] = termios.tcgetattr(sys.stdin)
        new_settings[3] = new_settings[3] & ~(termios.ECHO | termios.ICANON)
        termios.tcsetattr(sys.stdin, termios.TCSANOW, new_settings)
        return old_settings
    except (OSError, termios.error, AttributeError):
        return None


def restore_terminal(old_settings: Optional[List[Any]]) -> None:
    """Restore terminal to original settings.

    Args:
        old_settings: Terminal settings to restore, or None if no settings to restore.
    """
    # Send ANSI escape sequences to show cursor and exit alternate screen
    print("\033[?25h\033[?1049l", end="", flush=True)

    if old_settings and HAS_TERMIOS and sys.stdin.isatty():
        try:
            termios.tcsetattr(sys.stdin, termios.TCSANOW, old_settings)
        except (OSError, termios.error, AttributeError) as e:
            logger.warning(f"Failed to restore terminal settings: {e}")


def enter_alternate_screen() -> None:
    """Enter alternate screen buffer, clear and hide cursor.

    Sends ANSI escape sequences to:
    - Enter alternate screen buffer (\033[?1049h)
    - Clear screen (\033[2J)
    - Move cursor to home position (\033[H)
    - Hide cursor (\033[?25l)
    """
    print("\033[?1049h\033[2J\033[H\033[?25l", end="", flush=True)


def handle_cleanup_and_exit(
    old_terminal_settings: Optional[List[Any]], message: str = "Monitoring stopped."
) -> None:
    """Handle cleanup and exit gracefully.

    Args:
        old_terminal_settings: Terminal settings to restore before exit.
        message: Exit message to display to user.
    """
    restore_terminal(old_terminal_settings)
    print_themed(f"\n\n{message}", style="info")
    sys.exit(0)


def handle_error_and_exit(
    old_terminal_settings: Optional[List[Any]], error: Union[Exception, str]
) -> None:
    """Handle error cleanup and exit.

    Args:
        old_terminal_settings: Terminal settings to restore before exit.
        error: Exception or error message that caused the exit.

    Raises:
        The original error after cleanup and reporting.
    """
    restore_terminal(old_terminal_settings)
    logger.error(f"Terminal error: {error}")
    sys.stderr.write(f"\n\nError: {error}\n")

    report_error(
        exception=error,
        component="terminal_manager",
        context_name="terminal",
        context_data={"phase": "cleanup"},
        tags={"exit_type": "error_handler"},
    )
    raise error
