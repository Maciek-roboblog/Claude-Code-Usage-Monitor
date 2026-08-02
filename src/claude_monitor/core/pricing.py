"""Pricing calculations for Claude models.

This module provides the PricingCalculator class for calculating costs
based on token usage and model pricing. It supports all Claude model types
(Opus, Sonnet, Haiku) and provides both simple and detailed cost calculations
with caching.
"""

from typing import Any, Dict, Optional

from claude_monitor.core.models import (
    CostMode,
    TokenCounts,
    model_family,
    normalize_model_name,
)


class PricingCalculator:
    """Calculates costs based on model pricing with caching support.

    This class provides methods for calculating costs for individual models/tokens
    as well as detailed cost breakdowns for collections of usage entries.
    It supports custom pricing configurations and caches calculations for performance.

    Features:
    - Configurable pricing (from config or custom)
    - Fallback hardcoded pricing for robustness
    - Caching for performance
    - Support for all token types including cache
    - Backward compatible with both APIs
    """

    # Current per-family rates (Opus 4.5+, Sonnet 3.5+, Haiku 4.5, Fable 5).
    # Sonnet 5 uses the sticker rate; its time-boxed introductory discount
    # ($2/$10 through 2026-08-31) is not modeled.
    # Cache create = input * 1.25 (5-min TTL); cache read = input * 0.1.
    FALLBACK_PRICING: Dict[str, Dict[str, float]] = {
        "opus": {
            "input": 5.0,
            "output": 25.0,
            "cache_creation": 6.25,
            "cache_read": 0.5,
        },
        "sonnet": {
            "input": 3.0,
            "output": 15.0,
            "cache_creation": 3.75,
            "cache_read": 0.3,
        },
        "haiku": {
            "input": 1.0,
            "output": 5.0,
            "cache_creation": 1.25,
            "cache_read": 0.1,
        },
        "fable": {
            "input": 10.0,
            "output": 50.0,
            "cache_creation": 12.5,
            "cache_read": 1.0,
        },
    }

    # A non-Anthropic model (e.g. routed through Claude Code Router) has no Claude
    # rate; price it as unknown ($0) rather than fabricating a Claude one (#217, #199).
    UNKNOWN_PRICING: Dict[str, float] = {
        "input": 0.0,
        "output": 0.0,
        "cache_creation": 0.0,
        "cache_read": 0.0,
    }

    # Versions priced differently from the current family rate.
    LEGACY_PRICING: Dict[str, Dict[str, float]] = {
        # Opus 3 / 4.0 / 4.1 were $15/$75 before Opus 4.5 dropped to $5/$25
        "claude-3-opus": {
            "input": 15.0,
            "output": 75.0,
            "cache_creation": 18.75,
            "cache_read": 1.5,
        },
        "claude-opus-4-20250514": {
            "input": 15.0,
            "output": 75.0,
            "cache_creation": 18.75,
            "cache_read": 1.5,
        },
        "claude-opus-4-1-20250805": {
            "input": 15.0,
            "output": 75.0,
            "cache_creation": 18.75,
            "cache_read": 1.5,
        },
        "claude-opus-4-1": {
            "input": 15.0,
            "output": 75.0,
            "cache_creation": 18.75,
            "cache_read": 1.5,
        },
        "claude-opus-4-0": {
            "input": 15.0,
            "output": 75.0,
            "cache_creation": 18.75,
            "cache_read": 1.5,
        },
        # Haiku 3 / 3.5 were cheaper than Haiku 4.5
        "claude-3-haiku": {
            "input": 0.25,
            "output": 1.25,
            "cache_creation": 0.3,
            "cache_read": 0.03,
        },
        "claude-3-5-haiku": {
            "input": 0.8,
            "output": 4.0,
            "cache_creation": 1.0,
            "cache_read": 0.08,
        },
    }

    def __init__(
        self, custom_pricing: Optional[Dict[str, Dict[str, float]]] = None
    ) -> None:
        """Initialize with optional custom pricing.

        Args:
            custom_pricing: Optional custom pricing dictionary to override defaults.
                          Should follow same structure as MODEL_PRICING.
        """
        # Use fallback pricing if no custom pricing provided
        self.pricing: Dict[str, Dict[str, float]] = custom_pricing or {
            **self.LEGACY_PRICING,
            "claude-3-sonnet": self.FALLBACK_PRICING["sonnet"],
            "claude-3-5-sonnet": self.FALLBACK_PRICING["sonnet"],
            "claude-sonnet-4-20250514": self.FALLBACK_PRICING["sonnet"],
            "claude-opus-4-5": self.FALLBACK_PRICING["opus"],
            "claude-opus-4-6": self.FALLBACK_PRICING["opus"],
            "claude-opus-4-7": self.FALLBACK_PRICING["opus"],
            "claude-opus-4-8": self.FALLBACK_PRICING["opus"],
            "claude-opus-5": self.FALLBACK_PRICING["opus"],
            "claude-sonnet-5": self.FALLBACK_PRICING["sonnet"],
            "claude-haiku-4-5": self.FALLBACK_PRICING["haiku"],
            "claude-fable-5": self.FALLBACK_PRICING["fable"],
            # Mythos shares Fable's tier and pricing (Project Glasswing).
            "claude-mythos-5": self.FALLBACK_PRICING["fable"],
        }
        self._cost_cache: Dict[str, float] = {}

    def calculate_cost(
        self,
        model: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cache_creation_tokens: int = 0,
        cache_read_tokens: int = 0,
        tokens: Optional[TokenCounts] = None,
        strict: bool = False,
    ) -> float:
        """Calculate cost with flexible API supporting both signatures.

        Args:
            model: Model name
            input_tokens: Number of input tokens (ignored if tokens provided)
            output_tokens: Number of output tokens (ignored if tokens provided)
            cache_creation_tokens: Number of cache creation tokens
            cache_read_tokens: Number of cache read tokens
            tokens: Optional TokenCounts object (takes precedence)

        Returns:
            Total cost in USD
        """
        # Handle synthetic model
        if model == "<synthetic>":
            return 0.0

        # Support TokenCounts object
        if tokens is not None:
            input_tokens = tokens.input_tokens
            output_tokens = tokens.output_tokens
            cache_creation_tokens = tokens.cache_creation_tokens
            cache_read_tokens = tokens.cache_read_tokens

        # Create cache key
        cache_key = (
            f"{model}:{input_tokens}:{output_tokens}:"
            f"{cache_creation_tokens}:{cache_read_tokens}"
        )

        # Check cache
        if cache_key in self._cost_cache:
            return self._cost_cache[cache_key]

        # Get pricing for model
        pricing = self._get_pricing_for_model(model, strict=strict)

        # Calculate costs (pricing is per million tokens)
        cost = (
            (input_tokens / 1_000_000) * pricing["input"]
            + (output_tokens / 1_000_000) * pricing["output"]
            + (cache_creation_tokens / 1_000_000)
            * pricing.get("cache_creation", pricing["input"] * 1.25)
            + (cache_read_tokens / 1_000_000)
            * pricing.get("cache_read", pricing["input"] * 0.1)
        )

        # Round to 6 decimal places
        cost = round(cost, 6)

        # Cache result
        self._cost_cache[cache_key] = cost
        return cost

    def _get_pricing_for_model(
        self, model: str, strict: bool = False
    ) -> Dict[str, float]:
        """Get pricing for a model with optional fallback logic.

        Args:
            model: Model name
            strict: If True, raise KeyError for unknown models

        Returns:
            Pricing dictionary with input/output/cache costs

        Raises:
            KeyError: If strict=True and model is unknown
        """
        # Try normalized model name first
        normalized = normalize_model_name(model)

        # Check configured pricing
        if normalized in self.pricing:
            pricing = self.pricing[normalized]
            # Ensure cache pricing exists
            if "cache_creation" not in pricing:
                pricing["cache_creation"] = pricing["input"] * 1.25
            if "cache_read" not in pricing:
                pricing["cache_read"] = pricing["input"] * 0.1
            return pricing

        # Check original model name
        if model in self.pricing:
            pricing = self.pricing[model]
            if "cache_creation" not in pricing:
                pricing["cache_creation"] = pricing["input"] * 1.25
            if "cache_read" not in pricing:
                pricing["cache_read"] = pricing["input"] * 0.1
            return pricing

        # If strict mode, raise KeyError for unknown models
        if strict:
            raise KeyError(f"Unknown model: {model}")

        # Fallback to the current family rate by name (single source of truth:
        # core.models.model_family). Future/unversioned family names land here
        # and get the *current* rate; legacy rates apply only to the explicit
        # keys above. ponytail: *-fast premium variants get the base family
        # rate (underestimates fast mode); add verified keys above if needed.
        family = model_family(model)
        if family != "other":
            return self.FALLBACK_PRICING[family]
        if "claude" in model.lower():
            return self.FALLBACK_PRICING["sonnet"]
        # Not a recognizable Anthropic model: don't fabricate a Claude rate.
        return self.UNKNOWN_PRICING

    def calculate_cost_for_entry(
        self, entry_data: Dict[str, Any], mode: CostMode
    ) -> float:
        """Calculate cost for a single entry (backward compatibility).

        Args:
            entry_data: Entry data dictionary
            mode: Cost mode (for backward compatibility)

        Returns:
            Cost in USD
        """
        # If cost is present and mode is cached, use it
        if mode.value == "cached":
            cost_value = entry_data.get("costUSD") or entry_data.get("cost_usd")
            if cost_value is not None:
                return float(cost_value)

        # Otherwise calculate from tokens
        model = entry_data.get("model") or entry_data.get("Model")
        if not model:
            raise KeyError("Missing 'model' key in entry_data")

        # Extract token counts with different possible keys
        input_tokens = entry_data.get("inputTokens", 0) or entry_data.get(
            "input_tokens", 0
        )
        output_tokens = entry_data.get("outputTokens", 0) or entry_data.get(
            "output_tokens", 0
        )
        cache_creation = entry_data.get(
            "cacheCreationInputTokens", 0
        ) or entry_data.get("cache_creation_tokens", 0)
        cache_read = (
            entry_data.get("cacheReadInputTokens", 0)
            or entry_data.get("cache_read_input_tokens", 0)
            or entry_data.get("cache_read_tokens", 0)
        )

        return self.calculate_cost(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_creation_tokens=cache_creation,
            cache_read_tokens=cache_read,
        )
