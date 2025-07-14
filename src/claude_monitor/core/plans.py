"""Centralized plan configuration for Claude Monitor.

All plan limits (token, message, cost) live in one place (PLAN_LIMITS).
Shared constants (defaults, common limits, threshold) are exposed on the Plans class.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


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
    """Immutable configuration for a Claude subscription plan."""

    name: str
    token_limit: int
    cost_limit: float
    message_limit: int
    display_name: str

    @property
    def formatted_token_limit(self) -> str:
        """Human-readable token limit (e.g., '19k' instead of '19000')."""
        if self.token_limit >= 1_000:
            return f"{self.token_limit // 1_000}k"
        return str(self.token_limit)


PLAN_LIMITS: Dict[PlanType, Dict[str, Any]] = {
    PlanType.PRO: {
        "token_limit": 19_000,
        "cost_limit": 18.0,
        "message_limit": 250,
        "display_name": "Pro",
    },
    PlanType.MAX5: {
        "token_limit": 88_000,
        "cost_limit": 35.0,
        "message_limit": 1_000,
        "display_name": "Max5",
    },
    PlanType.MAX20: {
        "token_limit": 220_000,
        "cost_limit": 140.0,
        "message_limit": 2_000,
        "display_name": "Max20",
    },
    PlanType.CUSTOM: {
        "token_limit": 44_000,
        "cost_limit": 50.0,
        "message_limit": 250,
        "display_name": "Custom",
    },
}

_DEFAULTS: Dict[str, Any] = {
    "token_limit": PLAN_LIMITS[PlanType.PRO]["token_limit"],
    "cost_limit": PLAN_LIMITS[PlanType.CUSTOM]["cost_limit"],
    "message_limit": PLAN_LIMITS[PlanType.PRO]["message_limit"],
}


class Plans:
    """Registry and shared constants for all plan configurations."""

    DEFAULT_TOKEN_LIMIT: int = _DEFAULTS["token_limit"]
    DEFAULT_COST_LIMIT: float = _DEFAULTS["cost_limit"]
    DEFAULT_MESSAGE_LIMIT: int = _DEFAULTS["message_limit"]
    COMMON_TOKEN_LIMITS: List[int] = [19_000, 88_000, 220_000, 880_000]
    LIMIT_DETECTION_THRESHOLD: float = 0.95

    @classmethod
    def _build_config(cls, plan_type: PlanType) -> PlanConfig:
        """Instantiate PlanConfig from the PLAN_LIMITS dictionary."""
        data = PLAN_LIMITS[plan_type]
        return PlanConfig(
            name=plan_type.value,
            token_limit=data["token_limit"],
            cost_limit=data["cost_limit"],
            message_limit=data["message_limit"],
            display_name=data["display_name"],
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
