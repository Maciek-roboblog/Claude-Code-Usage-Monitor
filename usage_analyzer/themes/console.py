"""Theme-aware Rich console management."""

from typing import Optional

from rich.console import Console

from .config import ThemeConfig
from .detector import ThemeDetector
from .themes import ThemeType, get_theme

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
    message_key: Optional[str] = None,
    message: Optional[str] = None,
    style: Optional[str] = None,
    end: str = "\n",
    **format_kwargs,
) -> None:
    """Themed print function with i18n support using Rich console.

    Args:
        message_key: Clé de traduction i18n (ex: "error.data_fetch_failed")
        message: Message direct (pour compatibilité descendante)
        style: Rich style to apply
        end: String appended after the last value
        **format_kwargs: Variables pour formatage de la chaîne traduite

    Examples:
        # Mode i18n avec traduction
        print_themed(message_key="error.data_fetch_failed", style="error")

        # Mode i18n avec variables
        print_themed(
            message_key="notification.limit_exceeded",
            style="warning",
            plan="PRO",
            limit="100,000"
        )

        # Mode legacy (compatibilité descendante)
        print_themed(message="Hello world", style="info")
    """
    console = get_themed_console()

    # Déterminer le texte à afficher
    if message_key:
        # Mode i18n : traduction + formatage
        try:
            from ..i18n import _

            translated = _(message_key)

            if format_kwargs:
                formatted_text = translated.format(**format_kwargs)
            else:
                formatted_text = translated

        except (ImportError, KeyError) as e:
            # Fallback en cas d'erreur i18n
            formatted_text = f"[i18n error: {message_key}]"
            console.print(
                f"Warning: Translation failed for '{message_key}': {e}", style="dim red"
            )
    else:
        # Mode legacy : message direct
        formatted_text = message or ""

    # Affichage avec style Rich
    console.print(formatted_text, style=style, end=end)


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
        "current_theme": _current_theme.value if _current_theme else None,
        "console_initialized": _console is not None,
        "detector_info": detector.get_debug_info(),
        "config_info": config.get_debug_info(),
        "rich_available": True,
    }
