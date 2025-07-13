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
