"""WSL (Windows Subsystem for Linux) utilities for cross-platform path resolution."""

import logging
import os
import platform
import subprocess
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


class WSLDetector:
    """Detects and provides information about WSL installations."""

    def __init__(self) -> None:
        """Initialize WSL detector."""
        self._is_windows = platform.system() == "Windows"
        self._wsl_available = None
        self._distributions = None
        self._current_user = None

    def is_wsl_available(self) -> bool:
        """Check if WSL is available on this system."""
        if self._wsl_available is not None:
            return self._wsl_available

        if not self._is_windows:
            self._wsl_available = False
            return False

        try:
            # Check if wsl.exe exists and can list distributions
            result = subprocess.run(
                ["wsl", "--list", "--quiet"],
                capture_output=True,
                text=True,
                timeout=5
            )
            self._wsl_available = result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            self._wsl_available = False

        logger.debug(f"WSL availability: {self._wsl_available}")
        return self._wsl_available

    def get_distributions(self) -> List[str]:
        """Get list of installed WSL distributions."""
        if self._distributions is not None:
            return self._distributions

        self._distributions = []

        if not self.is_wsl_available():
            return self._distributions

        try:
            result = subprocess.run(
                ["wsl", "--list", "--quiet"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                # Parse distribution names from output
                distributions = []
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        # Remove BOM and clean up distribution name
                        distro = line.strip().replace('\x00', '').replace('\ufeff', '')
                        if distro:
                            distributions.append(distro)

                self._distributions = distributions
                logger.debug(f"Found WSL distributions: {self._distributions}")

        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
            logger.debug(f"Failed to get WSL distributions: {e}")

        return self._distributions

    def get_potential_usernames(self) -> List[str]:
        """Get potential usernames for WSL path construction."""
        usernames = []

        # Try Windows USERNAME first
        username = os.environ.get("USERNAME")
        if username:
            usernames.append(username.lower())
            logger.debug(f"Added Windows username: {username.lower()}")

        # Try USER (when running from WSL)
        username = os.environ.get("USER")
        if username:
            usernames.append(username.lower())
            logger.debug(f"Added Unix username: {username.lower()}")

        # Extract from USERPROFILE
        userprofile = os.environ.get("USERPROFILE")
        if userprofile:
            profile_username = Path(userprofile).name.lower()
            if profile_username not in usernames:
                usernames.append(profile_username)
                logger.debug(f"Added username from USERPROFILE: {profile_username}")

        # Discover actual WSL usernames that might differ from Windows username
        # This handles cases where Windows and WSL usernames don't match
        if usernames:
            # Try to detect actual WSL username by checking common WSL user patterns
            for distro in self.get_distributions():
                wsl_home_path = f"//wsl$/{distro}/home"
                try:
                    wsl_home = Path(wsl_home_path)
                    if wsl_home.exists():
                        # List users in WSL home directory
                        for user_dir in wsl_home.iterdir():
                            if user_dir.is_dir():
                                potential_user = user_dir.name.lower()
                                if potential_user not in usernames:
                                    usernames.append(potential_user)
                                    logger.debug(f"Discovered WSL username: {potential_user}")
                except Exception as e:
                    logger.debug(f"Could not scan WSL home directory {wsl_home_path}: {e}")

        if not usernames:
            logger.warning("Could not determine any potential usernames")

        return usernames

    def get_current_user(self) -> Optional[str]:
        """Get the primary current user for WSL path construction."""
        usernames = self.get_potential_usernames()
        return usernames[0] if usernames else None

    def get_claude_paths(self) -> List[Path]:
        """Get potential Claude data paths in WSL."""
        paths = []

        if not self.is_wsl_available():
            return paths

        usernames = self.get_potential_usernames()
        if not usernames:
            return paths

        distributions = self.get_distributions()
        if not distributions:
            logger.debug("No WSL distributions found")
            return paths

        # Generate paths for actual installed distributions and all potential usernames
        for distro in distributions:
            for username in usernames:
                # Try both wsl$ and wsl.localhost formats
                wsl_paths = [
                    f"//wsl$/{distro}/home/{username}/.claude/projects",
                    f"//wsl.localhost/{distro}/home/{username}/.claude/projects"
                ]

                for path_str in wsl_paths:
                    try:
                        path = Path(path_str)
                        paths.append(path)
                    except Exception as e:
                        logger.debug(f"Invalid WSL path {path_str}: {e}")

        logger.debug(f"Generated {len(paths)} WSL Claude paths for {len(usernames)} usernames and {len(distributions)} distributions")
        return paths


def get_wsl_claude_paths() -> List[Path]:
    """Get WSL Claude data paths if available.

    Returns:
        List of potential WSL Claude data directory paths.
    """
    detector = WSLDetector()
    return detector.get_claude_paths()


def is_wsl_available() -> bool:
    """Check if WSL is available on this system.

    Returns:
        True if WSL is available and has distributions installed.
    """
    detector = WSLDetector()
    return detector.is_wsl_available() and len(detector.get_distributions()) > 0
