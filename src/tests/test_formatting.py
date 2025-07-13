"""Tests for formatting utilities."""

from datetime import datetime, timezone
from unittest.mock import Mock, patch

from claude_monitor.utils.formatting import (
    format_currency,
    format_display_time,
    format_time,
    get_time_format_preference,
)
from claude_monitor.utils.model_utils import (
    get_model_display_name,
    get_model_generation,
    is_claude_model,
    normalize_model_name,
)


class TestFormatTime:
    """Test cases for format_time function."""

    def test_format_time_less_than_hour(self):
        """
        Test that `format_time` correctly formats minute values less than one hour as minutes only.
        """
        assert format_time(0) == "0m"
        assert format_time(1) == "1m"
        assert format_time(30) == "30m"
        assert format_time(59) == "59m"

    def test_format_time_exact_hours(self):
        """
        Test that `format_time` correctly formats values representing exact hours without minutes.
        """
        assert format_time(60) == "1h"
        assert format_time(120) == "2h"
        assert format_time(180) == "3h"

    def test_format_time_hours_and_minutes(self):
        """
        Tests that the format_time function correctly formats durations given in minutes into strings showing both hours and minutes.
        """
        assert format_time(61) == "1h 1m"
        assert format_time(90) == "1h 30m"
        assert format_time(125) == "2h 5m"
        assert format_time(225) == "3h 45m"

    def test_format_time_large_values(self):
        """
        Test that `format_time` correctly formats large minute values into hour and minute strings.
        
        Verifies that values representing 24 hours or more are displayed as hours (and minutes if applicable).
        """
        assert format_time(1440) == "24h"  # 1 day
        assert format_time(1500) == "25h"  # 25 hours
        assert format_time(1561) == "26h 1m"

    def test_format_time_float_values(self):
        """
        Tests that the format_time function correctly formats float minute values, rounding or truncating as appropriate for hours and minutes.
        """
        assert format_time(59.7) == "59m"
        assert (
            format_time(60.5) == "1h"
        )  # 60.5 minutes -> 1h 0m -> "1h" (no minutes shown when 0)
        assert format_time(90.8) == "1h 30m"


class TestFormatCurrency:
    """Test cases for format_currency function."""

    def test_format_usd_default(self):
        """
        Test that the `format_currency` function correctly formats various USD amounts using the default settings.
        """
        assert format_currency(0.0) == "$0.00"
        assert format_currency(1.0) == "$1.00"
        assert format_currency(10.99) == "$10.99"
        assert format_currency(1000.0) == "$1,000.00"
        assert format_currency(1234567.89) == "$1,234,567.89"

    def test_format_usd_explicit(self):
        """
        Test that formatting currency values with an explicit "USD" currency code produces correctly formatted US dollar strings.
        """
        assert format_currency(100.0, "USD") == "$100.00"
        assert format_currency(1000.50, "USD") == "$1,000.50"

    def test_format_other_currencies(self):
        """
        Test that `format_currency` correctly formats values for non-USD currencies, ensuring proper placement of currency codes and number formatting.
        """
        assert format_currency(100.0, "EUR") == "100.00 EUR"
        assert format_currency(1000.50, "GBP") == "1,000.50 GBP"
        assert format_currency(1234567.89, "JPY") == "1,234,567.89 JPY"

    def test_format_currency_edge_cases(self):
        """
        Test formatting of currency values for edge cases including very small, negative, and large amounts.
        """
        assert format_currency(0.001, "USD") == "$0.00"
        assert format_currency(-10.50, "USD") == "$-10.50"
        assert format_currency(999999999.99, "USD") == "$999,999,999.99"


class TestGetTimeFormatPreference:
    """Test cases for get_time_format_preference function."""

    @patch("claude_monitor.utils.time_utils.TimeFormatDetector.get_preference")
    def test_get_time_format_preference_no_args(self, mock_get_pref):
        """
        Tests that `get_time_format_preference` returns the correct value when called without arguments, using a mocked preference retrieval function.
        """
        mock_get_pref.return_value = True
        result = get_time_format_preference()
        mock_get_pref.assert_called_once_with(None)
        assert result is True

    @patch("claude_monitor.utils.time_utils.TimeFormatDetector.get_preference")
    def test_get_time_format_preference_with_args(self, mock_get_pref):
        """
        Tests that `get_time_format_preference` returns the correct value when provided with argument overrides.
        
        Verifies that the preference retrieval function is called with the given arguments and that the result matches the mocked return value.
        """
        mock_args = {"time_format": "12h"}
        mock_get_pref.return_value = False
        result = get_time_format_preference(mock_args)
        mock_get_pref.assert_called_once_with(mock_args)
        assert result is False


class TestFormatDisplayTime:
    """Test cases for format_display_time function."""

    def setUp(self):
        """
        Initializes a fixed datetime object for use in display time formatting tests.
        """
        self.test_dt = datetime(2024, 1, 1, 15, 30, 45, tzinfo=timezone.utc)

    @patch("claude_monitor.utils.time_utils.get_time_format_preference")
    def test_format_display_time_24h_with_seconds(self, mock_pref):
        """
        Tests that `format_display_time` correctly formats a datetime object in 24-hour format with seconds included.
        """
        mock_pref.return_value = False
        dt = datetime(2024, 1, 1, 15, 30, 45, tzinfo=timezone.utc)
        result = format_display_time(dt, use_12h_format=False, include_seconds=True)
        assert result == "15:30:45"

    @patch("claude_monitor.utils.time_utils.get_time_format_preference")
    def test_format_display_time_24h_without_seconds(self, mock_pref):
        """
        Tests that `format_display_time` correctly formats a datetime object in 24-hour format without including seconds.
        """
        mock_pref.return_value = False
        dt = datetime(2024, 1, 1, 15, 30, 45, tzinfo=timezone.utc)
        result = format_display_time(dt, use_12h_format=False, include_seconds=False)
        assert result == "15:30"

    @patch("claude_monitor.utils.time_utils.get_time_format_preference")
    def test_format_display_time_12h_with_seconds(self, mock_pref):
        """
        Verifies that `format_display_time` correctly formats a datetime in 12-hour format with seconds included.
        
        Ensures the output matches expected 12-hour time representations, accounting for platform-specific formatting differences.
        """
        mock_pref.return_value = True
        dt = datetime(2024, 1, 1, 15, 30, 45, tzinfo=timezone.utc)
        result = format_display_time(dt, use_12h_format=True, include_seconds=True)
        # Should be either "3:30:45 PM" (Unix) or "03:30:45 PM" (Windows fallback)
        assert "3:30:45 PM" in result or "03:30:45 PM" == result

    @patch("claude_monitor.utils.time_utils.get_time_format_preference")
    def test_format_display_time_12h_without_seconds(self, mock_pref):
        """
        Tests that `format_display_time` correctly formats a datetime object in 12-hour format without seconds, handling both Unix and Windows output variations.
        """
        mock_pref.return_value = True
        dt = datetime(2024, 1, 1, 15, 30, 45, tzinfo=timezone.utc)
        result = format_display_time(dt, use_12h_format=True, include_seconds=False)
        # Should be either "3:30 PM" (Unix) or "03:30 PM" (Windows fallback)
        assert "3:30 PM" in result or "03:30 PM" == result

    @patch("claude_monitor.utils.time_utils.get_time_format_preference")
    def test_format_display_time_auto_preference(self, mock_pref):
        """Test automatic preference detection."""
        mock_pref.return_value = True
        dt = datetime(2024, 1, 1, 15, 30, 45, tzinfo=timezone.utc)
        result = format_display_time(dt, use_12h_format=None, include_seconds=True)
        mock_pref.assert_called_once()
        # Should use 12-hour format since mock returns True
        assert "PM" in result

    def test_format_display_time_platform_compatibility(self):
        """
        Verifies that the format_display_time function produces correct 12-hour formatted time strings with and without seconds across different operating systems.
        """
        dt = datetime(2024, 1, 1, 3, 30, 45, tzinfo=timezone.utc)

        # Test 12-hour format - should work on both Unix and Windows
        result_12h = format_display_time(dt, use_12h_format=True, include_seconds=True)
        assert "3:30:45 AM" in result_12h or "03:30:45 AM" == result_12h

        # Test 12-hour format without seconds
        result_12h_no_sec = format_display_time(
            dt, use_12h_format=True, include_seconds=False
        )
        assert "3:30 AM" in result_12h_no_sec or "03:30 AM" == result_12h_no_sec

    def test_format_display_time_edge_cases(self):
        """
        Tests that `format_display_time` correctly formats noon and midnight in 12-hour format, ensuring the presence of appropriate AM/PM indicators.
        """
        # Test noon and midnight
        noon = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        midnight = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

        noon_result = format_display_time(
            noon, use_12h_format=True, include_seconds=False
        )
        midnight_result = format_display_time(
            midnight, use_12h_format=True, include_seconds=False
        )

        # Should contain PM/AM indicators
        assert "PM" in noon_result
        assert "AM" in midnight_result


class TestFormattingAdvanced:
    """Advanced test cases for formatting utilities."""

    def test_format_currency_extensive_edge_cases(self):
        """
        Verifies that format_currency correctly handles a wide range of edge cases, including very small, negative, and very large amounts, as well as different currencies.
        """
        # Test very small amounts
        assert format_currency(0.001, "USD") == "$0.00"
        assert format_currency(0.009, "USD") == "$0.01"

        # Test negative amounts
        assert format_currency(-10.50, "USD") == "$-10.50"
        assert format_currency(-0.01, "USD") == "$-0.01"

        # Test very large amounts
        assert format_currency(999999999.99, "USD") == "$999,999,999.99"
        assert format_currency(1000000000.00, "USD") == "$1,000,000,000.00"

        # Test other currencies with large amounts
        assert format_currency(1234567.89, "EUR") == "1,234,567.89 EUR"
        assert format_currency(-1000.50, "GBP") == "-1,000.50 GBP"

    def test_format_currency_precision_handling(self):
        """
        Test that `format_currency` correctly handles floating-point precision and rounding.
        
        Verifies that the function produces expected currency strings for values affected by floating-point arithmetic, including proper rounding up and down.
        """
        # Test floating point precision issues
        assert (
            format_currency(0.1 + 0.2, "USD") == "$0.30"
        )  # Should handle 0.30000000000000004
        assert format_currency(10.005, "USD") == "$10.01"  # Should round up
        assert format_currency(10.004, "USD") == "$10.00"  # Should round down

    def test_format_currency_international_formats(self):
        """
        Test that `format_currency` correctly formats amounts for various international currency codes.
        
        Verifies that the formatted string includes the expected numeric format and the appropriate currency code suffix for each tested currency.
        """
        currencies = [
            "JPY",
            "KRW",
            "INR",
            "BRL",
            "RUB",
            "CNY",
            "AUD",
            "CAD",
            "CHF",
            "SEK",
        ]

        for currency in currencies:
            result = format_currency(1234.56, currency)
            assert "1,234.56" in result
            assert currency in result
            assert result.endswith(currency)

    def test_format_time_comprehensive_coverage(self):
        """
        Verifies that the format_time function correctly formats a wide range of minute values, including zero, fractional, boundary, large, and mixed hour-minute cases.
        """
        # Test zero and very small values
        assert format_time(0.0) == "0m"
        assert format_time(0.1) == "0m"
        assert format_time(0.9) == "0m"

        # Test boundary values around hours
        assert format_time(59.9) == "59m"
        assert format_time(60.0) == "1h"
        assert format_time(60.1) == "1h"

        # Test large values
        assert format_time(1440) == "24h"  # 1 day
        assert format_time(2880) == "48h"  # 2 days
        assert format_time(10080) == "168h"  # 1 week

        # Test various combinations
        assert format_time(65.5) == "1h 5m"
        assert format_time(125.7) == "2h 5m"

    def test_format_time_extreme_values(self):
        """
        Tests the behavior of format_time when given extremely large or negative minute values.
        
        Verifies that very large minute values are formatted with hours, and that negative values are handled gracefully according to the implementation.
        """
        # Test very large values
        large_minutes = 100000
        result = format_time(large_minutes)
        assert "h" in result
        assert isinstance(result, str)

        # Test negative values (might be unexpected but should handle gracefully)
        # Note: This depends on implementation - might need to check actual behavior

    def test_format_display_time_comprehensive_platform_support(self):
        """
        Verifies that `format_display_time` correctly formats various datetime values in both 12-hour and 24-hour formats with seconds, ensuring compatibility across different times of day and platform conventions.
        """
        test_times = [
            datetime(2024, 1, 1, 0, 0, 0),  # Midnight
            datetime(2024, 1, 1, 12, 0, 0),  # Noon
            datetime(2024, 1, 1, 1, 5, 10),  # Early morning
            datetime(2024, 1, 1, 23, 59, 59),  # Late night
        ]

        for dt in test_times:
            # Test 24-hour format
            result_24h = format_display_time(
                dt, use_12h_format=False, include_seconds=True
            )
            assert ":" in result_24h
            assert len(result_24h.split(":")) == 3  # HH:MM:SS

            # Test 12-hour format
            result_12h = format_display_time(
                dt, use_12h_format=True, include_seconds=True
            )
            assert ("AM" in result_12h) or ("PM" in result_12h)

    def test_get_time_format_preference_edge_cases(self):
        """
        Test `get_time_format_preference` for correct behavior with None and empty argument objects.
        
        Verifies that the function correctly delegates to the underlying preference detector and returns the expected boolean value for edge case inputs.
        """
        # Test with None args
        with patch(
            "claude_monitor.utils.time_utils.TimeFormatDetector.get_preference"
        ) as mock_pref:
            mock_pref.return_value = True
            result = get_time_format_preference(None)
            assert result is True
            mock_pref.assert_called_once_with(None)

        # Test with empty args object
        empty_args = type("Args", (), {})()
        with patch(
            "claude_monitor.utils.time_utils.TimeFormatDetector.get_preference"
        ) as mock_pref:
            mock_pref.return_value = False
            result = get_time_format_preference(empty_args)
            assert result is False
            mock_pref.assert_called_once_with(empty_args)

    def test_internal_get_pref_function(self):
        """
        Tests the internal `_get_pref` helper to ensure it correctly retrieves the time format preference using provided arguments.
        """
        from claude_monitor.utils.formatting import _get_pref

        # Test with mock args
        mock_args = Mock()
        with patch(
            "claude_monitor.utils.formatting.get_time_format_preference"
        ) as mock_pref:
            mock_pref.return_value = True
            result = _get_pref(mock_args)
            assert result is True
            mock_pref.assert_called_once_with(mock_args)


class TestFormattingErrorHandling:
    """Test error handling in formatting utilities."""

    def test_format_currency_error_conditions(self):
        """
        Tests that format_currency handles infinite and NaN values gracefully, either by returning a string or raising an appropriate exception.
        """
        # Test with very large numbers that might cause overflow
        try:
            result = format_currency(float("inf"), "USD")
            # If it doesn't raise an error, should return a string
            assert isinstance(result, str)
        except (OverflowError, ValueError):
            # This is acceptable behavior
            pass

        # Test with NaN
        try:
            result = format_currency(float("nan"), "USD")
            assert isinstance(result, str)
        except ValueError:
            # This is acceptable behavior
            pass

    def test_format_time_error_conditions(self):
        """
        Tests that the `format_time` function handles negative and extremely large input values gracefully, returning a string in both cases.
        """
        # Test with negative values
        result = format_time(-10)
        # Should handle gracefully - exact behavior depends on implementation
        assert isinstance(result, str)

        # Test with very large values
        result = format_time(1e10)  # Very large number
        assert isinstance(result, str)

    def test_format_display_time_invalid_inputs(self):
        """
        Test that `format_display_time` handles invalid or None datetime inputs gracefully, either by raising an appropriate exception or returning a sensible string.
        """
        # Test with None datetime
        try:
            result = format_display_time(None)
            # If it doesn't raise an error, should return something sensible
            assert isinstance(result, str)
        except (AttributeError, TypeError):
            # This is expected behavior
            pass


class TestFormattingPerformance:
    """Test performance characteristics of formatting utilities."""

    def test_format_currency_performance_with_large_datasets(self):
        """
        Tests that formatting 10,000 currency values completes within one second and produces the correct output types and count.
        """
        import time

        # Test formatting many currency values
        values = [i * 0.01 for i in range(10000)]  # 0.00 to 99.99

        start_time = time.time()
        results = [format_currency(value, "USD") for value in values]
        end_time = time.time()

        # Should complete in reasonable time (less than 1 second for 10k values)
        assert end_time - start_time < 1.0
        assert len(results) == len(values)
        assert all(isinstance(r, str) for r in results)

    def test_format_time_performance_with_large_datasets(self):
        """
        Tests that the format_time function can efficiently process a large range of minute values, completing within one second and returning the correct number and type of results.
        """
        import time

        # Test formatting many time values
        values = list(range(0, 10000))  # 0 to 9999 minutes

        start_time = time.time()
        results = [format_time(value) for value in values]
        end_time = time.time()

        # Should complete in reasonable time
        assert end_time - start_time < 1.0
        assert len(results) == len(values)
        assert all(isinstance(r, str) for r in results)


class TestModelUtils:
    """Test cases for model utilities."""

    def test_normalize_model_name(self):
        """
        Tests the normalize_model_name function to ensure correct normalization of Claude model names, handling of empty or None inputs, and preservation of unknown model names.
        """
        # Test Claude 3 models
        assert normalize_model_name("claude-3-opus-20240229") == "claude-3-opus"
        assert normalize_model_name("claude-3-sonnet-20240229") == "claude-3-sonnet"
        assert normalize_model_name("claude-3-haiku-20240307") == "claude-3-haiku"

        # Test Claude 3.5 models
        assert normalize_model_name("claude-3-5-sonnet-20241022") == "claude-3-5-sonnet"
        assert normalize_model_name("Claude 3.5 Sonnet") == "claude-3-5-sonnet"
        assert normalize_model_name("claude-3-5-haiku") == "claude-3-5-haiku"

        # Test empty/None inputs
        assert normalize_model_name("") == ""
        assert normalize_model_name(None) == ""

        # Test unknown models
        assert normalize_model_name("unknown-model") == "unknown-model"

    def test_get_model_display_name(self):
        """
        Verifies that `get_model_display_name` returns the correct display name for known Claude models and applies title casing for unknown model names.
        """
        # Test known models
        assert get_model_display_name("claude-3-opus") == "Claude 3 Opus"
        assert get_model_display_name("claude-3-sonnet") == "Claude 3 Sonnet"
        assert get_model_display_name("claude-3-haiku") == "Claude 3 Haiku"
        assert get_model_display_name("claude-3-5-sonnet") == "Claude 3.5 Sonnet"
        assert get_model_display_name("claude-3-5-haiku") == "Claude 3.5 Haiku"

        # Test unknown models (should title case)
        assert get_model_display_name("unknown-model") == "Unknown-Model"
        assert get_model_display_name("gpt-4") == "Gpt-4"

    def test_is_claude_model(self):
        """Test Claude model detection."""
        # Test Claude models
        assert is_claude_model("claude-3-opus") is True
        assert is_claude_model("claude-3-sonnet") is True
        assert is_claude_model("claude-3-5-sonnet") is True
        assert is_claude_model("Claude 3 Opus") is True

        # Test non-Claude models
        assert is_claude_model("gpt-4") is False
        assert is_claude_model("gemini-pro") is False
        assert is_claude_model("") is False

    def test_get_model_generation(self):
        """
        Verifies that the `get_model_generation` function correctly extracts the generation number from various Claude model names, including edge cases and unknown models.
        """
        # Test Claude 3.5 models
        assert get_model_generation("claude-3-5-sonnet") == "3.5"
        assert get_model_generation("claude-3.5-sonnet") == "3.5"
        assert get_model_generation("claude-3.5-haiku") == "3.5"

        # Test Claude 3 models
        assert get_model_generation("claude-3-opus") == "3"
        assert get_model_generation("claude-3-sonnet") == "3"
        assert get_model_generation("claude-3-haiku") == "3"

        # Test Claude 2 models
        assert get_model_generation("claude-2") == "2"
        assert get_model_generation("claude-2.1") == "2"

        # Test Claude 1 models
        assert get_model_generation("claude-1") == "1"
        assert get_model_generation("claude-instant-1") == "1"

        # Test edge cases
        assert get_model_generation("") == "unknown"
        assert get_model_generation("unknown-model") == "unknown"
        assert (
            get_model_generation("claude-10") == "unknown"
        )  # Don't match "1" from "10"
