"""Model utilities for Claude Monitor.

This module provides model-related utility functions, re-exporting from core.models
for backward compatibility.
"""

import logging
import re
from typing import Dict, Match, Optional

logger = logging.getLogger(__name__)


def normalize_model_name(model: str) -> str:
    """Normalize model name to a standard format.

    This function delegates to the implementation in core.models.

    Args:
        model: Model name to normalize

    Returns:
        Normalized model name
    """
    from claude_monitor.core.models import normalize_model_name as _normalize_model_name

    return _normalize_model_name(model)


def get_model_display_name(model: str) -> str:
    """Get a display-friendly model name.

    Args:
        model: Model name to get display name for

    Returns:
        Display-friendly model name
    """
    from claude_monitor.core.models import get_claude_5_family, is_anthropic_model

    normalized: str = normalize_model_name(model)
    claude_5_family = get_claude_5_family(model)
    if claude_5_family is not None and is_anthropic_model(model):
        return f"Claude 5 {claude_5_family.title()}"

    display_names: Dict[str, str] = {
        "claude-3-opus": "Claude 3 Opus",
        "claude-3-sonnet": "Claude 3 Sonnet",
        "claude-3-haiku": "Claude 3 Haiku",
        "claude-3-5-sonnet": "Claude 3.5 Sonnet",
        "claude-3-5-haiku": "Claude 3.5 Haiku",
    }

    return display_names.get(normalized, normalized.title())


def is_claude_model(model: str) -> bool:
    """Check if a model is a Claude model.

    Args:
        model: Model name to check

    Returns:
        True if it's a Claude model, False otherwise
    """
    from claude_monitor.core.models import is_anthropic_model

    return model != "<synthetic>" and is_anthropic_model(model)


def get_model_generation(model: str) -> str:
    """Get the generation/version of a Claude model.

    Args:
        model: Model name

    Returns:
        Generation string (e.g., '3', '3.5') or 'unknown'
    """
    if not model:
        return "unknown"

    from claude_monitor.core.models import get_claude_5_family, is_anthropic_model

    if get_claude_5_family(model) is not None and is_anthropic_model(model):
        return "5"

    model_lower: str = model.lower()

    if "claude-3-5" in model_lower or "claude-3.5" in model_lower:
        return "3.5"
    if (
        "claude-3" in model_lower
        or "claude-3-opus" in model_lower
        or "claude-3-sonnet" in model_lower
        or "claude-3-haiku" in model_lower
    ):
        return "3"
    if re.search(r"claude-2(?:\D|$)", model_lower):
        return "2"
    if re.search(r"claude-1(?:\D|$)", model_lower) or "claude-instant-1" in model_lower:
        return "1"
    match: Optional[Match[str]] = re.search(r"claude-(\d)(?:\D|$)", model_lower)
    if match:
        version: str = match.group(1)
        if version in ["1", "2", "3"]:
            return version

    return "unknown"
