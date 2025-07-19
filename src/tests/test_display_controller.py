"""Tests for DisplayController class."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict
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
    def controller(self) -> Any:
        with patch("claude_monitor.ui.display_controller.NotificationManager"):
            return DisplayController()

    @pytest.fixture
    def sample_active_block(self) -> Dict[str, Any]:
        """Sample active block data."""
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
    def sample_args(self) -> Mock:
        """Sample CLI arguments."""
        args = Mock()
        args.plan = "pro"
        args.timezone = "UTC"
        args.time_format = "24h"
        args.custom_limit_tokens = None
        return args

    def test_init(self, controller: Any) -> None:
        """Test DisplayController initialization."""
        assert controller.session_display is not None
        assert controller.loading_screen is not None
        assert controller.error_display is not None
        assert controller.screen_manager is not None
        assert controller.live_manager is not None
        assert controller.notification_manager is not None

    def test_extract_session_data(
        self, controller: Any, sample_active_block: Dict[str, Any]
    ) -> None:
        """Test session data extraction."""
        result = controller._extract_session_data(sample_active_block)

        assert result["tokens_used"] == 15000
        assert result["session_cost"] == 0.45
        assert result["sent_messages"] == 12
        assert len(result["entries"]) == 2
        assert result["start_time_str"] == "2024-01-01T11:00:00Z"

    def test_calculate_token_limits_standard_plan(self, controller, sample_args):
        """Test token limit calculation for standard plans."""
        token_limit = 200000

        result = controller._calculate_token_limits(sample_args, token_limit)

        assert result == (200000, 200000)

    def test_calculate_token_limits_custom_plan(self, controller, sample_args):
        """Test token limit calculation for custom plans with explicit limit."""
        sample_args.plan = "custom"
        sample_args.custom_limit_tokens = 500000
        token_limit = 200000

        result = controller._calculate_token_limits(sample_args, token_limit)

        assert result == (500000, 500000)

    def test_calculate_token_limits_custom_plan_no_limit(self, controller, sample_args):
        """Test token limit calculation for custom plans without explicit limit."""
        sample_args.plan = "custom"
        sample_args.custom_limit_tokens = None
        token_limit = 200000

        result = controller._calculate_token_limits(sample_args, token_limit)

        assert result == (200000, 200000)

    @patch("claude_monitor.ui.display_controller.calculate_hourly_burn_rate")
    def test_calculate_time_data(self, mock_burn_rate, controller):
        """Test time data calculation."""
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
        """Test cost predictions for valid plans."""
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
        """Test cost predictions for invalid plans."""
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
        """Test notification checking for switch to custom."""
        with (
            patch.object(
                controller.notification_manager, "should_notify"
            ) as mock_should,
            patch.object(controller.notification_manager, "mark_notified") as mock_mark,
            patch.object(
                controller.notification_manager, "is_notification_active"
            ) as mock_active,
        ):
            # Configure should_notify to return True only for switch_to_custom
            def should_notify_side_effect(notification_type):
                return notification_type == "switch_to_custom"

            mock_should.side_effect = should_notify_side_effect
            mock_active.return_value = False

            result = controller._check_notifications(
                token_limit=500000,
                original_limit=200000,
                session_cost=2.0,
                cost_limit=5.0,
                predicted_end_time=datetime.now(timezone.utc) + timedelta(hours=2),
                reset_time=datetime.now(timezone.utc) + timedelta(hours=12),
            )

            assert result["show_switch_notification"] is True
            # Verify switch_to_custom was called
            assert any(
                call[0][0] == "switch_to_custom" for call in mock_should.call_args_list
            )
            mock_mark.assert_called_with("switch_to_custom")

    def test_check_notifications_exceed_limit(self, controller):
        """Test notification checking for exceeding limit."""
        with (
            patch.object(
                controller.notification_manager, "should_notify"
            ) as mock_should,
            patch.object(controller.notification_manager, "mark_notified") as mock_mark,
            patch.object(
                controller.notification_manager, "is_notification_active"
            ) as mock_active,
        ):
            # Configure should_notify to return True only for exceed_max_limit
            def should_notify_side_effect(notification_type):
                return notification_type == "exceed_max_limit"

            mock_should.side_effect = should_notify_side_effect
            mock_active.return_value = False

            result = controller._check_notifications(
                token_limit=200000,
                original_limit=200000,
                session_cost=6.0,  # Exceeds limit
                cost_limit=5.0,
                predicted_end_time=datetime.now(timezone.utc) + timedelta(hours=2),
                reset_time=datetime.now(timezone.utc) + timedelta(hours=12),
            )

            assert result["show_exceed_notification"] is True
            # Verify exceed_max_limit was called
            assert any(
                call[0][0] == "exceed_max_limit" for call in mock_should.call_args_list
            )
            mock_mark.assert_called_with("exceed_max_limit")

    def test_check_notifications_cost_will_exceed(self, controller):
        """Test notification checking for cost will exceed."""
        with (
            patch.object(
                controller.notification_manager, "should_notify"
            ) as mock_should,
            patch.object(controller.notification_manager, "mark_notified") as mock_mark,
        ):
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
        """Test display time formatting."""
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
        """Test model distribution calculation with empty stats."""
        result = controller._calculate_model_distribution({})
        assert result == {}

    @patch("claude_monitor.ui.display_controller.normalize_model_name")
    def test_calculate_model_distribution_valid_stats(self, mock_normalize, controller):
        """Test model distribution calculation with valid stats."""
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
        """Test create_data_display with no data."""
        result = controller.create_data_display({}, sample_args, 200000)

        assert result is not None
        # Should return error screen renderable

    def test_create_data_display_no_active_block(self, controller, sample_args):
        """Test create_data_display with no active blocks."""
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
        """Test create_data_display with active block."""
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
        """Test creating loading display."""
        result = controller.create_loading_display("pro", "UTC", "Loading...")

        assert result is not None

    def test_create_error_display(self, controller):
        """Test creating error display."""
        result = controller.create_error_display("pro", "UTC")

        assert result is not None

    def test_create_live_context(self, controller):
        """Test creating live context."""
        result = controller.create_live_context()

        assert result is not None

    def test_set_screen_dimensions(self, controller):
        """Test setting screen dimensions."""
        controller.set_screen_dimensions(120, 40)

        # Should not raise exception


class TestLiveDisplayManager:
    """Test cases for LiveDisplayManager class."""

    def test_init_default(self):
        """Test LiveDisplayManager initialization with defaults."""
        manager = LiveDisplayManager()

        assert manager._console is None
        assert manager._live_context is None
        assert manager._current_renderable is None

    def test_init_with_console(self):
        """Test LiveDisplayManager initialization with console."""
        mock_console = Mock()
        manager = LiveDisplayManager(console=mock_console)

        assert manager._console is mock_console

    @patch("claude_monitor.ui.display_controller.Live")
    def test_create_live_display_default(self, mock_live_class):
        """Test creating live display with defaults."""
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
        """Test creating live display with custom parameters."""
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
        """Test ScreenBufferManager initialization."""
        manager = ScreenBufferManager()

        assert manager.console is None

    @patch("claude_monitor.terminal.themes.get_themed_console")
    @patch("claude_monitor.ui.display_controller.Text")
    @patch("claude_monitor.ui.display_controller.Group")
    def test_create_screen_renderable(self, mock_group, mock_text, mock_get_console):
        """Test creating screen renderable from buffer."""
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
        """Test creating screen renderable with mixed string and object content."""
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
        """Create a DisplayController instance."""
        with patch("claude_monitor.ui.display_controller.NotificationManager"):
            return DisplayController()

    @pytest.fixture
    def sample_args(self):
        """Sample CLI arguments."""
        args = Mock()
        args.plan = "pro"
        args.timezone = "UTC"
        args.time_format = "24h"
        args.custom_limit_tokens = None
        return args

    def test_process_active_session_data_exception_handling(
        self, controller, sample_args
    ):
        """Test exception handling in _process_active_session_data."""
        sample_active_block = {"isActive": True, "totalTokens": 15000, "costUSD": 0.45}

        data = {"blocks": [sample_active_block]}

        # Mock an exception in session data extraction
        with patch.object(controller, "_extract_session_data") as mock_extract:
            mock_extract.side_effect = Exception("Test error")

            result = controller.create_data_display(data, sample_args, 200000)

            # Should return error screen renderable instead of crashing
            assert result is not None

    def test_format_display_times_invalid_timezone(self, controller, sample_args):
        """Test format_display_times with invalid timezone."""
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
        """Test model distribution with invalid stats format."""
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
        """Create a DisplayController instance."""
        with patch("claude_monitor.ui.display_controller.NotificationManager"):
            return DisplayController()

    @pytest.fixture
    def sample_args_custom(self):
        """Sample CLI arguments for custom plan."""
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
        """Test create_data_display with custom plan."""
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

            with (
                patch.object(
                    controller.buffer_manager, "create_screen_renderable"
                ) as mock_create,
                patch.object(
                    controller.session_display, "format_active_session_screen"
                ) as mock_format,
            ):
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
        """Test create_data_display exception handling."""
        args = Mock()
        args.plan = "pro"
        args.timezone = "UTC"

        data = {"blocks": [{"isActive": True, "totalTokens": 15000, "costUSD": 0.45}]}

        with patch.object(controller, "_process_active_session_data") as mock_process:
            mock_process.side_effect = Exception("Test error")

            with (
                patch.object(
                    controller.error_display, "format_error_screen"
                ) as mock_error,
                patch.object(
                    controller.buffer_manager, "create_screen_renderable"
                ) as mock_create,
            ):
                mock_error.return_value = ["error", "screen"]
                mock_create.return_value = "error_rendered"

                result = controller.create_data_display(data, args, 200000)

                assert result == "error_rendered"
                mock_error.assert_called_once_with("pro", "UTC")

    def test_create_data_display_format_session_exception(self, controller):
        """Test create_data_display with format_active_session_screen exception."""
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

                with (
                    patch.object(
                        controller.error_display, "format_error_screen"
                    ) as mock_error,
                    patch.object(
                        controller.buffer_manager, "create_screen_renderable"
                    ) as mock_create,
                ):
                    mock_error.return_value = ["error", "screen"]
                    mock_create.return_value = "error_rendered"

                    result = controller.create_data_display(data, args, 200000)

                    assert result == "error_rendered"
                    mock_error.assert_called_once_with("pro", "UTC")

    def test_process_active_session_data_comprehensive(self, controller):
        """Test _process_active_session_data with comprehensive data."""
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
        """Create a SessionCalculator instance."""
        return SessionCalculator()

    def test_init(self, calculator):
        """Test SessionCalculator initialization."""
        assert calculator.tz_handler is not None

    def test_calculate_time_data_with_start_end(self, calculator):
        """Test calculate_time_data with start and end times."""
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
        """Test calculate_time_data without end time."""
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
        """Test calculate_time_data without start time."""
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
        """Test calculate_cost_predictions with existing cost."""
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
        """Test calculate_cost_predictions without cost limit."""
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
        """Test calculate_cost_predictions with zero cost rate."""
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
    """Test the legacy create_screen_renderable function."""
    mock_manager = Mock()
    mock_manager_class.return_value = mock_manager
    mock_manager.create_screen_renderable.return_value = "rendered"

    from claude_monitor.ui.display_controller import create_screen_renderable

    screen_buffer = ["line1", "line2"]
    result = create_screen_renderable(screen_buffer)

    assert result == "rendered"
    mock_manager_class.assert_called_once()
    mock_manager.create_screen_renderable.assert_called_once_with(screen_buffer)
