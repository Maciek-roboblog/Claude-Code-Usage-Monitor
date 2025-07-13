"""Bootstrap utilities for CLI initialization."""

import logging
import os
import sys
from pathlib import Path
from typing import Optional

from claude_monitor.utils.time_utils import TimezoneHandler


def setup_logging(
    level: str = "INFO", log_file: Optional[Path] = None, disable_console: bool = False
) -> None:
    """
    Configures the application's logging system with the specified log level, optional file output, and optional console output.
    
    Parameters:
    	level (str): Logging level as a string (e.g., "DEBUG", "INFO").
    	log_file (Optional[Path]): Path to a file for logging output, if provided.
    	disable_console (bool): If True, disables logging to the console.
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    handlers = []
    if not disable_console:
        handlers.append(logging.StreamHandler(sys.stdout))
    if log_file:
        handlers.append(logging.FileHandler(log_file))

    if not handlers:
        handlers.append(logging.NullHandler())

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
    )


def setup_environment() -> None:
    """
    Initializes environment variables and ensures system output uses UTF-8 encoding.
    
    Sets default values for `CLAUDE_MONITOR_CONFIG` and `CLAUDE_MONITOR_CACHE_DIR` environment variables if they are not already set, and reconfigures standard output to UTF-8 encoding if necessary.
    """
    if sys.stdout.encoding != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")

    os.environ.setdefault(
        "CLAUDE_MONITOR_CONFIG", str(Path.home() / ".claude-monitor" / "config.yaml")
    )
    os.environ.setdefault(
        "CLAUDE_MONITOR_CACHE_DIR", str(Path.home() / ".claude-monitor" / "cache")
    )


def init_timezone(timezone: str = "Europe/Warsaw") -> TimezoneHandler:
    """
    Create and return a TimezoneHandler configured for the specified timezone.
    
    Parameters:
    	timezone (str): The timezone identifier to use (e.g., "Europe/Warsaw", "UTC"). Defaults to "Europe/Warsaw".
    
    Returns:
    	TimezoneHandler: An instance configured for the given timezone.
    """
    tz_handler = TimezoneHandler()
    if timezone != "Europe/Warsaw":
        tz_handler.set_timezone(timezone)
    return tz_handler


def ensure_directories() -> None:
    """
    Create the necessary `.claude-monitor` directories and subdirectories in the user's home directory if they do not already exist.
    """
    dirs = [
        Path.home() / ".claude-monitor",
        Path.home() / ".claude-monitor" / "cache",
        Path.home() / ".claude-monitor" / "logs",
        Path.home() / ".claude-monitor" / "reports",
    ]

    for directory in dirs:
        directory.mkdir(parents=True, exist_ok=True)
