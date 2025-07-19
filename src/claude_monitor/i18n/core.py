"""Central module for internationalization of Claude Monitor."""

import gettext
import logging
import sys
from pathlib import Path
from typing import Optional

# Import importlib.resources with fallback for Python < 3.9
if sys.version_info >= (3, 9):
    import importlib.resources as importlib_resources
else:
    try:
        import importlib_resources
    except ImportError:
        importlib_resources = None

logger = logging.getLogger(__name__)

# Global instance of the i18n core
_i18n_core: Optional["I18nCore"] = None


class I18nCore:
    """Central internationalization manager."""

    def __init__(self, language_code: str = "en"):
        """Initialize the i18n core.

        Args:
            language_code: Language code to use
        """
        self.current_language = language_code
        self.available_languages = ["en", "fr", "es", "de"]
        self._catalogs: dict[str, gettext.GNUTranslations] = {}
        self._load_translations()

    def _get_locales_path(self) -> Path:
        """Get the path to the locales folder via importlib.resources."""
        try:
            if importlib_resources is not None:
                # Portable access to package resources
                locales_traversable = (
                    importlib_resources.files("claude_monitor") / "locales"
                )
                return Path(str(locales_traversable))
            else:
                logger.warning("importlib.resources not available")
        except Exception as e:
            logger.warning(f"Failed to locate package resources: {e}")

        # Fallback to old path for development compatibility
        current_file = Path(__file__)
        project_root = current_file.parent.parent.parent.parent
        fallback_path = project_root / "locales"
        logger.debug(f"Using fallback locales path: {fallback_path}")
        return fallback_path

    def _load_translations(self) -> None:
        """Load translation files."""
        locales_path = self._get_locales_path()

        if not locales_path.exists():
            logger.warning(f"Locales directory not found: {locales_path}")
            return

        for lang in self.available_languages:
            try:
                lang_path = locales_path / lang / "LC_MESSAGES"
                if (lang_path / "messages.mo").exists():
                    catalog = gettext.translation(
                        "messages",
                        localedir=str(locales_path),
                        languages=[lang],
                        fallback=True,
                    )
                    self._catalogs[lang] = catalog
                    logger.debug(f"Loaded translation catalog for {lang}")
                else:
                    logger.debug(f"No .mo file found for {lang}")
            except Exception as e:
                logger.warning(f"Failed to load catalog for {lang}: {e}")

    def translate(self, message: str, **kwargs) -> str:
        """Translate a message.

        Args:
            message: Message to translate
            **kwargs: Variables for formatting

        Returns:
            Translated and formatted message
        """
        try:
            # Get the translation
            if self.current_language in self._catalogs:
                catalog = self._catalogs[self.current_language]
                translated = catalog.gettext(message)
            else:
                translated = message

            # Apply formatting if variables are provided
            if kwargs:
                try:
                    return str(translated.format(**kwargs))
                except (KeyError, ValueError) as e:
                    logger.warning(f"Formatting error for message '{message}': {e}")
                    return str(translated)

            return str(translated)

        except Exception as e:
            logger.error(f"Translation error for '{message}': {e}")
            return message

    def ngettext(self, singular: str, plural: str, n: int, **kwargs) -> str:
        """Translate with plural handling.

        Args:
            singular: Singular form
            plural: Plural form
            n: Number to determine the form
            **kwargs: Variables for formatting

        Returns:
            Translated message with appropriate form
        """
        try:
            if self.current_language in self._catalogs:
                catalog = self._catalogs[self.current_language]
                translated = catalog.ngettext(singular, plural, n)
            else:
                translated = singular if n == 1 else plural

            if kwargs:
                try:
                    return str(translated.format(**kwargs))
                except (KeyError, ValueError) as e:
                    logger.warning(f"Formatting error for ngettext '{singular}': {e}")
                    return str(translated)

            return str(translated)

        except Exception as e:
            logger.error(f"ngettext error for '{singular}'/'{plural}': {e}")
            return singular if n == 1 else plural

    def switch_language(self, language_code: str) -> bool:
        """Change the active language.

        Args:
            language_code: New language code

        Returns:
            True if the change succeeded
        """
        if language_code not in self.available_languages:
            logger.warning(f"Language {language_code} not supported")
            return False

        old_language = self.current_language
        self.current_language = language_code

        # Reload translations if necessary
        if language_code not in self._catalogs:
            self._load_translations()

        logger.info(f"Language switched from {old_language} to {language_code}")
        return True


def get_i18n_core() -> I18nCore:
    """Get the global i18n core instance.

    Returns:
        The i18n core instance

    Raises:
        RuntimeError: If the core is not initialized
    """
    global _i18n_core
    if _i18n_core is None:
        raise RuntimeError(
            "i18n core not initialized. Call initialize_i18n_core() first."
        )
    return _i18n_core


def initialize_i18n_core(language_code: str = "en") -> I18nCore:
    """Initialize the global i18n core.

    Args:
        language_code: Language code to use

    Returns:
        The initialized i18n core instance
    """
    global _i18n_core
    _i18n_core = I18nCore(language_code)
    logger.debug(f"i18n core initialized with language: {language_code}")
    return _i18n_core


def reset_i18n_core() -> None:
    """Reset the i18n core (mainly for testing)."""
    global _i18n_core
    _i18n_core = None
    logger.debug("i18n core reset")
