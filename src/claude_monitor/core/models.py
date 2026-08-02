"""Data models for Claude Monitor.
Core data structures for usage tracking, session management, and token calculations.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class CostMode(Enum):
    """Cost calculation modes for token usage analysis."""

    AUTO = "auto"
    CACHED = "cached"
    CALCULATED = "calculate"


def default_source() -> Dict[str, Any]:
    return {"kind": "claude_code_jsonl", "account": None}


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
    project: str = "unknown"
    source: Dict[str, Any] = field(default_factory=default_source)


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
    source: Dict[str, Any] = field(default_factory=default_source)
    # Reset time parsed from a limit message in this block, when present. Preferred
    # over start+5h for displaying the reset, since it is what Claude actually told
    # the user (issues #114, #106). Does not mutate end_time / block segmentation.
    usage_limit_reset_time: Optional[datetime] = None

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


def model_family(model: str) -> str:
    """Coarse Claude family for a model name.

    Single source of truth for family bucketing (pricing fallback, model usage
    bar, snapshot model distribution) so a new model launch is a one-place
    change. ``"fable"`` also covers Claude Mythos, which shares Fable's tier
    and pricing.

    Returns:
        One of ``"opus"``, ``"sonnet"``, ``"haiku"``, ``"fable"``, ``"other"``.
    """
    if not model:
        return "other"
    name = model.lower()
    if "fable" in name or "mythos" in name:
        return "fable"
    if "opus" in name:
        return "opus"
    if "sonnet" in name:
        return "sonnet"
    if "haiku" in name:
        return "haiku"
    return "other"


def normalize_model_name(model: str) -> str:
    """Normalize model name for consistent usage across the application.

    Claude 3-era names collapse to canonical legacy keys (``claude-3-opus``,
    ``claude-3-5-sonnet``, ...) so dated variants share one pricing entry.
    Anything newer (4.x, 5, Fable) passes through lowercased: collapsing
    unversioned names to the 3-era keys made ``claude-opus-5`` inherit legacy
    Opus 3 pricing ($15/$75 instead of $5/$25).

    Args:
        model: Raw model name from usage data

    Returns:
        Normalized model key

    Examples:
        >>> normalize_model_name("claude-3-opus-20240229")
        'claude-3-opus'
        >>> normalize_model_name("Claude 3.5 Sonnet")
        'claude-3-5-sonnet'
        >>> normalize_model_name("claude-opus-5")
        'claude-opus-5'
    """
    if not model:
        return ""

    model_lower = model.lower()

    is_3_5 = "3.5" in model_lower or "3-5" in model_lower
    is_3_era = is_3_5 or bool(re.search(r"claude[ -]3", model_lower))

    if is_3_era:
        if "opus" in model_lower:
            return "claude-3-opus"
        if "sonnet" in model_lower:
            return "claude-3-5-sonnet" if is_3_5 else "claude-3-sonnet"
        if "haiku" in model_lower:
            return "claude-3-5-haiku" if is_3_5 else "claude-3-haiku"

    if model_family(model_lower) != "other":
        return model_lower

    return model


def is_anthropic_model(model: str) -> bool:
    """Whether ``model`` is recognizably Anthropic/Claude (or the Claude-internal
    ``<synthetic>`` marker).

    Used by ``--filter-models anthropic`` to drop foreign models routed through
    Claude Code Router (e.g. GPT, DeepSeek, Gemini) so they do not count toward
    the Claude limit or cost. Matches on ``claude`` / ``anthropic`` only: every
    real Claude model id carries one of those (direct, Bedrock ``anthropic.``,
    or Vertex ``claude-`` forms), and matching bare family words like ``opus``
    would wrongly admit foreign names such as ``gpt-4-opus``. Empty/unknown names
    are treated as non-Anthropic.
    """
    if not model:
        return False
    name = model.lower()
    if name == "<synthetic>":
        return True
    return "claude" in name or "anthropic" in name
