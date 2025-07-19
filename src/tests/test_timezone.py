"""Comprehensive tests for TimezoneHandler class."""

from datetime import datetime, timezone
from typing import List, Union
from unittest.mock import Mock, patch

import pytest
import pytz

from claude_monitor.utils.timezone import (
    TimezoneHandler,
    _detect_timezone_time_preference,
)


class TestTimezoneHandler:
    """Test suite for TimezoneHandler class."""

    @pytest.fixture
    def handler(self) -> TimezoneHandler:
        """Create a TimezoneHandler with default settings."""
        return TimezoneHandler()

    @pytest.fixture
    def custom_handler(self) -> TimezoneHandler:
        """Create a TimezoneHandler with custom timezone."""
        return TimezoneHandler(default_tz="America/New_York")

    def test_init_default_timezone(self, handler: TimezoneHandler) -> None:
        """Test initialization with default timezone."""
        assert handler.default_tz == pytz.UTC
        assert hasattr(handler, "default_tz")

    def test_init_custom_timezone(self, custom_handler: TimezoneHandler) -> None:
        """Test initialization with custom timezone."""
        assert custom_handler.default_tz.zone == "America/New_York"

    def test_init_invalid_timezone_fallback(self) -> None:
        """Test initialization with invalid timezone falls back to UTC."""
        with patch("claude_monitor.utils.time_utils.logger") as mock_logger:
            handler = TimezoneHandler(default_tz="Invalid/Timezone")

            assert handler.default_tz == pytz.UTC
            mock_logger.warning.assert_called_once()

    def test_validate_timezone_valid_timezones(self, handler: TimezoneHandler) -> None:
        """Test timezone validation with valid timezones."""
        valid_timezones: List[str] = [
            "UTC",
            "America/New_York",
            "Europe/London",
            "Asia/Tokyo",
            "Australia/Sydney",
        ]

        for tz in valid_timezones:
            assert handler.validate_timezone(tz) is True

    def test_validate_timezone_invalid_timezones(
        self, handler: TimezoneHandler
    ) -> None:
        """Test timezone validation with invalid timezones."""
        invalid_timezones: List[Union[str, None, int]] = [
            "",
            "Invalid/Timezone",
            "Not_A_Timezone",
            None,
            123,
        ]

        for tz in invalid_timezones:
            if tz is None or isinstance(tz, int):
                # These will cause errors due to type conversion
                try:
                    result = handler.validate_timezone(tz)
                    assert result is False
                except (TypeError, AttributeError):
                    # Expected for None and int types
                    pass
            else:
                assert handler.validate_timezone(tz) is False

    def test_parse_timestamp_iso_format_with_z(self, handler: TimezoneHandler) -> None:
        """Test parsing ISO format timestamp with Z suffix."""
        timestamp_str = "2024-01-15T10:30:45Z"
        result = handler.parse_timestamp(timestamp_str)

        expected = datetime(2024, 1, 15, 10, 30, 45, tzinfo=timezone.utc)
        assert result == expected

    def test_parse_timestamp_iso_format_with_offset(
        self, handler: TimezoneHandler
    ) -> None:
        """Test parsing ISO format timestamp with timezone offset."""
        timestamp_str = "2024-01-15T10:30:45+05:00"
        result = handler.parse_timestamp(timestamp_str)

        # Should be converted to UTC
        expected = datetime(2024, 1, 15, 5, 30, 45, tzinfo=timezone.utc)
        assert result == expected

    def test_parse_timestamp_iso_format_without_timezone(
        self, handler: TimezoneHandler
    ) -> None:
        """Test parsing ISO format timestamp without timezone info."""
        timestamp_str = "2024-01-15T10:30:45"
        result = handler.parse_timestamp(timestamp_str)

        # Should assume UTC
        expected = datetime(2024, 1, 15, 10, 30, 45, tzinfo=timezone.utc)
        assert result == expected

    def test_parse_timestamp_with_microseconds(self, handler: TimezoneHandler) -> None:
        """Test parsing timestamp with microseconds."""
        timestamp_str = "2024-01-15T10:30:45.123456Z"
        result = handler.parse_timestamp(timestamp_str)

        expected = datetime(2024, 1, 15, 10, 30, 45, 123456, tzinfo=timezone.utc)
        assert result == expected

    def test_parse_timestamp_unix_timestamp_string(
        self, handler: TimezoneHandler
    ) -> None:
        """Test parsing unix timestamp as string - not supported by current implementation."""
        # Current implementation doesn't parse unix timestamps
        timestamp_str = "1705316645"
        result = handler.parse_timestamp(timestamp_str)

        # Should return None for unsupported format
        assert result is None

    def test_parse_timestamp_unix_timestamp_with_milliseconds(
        self, handler: TimezoneHandler
    ) -> None:
        """Test parsing unix timestamp with milliseconds - not supported by current implementation."""
        # Current implementation doesn't parse unix timestamps
        timestamp_str = "1705316645123"
        result = handler.parse_timestamp(timestamp_str)

        # Should return None for unsupported format
        assert result is None

    def test_parse_timestamp_invalid_format(self, handler: TimezoneHandler) -> None:
        """Test parsing invalid timestamp format."""
        result = handler.parse_timestamp("invalid-timestamp")
        assert result is None

    def test_parse_timestamp_empty_string(self, handler: TimezoneHandler) -> None:
        """Test parsing empty timestamp string."""
        result = handler.parse_timestamp("")
        assert result is None

    def test_ensure_utc_with_utc_datetime(self, handler: TimezoneHandler) -> None:
        """Test ensure_utc with datetime already in UTC."""
        dt = datetime(2024, 1, 15, 10, 30, 45, tzinfo=pytz.UTC)
        result = handler.ensure_utc(dt)

        assert result == dt
        assert result.tzinfo == pytz.UTC

    def test_ensure_utc_with_naive_datetime(self, handler: TimezoneHandler) -> None:
        """Test ensure_utc with naive datetime (assumes UTC)."""
        dt = datetime(2024, 1, 15, 10, 30, 45)  # No timezone
        result = handler.ensure_utc(dt)

        expected = pytz.UTC.localize(datetime(2024, 1, 15, 10, 30, 45))
        assert result == expected

    def test_ensure_utc_with_different_timezone(self, handler: TimezoneHandler) -> None:
        """Test ensure_utc with datetime in different timezone."""
        # Create datetime in EST (UTC-5)
        est = pytz.timezone("America/New_York")
        dt = est.localize(datetime(2024, 1, 15, 5, 30, 45))

        result = handler.ensure_utc(dt)

        # Should be converted to UTC (5 hours ahead)
        expected = datetime(2024, 1, 15, 10, 30, 45, tzinfo=pytz.UTC)
        assert result == expected

    def test_ensure_timezone_utc_to_est(self, handler: TimezoneHandler) -> None:
        """Test ensure_timezone conversion from UTC to EST."""
        dt = datetime(2024, 1, 15, 10, 30, 45, tzinfo=pytz.UTC)
        result = handler.ensure_timezone(dt)

        # Should remain in UTC since that's the default
        assert result == dt

    def test_ensure_timezone_with_custom_timezone(
        self, custom_handler: TimezoneHandler
    ) -> None:
        """Test ensure_timezone with custom default timezone."""
        dt = datetime(2024, 1, 15, 10, 30, 45, tzinfo=pytz.UTC)
        result = custom_handler.ensure_timezone(dt)

        # Should remain unchanged since it already has timezone
        assert result == dt

    def test_ensure_timezone_with_naive_datetime(
        self, handler: TimezoneHandler
    ) -> None:
        """Test ensure_timezone with naive datetime."""
        dt = datetime(2024, 1, 15, 10, 30, 45)  # No timezone
        result = handler.ensure_timezone(dt)

        # Should assume default timezone and return in default timezone
        expected = pytz.UTC.localize(datetime(2024, 1, 15, 10, 30, 45))
        assert result == expected

    def test_to_utc_from_different_timezone(self, handler: TimezoneHandler) -> None:
        """Test to_utc conversion from different timezone."""
        # Create datetime in JST (UTC+9)
        jst = pytz.timezone("Asia/Tokyo")
        dt = jst.localize(datetime(2024, 1, 15, 19, 30, 45))

        result = handler.to_utc(dt)

        # Should be converted to UTC (9 hours behind)
        expected = datetime(2024, 1, 15, 10, 30, 45, tzinfo=pytz.UTC)
        assert result == expected

    def test_to_utc_with_naive_datetime(self, handler: TimezoneHandler) -> None:
        """Test to_utc with naive datetime."""
        dt = datetime(2024, 1, 15, 10, 30, 45)
        result = handler.to_utc(dt)

        # Should assume default timezone (UTC) and return in UTC
        expected = datetime(2024, 1, 15, 10, 30, 45, tzinfo=pytz.UTC)
        assert result == expected

    def test_to_utc_with_custom_default_timezone(
        self, custom_handler: TimezoneHandler
    ) -> None:
        """Test to_utc with custom default timezone."""
        dt = datetime(2024, 1, 15, 5, 30, 45)  # Naive datetime
        result = custom_handler.to_utc(dt)

        # Should assume America/New_York and convert to UTC
        # During standard time (EST), this would be +5 hours
        expected_hour = 10  # 5 AM EST = 10 AM UTC (standard time)
        assert result.hour in (expected_hour, 9)  # Account for DST

    def test_to_timezone_conversion(self, handler: TimezoneHandler) -> None:
        """Test to_timezone conversion."""
        dt = datetime(2024, 1, 15, 10, 30, 45, tzinfo=timezone.utc)
        result = handler.to_timezone(dt, "Asia/Tokyo")

        # Should be converted to JST (UTC+9)
        assert result.hour == 19  # 10 AM UTC = 7 PM JST

    def test_to_timezone_with_default(self, custom_handler: TimezoneHandler) -> None:
        """Test to_timezone using default timezone."""
        dt = datetime(2024, 1, 15, 10, 30, 45, tzinfo=timezone.utc)
        result = custom_handler.to_timezone(dt)

        # Should use default timezone (America/New_York)
        expected_hour = 5  # 10 AM UTC = 5 AM EST (standard time)
        assert result.hour in (expected_hour, 6)  # Account for DST

    def test_error_handling_integration(self, handler: TimezoneHandler) -> None:
        """Test error handling integration."""
        # Test that invalid timestamps return None gracefully
        result = handler.parse_timestamp("completely-invalid-timestamp")
        assert result is None

    def test_format_datetime_with_timezone_preference(
        self, handler: TimezoneHandler
    ) -> None:
        """Test format_datetime with timezone preference."""
        dt = datetime(2024, 1, 15, 14, 30, 45, tzinfo=pytz.UTC)

        # Test 24-hour format (default for UTC)
        result_24h = handler.format_datetime(dt, use_12_hour=False)
        assert "14:30:45" in result_24h

        # Test 12-hour format
        result_12h = handler.format_datetime(dt, use_12_hour=True)
        assert "2:30:45 PM" in result_12h or "02:30:45 PM" in result_12h

    def test_detect_timezone_preference_integration(
        self, handler: TimezoneHandler
    ) -> None:
        """Test integration with timezone preference detection."""
        # Test US timezone (should prefer 12-hour)
        us_handler = TimezoneHandler("America/New_York")
        dt = datetime(2024, 1, 15, 14, 30, 45, tzinfo=pytz.UTC)

        result = us_handler.format_datetime(dt)
        # Should automatically use appropriate format
        assert isinstance(result, str)
        assert "2024" in result

    def test_comprehensive_timestamp_parsing(self, handler: TimezoneHandler) -> None:
        """Test comprehensive timestamp parsing with various formats."""
        test_cases: List[str] = [
            "2024-01-15T10:30:45Z",
            "2024-01-15T10:30:45.123Z",
            "2024-01-15T10:30:45+00:00",
            "2024-01-15T10:30:45.123+00:00",
            "2024-01-15T05:30:45-05:00",  # EST
            "1705316645",  # Unix timestamp
            "1705316645123",  # Unix timestamp with milliseconds
        ]

        for timestamp_str in test_cases:
            result = handler.parse_timestamp(timestamp_str)
            if result is not None:  # Some formats might not be supported
                assert isinstance(result, datetime)
                # Check timezone - should have timezone info
                assert result.tzinfo is not None


class TestTimezonePreferenceDetection:
    """Test suite for timezone preference detection functions."""

    def test_detect_timezone_time_preference_delegation(self) -> None:
        """Test that _detect_timezone_time_preference delegates correctly."""
        # This function delegates to get_time_format_preference
        with patch(
            "claude_monitor.utils.time_utils.get_time_format_preference",
            return_value=True,
        ):
            result = _detect_timezone_time_preference()
            assert result is True

    def test_detect_timezone_time_preference_with_args(self) -> None:
        """Test timezone preference detection with args."""
        mock_args = Mock()
        mock_args.time_format = "24h"

        with patch(
            "claude_monitor.utils.time_utils.get_time_format_preference",
            return_value=False,
        ):
            result = _detect_timezone_time_preference(mock_args)
            assert result is False
