"""Tests for CLI main module."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from claude_monitor.cli.main import _get_initial_token_limit, _run_monitoring, main
from claude_monitor.core.plans import Plans


class TestMain:
    """Test cases for main function."""

    def test_version_flag(self):
        """
        Test that the `--version` CLI flag prints the version information and returns exit code 0.
        """
        with patch("builtins.print") as mock_print:
            result = main(["--version"])
            assert result == 0
            mock_print.assert_called_once()
            assert "claude-monitor" in mock_print.call_args[0][0]

    def test_v_flag(self):
        """
        Test that the `-v` CLI flag prints the version information and returns exit code 0.
        """
        with patch("builtins.print") as mock_print:
            result = main(["-v"])
            assert result == 0
            mock_print.assert_called_once()
            assert "claude-monitor" in mock_print.call_args[0][0]

    @patch("claude_monitor.cli.main.Settings.load_with_last_used")
    @patch("claude_monitor.cli.main.setup_environment")
    @patch("claude_monitor.cli.main.ensure_directories")
    @patch("claude_monitor.cli.main.setup_logging")
    @patch("claude_monitor.cli.main.init_timezone")
    @patch("claude_monitor.cli.main._run_monitoring")
    def test_successful_main_execution(
        self,
        mock_run_monitoring,
        mock_init_timezone,
        mock_setup_logging,
        mock_ensure_directories,
        mock_setup_environment,
        mock_load_settings,
    ):
        """
        Test that the main function completes successfully with all setup steps executed.
        
        Verifies that environment setup, directory creation, logging, timezone initialization, and monitoring are called, and that the main function returns exit code 0.
        """
        mock_settings = Mock()
        mock_settings.log_file = None
        mock_settings.log_level = "INFO"
        mock_settings.timezone = "UTC"
        mock_settings.to_namespace.return_value = Mock()
        mock_load_settings.return_value = mock_settings

        result = main(["--plan", "pro"])

        assert result == 0
        mock_setup_environment.assert_called_once()
        mock_ensure_directories.assert_called_once()
        mock_setup_logging.assert_called_once()
        mock_init_timezone.assert_called_once_with("UTC")
        mock_run_monitoring.assert_called_once()

    @patch("claude_monitor.cli.main.Settings.load_with_last_used")
    @patch("claude_monitor.cli.main.setup_environment")
    @patch("claude_monitor.cli.main.ensure_directories")
    @patch("claude_monitor.cli.main.setup_logging")
    @patch("claude_monitor.cli.main.init_timezone")
    @patch("claude_monitor.cli.main._run_monitoring")
    def test_main_with_log_file(
        self,
        mock_run_monitoring,
        mock_init_timezone,
        mock_setup_logging,
        mock_ensure_directories,
        mock_setup_environment,
        mock_load_settings,
    ):
        """
        Test that the main function sets up logging with the specified log file and log level when the --log-file argument is provided.
        
        Asserts that logging is configured correctly and main returns a success exit code.
        """
        mock_settings = Mock()
        mock_settings.log_file = "/tmp/test.log"
        mock_settings.log_level = "DEBUG"
        mock_settings.timezone = "America/New_York"
        mock_settings.to_namespace.return_value = Mock()
        mock_load_settings.return_value = mock_settings

        result = main(["--log-file", "/tmp/test.log"])

        assert result == 0
        mock_setup_logging.assert_called_once_with(
            "DEBUG", "/tmp/test.log", disable_console=True
        )

    def test_keyboard_interrupt_handling(self):
        """
        Test that a keyboard interrupt during settings loading causes the main function to exit gracefully with code 0 and prints a user stop message.
        """
        with patch("claude_monitor.cli.main.Settings.load_with_last_used") as mock_load:
            mock_load.side_effect = KeyboardInterrupt()
            with patch("builtins.print") as mock_print:
                result = main(["--plan", "pro"])
                assert result == 0
                mock_print.assert_called_once_with("\n\nMonitoring stopped by user.")

    @patch("claude_monitor.cli.main.Settings.load_with_last_used")
    def test_exception_handling(self, mock_load_settings):
        """
        Test that the main function returns exit code 1 and prints a traceback when an exception occurs during settings loading.
        """
        mock_load_settings.side_effect = Exception("Test error")

        with patch("builtins.print"), patch("traceback.print_exc"):
            result = main(["--plan", "pro"])
            assert result == 1


class TestGetInitialTokenLimit:
    """Test cases for _get_initial_token_limit function."""

    @pytest.fixture
    def mock_args_pro(self):
        """
        Create and return a mock arguments object configured for the "pro" plan.
        
        Returns:
            Mock: A mock object with the 'plan' attribute set to "pro".
        """
        args = Mock()
        args.plan = "pro"
        return args

    @pytest.fixture
    def mock_args_custom_with_limit(self):
        """
        Create a mock arguments object for a custom plan with an explicit token limit.
        
        Returns:
            Mock: A mock object with 'plan' set to "custom" and 'custom_limit_tokens' set to 500000.
        """
        args = Mock()
        args.plan = "custom"
        args.custom_limit_tokens = 500000
        return args

    @pytest.fixture
    def mock_args_custom_no_limit(self):
        """
        Create a mock arguments object for a custom plan without an explicit token limit.
        
        Returns:
            Mock: A mock object with 'plan' set to "custom" and 'custom_limit_tokens' set to None.
        """
        args = Mock()
        args.plan = "custom"
        args.custom_limit_tokens = None
        return args

    @patch("claude_monitor.cli.main.get_token_limit")
    def test_pro_plan_token_limit(self, mock_get_token_limit, mock_args_pro):
        """
        Verify that the token limit for the "pro" plan is correctly retrieved using the token limit function.
        
        Ensures that `_get_initial_token_limit` calls the token limit retrieval with the "pro" plan and returns the expected value.
        """
        mock_get_token_limit.return_value = 200000

        result = _get_initial_token_limit(mock_args_pro, "/test/path")

        assert result == 200000
        mock_get_token_limit.assert_called_once_with("pro")

    @patch("claude_monitor.cli.main.print_themed")
    def test_custom_plan_with_explicit_limit(
        self, mock_print_themed, mock_args_custom_with_limit
    ):
        """
        Test that an explicit token limit is used for a custom plan and a themed message is printed.
        
        Verifies that when a custom plan is provided with an explicit token limit, the limit is returned and the appropriate informational message is displayed.
        """
        result = _get_initial_token_limit(mock_args_custom_with_limit, "/test/path")

        assert result == 500000
        mock_print_themed.assert_called_once_with(
            "Using custom token limit: 500,000 tokens", style="info"
        )

    @patch("claude_monitor.cli.main.analyze_usage")
    @patch("claude_monitor.cli.main.get_token_limit")
    @patch("claude_monitor.cli.main.print_themed")
    def test_custom_plan_p90_calculation_success(
        self,
        mock_print_themed,
        mock_get_token_limit,
        mock_analyze_usage,
        mock_args_custom_no_limit,
    ):
        """
        Test that the initial token limit for a custom plan is correctly calculated using P90 usage analysis when no explicit limit is provided.
        
        Simulates successful usage analysis and verifies that the token limit is determined based on analyzed usage data.
        """
        mock_usage_data = {"blocks": [{"totalTokens": 150000}]}
        mock_analyze_usage.return_value = mock_usage_data
        mock_get_token_limit.return_value = 175000

        result = _get_initial_token_limit(mock_args_custom_no_limit, "/test/path")

        assert result == 175000
        mock_analyze_usage.assert_called_once_with(
            hours_back=24, quick_start=True, use_cache=False, data_path="/test/path"
        )
        mock_get_token_limit.assert_called_once_with(
            "custom", [{"totalTokens": 150000}]
        )

    @patch("claude_monitor.cli.main.analyze_usage")
    @patch("claude_monitor.cli.main.print_themed")
    def test_custom_plan_p90_calculation_failure(
        self, mock_print_themed, mock_analyze_usage, mock_args_custom_no_limit
    ):
        """
        Test that when usage analysis fails for a custom plan without an explicit token limit, the default token limit is used and a warning is logged.
        """
        mock_analyze_usage.side_effect = Exception("Analysis failed")

        with patch("logging.getLogger") as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            result = _get_initial_token_limit(mock_args_custom_no_limit, "/test/path")

            assert result == Plans.DEFAULT_TOKEN_LIMIT
            mock_logger.warning.assert_called_once()

    @patch("claude_monitor.cli.main.analyze_usage")
    @patch("claude_monitor.cli.main.print_themed")
    def test_custom_plan_no_usage_data(
        self, mock_print_themed, mock_analyze_usage, mock_args_custom_no_limit
    ):
        """
        Test that the token limit falls back to the default value when no usage data is available for a custom plan.
        """
        mock_analyze_usage.return_value = None

        result = _get_initial_token_limit(mock_args_custom_no_limit, "/test/path")

        assert result == Plans.DEFAULT_TOKEN_LIMIT


class TestRunMonitoring:
    """Test cases for _run_monitoring function."""

    @pytest.fixture
    def mock_args(self):
        """
        Create and return a mock object representing CLI arguments for monitoring tests.
        
        Returns:
            Mock: A mock object with default attributes for theme, plan, timezone, refresh_per_second, and refresh_rate.
        """
        args = Mock()
        args.theme = None
        args.plan = "pro"
        args.timezone = "UTC"
        args.refresh_per_second = 1.0
        args.refresh_rate = 10
        return args

    @patch("claude_monitor.cli.main.discover_claude_data_paths")
    @patch("claude_monitor.cli.main.print_themed")
    def test_no_data_paths_found(
        self, mock_print_themed, mock_discover_paths, mock_args
    ):
        """
        Test that an error message is printed when no Claude data directories are found during monitoring setup.
        """
        mock_discover_paths.return_value = []

        with patch("claude_monitor.cli.main.setup_terminal") as mock_setup:
            mock_setup.return_value = Mock()
            _run_monitoring(mock_args)

            mock_print_themed.assert_called_once_with(
                "No Claude data directory found", style="error"
            )

    @patch("claude_monitor.cli.main.discover_claude_data_paths")
    @patch("claude_monitor.cli.main._get_initial_token_limit")
    @patch("claude_monitor.cli.main.get_themed_console")
    @patch("claude_monitor.cli.main.setup_terminal")
    @patch("claude_monitor.cli.main.DisplayController")
    @patch("claude_monitor.cli.main.enter_alternate_screen")
    @patch("claude_monitor.cli.main.MonitoringOrchestrator")
    @patch("claude_monitor.cli.main.restore_terminal")
    def test_successful_monitoring_setup(
        self,
        mock_restore_terminal,
        mock_orchestrator_class,
        mock_enter_screen,
        mock_display_controller_class,
        mock_setup_terminal,
        mock_get_console,
        mock_get_token_limit,
        mock_discover_paths,
        mock_args,
    ):
        """
        Test that the monitoring setup initializes all components, registers callbacks, and starts the orchestrator as expected.
        
        Simulates a successful monitoring environment by mocking discovery of data paths, token limit retrieval, console and terminal setup, display controller, orchestrator, and live display context. Verifies that the orchestrator is started and required callbacks are registered.
        """
        # Setup mocks
        mock_discover_paths.return_value = [Path("/test/claude/data")]
        mock_get_token_limit.return_value = 200000
        mock_console = Mock()
        mock_get_console.return_value = mock_console
        mock_setup_terminal.return_value = Mock()

        mock_display_controller = Mock()
        mock_display_controller_class.return_value = mock_display_controller
        mock_live_manager = Mock()
        mock_display_controller.live_manager = mock_live_manager
        mock_live_display = Mock()
        mock_live_manager.create_live_display.return_value = mock_live_display
        mock_display_controller.create_loading_display.return_value = Mock()

        mock_orchestrator = Mock()
        mock_orchestrator_class.return_value = mock_orchestrator
        mock_orchestrator.wait_for_initial_data.return_value = True

        # Setup context manager for live display
        mock_live_display.__enter__ = Mock(return_value=mock_live_display)
        mock_live_display.__exit__ = Mock(return_value=None)

        with patch("logging.getLogger") as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            # The function will run until keyboard interrupt
            with patch("time.sleep", side_effect=KeyboardInterrupt):
                with patch("claude_monitor.cli.main.handle_cleanup_and_exit"):
                    _run_monitoring(mock_args)

            # Verify key setup calls
            mock_orchestrator.start.assert_called_once()
            mock_orchestrator.register_update_callback.assert_called_once()
            mock_orchestrator.register_session_callback.assert_called_once()

    @patch("claude_monitor.cli.main.discover_claude_data_paths")
    @patch("claude_monitor.cli.main._get_initial_token_limit")
    @patch("claude_monitor.cli.main.get_themed_console")
    @patch("claude_monitor.cli.main.setup_terminal")
    @patch("claude_monitor.cli.main.handle_cleanup_and_exit")
    def test_keyboard_interrupt_handling(
        self,
        mock_handle_cleanup,
        mock_setup_terminal,
        mock_get_console,
        mock_get_token_limit,
        mock_discover_paths,
        mock_args,
    ):
        """
        Test that a keyboard interrupt during monitoring setup triggers the cleanup handler.
        
        Simulates a keyboard interrupt when starting the monitoring orchestrator and verifies that the cleanup function is called with the previous terminal settings.
        """
        mock_discover_paths.return_value = [Path("/test/claude/data")]
        mock_get_token_limit.return_value = 200000
        mock_old_settings = Mock()
        mock_setup_terminal.return_value = mock_old_settings

        with patch("claude_monitor.cli.main.DisplayController") as mock_dc_class:
            mock_display_controller = Mock()
            mock_dc_class.return_value = mock_display_controller
            mock_live_manager = Mock()
            mock_display_controller.live_manager = mock_live_manager
            mock_live_display = Mock()
            mock_live_display.__enter__ = Mock(return_value=mock_live_display)
            mock_live_display.__exit__ = Mock(return_value=None)
            mock_live_manager.create_live_display.return_value = mock_live_display
            mock_display_controller.create_loading_display.return_value = Mock()

            with patch("claude_monitor.cli.main.enter_alternate_screen"):
                with patch(
                    "claude_monitor.cli.main.MonitoringOrchestrator"
                ) as mock_orch_class:
                    mock_orchestrator = Mock()
                    mock_orch_class.return_value = mock_orchestrator

                    # Simulate keyboard interrupt during monitoring setup
                    mock_orchestrator.start.side_effect = KeyboardInterrupt()

                    _run_monitoring(mock_args)

                    mock_handle_cleanup.assert_called_once_with(mock_old_settings)

    def test_themed_console_with_theme_arg(self, mock_args):
        """
        Verify that specifying a theme argument results in the themed console being created with the correct theme during monitoring setup.
        """
        mock_args.theme = "DARK"

        with patch("claude_monitor.cli.main.get_themed_console") as mock_get_console:
            with patch(
                "claude_monitor.cli.main.discover_claude_data_paths", return_value=[]
            ):
                with patch("claude_monitor.cli.main.setup_terminal"):
                    with patch("claude_monitor.cli.main.print_themed"):
                        _run_monitoring(mock_args)

                        mock_get_console.assert_called_once_with(force_theme="dark")


class TestMonitoringCallbacks:
    """Test monitoring callback functions."""

    @patch("claude_monitor.cli.main.discover_claude_data_paths")
    @patch("claude_monitor.cli.main._get_initial_token_limit")
    @patch("claude_monitor.cli.main.get_themed_console")
    @patch("claude_monitor.cli.main.setup_terminal")
    @patch("claude_monitor.cli.main.DisplayController")
    @patch("claude_monitor.cli.main.enter_alternate_screen")
    @patch("claude_monitor.cli.main.MonitoringOrchestrator")
    @patch("claude_monitor.cli.main.restore_terminal")
    def test_data_update_callback(
        self,
        mock_restore_terminal,
        mock_orchestrator_class,
        mock_enter_screen,
        mock_display_controller_class,
        mock_setup_terminal,
        mock_get_console,
        mock_get_token_limit,
        mock_discover_paths,
    ):
        """
        Test that the data update callback registered with the orchestrator correctly triggers the display controller to update the data display with new monitoring data.
        
        This test sets up mocks for all dependencies, captures the update callback during monitoring setup, and verifies that invoking the callback with test data results in the display controller's `create_data_display` method being called with the expected arguments.
        """
        # Setup basic mocks
        mock_args = Mock()
        mock_args.theme = None
        mock_args.plan = "pro"
        mock_args.timezone = "UTC"
        mock_args.refresh_rate = 10
        mock_args.refresh_per_second = 1.0

        mock_discover_paths.return_value = [Path("/test/claude/data")]
        mock_get_token_limit.return_value = 200000
        mock_setup_terminal.return_value = Mock()

        # Setup display controller
        mock_display_controller = Mock()
        mock_display_controller_class.return_value = mock_display_controller
        mock_live_manager = Mock()
        mock_display_controller.live_manager = mock_live_manager
        mock_live_display = Mock()
        mock_live_manager.create_live_display.return_value = mock_live_display
        mock_display_controller.create_loading_display.return_value = Mock()
        mock_display_controller.create_data_display.return_value = Mock()

        # Setup orchestrator to capture callback
        mock_orchestrator = Mock()
        mock_orchestrator_class.return_value = mock_orchestrator
        mock_orchestrator.wait_for_initial_data.return_value = True

        update_callback = None

        def capture_callback(callback):
            """
            Captures and stores a callback function for later invocation by assigning it to the enclosing scope's variable.
            """
            nonlocal update_callback
            update_callback = callback

        mock_orchestrator.register_update_callback.side_effect = capture_callback

        # Setup context manager
        mock_live_display.__enter__ = Mock(return_value=mock_live_display)
        mock_live_display.__exit__ = Mock(return_value=None)

        with patch("logging.getLogger"):
            with patch("time.sleep", side_effect=KeyboardInterrupt):
                with patch("claude_monitor.cli.main.handle_cleanup_and_exit"):
                    _run_monitoring(mock_args)

        # Test the captured callback
        assert update_callback is not None

        test_data = {
            "data": {"blocks": [{"isActive": True, "totalTokens": 1000}]},
            "token_limit": 200000,
        }

        with patch("logging.getLogger"):
            update_callback(test_data)

            mock_display_controller.create_data_display.assert_called_once_with(
                test_data["data"], mock_args, 200000
            )
