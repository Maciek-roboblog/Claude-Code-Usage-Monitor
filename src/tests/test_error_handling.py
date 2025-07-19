"""Tests for error handling module."""

from typing import Dict
from unittest.mock import Mock, patch

import pytest

from claude_monitor.error_handling import ErrorLevel, report_error


class TestErrorLevel:
    """Test cases for ErrorLevel enum."""

    def test_error_level_values(self) -> None:
        """Test that ErrorLevel has correct values."""
        assert ErrorLevel.INFO == "info"
        assert ErrorLevel.ERROR == "error"

    def test_error_level_string_conversion(self) -> None:
        """Test ErrorLevel string conversion."""
        assert ErrorLevel.INFO.value == "info"
        assert ErrorLevel.ERROR.value == "error"


class TestReportError:
    """Test cases for report_error function."""

    @pytest.fixture
    def sample_exception(self) -> ValueError:
        """Create a sample exception for testing."""
        try:
            raise ValueError("Test error message")
        except ValueError as e:
            return e

    @pytest.fixture
    def sample_context_data(self) -> Dict[str, str]:
        """Sample context data for testing."""
        return {
            "user_id": "12345",
            "action": "process_data",
            "timestamp": "2024-01-01T12:00:00Z",
        }

    @pytest.fixture
    def sample_tags(self) -> Dict[str, str]:
        """Sample tags for testing."""
        return {"environment": "test", "version": "1.0.0"}

    @patch("claude_monitor.error_handling.logging.getLogger")
    def test_report_error_basic(
        self, mock_get_logger: Mock, sample_exception: ValueError
    ) -> None:
        """Test basic error reporting."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        report_error(exception=sample_exception, component="test_component")

        # Verify logger was called
        mock_get_logger.assert_called_once_with("test_component")
        mock_logger.error.assert_called_once()

    @patch("claude_monitor.error_handling.logging.getLogger")
    def test_report_error_with_full_context(
        self,
        mock_get_logger: Mock,
        sample_exception: ValueError,
        sample_context_data: Dict[str, str],
        sample_tags: Dict[str, str],
    ) -> None:
        """Test error reporting with full context."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        report_error(
            exception=sample_exception,
            component="test_component",
            context_name="test_context",
            context_data=sample_context_data,
            tags=sample_tags,
            level=ErrorLevel.ERROR,
        )

        # Verify logger configuration
        mock_get_logger.assert_called_once_with("test_component")
        mock_logger.error.assert_called_once()

        # Verify the extra data was passed correctly
        call_args = mock_logger.error.call_args
        assert call_args[1]["extra"]["context"] == "test_context"
        assert call_args[1]["extra"]["data"] == sample_context_data
        assert call_args[1]["extra"]["tags"] == sample_tags

    @patch("claude_monitor.error_handling.logging.getLogger")
    def test_report_error_with_info_level(
        self, mock_get_logger: Mock, sample_exception: ValueError
    ) -> None:
        """Test error reporting with INFO level."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        report_error(
            exception=sample_exception,
            component="test_component",
            level=ErrorLevel.INFO,
        )

        # Verify logger was called with info level
        mock_get_logger.assert_called_once_with("test_component")
        mock_logger.info.assert_called_once()

    @patch("claude_monitor.error_handling.logging.getLogger")
    def test_report_error_logging_only(
        self, mock_get_logger: Mock, sample_exception: ValueError
    ) -> None:
        """Test error reporting with logging only."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        report_error(exception=sample_exception, component="test_component")

        # Verify logger was created for component
        mock_get_logger.assert_called_once_with("test_component")

        # Verify logging was called
        mock_logger.error.assert_called_once()

    @patch("claude_monitor.error_handling.logging.getLogger")
    def test_report_error_with_context(
        self,
        mock_get_logger: Mock,
        sample_exception: ValueError,
        sample_context_data: Dict[str, str],
    ) -> None:
        """Test error reporting with context data."""
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

    @patch("claude_monitor.error_handling.logging.getLogger")
    def test_report_error_exception_handling(
        self, mock_get_logger: Mock, sample_exception: ValueError
    ) -> None:
        """Test that logging exceptions are handled gracefully."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        # Make logger raise an exception
        mock_logger.error.side_effect = Exception("Logging failed")

        # Should not raise exception
        try:
            report_error(exception=sample_exception, component="test_component")
        except Exception:
            pytest.fail("report_error should handle logging exceptions gracefully")

    def test_report_error_none_exception(self) -> None:
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

    def test_report_error_empty_component(self, sample_exception: ValueError) -> None:
        """Test error reporting with empty component name."""
        with patch(
            "claude_monitor.error_handling.logging.getLogger"
        ) as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            report_error(exception=sample_exception, component="")

            # Should still work
            mock_logger.error.assert_called()

    @patch("claude_monitor.error_handling.logging.getLogger")
    def test_report_error_no_tags(
        self, mock_get_logger: Mock, sample_exception: ValueError
    ) -> None:
        """Test error reporting with no additional tags."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        report_error(exception=sample_exception, component="test_component", tags=None)

        # Should still log the error
        mock_get_logger.assert_called_once_with("test_component")
        mock_logger.error.assert_called_once()

    @patch("claude_monitor.error_handling.logging.getLogger")
    def test_report_error_no_context(
        self, mock_get_logger: Mock, sample_exception: ValueError
    ) -> None:
        """Test error reporting with no context data."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        report_error(
            exception=sample_exception,
            component="test_component",
            context_name="test_context",
            context_data=None,
        )

        # Should still log the error
        mock_get_logger.assert_called_once_with("test_component")
        mock_logger.error.assert_called_once()

    @patch("claude_monitor.error_handling.logging.getLogger")
    def test_report_error_complex_exception(self, mock_get_logger: Mock) -> None:
        """Test error reporting with complex exception."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        # Create a complex exception with cause
        try:
            try:
                raise ValueError("Inner exception")
            except ValueError as inner:
                raise RuntimeError("Outer exception") from inner
        except RuntimeError as complex_exception:
            report_error(exception=complex_exception, component="test_component")

        # Should handle complex exceptions properly
        mock_get_logger.assert_called_once_with("test_component")
        mock_logger.error.assert_called_once()

    @patch("claude_monitor.error_handling.logging.getLogger")
    def test_report_error_empty_tags_dict(
        self, mock_get_logger: Mock, sample_exception: ValueError
    ) -> None:
        """Test error reporting with empty tags dictionary."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        report_error(
            exception=sample_exception,
            component="test_component",
            tags={},  # Empty dict
        )

        # Should still log the error
        mock_get_logger.assert_called_once_with("test_component")
        mock_logger.error.assert_called_once()

    @patch("claude_monitor.error_handling.logging.getLogger")
    def test_report_error_special_characters_in_component(
        self, mock_get_logger: Mock, sample_exception: ValueError
    ) -> None:
        """Test error reporting with special characters in component name."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        special_component = "test-component_with.special@chars"

        report_error(exception=sample_exception, component=special_component)

        # Should handle special characters in component name
        mock_get_logger.assert_called_once_with(special_component)
        mock_logger.error.assert_called_once()


class TestErrorHandlingEdgeCases:
    """Test edge cases for error handling module."""

    def test_error_level_equality(self) -> None:
        """Test ErrorLevel equality comparisons."""
        assert ErrorLevel.INFO == "info"
        assert ErrorLevel.ERROR == "error"
        assert ErrorLevel.INFO != ErrorLevel.ERROR

    def test_error_level_in_list(self) -> None:
        """Test ErrorLevel can be used in lists and comparisons."""
        levels = [ErrorLevel.INFO, ErrorLevel.ERROR]
        assert ErrorLevel.INFO in levels
        # Note: Since ErrorLevel(str, Enum), string values are equal to enum values
        assert "info" in levels  # String IS the same as enum for this type

    @patch("claude_monitor.error_handling.logging.getLogger")
    def test_report_error_with_unicode_data(self, mock_get_logger: Mock) -> None:
        """Test error reporting with unicode data."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        unicode_exception = ValueError("Test with unicode: 测试 🚀 émojis")
        unicode_context = {"message": "测试消息", "emoji": "🎉", "accents": "café"}

        report_error(
            exception=unicode_exception,
            component="test_component",
            context_name="unicode_test",
            context_data=unicode_context,
        )

        # Should handle unicode data properly
        mock_get_logger.assert_called_once_with("test_component")
        mock_logger.error.assert_called_once()
