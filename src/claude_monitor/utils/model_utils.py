"""Model utilities for Claude Monitor.

This module provides model-related utility functions, re-exporting from core.models
for backward compatibility.
"""

import logging
import re
from typing import Dict, Match, Optional

logger = logging.getLogger(__name__)

# Matches modern (4.x/5-era) Claude model ids on the *normalized* name, e.g.
# "claude-opus-4-5", "claude-sonnet-5", "claude-fable-5", optionally carrying
# a provider prefix (Bedrock's "anthropic.claude-opus-5"). The minor version is
# capped at 2 digits so a trailing 8-digit date snapshot (e.g. "-20251101" —
# or "-20250514" in two-segment ids like "claude-opus-4-20250514") can never
# be mistaken for a minor version; the date is dropped from display.
_MODERN_MODEL_DISPLAY_RE = re.compile(
    r"^(?:anthropic\.)?claude-(opus|sonnet|haiku|fable|mythos)"
    r"-(\d{1,2})(?:-(\d{1,2}))?(?:-\d{8})?$"
)

# Same family/version shape, but used with re.search (not anchored) against a
# raw, possibly-prefixed model string.
_MODERN_MODEL_GENERATION_RE = re.compile(
    r"claude-(?:opus|sonnet|haiku|fable|mythos)"
    r"-(\d{1,2})(?:-(\d{1,2}))?(?:-\d{8})?(?:\D|$)"
)


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

    Claude 3-era keys use an explicit lookup table. Modern (4.x/5-era) ids
    are rendered from their family/major/minor components, e.g.
    ``"claude-opus-4-5"`` -> ``"Claude Opus 4.5"`` and ``"claude-fable-5"``
    -> ``"Claude Fable 5"``. A trailing date snapshot is dropped. Anything
    unrecognized falls back to title-casing the normalized name.

    Args:
        model: Model name to get display name for

    Returns:
        Display-friendly model name
    """
    normalized: str = normalize_model_name(model)

    display_names: Dict[str, str] = {
        "claude-3-opus": "Claude 3 Opus",
        "claude-3-sonnet": "Claude 3 Sonnet",
        "claude-3-haiku": "Claude 3 Haiku",
        "claude-3-5-sonnet": "Claude 3.5 Sonnet",
        "claude-3-5-haiku": "Claude 3.5 Haiku",
    }

    if normalized in display_names:
        return display_names[normalized]

    match: Optional[Match[str]] = _MODERN_MODEL_DISPLAY_RE.match(normalized)
    if match:
        family, major, minor = match.group(1), match.group(2), match.group(3)
        version: str = f"{major}.{minor}" if minor else major
        return f"Claude {family.capitalize()} {version}"

    return normalized.title()


def is_claude_model(model: str) -> bool:
    """Check if a model is a Claude model.

    Args:
        model: Model name to check

    Returns:
        True if it's a Claude model, False otherwise
    """
    normalized: str = normalize_model_name(model)
    return normalized.startswith("claude-")


def get_model_generation(model: str) -> str:
    """Get the generation/version of a Claude model.

    Handles legacy 1/2/3/3.5-era names via the original literal checks, then
    falls back to a regex derivation of major[.minor] for modern (4.x/5-era)
    family-based ids, e.g. ``"claude-opus-4-5"`` -> ``"4.5"``,
    ``"claude-sonnet-4-6"`` -> ``"4.6"``, ``"claude-opus-5"`` -> ``"5"``.

    Args:
        model: Model name

    Returns:
        Generation string (e.g., '3', '3.5', '4.5', '5') or 'unknown'
    """
    if not model:
        return "unknown"

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

    modern_match: Optional[Match[str]] = _MODERN_MODEL_GENERATION_RE.search(model_lower)
    if modern_match:
        major, minor = modern_match.group(1), modern_match.group(2)
        return f"{major}.{minor}" if minor else major

    match: Optional[Match[str]] = re.search(r"claude-(\d)(?:\D|$)", model_lower)
    if match:
        version: str = match.group(1)
        if version in ["1", "2", "3"]:
            return version

    return "unknown"
