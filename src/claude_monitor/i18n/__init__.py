"""Public API for Claude Monitor internationalization."""

import logging
from pathlib import Path
from typing import Callable, Optional

from .core import get_i18n_core, initialize_i18n_core

logger = logging.getLogger(__name__)


def _ensure_compiled_translations() -> None:
    """Ensure translations are compiled (.mo files exist).

    If .mo files are missing but .po files exist, attempt to compile them.
    """
    try:
        current_dir = Path(__file__).parent.parent
        locales_dir = current_dir / "locales"
        if not locales_dir.exists():
            return
        # Checks if at least one .mo file is missing for a present language
        needs_compilation = False
        for lang_dir in locales_dir.iterdir():
            if lang_dir.is_dir():
                po_file = lang_dir / "LC_MESSAGES" / "messages.po"
                mo_file = lang_dir / "LC_MESSAGES" / "messages.mo"
                if po_file.exists() and not mo_file.exists():
                    needs_compilation = True
                    break
        if needs_compilation:
            logger.info("Compiling missing translation files...")
            _compile_translations_fallback()
    except Exception as e:
        logger.debug(f"Could not check/compile translations: {e}")
        # Fail silently - translations will fall back to English


def _compile_translations_fallback() -> None:
    """Fallback translation compilation using polib directly."""
    try:
        import polib

        current_dir = Path(__file__).parent.parent
        locales_dir = current_dir / "locales"
        for lang_dir in locales_dir.iterdir():
            if lang_dir.is_dir():
                po_file = lang_dir / "LC_MESSAGES" / "messages.po"
                mo_file = lang_dir / "LC_MESSAGES" / "messages.mo"
                if po_file.exists():
                    try:
                        po = polib.pofile(str(po_file))
                        po.save_as_mofile(str(mo_file))
                        logger.info(f"Compiled {lang_dir.name} translations")
                    except Exception as e:
                        logger.warning(f"Failed to compile {lang_dir.name}: {e}")
    except ImportError:
        logger.debug("polib not available for translation compilation")
    except Exception as e:
        logger.debug(f"Translation compilation failed: {e}")


def compile_translations() -> bool:
    """Public API to compile translations programmatically.

    Returns:
        True if compilation was successful, False otherwise
    """
    try:
        _compile_translations_fallback()
        return True
    except Exception as e:
        logger.error(f"Translation compilation failed: {e}")
        return False


def _(message: str, **kwargs) -> str:
    """Main translation function - used throughout the code.

    Args:
        message: Message to translate
        **kwargs: Variables for template formatting

    Returns:
        Translated and formatted message

    Example:
        # Simple message
        error_msg = _("Error occurred")

        # Message with variables
        error_msg = _("Error in {component}: {error}").format(
            component="data_reader",
            error=str(exception)
        )

        # Alternative with **kwargs (recommended)
        error_msg = _("Error in {component}: {error}",
                     component="data_reader",
                     error=str(exception))
    """
    try:
        i18n_core = get_i18n_core()
        return i18n_core.translate(message, **kwargs)
    except RuntimeError:
        # i18n not initialized yet, return original message
        logger.debug("i18n not initialized, returning original message")
        if kwargs:
            try:
                return message.format(**kwargs)
            except (KeyError, ValueError):
                return message
        return message


def ngettext(singular: str, plural: str, n: int, **kwargs) -> str:
    """Pluralization function with i18n.

    Args:
        singular: Singular form of the message
        plural: Plural form of the message
        n: Number to determine the form
        **kwargs: Variables for formatting

    Returns:
        Translated message in the appropriate form

    Example:
        msg = ngettext(
            "Found {count} session",
            "Found {count} sessions",
            session_count,
            count=session_count
        )
    """
    try:
        i18n_core = get_i18n_core()
        return i18n_core.ngettext(singular, plural, n, **kwargs)
    except RuntimeError:
        # Simple fallback without i18n
        template = singular if n == 1 else plural
        if kwargs:
            try:
                return template.format(**kwargs)
            except (KeyError, ValueError):
                return template
        return template


def lazy_gettext(message: str) -> Callable[[], str]:
    """Lazy version of gettext for templates/constants.

    Args:
        message: Message to translate lazily

    Returns:
        Translated message (evaluated at call time)

    Note:
        Used for constants/templates that must be
        translated at usage time, not at definition.
    """
    return lambda: _(message)


def get_current_language() -> str:
    """Get the currently active language.

    Returns:
        Current language code (e.g. 'fr', 'en', 'es', 'de')
    """
    try:
        i18n_core = get_i18n_core()
        return i18n_core.current_language
    except RuntimeError:
        return "en"  # Default fallback


def set_language(language_code: str) -> bool:
    """Change the active language.

    Args:
        language_code: Code of the new language

    Returns:
        True if the change succeeded, False otherwise
    """
    try:
        initialize_i18n_core(language_code)
        logger.info(f"Language switched to {language_code}")
        return True
    except Exception as e:
        logger.error(f"Failed to switch language to {language_code}: {e}")
        return False


def get_available_languages() -> list[str]:
    """Get the list of supported languages.

    Returns:
        List of available language codes
    """
    try:
        # Dynamically detects available languages in locales
        current_dir = Path(__file__).parent.parent
        locales_dir = current_dir / "locales"
        langs = []
        if locales_dir.exists():
            for lang_dir in locales_dir.iterdir():
                if lang_dir.is_dir():
                    langs.append(lang_dir.name)
        if langs:
            return langs
        # Fallback to core if nothing found
        i18n_core = get_i18n_core()
        return i18n_core.available_languages
    except Exception:
        return ["en"]


def init_i18n(
    language_code: Optional[str] = None, fallback_language: str = "en"
) -> None:
    """Initialize the i18n system (main initialization function).

    Args:
        language_code: Language code to use (None = auto-detect)
        fallback_language: Fallback language in case of problem

    Note:
        This function must be called at application startup,
        usually in main() or during settings initialization.
    """
    try:
        if language_code is None:
            import os

            env_lang = (
                os.environ.get("LANGUAGE")
                or os.environ.get("LANG")
                or os.environ.get("LC_ALL")
            )
            if env_lang:
                language_code = env_lang.split("_")[0].split(".")[0].lower()
            # Dynamic detection of available languages
            current_dir = Path(__file__).parent.parent
            locales_dir = current_dir / "locales"
            available_langs = []
            if locales_dir.exists():
                for lang_dir in locales_dir.iterdir():
                    if lang_dir.is_dir():
                        available_langs.append(lang_dir.name)
            # If the detected language is not available, fallback
            if language_code not in available_langs:
                language_code = fallback_language
        initialize_i18n_core(language_code)
        logger.info(f"i18n initialized with language: {language_code}")
    except Exception as e:
        logger.error(f"Failed to initialize i18n: {e}")
        try:
            initialize_i18n_core(fallback_language)
        except Exception as fallback_error:
            logger.critical(
                f"Even fallback i18n initialization failed: {fallback_error}"
            )
    _ensure_compiled_translations()


# Aliases for compatibility with standard gettext
gettext = _
