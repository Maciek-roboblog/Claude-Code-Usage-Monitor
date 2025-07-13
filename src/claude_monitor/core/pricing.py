"""Pricing calculations for Claude models.

This module provides the PricingCalculator class for calculating costs
based on token usage and model pricing. It supports all Claude model types
(Opus, Sonnet, Haiku) and provides both simple and detailed cost calculations
with caching.
"""

from typing import Any, Dict, Optional

from claude_monitor.core.models import TokenCounts, normalize_model_name


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

    FALLBACK_PRICING = {
        "opus": {
            "input": 15.0,
            "output": 75.0,
            "cache_creation": 18.75,
            "cache_read": 1.5,
        },
        "sonnet": {
            "input": 3.0,
            "output": 15.0,
            "cache_creation": 3.75,
            "cache_read": 0.3,
        },
        "haiku": {
            "input": 0.25,
            "output": 1.25,
            "cache_creation": 0.3,
            "cache_read": 0.03,
        },
    }

    def __init__(self, custom_pricing: Optional[Dict[str, Dict[str, float]]] = None):
        """
        Initializes the PricingCalculator with optional custom pricing.
        
        If a custom pricing dictionary is provided, it overrides the default fallback pricing for supported Claude models. Otherwise, default pricing is used. Initializes the internal cost cache for computed results.
        """
        # Use fallback pricing if no custom pricing provided
        self.pricing = custom_pricing or {
            "claude-3-opus": self.FALLBACK_PRICING["opus"],
            "claude-3-sonnet": self.FALLBACK_PRICING["sonnet"],
            "claude-3-haiku": self.FALLBACK_PRICING["haiku"],
            "claude-3-5-sonnet": self.FALLBACK_PRICING["sonnet"],
            "claude-3-5-haiku": self.FALLBACK_PRICING["haiku"],
            "claude-sonnet-4-20250514": self.FALLBACK_PRICING["sonnet"],
            "claude-opus-4-20250514": self.FALLBACK_PRICING["opus"],
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
        """
        Calculates the total USD cost for token usage on a specified Claude model.
        
        Supports both explicit token count arguments and a TokenCounts object (which takes precedence). Returns zero cost for the synthetic model. The cost is computed by multiplying each token type (input, output, cache creation, cache read) by its respective per-million-token rate for the given model, summing the results, and rounding to six decimal places. Results are cached for efficiency.
        
        Parameters:
            model (str): Name of the Claude model.
            input_tokens (int, optional): Number of input tokens. Ignored if `tokens` is provided.
            output_tokens (int, optional): Number of output tokens. Ignored if `tokens` is provided.
            cache_creation_tokens (int, optional): Number of cache creation tokens. Ignored if `tokens` is provided.
            cache_read_tokens (int, optional): Number of cache read tokens. Ignored if `tokens` is provided.
            tokens (Optional[TokenCounts]): Optional TokenCounts object containing all token counts. If provided, overrides individual token arguments.
            strict (bool, optional): If True, raises KeyError for unknown models; otherwise, uses fallback pricing.
        
        Returns:
            float: Total cost in USD for the specified token usage.
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
        """
        Retrieve the pricing dictionary for a given model, applying fallback logic if necessary.
        
        If the model is not found in the configured pricing and strict mode is enabled, raises a KeyError. Otherwise, falls back to hardcoded pricing based on the model name. Ensures that cache creation and cache read pricing fields are present in the returned dictionary.
        
        Parameters:
            model (str): The name of the model to retrieve pricing for.
            strict (bool): If True, raises a KeyError when the model is unknown; otherwise, uses fallback pricing.
        
        Returns:
            Dict[str, float]: A dictionary containing pricing rates for input, output, cache creation, and cache read tokens.
        
        Raises:
            KeyError: If strict is True and the model is not found in the configured pricing.
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

        # Fallback to hardcoded pricing based on model type
        model_lower = model.lower()
        if "opus" in model_lower:
            return self.FALLBACK_PRICING["opus"]
        if "haiku" in model_lower:
            return self.FALLBACK_PRICING["haiku"]
        # Default to Sonnet pricing
        return self.FALLBACK_PRICING["sonnet"]

    def calculate_cost_for_entry(self, entry_data: Dict[str, Any], mode: Any) -> float:
        """
        Calculate the cost in USD for a single usage entry dictionary, supporting legacy key formats and cached cost retrieval.
        
        If the mode indicates cached cost and a cost field is present in the entry, returns that value directly. Otherwise, extracts the model and token counts from the entry and computes the cost using the current pricing configuration.
        
        Parameters:
            entry_data (Dict[str, Any]): Dictionary containing usage entry data, possibly with legacy key names.
            mode (Any): Mode object indicating cost calculation behavior; if its value is "cached", a cached cost may be used.
        
        Returns:
            float: The calculated or cached cost in USD.
        
        Raises:
            KeyError: If the model key is missing from the entry data.
        """
        # If cost is present and mode is cached, use it
        if mode.value == "cached":
            cost_value = entry_data.get("costUSD") or entry_data.get("cost_usd")
            if cost_value is not None:
                return cost_value

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
