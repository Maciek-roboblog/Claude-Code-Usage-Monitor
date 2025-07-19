"""Centralized error handling utilities for Claude Monitor.

This module provides a unified interface for error reporting and logging.
"""

import logging
import os
import sys
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, Union

from claude_monitor.i18n import _


class ErrorLevel(str, Enum):
    """Error severity levels for logging."""

    INFO = "info"
    ERROR = "error"


def report_error(
    exception: Exception,
    component: str,
    context_name: Optional[str] = None,
    context_data: Optional[Dict[str, Any]] = None,
    tags: Optional[Dict[str, str]] = None,
    level: ErrorLevel = ErrorLevel.ERROR,
) -> None:
    """Report an exception with standardized logging and context.

    Args:
        exception: The exception to report
        component: Component name for logging (e.g., "data_loader", "monitor_controller")
        context_name: Optional context name (e.g., "file_error", "parsing")
        context_data: Optional dictionary of context data
        tags: Optional additional tags (for logging extra context)
        level: Error severity level
    """
    logger = logging.getLogger(component)
    log_method = getattr(logger, level.value, logger.error)

    extra_data = {"context": context_name, "data": context_data, "tags": tags}

    try:
        log_method(
            _(
                "Error in {component}: {exception}",
                component=component,
                exception=str(exception),
            ),
            exc_info=True,
            extra=extra_data,
        )
    except Exception:
        # If logging itself fails, we can't do much more than silently continue
        # to avoid cascading failures
        pass


def report_file_error(
    exception: Exception,
    file_path: Union[str, Path],
    operation: str = "read",
    additional_context: Optional[Dict[str, Any]] = None,
) -> None:
    """Report file-related errors with standardized context.

    Args:
        exception: The exception that occurred
        file_path: Path to the file
        operation: The operation that failed (read, write, parse, etc.)
        additional_context: Any additional context data
    """
    context_data = {
        "file_path": str(file_path),
        "operation": operation,
    }

    if additional_context:
        context_data.update(additional_context)

    report_error(
        exception=exception,
        component="file_handler",
        context_name="file_error",
        context_data=context_data,
        tags={"operation": operation},
    )


def get_error_context() -> Dict[str, Any]:
    """Get standard error context information.

    Returns:
        Dictionary containing system and application context
    """
    return {
        "python_version": sys.version,
        "platform": sys.platform,
        "cwd": os.getcwd(),
        "pid": os.getpid(),
        "argv": sys.argv,
    }


def report_application_startup_error(
    exception: Exception,
    component: str = "application_startup",
    additional_context: Optional[Dict[str, Any]] = None,
) -> None:
    """Report application startup-related errors with system context.

    Args:
        exception: The startup exception
        component: Component where startup failed
        additional_context: Additional context data
    """
    context_data = get_error_context()

    if additional_context:
        context_data.update(additional_context)

    report_error(
        exception=exception,
        component=component,
        context_name="startup_error",
        context_data=context_data,
        tags={"error_type": "startup"},
    )


def report_configuration_error(
    exception: Exception,
    config_file: Optional[Union[str, Path]] = None,
    config_section: Optional[str] = None,
    additional_context: Optional[Dict[str, Any]] = None,
) -> None:
    """Report configuration-related errors.

    Args:
        exception: The configuration exception
        config_file: Path to the configuration file
        config_section: Configuration section that failed
        additional_context: Additional context data
    """
    context_data = {
        "config_file": str(config_file) if config_file else None,
        "config_section": config_section,
    }

    if additional_context:
        context_data.update(additional_context)

    report_error(
        exception=exception,
        component="configuration",
        context_name="config_error",
        context_data=context_data,
        tags={"error_type": "configuration"},
    )
