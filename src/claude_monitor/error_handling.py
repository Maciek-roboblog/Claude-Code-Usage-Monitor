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
    """
    Reports an exception with standardized context and tags, logging locally and sending to Sentry if available.
    
    Parameters:
        exception (Exception): The exception instance to report.
        component (str): Identifier for the component where the error occurred.
        context_name (str, optional): Name for the error context (e.g., "file_error").
        context_data (dict, optional): Additional context data to include.
        tags (dict, optional): Additional tags for Sentry.
        level (ErrorLevel, optional): Severity level for the error (default is ErrorLevel.ERROR).
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
    """
    Report a file-related exception with standardized context and tagging.
    
    Parameters:
        exception (Exception): The exception instance to report.
        file_path (str): The path of the file involved in the error.
        operation (str, optional): The file operation that failed (e.g., "read", "write", "parse"). Defaults to "read".
        additional_context (dict, optional): Additional context data to include in the error report.
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
