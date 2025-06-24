from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum


class CostMode(Enum):
    """Cost calculation modes for token usage analysis."""
    AUTO = "auto"        # Use costUSD if available, otherwise calculate from tokens
    CALCULATE = "calculate"  # Always calculate from tokens using LiteLLM prices
    DISPLAY = "display"      # Always use costUSD, show 0 if missing


@dataclass
class UsageEntry:
    """Individual usage record from JSONL files."""
    timestamp: datetime
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    cost_usd: Optional[float] = None
    model: str = ""
    message_id: Optional[str] = None
    request_id: Optional[str] = None


@dataclass
class TokenCounts:
    """Token aggregation structure
    
    Aggregates different types of token usage with computed total.
    Supports Claude's four token types for accurate cost calculation.
    """
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    
    @property
    def total_tokens(self) -> int:
        """Calculate total token count as sum of input and output tokens only
        
        Returns:
            Sum of input_tokens + output_tokens (excluding cache tokens)
        """
        return self.input_tokens + self.output_tokens




@dataclass
class SessionBlock:
    """Aggregated session block for 5-hour periods."""
    id: str
    start_time: datetime
    end_time: datetime
    actual_end_time: Optional[datetime] = None
    is_active: bool = False
    is_gap: bool = False
    entries: List[UsageEntry] = field(default_factory=list)
    token_counts: TokenCounts = field(default_factory=TokenCounts)
    cost_usd: float = 0.0
    models: List[str] = field(default_factory=list)
    
    # Per-model statistics tracking
    per_model_stats: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Burn rate tracking
    burn_rate_snapshot: Optional['BurnRate'] = None
    projection_data: Optional[Dict[str, Any]] = None
    
    # Token limit tracking
    limit_messages: List[Dict[str, Any]] = field(default_factory=list)
    
    @property
    def duration_minutes(self) -> float:
        """Calculate block duration in minutes."""
        if self.actual_end_time:
            delta = self.actual_end_time - self.start_time
        else:
            from datetime import timezone
            delta = datetime.now(timezone.utc) - self.start_time
        return delta.total_seconds() / 60


@dataclass
class BurnRate:
    """Token consumption rate metrics."""
    tokens_per_minute: float
    cost_per_hour: float


@dataclass
class UsageProjection:
    """Usage projection for active blocks."""
    projected_total_tokens: int
    projected_total_cost: float
    remaining_minutes: int