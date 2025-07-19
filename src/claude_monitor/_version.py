"""Version management utilities.

This module provides centralized version management that reads from pyproject.toml
as the single source of truth, avoiding version duplication across the codebase.
"""

import importlib.metadata
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Union


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
            import tomli as tomllib  # type: ignore[import-untyped]
        except ImportError:
            # No TOML library available
            return "unknown"

    try:
        # Find pyproject.toml - go up from this file's directory
        current_dir = Path(__file__).parent
        for _ in range(5):  # Max 5 levels up
            pyproject_path = current_dir / "pyproject.toml"
            if pyproject_path.exists():
                with open(pyproject_path, "rb") as f:
                    data: Dict[str, Any] = tomllib.load(f)
                    project_data: Dict[str, Any] = data.get("project", {})
                    version: str = project_data.get("version", "unknown")
                    return version
            current_dir = current_dir.parent

        return "unknown"
    except Exception:
        return "unknown"


def get_package_info() -> Dict[str, Optional[str]]:
    """Get comprehensive package information.

    Returns:
        Dictionary containing version, name, and metadata
    """
    try:
        metadata = importlib.metadata.metadata("claude-monitor")
        return {
            "version": get_version(),
            "name": metadata.get("Name"),
            "author": metadata.get("Author"),
            "author_email": metadata.get("Author-email"),
            "description": metadata.get("Summary"),
            "home_page": metadata.get("Home-page"),
            "license": metadata.get("License"),
        }
    except importlib.metadata.PackageNotFoundError:
        return {
            "version": _get_version_from_pyproject(),
            "name": "claude-monitor",
            "author": None,
            "author_email": None,
            "description": None,
            "home_page": None,
            "license": None,
        }


def get_version_info() -> Dict[str, Any]:
    """Get detailed version and system information.

    Returns:
        Dictionary containing version, Python version, and system info
    """
    return {
        "version": get_version(),
        "python_version": sys.version,
        "python_version_info": {
            "major": sys.version_info.major,
            "minor": sys.version_info.minor,
            "micro": sys.version_info.micro,
        },
        "platform": sys.platform,
        "executable": sys.executable,
        "package_info": get_package_info(),
    }


def find_project_root(start_path: Optional[Union[str, Path]] = None) -> Optional[Path]:
    """Find the project root directory containing pyproject.toml.

    Args:
        start_path: Starting directory for search (defaults to current file location)

    Returns:
        Path to project root or None if not found
    """
    if start_path is None:
        current_dir = Path(__file__).parent
    else:
        current_dir = Path(start_path).resolve()

    # Search up to 10 levels to find pyproject.toml
    for _ in range(10):
        if (current_dir / "pyproject.toml").exists():
            return current_dir

        parent = current_dir.parent
        if parent == current_dir:  # Reached filesystem root
            break
        current_dir = parent

    return None


# Module-level version constant
__version__: str = get_version()
