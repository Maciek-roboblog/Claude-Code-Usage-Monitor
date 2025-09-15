"""Simplified settings management with CLI and last used params only."""

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

import pytz
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from claude_monitor import __version__

logger = logging.getLogger(__name__)


class LastUsedParams:
    """Manages last used parameters persistence (moved from last_used.py)."""

    def __init__(self, config_dir: Optional[Path] = None) -> None:
        """Initialize with config directory."""
        self.config_dir = config_dir or Path.home() / ".claude-monitor"
        self.params_file = self.config_dir / "last_used.json"

    def save(self, settings: "Settings") -> None:
        """Save current settings as last used."""
        try:
            params = {
                "theme": settings.theme,
                "timezone": settings.timezone,
                "time_format": settings.time_format,
                "refresh_rate": settings.refresh_rate,
                "reset_hour": settings.reset_hour,
                "view": settings.view,
                "timestamp": datetime.now().isoformat(),
            }

            if settings.custom_limit_tokens:
                params["custom_limit_tokens"] = settings.custom_limit_tokens

            self.config_dir.mkdir(parents=True, exist_ok=True)

            temp_file = self.params_file.with_suffix(".tmp")
            with open(temp_file, "w") as f:
                json.dump(params, f, indent=2)
            temp_file.replace(self.params_file)

            logger.debug(f"Saved last used params to {self.params_file}")

        except Exception as e:
            logger.warning(f"Failed to save last used params: {e}")

    def load(self) -> Dict[str, Any]:
        """Load last used parameters."""
        if not self.params_file.exists():
            return {}

        try:
            with open(self.params_file) as f:
                params = json.load(f)

            params.pop("timestamp", None)

            logger.debug(f"Loaded last used params from {self.params_file}")
            return params

        except Exception as e:
            logger.warning(f"Failed to load last used params: {e}")
            return {}

    def clear(self) -> None:
        """Clear last used parameters."""
        try:
            if self.params_file.exists():
                self.params_file.unlink()
                logger.debug("Cleared last used params")
        except Exception as e:
            logger.warning(f"Failed to clear last used params: {e}")

    def exists(self) -> bool:
        """Check if last used params exist."""
        return self.params_file.exists()


class Settings(BaseSettings):
    """claude-monitor - Real-time token usage monitoring for Claude AI"""

    model_config = SettingsConfigDict(
        env_file=None,
        env_prefix="",
        case_sensitive=False,
        validate_default=True,
        extra="ignore",
        cli_parse_args=True,
        cli_prog_name="claude-monitor",
        cli_kebab_case=True,
        cli_implicit_flags=True,
    )

    plan: Literal["pro", "max5", "max20", "custom"] = Field(
        default="custom",
        description="Plan type (pro, max5, max20, custom)",
    )

    view: Literal["realtime", "daily", "monthly", "session"] = Field(
        default="realtime",
        description="View mode (realtime, daily, monthly, session)",
    )

    @staticmethod
    def _get_system_timezone() -> str:
        """Lazy import to avoid circular dependencies."""
        from claude_monitor.utils.time_utils import get_system_timezone

        return get_system_timezone()

    @staticmethod
    def _get_system_time_format() -> str:
        """Lazy import to avoid circular dependencies."""
        from claude_monitor.utils.time_utils import get_system_time_format

        return get_system_time_format()

    timezone: str = Field(
        default="auto",
        description="Timezone for display (auto-detected from system). Examples: UTC, America/New_York, Europe/London, Europe/Warsaw, Asia/Tokyo, Australia/Sydney",
    )

    time_format: str = Field(
        default="auto",
        description="Time format (12h or 24h, auto-detected from system)",
    )

    theme: Literal["light", "dark", "classic", "auto"] = Field(
        default="auto",
        description="Display theme (light, dark, classic, auto)",
    )

    custom_limit_tokens: Optional[int] = Field(
        default=None, gt=0, description="Token limit for custom plan"
    )

    refresh_rate: int = Field(
        default=10, ge=1, le=60, description="Refresh rate in seconds"
    )

    refresh_per_second: float = Field(
        default=0.75,
        ge=0.1,
        le=20.0,
        description="Display refresh rate per second (0.1-20 Hz). Higher values use more CPU",
    )

    reset_hour: Optional[int] = Field(
        default=None, ge=0, le=23, description="Reset hour for daily limits (0-23)"
    )

    log_level: str = Field(default="INFO", description="Logging level")

    log_file: Optional[Path] = Field(default=None, description="Log file path")

    debug: bool = Field(
        default=False,
        description="Enable debug logging (equivalent to --log-level DEBUG)",
    )

    version: bool = Field(default=False, description="Show version information")

    clear: bool = Field(default=False, description="Clear saved configuration")

    @field_validator("plan", mode="before")
    @classmethod
    def validate_plan(cls, v: Any) -> str:
        """Validate and normalize plan value."""
        if isinstance(v, str):
            v_lower = v.lower()
            valid_plans = ["pro", "max5", "max20", "custom"]
            if v_lower in valid_plans:
                return v_lower
            raise ValueError(
                f"Invalid plan: {v}. Must be one of: {', '.join(valid_plans)}"
            )
        return v

    @field_validator("view", mode="before")
    @classmethod
    def validate_view(cls, v: Any) -> str:
        """Validate and normalize view value."""
        if isinstance(v, str):
            v_lower = v.lower()
            valid_views = ["realtime", "daily", "monthly", "session"]
            if v_lower in valid_views:
                return v_lower
            raise ValueError(
                f"Invalid view: {v}. Must be one of: {', '.join(valid_views)}"
            )
        return v

    @field_validator("theme", mode="before")
    @classmethod
    def validate_theme(cls, v: Any) -> str:
        """Validate and normalize theme value."""
        if isinstance(v, str):
            v_lower = v.lower()
            valid_themes = ["light", "dark", "classic", "auto"]
            if v_lower in valid_themes:
                return v_lower
            raise ValueError(
                f"Invalid theme: {v}. Must be one of: {', '.join(valid_themes)}"
            )
        return v

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        """Validate timezone."""
        if v not in ["local", "auto"] and v not in pytz.all_timezones:
            raise ValueError(f"Invalid timezone: {v}")
        return v

    @field_validator("time_format")
    @classmethod
    def validate_time_format(cls, v: str) -> str:
        """Validate time format."""
        if v not in ["12h", "24h", "auto"]:
            raise ValueError(
                f"Invalid time format: {v}. Must be '12h', '24h', or 'auto'"
            )
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Invalid log level: {v}")
        return v_upper

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Any,
        init_settings: Any,
        env_settings: Any,
        dotenv_settings: Any,
        file_secret_settings: Any,
    ) -> Tuple[Any, ...]:
        """Custom sources - only init and last used."""
        _ = (
            settings_cls,
            env_settings,
            dotenv_settings,
            file_secret_settings,
        )
        return (init_settings,)

    @classmethod
    def load_with_last_used(cls, argv: Optional[List[str]] = None) -> "Settings":
        """Load settings with last used params support (default behavior)."""
        if argv and "--version" in argv:
            print(f"claude-monitor {__version__}")
            import sys

            sys.exit(0)

        clear_config = argv and "--clear" in argv

        if clear_config:
            last_used = LastUsedParams()
            last_used.clear()
            settings = cls(_cli_parse_args=argv)
        else:
            last_used = LastUsedParams()
            last_params = last_used.load()

            settings = cls(_cli_parse_args=argv)

            cli_provided_fields = set()
            if argv:
                for _i, arg in enumerate(argv):
                    if arg.startswith("--"):
                        field_name = arg[2:].replace("-", "_")
                        if field_name in cls.model_fields:
                            cli_provided_fields.add(field_name)

            for key, value in last_params.items():
                if key == "plan":
                    continue
                if not hasattr(settings, key):
                    continue
                if key not in cli_provided_fields:
                    setattr(settings, key, value)

            if (
                "plan" in cli_provided_fields
                and settings.plan == "custom"
                and "custom_limit_tokens" not in cli_provided_fields
            ):
                settings.custom_limit_tokens = None

        if settings.timezone == "auto":
            settings.timezone = cls._get_system_timezone()
        if settings.time_format == "auto":
            settings.time_format = cls._get_system_time_format()

        if settings.debug:
            settings.log_level = "DEBUG"

        if settings.theme == "auto" or (
            "theme" not in cli_provided_fields and not clear_config
        ):
            from claude_monitor.terminal.themes import (
                BackgroundDetector,
                BackgroundType,
            )

            detector = BackgroundDetector()
            detected_bg = detector.detect_background()

            if detected_bg == BackgroundType.LIGHT:
                settings.theme = "light"
            elif detected_bg == BackgroundType.DARK:
                settings.theme = "dark"
            else:
                settings.theme = "auto"

        if not clear_config:
            last_used = LastUsedParams()
            last_used.save(settings)

        return settings

    def to_namespace(self) -> argparse.Namespace:
        """Convert to argparse.Namespace for compatibility."""
        args = argparse.Namespace()

        args.plan = self.plan
        args.view = self.view
        args.timezone = self.timezone
        args.theme = self.theme
        args.refresh_rate = self.refresh_rate
        args.refresh_per_second = self.refresh_per_second
        args.reset_hour = self.reset_hour
        args.custom_limit_tokens = self.custom_limit_tokens
        args.time_format = self.time_format
        args.log_level = self.log_level
        args.log_file = str(self.log_file) if self.log_file else None
        args.version = self.version

        return args
