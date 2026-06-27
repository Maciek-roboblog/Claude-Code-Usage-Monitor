"""Tests for macOS appearance detection in BackgroundDetector."""

import subprocess
from unittest.mock import patch, MagicMock

import pytest

from claude_monitor.terminal.themes import BackgroundDetector, BackgroundType


class TestCheckMacosAppearance:
    """Test suite for BackgroundDetector._check_macos_appearance."""

    @patch("subprocess.run")
    def test_dark_mode_detected(self, mock_run: MagicMock) -> None:
        """Dark mode returns DARK background type."""
        mock_run.return_value = MagicMock(returncode=0, stdout="Dark\n")
        result = BackgroundDetector._check_macos_appearance()
        assert result == BackgroundType.DARK

    @patch("subprocess.run")
    def test_light_mode_detected(self, mock_run: MagicMock) -> None:
        """Light mode (key absent, non-zero exit) returns LIGHT background type."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr=(
                "2026-04-12 16:00:00.000 defaults[1234:5678]\n"
                "The domain/default pair of (kCFPreferencesAnyApplication, "
                "AppleInterfaceStyle) does not exist"
            ),
        )
        result = BackgroundDetector._check_macos_appearance()
        assert result == BackgroundType.LIGHT

    @patch("subprocess.run")
    def test_unexpected_nonzero_exit_falls_back_to_dark(self, mock_run: MagicMock) -> None:
        """Non-zero exit with unexpected stderr falls back to DARK for contrast safety."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="some unexpected error",
        )
        result = BackgroundDetector._check_macos_appearance()
        assert result == BackgroundType.DARK

    @patch("subprocess.run")
    def test_command_timeout_falls_back_to_dark(self, mock_run: MagicMock) -> None:
        """Timeout during detection falls back to DARK."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="defaults", timeout=2)
        result = BackgroundDetector._check_macos_appearance()
        assert result == BackgroundType.DARK

    @patch("subprocess.run")
    def test_command_not_found_falls_back_to_dark(self, mock_run: MagicMock) -> None:
        """Missing 'defaults' command (non-macOS) falls back to DARK."""
        mock_run.side_effect = FileNotFoundError()
        result = BackgroundDetector._check_macos_appearance()
        assert result == BackgroundType.DARK

    @patch("subprocess.run")
    def test_os_error_falls_back_to_dark(self, mock_run: MagicMock) -> None:
        """OS error falls back to DARK."""
        mock_run.side_effect = OSError("Permission denied")
        result = BackgroundDetector._check_macos_appearance()
        assert result == BackgroundType.DARK


class TestAppleTerminalDetection:
    """Test that Apple Terminal uses macOS appearance detection."""

    @patch.dict("os.environ", {"TERM_PROGRAM": "Apple_Terminal"}, clear=True)
    @patch.object(BackgroundDetector, "_check_macos_appearance")
    def test_apple_terminal_delegates_to_macos_appearance(
        self, mock_appearance: MagicMock
    ) -> None:
        """Apple Terminal should check macOS appearance instead of assuming light."""
        mock_appearance.return_value = BackgroundType.DARK
        result = BackgroundDetector._check_environment_hints()
        assert result == BackgroundType.DARK
        mock_appearance.assert_called_once()

    @patch.dict("os.environ", {"TERM_PROGRAM": "Apple_Terminal"}, clear=True)
    @patch.object(BackgroundDetector, "_check_macos_appearance")
    def test_apple_terminal_light_mode(
        self, mock_appearance: MagicMock
    ) -> None:
        """Apple Terminal in light mode returns LIGHT."""
        mock_appearance.return_value = BackgroundType.LIGHT
        result = BackgroundDetector._check_environment_hints()
        assert result == BackgroundType.LIGHT
        mock_appearance.assert_called_once()
