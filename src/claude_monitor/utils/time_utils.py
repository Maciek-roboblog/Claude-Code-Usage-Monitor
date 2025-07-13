"""Unified time utilities module combining timezone and system time functionality."""

import locale
import logging
import os
import platform
import re
import subprocess
from datetime import datetime
from typing import Optional

import pytz

try:
    from babel.dates import get_timezone_location

    HAS_BABEL = True
except ImportError:
    HAS_BABEL = False

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
    def detect_from_cli(cls, args) -> Optional[bool]:
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
                import winreg

                with winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER, r"Control Panel\International"
                ) as key:
                    time_fmt = winreg.QueryValueEx(key, "sTimeFormat")[0]
                    if "h" in time_fmt and ("tt" in time_fmt or "t" in time_fmt):
                        return "12h"
            except Exception:
                pass

        return "12h" if cls.detect_from_locale() else "24h"

    @classmethod
    def get_preference(cls, args=None, timezone_name=None) -> bool:
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

    def __init__(self, default_tz: str = "UTC"):
        """Initialize with a default timezone."""
        self.default_tz = self._validate_and_get_tz(default_tz)

    def _validate_and_get_tz(self, tz_name: str):
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
                    return self.default_tz.localize(dt)
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
                return self.default_tz.localize(dt)
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
            return self.default_tz.localize(dt)
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
            tz_name = self.default_tz.zone
        return self.convert_to_timezone(dt, tz_name)

    def format_datetime(self, dt: datetime, use_12_hour: Optional[bool] = None) -> str:
        """Format datetime with timezone info."""
        if use_12_hour is None:
            use_12_hour = TimeFormatDetector.get_preference(
                timezone_name=dt.tzinfo.zone if dt.tzinfo else None
            )

        dt = self.ensure_timezone(dt)

        if use_12_hour:
            fmt = "%Y-%m-%d %I:%M:%S %p %Z"
        else:
            fmt = "%Y-%m-%d %H:%M:%S %Z"

        return dt.strftime(fmt)


def get_time_format_preference(args=None) -> bool:
    """Get time format preference - returns True for 12h, False for 24h."""
    return TimeFormatDetector.get_preference(args)


def get_system_timezone() -> str:
    """Get system timezone."""
    return SystemTimeDetector.get_timezone()


def get_system_time_format() -> str:
    """Get system time format ('12h' or '24h')."""
    return SystemTimeDetector.get_time_format()


def format_time(minutes):
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


def format_display_time(dt_obj, use_12h_format=None, include_seconds=True):
    """Central time formatting with 12h/24h support."""
    if use_12h_format is None:
        use_12h_format = get_time_format_preference()

    if use_12h_format:
        if include_seconds:
            try:
                return dt_obj.strftime("%-I:%M:%S %p")
            except ValueError:
                return dt_obj.strftime("%#I:%M:%S %p")
        else:
            try:
                return dt_obj.strftime("%-I:%M %p")
            except ValueError:
                return dt_obj.strftime("%#I:%M %p")
    elif include_seconds:
        return dt_obj.strftime("%H:%M:%S")
    else:
        return dt_obj.strftime("%H:%M")
