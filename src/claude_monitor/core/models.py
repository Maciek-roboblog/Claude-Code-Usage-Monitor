"""Data models for Claude Monitor.
Core data structures for usage tracking, session management, and token calculations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class CostMode(Enum):
    """Cost calculation modes for token usage analysis."""

    AUTO = "auto"
    CACHED = "cached"
    CALCULATED = "calculate"


@dataclass
class UsageEntry:
    """Individual usage record from Claude usage data."""

    timestamp: datetime
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    cost_usd: float = 0.0
    model: str = ""
    message_id: str = ""
    request_id: str = ""


@dataclass
class TokenCounts:
    """Token aggregation structure with computed totals."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        """Get total tokens across all types."""
        return (
            self.input_tokens
            + self.output_tokens
            + self.cache_creation_tokens
            + self.cache_read_tokens
        )


@dataclass
class BurnRate:
    """Token consumption rate metrics."""

    tokens_per_minute: float
    cost_per_hour: float


@dataclass
class UsageProjection:
    """Usage projection calculations for active blocks."""

    projected_total_tokens: int
    projected_total_cost: float
    remaining_minutes: float


@dataclass
class SessionBlock:
    """Aggregated session block representing a 5-hour period."""

    id: str
    start_time: datetime
    end_time: datetime
    entries: List[UsageEntry] = field(default_factory=list)
    token_counts: TokenCounts = field(default_factory=TokenCounts)
    is_active: bool = False
    is_gap: bool = False
    burn_rate: Optional[BurnRate] = None
    actual_end_time: Optional[datetime] = None
    per_model_stats: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    models: List[str] = field(default_factory=list)
    sent_messages_count: int = 0
    cost_usd: float = 0.0
    limit_messages: List[Dict[str, Any]] = field(default_factory=list)
    projection_data: Optional[Dict[str, Any]] = None
    burn_rate_snapshot: Optional[BurnRate] = None

    @property
    def total_tokens(self) -> int:
        """Get total tokens from token_counts."""
        return self.token_counts.total_tokens

    @property
    def total_cost(self) -> float:
        """Get total cost - alias for cost_usd."""
        return self.cost_usd

    @property
    def duration_minutes(self) -> float:
        """Get duration in minutes."""
        if self.actual_end_time:
            duration = (self.actual_end_time - self.start_time).total_seconds() / 60
        else:
            duration = (self.end_time - self.start_time).total_seconds() / 60
        return max(duration, 1.0)


def normalize_model_name(model: str) -> str:
    """Normalize model name for consistent usage across the application.

    Handles various model name formats and maps them to standard keys.
    (Moved from utils/model_utils.py)

    Args:
        model: Raw model name from usage data

    Returns:
        Normalized model key

    Examples:
        >>> normalize_model_name("claude-3-opus-20240229")
        'claude-3-opus'
        >>> normalize_model_name("Claude 3.5 Sonnet")
        'claude-3-5-sonnet'
    """
    if not model:
        return ""

    model_lower = model.lower()

    if (
        "claude-opus-4-" in model_lower
        or "claude-sonnet-4-" in model_lower
        or "claude-haiku-4-" in model_lower
        or "sonnet-4-" in model_lower
        or "opus-4-" in model_lower
        or "haiku-4-" in model_lower
    ):
        return model_lower

    if "opus" in model_lower:
        if "4-" in model_lower:
            return model_lower
        return "claude-3-opus"
    if "sonnet" in model_lower:
        if "4-" in model_lower:
            return model_lower
        if "3.5" in model_lower or "3-5" in model_lower:
            return "claude-3-5-sonnet"
        return "claude-3-sonnet"
    if "haiku" in model_lower:
        if "3.5" in model_lower or "3-5" in model_lower:
            return "claude-3-5-haiku"
        return "claude-3-haiku"

    return model


def parse_model_family(model: str) -> Optional[str]:
    """Extract model family (sonnet/opus/haiku) from model name.

    Args:
        model: Model name (e.g., 'claude-sonnet-4-5-20250929')

    Returns:
        Model family ('sonnet', 'opus', 'haiku') or None if not recognized

    Examples:
        >>> parse_model_family("claude-sonnet-4-5-20250929")
        'sonnet'
        >>> parse_model_family("claude-opus-4-1-20250815")
        'opus'
    """
    if not model:
        return None

    model_lower = model.lower()

    if "sonnet" in model_lower:
        return "sonnet"
    elif "opus" in model_lower:
        return "opus"
    elif "haiku" in model_lower:
        return "haiku"

    return None


def parse_model_generation(model: str) -> Optional[int]:
    """Extract major version/generation number from model name.

    Args:
        model: Model name (e.g., 'claude-sonnet-4-5-20250929')

    Returns:
        Major generation number (3, 4, 5, etc.) or None if not found

    Examples:
        >>> parse_model_generation("claude-sonnet-4-5-20250929")
        4
        >>> parse_model_generation("claude-3-5-sonnet")
        3
    """
    if not model:
        return None

    import re

    model_lower = model.lower()

    # Pattern: claude-{family}-{major}-{minor} or claude-{major}-{minor}-{family}
    # Examples: claude-sonnet-4-5-..., claude-3-5-sonnet, claude-3-opus
    patterns = [
        r"claude-(?:sonnet|opus|haiku)-(\d+)-",  # claude-sonnet-4-5
        r"claude-(\d+)-(?:\d+)?-?(?:sonnet|opus|haiku)",  # claude-3-5-sonnet
        r"claude-(\d+)-(?:sonnet|opus|haiku)",  # claude-3-opus
    ]

    for pattern in patterns:
        match = re.search(pattern, model_lower)
        if match:
            return int(match.group(1))

    return None


def parse_model_version(model: str) -> Optional[str]:
    """Extract full version string (major.minor) from model name.

    Args:
        model: Model name (e.g., 'claude-sonnet-4-5-20250929')

    Returns:
        Version string (e.g., '4.5', '3.5') or None if not found

    Examples:
        >>> parse_model_version("claude-sonnet-4-5-20250929")
        '4.5'
        >>> parse_model_version("claude-3-5-sonnet")
        '3.5'
    """
    if not model:
        return None

    import re

    model_lower = model.lower()

    # Pattern: {major}-{minor} after family name or before
    patterns = [
        r"(?:sonnet|opus|haiku)-(\d+)-(\d+)",  # sonnet-4-5
        r"claude-(\d+)-(\d+)",  # claude-3-5
    ]

    for pattern in patterns:
        match = re.search(pattern, model_lower)
        if match:
            major, minor = match.groups()
            return f"{major}.{minor}"

    # Fallback: just major version
    generation = parse_model_generation(model)
    if generation:
        return str(generation)

    return None


def get_model_display_name_with_version(model: str) -> str:
    """Get display name with version for a model.

    Args:
        model: Model name

    Returns:
        Display name with version (e.g., 'Sonnet 4.5', 'Opus 4.1')

    Examples:
        >>> get_model_display_name_with_version("claude-sonnet-4-5-20250929")
        'Sonnet 4.5'
        >>> get_model_display_name_with_version("claude-opus-4-1-20250815")
        'Opus 4.1'
    """
    family = parse_model_family(model)
    version = parse_model_version(model)

    if family and version:
        return f"{family.capitalize()} {version}"
    elif family:
        generation = parse_model_generation(model)
        if generation:
            return f"{family.capitalize()} {generation}"
        return family.capitalize()

    return model
