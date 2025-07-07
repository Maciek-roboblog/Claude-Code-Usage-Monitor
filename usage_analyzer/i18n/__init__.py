"""
Internationalization module for Claude Usage Monitor.

This module manages gettext configuration, locale detection,
and translation initialization.
"""

import gettext
import locale
import os
from pathlib import Path
from typing import Callable, Optional, Tuple, cast

from .message_keys import PLURAL

# Configuration
APP_DOMAIN = "claude_monitor"
LOCALE_DIR = Path(__file__).parent.parent / "locales"

# Global variables for translation functions
_translation_functions: Optional[Tuple[Callable[[str], str], Callable[..., str]]] = None


def get_system_locale() -> str:
    """
    Detects the system locale with robust fallback.

    Returns:
        Locale code (e.g., 'fr_FR', 'en_US')
    """
    try:
        # Try to detect via locale.getdefaultlocale()
        system_locale = locale.getdefaultlocale()[0]
        if system_locale:
            return system_locale
    except (ValueError, TypeError, AttributeError):
        pass

    # Fallback to environment variables
    for env_var in ["LC_ALL", "LC_MESSAGES", "LANG"]:
        env_locale = os.environ.get(env_var)
        if env_locale and env_locale != "C":
            # Clean the variable (e.g., 'fr_FR.UTF-8' -> 'fr_FR')
            return env_locale.split(".")[0]

    # Final fallback to American English
    return "en_US"


def init_translations(
    lang_code: Optional[str] = None,
) -> Tuple[Callable[[str], str], Callable[..., str]]:
    """
    Initializes gettext and returns translation functions.

    Args:
        lang_code: Explicit language code (e.g., 'fr_FR').
                   If None, auto-detect.

    Returns:
        Tuple containing (function _, function ngettext)
    """
    global _translation_functions

    if not lang_code:
        lang_code = get_system_locale()

    try:
        # Try to load the translation
        translation = gettext.translation(
            APP_DOMAIN,
            localedir=str(LOCALE_DIR),
            languages=[lang_code],
            fallback=True,  # CRUCIAL: fallback to msgid if missing
        )

        # Get translation functions
        gettext_func = translation.gettext
        # Cast to expected type to maintain type safety
        ngettext_func = cast(Callable[..., str], translation.ngettext)

    except (OSError, FileNotFoundError, gettext.GNUTranslations, AttributeError) as e:
        # On error, use default (pass-through) functions
        import logging

        logging.warning(f"Failed to load translations for {lang_code}: {e}")

        # Fallback functions that return the original text
        def gettext_func(message: str) -> str:
            return message

        def ngettext_func(singular: str, plural: str, n: int) -> str:
            return singular if n == 1 else plural

    _translation_functions = (gettext_func, ngettext_func)
    return _translation_functions


def get_translation_functions() -> Tuple[Callable[[str], str], Callable[..., str]]:
    """
    Returns the current translation functions.
    Initializes with system locale if not already done.

    Returns:
        Tuple containing (function _, function ngettext)
    """
    global _translation_functions

    if _translation_functions is None:
        _translation_functions = init_translations()

    return _translation_functions


# Export global functions for simple usage
def _get_translator():
    """Gets the main translation function."""
    return get_translation_functions()[0]


def _get_ngettext():
    """Gets the plural translation function."""
    return get_translation_functions()[1]


# Global exported functions
def _(message: str) -> str:
    """Main translation function."""
    return _get_translator()(message)


def ngettext(singular: str, plural: str, n: int) -> str:
    """Translation function with plural handling."""
    return _get_ngettext()(singular, plural, n)


# Plural helper functions
def ngettext_helper(singular_key: str, plural_key: str, n: int) -> str:
    """
    Helper function to use ngettext with keys.

    Args:
        singular_key: Key for singular form
        plural_key: Key for plural form (same as singular_key)
        n: Number to determine singular/plural

    Returns:
        Translated string in singular or plural according to n
    """
    ngettext_func = get_translation_functions()[1]
    return ngettext_func(singular_key, plural_key, n)


def format_tokens_left(n: int) -> str:
    """Format the number of tokens left with English pluralization."""

    plural_form = ngettext_helper(PLURAL.TOKENS_LEFT, PLURAL.TOKENS_LEFT, n)
    formatted_number = format_number_english(n)
    return f"{formatted_number} {plural_form}"


def format_sessions_active(n: int) -> str:
    """Format the number of active sessions with English pluralization."""

    plural_form = ngettext_helper(PLURAL.SESSIONS_ACTIVE, PLURAL.SESSIONS_ACTIVE, n)
    return f"{n} {plural_form}"


def format_number_english(number: int) -> str:
    """
    Format a number according to English conventions (commas for thousands).

    Args:
        number: Number to format

    Returns:
        Number formatted with commas as thousand separators
    """
    return f"{number:,}"


def format_currency_english(amount: float) -> str:
    """
    Format a monetary value according to English conventions.

    Args:
        amount: Amount to format

    Returns:
        Amount formatted with commas and period as decimal separator
    """
    # Handle potential floating point precision issues
    formatted = f"{amount:.4f}".rstrip("0").rstrip(".").replace(".", ",")
    # Ajouter espaces pour les milliers si nécessaire
    if amount >= 1000:
        parts = formatted.split(",")
        # Handle empty decimal part
        if len(parts) > 1 and parts[1]:
            parts[0] = f"{int(parts[0]):,}".replace(",", " ")
        else:
            formatted = f"{int(amount):,}".replace(",", " ")
            return formatted
        formatted = ",".join(parts)
    return formatted


# For compatibility and tests
__all__ = [
    "init_translations",
    "get_system_locale",
    "get_translation_functions",
    "_",
    "ngettext",
    "APP_DOMAIN",
    "LOCALE_DIR",
]
