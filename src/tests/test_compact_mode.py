"""Comprehensive tests for compact mode functionality.

This module consolidates all tests related to the compact display mode,
including CLI parsing, configuration, formatting, and integration tests.
"""

import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from pydantic import ValidationError

from claude_monitor.compact.color_manager import CompactColorManager
from claude_monitor.compact.field_selector import CompactFieldSelector
from claude_monitor.core.models import CompactColorThresholds
from claude_monitor.core.settings import LastUsedParams, Settings


class TestCompactModeSettings:
    """Test suite for compact mode settings and configuration."""

    def test_compact_field_exists(self) -> None:
        """Test that compact field exists in Settings model."""
        settings = Settings(_cli_parse_args=[])
        assert hasattr(settings, "compact")
        assert settings.compact is False  # Default value

    def test_compact_cli_parsing_enabled(self) -> None:
        """Test compact mode can be enabled via CLI."""
        settings = Settings.load_with_last_used(["--compact"])
        assert settings.compact is True

    def test_compact_cli_parsing_disabled(self) -> None:
        """Test compact mode can be disabled via CLI."""
        settings = Settings.load_with_last_used(["--no-compact"])
        assert settings.compact is False

    def test_compact_persisted(self) -> None:
        """Test that compact mode is saved to last used params."""
        temp_dir = Path(tempfile.mkdtemp())
        last_used = LastUsedParams(temp_dir)

        try:
            # Create settings with compact enabled
            settings = Settings.load_with_last_used(["--compact"])
            settings.theme = "dark"  # Set another field

            # Save settings
            last_used.save(settings)

            # Load saved params and check compact is there
            saved_params = last_used.load()
            assert saved_params["compact"] is True
            assert "theme" in saved_params  # Other fields are also saved

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_compact_to_namespace(self) -> None:
        """Test that compact field is included in namespace conversion."""
        settings = Settings.load_with_last_used(["--compact"])
        args = settings.to_namespace()

        assert hasattr(args, "compact")
        assert args.compact is True

    def test_compact_default_to_namespace(self) -> None:
        """Test that compact defaults to False in namespace conversion."""
        settings = Settings(_cli_parse_args=[])
        args = settings.to_namespace()

        assert hasattr(args, "compact")
        assert args.compact is False

    def test_compact_compatibility_with_other_flags(self) -> None:
        """Test compact mode works with other CLI flags."""
        settings = Settings.load_with_last_used(
            ["--compact", "--plan", "pro", "--theme", "dark"]
        )

        assert settings.compact is True
        assert settings.plan == "pro"
        assert settings.theme == "dark"


class TestCompactFieldsParsing:
    """Test suite for compact fields CLI parsing."""

    def test_compact_fields_valid_single(self) -> None:
        """Test parsing single compact field."""
        settings = Settings(_cli_parse_args=["--compact-fields", "tokens"])
        assert settings.compact_fields == ["tokens"]

    def test_compact_fields_valid_multiple(self) -> None:
        """Test parsing multiple compact fields."""
        args = ["--compact-fields", "tokens,burn_rate,percentage"]
        settings = Settings(_cli_parse_args=args)
        assert settings.compact_fields == ["tokens", "burn_rate", "percentage"]

    def test_compact_fields_with_spaces(self) -> None:
        """Test parsing compact fields with spaces."""
        args = ["--compact-fields", "tokens, burn_rate, percentage"]
        settings = Settings(_cli_parse_args=args)
        assert settings.compact_fields == ["tokens", "burn_rate", "percentage"]

    def test_compact_fields_invalid(self) -> None:
        """Test parsing invalid compact fields raises error."""
        with pytest.raises(ValueError, match="Invalid compact fields"):
            Settings(_cli_parse_args=["--compact-fields", "invalid_field"])

    def test_compact_fields_default_none(self) -> None:
        """Test compact fields defaults to None."""
        settings = Settings(_cli_parse_args=[])
        assert settings.compact_fields is None

    def test_compact_fields_empty_string(self) -> None:
        """Test empty compact fields string."""
        with pytest.raises(ValueError):
            Settings(_cli_parse_args=["--compact-fields", ""])

    def test_compact_fields_all_valid_options(self) -> None:
        """Test all valid compact field options."""
        valid_fields = [
            "tokens",
            "percentage",
            "burn_rate",
            "time_remaining",
            "cost",
            "plan_info",
        ]
        args = ["--compact-fields", ",".join(valid_fields)]
        settings = Settings(_cli_parse_args=args)
        assert settings.compact_fields == valid_fields


class TestCompactColorThresholds:
    """Test suite for CompactColorThresholds model."""

    def test_default_values(self) -> None:
        """Test default threshold values."""
        thresholds = CompactColorThresholds()

        assert thresholds.low_threshold == 50.0
        assert thresholds.high_threshold == 80.0
        assert thresholds.burn_rate_critical == 80.0

    def test_valid_custom_values(self) -> None:
        """Test creating thresholds with valid custom values."""
        thresholds = CompactColorThresholds(
            low_threshold=30.0, high_threshold=70.0, burn_rate_critical=90.0
        )

        assert thresholds.low_threshold == 30.0
        assert thresholds.high_threshold == 70.0
        assert thresholds.burn_rate_critical == 90.0

    def test_boundary_values_minimum(self) -> None:
        """Test minimum boundary values."""
        thresholds = CompactColorThresholds(
            low_threshold=0.0, high_threshold=0.1, burn_rate_critical=0.0
        )
        assert thresholds.low_threshold == 0.0
        assert thresholds.high_threshold == 0.1
        assert thresholds.burn_rate_critical == 0.0

    def test_boundary_values_maximum(self) -> None:
        """Test maximum boundary values."""
        thresholds = CompactColorThresholds(
            low_threshold=99.9, high_threshold=100.0, burn_rate_critical=100.0
        )
        assert thresholds.low_threshold == 99.9
        assert thresholds.high_threshold == 100.0
        assert thresholds.burn_rate_critical == 100.0

    def test_invalid_negative_values(self) -> None:
        """Test invalid negative values raise error."""
        with pytest.raises(ValidationError):
            CompactColorThresholds(low_threshold=-1.0)

    def test_invalid_high_values(self) -> None:
        """Test invalid high values raise error."""
        with pytest.raises(ValidationError):
            CompactColorThresholds(high_threshold=150.0)

    def test_low_greater_than_high(self) -> None:
        """Test validation when low > high threshold."""
        with pytest.raises(ValidationError):
            CompactColorThresholds(low_threshold=80.0, high_threshold=50.0)


class TestCompactColorManager:
    """Test suite for CompactColorManager."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.default_thresholds = CompactColorThresholds(
            low_threshold=50.0, high_threshold=80.0, burn_rate_critical=80.0
        )
        self.color_manager = CompactColorManager(self.default_thresholds)

    def test_usage_color_low(self) -> None:
        """Test low usage color (green)."""
        assert self.color_manager.get_usage_color(25.0) == "[green]"
        assert self.color_manager.get_usage_color(49.9) == "[green]"

    def test_usage_color_medium(self) -> None:
        """Test medium usage color (yellow)."""
        assert self.color_manager.get_usage_color(50.0) == "[yellow]"
        assert self.color_manager.get_usage_color(75.0) == "[yellow]"
        assert self.color_manager.get_usage_color(79.9) == "[yellow]"

    def test_usage_color_high(self) -> None:
        """Test high usage color (red)."""
        assert self.color_manager.get_usage_color(80.0) == "[red]"
        assert self.color_manager.get_usage_color(95.0) == "[red]"
        assert self.color_manager.get_usage_color(120.0) == "[red]"

    def test_burn_rate_color_low(self) -> None:
        """Test low burn rate color (green)."""
        max_rate = 1000.0
        assert self.color_manager.get_burn_rate_color(100.0, max_rate) == "[green]"
        assert self.color_manager.get_burn_rate_color(499.0, max_rate) == "[green]"

    def test_burn_rate_color_medium(self) -> None:
        """Test medium burn rate color (orange)."""
        max_rate = 1000.0
        assert self.color_manager.get_burn_rate_color(500.0, max_rate) == "[orange1]"
        assert self.color_manager.get_burn_rate_color(750.0, max_rate) == "[yellow]"

    def test_burn_rate_color_critical(self) -> None:
        """Test critical burn rate color (red)."""
        max_rate = 1000.0
        assert self.color_manager.get_burn_rate_color(800.0, max_rate) == "[bold red]"
        assert self.color_manager.get_burn_rate_color(1000.0, max_rate) == "[bold red]"

    def test_burn_rate_color_zero_max_rate(self) -> None:
        """Test burn rate color with zero max rate."""
        assert self.color_manager.get_burn_rate_color(100.0, 0.0) == "[dim]"
        assert self.color_manager.get_burn_rate_color(0.0, 0.0) == "[dim]"

    def test_custom_thresholds(self) -> None:
        """Test color manager with custom thresholds."""
        custom_thresholds = CompactColorThresholds(
            low_threshold=30.0, high_threshold=70.0, burn_rate_critical=90.0
        )
        custom_manager = CompactColorManager(custom_thresholds)

        assert custom_manager.get_usage_color(25.0) == "[green]"
        assert custom_manager.get_usage_color(50.0) == "[yellow]"
        assert custom_manager.get_usage_color(75.0) == "[red]"

    def test_no_color_flag(self) -> None:
        """Test color manager with no_color flag."""
        no_color_manager = CompactColorManager(self.default_thresholds, no_color=True)

        assert no_color_manager.get_usage_color(75.0) == ""
        assert no_color_manager.get_burn_rate_color(500.0, 1000.0) == ""
        assert no_color_manager.get_close_color() == ""
        assert not no_color_manager._should_use_colors()

    @patch.dict(os.environ, {"NO_COLOR": "1"})
    def test_no_color_environment(self) -> None:
        """Test color detection with NO_COLOR environment variable."""
        manager = CompactColorManager(self.default_thresholds)
        assert not manager.color_support
        assert not manager._should_use_colors()

    @patch.dict(os.environ, {"FORCE_COLOR": "1"})
    def test_force_color_environment(self) -> None:
        """Test color detection with FORCE_COLOR environment variable."""
        manager = CompactColorManager(self.default_thresholds)
        assert manager.color_support

    def test_contextual_state_detection(self) -> None:
        """Test contextual state detection methods."""
        # Test critical state
        assert self.color_manager._is_critical_state(85.0, 900.0, 1000.0)
        assert self.color_manager._is_critical_state(75.0, 850.0, 1000.0)
        assert not self.color_manager._is_critical_state(75.0, 700.0, 1000.0)

        # Test warning state
        assert self.color_manager._is_warning_state(60.0, 600.0, 1000.0)
        assert self.color_manager._is_warning_state(40.0, 600.0, 1000.0)
        assert not self.color_manager._is_warning_state(40.0, 400.0, 1000.0)

        # Test success state
        assert self.color_manager._is_success_state(30.0)
        assert not self.color_manager._is_success_state(60.0)

    def test_apply_usage_color(self) -> None:
        """Test applying usage-based coloring to text."""
        result = self.color_manager.apply_usage_color("30%", 30.0)
        assert result == "[green]30%[/]"

        result = self.color_manager.apply_usage_color("85%", 85.0)
        assert result == "[red]85%[/]"

    def test_apply_burn_rate_color(self) -> None:
        """Test applying burn rate-based coloring to text."""
        result = self.color_manager.apply_burn_rate_color("400/min", 400.0, 1000.0)
        assert result == "[green]400/min[/]"

        result = self.color_manager.apply_burn_rate_color("900/min", 900.0, 1000.0)
        assert result == "[bold red]900/min[/]"


class TestCompactFieldSelector:
    """Test suite for CompactFieldSelector."""

    def test_init_with_fields(self) -> None:
        """Test initialization with field list."""
        selector = CompactFieldSelector(["tokens", "percentage"])
        assert selector.selected_fields == ["tokens", "percentage"]

    def test_init_without_fields(self) -> None:
        """Test initialization without field list uses defaults."""
        selector = CompactFieldSelector()
        assert len(selector.selected_fields) > 0
        assert "tokens" in selector.selected_fields

    def test_valid_field_names(self) -> None:
        """Test all valid field names are accepted."""
        valid_fields = [
            "tokens",
            "percentage",
            "burn_rate",
            "time_remaining",
            "cost",
            "plan_info",
        ]
        for field in valid_fields:
            selector = CompactFieldSelector([field])
            assert selector.selected_fields == [field]

    def test_invalid_field_raises_error(self) -> None:
        """Test invalid field name raises error."""
        from claude_monitor.compact.field_selector import CompactFieldValidationError

        with pytest.raises(CompactFieldValidationError):
            CompactFieldSelector(["invalid_field"])

    def test_duplicate_fields_removed(self) -> None:
        """Test duplicate fields are removed."""
        selector = CompactFieldSelector(["tokens", "tokens", "percentage"])
        assert selector.selected_fields == ["tokens", "percentage"]

    def test_field_order_preserved(self) -> None:
        """Test field order is preserved."""
        fields = ["percentage", "tokens", "burn_rate"]
        selector = CompactFieldSelector(fields)
        assert selector.selected_fields == fields


class TestCompactModeIntegration:
    """Integration tests for compact mode functionality."""

    def test_settings_with_all_compact_options(self) -> None:
        """Test settings with all compact options."""
        settings = Settings(
            _cli_parse_args=[
                "--compact",
                "--compact-fields",
                "tokens,percentage,burn_rate",
            ]
        )

        assert settings.compact is True
        assert settings.compact_fields == ["tokens", "percentage", "burn_rate"]

    def test_compact_mode_persistence_inclusion(self) -> None:
        """Test that compact mode options are persisted."""
        temp_dir = Path(tempfile.mkdtemp())
        last_used = LastUsedParams(temp_dir)

        try:
            # Create settings with all compact options
            settings = Settings(
                _cli_parse_args=[
                    "--compact",
                    "--compact-fields",
                    "tokens,percentage",
                    "--theme",
                    "dark",  # This should be persisted
                ]
            )

            # Save settings
            last_used.save(settings)

            # Load saved params
            saved_params = last_used.load()

            # Compact options should be saved
            assert saved_params["compact"] is True
            assert saved_params["compact_fields"] == ["tokens", "percentage"]

            # Other options should also be saved
            assert "theme" in saved_params
            assert saved_params["theme"] == "dark"

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_compact_mode_with_load_with_last_used(self) -> None:
        """Test compact mode works with load_with_last_used method."""
        temp_dir = Path(tempfile.mkdtemp())

        try:
            with patch("claude_monitor.core.settings.LastUsedParams") as MockLastUsed:
                mock_instance = Mock()
                mock_instance.load.return_value = {"theme": "light", "plan": "pro"}
                MockLastUsed.return_value = mock_instance

                settings = Settings.load_with_last_used(
                    [
                        "--compact",
                        "--compact-fields",
                        "tokens",
                        "--theme",
                        "dark",  # Override saved theme
                    ]
                )

                # Compact options from CLI
                assert settings.compact is True
                assert settings.compact_fields == ["tokens"]

                # CLI should override saved params
                assert settings.theme == "dark"

                # Saved params should be loaded
                assert settings.plan == "pro"

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_namespace_conversion_with_compact_options(self) -> None:
        """Test namespace conversion includes all compact options."""
        settings = Settings(
            _cli_parse_args=[
                "--compact",
                "--compact-fields",
                "tokens,percentage",
            ]
        )

        namespace = settings.to_namespace()

        assert hasattr(namespace, "compact")
        assert namespace.compact is True

        assert hasattr(namespace, "compact_fields")
        assert namespace.compact_fields == ["tokens", "percentage"]

    @patch("claude_monitor.core.settings.Settings._get_system_timezone")
    @patch("claude_monitor.core.settings.Settings._get_system_time_format")
    def test_compact_mode_with_auto_detection(
        self, mock_time_format: Mock, mock_timezone: Mock
    ) -> None:
        """Test compact mode works with auto timezone/format detection."""
        mock_timezone.return_value = "UTC"
        mock_time_format.return_value = "24h"

        settings = Settings.load_with_last_used(
            ["--compact", "--timezone", "auto", "--time-format", "auto"]
        )

        assert settings.compact is True
        assert settings.timezone == "UTC"  # Should be resolved from auto
        assert settings.time_format == "24h"  # Should be resolved from auto


class TestCompactModeValidation:
    """Test validation and error handling for compact mode."""

    def test_compact_fields_validation_empty_list(self) -> None:
        """Test validation with empty compact fields list."""
        with pytest.raises(ValueError):
            Settings(_cli_parse_args=["--compact-fields", ""])

    def test_compact_fields_validation_mixed_valid_invalid(self) -> None:
        """Test validation with mix of valid and invalid fields."""
        with pytest.raises(ValueError, match="Invalid compact fields"):
            args = ["--compact-fields", "tokens,invalid_field,percentage"]
            Settings(_cli_parse_args=args)

    def test_color_thresholds_validation_order(self) -> None:
        """Test color thresholds validation for correct order."""
        # Valid order
        thresholds = CompactColorThresholds(low_threshold=30.0, high_threshold=80.0)
        assert thresholds.low_threshold < thresholds.high_threshold

        # Invalid order should raise error
        with pytest.raises(ValidationError):
            CompactColorThresholds(low_threshold=80.0, high_threshold=30.0)


class TestCompactModeHelp:
    """Test help and description for compact mode options."""

    def test_compact_fields_have_descriptions(self) -> None:
        """Test that compact mode fields have proper descriptions."""
        field_info = Settings.model_fields

        assert "compact" in field_info
        assert field_info["compact"].description is not None

    def test_compact_fields_default_values_documented(self) -> None:
        """Test that default values are properly set."""
        settings = Settings(_cli_parse_args=[])

        assert settings.compact is False
