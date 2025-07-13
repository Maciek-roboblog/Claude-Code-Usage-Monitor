"""Comprehensive tests for core/settings.py module."""

import argparse
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from claude_monitor.core.settings import LastUsedParams, Settings


class TestLastUsedParams:
    """Test suite for LastUsedParams class."""

    def setup_method(self):
        """
        Set up a temporary directory and initialize a LastUsedParams instance for testing.
        """
        self.temp_dir = Path(tempfile.mkdtemp())
        self.last_used = LastUsedParams(self.temp_dir)

    def teardown_method(self):
        """
        Remove the temporary directory used for testing, cleaning up any files or subdirectories created during the test.
        """
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init_default_config_dir(self):
        """
        Tests that LastUsedParams initializes with the default configuration directory and correct parameters file path.
        """
        last_used = LastUsedParams()
        expected_dir = Path.home() / ".claude-monitor"
        assert last_used.config_dir == expected_dir
        assert last_used.params_file == expected_dir / "last_used.json"

    def test_init_custom_config_dir(self):
        """
        Test that LastUsedParams initializes correctly with a custom configuration directory.
        
        Verifies that the config directory and params file path are set to the provided custom directory.
        """
        custom_dir = Path("/tmp/custom-config")
        last_used = LastUsedParams(custom_dir)
        assert last_used.config_dir == custom_dir
        assert last_used.params_file == custom_dir / "last_used.json"

    def test_save_success(self):
        """
        Verifies that parameters are saved to a file correctly, excluding the "plan" field, and that all expected fields and a timestamp are present in the saved data.
        """
        # Create mock settings
        mock_settings = Mock()
        mock_settings.plan = "pro"
        mock_settings.theme = "dark"
        mock_settings.timezone = "UTC"
        mock_settings.time_format = "24h"
        mock_settings.refresh_rate = 5
        mock_settings.reset_hour = 12
        mock_settings.custom_limit_tokens = 1000

        # Save parameters
        self.last_used.save(mock_settings)

        # Verify file exists and contains correct data
        assert self.last_used.params_file.exists()

        with open(self.last_used.params_file) as f:
            data = json.load(f)

        # Verify plan is not saved (by design)
        assert "plan" not in data
        assert data["theme"] == "dark"
        assert data["timezone"] == "UTC"
        assert data["time_format"] == "24h"
        assert data["refresh_rate"] == 5
        assert data["reset_hour"] == 12
        assert data["custom_limit_tokens"] == 1000
        assert "timestamp" in data

    def test_save_without_custom_limit(self):
        """
        Test that saving settings omits the 'custom_limit_tokens' field when it is None.
        """
        mock_settings = Mock()
        mock_settings.plan = "pro"
        mock_settings.theme = "light"
        mock_settings.timezone = "UTC"
        mock_settings.time_format = "12h"
        mock_settings.refresh_rate = 10
        mock_settings.reset_hour = None
        mock_settings.custom_limit_tokens = None

        self.last_used.save(mock_settings)

        with open(self.last_used.params_file) as f:
            data = json.load(f)

        assert "custom_limit_tokens" not in data
        assert data["theme"] == "light"

    def test_save_creates_directory(self):
        """
        Test that the save method creates the configuration directory if it does not exist before saving parameters.
        """
        # Use non-existent directory
        non_existent_dir = self.temp_dir / "non-existent"
        last_used = LastUsedParams(non_existent_dir)

        mock_settings = Mock()
        mock_settings.plan = "pro"
        mock_settings.theme = "dark"
        mock_settings.timezone = "UTC"
        mock_settings.time_format = "24h"
        mock_settings.refresh_rate = 5
        mock_settings.reset_hour = 12
        mock_settings.custom_limit_tokens = None

        last_used.save(mock_settings)

        assert non_existent_dir.exists()
        assert last_used.params_file.exists()

    @patch("claude_monitor.core.settings.logger")
    def test_save_error_handling(self, mock_logger):
        """
        Test that the save method handles file write errors gracefully by logging a warning instead of raising an exception.
        """
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

            # Should not raise exception
            self.last_used.save(mock_settings)

            # Should log warning
            mock_logger.warning.assert_called_once()

    def test_load_success(self):
        """
        Test that parameters are loaded correctly from a JSON file, with the timestamp field excluded from the result.
        """
        # Create test data
        test_data = {
            "theme": "dark",
            "timezone": "Europe/Warsaw",
            "time_format": "24h",
            "refresh_rate": 5,
            "reset_hour": 8,
            "custom_limit_tokens": 2000,
            "timestamp": "2024-01-01T12:00:00",
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

    def test_load_file_not_exists(self):
        """
        Test that loading parameters returns an empty dictionary when the params file does not exist.
        """
        result = self.last_used.load()
        assert result == {}

    @patch("claude_monitor.core.settings.logger")
    def test_load_error_handling(self, mock_logger):
        """
        Test that loading from an invalid JSON file returns an empty dictionary and logs a warning.
        """
        # Create invalid JSON file
        with open(self.last_used.params_file, "w") as f:
            f.write("invalid json")

        result = self.last_used.load()

        assert result == {}
        mock_logger.warning.assert_called_once()

    def test_clear_success(self):
        """
        Test that the clear method successfully deletes the parameters file if it exists.
        """
        # Create file first
        test_data = {"theme": "dark"}
        with open(self.last_used.params_file, "w") as f:
            json.dump(test_data, f)

        assert self.last_used.params_file.exists()

        # Clear parameters
        self.last_used.clear()

        assert not self.last_used.params_file.exists()

    def test_clear_file_not_exists(self):
        """
        Test that clearing parameters does not raise an exception when the params file does not exist.
        """
        # Should not raise exception
        self.last_used.clear()

    @patch("claude_monitor.core.settings.logger")
    def test_clear_error_handling(self, mock_logger):
        """
        Test that the clear method handles exceptions gracefully when file deletion fails, ensuring a warning is logged and no exception is raised.
        """
        # Create file but mock unlink to raise exception
        with open(self.last_used.params_file, "w") as f:
            f.write("{}")

        with patch.object(Path, "unlink", side_effect=PermissionError("Access denied")):
            self.last_used.clear()
            mock_logger.warning.assert_called_once()

    def test_exists_true(self):
        """
        Test that the `exists` method returns True when the parameters file exists.
        """
        with open(self.last_used.params_file, "w") as f:
            f.write("{}")

        assert self.last_used.exists() is True

    def test_exists_false(self):
        """
        Test that the `exists` method returns False when the parameters file does not exist.
        """
        assert self.last_used.exists() is False


class TestSettings:
    """Test suite for Settings class."""

    def test_default_values(self):
        """
        Verifies that a Settings instance initialized with no CLI arguments has all fields set to their expected default values.
        """
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

    def test_plan_validator_valid_values(self):
        """
        Test that the plan validator accepts valid plan values and normalizes them to lowercase.
        """
        valid_plans = ["pro", "max5", "max20", "custom"]

        for plan in valid_plans:
            settings = Settings(plan=plan, _cli_parse_args=[])
            assert settings.plan == plan.lower()

    def test_plan_validator_case_insensitive(self):
        """
        Test that the plan validator accepts plan values in any case and normalizes them to lowercase.
        """
        settings = Settings(plan="PRO", _cli_parse_args=[])
        assert settings.plan == "pro"

        settings = Settings(plan="Max5", _cli_parse_args=[])
        assert settings.plan == "max5"

    def test_plan_validator_invalid_value(self):
        """
        Test that the plan validator raises a ValueError when an invalid plan value is provided.
        """
        with pytest.raises(ValueError, match="Invalid plan: invalid"):
            Settings(plan="invalid", _cli_parse_args=[])

    def test_theme_validator_valid_values(self):
        """
        Verifies that the theme validator accepts valid theme values and normalizes them to lowercase.
        """
        valid_themes = ["light", "dark", "classic", "auto"]

        for theme in valid_themes:
            settings = Settings(theme=theme, _cli_parse_args=[])
            assert settings.theme == theme.lower()

    def test_theme_validator_case_insensitive(self):
        """
        Test that the theme validator accepts theme values in a case-insensitive manner and normalizes them to lowercase.
        """
        settings = Settings(theme="LIGHT", _cli_parse_args=[])
        assert settings.theme == "light"

        settings = Settings(theme="Dark", _cli_parse_args=[])
        assert settings.theme == "dark"

    def test_theme_validator_invalid_value(self):
        """
        Test that the theme validator raises a ValueError when an invalid theme value is provided.
        """
        with pytest.raises(ValueError, match="Invalid theme: invalid"):
            Settings(theme="invalid", _cli_parse_args=[])

    def test_timezone_validator_valid_values(self):
        """
        Verify that the Settings class accepts valid timezone values, including "auto", "local", and specific timezone names.
        """
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

    def test_timezone_validator_invalid_value(self):
        """
        Test that providing an invalid timezone value to Settings raises a ValueError.
        """
        with pytest.raises(ValueError, match="Invalid timezone: Invalid/Timezone"):
            Settings(timezone="Invalid/Timezone", _cli_parse_args=[])

    def test_time_format_validator_valid_values(self):
        """
        Verify that the time format validator accepts valid values ("12h", "24h", "auto") when initializing the Settings class.
        """
        valid_formats = ["12h", "24h", "auto"]

        for fmt in valid_formats:
            settings = Settings(time_format=fmt, _cli_parse_args=[])
            assert settings.time_format == fmt

    def test_time_format_validator_invalid_value(self):
        """
        Test that providing an invalid value to the time format validator raises a ValueError.
        """
        with pytest.raises(ValueError, match="Invalid time format: invalid"):
            Settings(time_format="invalid", _cli_parse_args=[])

    def test_log_level_validator_valid_values(self):
        """
        Verify that the log level validator in the Settings class accepts all valid log level values, including case-insensitive input.
        """
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        for level in valid_levels:
            settings = Settings(log_level=level, _cli_parse_args=[])
            assert settings.log_level == level

            # Test case insensitive
            settings = Settings(log_level=level.lower(), _cli_parse_args=[])
            assert settings.log_level == level

    def test_log_level_validator_invalid_value(self):
        """
        Test that providing an invalid log level to Settings raises a ValueError.
        """
        with pytest.raises(ValueError, match="Invalid log level: invalid"):
            Settings(log_level="invalid", _cli_parse_args=[])

    def test_field_constraints(self):
        """
        Verifies that the Settings class enforces field constraints and raises ValueError for invalid values.
        
        Tests that invalid values for custom_limit_tokens, refresh_rate, refresh_per_second, and reset_hour are correctly rejected.
        """
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
    def test_load_with_last_used_version_flag(self, mock_time_format, mock_timezone):
        """
        Test that passing the --version flag prints version information and exits the program.
        """
        with patch("builtins.print") as mock_print:
            with patch("sys.exit") as mock_exit:
                Settings.load_with_last_used(["--version"])

                mock_print.assert_called_once()
                mock_exit.assert_called_once_with(0)

    @patch("claude_monitor.core.settings.Settings._get_system_timezone")
    @patch("claude_monitor.core.settings.Settings._get_system_time_format")
    def test_load_with_last_used_clear_flag(self, mock_time_format, mock_timezone):
        """
        Tests that passing the '--clear' flag to Settings.load_with_last_used calls the clear method on the LastUsedParams instance.
        """
        mock_timezone.return_value = "UTC"
        mock_time_format.return_value = "24h"

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create mock last used params
            config_dir = Path(temp_dir)
            params_file = config_dir / "last_used.json"
            params_file.parent.mkdir(parents=True, exist_ok=True)

            test_data = {"theme": "dark", "timezone": "Europe/Warsaw"}
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
    def test_load_with_last_used_merge_params(self, mock_time_format, mock_timezone):
        """
        Test that loading settings with no CLI arguments merges values from last used parameters and saves the updated settings.
        """
        mock_timezone.return_value = "UTC"
        mock_time_format.return_value = "24h"

        # Mock last used params
        test_params = {
            "theme": "dark",
            "timezone": "Europe/Warsaw",
            "refresh_rate": 15,
            "custom_limit_tokens": 5000,
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
    def test_load_with_last_used_cli_priority(self, mock_time_format, mock_timezone):
        """
        Test that command-line arguments override last used parameters when loading settings.
        
        Ensures that values provided via CLI take precedence over those loaded from the last used parameters, while unspecified fields fall back to the last used values.
        """
        mock_timezone.return_value = "UTC"
        mock_time_format.return_value = "24h"

        # Mock last used params
        test_params = {"theme": "dark", "timezone": "Europe/Warsaw", "refresh_rate": 15}

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
    def test_load_with_last_used_auto_timezone(self, mock_time_format, mock_timezone):
        """
        Test that the settings loader detects and sets the system timezone and time format when no timezone is specified in the CLI arguments or last used parameters.
        """
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
    def test_load_with_last_used_debug_flag(self, mock_time_format, mock_timezone):
        """
        Test that enabling the debug flag sets debug mode to True and overrides the log level to "DEBUG".
        """
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
        self, MockDetector, mock_time_format, mock_timezone
    ):
        """
        Tests that when the theme is set to "auto", the theme is automatically detected using the background detector and set to "dark".
        """
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
        self, mock_time_format, mock_timezone
    ):
        """
        Test that switching to the "custom" plan via CLI resets `custom_limit_tokens` to None if not specified in the CLI arguments, even when a previous value exists in last used parameters.
        """
        mock_timezone.return_value = "UTC"
        mock_time_format.return_value = "24h"

        test_params = {"custom_limit_tokens": 5000}

        with patch("claude_monitor.core.settings.LastUsedParams") as MockLastUsed:
            mock_instance = Mock()
            mock_instance.load.return_value = test_params
            MockLastUsed.return_value = mock_instance

            # Switch to custom plan via CLI without specifying custom limit
            settings = Settings.load_with_last_used(["--plan", "custom"])

            assert settings.plan == "custom"
            assert settings.custom_limit_tokens is None  # Should be reset

    def test_to_namespace(self):
        """
        Tests that the Settings instance is correctly converted to an argparse.Namespace with all fields accurately mapped.
        """
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

    def test_to_namespace_none_values(self):
        """
        Test that converting a Settings instance with default (None) values to an argparse.Namespace preserves None for optional fields.
        """
        settings = Settings(_cli_parse_args=[])
        namespace = settings.to_namespace()

        assert namespace.log_file is None
        assert namespace.reset_hour is None
        assert namespace.custom_limit_tokens is None


class TestSettingsIntegration:
    """Integration tests for Settings class."""

    def test_complete_workflow(self):
        """
        Integration test that verifies settings persistence and correct merging of CLI arguments with previously saved parameters across multiple runs using real file operations.
        
        Simulates two consecutive runs: the first saves settings with specific CLI arguments, and the second loads and merges new CLI arguments with the previously saved settings, ensuring correct precedence and persistence.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)

            # Mock the config directory
            with patch("claude_monitor.core.settings.LastUsedParams") as MockLastUsed:
                # Create real LastUsedParams instance with temp directory
                real_last_used = LastUsedParams(config_dir)
                MockLastUsed.return_value = real_last_used

                with patch(
                    "claude_monitor.core.settings.Settings._get_system_timezone",
                    return_value="UTC",
                ):
                    with patch(
                        "claude_monitor.core.settings.Settings._get_system_time_format",
                        return_value="24h",
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

    def test_settings_customise_sources(self):
        """
        Tests that `settings_customise_sources` returns only the "init_settings" source, ignoring other provided sources.
        """
        sources = Settings.settings_customise_sources(
            Settings,
            "init_settings",
            "env_settings",
            "dotenv_settings",
            "file_secret_settings",
        )

        # Should only return init_settings
        assert sources == ("init_settings",)
