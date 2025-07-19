"""Localized formatting for numbers, currencies, dates according to regional conventions."""

import locale
import logging
from decimal import Decimal
from typing import Optional, Union

logger = logging.getLogger(__name__)

# Global instance of the formatter
_formatter: Optional["LocalizedFormatter"] = None


class LocalizedFormatter:
    """Manager for localized formatting according to regional conventions."""

    def __init__(self, language_code: str = "en"):
        """Initialize the localized formatter.

        Args:
            language_code: Language code for formatting
        """
        self.language_code = language_code
        self._setup_locale()

    def _setup_locale(self) -> None:
        """Configure the system locale according to the language."""
        locale_map = {
            "en": ["en_US.UTF-8", "en_US", "English"],
            "es": ["es_ES.UTF-8", "es_ES", "Spanish"],
            "de": ["de_DE.UTF-8", "de_DE", "German"],
            "fr": ["fr_FR.UTF-8", "fr_FR", "French"],
        }

        if self.language_code in locale_map:
            locales_to_try = locale_map[self.language_code]
            for loc in locales_to_try:
                try:
                    locale.setlocale(locale.LC_ALL, loc)
                    logger.debug(f"Locale set to {loc}")
                    return
                except locale.Error:
                    continue

        # Fallback to default locale
        try:
            locale.setlocale(locale.LC_ALL, "")
            logger.debug("Using system default locale")
        except locale.Error:
            logger.warning("Could not set any locale, using C locale")

    def format_number(self, number: Union[int, float, Decimal]) -> str:
        """Format a number according to local conventions.

        Args:
            number: Number to format

        Returns:
            Number formatted according to the locale
        """
        try:
            if isinstance(number, Decimal):
                number = float(number)
            return locale.format_string("%.2f", number, grouping=True)
        except Exception as e:
            logger.warning(f"Number formatting error: {e}")
            return str(number)

    def format_currency(
        self, amount: Union[int, float, Decimal], currency: str = "USD"
    ) -> str:
        """Format a currency according to local conventions.

        Args:
            amount: Amount to format
            currency: Currency code (USD, EUR, etc.)

        Returns:
            Amount formatted with currency symbol
        """
        try:
            if isinstance(amount, Decimal):
                amount = float(amount)

            # Currency symbols according to language
            currency_symbols = {"USD": "$", "EUR": "€", "GBP": "£"}

            symbol = currency_symbols.get(currency, currency)
            formatted_amount = locale.format_string("%.2f", amount, grouping=True)

            # Symbol position according to language
            if self.language_code == "fr" and currency == "EUR":
                return f"{formatted_amount} {symbol}"  # 123,45 €
            else:
                return f"{symbol}{formatted_amount}"  # $123.45

        except Exception as e:
            logger.warning(f"Currency formatting error: {e}")
            return f"{currency} {amount}"

    def format_percentage(self, value: Union[int, float]) -> str:
        """Format a percentage according to local conventions.

        Args:
            value: Percentage value (0.25 for 25%)

        Returns:
            Formatted percentage
        """
        try:
            percentage = value * 100
            formatted = locale.format_string("%.1f", percentage, grouping=True)
            return f"{formatted}%"
        except Exception as e:
            logger.warning(f"Percentage formatting error: {e}")
            return f"{value * 100:.1f}%"

    def format_file_size(self, bytes_count: int) -> str:
        """Format a file size with localized units.

        Args:
            bytes_count: Number of bytes

        Returns:
            Formatted size with units
        """
        try:
            units = {
                "en": ["B", "KB", "MB", "GB", "TB"],
                "fr": ["o", "Ko", "Mo", "Go", "To"],
                "es": ["B", "KB", "MB", "GB", "TB"],
                "de": ["B", "KB", "MB", "GB", "TB"],
            }

            unit_list = units.get(self.language_code, units["en"])

            size = float(bytes_count)
            unit_index = 0

            while size >= 1024 and unit_index < len(unit_list) - 1:
                size /= 1024
                unit_index += 1

            if unit_index == 0:
                return f"{int(size)} {unit_list[unit_index]}"
            else:
                formatted_size = locale.format_string("%.1f", size, grouping=True)
                return f"{formatted_size} {unit_list[unit_index]}"

        except Exception as e:
            logger.warning(f"File size formatting error: {e}")
            return f"{bytes_count} B"


def get_formatter() -> LocalizedFormatter:
    """Get the global instance of the formatter.

    Returns:
        Instance of the localized formatter

    Raises:
        RuntimeError: If the formatter is not initialized
    """
    global _formatter
    if _formatter is None:
        raise RuntimeError(
            "Formatter not initialized. Call initialize_formatter() first."
        )
    return _formatter


def initialize_formatter(language_code: str = "en") -> LocalizedFormatter:
    """Initialize the global formatter.

    Args:
        language_code: Language code for formatting

    Returns:
        Instance of the initialized formatter
    """
    global _formatter
    _formatter = LocalizedFormatter(language_code)
    logger.debug(f"Formatter initialized with language: {language_code}")
    return _formatter


def reset_formatter() -> None:
    """Reset the formatter (mainly for tests)."""
    global _formatter
    _formatter = None
    logger.debug("Formatter reset")
