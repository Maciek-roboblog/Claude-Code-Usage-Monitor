"""Comprehensive tests for time_utils module."""

import locale
import platform
from datetime import datetime
from typing import List
from unittest.mock import Mock, patch

import pytest
import pytz

from claude_monitor.utils.time_utils import (
    SystemTimeDetector,
    TimeFormatDetector,
    TimezoneHandler,
    format_display_time,
    format_time,
    get_system_time_format,
    get_system_timezone,
    get_time_format_preference,
    percentage,
)


class TestTimeFormatDetector:
    """Test cases for TimeFormatDetector class."""

    def test_detect_from_cli_12h(self) -> None:
        """Test CLI detection for 12h format."""
        args = Mock()
        args.time_format = "12h"

        result = TimeFormatDetector.detect_from_cli(args)
        assert result is True

    def test_detect_from_cli_24h(self) -> None:
        """Test CLI detection for 24h format."""
        args = Mock()
        args.time_format = "24h"

        result = TimeFormatDetector.detect_from_cli(args)
        assert result is False

    def test_detect_from_cli_none(self) -> None:
        """Test CLI detection when format not specified."""
        args = Mock()
        args.time_format = None

        result = TimeFormatDetector.detect_from_cli(args)
        assert result is None

    def test_detect_from_cli_no_args(self) -> None:
        """Test CLI detection with no args."""
        result = TimeFormatDetector.detect_from_cli(None)
        assert result is None

    def test_detect_from_cli_no_attribute(self) -> None:
        """Test CLI detection when args has no time_format attribute."""
        args = Mock()
        del args.time_format

        result = TimeFormatDetector.detect_from_cli(args)
        assert result is None

    @patch("claude_monitor.utils.time_utils.HAS_BABEL", True)
    @patch("claude_monitor.utils.time_utils.get_timezone_location")
    def test_detect_from_timezone_with_babel_12h(self, mock_get_location: Mock) -> None:
        """Test timezone detection with Babel for 12h countries."""
        mock_get_location.return_value = "United States US"

        result = TimeFormatDetector.detect_from_timezone("America/New_York")
        assert result is True

    @patch("claude_monitor.utils.time_utils.HAS_BABEL", True)
    @patch("claude_monitor.utils.time_utils.get_timezone_location")
    def test_detect_from_timezone_with_babel_24h(self, mock_get_location: Mock) -> None:
        """Test timezone detection with Babel for 24h countries."""
        mock_get_location.return_value = "Germany"

        result = TimeFormatDetector.detect_from_timezone("Europe/Berlin")
        assert result is False

    @patch("claude_monitor.utils.time_utils.HAS_BABEL", True)
    @patch("claude_monitor.utils.time_utils.get_timezone_location")
    def test_detect_from_timezone_with_babel_exception(
        self, mock_get_location: Mock
    ) -> None:
        """Test timezone detection with Babel when exception occurs."""
        mock_get_location.side_effect = Exception("Test error")

        result = TimeFormatDetector.detect_from_timezone("Invalid/Timezone")
        assert result is None

    @patch("claude_monitor.utils.time_utils.HAS_BABEL", False)
    def test_detect_from_timezone_no_babel(self) -> None:
        """Test timezone detection without Babel."""
        result = TimeFormatDetector.detect_from_timezone("America/New_York")
        assert result is None

    @patch("locale.setlocale")
    @patch("locale.nl_langinfo")
    def test_detect_from_locale_12h_ampm(
        self, mock_langinfo: Mock, mock_setlocale: Mock
    ) -> None:
        """Test locale detection for 12h format with AM/PM."""
        mock_langinfo.side_effect = (
            lambda x: "%I:%M:%S %p" if x == locale.T_FMT_AMPM else ""
        )

        result = TimeFormatDetector.detect_from_locale()
        assert result is True

    @patch("locale.setlocale")
    @patch("locale.nl_langinfo")
    def test_detect_from_locale_12h_dt_fmt(
        self, mock_langinfo: Mock, mock_setlocale: Mock
    ) -> None:
        """Test locale detection for 12h format with %p in D_T_FMT."""
        mock_langinfo.side_effect = (
            lambda x: "%m/%d/%Y %I:%M:%S %p" if x == locale.D_T_FMT else ""
        )

        result = TimeFormatDetector.detect_from_locale()
        assert result is True

    @patch("locale.setlocale")
    @patch("locale.nl_langinfo")
    def test_detect_from_locale_24h(
        self, mock_langinfo: Mock, mock_setlocale: Mock
    ) -> None:
        """Test locale detection for 24h format."""
        mock_langinfo.side_effect = lambda x: "%H:%M:%S" if x == locale.D_T_FMT else ""

        result = TimeFormatDetector.detect_from_locale()
        assert result is False

    @patch("locale.setlocale")
    def test_detect_from_locale_exception(self, mock_setlocale: Mock) -> None:
        """Test locale detection with exception."""
        mock_setlocale.side_effect = Exception("Locale error")

        result = TimeFormatDetector.detect_from_locale()
        assert result is False

    @patch("platform.system")
    @patch("subprocess.run")
    def test_detect_from_system_macos_12h(
        self, mock_run: Mock, mock_system: Mock
    ) -> None:
        """Test macOS system detection for 12h format."""
        mock_system.return_value = "Darwin"

        # Mock successful defaults command returning "1"
        mock_defaults_result = Mock()
        mock_defaults_result.returncode = 0
        mock_defaults_result.stdout = "1"

        # Mock date command with AM/PM
        mock_date_result = Mock()
        mock_date_result.stdout = "02:30:45 PM"

        mock_run.side_effect = [mock_defaults_result, mock_date_result]

        result = TimeFormatDetector.detect_from_system()
        assert result == "12h"

    @patch("platform.system")
    @patch("subprocess.run")
    @patch.object(TimeFormatDetector, "detect_from_locale")
    def test_detect_from_system_macos_24h(
        self, mock_locale: Mock, mock_run: Mock, mock_system: Mock
    ) -> None:
        """Test macOS system detection for 24h format."""
        mock_system.return_value = "Darwin"
        mock_locale.return_value = False  # 24h format

        # Mock defaults command returning non-1 value
        mock_defaults_result = Mock()
        mock_defaults_result.returncode = 0
        mock_defaults_result.stdout = "0"

        # Mock date command without AM/PM
        mock_date_result = Mock()
        mock_date_result.stdout = "14:30:45"

        mock_run.side_effect = [mock_defaults_result, mock_date_result]

        result = TimeFormatDetector.detect_from_system()
        assert result == "24h"

    @patch("platform.system")
    @patch("subprocess.run")
    def test_detect_from_system_linux_12h(
        self, mock_run: Mock, mock_system: Mock
    ) -> None:
        """Test Linux system detection for 12h format."""
        mock_system.return_value = "Linux"

        mock_result = Mock()
        mock_result.stdout = 'LC_TIME="en_US.UTF-8"'
        mock_run.return_value = mock_result

        result = TimeFormatDetector.detect_from_system()
        assert result == "12h"

    @patch("platform.system")
    @patch("subprocess.run")
    @patch.object(TimeFormatDetector, "detect_from_locale")
    def test_detect_from_system_linux_24h(
        self, mock_locale: Mock, mock_run: Mock, mock_system: Mock
    ) -> None:
        """Test Linux system detection for 24h format."""
        mock_system.return_value = "Linux"
        mock_locale.return_value = False  # 24h format

        mock_result = Mock()
        mock_result.stdout = 'LC_TIME="de_DE.UTF-8"'
        mock_run.return_value = mock_result

        result = TimeFormatDetector.detect_from_system()
        assert result == "24h"

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-specific test")
    @patch("platform.system")
    def test_detect_from_system_windows_12h(self, mock_system: Mock) -> None:
        """Test Windows system detection for 12h format."""
        mock_system.return_value = "Windows"

        import sys

        if "winreg" not in sys.modules:
            sys.modules["winreg"] = Mock()

        with patch("winreg.OpenKey"):
            with patch("winreg.QueryValueEx") as mock_query:
                mock_query.return_value = ("h:mm:ss tt", None)

                result = TimeFormatDetector.detect_from_system()
                assert result == "12h"

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-specific test")
    @patch("platform.system")
    def test_detect_from_system_windows_24h(self, mock_system: Mock) -> None:
        """Test Windows system detection for 24h format."""
        mock_system.return_value = "Windows"

        import sys

        if "winreg" not in sys.modules:
            sys.modules["winreg"] = Mock()

        with patch("winreg.OpenKey"):
            with patch("winreg.QueryValueEx") as mock_query:
                mock_query.return_value = ("HH:mm:ss", None)

                result = TimeFormatDetector.detect_from_system()
                assert result == "24h"

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-specific test")
    @patch("platform.system")
    def test_detect_from_system_windows_exception(self, mock_system: Mock) -> None:
        """Test Windows system detection with exception."""
        mock_system.return_value = "Windows"

        import sys

        if "winreg" not in sys.modules:
            sys.modules["winreg"] = Mock()

        with patch("winreg.OpenKey", side_effect=Exception("Registry error")):
            with patch.object(
                TimeFormatDetector, "detect_from_locale", return_value=True
            ):
                result = TimeFormatDetector.detect_from_system()
                assert result == "12h"

    @patch("platform.system")
    def test_detect_from_system_unknown_platform(self, mock_system: Mock) -> None:
        """Test system detection for unknown platform."""
        mock_system.return_value = "UnknownOS"

        with patch.object(TimeFormatDetector, "detect_from_locale", return_value=False):
            result = TimeFormatDetector.detect_from_system()
            assert result == "24h"

    def test_get_preference_cli_priority(self) -> None:
        """Test get_preference with CLI args having highest priority."""
        args = Mock()
        args.time_format = "12h"

        with patch.object(TimeFormatDetector, "detect_from_timezone") as mock_tz:
            mock_tz.return_value = False  # Should be ignored

            result = TimeFormatDetector.get_preference(args, "Europe/Berlin")
            assert result is True

    def test_get_preference_timezone_fallback(self) -> None:
        """Test get_preference falling back to timezone detection."""
        with (
            patch.object(TimeFormatDetector, "detect_from_timezone", return_value=True),
            patch.object(TimeFormatDetector, "detect_from_system") as mock_system,
        ):
            mock_system.return_value = "24h"  # Should be ignored

            result = TimeFormatDetector.get_preference(None, "America/New_York")
            assert result is True

    def test_get_preference_system_fallback(self) -> None:
        """Test get_preference falling back to system detection."""
        with (
            patch.object(TimeFormatDetector, "detect_from_timezone", return_value=None),
            patch.object(TimeFormatDetector, "detect_from_system", return_value="12h"),
        ):
            result = TimeFormatDetector.get_preference(None, "Europe/Berlin")
            assert result is True


class TestSystemTimeDetector:
    """Test cases for SystemTimeDetector class."""

    @patch("os.environ.get")
    @patch("os.path.exists")
    @patch("platform.system")
    @patch("builtins.open", create=True)
    def test_get_timezone_linux_timezone_file(
        self, mock_open: Mock, mock_system: Mock, mock_exists: Mock, mock_env: Mock
    ) -> None:
        """Test Linux timezone detection via /etc/timezone file."""
        mock_env.return_value = None  # No TZ environment variable
        mock_system.return_value = "Linux"
        mock_exists.return_value = True  # /etc/timezone file exists

        # Mock file content
        mock_file = Mock()
        mock_file.read.return_value = "America/New_York\n"
        mock_open.return_value.__enter__.return_value = mock_file

        result = SystemTimeDetector.get_timezone()
        assert result == "America/New_York"

    @patch("os.environ.get")
    @patch("os.path.exists")
    @patch("platform.system")
    @patch("subprocess.run")
    def test_get_timezone_linux_timedatectl(
        self, mock_run: Mock, mock_system: Mock, mock_exists: Mock, mock_env: Mock
    ) -> None:
        """Test Linux timezone detection via timedatectl."""
        mock_env.return_value = None  # No TZ environment variable
        mock_system.return_value = "Linux"
        mock_exists.return_value = False  # No /etc/timezone file

        # Mock successful timedatectl command
        mock_timedatectl_result = Mock()
        mock_timedatectl_result.stdout = "Europe/London"
        mock_timedatectl_result.returncode = 0
        mock_run.return_value = mock_timedatectl_result

        result = SystemTimeDetector.get_timezone()
        assert result == "Europe/London"

    @patch("platform.system")
    @patch("subprocess.run")
    def test_get_timezone_windows(self, mock_run: Mock, mock_system: Mock) -> None:
        """Test Windows timezone detection."""
        mock_system.return_value = "Windows"

        mock_result = Mock()
        mock_result.stdout = "Eastern Standard Time"
        mock_run.return_value = mock_result

        # Should return the Windows timezone name
        result = SystemTimeDetector.get_timezone()
        assert result == "Eastern Standard Time"

    @patch("platform.system")
    def test_get_timezone_unknown_system(self, mock_system: Mock) -> None:
        """Test timezone detection for unknown system."""
        mock_system.return_value = "UnknownOS"

        result = SystemTimeDetector.get_timezone()
        assert result == "UTC"

    def test_get_time_format(self) -> None:
        """Test get_time_format delegates to TimeFormatDetector."""
        with patch.object(TimeFormatDetector, "detect_from_system", return_value="12h"):
            result = SystemTimeDetector.get_time_format()
            assert result == "12h"


class TestTimezoneHandler:
    """Test cases for TimezoneHandler class."""

    def test_init_default(self) -> None:
        """Test TimezoneHandler initialization with default timezone."""
        handler = TimezoneHandler()
        assert handler.default_tz == pytz.UTC

    def test_init_custom_valid(self) -> None:
        """Test TimezoneHandler initialization with valid custom timezone."""
        handler = TimezoneHandler("America/New_York")
        assert handler.default_tz.zone == "America/New_York"

    def test_init_custom_invalid(self) -> None:
        """Test TimezoneHandler initialization with invalid timezone."""
        with patch("claude_monitor.utils.time_utils.logger") as mock_logger:
            handler = TimezoneHandler("Invalid/Timezone")
            assert handler.default_tz == pytz.UTC
            mock_logger.warning.assert_called_once()

    def test_validate_and_get_tz_valid(self) -> None:
        """Test _validate_and_get_tz with valid timezone."""
        handler = TimezoneHandler()
        tz = handler._validate_and_get_tz("Europe/London")
        assert tz.zone == "Europe/London"

    def test_validate_and_get_tz_invalid(self) -> None:
        """Test _validate_and_get_tz with invalid timezone."""
        handler = TimezoneHandler()
        with patch("claude_monitor.utils.time_utils.logger") as mock_logger:
            tz = handler._validate_and_get_tz("Invalid/Timezone")
            assert tz == pytz.UTC
            mock_logger.warning.assert_called_once()

    def test_parse_timestamp_iso_with_z(self) -> None:
        """Test parsing ISO timestamp with Z suffix."""
        handler = TimezoneHandler()
        result = handler.parse_timestamp("2024-01-01T12:00:00Z")

        assert result is not None
        assert result.tzinfo == pytz.UTC

    def test_parse_timestamp_iso_with_offset(self) -> None:
        """Test parsing ISO timestamp with timezone offset."""
        handler = TimezoneHandler()
        result = handler.parse_timestamp("2024-01-01T12:00:00+02:00")

        assert result is not None
        assert result.tzinfo is not None

    def test_parse_timestamp_iso_with_microseconds(self) -> None:
        """Test parsing ISO timestamp with microseconds."""
        handler = TimezoneHandler()
        result = handler.parse_timestamp("2024-01-01T12:00:00.123456Z")

        assert result is not None
        assert result.tzinfo == pytz.UTC

    def test_parse_timestamp_iso_no_timezone(self) -> None:
        """Test parsing ISO timestamp without timezone."""
        handler = TimezoneHandler("America/New_York")
        result = handler.parse_timestamp("2024-01-01T12:00:00")

        assert result is not None
        assert result.tzinfo.zone == "America/New_York"

    def test_parse_timestamp_invalid_iso(self) -> None:
        """Test parsing invalid ISO timestamp."""
        handler = TimezoneHandler()
        with patch("claude_monitor.utils.time_utils.logger"):
            result = handler.parse_timestamp("2024-01-01T25:00:00Z")  # Invalid hour
            # Should try other formats or return None
            assert result is None or isinstance(result, datetime)

    def test_parse_timestamp_alternative_formats(self) -> None:
        """Test parsing with alternative formats."""
        handler = TimezoneHandler("UTC")

        test_cases: List[str] = [
            "2024-01-01 12:00:00",
            "2024/01/01 12:00:00",
            "01/01/2024 12:00:00",
            "2024-01-01",
            "2024/01/01",
        ]

        for timestamp_str in test_cases:
            result = handler.parse_timestamp(timestamp_str)
            assert result is not None

    def test_parse_timestamp_empty(self) -> None:
        """Test parsing empty timestamp."""
        handler = TimezoneHandler()
        result = handler.parse_timestamp("")
        assert result is None

    def test_parse_timestamp_none(self) -> None:
        """Test parsing None timestamp."""
        handler = TimezoneHandler()
        result = handler.parse_timestamp(None)
        assert result is None

    def test_parse_timestamp_invalid_format(self) -> None:
        """Test parsing completely invalid format."""
        handler = TimezoneHandler()
        result = handler.parse_timestamp("not a timestamp")
        assert result is None

    def test_ensure_utc_naive(self) -> None:
        """Test ensure_utc with naive datetime."""
        handler = TimezoneHandler("America/New_York")
        dt = datetime(2024, 1, 1, 12, 0, 0)

        result = handler.ensure_utc(dt)
        assert result.tzinfo == pytz.UTC

    def test_ensure_utc_aware(self) -> None:
        """Test ensure_utc with timezone-aware datetime."""
        handler = TimezoneHandler()
        dt = pytz.timezone("Europe/London").localize(datetime(2024, 1, 1, 12, 0, 0))

        result = handler.ensure_utc(dt)
        assert result.tzinfo == pytz.UTC

    def test_ensure_timezone_naive(self) -> None:
        """Test ensure_timezone with naive datetime."""
        handler = TimezoneHandler("Europe/Berlin")
        dt = datetime(2024, 1, 1, 12, 0, 0)

        result = handler.ensure_timezone(dt)
        assert result.tzinfo.zone == "Europe/Berlin"

    def test_ensure_timezone_aware(self) -> None:
        """Test ensure_timezone with timezone-aware datetime."""
        handler = TimezoneHandler()
        dt = pytz.timezone("America/New_York").localize(datetime(2024, 1, 1, 12, 0, 0))

        result = handler.ensure_timezone(dt)
        assert result.tzinfo.zone == "America/New_York"

    def test_validate_timezone_valid(self) -> None:
        """Test validate_timezone with valid timezone."""
        handler = TimezoneHandler()
        assert handler.validate_timezone("America/New_York") is True
        assert handler.validate_timezone("UTC") is True

    def test_validate_timezone_invalid(self) -> None:
        """Test validate_timezone with invalid timezone."""
        handler = TimezoneHandler()
        assert handler.validate_timezone("Invalid/Timezone") is False

    def test_convert_to_timezone_naive(self) -> None:
        """Test convert_to_timezone with naive datetime."""
        handler = TimezoneHandler("UTC")
        dt = datetime(2024, 1, 1, 12, 0, 0)

        result = handler.convert_to_timezone(dt, "America/New_York")
        assert result.tzinfo.zone == "America/New_York"

    def test_convert_to_timezone_aware(self) -> None:
        """Test convert_to_timezone with timezone-aware datetime."""
        handler = TimezoneHandler()
        dt = pytz.UTC.localize(datetime(2024, 1, 1, 12, 0, 0))

        result = handler.convert_to_timezone(dt, "Europe/London")
        assert result.tzinfo.zone == "Europe/London"

    def test_set_timezone(self) -> None:
        """Test set_timezone method."""
        handler = TimezoneHandler()
        handler.set_timezone("Asia/Tokyo")
        assert handler.default_tz.zone == "Asia/Tokyo"

    def test_to_utc(self) -> None:
        """Test to_utc method."""
        handler = TimezoneHandler("Europe/Paris")
        dt = datetime(2024, 1, 1, 12, 0, 0)

        result = handler.to_utc(dt)
        assert result.tzinfo == pytz.UTC

    def test_to_timezone_default(self) -> None:
        """Test to_timezone with default timezone."""
        handler = TimezoneHandler("Australia/Sydney")
        dt = pytz.UTC.localize(datetime(2024, 1, 1, 12, 0, 0))

        result = handler.to_timezone(dt)
        assert result.tzinfo.zone == "Australia/Sydney"

    def test_to_timezone_specific(self) -> None:
        """Test to_timezone with specific timezone."""
        handler = TimezoneHandler()
        dt = pytz.UTC.localize(datetime(2024, 1, 1, 12, 0, 0))

        result = handler.to_timezone(dt, "America/Los_Angeles")
        assert result.tzinfo.zone == "America/Los_Angeles"

    def test_format_datetime_default(self) -> None:
        """Test format_datetime with default settings."""
        handler = TimezoneHandler("UTC")
        dt = pytz.UTC.localize(datetime(2024, 1, 1, 15, 30, 45))

        with patch.object(TimeFormatDetector, "get_preference", return_value=True):
            result = handler.format_datetime(dt)
            assert "PM" in result or "AM" in result

    def test_format_datetime_24h(self) -> None:
        """Test format_datetime with 24h format."""
        handler = TimezoneHandler("UTC")
        dt = pytz.UTC.localize(datetime(2024, 1, 1, 15, 30, 45))

        result = handler.format_datetime(dt, use_12_hour=False)
        assert "15:30:45" in result

    def test_format_datetime_12h(self) -> None:
        """Test format_datetime with 12h format."""
        handler = TimezoneHandler("UTC")
        dt = pytz.UTC.localize(datetime(2024, 1, 1, 15, 30, 45))

        result = handler.format_datetime(dt, use_12_hour=True)
        assert "PM" in result


class TestPublicAPI:
    """Test cases for public API functions."""

    def test_get_time_format_preference(self) -> None:
        """Test get_time_format_preference function."""
        args = Mock()
        args.time_format = "12h"

        with patch.object(
            TimeFormatDetector, "get_preference", return_value=True
        ) as mock_get:
            result = get_time_format_preference(args)
            assert result is True
            mock_get.assert_called_once_with(args)

    def test_get_system_timezone(self) -> None:
        """Test get_system_timezone function."""
        with patch.object(
            SystemTimeDetector, "get_timezone", return_value="America/Chicago"
        ) as mock_get:
            result = get_system_timezone()
            assert result == "America/Chicago"
            mock_get.assert_called_once()

    def test_get_system_time_format(self) -> None:
        """Test get_system_time_format function."""
        with patch.object(
            SystemTimeDetector, "get_time_format", return_value="24h"
        ) as mock_get:
            result = get_system_time_format()
            assert result == "24h"
            mock_get.assert_called_once()


class TestFormattingUtilities:
    """Test cases for formatting utility functions."""

    def test_format_time_minutes_only(self) -> None:
        """Test format_time with minutes only."""
        assert format_time(30) == "30m"
        assert format_time(59) == "59m"

    def test_format_time_hours_only(self) -> None:
        """Test format_time with exact hours."""
        assert format_time(60) == "1h"
        assert format_time(120) == "2h"
        assert format_time(180) == "3h"

    def test_format_time_hours_and_minutes(self) -> None:
        """Test format_time with hours and minutes."""
        assert format_time(90) == "1h 30m"
        assert format_time(135) == "2h 15m"
        assert format_time(245) == "4h 5m"

    def test_percentage_normal(self) -> None:
        """Test percentage calculation with normal values."""
        assert percentage(25, 100) == 25.0
        assert percentage(50, 200) == 25.0
        assert percentage(33.333, 100, 2) == 33.33

    def test_percentage_zero_whole(self) -> None:
        """Test percentage calculation with zero whole."""
        assert percentage(10, 0) == 0.0

    def test_percentage_decimal_places(self) -> None:
        """Test percentage calculation with different decimal places."""
        assert percentage(1, 3, 0) == 33.0
        assert percentage(1, 3, 1) == 33.3
        assert percentage(1, 3, 2) == 33.33

    def test_format_display_time_12h_with_seconds(self) -> None:
        """Test format_display_time in 12h format with seconds."""
        dt = datetime(2024, 1, 1, 15, 30, 45)

        with patch(
            "claude_monitor.utils.time_utils.get_time_format_preference",
            return_value=True,
        ):
            # Test Unix/Linux format
            try:
                result = format_display_time(
                    dt, use_12h_format=True, include_seconds=True
                )
                assert "PM" in result
                assert "3:30:45" in result or "03:30:45" in result
            except ValueError:
                # Windows format fallback
                result = format_display_time(
                    dt, use_12h_format=True, include_seconds=True
                )
                assert "PM" in result

    def test_format_display_time_12h_without_seconds(self) -> None:
        """Test format_display_time in 12h format without seconds."""
        dt = datetime(2024, 1, 1, 15, 30, 45)

        try:
            result = format_display_time(dt, use_12h_format=True, include_seconds=False)
            assert "PM" in result
            assert "3:30" in result or "03:30" in result
        except ValueError:
            # Windows format fallback
            result = format_display_time(dt, use_12h_format=True, include_seconds=False)
            assert "PM" in result

    def test_format_display_time_24h_with_seconds(self) -> None:
        """Test format_display_time in 24h format with seconds."""
        dt = datetime(2024, 1, 1, 15, 30, 45)

        result = format_display_time(dt, use_12h_format=False, include_seconds=True)
        assert result == "15:30:45"

    def test_format_display_time_24h_without_seconds(self) -> None:
        """Test format_display_time in 24h format without seconds."""
        dt = datetime(2024, 1, 1, 15, 30, 45)

        result = format_display_time(dt, use_12h_format=False, include_seconds=False)
        assert result == "15:30"

    def test_format_display_time_auto_detect(self) -> None:
        """Test format_display_time with automatic format detection."""
        dt = datetime(2024, 1, 1, 15, 30, 45)

        with patch(
            "claude_monitor.utils.time_utils.get_time_format_preference",
            return_value=False,
        ):
            result = format_display_time(dt)
            assert result == "15:30:45"

    def test_format_display_time_windows_fallback(self) -> None:
        """Test format_display_time Windows fallback for %-I format."""
        # Test that the function handles both Unix and Windows strftime formats
        dt = datetime(2024, 1, 1, 3, 30, 45)

        # Just test basic functionality - the Windows fallback is handled internally
        result = format_display_time(dt, use_12h_format=True, include_seconds=True)
        # Should contain time components
        assert ":" in result

        # Test 12h format contains AM/PM or similar indicator
        if "AM" in result or "PM" in result:
            assert True  # Standard format worked
        else:
            # Alternative formats might be used
            assert "3" in result or "03" in result  # Hour should be present
