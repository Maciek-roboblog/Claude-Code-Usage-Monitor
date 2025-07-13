"""Tests for DisplayController class."""

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

import pytest

from claude_monitor.ui.display_controller import (
    DisplayController,
    LiveDisplayManager,
    ScreenBufferManager,
    SessionCalculator,
)


class TestDisplayController:
    """Test cases for DisplayController class."""

    @pytest.fixture
    def controller(self):
        """
        Creates a DisplayController instance with the NotificationManager patched for testing purposes.
        
        Returns:
            DisplayController: An instance of DisplayController with NotificationManager mocked.
        """
        with patch("claude_monitor.ui.display_controller.NotificationManager"):
            return DisplayController()

    @pytest.fixture
    def sample_active_block(self):
        """
        Return a sample dictionary representing an active session block with token usage, cost, message count, per-model statistics, entries, and timestamps.
        """
        return {
            "isActive": True,
            "totalTokens": 15000,
            "costUSD": 0.45,
            "sentMessagesCount": 12,
            "perModelStats": {
                "claude-3-opus": {"inputTokens": 5000, "outputTokens": 3000},
                "claude-3-5-sonnet": {"inputTokens": 4000, "outputTokens": 3000},
            },
            "entries": [
                {"timestamp": "2024-01-01T12:00:00Z", "tokens": 5000},
                {"timestamp": "2024-01-01T12:30:00Z", "tokens": 10000},
            ],
            "startTime": "2024-01-01T11:00:00Z",
            "endTime": "2024-01-01T13:00:00Z",
        }

    @pytest.fixture
    def sample_args(self):
        """
        Provides a mock object representing sample CLI arguments for testing.
        
        Returns:
            args (Mock): A mock object with attributes for plan, timezone, time format, and custom token limit.
        """
        args = Mock()
        args.plan = "pro"
        args.timezone = "UTC"
        args.time_format = "24h"
        args.custom_limit_tokens = None
        return args

    def test_init(self, controller):
        """
        Verify that the DisplayController initializes all required components.
        """
        assert controller.session_display is not None
        assert controller.loading_screen is not None
        assert controller.error_display is not None
        assert controller.screen_manager is not None
        assert controller.live_manager is not None
        assert controller.notification_manager is not None

    def test_extract_session_data(self, controller, sample_active_block):
        """
        Test that the DisplayController correctly extracts session data fields from an active session block.
        
        Verifies that tokens used, session cost, sent messages, entries count, and start time string are accurately parsed from the provided session data.
        """
        result = controller._extract_session_data(sample_active_block)

        assert result["tokens_used"] == 15000
        assert result["session_cost"] == 0.45
        assert result["sent_messages"] == 12
        assert len(result["entries"]) == 2
        assert result["start_time_str"] == "2024-01-01T11:00:00Z"

    def test_calculate_token_limits_standard_plan(self, controller, sample_args):
        """
        Test that token limit calculation returns the default limits for standard plans.
        
        Verifies that the `_calculate_token_limits` method returns the provided token limit as both the maximum and remaining limits when using standard plan arguments.
        """
        token_limit = 200000

        result = controller._calculate_token_limits(sample_args, token_limit)

        assert result == (200000, 200000)

    def test_calculate_token_limits_custom_plan(self, controller, sample_args):
        """
        Test that token limit calculation returns the explicit custom limit for custom plans.
        
        Verifies that when a custom plan and custom token limit are specified, the controller returns the custom limit for both the plan and session.
        """
        sample_args.plan = "custom"
        sample_args.custom_limit_tokens = 500000
        token_limit = 200000

        result = controller._calculate_token_limits(sample_args, token_limit)

        assert result == (500000, 500000)

    def test_calculate_token_limits_custom_plan_no_limit(self, controller, sample_args):
        """
        Test that token limit calculation for a custom plan without a specified custom limit falls back to the provided default token limit.
        """
        sample_args.plan = "custom"
        sample_args.custom_limit_tokens = None
        token_limit = 200000

        result = controller._calculate_token_limits(sample_args, token_limit)

        assert result == (200000, 200000)

    @patch("claude_monitor.ui.display_controller.calculate_hourly_burn_rate")
    def test_calculate_time_data(self, mock_burn_rate, controller):
        """
        Test that the controller's time data calculation method returns the expected elapsed and total session minutes and reset time using mocked session calculator output.
        """
        session_data = {
            "start_time_str": "2024-01-01T11:00:00Z",
            "end_time_str": "2024-01-01T13:00:00Z",
        }
        current_time = datetime(2024, 1, 1, 12, 30, 0, tzinfo=timezone.utc)

        with patch.object(
            controller.session_calculator, "calculate_time_data"
        ) as mock_calc:
            mock_calc.return_value = {
                "elapsed_session_minutes": 90,
                "total_session_minutes": 120,
                "reset_time": current_time + timedelta(hours=12),
            }

            result = controller._calculate_time_data(session_data, current_time)

            assert result["elapsed_session_minutes"] == 90
            assert result["total_session_minutes"] == 120
            mock_calc.assert_called_once_with(session_data, current_time)

    @patch("claude_monitor.ui.display_controller.Plans.is_valid_plan")
    def test_calculate_cost_predictions_valid_plan(
        self, mock_is_valid, controller, sample_args
    ):
        """
        Verify that cost predictions are correctly calculated for valid plans using the provided session data, time data, and cost limit.
        """
        mock_is_valid.return_value = True
        session_data = {"session_cost": 0.45}
        time_data = {"elapsed_session_minutes": 90}
        cost_limit_p90 = 5.0

        with patch.object(
            controller.session_calculator, "calculate_cost_predictions"
        ) as mock_calc:
            mock_calc.return_value = {
                "cost_limit": 5.0,
                "predicted_end_time": datetime.now(timezone.utc),
            }

            result = controller._calculate_cost_predictions(
                session_data, time_data, sample_args, cost_limit_p90
            )

            assert result["cost_limit"] == 5.0
            mock_calc.assert_called_once_with(session_data, time_data, 5.0)

    def test_calculate_cost_predictions_invalid_plan(self, controller, sample_args):
        """
        Verify that cost prediction calculation for an invalid plan uses the default cost limit and calls the calculator with correct arguments.
        """
        sample_args.plan = "invalid"
        session_data = {"session_cost": 0.45}
        time_data = {"elapsed_session_minutes": 90}

        with patch.object(
            controller.session_calculator, "calculate_cost_predictions"
        ) as mock_calc:
            mock_calc.return_value = {
                "cost_limit": 100.0,
                "predicted_end_time": datetime.now(timezone.utc),
            }

            controller._calculate_cost_predictions(
                session_data, time_data, sample_args, None
            )

            mock_calc.assert_called_once_with(session_data, time_data, 100.0)

    def test_check_notifications_switch_to_custom(self, controller):
        """
        Test that the notification logic correctly triggers and marks the "switch_to_custom" notification when appropriate conditions are met.
        
        Verifies that the notification manager's methods are called as expected and that the result indicates the switch notification should be shown.
        """
        with patch.object(
            controller.notification_manager, "should_notify"
        ) as mock_should:
            with patch.object(
                controller.notification_manager, "mark_notified"
            ) as mock_mark:
                with patch.object(
                    controller.notification_manager, "is_notification_active"
                ) as mock_active:
                    # Configure should_notify to return True only for switch_to_custom
                    def should_notify_side_effect(notification_type):
                        """
                        Determine if a notification should be triggered for the given notification type.
                        
                        Returns:
                            bool: True if the notification type is "switch_to_custom", otherwise False.
                        """
                        return notification_type == "switch_to_custom"

                    mock_should.side_effect = should_notify_side_effect
                    mock_active.return_value = False

                    result = controller._check_notifications(
                        token_limit=500000,
                        original_limit=200000,
                        session_cost=2.0,
                        cost_limit=5.0,
                        predicted_end_time=datetime.now(timezone.utc)
                        + timedelta(hours=2),
                        reset_time=datetime.now(timezone.utc) + timedelta(hours=12),
                    )

                    assert result["show_switch_notification"] is True
                    # Verify switch_to_custom was called
                    assert any(
                        call[0][0] == "switch_to_custom"
                        for call in mock_should.call_args_list
                    )
                    mock_mark.assert_called_with("switch_to_custom")

    def test_check_notifications_exceed_limit(self, controller):
        """
        Test that the notification logic correctly triggers and marks the "exceed_max_limit" notification when the session cost exceeds the cost limit.
        
        This test mocks the notification manager's methods to simulate the notification state and verifies that the exceed notification is shown and marked as notified when appropriate.
        """
        with patch.object(
            controller.notification_manager, "should_notify"
        ) as mock_should:
            with patch.object(
                controller.notification_manager, "mark_notified"
            ) as mock_mark:
                with patch.object(
                    controller.notification_manager, "is_notification_active"
                ) as mock_active:
                    # Configure should_notify to return True only for exceed_max_limit
                    def should_notify_side_effect(notification_type):
                        """
                        Determine if a notification should be triggered based on the notification type.
                        
                        Returns:
                            bool: True if the notification type is "exceed_max_limit", otherwise False.
                        """
                        return notification_type == "exceed_max_limit"

                    mock_should.side_effect = should_notify_side_effect
                    mock_active.return_value = False

                    result = controller._check_notifications(
                        token_limit=200000,
                        original_limit=200000,
                        session_cost=6.0,  # Exceeds limit
                        cost_limit=5.0,
                        predicted_end_time=datetime.now(timezone.utc)
                        + timedelta(hours=2),
                        reset_time=datetime.now(timezone.utc) + timedelta(hours=12),
                    )

                    assert result["show_exceed_notification"] is True
                    # Verify exceed_max_limit was called
                    assert any(
                        call[0][0] == "exceed_max_limit"
                        for call in mock_should.call_args_list
                    )
                    mock_mark.assert_called_with("exceed_max_limit")

    def test_check_notifications_cost_will_exceed(self, controller):
        """
        Test that the notification for "cost will exceed" is triggered when the predicted end time is before the reset time.
        
        Verifies that the notification manager's `should_notify` and `mark_notified` methods are called appropriately and that the result indicates the notification should be shown.
        """
        with patch.object(
            controller.notification_manager, "should_notify"
        ) as mock_should:
            with patch.object(
                controller.notification_manager, "mark_notified"
            ) as mock_mark:
                mock_should.return_value = True

                # Predicted end time before reset time
                predicted_end = datetime.now(timezone.utc) + timedelta(hours=1)
                reset_time = datetime.now(timezone.utc) + timedelta(hours=12)

                result = controller._check_notifications(
                    token_limit=200000,
                    original_limit=200000,
                    session_cost=2.0,
                    cost_limit=5.0,
                    predicted_end_time=predicted_end,
                    reset_time=reset_time,
                )

                assert result["show_cost_will_exceed"] is True
                mock_should.assert_called_with("cost_will_exceed")
                mock_mark.assert_called_with("cost_will_exceed")

    @patch("claude_monitor.ui.display_controller.TimezoneHandler")
    @patch("claude_monitor.ui.display_controller.get_time_format_preference")
    @patch("claude_monitor.ui.display_controller.format_display_time")
    def test_format_display_times(
        self,
        mock_format_time,
        mock_get_format,
        mock_tz_handler_class,
        controller,
        sample_args,
    ):
        """
        Tests that the display time formatting method returns correctly formatted time strings for current, predicted end, and reset times.
        """
        mock_tz_handler = Mock()
        mock_tz_handler.validate_timezone.return_value = True
        mock_tz_handler.convert_to_timezone.return_value = datetime.now(timezone.utc)
        mock_tz_handler_class.return_value = mock_tz_handler

        mock_get_format.return_value = "24h"
        mock_format_time.return_value = "12:00:00"

        current_time = datetime.now(timezone.utc)
        predicted_end = current_time + timedelta(hours=2)
        reset_time = current_time + timedelta(hours=12)

        result = controller._format_display_times(
            sample_args, current_time, predicted_end, reset_time
        )

        assert "predicted_end_str" in result
        assert "reset_time_str" in result
        assert "current_time_str" in result

    def test_calculate_model_distribution_empty_stats(self, controller):
        """
        Test that model distribution calculation returns an empty dictionary when given empty statistics.
        """
        result = controller._calculate_model_distribution({})
        assert result == {}

    @patch("claude_monitor.ui.display_controller.normalize_model_name")
    def test_calculate_model_distribution_valid_stats(self, mock_normalize, controller):
        """
        Verify that the model distribution calculation correctly computes percentage usage for each model given valid token statistics and normalization.
        """
        mock_normalize.side_effect = lambda x: {
            "claude-3-opus": "claude-3-opus",
            "claude-3-5-sonnet": "claude-3.5-sonnet",
        }.get(x, "unknown")

        raw_stats = {
            "claude-3-opus": {"input_tokens": 5000, "output_tokens": 3000},
            "claude-3-5-sonnet": {"input_tokens": 4000, "output_tokens": 3000},
        }

        result = controller._calculate_model_distribution(raw_stats)

        # Total tokens: opus=8000, sonnet=7000, total=15000
        expected_opus_pct = (8000 / 15000) * 100  # ~53.33%
        expected_sonnet_pct = (7000 / 15000) * 100  # ~46.67%

        assert abs(result["claude-3-opus"] - expected_opus_pct) < 0.1
        assert abs(result["claude-3.5-sonnet"] - expected_sonnet_pct) < 0.1

    def test_create_data_display_no_data(self, controller, sample_args):
        """
        Test that `create_data_display` returns an error screen renderable when called with no data.
        """
        result = controller.create_data_display({}, sample_args, 200000)

        assert result is not None
        # Should return error screen renderable

    def test_create_data_display_no_active_block(self, controller, sample_args):
        """
        Test that create_data_display returns the appropriate screen when there are no active session blocks.
        
        Verifies that when the input data contains only inactive blocks, the method returns a non-null renderable indicating no active session.
        """
        data = {"blocks": [{"isActive": False, "totalTokens": 1000}]}

        result = controller.create_data_display(data, sample_args, 200000)

        assert result is not None
        # Should return no active session screen

    @patch("claude_monitor.ui.display_controller.Plans.is_valid_plan")
    @patch("claude_monitor.core.plans.get_cost_limit")
    @patch("claude_monitor.ui.display_controller.Plans.get_message_limit")
    def test_create_data_display_with_active_block(
        self,
        mock_msg_limit,
        mock_cost_limit,
        mock_is_valid,
        controller,
        sample_args,
        sample_active_block,
    ):
        """
        Test that `create_data_display` correctly processes and renders an active session when valid session data is present.
        
        This test mocks plan validation, cost and message limit retrieval, and session data processing to ensure the display controller produces a non-null renderable output for an active session block.
        """
        mock_is_valid.return_value = True
        mock_cost_limit.return_value = 5.0
        mock_msg_limit.return_value = 1000

        data = {"blocks": [sample_active_block]}

        with patch.object(controller, "_process_active_session_data") as mock_process:
            mock_process.return_value = {
                "plan": "pro",
                "timezone": "UTC",
                "tokens_used": 15000,
                "token_limit": 200000,
                "usage_percentage": 7.5,
                "tokens_left": 185000,
                "elapsed_session_minutes": 90,
                "total_session_minutes": 120,
                "burn_rate": 10.0,
                "session_cost": 0.45,
                "per_model_stats": {},
                "model_distribution": {},
                "sent_messages": 12,
                "entries": [],
                "predicted_end_str": "14:00",
                "reset_time_str": "00:00",
                "current_time_str": "12:30",
                "show_switch_notification": False,
                "show_exceed_notification": False,
                "show_tokens_will_run_out": False,
                "original_limit": 200000,
                "cost_limit_p90": 5.0,
                "messages_limit_p90": 1000,
            }

            with patch.object(
                controller.session_display, "format_active_session_screen"
            ) as mock_format:
                mock_format.return_value = ["Sample screen buffer"]

                result = controller.create_data_display(data, sample_args, 200000)

                assert result is not None
                mock_process.assert_called_once()
                mock_format.assert_called_once()

    def test_create_loading_display(self, controller):
        """
        Test that the loading display is created successfully for the given plan, timezone, and message.
        """
        result = controller.create_loading_display("pro", "UTC", "Loading...")

        assert result is not None

    def test_create_error_display(self, controller):
        """
        Test that the error display is created successfully for a given plan and timezone.
        
        Asserts that the returned error display renderable is not None.
        """
        result = controller.create_error_display("pro", "UTC")

        assert result is not None

    def test_create_live_context(self, controller):
        """
        Test that the `create_live_context` method of the controller returns a non-null live context object.
        """
        result = controller.create_live_context()

        assert result is not None

    def test_set_screen_dimensions(self, controller):
        """
        Verify that setting screen dimensions on the controller does not raise any exceptions.
        """
        controller.set_screen_dimensions(120, 40)

        # Should not raise exception


class TestLiveDisplayManager:
    """Test cases for LiveDisplayManager class."""

    def test_init_default(self):
        """
        Test that LiveDisplayManager initializes with default values for console, live context, and current renderable.
        """
        manager = LiveDisplayManager()

        assert manager._console is None
        assert manager._live_context is None
        assert manager._current_renderable is None

    def test_init_with_console(self):
        """
        Test that LiveDisplayManager initializes with a provided console object.
        """
        mock_console = Mock()
        manager = LiveDisplayManager(console=mock_console)

        assert manager._console is mock_console

    @patch("claude_monitor.ui.display_controller.Live")
    def test_create_live_display_default(self, mock_live_class):
        """
        Test that `LiveDisplayManager.create_live_display` creates a live display with default parameters and returns the expected object.
        """
        mock_live = Mock()
        mock_live_class.return_value = mock_live

        manager = LiveDisplayManager()
        result = manager.create_live_display()

        assert result is mock_live
        mock_live_class.assert_called_once_with(
            console=None,
            refresh_per_second=0.75,
            auto_refresh=True,
            vertical_overflow="visible",
        )

    @patch("claude_monitor.ui.display_controller.Live")
    def test_create_live_display_custom(self, mock_live_class):
        """
        Test that LiveDisplayManager creates a live display with custom console, refresh rate, and auto-refresh settings.
        """
        mock_live = Mock()
        mock_live_class.return_value = mock_live
        mock_console = Mock()

        manager = LiveDisplayManager()
        result = manager.create_live_display(
            auto_refresh=False, console=mock_console, refresh_per_second=2.0
        )

        assert result is mock_live
        mock_live_class.assert_called_once_with(
            console=mock_console,
            refresh_per_second=2.0,
            auto_refresh=False,
            vertical_overflow="visible",
        )


class TestScreenBufferManager:
    """Test cases for ScreenBufferManager class."""

    def test_init(self):
        """
        Test that the ScreenBufferManager initializes with the console attribute set to None.
        """
        manager = ScreenBufferManager()

        assert manager.console is None

    @patch("claude_monitor.terminal.themes.get_themed_console")
    @patch("claude_monitor.ui.display_controller.Text")
    @patch("claude_monitor.ui.display_controller.Group")
    def test_create_screen_renderable(self, mock_group, mock_text, mock_get_console):
        """
        Test that ScreenBufferManager creates a screen renderable from a list of string lines.
        
        Verifies that each line is converted to a markup text object and that the resulting group object is returned.
        """
        mock_console = Mock()
        mock_get_console.return_value = mock_console

        mock_text_obj = Mock()
        mock_text.from_markup.return_value = mock_text_obj

        mock_group_obj = Mock()
        mock_group.return_value = mock_group_obj

        manager = ScreenBufferManager()
        screen_buffer = ["Line 1", "Line 2", "Line 3"]

        result = manager.create_screen_renderable(screen_buffer)

        assert result is mock_group_obj
        assert mock_text.from_markup.call_count == 3
        mock_group.assert_called_once()

    @patch("claude_monitor.terminal.themes.get_themed_console")
    @patch("claude_monitor.ui.display_controller.Group")
    def test_create_screen_renderable_with_objects(self, mock_group, mock_get_console):
        """
        Test that ScreenBufferManager creates a screen renderable from a buffer containing both strings and objects.
        
        Verifies that the renderable is constructed using the Group class and that mixed content is handled correctly.
        """
        mock_console = Mock()
        mock_get_console.return_value = mock_console

        mock_group_obj = Mock()
        mock_group.return_value = mock_group_obj

        manager = ScreenBufferManager()
        mock_object = Mock()
        screen_buffer = ["String line", mock_object]

        result = manager.create_screen_renderable(screen_buffer)

        assert result is mock_group_obj
        mock_group.assert_called_once()


class TestDisplayControllerEdgeCases:
    """Test edge cases for DisplayController."""

    @pytest.fixture
    def controller(self):
        """
        Creates and returns a new DisplayController instance with NotificationManager patched for testing purposes.
        
        Returns:
            DisplayController: A new instance of DisplayController with NotificationManager mocked.
        """
        with patch("claude_monitor.ui.display_controller.NotificationManager"):
            return DisplayController()

    @pytest.fixture
    def sample_args(self):
        """
        Provides a mock object representing sample CLI arguments for testing.
        
        Returns:
            args (Mock): A mock object with attributes for plan, timezone, time format, and custom token limit.
        """
        args = Mock()
        args.plan = "pro"
        args.timezone = "UTC"
        args.time_format = "24h"
        args.custom_limit_tokens = None
        return args

    def test_process_active_session_data_exception_handling(
        self, controller, sample_args
    ):
        """
        Tests that `create_data_display` handles exceptions raised during active session data extraction and returns an error screen renderable instead of crashing.
        """
        sample_active_block = {"isActive": True, "totalTokens": 15000, "costUSD": 0.45}

        data = {"blocks": [sample_active_block]}

        # Mock an exception in session data extraction
        with patch.object(controller, "_extract_session_data") as mock_extract:
            mock_extract.side_effect = Exception("Test error")

            result = controller.create_data_display(data, sample_args, 200000)

            # Should return error screen renderable instead of crashing
            assert result is not None

    def test_format_display_times_invalid_timezone(self, controller, sample_args):
        """
        Test that _format_display_times handles an invalid timezone string gracefully and returns formatted time strings for predicted end, reset, and current time.
        """
        sample_args.timezone = "Invalid/Timezone"

        current_time = datetime.now(timezone.utc)
        predicted_end = current_time + timedelta(hours=2)
        reset_time = current_time + timedelta(hours=12)

        # Should handle invalid timezone gracefully
        result = controller._format_display_times(
            sample_args, current_time, predicted_end, reset_time
        )

        assert "predicted_end_str" in result
        assert "reset_time_str" in result
        assert "current_time_str" in result

    def test_calculate_model_distribution_invalid_stats(self, controller):
        """
        Test that model distribution calculation handles invalid stats formats gracefully.
        
        Verifies that the `_calculate_model_distribution` method returns a dictionary and does not raise exceptions when provided with malformed or non-numeric model statistics.
        """
        invalid_stats = {
            "invalid-model": "not-a-dict",
            "another-model": {"inputTokens": "not-a-number"},
        }

        # Should handle invalid data gracefully
        result = controller._calculate_model_distribution(invalid_stats)

        # Should return empty or handle gracefully
        assert isinstance(result, dict)


class TestDisplayControllerAdvanced:
    """Advanced test cases for DisplayController to improve coverage."""

    @pytest.fixture
    def controller(self):
        """
        Creates and returns a new DisplayController instance with NotificationManager patched for testing purposes.
        
        Returns:
            DisplayController: A new instance of DisplayController with NotificationManager mocked.
        """
        with patch("claude_monitor.ui.display_controller.NotificationManager"):
            return DisplayController()

    @pytest.fixture
    def sample_args_custom(self):
        """
        Return a mock CLI arguments object configured for a custom plan.
        
        Returns:
            args (Mock): Mock object with custom plan, UTC timezone, 24-hour time format, and no custom token limit.
        """
        args = Mock()
        args.plan = "custom"
        args.timezone = "UTC"
        args.time_format = "24h"
        args.custom_limit_tokens = None
        return args

    @patch("claude_monitor.ui.display_controller.AdvancedCustomLimitDisplay")
    @patch("claude_monitor.ui.display_controller.Plans.get_message_limit")
    @patch("claude_monitor.core.plans.get_cost_limit")
    def test_create_data_display_custom_plan(
        self,
        mock_get_cost,
        mock_get_message,
        mock_advanced_display,
        controller,
        sample_args_custom,
    ):
        """
        Test that `create_data_display` correctly handles a custom plan by integrating advanced display logic, collecting session data, calculating percentiles, and rendering the appropriate screen output.
        """
        # Mock advanced display
        mock_temp_display = Mock()
        mock_advanced_display.return_value = mock_temp_display
        mock_temp_display._collect_session_data.return_value = {"limit_sessions": []}
        mock_temp_display._calculate_session_percentiles.return_value = {
            "costs": {"p90": 5.0},
            "messages": {"p90": 100},
        }

        # Mock data with active block
        data = {
            "blocks": [
                {
                    "isActive": True,
                    "totalTokens": 15000,
                    "costUSD": 0.45,
                    "sentMessagesCount": 12,
                    "perModelStats": {
                        "claude-3-haiku": {"input_tokens": 100, "output_tokens": 50}
                    },
                    "entries": [{"timestamp": "2024-01-01T12:00:00Z"}],
                    "startTime": "2024-01-01T11:00:00Z",
                    "endTime": "2024-01-01T13:00:00Z",
                }
            ]
        }

        with patch.object(controller, "_process_active_session_data") as mock_process:
            mock_process.return_value = {
                "plan": "custom",
                "timezone": "UTC",
                "tokens_used": 15000,
                "token_limit": 200000,
            }

            with patch.object(
                controller.buffer_manager, "create_screen_renderable"
            ) as mock_create:
                with patch.object(
                    controller.session_display, "format_active_session_screen"
                ) as mock_format:
                    mock_format.return_value = ["screen", "buffer"]
                    mock_create.return_value = "rendered_screen"

                    result = controller.create_data_display(
                        data, sample_args_custom, 200000
                    )

                    assert result == "rendered_screen"
                    mock_advanced_display.assert_called_once_with(None)
                    mock_temp_display._collect_session_data.assert_called_once_with(
                        data["blocks"]
                    )

    def test_create_data_display_exception_handling(self, controller):
        """
        Test that create_data_display returns an error screen renderable when an exception occurs during active session data processing.
        """
        args = Mock()
        args.plan = "pro"
        args.timezone = "UTC"

        data = {"blocks": [{"isActive": True, "totalTokens": 15000, "costUSD": 0.45}]}

        with patch.object(controller, "_process_active_session_data") as mock_process:
            mock_process.side_effect = Exception("Test error")

            with patch.object(
                controller.error_display, "format_error_screen"
            ) as mock_error:
                with patch.object(
                    controller.buffer_manager, "create_screen_renderable"
                ) as mock_create:
                    mock_error.return_value = ["error", "screen"]
                    mock_create.return_value = "error_rendered"

                    result = controller.create_data_display(data, args, 200000)

                    assert result == "error_rendered"
                    mock_error.assert_called_once_with("pro", "UTC")

    def test_create_data_display_format_session_exception(self, controller):
        """
        Test that create_data_display returns an error screen renderable when format_active_session_screen raises an exception.
        """
        args = Mock()
        args.plan = "pro"
        args.timezone = "UTC"

        data = {
            "blocks": [
                {
                    "isActive": True,
                    "totalTokens": 15000,
                    "costUSD": 0.45,
                    "sentMessagesCount": 12,
                    "perModelStats": {"claude-3-haiku": {"input_tokens": 100}},
                    "entries": [{"timestamp": "2024-01-01T12:00:00Z"}],
                    "startTime": "2024-01-01T11:00:00Z",
                    "endTime": "2024-01-01T13:00:00Z",
                }
            ]
        }

        with patch.object(controller, "_process_active_session_data") as mock_process:
            mock_process.return_value = {
                "plan": "pro",
                "timezone": "UTC",
                "tokens_used": 15000,
                "per_model_stats": {"claude-3-haiku": {"input_tokens": 100}},
                "entries": [{"timestamp": "2024-01-01T12:00:00Z"}],
            }

            with patch.object(
                controller.session_display, "format_active_session_screen"
            ) as mock_format:
                mock_format.side_effect = Exception("Format error")

                with patch.object(
                    controller.error_display, "format_error_screen"
                ) as mock_error:
                    with patch.object(
                        controller.buffer_manager, "create_screen_renderable"
                    ) as mock_create:
                        mock_error.return_value = ["error", "screen"]
                        mock_create.return_value = "error_rendered"

                        result = controller.create_data_display(data, args, 200000)

                        assert result == "error_rendered"
                        mock_error.assert_called_once_with("pro", "UTC")

    def test_process_active_session_data_comprehensive(self, controller):
        """
        Tests that `_process_active_session_data` correctly aggregates and returns comprehensive session data, including tokens used, token limits, session cost, burn rate, model distribution, and notification flags, when provided with a fully populated active session block and mocked dependencies.
        """
        active_block = {
            "totalTokens": 15000,
            "costUSD": 0.45,
            "sentMessagesCount": 12,
            "perModelStats": {
                "claude-3-haiku": {"input_tokens": 100, "output_tokens": 50},
                "claude-3-sonnet": {"input_tokens": 200, "output_tokens": 100},
            },
            "entries": [
                {"timestamp": "2024-01-01T12:00:00Z"},
                {"timestamp": "2024-01-01T12:30:00Z"},
            ],
            "startTime": "2024-01-01T11:00:00Z",
            "endTime": "2024-01-01T13:00:00Z",
        }

        data = {"blocks": [active_block]}

        args = Mock()
        args.plan = "pro"
        args.timezone = "UTC"
        args.time_format = "24h"
        args.custom_limit_tokens = None

        current_time = datetime(2024, 1, 1, 12, 30, tzinfo=timezone.utc)

        with patch(
            "claude_monitor.ui.display_controller.calculate_hourly_burn_rate"
        ) as mock_burn:
            mock_burn.return_value = 5.5

            with patch.object(
                controller.session_calculator, "calculate_time_data"
            ) as mock_time:
                mock_time.return_value = {
                    "elapsed_session_minutes": 90,
                    "total_session_minutes": 120,
                    "reset_time": current_time + timedelta(hours=1),
                }

                with patch.object(
                    controller.session_calculator, "calculate_cost_predictions"
                ) as mock_cost:
                    mock_cost.return_value = {
                        "cost_limit": 5.0,
                        "predicted_end_time": current_time + timedelta(hours=2),
                    }

                    with patch.object(
                        controller, "_check_notifications"
                    ) as mock_notify:
                        mock_notify.return_value = {
                            "show_switch_notification": False,
                            "show_exceed_notification": False,
                            "show_cost_will_exceed": False,
                        }

                        with patch.object(
                            controller, "_format_display_times"
                        ) as mock_format:
                            mock_format.return_value = {
                                "predicted_end_str": "14:30",
                                "reset_time_str": "13:30",
                                "current_time_str": "12:30",
                            }

                            result = controller._process_active_session_data(
                                active_block, data, args, 200000, current_time, 5.0
                            )

                            assert result["tokens_used"] == 15000
                            assert result["token_limit"] == 200000
                            assert result["session_cost"] == 0.45
                            assert result["burn_rate"] == 5.5
                            assert "model_distribution" in result
                            assert result["show_switch_notification"] is False


class TestSessionCalculator:
    """Test cases for SessionCalculator class."""

    @pytest.fixture
    def calculator(self):
        """
        Create and return a new SessionCalculator instance.
        """
        return SessionCalculator()

    def test_init(self, calculator):
        """
        Verify that the SessionCalculator initializes with a non-null timezone handler.
        """
        assert calculator.tz_handler is not None

    def test_calculate_time_data_with_start_end(self, calculator):
        """
        Tests that `calculate_time_data` correctly computes start time, reset time, total session minutes, and elapsed session minutes when both start and end times are provided in the session data.
        """
        session_data = {
            "start_time_str": "2024-01-01T11:00:00Z",
            "end_time_str": "2024-01-01T13:00:00Z",
        }
        current_time = datetime(2024, 1, 1, 12, 30, tzinfo=timezone.utc)

        with patch.object(calculator.tz_handler, "parse_timestamp") as mock_parse:
            with patch.object(calculator.tz_handler, "ensure_utc") as mock_ensure:
                start_time = datetime(2024, 1, 1, 11, 0, tzinfo=timezone.utc)
                end_time = datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc)

                mock_parse.side_effect = [start_time, end_time]
                mock_ensure.side_effect = [start_time, end_time]

                result = calculator.calculate_time_data(session_data, current_time)

                assert result["start_time"] == start_time
                assert result["reset_time"] == end_time
                assert result["total_session_minutes"] == 120  # 2 hours
                assert result["elapsed_session_minutes"] == 90  # 1.5 hours

    def test_calculate_time_data_no_end_time(self, calculator):
        """
        Test that calculate_time_data correctly computes reset time as five hours after the start time when no end time is provided in the session data.
        """
        session_data = {"start_time_str": "2024-01-01T11:00:00Z"}
        current_time = datetime(2024, 1, 1, 12, 30, tzinfo=timezone.utc)

        with patch.object(calculator.tz_handler, "parse_timestamp") as mock_parse:
            with patch.object(calculator.tz_handler, "ensure_utc") as mock_ensure:
                start_time = datetime(2024, 1, 1, 11, 0, tzinfo=timezone.utc)

                mock_parse.return_value = start_time
                mock_ensure.return_value = start_time

                result = calculator.calculate_time_data(session_data, current_time)

                assert result["start_time"] == start_time
                # Reset time should be start_time + 5 hours
                expected_reset = start_time + timedelta(hours=5)
                assert result["reset_time"] == expected_reset

    def test_calculate_time_data_no_start_time(self, calculator):
        """
        Verify that calculate_time_data correctly handles missing start time by using the current time as the base and applying default session duration and reset logic.
        """
        session_data = {}
        current_time = datetime(2024, 1, 1, 12, 30, tzinfo=timezone.utc)

        result = calculator.calculate_time_data(session_data, current_time)

        assert result["start_time"] is None
        # Reset time should be current_time + 5 hours
        expected_reset = current_time + timedelta(hours=5)
        assert result["reset_time"] == expected_reset
        assert result["total_session_minutes"] == 300  # 5 hours default
        assert result["elapsed_session_minutes"] >= 0

    def test_calculate_cost_predictions_with_cost(self, calculator):
        """
        Test that calculate_cost_predictions computes cost per minute, remaining cost, and predicted end time when session cost is provided.
        """
        session_data = {"session_cost": 2.5}
        time_data = {"elapsed_session_minutes": 60}
        cost_limit = 10.0

        with patch("claude_monitor.ui.display_controller.datetime") as mock_datetime:
            current_time = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
            mock_datetime.now.return_value = current_time
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            result = calculator.calculate_cost_predictions(
                session_data, time_data, cost_limit
            )

            assert result["cost_per_minute"] == 2.5 / 60  # Approximately 0.0417
            assert result["cost_limit"] == 10.0
            assert result["cost_remaining"] == 7.5
            assert "predicted_end_time" in result

    def test_calculate_cost_predictions_no_cost_limit(self, calculator):
        """
        Test that calculate_cost_predictions uses the default cost limit when none is provided.
        
        Verifies that the method returns a default cost limit, calculates the remaining cost, and includes a predicted end time in the result.
        """
        session_data = {"session_cost": 1.0}
        time_data = {
            "elapsed_session_minutes": 30,
            "reset_time": datetime(2024, 1, 1, 17, 0, tzinfo=timezone.utc),
        }

        with patch("claude_monitor.ui.display_controller.datetime") as mock_datetime:
            current_time = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
            mock_datetime.now.return_value = current_time
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            result = calculator.calculate_cost_predictions(
                session_data, time_data, None
            )

            assert result["cost_limit"] == 100.0  # Default
            assert result["cost_remaining"] == 99.0
            assert "predicted_end_time" in result

    def test_calculate_cost_predictions_zero_cost_rate(self, calculator):
        """
        Test that calculate_cost_predictions returns a zero cost rate and sets predicted end time to the reset time when session cost is zero.
        """
        session_data = {"session_cost": 0.0}
        time_data = {
            "elapsed_session_minutes": 60,
            "reset_time": datetime(2024, 1, 1, 17, 0, tzinfo=timezone.utc),
        }
        cost_limit = 10.0

        with patch("claude_monitor.ui.display_controller.datetime") as mock_datetime:
            current_time = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
            mock_datetime.now.return_value = current_time
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            result = calculator.calculate_cost_predictions(
                session_data, time_data, cost_limit
            )

            assert result["cost_per_minute"] == 0.0
            assert result["predicted_end_time"] == time_data["reset_time"]


# Test the legacy function
@patch("claude_monitor.ui.display_controller.ScreenBufferManager")
def test_create_screen_renderable_legacy(mock_manager_class):
    """
    Test that the legacy create_screen_renderable function delegates to ScreenBufferManager and returns the expected rendered output.
    """
    mock_manager = Mock()
    mock_manager_class.return_value = mock_manager
    mock_manager.create_screen_renderable.return_value = "rendered"

    from claude_monitor.ui.display_controller import create_screen_renderable

    screen_buffer = ["line1", "line2"]
    result = create_screen_renderable(screen_buffer)

    assert result == "rendered"
    mock_manager_class.assert_called_once()
    mock_manager.create_screen_renderable.assert_called_once_with(screen_buffer)
