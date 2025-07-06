"""
Internationalization module for Claude Usage Monitor.

This module manages gettext configuration, locale detection,
and translation initialization.
"""

import gettext
import locale
import os
from pathlib import Path
from typing import Callable, Optional, Tuple

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
        # Note: ignore type warning for ngettext - function is compatible
        ngettext_func = translation.ngettext  # type: ignore

    except Exception as e:
        # On error, use default (pass-through) functions
        print(f"Warning: Failed to load translations for {lang_code}: {e}")

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


# Fonctions d'aide pour les pluriels
def ngettext_helper(singular_key: str, plural_key: str, n: int) -> str:
    """
    Fonction d'aide pour utiliser ngettext avec des clés.

    Args:
        singular_key: Clé pour la forme singulière
        plural_key: Clé pour la forme plurielle (même que singular_key)
        n: Nombre pour déterminer singulier/pluriel

    Returns:
        Chaîne traduite au singulier ou pluriel selon n
    """
    ngettext_func = get_translation_functions()[1]
    return ngettext_func(singular_key, plural_key, n)


def format_tokens_left(n: int) -> str:
    """Formate le nombre de tokens restants avec pluriel français."""
    from .message_keys import PLURAL

    plural_form = ngettext_helper(PLURAL.TOKENS_LEFT, PLURAL.TOKENS_LEFT, n)
    formatted_number = format_number_french(n)
    return f"{formatted_number} {plural_form}"


def format_sessions_active(n: int) -> str:
    """Formate le nombre de sessions actives avec pluriel français."""
    from .message_keys import PLURAL

    plural_form = ngettext_helper(PLURAL.SESSIONS_ACTIVE, PLURAL.SESSIONS_ACTIVE, n)
    return f"{n} {plural_form}"


def format_number_french(number: int) -> str:
    """
    Formate un nombre selon les conventions françaises (espaces pour milliers).

    Args:
        number: Nombre à formater

    Returns:
        Nombre formaté avec espaces comme séparateurs de milliers
    """
    return f"{number:,}".replace(",", " ")


def format_currency_french(amount: float) -> str:
    """
    Formate une valeur monétaire selon les conventions françaises.

    Args:
        amount: Montant à formater

    Returns:
        Montant formaté avec espaces et virgule décimale
    """
    formatted = f"{amount:.4f}".replace(".", ",")
    # Ajouter espaces pour les milliers si nécessaire
    if amount >= 1000:
        parts = formatted.split(",")
        parts[0] = f"{int(parts[0]):,}".replace(",", " ")
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
