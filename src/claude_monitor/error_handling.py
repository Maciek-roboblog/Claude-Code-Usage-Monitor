"""Centralized error handling and Sentry reporting utilities for Claude Monitor.

This module provides a unified interface for error reporting, replacing duplicate
Sentry error handling patterns throughout the codebase.
"""

import logging
from enum import Enum
from typing import Any, Dict, Optional

try:
    import sentry_sdk

    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False
    logging.warning(
        "Sentry SDK not available - error reporting will be limited to logging"
    )


class ErrorLevel(str, Enum):
    """Error severity levels matching Sentry's level system."""

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
    """Report an exception to Sentry with standardized context and tagging.

    This replaces the common pattern:
    ```python
    with sentry_sdk.configure_scope() as scope:
        scope.set_tag("component", "component_name")
        scope.set_context("context_name", {...})
    sentry_sdk.capture_exception(exception)
    ```

    Args:
        exception: The exception to report
        component: Component name for tagging (e.g., "data_loader", "monitor_controller")
        context_name: Optional context name (e.g., "file_error", "parsing")
        context_data: Optional dictionary of context data
        tags: Optional additional tags beyond the component tag
        level: Error severity level
    """
    logger = logging.getLogger(component)
    log_method = getattr(logger, level.value, logger.error)
    log_method(
        f"Error in {component}: {exception}",
        exc_info=True,
        extra={"context": context_name, "data": context_data},
    )

    if not SENTRY_AVAILABLE:
        return

    try:
        with sentry_sdk.configure_scope() as scope:
            scope.set_tag("component", component)

            if tags:
                for tag_key, tag_value in tags.items():
                    scope.set_tag(tag_key, str(tag_value))

            if context_name and context_data:
                scope.set_context(context_name, context_data)
            elif context_data:
                scope.set_context(component, context_data)

            scope.level = level.value
        sentry_sdk.capture_exception(exception)

    except Exception as e:
        logger.warning(f"Failed to report error to Sentry: {e}")


def report_file_error(
    exception: Exception,
    file_path: str,
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
