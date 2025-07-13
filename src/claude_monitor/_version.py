"""Version management utilities.

This module provides centralized version management that reads from pyproject.toml
as the single source of truth, avoiding version duplication across the codebase.
"""

import importlib.metadata


def get_version() -> str:
    """Get version from package metadata.

    This reads the version from the installed package metadata,
    which is set from pyproject.toml during build/installation.

    Returns:
        Version string (e.g., "3.0.0")
    """
    try:
        return importlib.metadata.version("claude-monitor")
    except importlib.metadata.PackageNotFoundError:
        # Fallback for development environments where package isn't installed
        return _get_version_from_pyproject()


def _get_version_from_pyproject() -> str:
    """Fallback: read version directly from pyproject.toml.

    This is used when the package isn't installed (e.g., development mode).

    Returns:
        Version string or "unknown" if cannot be determined
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
