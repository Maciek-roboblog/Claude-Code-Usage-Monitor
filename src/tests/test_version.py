"""Tests for version management."""

from typing import Dict
from unittest.mock import mock_open, patch

import pytest

from claude_monitor._version import _get_version_from_pyproject, get_version


def test_get_version_from_metadata() -> None:
    """Test getting version from package metadata."""
    with patch("importlib.metadata.version") as mock_version:
        mock_version.return_value = "3.0.0"
        version = get_version()
        assert version == "3.0.0"
        mock_version.assert_called_once_with("claude-monitor")


def test_get_version_fallback_to_pyproject() -> None:
    """Test fallback to pyproject.toml when package not installed."""
    mock_toml_content = """
[project]
name = "claude-monitor"
version = "3.0.0"
"""

    with patch("importlib.metadata.version") as mock_version:
        mock_version.side_effect = ImportError("Package not found")

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("builtins.open", mock_open(read_data=mock_toml_content.encode())),
        ):
            try:
                with patch("tomllib.load") as mock_load:
                    mock_load.return_value: Dict[str, Dict[str, str]] = {
                        "project": {"version": "3.0.0"}
                    }
                    version = _get_version_from_pyproject()
                    assert version == "3.0.0"
            except ImportError:
                # Python < 3.11, use tomli
                with patch("tomli.load") as mock_load:
                    mock_load.return_value: Dict[str, Dict[str, str]] = {
                        "project": {"version": "3.0.0"}
                    }
                    version = _get_version_from_pyproject()
                    assert version == "3.0.0"


def test_get_version_fallback_unknown() -> None:
    """Test fallback to 'unknown' when everything fails."""
    with patch("importlib.metadata.version") as mock_version:
        mock_version.side_effect = ImportError("Package not found")

        with patch("pathlib.Path.exists", return_value=False):
            version = _get_version_from_pyproject()
            assert version == "unknown"


def test_version_import_from_main_module() -> None:
    """Test that version can be imported from main module."""
    from claude_monitor import __version__

    assert isinstance(__version__, str)
    assert len(__version__) > 0


def test_version_format() -> None:
    """Test that version follows expected format."""
    from claude_monitor import __version__

    # Should be semantic version format (X.Y.Z) or include "unknown"
    if __version__ != "unknown":
        parts = __version__.split(".")
        assert len(parts) >= 2, (
            f"Version should have at least 2 parts, got: {__version__}"
        )

        # First part should be numeric
        assert parts[0].isdigit(), f"Major version should be numeric, got: {parts[0]}"
        assert parts[1].isdigit(), f"Minor version should be numeric, got: {parts[1]}"


def test_version_consistency() -> None:
    """Test that version is consistent across imports."""
    from claude_monitor import __version__ as version1
    from claude_monitor._version import __version__ as version2

    assert version1 == version2, "Version should be consistent across imports"


@pytest.mark.integration
def test_version_matches_pyproject() -> None:
    """Integration test: verify version matches pyproject.toml."""
    from pathlib import Path

    # Read version from pyproject.toml
    pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
    if pyproject_path.exists():
        try:
            import tomllib

            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
                expected_version = data["project"]["version"]
        except ImportError:
            # Python < 3.11, use tomli
            import tomli

            with open(pyproject_path, "rb") as f:
                data = tomli.load(f)
                expected_version = data["project"]["version"]

        # Compare with module version (only in installed package)
        from claude_monitor import __version__

        if __version__ != "unknown":
            assert __version__ == expected_version, (
                f"Module version {__version__} should match "
                f"pyproject.toml version {expected_version}"
            )
