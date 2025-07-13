"""Terminal management for Claude Monitor.
Raw mode setup, input handling, and terminal control.
"""

import logging
import signal
import sys
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Protocol,
    TypedDict,
    Union,
    runtime_checkable,
)

from claude_monitor.error_handling import report_error
from claude_monitor.terminal.themes import print_themed

logger = logging.getLogger(__name__)

# Platform-specific imports with proper typing
try:
    import termios
    import tty

    HAS_TERMIOS = True
except ImportError:
    HAS_TERMIOS = False

# Type alias for terminal attributes - using Any for cross-platform compatibility
# This provides a clean interface while maintaining compatibility
TerminalAttributesType = Any

try:
    import msvcrt

    HAS_MSVCRT = True
except ImportError:
    HAS_MSVCRT = False


# Advanced typing for terminal operations
class TerminalCapabilities(TypedDict, total=False):
    """Terminal capability detection results."""

    has_color: bool
    has_unicode: bool
    has_truecolor: bool
    width: int
    height: int
    cursor_control: bool
    alternate_screen: bool


@runtime_checkable
class TerminalController(Protocol):
    """Protocol for terminal control operations."""

    def setup_raw_mode(self) -> Optional[TerminalAttributesType]:
        """Setup terminal raw mode."""
        ...

    def restore_settings(self, settings: Optional[TerminalAttributesType]) -> None:
        """Restore terminal settings."""
        ...

    def get_capabilities(self) -> TerminalCapabilities:
        """Get terminal capabilities."""
        ...


# Signal handler type for cross-platform compatibility
SignalHandler = Union[Callable[[int, Any], None], int, None]


class TerminalManager:
    """Advanced terminal manager with cross-platform support."""

    def __init__(self) -> None:
        self._original_settings: Optional[TerminalAttributesType] = None
        self._signal_handlers: Dict[int, SignalHandler] = {}
        self._capabilities: Optional[TerminalCapabilities] = None

    def get_capabilities(self) -> TerminalCapabilities:
        """Detect and cache terminal capabilities."""
        if self._capabilities is not None:
            return self._capabilities

        capabilities: TerminalCapabilities = {
            "has_color": self._detect_color_support(),
            "has_unicode": self._detect_unicode_support(),
            "has_truecolor": self._detect_truecolor_support(),
            "cursor_control": HAS_TERMIOS,
            "alternate_screen": HAS_TERMIOS,
        }

        # Get terminal dimensions
        try:
            if HAS_TERMIOS:
                import shutil

                size = shutil.get_terminal_size()
                capabilities["width"] = size.columns
                capabilities["height"] = size.lines
            else:
                capabilities["width"] = 80
                capabilities["height"] = 24
        except (OSError, AttributeError):
            capabilities["width"] = 80
            capabilities["height"] = 24

        self._capabilities = capabilities
        return capabilities

    def _detect_color_support(self) -> bool:
        """Detect if terminal supports colors."""
        import os

        return (
            os.environ.get("COLORTERM") is not None
            or "color" in os.environ.get("TERM", "").lower()
            or os.environ.get("TERM") in {"xterm-256color", "screen-256color"}
        )

    def _detect_unicode_support(self) -> bool:
        """Detect if terminal supports Unicode."""
        import os

        encoding = os.environ.get("LANG", "").lower()
        return "utf" in encoding or sys.stdout.encoding.lower().startswith("utf")

    def _detect_truecolor_support(self) -> bool:
        """Detect if terminal supports 24-bit colors."""
        import os

        return os.environ.get("COLORTERM") in {
            "truecolor",
            "24bit",
        } or "RGB" in os.environ.get("TERM", "")


def setup_terminal() -> Optional[TerminalAttributesType]:
    """Setup terminal for raw mode to prevent input interference.

    Returns:
        Terminal settings for restoration, or None if setup failed.
    """
    if not HAS_TERMIOS or not sys.stdin.isatty():
        return None

    try:
        old_settings = termios.tcgetattr(sys.stdin)
        new_settings = termios.tcgetattr(sys.stdin)

        # Modify local modes for raw input - termios uses specific indices
        new_settings[3] = new_settings[3] & ~(termios.ECHO | termios.ICANON)

        # Apply settings immediately
        termios.tcsetattr(sys.stdin, termios.TCSANOW, new_settings)
        return old_settings
    except (OSError, termios.error, AttributeError) as e:
        logger.debug(f"Failed to setup terminal raw mode: {e}")
        return None


def restore_terminal(old_settings: Optional[TerminalAttributesType]) -> None:
    """Restore terminal to original settings with enhanced error handling.

    Args:
        old_settings: Previously saved terminal attributes to restore.
    """
    # Restore cursor and exit alternate screen first
    _restore_terminal_display()

    if old_settings and HAS_TERMIOS and sys.stdin.isatty():
        try:
            termios.tcsetattr(sys.stdin, termios.TCSANOW, old_settings)
            logger.debug("Terminal settings restored successfully")
        except (OSError, termios.error, AttributeError) as e:
            logger.warning(f"Failed to restore terminal settings: {e}")
            # Attempt graceful fallback
            _attempt_terminal_reset()


def _restore_terminal_display() -> None:
    """Restore terminal display state."""
    try:
        # Show cursor and exit alternate screen
        sys.stdout.write("\033[?25h\033[?1049l")
        sys.stdout.flush()
    except (OSError, AttributeError) as e:
        logger.debug(f"Failed to restore terminal display: {e}")


def _attempt_terminal_reset() -> None:
    """Attempt to reset terminal using system commands as fallback."""
    try:
        import subprocess

        subprocess.run(["reset"], check=False, capture_output=True, timeout=1.0)
    except (OSError, subprocess.TimeoutExpired, FileNotFoundError):
        # Reset command not available or failed - continue gracefully
        pass


def enter_alternate_screen() -> None:
    """Enter alternate screen buffer, clear and hide cursor."""
    print("\033[?1049h\033[2J\033[H\033[?25l", end="", flush=True)


# Signal handling for graceful shutdown
class SignalManager:
    """Advanced signal handling for terminal applications."""

    def __init__(
        self, terminal_settings: Optional[TerminalAttributesType] = None
    ) -> None:
        self._terminal_settings = terminal_settings
        self._original_handlers: Dict[int, SignalHandler] = {}

    def setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        signals_to_handle: List[int] = [signal.SIGINT, signal.SIGTERM]

        # Add SIGWINCH for window resize if available
        if hasattr(signal, "SIGWINCH"):
            signals_to_handle.append(signal.SIGWINCH)

        for sig in signals_to_handle:
            try:
                original_handler = signal.signal(sig, self._signal_handler)
                self._original_handlers[sig] = original_handler
            except (OSError, ValueError) as e:
                logger.debug(f"Cannot setup handler for signal {sig}: {e}")

    def _signal_handler(self, signum: int, frame: Any) -> None:
        """Handle received signals gracefully."""
        if signum == signal.SIGINT:
            handle_cleanup_and_exit(self._terminal_settings, "Interrupted by user.")
        elif signum == signal.SIGTERM:
            handle_cleanup_and_exit(self._terminal_settings, "Terminated.")
        elif hasattr(signal, "SIGWINCH") and signum == signal.SIGWINCH:
            # Handle window resize - could trigger display refresh
            logger.debug("Terminal window resized")

    def restore_signal_handlers(self) -> None:
        """Restore original signal handlers."""
        for sig, handler in self._original_handlers.items():
            try:
                signal.signal(sig, handler)
            except (OSError, ValueError) as e:
                logger.debug(f"Cannot restore handler for signal {sig}: {e}")


def handle_cleanup_and_exit(
    old_terminal_settings: Optional[TerminalAttributesType],
    message: str = "Monitoring stopped.",
) -> None:
    """Handle cleanup and exit gracefully with enhanced error handling.

    Args:
        old_terminal_settings: Terminal settings to restore.
        message: Exit message to display.
    """
    try:
        restore_terminal(old_terminal_settings)
        print_themed(f"\n\n{message}", style="info")
    except Exception as e:
        # Ensure we can still exit even if restoration fails
        logger.error(f"Error during cleanup: {e}")
        sys.stderr.write(f"\n\n{message}\n")
    finally:
        sys.exit(0)


def handle_error_and_exit(
    old_terminal_settings: Optional[TerminalAttributesType], error: Exception
) -> None:
    """Handle error cleanup and exit with comprehensive error reporting.

    Args:
        old_terminal_settings: Terminal settings to restore.
        error: Exception that caused the error.
    """
    try:
        restore_terminal(old_terminal_settings)
    except Exception as restore_error:
        logger.error(
            f"Failed to restore terminal during error handling: {restore_error}"
        )

    logger.error(f"Terminal error: {error}", exc_info=True)
    sys.stderr.write(f"\n\nError: {error}\n")

    report_error(
        exception=error,
        component="terminal_manager",
        context_name="terminal",
        context_data={
            "phase": "cleanup",
            "has_termios": HAS_TERMIOS,
            "has_msvcrt": HAS_MSVCRT,
            "is_tty": sys.stdin.isatty() if hasattr(sys.stdin, "isatty") else False,
        },
        tags={"exit_type": "error_handler"},
    )
    raise error


# Performance optimization for terminal operations
class TerminalOptimizer:
    """Performance optimization for terminal operations."""

    @staticmethod
    def batch_terminal_writes(operations: List[str]) -> None:
        """Batch multiple terminal operations for better performance.

        Args:
            operations: List of ANSI escape sequences to write.
        """
        if not operations:
            return

        try:
            # Combine all operations into a single write
            combined = "".join(operations)
            sys.stdout.write(combined)
            sys.stdout.flush()
        except (OSError, AttributeError) as e:
            logger.debug(f"Failed to batch terminal writes: {e}")
            # Fallback to individual writes
            for operation in operations:
                try:
                    sys.stdout.write(operation)
                except (OSError, AttributeError):
                    continue
            try:
                sys.stdout.flush()
            except (OSError, AttributeError):
                pass

    @staticmethod
    def optimize_cursor_movement(x: int, y: int) -> str:
        """Generate optimized cursor movement sequence.

        Args:
            x: Target column (0-based).
            y: Target row (0-based).

        Returns:
            Optimized ANSI escape sequence for cursor movement.
        """
        # Use direct positioning for efficiency
        return f"\033[{y + 1};{x + 1}H"
