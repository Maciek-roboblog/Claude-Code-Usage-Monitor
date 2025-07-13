"""Model utilities for Claude Monitor.

This module provides model-related utility functions, re-exporting from core.models
for backward compatibility.
"""

import logging

logger = logging.getLogger(__name__)


def normalize_model_name(model: str) -> str:
    """
    Normalize a Claude model name to a standard canonical format.
    
    Parameters:
        model (str): The model name to normalize.
    
    Returns:
        str: The normalized model name.
    """
    from claude_monitor.core.models import normalize_model_name as _normalize_model_name

    return _normalize_model_name(model)


def get_model_display_name(model: str) -> str:
    """
    Return a user-friendly display name for a given Claude model.
    
    If the model matches a known Claude model, returns its human-readable name; otherwise, returns the normalized model name in title case.
    """
    normalized = normalize_model_name(model)

    display_names = {
        "claude-3-opus": "Claude 3 Opus",
        "claude-3-sonnet": "Claude 3 Sonnet",
        "claude-3-haiku": "Claude 3 Haiku",
        "claude-3-5-sonnet": "Claude 3.5 Sonnet",
        "claude-3-5-haiku": "Claude 3.5 Haiku",
    }

    return display_names.get(normalized, normalized.title())


def is_claude_model(model: str) -> bool:
    """
    Determine whether the given model name corresponds to a Claude model.
    
    Returns:
        bool: True if the normalized model name starts with "claude-", otherwise False.
    """
    normalized = normalize_model_name(model)
    return normalized.startswith("claude-")


def get_model_generation(model: str) -> str:
    """
    Determine the generation or version of a Claude model from its name.
    
    Parameters:
        model (str): The model name to analyze.
    
    Returns:
        str: The generation string (e.g., "3", "3.5", "2", "1") if recognized, or "unknown" if the version cannot be determined.
    """
    if not model:
        return "unknown"

    import re

    model_lower = model.lower()

    if "claude-3-5" in model_lower or "claude-3.5" in model_lower:
        return "3.5"
    elif (
        "claude-3" in model_lower
        or "claude-3-opus" in model_lower
        or "claude-3-sonnet" in model_lower
        or "claude-3-haiku" in model_lower
    ):
        return "3"
    elif re.search(r"claude-2(?:\D|$)", model_lower):
        return "2"
    elif (
        re.search(r"claude-1(?:\D|$)", model_lower) or "claude-instant-1" in model_lower
    ):
        return "1"
    else:
        match = re.search(r"claude-(\d)(?:\D|$)", model_lower)
        if match:
            version = match.group(1)
            if version in ["1", "2", "3"]:
                return version

        return "unknown"
