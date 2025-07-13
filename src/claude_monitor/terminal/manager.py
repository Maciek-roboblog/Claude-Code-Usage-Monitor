"""Terminal management for Claude Monitor.
Raw mode setup, input handling, and terminal control.
"""

import logging
import sys

from claude_monitor.error_handling import report_error
from claude_monitor.terminal.themes import print_themed

logger = logging.getLogger(__name__)

try:
    import termios

    HAS_TERMIOS = True
except ImportError:
    HAS_TERMIOS = False


def setup_terminal():
    """
    Configures the terminal to raw mode by disabling echo and canonical input processing.
    
    Returns:
        old_settings: The original terminal settings if successful, or None if terminal control is unavailable or setup fails.
    """
    if not HAS_TERMIOS or not sys.stdin.isatty():
        return None

    try:
        old_settings = termios.tcgetattr(sys.stdin)
        new_settings = termios.tcgetattr(sys.stdin)
        new_settings[3] = new_settings[3] & ~(termios.ECHO | termios.ICANON)
        termios.tcsetattr(sys.stdin, termios.TCSANOW, new_settings)
        return old_settings
    except (OSError, termios.error, AttributeError):
        return None


def restore_terminal(old_settings):
    """
    Restores the terminal to its original settings and exits the alternate screen buffer.
    
    If original terminal settings are provided and terminal control is available, attempts to restore the terminal configuration. Also ensures the cursor is shown and the alternate screen buffer is exited using ANSI escape sequences.
    """
    print("\033[?25h\033[?1049l", end="", flush=True)

    if old_settings and HAS_TERMIOS and sys.stdin.isatty():
        try:
            termios.tcsetattr(sys.stdin, termios.TCSANOW, old_settings)
        except (OSError, termios.error, AttributeError) as e:
            logger.warning(f"Failed to restore terminal settings: {e}")


def enter_alternate_screen():
    """
    Switches the terminal to the alternate screen buffer, clears the display, moves the cursor to the home position, and hides the cursor.
    """
    print("\033[?1049h\033[2J\033[H\033[?25l", end="", flush=True)


def handle_cleanup_and_exit(old_terminal_settings, message="Monitoring stopped."):
    """
    Restores the terminal to its original settings, displays an informational message, and exits the program gracefully.
    
    Parameters:
        old_terminal_settings: The terminal settings to restore before exiting.
        message (str): The message to display before exiting. Defaults to "Monitoring stopped."
    """
    restore_terminal(old_terminal_settings)
    print_themed(f"\n\n{message}", style="info")
    sys.exit(0)


def handle_error_and_exit(old_terminal_settings, error):
    """
    Restores the terminal to its previous state, logs and reports the given error, writes the error message to standard error, and re-raises the exception to propagate it.
    """
    restore_terminal(old_terminal_settings)
    logger.error(f"Terminal error: {error}", exc_info=True)
    sys.stderr.write(f"\n\nError: {error}\n")

    report_error(
        exception=error,
        component="terminal_manager",
        context_name="terminal",
        context_data={"phase": "cleanup"},
        tags={"exit_type": "error_handler"},
    )
    raise error
