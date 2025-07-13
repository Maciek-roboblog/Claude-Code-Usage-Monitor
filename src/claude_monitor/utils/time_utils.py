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
        """
        Detects the user's time format preference from CLI arguments.
        
        Returns:
            True if the CLI specifies 12-hour format, False if 24-hour format, or None if not specified.
        """
        if args and hasattr(args, "time_format"):
            if args.time_format == "12h":
                return True
            elif args.time_format == "24h":
                return False
        return None

    @classmethod
    def detect_from_timezone(cls, timezone_name: str) -> Optional[bool]:
        """
        Infers whether a timezone typically uses the 12-hour or 24-hour time format based on its geographic location, using Babel if available.
        
        Parameters:
            timezone_name (str): The IANA timezone name to analyze.
        
        Returns:
            True if the timezone is associated with a country that predominantly uses the 12-hour format, False if 24-hour, or None if detection is not possible.
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
        """
        Detects whether the system locale prefers a 12-hour or 24-hour time format.
        
        Returns:
            bool: True if the locale uses a 12-hour format, False if it uses a 24-hour format.
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
        """
        Detects the system's preferred time format (12-hour or 24-hour) using platform-specific methods.
        
        Returns:
            str: '12h' if the system uses a 12-hour time format, '24h' if it uses a 24-hour format.
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
        """
        Determines the user's preferred time format (12-hour or 24-hour) using CLI arguments, timezone, or system settings.
        
        Returns:
            bool: True if 12-hour format is preferred, False if 24-hour format is preferred.
        """
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
        """
        Detects and returns the system's current timezone as a string.
        
        Checks the TZ environment variable first, then uses platform-specific methods to determine the timezone on macOS, Linux, or Windows. Returns "UTC" if the timezone cannot be determined.
        """
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
        """
        Detects and returns the system's time format as either "12h" or "24h".
        """
        return TimeFormatDetector.detect_from_system()


class TimezoneHandler:
    """Handles timezone conversions and timestamp parsing."""

    def __init__(self, default_tz: str = "UTC"):
        """
        Initialize the TimezoneHandler with a specified default timezone.
        
        Parameters:
            default_tz (str): The timezone name to use as default. Defaults to "UTC".
        """
        self.default_tz = self._validate_and_get_tz(default_tz)

    def _validate_and_get_tz(self, tz_name: str):
        """
        Validates the given timezone name and returns the corresponding pytz timezone object.
        
        If the timezone name is invalid or unknown, returns UTC.
        """
        try:
            return pytz.timezone(tz_name)
        except pytz.exceptions.UnknownTimeZoneError:
            logger.warning(f"Unknown timezone '{tz_name}', using UTC")
            return pytz.UTC

    def parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """
        Parses a timestamp string in ISO 8601 or common date/time formats and returns a timezone-aware datetime object.
        
        Attempts to interpret the input as an ISO 8601 timestamp (with optional timezone or microseconds), or as one of several common date/time formats. Naive datetimes are localized to the default timezone. Returns `None` if parsing fails.
        
        Parameters:
            timestamp_str (str): The timestamp string to parse.
        
        Returns:
            Optional[datetime]: A timezone-aware datetime object if parsing succeeds, otherwise `None`.
        """
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
        """
        Converts a datetime object to UTC, localizing it to the default timezone if it is naive.
        
        Parameters:
            dt (datetime): The datetime object to convert.
        
        Returns:
            datetime: The UTC-aware datetime object.
        """
        if dt.tzinfo is None:
            dt = self.default_tz.localize(dt)
        return dt.astimezone(pytz.UTC)

    def ensure_timezone(self, dt: datetime) -> datetime:
        """
        Ensures that a datetime object is timezone-aware, localizing it to the default timezone if it is naive.
        
        Parameters:
        	dt (datetime): The datetime object to check and localize if necessary.
        
        Returns:
        	datetime: A timezone-aware datetime object.
        """
        if dt.tzinfo is None:
            return self.default_tz.localize(dt)
        return dt

    def validate_timezone(self, tz_name: str) -> bool:
        """
        Check whether the given timezone name is recognized by pytz.
        
        Parameters:
            tz_name (str): The timezone name to validate.
        
        Returns:
            bool: True if the timezone name is valid, False otherwise.
        """
        try:
            pytz.timezone(tz_name)
            return True
        except pytz.exceptions.UnknownTimeZoneError:
            return False

    def convert_to_timezone(self, dt: datetime, tz_name: str) -> datetime:
        """
        Converts a datetime object to the specified timezone.
        
        If the input datetime is naive, it is first localized to the handler's default timezone before conversion.
        
        Parameters:
            dt (datetime): The datetime object to convert. Naive datetimes are assumed to be in the default timezone.
            tz_name (str): The name of the target timezone.
        
        Returns:
            datetime: The datetime object converted to the specified timezone.
        """
        tz = self._validate_and_get_tz(tz_name)
        if dt.tzinfo is None:
            dt = self.default_tz.localize(dt)
        return dt.astimezone(tz)

    def set_timezone(self, tz_name: str) -> None:
        """
        Sets the default timezone for the handler.
        
        Parameters:
        	tz_name (str): The name of the timezone to set as default.
        """
        self.default_tz = self._validate_and_get_tz(tz_name)

    def to_utc(self, dt: datetime) -> datetime:
        """
        Converts a datetime object to UTC, localizing naive datetimes to the default timezone first.
        
        Parameters:
        	dt (datetime): The datetime object to convert.
        
        Returns:
        	datetime: The UTC-converted datetime object.
        """
        return self.ensure_utc(dt)

    def to_timezone(self, dt: datetime, tz_name: Optional[str] = None) -> datetime:
        """
        Converts a datetime object to the specified timezone, or to the default timezone if none is provided.
        
        Parameters:
        	dt (datetime): The datetime object to convert.
        	tz_name (str, optional): The target timezone name. If not provided, the default timezone is used.
        
        Returns:
        	datetime: The datetime object converted to the target timezone.
        """
        if tz_name is None:
            tz_name = self.default_tz.zone
        return self.convert_to_timezone(dt, tz_name)

    def format_datetime(self, dt: datetime, use_12_hour: Optional[bool] = None) -> str:
        """
        Formats a datetime object as a string with timezone information, using either 12-hour or 24-hour format.
        
        Parameters:
            dt (datetime): The datetime object to format.
            use_12_hour (Optional[bool]): If True, formats in 12-hour format; if False, uses 24-hour format. If None, the preferred format is detected automatically.
        
        Returns:
            str: The formatted datetime string with timezone abbreviation.
        """
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
    """
    Determine the user's preferred time format.
    
    Returns:
        bool: True if 12-hour format is preferred, False if 24-hour format is preferred.
    """
    return TimeFormatDetector.get_preference(args)


def get_system_timezone() -> str:
    """
    Returns the system's current timezone as a string.
    
    If detection fails, defaults to "UTC".
    """
    return SystemTimeDetector.get_timezone()


def get_system_time_format() -> str:
    """
    Return the system's time format as either '12h' or '24h', based on platform-specific detection.
    """
    return SystemTimeDetector.get_time_format()


def format_time(minutes):
    """
    Convert a number of minutes into a human-readable string in hours and minutes.
    
    Parameters:
        minutes (int or float): The total number of minutes to format.
    
    Returns:
        str: A string representing the time in "Xh Ym" or "Xm" format.
    """
    if minutes < 60:
        return f"{int(minutes)}m"
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    if mins == 0:
        return f"{hours}h"
    return f"{hours}h {mins}m"


def percentage(part: float, whole: float, decimal_places: int = 1) -> float:
    """
    Safely calculate the percentage of `part` relative to `whole`, rounded to a specified number of decimal places.
    
    Returns:
        The percentage value as a float, or 0.0 if `whole` is zero.
    """
    if whole == 0:
        return 0.0
    result = (part / whole) * 100
    return round(result, decimal_places)


def format_display_time(dt_obj, use_12h_format=None, include_seconds=True):
    """
    Format a datetime object as a string in 12-hour or 24-hour format, with optional seconds.
    
    Parameters:
        dt_obj (datetime): The datetime object to format.
        use_12h_format (bool, optional): If True, formats in 12-hour format; if False, uses 24-hour format. If None, detects preference automatically.
        include_seconds (bool, optional): If True, includes seconds in the output.
    
    Returns:
        str: The formatted time string.
    """
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
