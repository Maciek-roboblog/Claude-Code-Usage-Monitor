"""Comprehensive tests for core/settings.py module."""

import argparse
import json
import tempfile
from pathlib import Path
from typing import Dict, List, Union
from unittest.mock import Mock, patch

import pytest

from claude_monitor.core.settings import LastUsedParams, Settings


class TestLastUsedParams:
    """Test suite for LastUsedParams class."""

    def setup_method(self) -> None:
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.last_used = LastUsedParams(self.temp_dir)

    def teardown_method(self) -> None:
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init_default_config_dir(self) -> None:
        """Test initialization with default config directory."""
        last_used = LastUsedParams()
        expected_dir = Path.home() / ".claude-monitor"
        assert last_used.config_dir == expected_dir
        assert last_used.params_file == expected_dir / "last_used.json"

    def test_init_custom_config_dir(self) -> None:
        """Test initialization with custom config directory."""
        custom_dir = Path("/tmp/custom-config")
        last_used = LastUsedParams(custom_dir)
        assert last_used.config_dir == custom_dir
        assert last_used.params_file == custom_dir / "last_used.json"

    def test_save_success(self) -> None:
        """Test successful saving of parameters."""
        # Create mock settings with type object
        mock_settings = type(
            "MockSettings",
            (),
            {
                "plan": "pro",
                "theme": "dark",
                "timezone": "UTC",
                "time_format": "24h",
                "refresh_rate": 5,
                "reset_hour": 12,
                "custom_limit_tokens": 1000,
                "view": "realtime",
            },
        )()

        # Save parameters
        self.last_used.save(mock_settings)

        # Verify file exists and contains correct data
        assert self.last_used.params_file.exists()

        with open(self.last_used.params_file) as f:
            data = json.load(f)

        # Plan is persisted so it survives across runs (issue #162)
        assert data["plan"] == "pro"
        assert data["theme"] == "dark"
        assert data["timezone"] == "UTC"
        assert data["time_format"] == "24h"
        assert data["refresh_rate"] == 5
        assert data["reset_hour"] == 12
        assert data["custom_limit_tokens"] == 1000
        assert data["view"] == "realtime"
        assert "timestamp" in data

    def test_save_without_custom_limit(self) -> None:
        """Test saving without custom limit tokens."""
        mock_settings = type(
            "MockSettings",
            (),
            {
                "plan": "pro",
                "theme": "light",
                "timezone": "UTC",
                "time_format": "12h",
                "refresh_rate": 10,
                "reset_hour": None,
                "custom_limit_tokens": None,
                "view": "realtime",
            },
        )()

        self.last_used.save(mock_settings)

        with open(self.last_used.params_file) as f:
            data = json.load(f)

        assert "custom_limit_tokens" not in data
        assert data["theme"] == "light"

    def test_save_creates_directory(self) -> None:
        """Test that save creates directory if it doesn't exist."""
        # Use non-existent directory
        non_existent_dir = self.temp_dir / "non-existent"
        last_used = LastUsedParams(non_existent_dir)

        mock_settings = type(
            "MockSettings",
            (),
            {
                "plan": "pro",
                "theme": "dark",
                "timezone": "UTC",
                "time_format": "24h",
                "refresh_rate": 5,
                "reset_hour": 12,
                "custom_limit_tokens": None,
                "view": "realtime",
            },
        )()

        last_used.save(mock_settings)

        assert non_existent_dir.exists()
        assert last_used.params_file.exists()

    @patch("claude_monitor.core.settings.logger")
    def test_save_error_handling(self, mock_logger: Mock) -> None:
        """Test error handling during save operation."""
        # Mock file operations to raise exception
        with patch("builtins.open", side_effect=PermissionError("Access denied")):
            mock_settings = Mock()
            mock_settings.plan = "pro"
            mock_settings.theme = "dark"
            mock_settings.timezone = "UTC"
            mock_settings.time_format = "24h"
            mock_settings.refresh_rate = 5
            mock_settings.reset_hour = 12
            mock_settings.custom_limit_tokens = None
            mock_settings.view = "realtime"

            # Should not raise exception
            self.last_used.save(mock_settings)

            # Should log warning
            mock_logger.warning.assert_called_once()

    def test_load_success(self) -> None:
        """Test successful loading of parameters."""
        # Create test data
        test_data: Dict[str, Union[str, int]] = {
            "theme": "dark",
            "timezone": "Europe/Warsaw",
            "time_format": "24h",
            "refresh_rate": 5,
            "reset_hour": 8,
            "custom_limit_tokens": 2000,
            "timestamp": "2024-01-01T12:00:00",
            "view": "realtime",
        }

        with open(self.last_used.params_file, "w") as f:
            json.dump(test_data, f)

        # Load parameters
        result = self.last_used.load()

        # Verify timestamp is removed and other data is present
        assert "timestamp" not in result
        assert result["theme"] == "dark"
        assert result["timezone"] == "Europe/Warsaw"
        assert result["time_format"] == "24h"
        assert result["refresh_rate"] == 5
        assert result["reset_hour"] == 8
        assert result["custom_limit_tokens"] == 2000

    def test_load_file_not_exists(self) -> None:
        """Test loading when file doesn't exist."""
        result = self.last_used.load()
        assert result == {}

    @patch("claude_monitor.core.settings.logger")
    def test_load_error_handling(self, mock_logger: Mock) -> None:
        """Test error handling during load operation."""
        # Create invalid JSON file
        with open(self.last_used.params_file, "w") as f:
            f.write("invalid json")

        result = self.last_used.load()

        assert result == {}
        mock_logger.warning.assert_called_once()

    def test_clear_success(self) -> None:
        """Test successful clearing of parameters."""
        # Create file first
        test_data: Dict[str, str] = {"theme": "dark"}
        with open(self.last_used.params_file, "w") as f:
            json.dump(test_data, f)

        assert self.last_used.params_file.exists()

        # Clear parameters
        self.last_used.clear()

        assert not self.last_used.params_file.exists()

    def test_clear_file_not_exists(self) -> None:
        """Test clearing when file doesn't exist."""
        # Should not raise exception
        self.last_used.clear()

    @patch("claude_monitor.core.settings.logger")
    def test_clear_error_handling(self, mock_logger: Mock) -> None:
        """Test error handling during clear operation."""
        # Create file but mock unlink to raise exception
        with open(self.last_used.params_file, "w") as f:
            f.write("{}")

        with patch.object(Path, "unlink", side_effect=PermissionError("Access denied")):
            self.last_used.clear()
            mock_logger.warning.assert_called_once()

    def test_exists_true(self) -> None:
        """Test exists method when file exists."""
        with open(self.last_used.params_file, "w") as f:
            f.write("{}")

        assert self.last_used.exists() is True

    def test_exists_false(self) -> None:
        """Test exists method when file doesn't exist."""
        assert self.last_used.exists() is False


class TestSettings:
    """Test suite for Settings class."""

    def test_default_values(self) -> None:
        """Test default settings values."""
        settings = Settings(_cli_parse_args=[])

        assert settings.plan == "custom"
        assert settings.timezone == "auto"
        assert settings.time_format == "auto"
        assert settings.theme == "auto"
        assert settings.custom_limit_tokens is None
        assert settings.refresh_rate == 10
        assert settings.refresh_per_second == 0.75
        assert settings.reset_hour is None
        assert settings.log_level == "INFO"
        assert settings.log_file is None
        assert settings.debug is False
        assert settings.version is False
        assert settings.clear is False
        assert settings.api is False
        assert settings.api_cache_file is None
        assert settings.api_ttl_seconds == 180

    def test_plan_validator_valid_values(self) -> None:
        """Test plan validator with valid values."""
        valid_plans: List[str] = ["pro", "max5", "max20", "team", "custom"]

        for plan in valid_plans:
            settings = Settings(plan=plan, _cli_parse_args=[])
            assert settings.plan == plan.lower()

    def test_plan_validator_case_insensitive(self) -> None:
        """Test plan validator is case insensitive."""
        settings = Settings(plan="PRO", _cli_parse_args=[])
        assert settings.plan == "pro"

        settings = Settings(plan="Max5", _cli_parse_args=[])
        assert settings.plan == "max5"

        settings = Settings(plan="TEAM", _cli_parse_args=[])
        assert settings.plan == "team"

    def test_plan_validator_invalid_value(self) -> None:
        """Test plan validator with invalid value."""
        with pytest.raises(ValueError, match="Invalid plan: invalid"):
            Settings(plan="invalid", _cli_parse_args=[])

    def test_theme_validator_valid_values(self) -> None:
        """Test theme validator with valid values."""
        valid_themes: List[str] = ["light", "dark", "classic", "auto"]

        for theme in valid_themes:
            settings = Settings(theme=theme, _cli_parse_args=[])
            assert settings.theme == theme.lower()

    def test_theme_validator_case_insensitive(self) -> None:
        """Test theme validator is case insensitive."""
        settings = Settings(theme="LIGHT", _cli_parse_args=[])
        assert settings.theme == "light"

        settings = Settings(theme="Dark", _cli_parse_args=[])
        assert settings.theme == "dark"

    def test_theme_validator_invalid_value(self) -> None:
        """Test theme validator with invalid value."""
        with pytest.raises(ValueError, match="Invalid theme: invalid"):
            Settings(theme="invalid", _cli_parse_args=[])

    def test_timezone_validator_valid_values(self) -> None:
        """Test timezone validator with valid values."""
        # Test auto/local values
        settings = Settings(timezone="auto", _cli_parse_args=[])
        assert settings.timezone == "auto"

        settings = Settings(timezone="local", _cli_parse_args=[])
        assert settings.timezone == "local"

        # Test valid timezone
        settings = Settings(timezone="UTC", _cli_parse_args=[])
        assert settings.timezone == "UTC"

        settings = Settings(timezone="Europe/Warsaw", _cli_parse_args=[])
        assert settings.timezone == "Europe/Warsaw"

    def test_timezone_validator_invalid_value(self) -> None:
        """Test timezone validator with invalid value."""
        with pytest.raises(ValueError, match="Invalid timezone: Invalid/Timezone"):
            Settings(timezone="Invalid/Timezone", _cli_parse_args=[])

    def test_time_format_validator_valid_values(self) -> None:
        """Test time format validator with valid values."""
        valid_formats: List[str] = ["12h", "24h", "auto"]

        for fmt in valid_formats:
            settings = Settings(time_format=fmt, _cli_parse_args=[])
            assert settings.time_format == fmt

    def test_time_format_validator_invalid_value(self) -> None:
        """Test time format validator with invalid value."""
        with pytest.raises(ValueError, match="Invalid time format: invalid"):
            Settings(time_format="invalid", _cli_parse_args=[])

    def test_log_level_validator_valid_values(self) -> None:
        """Test log level validator with valid values."""
        valid_levels: List[str] = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        for level in valid_levels:
            settings = Settings(log_level=level, _cli_parse_args=[])
            assert settings.log_level == level

            # Test case insensitive
            settings = Settings(log_level=level.lower(), _cli_parse_args=[])
            assert settings.log_level == level

    def test_log_level_validator_invalid_value(self) -> None:
        """Test log level validator with invalid value."""
        with pytest.raises(ValueError, match="Invalid log level: invalid"):
            Settings(log_level="invalid", _cli_parse_args=[])

    def test_field_constraints(self) -> None:
        """Test field constraints and validation."""
        # Test positive constraints
        with pytest.raises(ValueError):
            Settings(custom_limit_tokens=0, _cli_parse_args=[])

        with pytest.raises(ValueError):
            Settings(custom_limit_tokens=-100, _cli_parse_args=[])

        # Test range constraints
        with pytest.raises(ValueError):
            Settings(refresh_rate=0, _cli_parse_args=[])

        with pytest.raises(ValueError):
            Settings(refresh_rate=61, _cli_parse_args=[])

        with pytest.raises(ValueError):
            Settings(refresh_per_second=0.05, _cli_parse_args=[])

        with pytest.raises(ValueError):
            Settings(refresh_per_second=25.0, _cli_parse_args=[])

        with pytest.raises(ValueError):
            Settings(reset_hour=-1, _cli_parse_args=[])

        with pytest.raises(ValueError):
            Settings(reset_hour=24, _cli_parse_args=[])

    @patch("claude_monitor.core.settings.Settings._get_system_timezone")
    @patch("claude_monitor.core.settings.Settings._get_system_time_format")
    def test_load_with_last_used_version_flag(
        self, mock_time_format: Mock, mock_timezone: Mock
    ) -> None:
        """Test version flag handling."""
        with patch("builtins.print") as mock_print:
            with patch("sys.exit") as mock_exit:
                Settings.load_with_last_used(["--version"])

                mock_print.assert_called_once()
                mock_exit.assert_called_once_with(0)

    @patch("claude_monitor.core.settings.Settings._get_system_timezone")
    @patch("claude_monitor.core.settings.Settings._get_system_time_format")
    def test_load_with_last_used_clear_flag(
        self, mock_time_format: Mock, mock_timezone: Mock
    ) -> None:
        """Test clear flag handling."""
        mock_timezone.return_value = "UTC"
        mock_time_format.return_value = "24h"

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create mock last used params
            config_dir = Path(temp_dir)
            params_file = config_dir / "last_used.json"
            params_file.parent.mkdir(parents=True, exist_ok=True)

            test_data: Dict[str, str] = {"theme": "dark", "timezone": "Europe/Warsaw"}
            with open(params_file, "w") as f:
                json.dump(test_data, f)

            with patch("claude_monitor.core.settings.LastUsedParams") as MockLastUsed:
                mock_instance = Mock()
                MockLastUsed.return_value = mock_instance

                Settings.load_with_last_used(["--clear"])

                # Should call clear
                mock_instance.clear.assert_called_once()

    @patch("claude_monitor.core.settings.Settings._get_system_timezone")
    @patch("claude_monitor.core.settings.Settings._get_system_time_format")
    def test_load_with_last_used_merge_params(
        self, mock_time_format: Mock, mock_timezone: Mock
    ) -> None:
        """Test merging with last used parameters."""
        mock_timezone.return_value = "UTC"
        mock_time_format.return_value = "24h"

        # Mock last used params
        test_params: Dict[str, Union[str, int]] = {
            "theme": "dark",
            "timezone": "Europe/Warsaw",
            "refresh_rate": 15,
            "custom_limit_tokens": 5000,
            "view": "realtime",
        }

        with patch("claude_monitor.core.settings.LastUsedParams") as MockLastUsed:
            mock_instance = Mock()
            mock_instance.load.return_value = test_params
            MockLastUsed.return_value = mock_instance

            # Load without CLI arguments - should use last used params
            settings = Settings.load_with_last_used([])

            assert settings.theme == "dark"
            assert settings.timezone == "Europe/Warsaw"
            assert settings.refresh_rate == 15
            assert settings.custom_limit_tokens == 5000

            # Should save current settings
            mock_instance.save.assert_called_once()

    @patch("claude_monitor.core.settings.Settings._get_system_timezone")
    @patch("claude_monitor.core.settings.Settings._get_system_time_format")
    def test_load_with_last_used_cli_priority(
        self, mock_time_format: Mock, mock_timezone: Mock
    ) -> None:
        """Test CLI arguments take priority over last used params."""
        mock_timezone.return_value = "UTC"
        mock_time_format.return_value = "24h"

        # Mock last used params
        test_params: Dict[str, Union[str, int]] = {
            "theme": "dark",
            "timezone": "Europe/Warsaw",
            "refresh_rate": 15,
            "view": "realtime",
        }

        with patch("claude_monitor.core.settings.LastUsedParams") as MockLastUsed:
            mock_instance = Mock()
            mock_instance.load.return_value = test_params
            MockLastUsed.return_value = mock_instance

            # Load with CLI arguments - CLI should override
            settings = Settings.load_with_last_used(
                ["--theme", "light", "--refresh-rate", "5"]
            )

            assert settings.theme == "light"  # CLI override
            assert settings.refresh_rate == 5  # CLI override
            assert settings.timezone == "Europe/Warsaw"  # From last used

    @patch("claude_monitor.core.settings.Settings._get_system_timezone")
    @patch("claude_monitor.core.settings.Settings._get_system_time_format")
    def test_load_with_last_used_auto_timezone(
        self, mock_time_format: Mock, mock_timezone: Mock
    ) -> None:
        """Test auto timezone detection."""
        mock_timezone.return_value = "America/New_York"
        mock_time_format.return_value = "12h"

        with patch("claude_monitor.core.settings.LastUsedParams") as MockLastUsed:
            mock_instance = Mock()
            mock_instance.load.return_value = {}
            MockLastUsed.return_value = mock_instance

            settings = Settings.load_with_last_used([])

            assert settings.timezone == "America/New_York"
            assert settings.time_format == "12h"

    @patch("claude_monitor.core.settings.Settings._get_system_timezone")
    @patch("claude_monitor.core.settings.Settings._get_system_time_format")
    def test_load_with_last_used_local_timezone_alias(
        self, mock_time_format: Mock, mock_timezone: Mock
    ) -> None:
        """`--timezone local` resolves before display code validates the timezone."""
        mock_timezone.return_value = "Australia/Brisbane"
        mock_time_format.return_value = "24h"

        with patch("claude_monitor.core.settings.LastUsedParams") as MockLastUsed:
            mock_instance = Mock()
            mock_instance.load.return_value = {}
            MockLastUsed.return_value = mock_instance

            settings = Settings.load_with_last_used(["--timezone", "local"])

            assert settings.timezone == "Australia/Brisbane"

    @patch("claude_monitor.core.settings.Settings._get_system_timezone")
    @patch("claude_monitor.core.settings.Settings._get_system_time_format")
    def test_load_with_last_used_debug_flag(
        self, mock_time_format: Mock, mock_timezone: Mock
    ) -> None:
        """Test debug flag overrides log level."""
        mock_timezone.return_value = "UTC"
        mock_time_format.return_value = "24h"

        with patch("claude_monitor.core.settings.LastUsedParams") as MockLastUsed:
            mock_instance = Mock()
            mock_instance.load.return_value = {}
            MockLastUsed.return_value = mock_instance

            settings = Settings.load_with_last_used(["--debug"])

            assert settings.debug is True
            assert settings.log_level == "DEBUG"

    @patch("claude_monitor.core.settings.Settings._get_system_timezone")
    @patch("claude_monitor.core.settings.Settings._get_system_time_format")
    @patch("claude_monitor.terminal.themes.BackgroundDetector")
    def test_load_with_last_used_theme_detection(
        self, MockDetector: Mock, mock_time_format: Mock, mock_timezone: Mock
    ) -> None:
        """Test theme auto-detection."""
        mock_timezone.return_value = "UTC"
        mock_time_format.return_value = "24h"

        # Mock background detector
        mock_detector_instance = Mock()
        MockDetector.return_value = mock_detector_instance

        from claude_monitor.terminal.themes import BackgroundType

        mock_detector_instance.detect_background.return_value = BackgroundType.DARK

        with patch("claude_monitor.core.settings.LastUsedParams") as MockLastUsed:
            mock_instance = Mock()
            mock_instance.load.return_value = {}
            MockLastUsed.return_value = mock_instance

            settings = Settings.load_with_last_used([])

            assert settings.theme == "dark"

    @patch("claude_monitor.core.settings.Settings._get_system_timezone")
    @patch("claude_monitor.core.settings.Settings._get_system_time_format")
    def test_load_with_last_used_custom_plan_reset(
        self, mock_time_format: Mock, mock_timezone: Mock
    ) -> None:
        """Test custom plan resets custom_limit_tokens if not provided via CLI."""
        mock_timezone.return_value = "UTC"
        mock_time_format.return_value = "24h"

        test_params: Dict[str, int] = {"custom_limit_tokens": 5000}

        with patch("claude_monitor.core.settings.LastUsedParams") as MockLastUsed:
            mock_instance = Mock()
            mock_instance.load.return_value = test_params
            MockLastUsed.return_value = mock_instance

            # Switch to custom plan via CLI without specifying custom limit
            settings = Settings.load_with_last_used(["--plan", "custom"])

            assert settings.plan == "custom"
            assert settings.custom_limit_tokens is None  # Should be reset

    @patch("claude_monitor.core.settings.Settings._get_system_timezone")
    @patch("claude_monitor.core.settings.Settings._get_system_time_format")
    def test_load_with_last_used_restores_saved_plan(
        self, mock_time_format: Mock, mock_timezone: Mock
    ) -> None:
        """A saved plan is restored when --plan is not given (issue #162)."""
        mock_timezone.return_value = "UTC"
        mock_time_format.return_value = "24h"

        with patch("claude_monitor.core.settings.LastUsedParams") as MockLastUsed:
            mock_instance = Mock()
            mock_instance.load.return_value = {"plan": "max5"}
            MockLastUsed.return_value = mock_instance

            settings = Settings.load_with_last_used([])

            assert settings.plan == "max5"

    @patch("claude_monitor.core.settings.Settings._get_system_timezone")
    @patch("claude_monitor.core.settings.Settings._get_system_time_format")
    def test_load_with_last_used_cli_plan_overrides_saved(
        self, mock_time_format: Mock, mock_timezone: Mock
    ) -> None:
        """An explicit --plan overrides the saved plan (issue #162)."""
        mock_timezone.return_value = "UTC"
        mock_time_format.return_value = "24h"

        with patch("claude_monitor.core.settings.LastUsedParams") as MockLastUsed:
            mock_instance = Mock()
            mock_instance.load.return_value = {"plan": "max5"}
            MockLastUsed.return_value = mock_instance

            settings = Settings.load_with_last_used(["--plan", "pro"])

            assert settings.plan == "pro"

    @patch("claude_monitor.core.settings.Settings._get_system_timezone")
    @patch("claude_monitor.core.settings.Settings._get_system_time_format")
    @patch("claude_monitor.terminal.themes.BackgroundDetector")
    def test_load_with_last_used_saved_theme_survives_autodetect(
        self, MockDetector: Mock, mock_time_format: Mock, mock_timezone: Mock
    ) -> None:
        """A saved explicit theme is not overwritten by auto-detect (issues #102, #200)."""
        mock_timezone.return_value = "UTC"
        mock_time_format.return_value = "24h"

        from claude_monitor.terminal.themes import BackgroundType

        mock_detector_instance = Mock()
        mock_detector_instance.detect_background.return_value = BackgroundType.LIGHT
        MockDetector.return_value = mock_detector_instance

        with patch("claude_monitor.core.settings.LastUsedParams") as MockLastUsed:
            mock_instance = Mock()
            mock_instance.load.return_value = {"theme": "dark"}
            MockLastUsed.return_value = mock_instance

            settings = Settings.load_with_last_used([])

            assert settings.theme == "dark"
            mock_detector_instance.detect_background.assert_not_called()

    def test_to_namespace(self) -> None:
        """Test conversion to argparse.Namespace."""
        settings = Settings(
            plan="pro",
            timezone="UTC",
            theme="dark",
            refresh_rate=5,
            refresh_per_second=1.0,
            reset_hour=8,
            custom_limit_tokens=1000,
            time_format="24h",
            log_level="DEBUG",
            log_file=Path("/tmp/test.log"),
            version=True,
            _cli_parse_args=[],
        )

        namespace = settings.to_namespace()

        assert isinstance(namespace, argparse.Namespace)
        assert namespace.plan == "pro"
        assert namespace.timezone == "UTC"
        assert namespace.theme == "dark"
        assert namespace.refresh_rate == 5
        assert namespace.refresh_per_second == 1.0
        assert namespace.reset_hour == 8
        assert namespace.custom_limit_tokens == 1000
        assert namespace.time_format == "24h"
        assert namespace.log_level == "DEBUG"
        assert namespace.log_file == "/tmp/test.log"
        assert namespace.version is True

    def test_to_namespace_none_values(self) -> None:
        """Test conversion to namespace with None values."""
        settings = Settings(_cli_parse_args=[])
        namespace = settings.to_namespace()

        assert namespace.log_file is None
        assert namespace.reset_hour is None
        assert namespace.custom_limit_tokens is None

    def test_hide_model_distribution_persisted_to_namespace(self) -> None:
        """--hide-model-distribution defaults off and is carried into the namespace (#161)."""
        assert Settings(_cli_parse_args=[]).hide_model_distribution is False

        namespace = Settings(
            hide_model_distribution=True, _cli_parse_args=[]
        ).to_namespace()
        assert namespace.hide_model_distribution is True

    def test_header_and_emoji_flags_map_to_namespace(self) -> None:
        """header/emoji default on; --no-header/--no-emoji flip them off (#57)."""
        default = Settings(_cli_parse_args=[])
        assert default.header is True
        assert default.emoji is True
        assert default.to_namespace().no_header is False
        assert default.to_namespace().no_emoji is False

        namespace = Settings(
            header=False, emoji=False, _cli_parse_args=[]
        ).to_namespace()
        assert namespace.no_header is True
        assert namespace.no_emoji is True

    @patch("claude_monitor.core.settings.Settings._get_system_timezone")
    @patch("claude_monitor.core.settings.Settings._get_system_time_format")
    def test_cli_plan_equals_form_overrides_saved(
        self, mock_time_format: Mock, mock_timezone: Mock
    ) -> None:
        """--plan=pro (equals form) must beat a saved plan, like --plan pro (codex P1)."""
        mock_timezone.return_value = "UTC"
        mock_time_format.return_value = "24h"

        with patch("claude_monitor.core.settings.LastUsedParams") as MockLastUsed:
            mock_instance = Mock()
            mock_instance.load.return_value = {"plan": "max5"}
            MockLastUsed.return_value = mock_instance

            settings = Settings.load_with_last_used(["--plan=pro"])

            assert settings.plan == "pro"

    @patch("claude_monitor.core.settings.Settings._get_system_timezone")
    @patch("claude_monitor.core.settings.Settings._get_system_time_format")
    @patch("claude_monitor.terminal.themes.BackgroundDetector")
    def test_auto_theme_persisted_as_auto_not_resolved(
        self, MockDetector: Mock, mock_time_format: Mock, mock_timezone: Mock
    ) -> None:
        """Auto theme resolves for display but persists 'auto' so it keeps re-detecting (codex P2)."""
        mock_timezone.return_value = "UTC"
        mock_time_format.return_value = "24h"

        from claude_monitor.terminal.themes import BackgroundType

        detector = Mock()
        detector.detect_background.return_value = BackgroundType.DARK
        MockDetector.return_value = detector

        with patch("claude_monitor.core.settings.LastUsedParams") as MockLastUsed:
            mock_instance = Mock()
            mock_instance.load.return_value = {}
            MockLastUsed.return_value = mock_instance

            settings = Settings.load_with_last_used([])

            assert settings.theme == "dark"  # resolved for this run's display
            persisted = mock_instance.save.call_args[0][0]
            assert persisted.theme == "auto"  # re-detects next launch

    def test_once_and_output_defaults_and_namespace(self) -> None:
        """--once defaults off; --output defaults rich; both reach the namespace (#126)."""
        default = Settings(_cli_parse_args=[])
        assert default.once is False
        assert default.output == "rich"

        namespace = Settings(
            once=True, output="json", _cli_parse_args=[]
        ).to_namespace()
        assert namespace.once is True
        assert namespace.output == "json"

    def test_output_validator_rejects_unknown(self) -> None:
        """--output xml is rejected with a clear message (#126)."""
        with pytest.raises(ValueError, match="Invalid output"):
            Settings(output="xml", _cli_parse_args=[])

    def test_output_lowercases_value(self) -> None:
        assert Settings(output="JSON", _cli_parse_args=[]).output == "json"

    def test_report_views_and_csv_output_reach_namespace(self) -> None:
        """Warehouse reports add entries/sessions/burn-rate views and CSV output."""
        for view in ("entries", "sessions", "burn-rate"):
            settings = Settings(
                view=view,
                output="CSV",
                warehouse_file="/tmp/usage.json",
                _cli_parse_args=[],
            )
            namespace = settings.to_namespace()
            assert settings.view == view
            assert namespace.view == view
            assert settings.output == "csv"
            assert namespace.output == "csv"

    def test_write_state_defaults_and_namespace(self) -> None:
        """--write-state defaults off, --state-file default None; both reach the namespace (#184)."""
        default = Settings(_cli_parse_args=[])
        assert default.write_state is False
        assert default.state_file is None

        namespace = Settings(
            write_state=True, state_file="/tmp/s.json", _cli_parse_args=[]
        ).to_namespace()
        assert namespace.write_state is True
        assert namespace.state_file == "/tmp/s.json"

    def test_warehouse_defaults_cli_and_namespace(self) -> None:
        """The persistent warehouse is opt-in and carries its file/retention knobs."""
        default = Settings(_cli_parse_args=[])
        assert default.warehouse is False
        assert default.warehouse_file is None
        assert default.warehouse_retention_days == 365

        namespace = Settings(
            warehouse=True,
            warehouse_file="/tmp/usage.json",
            warehouse_retention_days=30,
            _cli_parse_args=[],
        ).to_namespace()
        assert namespace.warehouse is True
        assert namespace.warehouse_file == "/tmp/usage.json"
        assert namespace.warehouse_retention_days == 30

        parsed = Settings(
            _cli_parse_args=[
                "--warehouse",
                "--warehouse-file",
                "/tmp/cli-usage.json",
                "--warehouse-retention-days",
                "45",
            ]
        )
        assert parsed.warehouse is True
        assert parsed.warehouse_file == "/tmp/cli-usage.json"
        assert parsed.warehouse_retention_days == 45

    def test_api_usage_defaults_cli_and_namespace(self) -> None:
        """The experimental OAuth usage API is opt-in and exposes cache knobs."""
        default = Settings(_cli_parse_args=[])
        assert default.api is False
        assert default.api_cache_file is None
        assert default.api_ttl_seconds == 180

        namespace = Settings(
            api=True,
            api_cache_file="/tmp/api-cache.json",
            api_ttl_seconds=45,
            _cli_parse_args=[],
        ).to_namespace()
        assert namespace.api is True
        assert namespace.api_cache_file == "/tmp/api-cache.json"
        assert namespace.api_ttl_seconds == 45

        parsed = Settings(
            _cli_parse_args=[
                "--api",
                "--api-cache-file",
                "/tmp/cli-api-cache.json",
                "--api-ttl-seconds",
                "60",
            ]
        )
        assert parsed.api is True
        assert parsed.api_cache_file == "/tmp/cli-api-cache.json"
        assert parsed.api_ttl_seconds == 60

    def test_table_formatter_flags_default_cli_and_namespace(self) -> None:
        """PR #175's formatting knobs remain explicit and sparklines are opt-in."""
        default = Settings(_cli_parse_args=[])
        assert default.date_format is None
        assert default.abbreviate_tokens is False
        assert default.sparklines is False

        namespace = Settings(
            date_format="%d.%m.%Y",
            abbreviate_tokens=True,
            sparklines=True,
            _cli_parse_args=[],
        ).to_namespace()
        assert namespace.date_format == "%d.%m.%Y"
        assert namespace.abbreviate_tokens is True
        assert namespace.sparklines is True

        parsed = Settings(
            _cli_parse_args=[
                "--date-format",
                "%d.%m.%Y",
                "--abbreviate-tokens",
                "--sparklines",
            ]
        )
        assert parsed.date_format == "%d.%m.%Y"
        assert parsed.abbreviate_tokens is True
        assert parsed.sparklines is True

    def test_compact_default_and_namespace(self) -> None:
        """--compact defaults off and reaches the namespace (#65)."""
        assert Settings(_cli_parse_args=[]).compact is False
        assert Settings(compact=True, _cli_parse_args=[]).to_namespace().compact is True

    def test_filter_models_default_and_namespace(self) -> None:
        """--filter-models defaults to 'all' and reaches the namespace (#113)."""
        assert Settings(_cli_parse_args=[]).filter_models == "all"
        ns = Settings(filter_models="ANTHROPIC", _cli_parse_args=[]).to_namespace()
        assert ns.filter_models == "anthropic"  # validated + lowercased

    def test_filter_models_rejects_invalid(self) -> None:
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Settings(filter_models="openai", _cli_parse_args=[])

    def test_data_paths_default_cli_and_namespace(self) -> None:
        """--data-paths is a pydantic-settings list field, not a manual parser."""
        default = Settings(_cli_parse_args=[])
        assert default.data_paths == []
        assert default.to_namespace().data_paths == []

        parsed = Settings(
            _cli_parse_args=["--data-paths", "/a", "--data-paths", "/b,/c"]
        )
        assert parsed.data_paths == ["/a", "/b", "/c"]
        assert parsed.to_namespace().data_paths == ["/a", "/b", "/c"]

    def test_data_paths_rejects_blank_values(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Settings(data_paths=["/a", "  "], _cli_parse_args=[])


class TestDateRangeFlags:
    """Tests for the ``--from``/``--to`` date-range flags."""

    def test_daily_accepts_iso_date(self) -> None:
        """Daily view accepts ``YYYY-MM-DD`` boundaries."""
        settings = Settings(
            view="daily",
            date_from="2026-06-01",
            date_to="2026-06-05",
            _cli_parse_args=[],
        )
        assert settings.date_from == "2026-06-01"
        assert settings.date_to == "2026-06-05"

    def test_daily_rejects_month_format(self) -> None:
        """Daily view rejects the ``YYYY-MM`` month format."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Settings(view="daily", date_from="2026-06", _cli_parse_args=[])

    def test_daily_rejects_invalid_calendar_date(self) -> None:
        """Daily view rejects impossible dates such as month 13."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Settings(view="daily", date_from="2026-13-01", _cli_parse_args=[])

    def test_daily_rejects_non_canonical_date(self) -> None:
        """Daily view rejects non-zero-padded input that strptime would accept."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Settings(view="daily", date_from="2026-6-1", _cli_parse_args=[])

    def test_monthly_rejects_non_canonical_month(self) -> None:
        """Monthly view rejects non-zero-padded months like ``2026-6``."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Settings(view="monthly", date_from="2026-6", _cli_parse_args=[])

    def test_monthly_from_after_to_uses_parsed_order(self) -> None:
        """``2026-10`` > ``2026-6`` must be caught via parsed comparison.

        A raw string comparison would order ``"2026-10" < "2026-6"`` and miss
        this inverted range; comparing parsed datetimes rejects it correctly.
        """
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Settings(
                view="monthly",
                date_from="2026-10",
                date_to="2026-06",
                _cli_parse_args=[],
            )

    def test_monthly_accepts_month_format(self) -> None:
        """Monthly view accepts ``YYYY-MM`` boundaries."""
        settings = Settings(
            view="monthly",
            date_from="2026-06",
            date_to="2026-07",
            _cli_parse_args=[],
        )
        assert settings.date_from == "2026-06"
        assert settings.date_to == "2026-07"

    def test_monthly_rejects_day_format(self) -> None:
        """Monthly view rejects the ``YYYY-MM-DD`` day format."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Settings(view="monthly", date_from="2026-06-01", _cli_parse_args=[])

    def test_range_rejected_for_non_table_view(self) -> None:
        """The flags only apply to the daily and monthly views."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Settings(view="realtime", date_from="2026-06-01", _cli_parse_args=[])

    def test_from_after_to_rejected(self) -> None:
        """``--from`` must not be later than ``--to``."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Settings(
                view="daily",
                date_from="2026-06-05",
                date_to="2026-06-01",
                _cli_parse_args=[],
            )

    def test_one_sided_ranges_allowed(self) -> None:
        """Either boundary may be omitted."""
        only_from = Settings(view="daily", date_from="2026-06-05", _cli_parse_args=[])
        assert only_from.date_from == "2026-06-05"
        assert only_from.date_to is None

        only_to = Settings(view="monthly", date_to="2026-06", _cli_parse_args=[])
        assert only_to.date_from is None
        assert only_to.date_to == "2026-06"

    def test_no_range_is_default(self) -> None:
        """Without the flags both boundaries default to ``None``."""
        settings = Settings(view="realtime", _cli_parse_args=[])
        assert settings.date_from is None
        assert settings.date_to is None

    def test_cli_from_to_aliases_parse(self) -> None:
        """The ``--from``/``--to`` CLI tokens map onto the fields."""
        settings = Settings(
            _cli_parse_args=[
                "--view",
                "daily",
                "--from",
                "2026-06-01",
                "--to",
                "2026-06-05",
            ]
        )
        assert settings.date_from == "2026-06-01"
        assert settings.date_to == "2026-06-05"

    def test_to_namespace_carries_date_range(self) -> None:
        """The range values are plumbed into the argparse namespace."""
        settings = Settings(
            view="daily",
            date_from="2026-06-01",
            date_to="2026-06-05",
            _cli_parse_args=[],
        )
        namespace = settings.to_namespace()
        assert namespace.date_from == "2026-06-01"
        assert namespace.date_to == "2026-06-05"


class TestSettingsIntegration:
    """Integration tests for Settings class."""

    def test_complete_workflow(self) -> None:
        """Test complete workflow with real file operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)

            # Mock the config directory
            with patch("claude_monitor.core.settings.LastUsedParams") as MockLastUsed:
                # Create real LastUsedParams instance with temp directory
                real_last_used = LastUsedParams(config_dir)
                MockLastUsed.return_value = real_last_used

                with (
                    patch(
                        "claude_monitor.core.settings.Settings._get_system_timezone",
                        return_value="UTC",
                    ),
                    patch(
                        "claude_monitor.core.settings.Settings._get_system_time_format",
                        return_value="24h",
                    ),
                ):
                    # First run - should create file
                    settings1 = Settings.load_with_last_used(
                        ["--theme", "dark", "--refresh-rate", "5"]
                    )

                    assert settings1.theme == "dark"
                    assert settings1.refresh_rate == 5

                    # Second run - should load from file
                    settings2 = Settings.load_with_last_used(["--plan", "pro"])

                    assert settings2.theme == "dark"  # From last used
                    assert settings2.refresh_rate == 5  # From last used
                    assert settings2.plan == "pro"  # From CLI

    def test_settings_customise_sources(self) -> None:
        """Test settings source customization."""
        sources = Settings.settings_customise_sources(
            Settings,
            "init_settings",
            "env_settings",
            "dotenv_settings",
            "file_secret_settings",
        )

        # Should only return init_settings
        assert sources == ("init_settings",)
