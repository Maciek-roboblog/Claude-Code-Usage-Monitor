"""Centralized plan configuration for Claude Monitor.

All plan limits (token, message, cost) live in one place (PLAN_LIMITS).
Shared constants (defaults, common limits, threshold) are exposed on the Plans class.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class PlanType(Enum):
    """Available Claude subscription plan types."""

    PRO = "pro"
    MAX5 = "max5"
    MAX20 = "max20"
    CUSTOM = "custom"

    @classmethod
    def from_string(cls, value: str) -> "PlanType":
        """
        Create a PlanType enum member from a case-insensitive string.
        
        Parameters:
            value (str): The plan type name to convert.
        
        Returns:
            PlanType: The corresponding PlanType enum member.
        
        Raises:
            ValueError: If the provided string does not match any PlanType.
        """
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
        """
        Returns the token limit as a human-readable string, using 'k' notation for values of 1,000 or more.
        """
        if self.token_limit >= 1_000:
            return f"{self.token_limit // 1_000}k"
        return str(self.token_limit)


PLAN_LIMITS: Dict[PlanType, Dict[str, Any]] = {
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

    DEFAULT_TOKEN_LIMIT = _DEFAULTS["token_limit"]
    DEFAULT_COST_LIMIT = _DEFAULTS["cost_limit"]
    DEFAULT_MESSAGE_LIMIT = _DEFAULTS["message_limit"]
    COMMON_TOKEN_LIMITS = [44_000, 88_000, 220_000, 880_000]
    LIMIT_DETECTION_THRESHOLD = 0.95

    @classmethod
    def _build_config(cls, plan_type: PlanType) -> PlanConfig:
        """
        Create a PlanConfig instance for the specified PlanType using predefined plan limits.
        
        Parameters:
        	plan_type (PlanType): The subscription plan type for which to build the configuration.
        
        Returns:
        	PlanConfig: The configuration object containing limits and display name for the given plan type.
        """
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
        """
        Return a dictionary of all available plan types mapped to their configuration objects.
        
        Returns:
            Dict[PlanType, PlanConfig]: Mapping of each PlanType to its corresponding PlanConfig instance.
        """
        return {pt: cls._build_config(pt) for pt in PLAN_LIMITS}

    @classmethod
    def get_plan(cls, plan_type: PlanType) -> PlanConfig:
        """
        Return the configuration details for the specified subscription plan type.
        
        Parameters:
        	plan_type (PlanType): The type of subscription plan.
        
        Returns:
        	PlanConfig: The configuration object containing limits and display information for the given plan type.
        """
        return cls._build_config(plan_type)

    @classmethod
    def get_plan_by_name(cls, name: str) -> Optional[PlanConfig]:
        """
        Return the PlanConfig for a given plan name string, or None if the name is invalid.
        
        Parameters:
            name (str): The case-insensitive name of the plan.
        
        Returns:
            Optional[PlanConfig]: The configuration for the specified plan, or None if the name does not match any known plan.
        """
        try:
            pt = PlanType.from_string(name)
            return cls.get_plan(pt)
        except ValueError:
            return None

    @classmethod
    def get_token_limit(cls, plan: str, blocks=None) -> int:
        """
        Return the token limit for the specified plan name.
        
        For the "custom" plan, if `blocks` are provided, calculates the P90 token limit using the provided session blocks. Returns the predefined or default token limit for other plans or if calculation is not possible.
        
        Parameters:
            plan (str): The name of the subscription plan.
            blocks: Optional session blocks for P90 calculation (used only for "custom" plans).
        
        Returns:
            int: The token limit for the specified plan.
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
        """
        Return the cost limit for the specified plan name, or the default cost limit if the plan is unrecognized.
        
        Parameters:
            plan (str): The name of the subscription plan.
        
        Returns:
            float: The cost limit associated with the plan, or the default if the plan is invalid.
        """
        cfg = cls.get_plan_by_name(plan)
        return cfg.cost_limit if cfg else cls.DEFAULT_COST_LIMIT

    @classmethod
    def get_message_limit(cls, plan: str) -> int:
        """
        Return the message limit for the specified plan name, or the default limit if the plan is unrecognized.
        
        Parameters:
            plan (str): The name of the subscription plan.
        
        Returns:
            int: The maximum number of messages allowed for the plan.
        """
        cfg = cls.get_plan_by_name(plan)
        return cfg.message_limit if cfg else cls.DEFAULT_MESSAGE_LIMIT

    @classmethod
    def is_valid_plan(cls, plan: str) -> bool:
        """
        Return True if the provided plan name corresponds to a recognized subscription plan; otherwise, return False.
        
        Parameters:
            plan (str): The name of the subscription plan to validate.
        
        Returns:
            bool: True if the plan name is valid, False otherwise.
        """
        return cls.get_plan_by_name(plan) is not None


TOKEN_LIMITS: Dict[str, int] = {
    plan.value: config.token_limit
    for plan, config in Plans.all_plans().items()
    if plan != PlanType.CUSTOM
}

DEFAULT_TOKEN_LIMIT: int = Plans.DEFAULT_TOKEN_LIMIT
COMMON_TOKEN_LIMITS = Plans.COMMON_TOKEN_LIMITS
LIMIT_DETECTION_THRESHOLD: float = Plans.LIMIT_DETECTION_THRESHOLD

COST_LIMITS: Dict[str, float] = {
    plan.value: config.cost_limit
    for plan, config in Plans.all_plans().items()
    if plan != PlanType.CUSTOM
}

DEFAULT_COST_LIMIT: float = Plans.DEFAULT_COST_LIMIT


def get_token_limit(plan: str, blocks=None) -> int:
    """
    Return the token limit for the specified plan name.
    
    If the plan is "custom" and session blocks are provided, calculates the P90 token limit using those blocks; otherwise, returns the predefined or default token limit.
    
    Parameters:
        plan (str): The name of the subscription plan.
        blocks: Optional session blocks used for P90 calculation with custom plans.
    
    Returns:
        int: The token limit for the specified plan.
    """
    return Plans.get_token_limit(plan, blocks)


def get_cost_limit(plan: str) -> float:
    """
    Return the cost limit in USD for the specified subscription plan.
    
    Parameters:
        plan (str): The name of the subscription plan.
    
    Returns:
        float: The cost limit in USD for the given plan, or the default if the plan is unrecognized.
    """
    return Plans.get_cost_limit(plan)
