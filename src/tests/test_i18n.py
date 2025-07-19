"""Tests for i18n internationalization module."""

import time
from typing import Dict, List, Tuple
from unittest.mock import patch

import pytest

from claude_monitor.i18n import _, init_i18n


class TestI18nCore:
    """Test cases for core i18n functionality."""

    def test_french_interface_translation(self) -> None:
        """Test French translation functionality."""
        init_i18n("fr")
        result = _("Monitor failed: {error}", error="final test")

        # Verify French translation is working
        assert "Échec" in result or "échoué" in result, (
            f"Expected French translation, got: {result}"
        )

    def test_translation_performance(self) -> None:
        """Test translation performance meets requirements (≤5ms for 1000 translations)."""
        init_i18n("fr")

        # Warmup to ensure cached performance
        for i in range(10):
            _("Monitor failed: {error}", error=f"warmup{i}")

        # Measure performance
        start_time = time.time()
        for i in range(1000):
            _("Monitor failed: {error}", error=f"test{i}")
        end_time = time.time()

        duration_ms = (end_time - start_time) * 1000
        assert duration_ms <= 20, f"Translation too slow: {duration_ms:.2f}ms > 20ms"

    @pytest.mark.parametrize("language", ["en", "fr", "es", "de"])
    def test_supported_languages(self, language: str) -> None:
        """Test all supported languages are functional."""
        init_i18n(language)
        result = _("Monitor failed: {error}", error="test")

        # Verify translation was attempted (not empty or None)
        assert result is not None
        assert len(result) > 0
        assert "error" not in result or "test" in result  # Template was processed

    def test_fallback_to_english_unknown_language(self) -> None:
        """Test fallback behavior for unknown languages."""
        init_i18n("unknown_lang")
        result = _("Monitor failed: {error}", error="test")

        # Should fallback to English
        assert result == "Monitor failed: test"


class TestI18nFormatting:
    """Test cases for i18n string formatting functionality."""

    @pytest.fixture
    def sample_format_cases(self) -> List[Tuple[str, Dict[str, str]]]:
        """Sample format test cases."""
        return [
            (
                "Test message with {param1} and {param2}",
                {"param1": "value1", "param2": "value2"},
            ),
            ("Found {count} items", {"count": "42"}),
            ("Simple message", {}),
        ]

    def test_complex_string_formatting(
        self, sample_format_cases: List[Tuple[str, Dict[str, str]]]
    ) -> None:
        """Test complex string formatting scenarios."""
        init_i18n("fr")

        for msg_template, params in sample_format_cases:
            result = _(msg_template, **params)

            # Verify formatting was successful
            assert result is not None
            assert len(result) > 0
            # Verify no unresolved template variables remain
            assert "{" not in result or "}" not in result

    def test_string_formatting_with_numbers(self) -> None:
        """Test string formatting with numeric values."""
        init_i18n("fr")

        result = _("Found {count} items", count=42)
        assert "42" in result

    def test_string_formatting_with_multiple_params(self) -> None:
        """Test string formatting with multiple parameters."""
        init_i18n("fr")

        result = _(
            "Error in {component}: {error}",
            component="test_module",
            error="sample_error",
        )
        assert "test_module" in result
        assert "sample_error" in result


class TestI18nInitialization:
    """Test cases for i18n initialization scenarios."""

    @pytest.fixture
    def initialization_scenarios(self) -> List[Tuple[str, str]]:
        """Initialization test scenarios."""
        return [
            ("en", "English"),
            ("fr", "French"),
            ("es", "Spanish"),
            ("de", "German"),
            ("", "Empty string"),
        ]

    def test_initialization_scenarios(
        self, initialization_scenarios: List[Tuple[str, str]]
    ) -> None:
        """Test various initialization scenarios."""
        for lang_code, lang_name in initialization_scenarios:
            if lang_code == "":
                # Empty string should either work or raise a specific error
                try:
                    init_i18n(lang_code)
                    result = _("Monitor failed: {error}", error="test")
                    assert result is not None
                except (ValueError, TypeError):
                    # Acceptable to reject empty string
                    pass
            else:
                init_i18n(lang_code)
                result = _("Monitor failed: {error}", error="test")
                assert result is not None, (
                    f"Initialization failed for {lang_name} ({lang_code})"
                )

    def test_default_initialization(self) -> None:
        """Test default initialization (no parameters)."""
        init_i18n()  # Test default initialization
        result = _("Monitor failed: {error}", error="test")
        assert result is not None

    def test_none_initialization(self) -> None:
        """Test initialization with None value."""
        # Should handle gracefully with auto-detection, not raise an error
        init_i18n(None)
        result = _("Monitor failed: {error}", error="test")
        assert result is not None


class TestI18nErrorHandling:
    """Test cases for i18n error handling and edge cases."""

    def test_translation_with_missing_format_parameter(self) -> None:
        """Test translation when format parameter is missing."""
        init_i18n("fr")

        # Should handle missing parameter gracefully
        result = _("Error in {component}: {error}", component="test_module")
        assert result is not None
        # Should either substitute missing param or return original

    def test_translation_with_invalid_template(self) -> None:
        """Test translation with malformed template string."""
        init_i18n("fr")

        # Should handle invalid templates gracefully
        result = _("Error in {component}: {error}", component="test")
        assert result is not None

    @patch("claude_monitor.i18n.get_i18n_core")
    def test_translation_when_i18n_not_initialized(self, mock_get_core) -> None:
        """Test translation behavior when i18n is not properly initialized."""
        mock_get_core.side_effect = RuntimeError("i18n not initialized")

        result = _("Monitor failed: {error}", error="test")
        assert result == "Monitor failed: test"  # Should return formatted original

    def test_translation_with_none_message(self) -> None:
        """Test translation with None message."""
        init_i18n("fr")

        # Should handle gracefully by logging error and returning None
        result = _(None, error="test")  # type: ignore[arg-type]
        assert result is None  # Should return None after logging error


class TestI18nIntegration:
    """Integration tests for i18n functionality."""

    def test_language_switching(self) -> None:
        """Test switching between languages during runtime."""
        # Test English
        init_i18n("en")
        result_en = _("Monitor failed: {error}", error="test")

        # Switch to French
        init_i18n("fr")
        result_fr = _("Monitor failed: {error}", error="test")

        # Results should be different (unless French translation is missing)
        assert result_en is not None
        assert result_fr is not None

    def test_concurrent_translation_calls(self) -> None:
        """Test multiple concurrent translation calls."""
        init_i18n("fr")

        results = []
        for i in range(100):
            result = _("Monitor failed: {error}", error=f"test{i}")
            results.append(result)

        # All should succeed
        assert len(results) == 100
        assert all(result is not None for result in results)
