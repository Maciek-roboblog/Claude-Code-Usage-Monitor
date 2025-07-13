"""Unified time utilities module combining timezone and system time functionality."""

import locale
import logging
import os
import platform
import re
import subprocess
from datetime import datetime

# Platform-specific imports
from types import ModuleType
from typing import Any, List, Optional, Tuple, Union, cast

import pytz
from pytz import BaseTzInfo

winreg: Union[ModuleType, None]
if platform.system() == "Windows":
    try:
        import winreg
    except ImportError:
        winreg = None
else:
    winreg = None

try:
    from babel.dates import get_timezone_location

    HAS_BABEL = True
except ImportError:
    HAS_BABEL = False

    def get_timezone_location(
        timezone_name: str, locale: str = "en_US"
    ) -> Optional[str]:
        """Fallback function when babel is not available."""
        return None


logger = logging.getLogger(__name__)


class TimeFormatDetector:
    """Unified time format detection using multiple strategies."""

    TWELVE_HOUR_COUNTRIES = {
        "US",
        "CA",
        "AU",
        "NZ",
        "PH",
        "IN",
        "EG",
        "SA",
        "CO",
        "PK",
        "MY",
        "GH",
        "KE",
        "NG",
        "PE",
        "ZA",
        "LK",
        "BD",
        "JO",
        "SG",
        "IE",
        "MT",
        "GB",
    }

    @classmethod
    def detect_from_cli(cls, args: Any) -> Optional[bool]:
        """Detect from CLI arguments.

        Returns:
            True for 12h format, False for 24h, None if not specified
        """
        if args and hasattr(args, "time_format"):
            if args.time_format == "12h":
                return True
            elif args.time_format == "24h":
                return False
        return None

    @classmethod
    def detect_from_timezone(cls, timezone_name: str) -> Optional[bool]:
        """Detect using Babel/timezone data.

        Returns:
            True for 12h format, False for 24h, None if cannot determine
        """
        if not HAS_BABEL:
            return None

        try:
            location = get_timezone_location(timezone_name, locale="en_US")
            if location:
                for country_code in cls.TWELVE_HOUR_COUNTRIES:
                    if country_code in location or location.endswith(country_code):
                        return True
            return False
        except Exception:
            return None

    @classmethod
    def detect_from_locale(cls) -> bool:
        """Detect from system locale.

        Returns:
            True for 12h format, False for 24h
        """
        try:
            locale.setlocale(locale.LC_TIME, "")
            time_str = locale.nl_langinfo(locale.T_FMT_AMPM)
            if time_str:
                return True

            dt_fmt = locale.nl_langinfo(locale.D_T_FMT)
            if "%p" in dt_fmt or "%I" in dt_fmt:
                return True

            return False
        except Exception:
            return False

    @classmethod
    def detect_from_system(cls) -> str:
        """Platform-specific system detection.

        Returns:
            '12h' or '24h'
        """
        system = platform.system()

        if system == "Darwin":
            try:
                result = subprocess.run(
                    ["defaults", "read", "NSGlobalDomain", "AppleICUForce12HourTime"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if result.returncode == 0 and result.stdout.strip() == "1":
                    return "12h"

                date_output = subprocess.run(
                    ["date", "+%r"], capture_output=True, text=True, check=True
                ).stdout.strip()
                if "AM" in date_output or "PM" in date_output:
                    return "12h"
            except Exception:
                pass

        elif system == "Linux":
            try:
                result = subprocess.run(
                    ["locale", "LC_TIME"], capture_output=True, text=True, check=True
                )
                lc_time = result.stdout.strip().split("=")[-1].strip('"')
                if lc_time and any(x in lc_time for x in ["en_US", "en_CA", "en_AU"]):
                    return "12h"
            except Exception:
                pass

        elif system == "Windows":
            try:
                # Windows registry detection - only available on Windows platform
                if platform.system() == "Windows" and winreg is not None:
                    with winreg.OpenKey(
                        winreg.HKEY_CURRENT_USER, r"Control Panel\International"
                    ) as key:
                        time_fmt, _ = winreg.QueryValueEx(key, "sTimeFormat")
                        if (
                            isinstance(time_fmt, str)
                            and "h" in time_fmt
                            and ("tt" in time_fmt or "t" in time_fmt)
                        ):
                            return "12h"
            except (ImportError, OSError, Exception):
                pass

        return "12h" if cls.detect_from_locale() else "24h"

    @classmethod
    def get_preference(
        cls, args: Optional[Any] = None, timezone_name: Optional[str] = None
    ) -> bool:
        """Main entry point - returns True for 12h, False for 24h."""
        cli_pref = cls.detect_from_cli(args)
        if cli_pref is not None:
            return cli_pref

        if timezone_name:
            tz_pref = cls.detect_from_timezone(timezone_name)
            if tz_pref is not None:
                return tz_pref

        return cls.detect_from_system() == "12h"


class SystemTimeDetector:
    """System timezone and time format detection."""

    @staticmethod
    def get_timezone() -> str:
        """Detect system timezone."""
        tz = os.environ.get("TZ")
        if tz:
            return tz

        system = platform.system()

        if system == "Darwin":
            try:
                result = subprocess.run(
                    ["readlink", "/etc/localtime"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                tz_path = result.stdout.strip()
                if "zoneinfo/" in tz_path:
                    return tz_path.split("zoneinfo/")[-1]
            except Exception:
                pass

        elif system == "Linux":
            if os.path.exists("/etc/timezone"):
                try:
                    with open("/etc/timezone", "r") as f:
                        tz = f.read().strip()
                        if tz:
                            return tz
                except Exception:
                    pass

            try:
                result = subprocess.run(
                    ["timedatectl", "show", "-p", "Timezone", "--value"],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                tz = result.stdout.strip()
                if tz:
                    return tz
            except Exception:
                pass

        elif system == "Windows":
            try:
                subprocess.run(
                    ["tzutil", "/g"], capture_output=True, text=True, check=True
                )
            except Exception:
                pass

        return "UTC"

    @staticmethod
    def get_time_format() -> str:
        """Detect system time format ('12h' or '24h')."""
        return TimeFormatDetector.detect_from_system()


class TimezoneHandler:
    """Handles timezone conversions and timestamp parsing."""

    def __init__(self, default_tz: str = "UTC") -> None:
        """Initialize with a default timezone."""
        self.default_tz: BaseTzInfo = self._validate_and_get_tz(default_tz)

    def _validate_and_get_tz(self, tz_name: str) -> BaseTzInfo:
        """Validate and return pytz timezone object."""
        try:
            return pytz.timezone(tz_name)
        except pytz.exceptions.UnknownTimeZoneError:
            logger.warning(f"Unknown timezone '{tz_name}', using UTC")
            return pytz.UTC

    def parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Parse various timestamp formats."""
        if not timestamp_str:
            return None

        iso_tz_pattern = (
            r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(\.\d+)?(Z|[+-]\d{2}:\d{2})?"
        )
        match = re.match(iso_tz_pattern, timestamp_str)
        if match:
            try:
                base_str = match.group(1)
                microseconds = match.group(2) or ""
                tz_str = match.group(3) or ""

                dt = datetime.fromisoformat(base_str + microseconds)

                if tz_str == "Z":
                    return dt.replace(tzinfo=pytz.UTC)
                elif tz_str:
                    return datetime.fromisoformat(timestamp_str)
                else:
                    return cast(datetime, self.default_tz.localize(dt))
            except Exception as e:
                logger.debug(f"Failed to parse ISO timestamp: {e}")

        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y/%m/%d %H:%M:%S",
            "%d/%m/%Y %H:%M:%S",
            "%m/%d/%Y %H:%M:%S",
            "%Y-%m-%d",
            "%Y/%m/%d",
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(timestamp_str, fmt)
                return cast(datetime, self.default_tz.localize(dt))
            except ValueError:
                continue

        return None

    def ensure_utc(self, dt: datetime) -> datetime:
        """Convert datetime to UTC."""
        if dt.tzinfo is None:
            dt = self.default_tz.localize(dt)
        return dt.astimezone(pytz.UTC)

    def ensure_timezone(self, dt: datetime) -> datetime:
        """Ensure datetime has timezone info."""
        if dt.tzinfo is None:
            return cast(datetime, self.default_tz.localize(dt))
        return dt

    def validate_timezone(self, tz_name: str) -> bool:
        """Check if timezone name is valid."""
        try:
            pytz.timezone(tz_name)
            return True
        except pytz.exceptions.UnknownTimeZoneError:
            return False

    def convert_to_timezone(self, dt: datetime, tz_name: str) -> datetime:
        """Convert datetime to specific timezone."""
        tz = self._validate_and_get_tz(tz_name)
        if dt.tzinfo is None:
            dt = self.default_tz.localize(dt)
        return dt.astimezone(tz)

    def set_timezone(self, tz_name: str) -> None:
        """Set default timezone."""
        self.default_tz = self._validate_and_get_tz(tz_name)

    def to_utc(self, dt: datetime) -> datetime:
        """Convert to UTC (assumes naive datetime is in default tz)."""
        return self.ensure_utc(dt)

    def to_timezone(self, dt: datetime, tz_name: Optional[str] = None) -> datetime:
        """Convert to timezone (defaults to default_tz)."""
        if tz_name is None:
            tz_name = (
                str(self.default_tz.zone) if hasattr(self.default_tz, "zone") else "UTC"
            )
        return self.convert_to_timezone(dt, tz_name)

    def format_datetime(self, dt: datetime, use_12_hour: Optional[bool] = None) -> str:
        """Format datetime with timezone info."""
        if use_12_hour is None:
            use_12_hour = TimeFormatDetector.get_preference(
                timezone_name=(
                    str(dt.tzinfo.zone)
                    if dt.tzinfo and hasattr(dt.tzinfo, "zone")
                    else None
                )
            )

        dt = self.ensure_timezone(dt)

        if use_12_hour:
            fmt = "%Y-%m-%d %I:%M:%S %p %Z"
        else:
            fmt = "%Y-%m-%d %H:%M:%S %Z"

        return dt.strftime(fmt)

    def is_dst(self, dt: datetime, tz_name: Optional[str] = None) -> bool:
        """Check if datetime falls during daylight saving time.

        Args:
            dt: Datetime to check
            tz_name: Timezone name (defaults to default_tz)

        Returns:
            True if during DST, False otherwise
        """
        if tz_name is None:
            tz = self.default_tz
        else:
            tz = self._validate_and_get_tz(tz_name)

        # Ensure datetime has timezone info
        if dt.tzinfo is None:
            dt = tz.localize(dt)
        else:
            dt = dt.astimezone(tz)

        # Check if DST is in effect
        return bool(dt.dst())

    def get_dst_transitions(
        self, year: int, tz_name: Optional[str] = None
    ) -> List[Tuple[datetime, str]]:
        """Get DST transition dates for a given year.

        Args:
            year: Year to get transitions for
            tz_name: Timezone name (defaults to default_tz)

        Returns:
            List of (transition_datetime, transition_type) tuples
            transition_type can be 'start' or 'end'
        """
        if tz_name is None:
            tz = self.default_tz
        else:
            tz = self._validate_and_get_tz(tz_name)

        transitions: List[Tuple[datetime, str]] = []

        try:
            # Check each month for transitions
            for month in range(1, 13):
                for day in range(1, 32):
                    try:
                        # Check beginning and end of each day
                        dt1 = tz.localize(datetime(year, month, day, 0, 0, 0))
                        dt2 = tz.localize(datetime(year, month, day, 23, 59, 59))

                        dst1 = bool(dt1.dst())
                        dst2 = bool(dt2.dst())

                        if dst1 != dst2:
                            # DST transition occurred on this day
                            transition_type = "start" if dst2 else "end"
                            transitions.append((dt1.replace(hour=12), transition_type))

                    except (
                        ValueError,
                        pytz.exceptions.NonExistentTimeError,
                        pytz.exceptions.AmbiguousTimeError,
                    ):
                        # Skip invalid dates or transition times
                        continue

        except Exception as e:
            logger.debug(f"Error getting DST transitions: {e}")

        return transitions

    def handle_ambiguous_time(
        self, dt: datetime, tz_name: Optional[str] = None, prefer_dst: bool = True
    ) -> datetime:
        """Handle ambiguous times during DST transitions.

        Args:
            dt: Naive datetime that may be ambiguous
            tz_name: Timezone name (defaults to default_tz)
            prefer_dst: Whether to prefer DST interpretation for ambiguous times

        Returns:
            Localized datetime with resolved ambiguity
        """
        if tz_name is None:
            tz = self.default_tz
        else:
            tz = self._validate_and_get_tz(tz_name)

        try:
            # Try normal localization first
            return cast(datetime, tz.localize(dt))
        except pytz.exceptions.AmbiguousTimeError:
            # Handle ambiguous time by choosing DST preference
            return cast(datetime, tz.localize(dt, is_dst=prefer_dst))
        except pytz.exceptions.NonExistentTimeError:
            # Handle non-existent time by moving forward one hour
            dt_adjusted = dt.replace(hour=dt.hour + 1)
            return cast(datetime, tz.localize(dt_adjusted))

    def safe_localize(self, dt: datetime, tz_name: Optional[str] = None) -> datetime:
        """Safely localize a naive datetime, handling DST edge cases.

        Args:
            dt: Naive datetime to localize
            tz_name: Timezone name (defaults to default_tz)

        Returns:
            Safely localized datetime
        """
        if dt.tzinfo is not None:
            return dt  # Already has timezone info

        if tz_name is None:
            tz = self.default_tz
        else:
            tz = self._validate_and_get_tz(tz_name)

        try:
            return cast(datetime, tz.localize(dt))
        except (
            pytz.exceptions.AmbiguousTimeError,
            pytz.exceptions.NonExistentTimeError,
        ):
            # Use the ambiguous time handler for edge cases
            return self.handle_ambiguous_time(dt, tz_name)


def get_time_format_preference(args: Optional[Any] = None) -> bool:
    """Get time format preference - returns True for 12h, False for 24h."""
    return TimeFormatDetector.get_preference(args)


def get_system_timezone() -> str:
    """Get system timezone."""
    return SystemTimeDetector.get_timezone()


def get_system_time_format() -> str:
    """Get system time format ('12h' or '24h')."""
    return SystemTimeDetector.get_time_format()


def format_time(minutes: float) -> str:
    """Format minutes into human-readable time (e.g., '3h 45m')."""
    if minutes < 60:
        return f"{int(minutes)}m"
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    if mins == 0:
        return f"{hours}h"
    return f"{hours}h {mins}m"


def percentage(part: float, whole: float, decimal_places: int = 1) -> float:
    """Calculate percentage with safe division.

    Args:
        part: Part value
        whole: Whole value
        decimal_places: Number of decimal places to round to

    Returns:
        Percentage value
    """
    if whole == 0:
        return 0.0
    result = (part / whole) * 100
    return round(result, decimal_places)


def format_display_time(
    dt_obj: datetime,
    use_12h_format: Optional[bool] = None,
    include_seconds: bool = True,
    locale_aware: bool = False,
) -> str:
    """Central time formatting with 12h/24h support and enhanced locale awareness.

    Args:
        dt_obj: Datetime object to format
        use_12h_format: Force 12h format (True) or 24h format (False), None for auto-detect
        include_seconds: Whether to include seconds in output
        locale_aware: Whether to use locale-specific formatting

    Returns:
        Formatted time string
    """
    if use_12h_format is None:
        use_12h_format = get_time_format_preference()

    # Determine format strings based on platform and locale
    if locale_aware:
        try:
            # Try to use locale-specific formatting
            locale.setlocale(locale.LC_TIME, "")
            if use_12h_format:
                fmt = (
                    locale.nl_langinfo(locale.T_FMT_AMPM)
                    if include_seconds
                    else "%I:%M %p"
                )
            else:
                fmt = locale.nl_langinfo(locale.T_FMT) if include_seconds else "%H:%M"
        except (locale.Error, AttributeError):
            # Fallback to standard formatting
            locale_aware = False

    if not locale_aware:
        # Standard formatting with cross-platform compatibility
        if use_12h_format:
            if include_seconds:
                # Handle platform-specific hour formatting
                try:
                    return dt_obj.strftime(
                        "%-I:%M:%S %p"
                    )  # Unix-style (no leading zero)
                except ValueError:
                    try:
                        return dt_obj.strftime(
                            "%#I:%M:%S %p"
                        )  # Windows-style (no leading zero)
                    except ValueError:
                        return dt_obj.strftime(
                            "%I:%M:%S %p"
                        )  # Standard (with leading zero)
            else:
                try:
                    return dt_obj.strftime("%-I:%M %p")
                except ValueError:
                    try:
                        return dt_obj.strftime("%#I:%M %p")
                    except ValueError:
                        return dt_obj.strftime("%I:%M %p")
        elif include_seconds:
            return dt_obj.strftime("%H:%M:%S")
        else:
            return dt_obj.strftime("%H:%M")

    # Use locale-aware formatting
    try:
        return dt_obj.strftime(fmt)
    except (ValueError, TypeError):
        # Fallback to basic formatting if locale formatting fails
        return format_display_time(
            dt_obj, use_12h_format, include_seconds, locale_aware=False
        )


def create_timezone_aware_datetime(
    year: int,
    month: int,
    day: int,
    hour: int = 0,
    minute: int = 0,
    second: int = 0,
    microsecond: int = 0,
    tz_name: str = "UTC",
    handle_dst: bool = True,
) -> datetime:
    """Create a timezone-aware datetime with DST handling.

    Args:
        year, month, day, hour, minute, second, microsecond: Datetime components
        tz_name: Timezone name
        handle_dst: Whether to handle DST edge cases automatically

    Returns:
        Timezone-aware datetime object
    """
    handler = TimezoneHandler(tz_name)
    naive_dt = datetime(year, month, day, hour, minute, second, microsecond)

    if handle_dst:
        return handler.safe_localize(naive_dt, tz_name)
    else:
        return cast(datetime, handler.default_tz.localize(naive_dt))


def get_timezone_info(tz_name: str) -> dict[str, Any]:
    """Get comprehensive timezone information.

    Args:
        tz_name: Timezone name

    Returns:
        Dictionary with timezone information including DST status, offset, etc.
    """
    handler = TimezoneHandler(tz_name)
    now = datetime.now()
    localized_now = handler.safe_localize(now, tz_name)

    info = {
        "timezone_name": tz_name,
        "is_valid": handler.validate_timezone(tz_name),
        "current_offset": str(localized_now.utcoffset()),
        "is_dst": handler.is_dst(localized_now, tz_name),
        "dst_offset": str(localized_now.dst()),
        "formatted_time_12h": handler.format_datetime(localized_now, use_12_hour=True),
        "formatted_time_24h": handler.format_datetime(localized_now, use_12_hour=False),
    }

    # Add DST transitions for current year
    try:
        transitions = handler.get_dst_transitions(now.year, tz_name)
        info["dst_transitions"] = [
            (dt.isoformat(), transition_type) for dt, transition_type in transitions
        ]
    except Exception:
        info["dst_transitions"] = []

    return info
