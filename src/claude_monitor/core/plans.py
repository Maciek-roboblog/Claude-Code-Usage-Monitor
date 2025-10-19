"""Centralized plan configuration for Claude Monitor.

All plan limits (token, message, cost) live in one place (PLAN_LIMITS).
Shared constants (defaults, common limits, threshold) are exposed on the Plans class.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class PlanType(Enum):
    """Available Claude subscription plan types."""

    PRO = "pro"
    MAX5 = "max5"
    MAX20 = "max20"
    CUSTOM = "custom"

    @classmethod
    def from_string(cls, value: str) -> "PlanType":
        """Case-insensitive creation of PlanType from a string."""
        try:
            return cls(value.lower())
        except ValueError:
            raise ValueError(f"Unknown plan type: {value}")


@dataclass(frozen=True)
class PlanConfig:
    """Immutable configuration for a Claude subscription plan.

    Updated Oct 2025: Added weekly hour limits for Sonnet 4 and Opus 4.
    Weekly limits were introduced by Anthropic in August 2025 as a new
    rate limiting mechanism separate from 5-hour session token limits.
    """

    name: str
    token_limit: int
    cost_limit: float
    message_limit: int
    display_name: str
    weekly_sonnet4_hours: Optional[tuple[int, int]] = None  # (min, max) hours/week
    weekly_opus4_hours: Optional[tuple[int, int]] = None  # (min, max) hours/week

    @property
    def formatted_token_limit(self) -> str:
        """Human-readable token limit (e.g., '44k' instead of '44000')."""
        if self.token_limit >= 1_000:
            return f"{self.token_limit // 1_000}k"
        return str(self.token_limit)

    @property
    def has_weekly_limits(self) -> bool:
        """Check if this plan has weekly hour limits defined."""
        return self.weekly_sonnet4_hours is not None or self.weekly_opus4_hours is not None

    @property
    def formatted_weekly_sonnet4(self) -> str:
        """Human-readable Sonnet 4 weekly limit (e.g., '40-80h/week')."""
        if not self.weekly_sonnet4_hours:
            return "N/A"
        min_h, max_h = self.weekly_sonnet4_hours
        if min_h == max_h == 0:
            return "Not available"
        return f"{min_h}-{max_h}h/week"

    @property
    def formatted_weekly_opus4(self) -> str:
        """Human-readable Opus 4 weekly limit (e.g., '15-35h/week')."""
        if not self.weekly_opus4_hours:
            return "N/A"
        min_h, max_h = self.weekly_opus4_hours
        if min_h == max_h == 0:
            return "Not available"
        return f"{min_h}-{max_h}h/week"


PLAN_LIMITS: Dict[PlanType, Dict[str, Any]] = {
    PlanType.PRO: {
        "token_limit": 44_000,  # Updated Oct 2025: ~44k tokens per 5h session
        "cost_limit": 18.0,
        "message_limit": 250,
        "display_name": "Pro",
        # Weekly limits introduced Aug 2025 (measured in hours, not tokens)
        "weekly_sonnet4_hours": (40, 80),  # Range: min-max hours per week
        "weekly_opus4_hours": (0, 0),  # Opus 4 not available on Pro plan
    },
    PlanType.MAX5: {
        "token_limit": 88_000,
        "cost_limit": 35.0,
        "message_limit": 1_000,
        "display_name": "Max5",
        # Weekly limits introduced Aug 2025
        "weekly_sonnet4_hours": (140, 280),
        "weekly_opus4_hours": (15, 35),
    },
    PlanType.MAX20: {
        "token_limit": 220_000,
        "cost_limit": 140.0,
        "message_limit": 2_000,
        "display_name": "Max20",
        # Weekly limits introduced Aug 2025
        "weekly_sonnet4_hours": (240, 480),
        "weekly_opus4_hours": (24, 40),
    },
    PlanType.CUSTOM: {
        "token_limit": 44_000,
        "cost_limit": 50.0,
        "message_limit": 250,
        "display_name": "Custom",
        # Custom plans don't have predefined weekly limits
        "weekly_sonnet4_hours": None,
        "weekly_opus4_hours": None,
    },
}

_DEFAULTS: Dict[str, Any] = {
    "token_limit": PLAN_LIMITS[PlanType.PRO]["token_limit"],
    "cost_limit": PLAN_LIMITS[PlanType.CUSTOM]["cost_limit"],
    "message_limit": PLAN_LIMITS[PlanType.PRO]["message_limit"],
}

# Weekly hour limits by model family and generation
# Format: (family, generation) -> (plan_type -> (min_hours, max_hours))
# Introduced Aug 2025: Anthropic now tracks weekly usage in hours, not tokens
# This mapping supports dynamic detection of model versions (4.5, 4.1, etc.)
WEEKLY_LIMITS_BY_MODEL_FAMILY: Dict[Tuple[str, int], Dict[PlanType, Tuple[int, int]]] = {
    ("sonnet", 4): {  # Sonnet 4.x (includes 4.5, 4.0, etc.)
        PlanType.PRO: (40, 80),
        PlanType.MAX5: (140, 280),
        PlanType.MAX20: (240, 480),
        PlanType.CUSTOM: (0, 0),  # Custom plans have no predefined limits
    },
    ("opus", 4): {  # Opus 4.x (includes 4.1, 4.0, etc.)
        PlanType.PRO: (0, 0),  # Opus 4 not available on Pro
        PlanType.MAX5: (15, 35),
        PlanType.MAX20: (24, 40),
        PlanType.CUSTOM: (0, 0),
    },
    ("haiku", 4): {  # Haiku 4.x (includes 4.5, 4.0, etc.)
        # Haiku typically doesn't have weekly hour limits (free/unlimited)
        PlanType.PRO: (0, 0),
        PlanType.MAX5: (0, 0),
        PlanType.MAX20: (0, 0),
        PlanType.CUSTOM: (0, 0),
    },
    # Future models (5.x, 6.x) can be added here as they are released
}


def get_weekly_limits_for_model(
    model_name: str, plan_type: PlanType
) -> Optional[Tuple[int, int]]:
    """Get weekly hour limits for a specific model and plan.

    Args:
        model_name: Full model name (e.g., 'claude-sonnet-4-5-20250929')
        plan_type: Plan type (PRO, MAX5, MAX20, CUSTOM)

    Returns:
        Tuple of (min_hours, max_hours) or None if not found

    Examples:
        >>> get_weekly_limits_for_model("claude-sonnet-4-5-20250929", PlanType.PRO)
        (40, 80)
        >>> get_weekly_limits_for_model("claude-opus-4-1-20250815", PlanType.MAX5)
        (15, 35)
    """
    from claude_monitor.core.models import parse_model_family, parse_model_generation

    family = parse_model_family(model_name)
    generation = parse_model_generation(model_name)

    if not family or not generation:
        return None

    key = (family, generation)
    if key in WEEKLY_LIMITS_BY_MODEL_FAMILY:
        plan_limits = WEEKLY_LIMITS_BY_MODEL_FAMILY[key]
        if plan_type in plan_limits:
            limits = plan_limits[plan_type]
            # Return None if limits are (0, 0) which means not available/unlimited
            if limits == (0, 0):
                return None
            return limits

    return None


class Plans:
    """Registry and shared constants for all plan configurations."""

    DEFAULT_TOKEN_LIMIT: int = _DEFAULTS["token_limit"]
    DEFAULT_COST_LIMIT: float = _DEFAULTS["cost_limit"]
    DEFAULT_MESSAGE_LIMIT: int = _DEFAULTS["message_limit"]
    # Updated Oct 2025: Corrected common token limits based on current plans
    COMMON_TOKEN_LIMITS: List[int] = [44_000, 88_000, 220_000]
    LIMIT_DETECTION_THRESHOLD: float = 0.95

    @classmethod
    def _build_config(cls, plan_type: PlanType) -> PlanConfig:
        """Instantiate PlanConfig from the PLAN_LIMITS dictionary.

        Updated Oct 2025: Now includes weekly hour limits for Sonnet 4 and Opus 4.
        """
        data = PLAN_LIMITS[plan_type]
        return PlanConfig(
            name=plan_type.value,
            token_limit=data["token_limit"],
            cost_limit=data["cost_limit"],
            message_limit=data["message_limit"],
            display_name=data["display_name"],
            weekly_sonnet4_hours=data.get("weekly_sonnet4_hours"),
            weekly_opus4_hours=data.get("weekly_opus4_hours"),
        )

    @classmethod
    def all_plans(cls) -> Dict[PlanType, PlanConfig]:
        """Return a copy of all available plan configurations."""
        return {pt: cls._build_config(pt) for pt in PLAN_LIMITS}

    @classmethod
    def get_plan(cls, plan_type: PlanType) -> PlanConfig:
        """Get configuration for a specific PlanType."""
        return cls._build_config(plan_type)

    @classmethod
    def get_plan_by_name(cls, name: str) -> Optional[PlanConfig]:
        """Get PlanConfig by its string name (case-insensitive)."""
        try:
            pt = PlanType.from_string(name)
            return cls.get_plan(pt)
        except ValueError:
            return None

    @classmethod
    def get_token_limit(
        cls, plan: str, blocks: Optional[List[Dict[str, Any]]] = None
    ) -> int:
        """
        Get the token limit for a plan.

        For "custom" plans, if `blocks` are provided, compute the P90 limit.
        Otherwise, return the predefined limit or default.
        """
        cfg = cls.get_plan_by_name(plan)
        if cfg is None:
            return cls.DEFAULT_TOKEN_LIMIT

        if cfg.name == PlanType.CUSTOM.value and blocks:
            from claude_monitor.core.p90_calculator import P90Calculator

            p90_limit = P90Calculator().calculate_p90_limit(blocks)
            if p90_limit:
                return p90_limit

        return cfg.token_limit

    @classmethod
    def get_cost_limit(cls, plan: str) -> float:
        """Get the cost limit for a plan, or default if invalid."""
        cfg = cls.get_plan_by_name(plan)
        return cfg.cost_limit if cfg else cls.DEFAULT_COST_LIMIT

    @classmethod
    def get_message_limit(cls, plan: str) -> int:
        """Get the message limit for a plan, or default if invalid."""
        cfg = cls.get_plan_by_name(plan)
        return cfg.message_limit if cfg else cls.DEFAULT_MESSAGE_LIMIT

    @classmethod
    def is_valid_plan(cls, plan: str) -> bool:
        """Check whether a given plan name is recognized."""
        return cls.get_plan_by_name(plan) is not None


TOKEN_LIMITS: Dict[str, int] = {
    plan.value: config.token_limit
    for plan, config in Plans.all_plans().items()
    if plan != PlanType.CUSTOM
}

DEFAULT_TOKEN_LIMIT: int = Plans.DEFAULT_TOKEN_LIMIT
COMMON_TOKEN_LIMITS: List[int] = Plans.COMMON_TOKEN_LIMITS
LIMIT_DETECTION_THRESHOLD: float = Plans.LIMIT_DETECTION_THRESHOLD

COST_LIMITS: Dict[str, float] = {
    plan.value: config.cost_limit
    for plan, config in Plans.all_plans().items()
    if plan != PlanType.CUSTOM
}

DEFAULT_COST_LIMIT: float = Plans.DEFAULT_COST_LIMIT


def get_token_limit(plan: str, blocks: Optional[List[Dict[str, Any]]] = None) -> int:
    """Get token limit for a plan, using P90 for custom plans.

    Args:
        plan: Plan type ('pro', 'max5', 'max20', 'custom')
        blocks: Optional session blocks for custom P90 calculation

    Returns:
        Token limit for the plan
    """
    return Plans.get_token_limit(plan, blocks)


def get_cost_limit(plan: str) -> float:
    """Get standard cost limit for a plan.

    Args:
        plan: Plan type ('pro', 'max5', 'max20', 'custom')

    Returns:
        Cost limit for the plan in USD
    """
    return Plans.get_cost_limit(plan)
