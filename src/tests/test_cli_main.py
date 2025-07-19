"""Simplified tests for CLI main module."""

from pathlib import Path
from unittest.mock import Mock, patch

from claude_monitor.cli.main import main


class TestMain:
    """Test cases for main function."""

    def test_version_flag(self) -> None:
        """Test --version flag returns 0 and prints version."""
        with patch("builtins.print") as mock_print:
            result = main(["--version"])
            assert result == 0
            mock_print.assert_called_once()
            assert "claude-monitor" in mock_print.call_args[0][0]

    def test_v_flag(self) -> None:
        """Test -v flag returns 0 and prints version."""
        with patch("builtins.print") as mock_print:
            result = main(["-v"])
            assert result == 0
            mock_print.assert_called_once()
            assert "claude-monitor" in mock_print.call_args[0][0]

    @patch("claude_monitor.core.settings.Settings.load_with_last_used")
    def test_keyboard_interrupt_handling(self, mock_load: Mock) -> None:
        """Test keyboard interrupt returns 0."""
        mock_load.side_effect = KeyboardInterrupt()
        with patch("builtins.print") as mock_print:
            result = main(["--plan", "pro"])
            assert result == 0
            mock_print.assert_called_once_with("\n\nMonitoring stopped by user.")

    @patch("claude_monitor.core.settings.Settings.load_with_last_used")
    def test_exception_handling(self, mock_load_settings: Mock) -> None:
        """Test exception handling returns 1."""
        mock_load_settings.side_effect = Exception("Test error")

        with patch("builtins.print"), patch("traceback.print_exc"):
            result = main(["--plan", "pro"])
            assert result == 1

    @patch("claude_monitor.core.settings.Settings.load_with_last_used")
    def test_successful_main_execution(self, mock_load_settings: Mock) -> None:
        """Test successful main execution by mocking core components."""
        mock_args = Mock()
        mock_args.theme = None
        mock_args.plan = "pro"
        mock_args.timezone = "UTC"
        mock_args.refresh_per_second = 1.0
        mock_args.refresh_rate = 10

        mock_settings = Mock()
        mock_settings.log_file = None
        mock_settings.log_level = "INFO"
        mock_settings.timezone = "UTC"
        mock_settings.to_namespace.return_value = mock_args

        mock_load_settings.return_value = mock_settings

        # Get the actual module to avoid Python version compatibility issues with mock.patch
        import sys

        actual_module = sys.modules["claude_monitor.cli.main"]

        # Manually replace the function - this works across all Python versions
        original_discover = actual_module.discover_claude_data_paths
        actual_module.discover_claude_data_paths = Mock(
            return_value=[Path("/test/path")]
        )

        try:
            with (
                patch("claude_monitor.terminal.manager.setup_terminal"),
                patch("claude_monitor.terminal.themes.get_themed_console"),
                patch("claude_monitor.ui.display_controller.DisplayController"),
                patch("claude_monitor.monitoring.orchestrator.MonitoringOrchestrator"),
                patch("time.sleep", side_effect=KeyboardInterrupt),
                patch("sys.exit"),
            ):  # Don't actually exit
                result = main(["--plan", "pro"])
                assert result == 0
        finally:
            # Restore the original function
            actual_module.discover_claude_data_paths = original_discover


class TestFunctions:
    """Test module functions."""

    def test_get_standard_claude_paths(self) -> None:
        """Test getting standard Claude paths."""
        from claude_monitor.cli.main import get_standard_claude_paths

        paths = get_standard_claude_paths()
        assert isinstance(paths, list)
        assert len(paths) > 0
        assert "~/.claude/projects" in paths

    def test_discover_claude_data_paths_no_paths(self) -> None:
        """Test discover with no existing paths."""
        from claude_monitor.cli.main import discover_claude_data_paths

        with patch("pathlib.Path.exists", return_value=False):
            paths = discover_claude_data_paths()
            assert paths == []

    def test_discover_claude_data_paths_with_custom(self) -> None:
        """Test discover with custom paths."""
        from claude_monitor.cli.main import discover_claude_data_paths

        custom_paths = ["/custom/path"]
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("pathlib.Path.is_dir", return_value=True),
        ):
            paths = discover_claude_data_paths(custom_paths)
            assert len(paths) == 1
            assert paths[0].name == "path"
