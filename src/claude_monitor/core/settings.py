"""Simplified settings management with CLI and last used params only."""

import argparse
import json
import logging
import string
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

import pytz
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from claude_monitor import __version__

logger = logging.getLogger(__name__)

_TITLE_FORMAT_KEYS = {"pct", "plan", "used", "limit", "cost", "reset"}


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
                "plan": settings.plan,
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
        populate_by_name=True,
    )

    plan: Literal["pro", "max5", "max20", "team", "custom"] = Field(
        default="custom",
        description="Plan type (pro, max5, max20, team, custom)",
    )

    view: Literal[
        "realtime", "daily", "monthly", "session", "entries", "sessions", "burn-rate"
    ] = Field(
        default="realtime",
        description=(
            "View mode (realtime, daily, monthly, session, entries, sessions, burn-rate)"
        ),
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

    hide_model_distribution: bool = Field(
        default=False, description="Hide the model distribution bar"
    )

    header: bool = Field(
        default=True, description="Show the header banner (--no-header to hide)"
    )

    emoji: bool = Field(
        default=True, description="Show emoji (--no-emoji for plain output)"
    )

    once: bool = Field(
        default=False,
        description="Measure usage once, print a snapshot, and exit (no live loop)",
    )

    statusline: bool = Field(
        default=False,
        description="Run as a Claude Code statusline hook: read session JSON on "
        "stdin, capture official rate_limits, and print a one-line status",
    )

    filter_models: Literal["all", "anthropic"] = Field(
        default="all",
        description="Which models to count: 'all' (default) or 'anthropic' to "
        "exclude non-Claude models (e.g. routed via Claude Code Router)",
    )

    compact: bool = Field(
        default=False,
        description="Single-line compact output (works live and one-shot)",
    )

    output: Literal["rich", "json", "text", "csv"] = Field(
        default="rich",
        description="One-shot/report output format (rich, json, text, csv)",
    )

    write_state: bool = Field(
        default=False,
        description="Write the usage snapshot to a state file for external tools",
    )

    state_file: Optional[str] = Field(
        default=None,
        description="State file path for --write-state "
        "(default ~/.claude-monitor/state/latest.json)",
    )

    api: bool = Field(
        default=False,
        description="Enable the experimental Anthropic OAuth usage API",
    )

    api_cache_file: Optional[str] = Field(
        default=None,
        description=(
            "Experimental API cache file path "
            "(default ~/.claude-monitor/api/latest.json)"
        ),
    )

    api_ttl_seconds: int = Field(
        default=180,
        ge=1,
        description="Freshness TTL for the experimental API cache in seconds",
    )

    data_paths: List[str] = Field(
        default_factory=list,
        description="Claude data directories to scan; repeat or comma-separate values",
    )

    warehouse: bool = Field(
        default=False,
        description="Persist usage entries to the opt-in local warehouse",
    )

    warehouse_file: Optional[str] = Field(
        default=None,
        description="Usage warehouse file path (default ~/.claude-monitor/warehouse/usage.json)",
    )

    warehouse_retention_days: int = Field(
        default=365,
        ge=1,
        description="Days of usage records to retain in the warehouse",
    )

    date_format: Optional[str] = Field(
        default=None,
        description="Date format for daily/monthly table periods, e.g. %d.%m.%Y",
    )

    date_from: Optional[str] = Field(
        default=None,
        alias="from",
        description=(
            "Start of date range, inclusive. daily: YYYY-MM-DD, monthly: YYYY-MM"
        ),
    )

    date_to: Optional[str] = Field(
        default=None,
        alias="to",
        description=(
            "End of date range, inclusive. daily: YYYY-MM-DD, monthly: YYYY-MM"
        ),
    )

    abbreviate_tokens: bool = Field(
        default=False,
        description="Abbreviate token counts in table views",
    )

    sparklines: bool = Field(
        default=False,
        description="Show opt-in sparklines in table views",
    )

    set_terminal_title: bool = Field(
        default=False,
        description="Set the terminal title from the usage snapshot",
    )

    title_format: str = Field(
        default="{pct}% {plan}",
        description=(
            "Terminal title template using {pct}, {plan}, {used}, {limit}, "
            "{cost}, and {reset}"
        ),
    )

    @field_validator("output", mode="before")
    @classmethod
    def validate_output(cls, v: Any) -> str:
        """Validate and normalize output format value."""
        if isinstance(v, str):
            v_lower = v.lower()
            valid_outputs = ["rich", "json", "text", "csv"]
            if v_lower in valid_outputs:
                return v_lower
            raise ValueError(
                f"Invalid output: {v}. Must be one of: {', '.join(valid_outputs)}"
            )
        return v

    @field_validator("title_format", mode="before")
    @classmethod
    def validate_title_format(cls, v: Any) -> str:
        """Validate terminal title templates without inventing a DSL."""
        if not isinstance(v, str):
            return v
        try:
            parsed = list(string.Formatter().parse(v))
        except ValueError as e:
            raise ValueError(f"Invalid title-format template: {e}") from e

        for _literal, field_name, _format_spec, _conversion in parsed:
            if field_name is None:
                continue
            if field_name not in _TITLE_FORMAT_KEYS:
                raise ValueError(f"Unknown title-format key: {field_name}")

        try:
            v.format(
                pct=12.3,
                plan="pro",
                used=1200,
                limit=1900,
                cost=1.23,
                reset="17:00",
            )
        except (IndexError, KeyError, TypeError, ValueError) as e:
            raise ValueError(f"Invalid title-format template: {e}") from e
        return v

    @field_validator("data_paths", mode="before")
    @classmethod
    def validate_data_paths(cls, v: Any) -> Any:
        """Reject blank data paths while letting pydantic parse list syntax."""
        if v is None:
            return v
        if isinstance(v, str):
            parts = [part.strip() for part in v.split(",")]
        else:
            parts = []
            for item in v:
                if isinstance(item, str):
                    parts.extend(part.strip() for part in item.split(","))
                else:
                    parts.append(item)
        if any(isinstance(part, str) and not part for part in parts):
            raise ValueError("data-paths entries must not be blank")
        return parts

    @field_validator("filter_models", mode="before")
    @classmethod
    def validate_filter_models(cls, v: Any) -> str:
        """Validate and normalize the model filter value."""
        if isinstance(v, str):
            v_lower = v.lower()
            valid = ["all", "anthropic"]
            if v_lower in valid:
                return v_lower
            raise ValueError(
                f"Invalid filter-models: {v}. Must be one of: {', '.join(valid)}"
            )
        return v

    @field_validator("plan", mode="before")
    @classmethod
    def validate_plan(cls, v: Any) -> str:
        """Validate and normalize plan value."""
        if isinstance(v, str):
            v_lower = v.lower()
            valid_plans = ["pro", "max5", "max20", "team", "custom"]
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
            valid_views = [
                "realtime",
                "daily",
                "monthly",
                "session",
                "entries",
                "sessions",
                "burn-rate",
            ]
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

    @model_validator(mode="after")
    def validate_date_range(self) -> "Settings":
        """Validate ``--from``/``--to`` against the active view.

        The accepted format depends on ``view``: ``daily`` expects
        ``YYYY-MM-DD`` and ``monthly`` expects ``YYYY-MM``. Both boundaries are
        optional (one-sided ranges are allowed), but when both are present the
        start must not be after the end. The flags only apply to the ``daily``
        and ``monthly`` table views.

        Returns:
            The validated settings instance.

        Raises:
            ValueError: If a date is malformed for the active view, if the
                flags are used with an unsupported view, or if ``date_from`` is
                after ``date_to``.
        """
        if self.date_from is None and self.date_to is None:
            return self

        if self.view not in ("daily", "monthly"):
            raise ValueError("--from/--to only apply to --view daily or --view monthly")

        date_pattern = "%Y-%m-%d" if self.view == "daily" else "%Y-%m"
        expected = "YYYY-MM-DD" if self.view == "daily" else "YYYY-MM"
        parsed: Dict[str, datetime] = {}
        for label, value in (("--from", self.date_from), ("--to", self.date_to)):
            if value is None:
                continue
            try:
                dt = datetime.strptime(value, date_pattern)
            except ValueError:
                dt = None
            # strptime accepts non-canonical input like "2026-6-1"; require the
            # value to round-trip so only zero-padded YYYY-MM-DD / YYYY-MM pass.
            if dt is None or dt.strftime(date_pattern) != value:
                raise ValueError(
                    f"{label} value {value!r} is invalid for --view "
                    f"{self.view}; expected {expected}"
                )
            parsed[label] = dt

        # Compare parsed datetimes, not raw strings: "2026-6" > "2026-10" is a
        # lexical false positive that the parsed comparison avoids.
        if (
            "--from" in parsed
            and "--to" in parsed
            and parsed["--from"] > parsed["--to"]
        ):
            raise ValueError(
                f"--from ({self.date_from}) is after --to ({self.date_to})"
            )

        return self

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
            # Map aliases (e.g. --from -> date_from) back to field names so an
            # aliased flag is recognized as CLI-provided and not overwritten by
            # a saved last-used value.
            alias_to_field = {
                field.alias: name
                for name, field in cls.model_fields.items()
                if field.alias is not None
            }
            if argv:
                for _i, arg in enumerate(argv):
                    if arg.startswith("--"):
                        # Handle both "--plan pro" and "--plan=pro" forms.
                        field_name = arg[2:].split("=", 1)[0].replace("-", "_")
                        field_name = alias_to_field.get(field_name, field_name)
                        if field_name in cls.model_fields:
                            cli_provided_fields.add(field_name)

            for key, value in last_params.items():
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

        if settings.timezone in ("auto", "local"):
            settings.timezone = cls._get_system_timezone()
        if settings.time_format == "auto":
            settings.time_format = cls._get_system_time_format()

        if settings.debug:
            settings.log_level = "DEBUG"

        theme_was_auto = settings.theme == "auto"
        if theme_was_auto:
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
            # Persist the user's "auto" intent (not the resolved light/dark) so
            # background auto-detection keeps running on the next launch.
            to_persist = (
                settings.model_copy(update={"theme": "auto"})
                if theme_was_auto
                else settings
            )
            last_used.save(to_persist)

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
        args.hide_model_distribution = self.hide_model_distribution
        args.no_header = not self.header
        args.no_emoji = not self.emoji
        args.once = self.once
        args.compact = self.compact
        args.output = self.output
        args.write_state = self.write_state
        args.state_file = self.state_file
        args.api = self.api
        args.api_cache_file = self.api_cache_file
        args.api_ttl_seconds = self.api_ttl_seconds
        args.data_paths = list(self.data_paths)
        args.warehouse = self.warehouse
        args.warehouse_file = self.warehouse_file
        args.warehouse_retention_days = self.warehouse_retention_days
        args.date_format = self.date_format
        args.date_from = self.date_from
        args.date_to = self.date_to
        args.abbreviate_tokens = self.abbreviate_tokens
        args.sparklines = self.sparklines
        args.filter_models = self.filter_models
        args.set_terminal_title = self.set_terminal_title
        args.title_format = self.title_format

        return args
