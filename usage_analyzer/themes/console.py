"""Theme-aware Rich console management."""

from typing import Optional
from rich.console import Console
from .detector import ThemeDetector
from .themes import get_theme, ThemeType
from .config import ThemeConfig

# Global console instance
_console: Optional[Console] = None
_current_theme: Optional[ThemeType] = None


def get_themed_console(force_theme: Optional[ThemeType] = None) -> Console:
    """Get a theme-aware Rich console instance.
    
    Args:
        force_theme: Force a specific theme (overrides detection)
        
    Returns:
        Configured Rich Console instance
    """
    global _console, _current_theme
    
    # Determine theme to use
    if force_theme is not None:
        theme_to_use = force_theme
    else:
        # Check user config first
        config = ThemeConfig()
        user_preference = config.get_user_theme_preference()
        
        if user_preference and user_preference != ThemeType.AUTO:
            theme_to_use = user_preference
        else:
            # Auto-detect theme
            detector = ThemeDetector()
            theme_to_use = detector.detect_theme()
    
    # Create or update console if theme changed
    if _console is None or _current_theme != theme_to_use:
        theme = get_theme(theme_to_use)
        _console = Console(theme=theme, force_terminal=True)
        _current_theme = theme_to_use
    
    return _console


def print_themed(
    *args,
    style: Optional[str] = None,
    end: str = "\n",
    **kwargs
) -> None:
    """Themed print function using Rich console.
    
    Args:
        *args: Arguments to print
        style: Rich style to apply
        end: String appended after the last value
        **kwargs: Additional keyword arguments for Rich print
    """
    console = get_themed_console()
    console.print(*args, style=style, end=end, **kwargs)


def get_current_theme() -> Optional[ThemeType]:
    """Get the currently active theme type.
    
    Returns:
        Current theme type or None if not initialized
    """
    return _current_theme


def reset_console() -> None:
    """Reset the console instance (forces re-detection on next use)."""
    global _console, _current_theme
    _console = None
    _current_theme = None


def debug_theme_info() -> dict:
    """Get comprehensive debug information about current theme setup.
    
    Returns:
        Dictionary with debug information
    """
    detector = ThemeDetector()
    config = ThemeConfig()
    
    return {
        'current_theme': _current_theme.value if _current_theme else None,
        'console_initialized': _console is not None,
        'detector_info': detector.get_debug_info(),
        'config_info': config.get_debug_info(),
        'rich_available': True,
    }