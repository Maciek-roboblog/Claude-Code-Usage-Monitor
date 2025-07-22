"""Simplified tests for CLI main module."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

from claude_monitor.cli.main import _run_json_output, main


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
        mock_args.json_output = False

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

    @patch("claude_monitor.core.settings.Settings.load_with_last_used")
    def test_json_output_mode_triggered(self, mock_load_settings: Mock) -> None:
        """Test that JSON output mode is triggered when --json-output flag is used."""
        mock_args = Mock()
        mock_args.json_output = True
        mock_args.plan = "pro"
        
        mock_settings = Mock()
        mock_settings.log_file = None
        mock_settings.log_level = "INFO"
        mock_settings.timezone = "UTC"
        mock_settings.to_namespace.return_value = mock_args
        mock_load_settings.return_value = mock_settings

        with (
            patch("claude_monitor.cli.main._run_json_output", return_value=0) as mock_json_output,
            patch("claude_monitor.cli.main._run_monitoring") as mock_monitoring,
        ):
            result = main(["--json-output", "--plan", "pro"])
            
            assert result == 0
            mock_json_output.assert_called_once_with(mock_args)
            mock_monitoring.assert_not_called()

    @patch("claude_monitor.core.settings.Settings.load_with_last_used")
    def test_normal_mode_when_no_json_flag(self, mock_load_settings: Mock) -> None:
        """Test that normal monitoring mode runs when --json-output is not used."""
        mock_args = Mock()
        mock_args.json_output = False
        mock_args.plan = "pro"
        mock_args.theme = None
        mock_args.refresh_per_second = 1.0
        mock_args.refresh_rate = 10
        
        mock_settings = Mock()
        mock_settings.log_file = None
        mock_settings.log_level = "INFO"
        mock_settings.timezone = "UTC"
        mock_settings.to_namespace.return_value = mock_args
        mock_load_settings.return_value = mock_settings

        with (
            patch("claude_monitor.cli.main._run_json_output") as mock_json_output,
            patch("claude_monitor.cli.main._run_monitoring") as mock_monitoring,
            patch("claude_monitor.cli.main.discover_claude_data_paths", return_value=[Path("/test/path")]),
            patch("claude_monitor.terminal.manager.setup_terminal"),
            patch("claude_monitor.terminal.themes.get_themed_console"),
            patch("claude_monitor.ui.display_controller.DisplayController"),
            patch("claude_monitor.monitoring.orchestrator.MonitoringOrchestrator"),
            patch("time.sleep", side_effect=KeyboardInterrupt),
        ):
            result = main(["--plan", "pro"])
            
            assert result == 0
            mock_json_output.assert_not_called()
            mock_monitoring.assert_called_once()


class TestJsonOutput:
    """Test cases for JSON output functionality."""

    @patch("claude_monitor.cli.main.analyze_usage")
    @patch("claude_monitor.cli.main.discover_claude_data_paths")
    def test_json_output_success(self, mock_discover_paths: Mock, mock_analyze_usage: Mock) -> None:
        """Test successful JSON output with valid data."""
        # Setup mocks
        mock_discover_paths.return_value = [Path("/test/path")]
        mock_usage_data = {
            "blocks": [
                {
                    "id": "test-session",
                    "isActive": True,
                    "totalTokens": 1500,
                    "costUSD": 0.75,
                    "startTime": "2025-01-20T10:00:00Z",
                    "endTime": "2025-01-20T15:00:00Z"
                }
            ],
            "metadata": {
                "generated_at": "2025-01-20T15:30:00Z",
                "entries_count": 1
            }
        }
        mock_analyze_usage.return_value = mock_usage_data

        # Create args mock  
        args = Mock()
        args.plan = "pro"

        # Capture stdout
        with patch("builtins.print") as mock_print:
            result = _run_json_output(args)

        # Verify result
        assert result == 0
        mock_print.assert_called_once()
        
        # Parse and verify JSON output
        json_output = mock_print.call_args[0][0]
        parsed_output = json.loads(json_output)
        
        assert parsed_output["success"] is True
        assert parsed_output["error"] is None
        assert parsed_output["data"] == mock_usage_data
        assert parsed_output["metadata"]["data_path"] == "/test/path"
        assert parsed_output["metadata"]["plan"] == "pro"
        assert "version" in parsed_output["metadata"]

    @patch("claude_monitor.cli.main.discover_claude_data_paths")
    def test_json_output_no_claude_data_directory(self, mock_discover_paths: Mock) -> None:
        """Test JSON output when no Claude data directory is found."""
        mock_discover_paths.return_value = []

        args = Mock()
        args.plan = "pro"

        with patch("builtins.print") as mock_print:
            result = _run_json_output(args)

        assert result == 1
        mock_print.assert_called_once()
        
        json_output = mock_print.call_args[0][0]
        parsed_output = json.loads(json_output)
        
        assert parsed_output["success"] is False
        assert parsed_output["error"] == "No Claude data directory found"
        assert parsed_output["data"] is None
        assert "version" in parsed_output["metadata"]

    @patch("claude_monitor.cli.main.analyze_usage")
    @patch("claude_monitor.cli.main.discover_claude_data_paths")
    def test_json_output_analyze_usage_returns_none(self, mock_discover_paths: Mock, mock_analyze_usage: Mock) -> None:
        """Test JSON output when analyze_usage returns None."""
        mock_discover_paths.return_value = [Path("/test/path")]
        mock_analyze_usage.return_value = None

        args = Mock()
        args.plan = "pro"

        with patch("builtins.print") as mock_print:
            result = _run_json_output(args)

        assert result == 1
        mock_print.assert_called_once()
        
        json_output = mock_print.call_args[0][0]
        parsed_output = json.loads(json_output)
        
        assert parsed_output["success"] is False
        assert parsed_output["error"] == "Failed to analyze usage data"
        assert parsed_output["data"] is None
        assert "version" in parsed_output["metadata"]

    @patch("claude_monitor.cli.main.analyze_usage")
    @patch("claude_monitor.cli.main.discover_claude_data_paths")
    def test_json_output_with_exception(self, mock_discover_paths: Mock, mock_analyze_usage: Mock) -> None:
        """Test JSON output when an exception occurs during analysis."""
        mock_discover_paths.return_value = [Path("/test/path")]
        mock_analyze_usage.side_effect = Exception("Test exception")

        args = Mock()
        args.plan = "pro"

        with patch("builtins.print") as mock_print:
            result = _run_json_output(args)

        assert result == 1
        mock_print.assert_called_once()
        
        json_output = mock_print.call_args[0][0]
        parsed_output = json.loads(json_output)
        
        assert parsed_output["success"] is False
        assert parsed_output["error"] == "Test exception"
        assert parsed_output["data"] is None
        assert "version" in parsed_output["metadata"]

    @patch("claude_monitor.cli.main.analyze_usage")
    @patch("claude_monitor.cli.main.discover_claude_data_paths")
    def test_json_output_with_custom_hours_back(self, mock_discover_paths: Mock, mock_analyze_usage: Mock) -> None:
        """Test JSON output uses custom hours_back parameter."""
        mock_discover_paths.return_value = [Path("/test/path")]
        mock_usage_data = {"blocks": [], "metadata": {"generated_at": "2025-01-20T15:30:00Z"}}
        mock_analyze_usage.return_value = mock_usage_data

        args = Mock()
        args.plan = "custom"
        args.hours_back = 48  # Custom value

        with patch("builtins.print"):
            result = _run_json_output(args)

        assert result == 0
        mock_analyze_usage.assert_called_once_with(
            hours_back=48,
            use_cache=True,
            quick_start=False,
            data_path="/test/path"
        )

    @patch("claude_monitor.cli.main.analyze_usage")
    @patch("claude_monitor.cli.main.discover_claude_data_paths")
    def test_json_output_metadata_structure(self, mock_discover_paths: Mock, mock_analyze_usage: Mock) -> None:
        """Test that JSON output metadata has correct structure."""
        mock_discover_paths.return_value = [Path("/custom/path")]
        mock_usage_data = {
            "blocks": [],
            "metadata": {"generated_at": "2025-01-20T15:30:00Z", "entries_count": 0}
        }
        mock_analyze_usage.return_value = mock_usage_data

        args = Mock()
        args.plan = "max20"
        args.hours_back = 72

        with patch("builtins.print") as mock_print:
            result = _run_json_output(args)

        assert result == 0
        
        json_output = mock_print.call_args[0][0]
        parsed_output = json.loads(json_output)
        
        # Verify metadata structure
        metadata = parsed_output["metadata"]
        assert metadata["data_path"] == "/custom/path"
        assert metadata["hours_back"] == 72
        assert metadata["plan"] == "max20"
        assert metadata["generated_at"] == "2025-01-20T15:30:00Z"
        assert "version" in metadata


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
