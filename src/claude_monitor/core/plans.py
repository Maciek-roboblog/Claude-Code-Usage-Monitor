"""Centralized plan configuration for Claude Monitor.

All plan limits (token, message, cost) live in one place (PLAN_LIMITS).
Shared constants (defaults, common limits, threshold) are exposed on the Plans class.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, TypedDict


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
        """Human-readable token limit (e.g., '44k' instead of '44000')."""
        if self.token_limit >= 1_000:
            return f"{self.token_limit // 1_000}k"
        return str(self.token_limit)


class PlanLimitData(TypedDict):
    """Type definition for plan limit configuration data."""

    token_limit: int
    cost_limit: float
    message_limit: int
    display_name: str


PLAN_LIMITS: Dict[PlanType, PlanLimitData] = {
    PlanType.PRO: {
        "token_limit": 44_000,
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
        "cost_limit": 200.0,
        "message_limit": 250,
        "display_name": "Custom",
    },
}

_DEFAULTS = {
    "token_limit": PLAN_LIMITS[PlanType.PRO]["token_limit"],
    "cost_limit": PLAN_LIMITS[PlanType.CUSTOM]["cost_limit"],
    "message_limit": PLAN_LIMITS[PlanType.PRO]["message_limit"],
}


class Plans:
    """Registry and shared constants for all plan configurations."""

    DEFAULT_TOKEN_LIMIT: int = int(_DEFAULTS["token_limit"])
    DEFAULT_COST_LIMIT: float = float(_DEFAULTS["cost_limit"])
    DEFAULT_MESSAGE_LIMIT: int = int(_DEFAULTS["message_limit"])
    COMMON_TOKEN_LIMITS: List[int] = [44_000, 88_000, 220_000, 880_000]
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
            try:
                from claude_monitor.core.p90_calculator import P90Calculator

                p90_limit = P90Calculator().calculate_p90_limit(blocks)
                if p90_limit:
                    return p90_limit
            except ImportError:
                # Fallback to default if P90Calculator is not available
                pass

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

    @classmethod
    def validate_plan_limits(
        cls,
        token_limit: int,
        cost_limit: float,
        message_limit: int,
    ) -> bool:
        """Validate that plan limits are within reasonable bounds.

        Args:
            token_limit: Token limit to validate
            cost_limit: Cost limit to validate
            message_limit: Message limit to validate

        Returns:
            True if limits are valid, False otherwise
        """
        return (
            token_limit > 0
            and cost_limit > 0.0
            and message_limit > 0
            and token_limit <= 1_000_000  # Max 1M tokens
            and cost_limit <= 1000.0  # Max $1000
            and message_limit <= 10_000  # Max 10k messages
        )

    @classmethod
    def create_custom_plan(
        cls,
        name: str,
        token_limit: int,
        cost_limit: float,
        message_limit: int,
        display_name: Optional[str] = None,
    ) -> Optional[PlanConfig]:
        """Create a custom plan configuration with validation.

        Args:
            name: Plan identifier name
            token_limit: Token usage limit
            cost_limit: Cost usage limit in USD
            message_limit: Message count limit
            display_name: Human-readable plan name

        Returns:
            PlanConfig instance if valid, None if invalid limits
        """
        if not cls.validate_plan_limits(token_limit, cost_limit, message_limit):
            return None

        return PlanConfig(
            name=name,
            token_limit=token_limit,
            cost_limit=cost_limit,
            message_limit=message_limit,
            display_name=display_name or name.title(),
        )

    @classmethod
    def get_plan_tier(cls, plan_type: PlanType) -> str:
        """Get the tier classification for a plan type.

        Args:
            plan_type: The plan type to classify

        Returns:
            Tier classification string
        """
        tier_mapping = {
            PlanType.PRO: "basic",
            PlanType.MAX5: "premium",
            PlanType.MAX20: "enterprise",
            PlanType.CUSTOM: "custom",
        }
        return tier_mapping.get(plan_type, "unknown")

    @classmethod
    def is_usage_limit_exceeded(
        cls,
        plan_type: PlanType,
        current_tokens: int,
        current_cost: float,
        current_messages: int,
    ) -> Dict[str, bool]:
        """Check if current usage exceeds plan limits.

        Args:
            plan_type: The subscription plan type
            current_tokens: Current token usage
            current_cost: Current cost usage
            current_messages: Current message count

        Returns:
            Dictionary indicating which limits are exceeded
        """
        config = cls.get_plan(plan_type)

        return {
            "tokens": current_tokens > config.token_limit,
            "cost": current_cost > config.cost_limit,
            "messages": current_messages > config.message_limit,
        }

    @classmethod
    def calculate_usage_percentage(
        cls,
        plan_type: PlanType,
        current_tokens: int,
        current_cost: float,
        current_messages: int,
    ) -> Dict[str, float]:
        """Calculate usage percentage for each limit type.

        Args:
            plan_type: The subscription plan type
            current_tokens: Current token usage
            current_cost: Current cost usage
            current_messages: Current message count

        Returns:
            Dictionary with usage percentages (0.0 to 1.0+)
        """
        config = cls.get_plan(plan_type)

        return {
            "tokens": current_tokens / config.token_limit,
            "cost": current_cost / config.cost_limit,
            "messages": current_messages / config.message_limit,
        }


# Plan limit dictionaries for backward compatibility
TOKEN_LIMITS: Dict[str, int] = {
    plan.value: config.token_limit
    for plan, config in Plans.all_plans().items()
    if plan != PlanType.CUSTOM
}

# Default limits with explicit typing
DEFAULT_TOKEN_LIMIT: int = Plans.DEFAULT_TOKEN_LIMIT
COMMON_TOKEN_LIMITS: List[int] = Plans.COMMON_TOKEN_LIMITS
LIMIT_DETECTION_THRESHOLD: float = Plans.LIMIT_DETECTION_THRESHOLD

COST_LIMITS: Dict[str, float] = {
    plan.value: config.cost_limit
    for plan, config in Plans.all_plans().items()
    if plan != PlanType.CUSTOM
}

DEFAULT_COST_LIMIT: float = Plans.DEFAULT_COST_LIMIT
DEFAULT_MESSAGE_LIMIT: int = Plans.DEFAULT_MESSAGE_LIMIT


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
