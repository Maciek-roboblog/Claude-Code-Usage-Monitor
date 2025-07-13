"""Version management utilities.

This module provides centralized version management that reads from pyproject.toml
as the single source of truth, avoiding version duplication across the codebase.
"""

import importlib.metadata


def get_version() -> str:
    """
    Retrieve the current package version as a string.
    
    Attempts to obtain the version from the installed package metadata. If the package is not installed, falls back to reading the version from `pyproject.toml`. Returns "unknown" if the version cannot be determined.
    
    Returns:
        str: The version string of the package, or "unknown" if unavailable.
    """
    try:
        return importlib.metadata.version("claude-monitor")
    except importlib.metadata.PackageNotFoundError:
        # Fallback for development environments where package isn't installed
        return _get_version_from_pyproject()


def _get_version_from_pyproject() -> str:
    """
    Attempts to read the package version from a `pyproject.toml` file located up to five directory levels above the current file.
    
    Returns:
        str: The version string if found, otherwise "unknown".
    """
    try:
        # Python 3.11+
        import tomllib
    except ImportError:
        try:
            # Python < 3.11 fallback
            import tomli as tomllib  # type: ignore
        except ImportError:
            # No TOML library available
            return "unknown"

    try:
        from pathlib import Path

        # Find pyproject.toml - go up from this file's directory
        current_dir = Path(__file__).parent
        for _ in range(5):  # Max 5 levels up
            pyproject_path = current_dir / "pyproject.toml"
            if pyproject_path.exists():
                with open(pyproject_path, "rb") as f:
                    data = tomllib.load(f)
                    return data.get("project", {}).get("version", "unknown")
            current_dir = current_dir.parent

        return "unknown"
    except Exception:
        return "unknown"


# Module-level version constant
__version__: str = get_version()
