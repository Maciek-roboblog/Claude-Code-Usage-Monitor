"""Test WSL integration with Claude data reader."""

from pathlib import Path
from unittest.mock import patch

from claude_monitor.data.reader import _resolve_claude_data_path


class TestWSLIntegration:
    """Test WSL integration with Claude data reader."""

    def test_custom_path_override(self):
        """Test that custom path overrides auto-detection."""
        custom_path = "/custom/path"
        result = _resolve_claude_data_path(custom_path)
        assert result == Path(custom_path).expanduser()

    @patch("claude_monitor.utils.wsl_utils.get_wsl_claude_paths")
    def test_wsl_path_resolution(self, mock_get_wsl_paths):
        """Test WSL path resolution in data reader."""
        # Test that WSL utils are called when available
        mock_get_wsl_paths.return_value = []  # No WSL paths available

        result = _resolve_claude_data_path()

        # Should call get_wsl_claude_paths
        mock_get_wsl_paths.assert_called_once()

        # Should fall back to default since no WSL paths
        assert result == Path("~/.claude/projects").expanduser()

    @patch("claude_monitor.utils.wsl_utils.get_wsl_claude_paths")
    def test_wsl_utilities_import_error(self, mock_import_error):
        """Test graceful handling of WSL utilities import error."""
        mock_import_error.side_effect = ImportError("WSL utilities not available")

        # Should fall back to default path without error
        result = _resolve_claude_data_path()
        assert result == Path("~/.claude/projects").expanduser()

    @patch("claude_monitor.utils.wsl_utils.get_wsl_claude_paths")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.rglob")
    def test_fallback_when_no_jsonl_files(
        self, mock_rglob, mock_exists, mock_get_wsl_paths
    ):
        """Test fallback to default when WSL paths have no JSONL files."""
        # Mock WSL path exists but has no JSONL files
        wsl_path = Path("//wsl$/Ubuntu/home/testuser/.claude/projects")
        default_path = Path("~/.claude/projects").expanduser()

        mock_get_wsl_paths.return_value = [wsl_path]
        mock_exists.return_value = False  # No paths exist
        mock_rglob.return_value = []  # No JSONL files

        result = _resolve_claude_data_path()

        # Should fall back to default
        assert result == default_path
