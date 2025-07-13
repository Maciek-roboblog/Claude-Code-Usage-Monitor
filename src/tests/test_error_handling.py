"""Tests for error handling module."""

from unittest.mock import Mock, patch

import pytest

from claude_monitor.error_handling import SENTRY_AVAILABLE, ErrorLevel, report_error


class TestErrorLevel:
    """Test cases for ErrorLevel enum."""

    def test_error_level_values(self):
        """Test that ErrorLevel has correct values."""
        assert ErrorLevel.INFO == "info"
        assert ErrorLevel.ERROR == "error"

    def test_error_level_string_conversion(self):
        """Test ErrorLevel string conversion."""
        assert ErrorLevel.INFO.value == "info"
        assert ErrorLevel.ERROR.value == "error"


class TestReportError:
    """Test cases for report_error function."""

    @pytest.fixture
    def sample_exception(self):
        """Create a sample exception for testing."""
        try:
            raise ValueError("Test error message")
        except ValueError as e:
            return e

    @pytest.fixture
    def sample_context_data(self):
        """Sample context data for testing."""
        return {
            "user_id": "12345",
            "action": "process_data",
            "timestamp": "2024-01-01T12:00:00Z",
        }

    @pytest.fixture
    def sample_tags(self):
        """Sample tags for testing."""
        return {"environment": "test", "version": "1.0.0"}

    @patch("claude_monitor.error_handling.SENTRY_AVAILABLE", True)
    @patch("claude_monitor.error_handling.sentry_sdk")
    def test_report_error_with_sentry_basic(self, mock_sentry, sample_exception):
        """Test basic error reporting when Sentry is available."""
        mock_scope = Mock()
        mock_sentry.configure_scope.return_value.__enter__ = Mock(
            return_value=mock_scope
        )
        mock_sentry.configure_scope.return_value.__exit__ = Mock(return_value=None)

        report_error(exception=sample_exception, component="test_component")

        # Verify Sentry was called
        mock_sentry.configure_scope.assert_called_once()
        mock_scope.set_tag.assert_called_with("component", "test_component")
        mock_sentry.capture_exception.assert_called_once_with(sample_exception)

    @patch("claude_monitor.error_handling.SENTRY_AVAILABLE", True)
    @patch("claude_monitor.error_handling.sentry_sdk")
    def test_report_error_with_sentry_full_context(
        self, mock_sentry, sample_exception, sample_context_data, sample_tags
    ):
        """Test error reporting with full context when Sentry is available."""
        mock_scope = Mock()
        mock_sentry.configure_scope.return_value.__enter__ = Mock(
            return_value=mock_scope
        )
        mock_sentry.configure_scope.return_value.__exit__ = Mock(return_value=None)

        report_error(
            exception=sample_exception,
            component="test_component",
            context_name="test_context",
            context_data=sample_context_data,
            tags=sample_tags,
            level=ErrorLevel.ERROR,
        )

        # Verify Sentry configuration
        mock_sentry.configure_scope.assert_called_once()

        # Check that set_tag was called for component and custom tags
        assert mock_scope.set_tag.call_count == 3

        # Verify all expected tags were set
        call_args = [call[0] for call in mock_scope.set_tag.call_args_list]
        expected_tags = [
            ("component", "test_component"),
            ("environment", "test"),
            ("version", "1.0.0"),
        ]

        for expected_tag in expected_tags:
            assert expected_tag in call_args

        # Verify context was set
        mock_scope.set_context.assert_called_once_with(
            "test_context", sample_context_data
        )

        # Verify exception was captured with correct level
        mock_sentry.capture_exception.assert_called_once_with(sample_exception)

    @patch("claude_monitor.error_handling.SENTRY_AVAILABLE", True)
    @patch("claude_monitor.error_handling.sentry_sdk")
    def test_report_error_with_info_level(self, mock_sentry, sample_exception):
        """Test error reporting with INFO level."""
        mock_scope = Mock()
        mock_sentry.configure_scope.return_value.__enter__ = Mock(
            return_value=mock_scope
        )
        mock_sentry.configure_scope.return_value.__exit__ = Mock(return_value=None)

        report_error(
            exception=sample_exception,
            component="test_component",
            level=ErrorLevel.INFO,
        )

        # Verify Sentry was called
        mock_sentry.configure_scope.assert_called_once()
        mock_sentry.capture_exception.assert_called_once_with(sample_exception)

    @patch("claude_monitor.error_handling.SENTRY_AVAILABLE", False)
    @patch("claude_monitor.error_handling.logging.getLogger")
    def test_report_error_without_sentry(self, mock_get_logger, sample_exception):
        """Test error reporting when Sentry is not available."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        report_error(exception=sample_exception, component="test_component")

        # Verify logger was created for component
        mock_get_logger.assert_called_once_with("test_component")

        # Verify logging was called
        mock_logger.error.assert_called_once()

    @patch("claude_monitor.error_handling.SENTRY_AVAILABLE", False)
    @patch("claude_monitor.error_handling.logging.getLogger")
    def test_report_error_without_sentry_with_context(
        self, mock_get_logger, sample_exception, sample_context_data
    ):
        """Test error reporting without Sentry but with context data."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        report_error(
            exception=sample_exception,
            component="test_component",
            context_name="test_context",
            context_data=sample_context_data,
        )

        # Verify logger was created and used
        mock_get_logger.assert_called_once_with("test_component")
        mock_logger.error.assert_called_once()

    @patch("claude_monitor.error_handling.SENTRY_AVAILABLE", True)
    @patch("claude_monitor.error_handling.sentry_sdk")
    def test_report_error_sentry_exception_handling(
        self, mock_sentry, sample_exception
    ):
        """Test that Sentry exceptions are handled gracefully."""
        # Make Sentry raise an exception
        mock_sentry.configure_scope.side_effect = Exception("Sentry failed")

        # Should not raise exception
        with patch(
            "claude_monitor.error_handling.logging.getLogger"
        ) as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            report_error(exception=sample_exception, component="test_component")

            # Should still log the error
            mock_logger.error.assert_called()

    def test_report_error_none_exception(self):
        """Test error reporting with None exception."""
        # Should handle gracefully without crashing
        with patch(
            "claude_monitor.error_handling.logging.getLogger"
        ) as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            report_error(exception=None, component="test_component")

            # Should still log something
            mock_logger.error.assert_called()

    def test_report_error_empty_component(self, sample_exception):
        """Test error reporting with empty component name."""
        with patch(
            "claude_monitor.error_handling.logging.getLogger"
        ) as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            report_error(exception=sample_exception, component="")

            # Should still work
            mock_logger.error.assert_called()

    @patch("claude_monitor.error_handling.SENTRY_AVAILABLE", True)
    @patch("claude_monitor.error_handling.sentry_sdk")
    def test_report_error_no_tags(self, mock_sentry, sample_exception):
        """Test error reporting with no additional tags."""
        mock_scope = Mock()
        mock_sentry.configure_scope.return_value.__enter__ = Mock(
            return_value=mock_scope
        )
        mock_sentry.configure_scope.return_value.__exit__ = Mock(return_value=None)

        report_error(exception=sample_exception, component="test_component", tags=None)

        # Should only set component tag
        mock_scope.set_tag.assert_called_once_with("component", "test_component")

    @patch("claude_monitor.error_handling.SENTRY_AVAILABLE", True)
    @patch("claude_monitor.error_handling.sentry_sdk")
    def test_report_error_no_context(self, mock_sentry, sample_exception):
        """Test error reporting with no context data."""
        mock_scope = Mock()
        mock_sentry.configure_scope.return_value.__enter__ = Mock(
            return_value=mock_scope
        )
        mock_sentry.configure_scope.return_value.__exit__ = Mock(return_value=None)

        report_error(
            exception=sample_exception,
            component="test_component",
            context_name="test_context",
            context_data=None,
        )

        # Should not set context if data is None
        mock_scope.set_context.assert_not_called()

    @patch("claude_monitor.error_handling.SENTRY_AVAILABLE", True)
    @patch("claude_monitor.error_handling.sentry_sdk")
    def test_report_error_complex_exception(self, mock_sentry):
        """Test error reporting with complex exception."""
        mock_scope = Mock()
        mock_sentry.configure_scope.return_value.__enter__ = Mock(
            return_value=mock_scope
        )
        mock_sentry.configure_scope.return_value.__exit__ = Mock(return_value=None)

        # Create a complex exception with cause
        try:
            try:
                raise ValueError("Inner exception")
            except ValueError as inner:
                raise RuntimeError("Outer exception") from inner
        except RuntimeError as complex_exception:
            report_error(exception=complex_exception, component="test_component")

        # Should handle complex exceptions properly
        mock_sentry.capture_exception.assert_called_once()

    def test_sentry_availability_flag(self):
        """Test that SENTRY_AVAILABLE is a boolean."""
        assert isinstance(SENTRY_AVAILABLE, bool)

    @patch("claude_monitor.error_handling.SENTRY_AVAILABLE", True)
    @patch("claude_monitor.error_handling.sentry_sdk")
    def test_report_error_empty_tags_dict(self, mock_sentry, sample_exception):
        """Test error reporting with empty tags dictionary."""
        mock_scope = Mock()
        mock_sentry.configure_scope.return_value.__enter__ = Mock(
            return_value=mock_scope
        )
        mock_sentry.configure_scope.return_value.__exit__ = Mock(return_value=None)

        report_error(
            exception=sample_exception,
            component="test_component",
            tags={},  # Empty dict
        )

        # Should only set component tag
        mock_scope.set_tag.assert_called_once_with("component", "test_component")

    @patch("claude_monitor.error_handling.SENTRY_AVAILABLE", True)
    @patch("claude_monitor.error_handling.sentry_sdk")
    def test_report_error_special_characters_in_component(
        self, mock_sentry, sample_exception
    ):
        """Test error reporting with special characters in component name."""
        mock_scope = Mock()
        mock_sentry.configure_scope.return_value.__enter__ = Mock(
            return_value=mock_scope
        )
        mock_sentry.configure_scope.return_value.__exit__ = Mock(return_value=None)

        special_component = "test-component_with.special@chars"

        report_error(exception=sample_exception, component=special_component)

        # Should handle special characters in component name
        mock_scope.set_tag.assert_called_once_with("component", special_component)
        mock_sentry.capture_exception.assert_called_once()


class TestErrorHandlingEdgeCases:
    """Test edge cases for error handling module."""

    def test_error_level_equality(self):
        """Test ErrorLevel equality comparisons."""
        assert ErrorLevel.INFO == "info"
        assert ErrorLevel.ERROR == "error"
        assert ErrorLevel.INFO != ErrorLevel.ERROR

    def test_error_level_in_list(self):
        """Test ErrorLevel can be used in lists and comparisons."""
        levels = [ErrorLevel.INFO, ErrorLevel.ERROR]
        assert ErrorLevel.INFO in levels
        # Note: Since ErrorLevel(str, Enum), string values are equal to enum values
        assert "info" in levels  # String IS the same as enum for this type

    @patch("claude_monitor.error_handling.SENTRY_AVAILABLE", True)
    @patch("claude_monitor.error_handling.sentry_sdk")
    def test_report_error_with_unicode_data(self, mock_sentry):
        """Test error reporting with unicode data."""
        mock_scope = Mock()
        mock_sentry.configure_scope.return_value.__enter__ = Mock(
            return_value=mock_scope
        )
        mock_sentry.configure_scope.return_value.__exit__ = Mock(return_value=None)

        unicode_exception = ValueError("Test with unicode: 测试 🚀 émojis")
        unicode_context = {"message": "测试消息", "emoji": "🎉", "accents": "café"}

        report_error(
            exception=unicode_exception,
            component="test_component",
            context_name="unicode_test",
            context_data=unicode_context,
        )

        # Should handle unicode data properly
        mock_sentry.capture_exception.assert_called_once_with(unicode_exception)
        mock_scope.set_context.assert_called_once_with("unicode_test", unicode_context)
