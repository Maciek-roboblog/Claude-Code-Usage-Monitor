"""Test WSL utilities for proper Windows Subsystem for Linux support."""

import os
from pathlib import Path
from unittest.mock import Mock, patch

from claude_monitor.utils.wsl_utils import (
    WSLDetector,
    get_wsl_claude_paths,
    is_wsl_available,
)


class TestWSLDetector:
    """Test WSL detection functionality."""

    @patch("platform.system")
    def test_wsl_not_available_on_linux(self, mock_platform):
        """Test that WSL is not available on Linux."""
        mock_platform.return_value = "Linux"
        detector = WSLDetector()
        assert not detector.is_wsl_available()
        assert detector.get_distributions() == []

    @patch("platform.system")
    @patch("subprocess.run")
    def test_wsl_available_on_windows(self, mock_run, mock_platform):
        """Test WSL detection on Windows."""
        mock_platform.return_value = "Windows"
        mock_run.return_value = Mock(returncode=0, stdout="Ubuntu\nDebian\n")

        detector = WSLDetector()
        assert detector.is_wsl_available()

        distributions = detector.get_distributions()
        assert "Ubuntu" in distributions
        assert "Debian" in distributions

    @patch("platform.system")
    @patch("subprocess.run")
    def test_wsl_unavailable_on_windows(self, mock_run, mock_platform):
        """Test WSL not available on Windows."""
        mock_platform.return_value = "Windows"
        mock_run.side_effect = FileNotFoundError()

        detector = WSLDetector()
        assert not detector.is_wsl_available()

    @patch.dict(os.environ, {"USERNAME": "testuser"})
    def test_username_detection_windows(self):
        """Test username detection from Windows environment."""
        detector = WSLDetector()
        username = detector.get_current_user()
        assert username == "testuser"

    @patch.dict(os.environ, {"USER": "unixuser"}, clear=True)
    def test_username_detection_unix(self):
        """Test username detection from Unix environment."""
        detector = WSLDetector()
        username = detector.get_current_user()
        assert username == "unixuser"

    @patch("platform.system")
    @patch("subprocess.run")
    @patch.dict(os.environ, {"USERNAME": "testuser"})
    def test_claude_paths_generation(self, mock_run, mock_platform):
        """Test Claude paths are generated correctly."""
        mock_platform.return_value = "Windows"
        mock_run.return_value = Mock(returncode=0, stdout="Ubuntu\n")

        detector = WSLDetector()
        paths = detector.get_claude_paths()

        expected_paths = [
            "//wsl$/Ubuntu/home/testuser/.claude/projects",
            "//wsl.localhost/Ubuntu/home/testuser/.claude/projects",
        ]

        path_strs = [str(path) for path in paths]
        for expected in expected_paths:
            assert expected in path_strs

    @patch("platform.system")
    @patch("subprocess.run")
    def test_no_distributions_found(self, mock_run, mock_platform):
        """Test behavior when no WSL distributions are found."""
        mock_platform.return_value = "Windows"
        mock_run.return_value = Mock(returncode=0, stdout="")

        detector = WSLDetector()
        assert detector.is_wsl_available()  # WSL exists but no distros
        assert detector.get_distributions() == []
        assert detector.get_claude_paths() == []


class TestWSLUtilityFunctions:
    """Test utility functions for WSL support."""

    @patch("claude_monitor.utils.wsl_utils.WSLDetector")
    def test_get_wsl_claude_paths(self, mock_detector_class):
        """Test get_wsl_claude_paths function."""
        mock_detector = Mock()
        mock_detector.get_claude_paths.return_value = [
            Path("//wsl$/Ubuntu/home/user/.claude/projects")
        ]
        mock_detector_class.return_value = mock_detector

        paths = get_wsl_claude_paths()
        assert len(paths) == 1
        assert "Ubuntu" in str(paths[0])

    @patch("claude_monitor.utils.wsl_utils.WSLDetector")
    def test_is_wsl_available_with_distributions(self, mock_detector_class):
        """Test is_wsl_available function with distributions."""
        mock_detector = Mock()
        mock_detector.is_wsl_available.return_value = True
        mock_detector.get_distributions.return_value = ["Ubuntu"]
        mock_detector_class.return_value = mock_detector

        assert is_wsl_available() is True

    @patch("claude_monitor.utils.wsl_utils.WSLDetector")
    def test_is_wsl_available_no_distributions(self, mock_detector_class):
        """Test is_wsl_available function without distributions."""
        mock_detector = Mock()
        mock_detector.is_wsl_available.return_value = True
        mock_detector.get_distributions.return_value = []
        mock_detector_class.return_value = mock_detector

        assert is_wsl_available() is False
