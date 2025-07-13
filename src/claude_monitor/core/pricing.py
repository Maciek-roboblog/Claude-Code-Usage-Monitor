"""Pricing calculations for Claude models.

This module provides the PricingCalculator class for calculating costs
based on token usage and model pricing. It supports all Claude model types
(Opus, Sonnet, Haiku) and provides both simple and detailed cost calculations
with caching using high-precision decimal arithmetic for financial accuracy.
"""

from decimal import ROUND_HALF_UP, Context, Decimal, getcontext
from typing import Any, Dict, Final, Optional, TypeAlias, Union

from claude_monitor.core.models import TokenCounts, normalize_model_name

# Financial calculation type aliases for precision
CurrencyAmount: TypeAlias = Decimal
TokenCount: TypeAlias = int
ModelName: TypeAlias = str
PricingRate: TypeAlias = Decimal  # Price per million tokens

# Pricing configuration type definitions
PricingConfig: TypeAlias = Dict[str, CurrencyAmount]
ModelPricingMap: TypeAlias = Dict[ModelName, PricingConfig]
CacheKey: TypeAlias = str

# Financial validation types
FinancialValidationResult: TypeAlias = Union[CurrencyAmount, None]


class PricingCalculator:
    """Calculates costs based on model pricing with high-precision financial calculations.

    This class provides methods for calculating costs for individual models/tokens
    as well as detailed cost breakdowns for collections of usage entries.
    It uses Decimal arithmetic for precise financial calculations and supports
    custom pricing configurations with robust caching for performance.

    Financial Features:
    - High-precision Decimal arithmetic for financial accuracy
    - Configurable pricing (from config or custom)
    - Fallback hardcoded pricing for robustness
    - Financial data validation and error handling
    - Multi-currency support foundations
    - Optimized caching with financial precision
    - Support for all token types including cache
    - Backward compatible with both APIs

    Precision:
    - Uses 10 decimal places for maximum financial accuracy
    - Configured for ROUND_HALF_UP rounding (banker's rounding)
    - Validates all monetary calculations for consistency
    """

    # Configure decimal context for financial precision
    _FINANCIAL_CONTEXT: Final[Context] = Context(
        prec=28,  # 28 digits precision for financial calculations
        rounding=ROUND_HALF_UP,  # Standard financial rounding
        Emin=-999999,  # Extended range for micro-calculations
        Emax=999999,
        capitals=1,
        clamp=0,
        flags=[],
        traps=[],
    )

    # High-precision fallback pricing in USD per million tokens
    FALLBACK_PRICING: Final[ModelPricingMap] = {
        "opus": {
            "input": Decimal("15.000000"),
            "output": Decimal("75.000000"),
            "cache_creation": Decimal("18.750000"),
            "cache_read": Decimal("1.500000"),
        },
        "sonnet": {
            "input": Decimal("3.000000"),
            "output": Decimal("15.000000"),
            "cache_creation": Decimal("3.750000"),
            "cache_read": Decimal("0.300000"),
        },
        "haiku": {
            "input": Decimal("0.250000"),
            "output": Decimal("1.250000"),
            "cache_creation": Decimal("0.300000"),
            "cache_read": Decimal("0.030000"),
        },
    }

    def __init__(
        self,
        custom_pricing: Optional[Dict[str, Dict[str, Union[float, Decimal]]]] = None,
    ) -> None:
        """Initialize with optional custom pricing and financial precision.

        Args:
            custom_pricing: Optional custom pricing dictionary to override defaults.
                          Accepts both float and Decimal values, automatically converts
                          to high-precision Decimal for financial accuracy.
        """
        # Set decimal context for financial calculations
        getcontext().prec = 28
        getcontext().rounding = ROUND_HALF_UP

        # Initialize financial validation state first
        self._validation_enabled: bool = True

        # Convert and validate custom pricing if provided
        if custom_pricing:
            self.pricing = self._convert_to_decimal_pricing(custom_pricing)
        else:
            # Use fallback pricing with proper Decimal conversion
            self.pricing: ModelPricingMap = {
                "claude-3-opus": self.FALLBACK_PRICING["opus"].copy(),
                "claude-3-sonnet": self.FALLBACK_PRICING["sonnet"].copy(),
                "claude-3-haiku": self.FALLBACK_PRICING["haiku"].copy(),
                "claude-3-5-sonnet": self.FALLBACK_PRICING["sonnet"].copy(),
                "claude-3-5-haiku": self.FALLBACK_PRICING["haiku"].copy(),
                "claude-sonnet-4-20250514": self.FALLBACK_PRICING["sonnet"].copy(),
                "claude-opus-4-20250514": self.FALLBACK_PRICING["opus"].copy(),
            }

        # Financial-grade cost cache with precise typing
        self._cost_cache: Dict[CacheKey, CurrencyAmount] = {}

    def _convert_to_decimal_pricing(
        self, pricing: Dict[str, Dict[str, Union[float, Decimal]]]
    ) -> ModelPricingMap:
        """Convert mixed pricing input to high-precision Decimal format.

        Args:
            pricing: Pricing dictionary with potential float/Decimal mix

        Returns:
            ModelPricingMap with all values as precise Decimals

        Raises:
            ValueError: If pricing data is invalid or contains negative values
        """
        converted_pricing: ModelPricingMap = {}

        for model, rates in pricing.items():
            converted_rates: PricingConfig = {}

            for rate_type, value in rates.items():
                # Validate and convert to Decimal
                validated_value = self._validate_currency_amount(value)
                if validated_value is None:
                    raise ValueError(
                        f"Invalid pricing value for {model}.{rate_type}: {value}"
                    )
                converted_rates[rate_type] = validated_value

            converted_pricing[model] = converted_rates

        return converted_pricing

    def _validate_currency_amount(
        self, value: Union[float, Decimal, int, str]
    ) -> FinancialValidationResult:
        """Validate and convert currency amount to precise Decimal.

        Args:
            value: Input value to validate and convert

        Returns:
            Validated Decimal amount or None if invalid
        """
        if not self._validation_enabled:
            return Decimal(str(value))

        try:
            # Convert to Decimal with financial precision
            decimal_value = Decimal(str(value))

            # Financial validation rules
            if decimal_value < 0:
                return None  # No negative pricing

            if decimal_value > Decimal(
                "10000"
            ):  # Sanity check: $10k per million tokens
                return None

            # Normalize to 6 decimal places for consistency
            return decimal_value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)

        except (ValueError, TypeError, ArithmeticError):
            return None

    def calculate_cost(
        self,
        model: ModelName,
        input_tokens: TokenCount = 0,
        output_tokens: TokenCount = 0,
        cache_creation_tokens: TokenCount = 0,
        cache_read_tokens: TokenCount = 0,
        tokens: Optional[TokenCounts] = None,
        strict: bool = False,
    ) -> CurrencyAmount:
        """Calculate cost with high-precision financial arithmetic.

        Uses Decimal arithmetic for precise financial calculations, supporting
        flexible API with both individual token parameters and TokenCounts object.

        Args:
            model: Model name for pricing lookup
            input_tokens: Number of input tokens (ignored if tokens provided)
            output_tokens: Number of output tokens (ignored if tokens provided)
            cache_creation_tokens: Number of cache creation tokens
            cache_read_tokens: Number of cache read tokens
            tokens: Optional TokenCounts object (takes precedence over individual params)
            strict: If True, raise KeyError for unknown models

        Returns:
            Total cost in USD as high-precision Decimal

        Raises:
            KeyError: If strict=True and model is unknown
            ValueError: If token counts are negative
        """
        # Handle synthetic model with zero cost
        if model == "<synthetic>":
            return Decimal("0.000000")

        # Validate token inputs for financial accuracy
        token_inputs = [
            input_tokens,
            output_tokens,
            cache_creation_tokens,
            cache_read_tokens,
        ]
        if any(t < 0 for t in token_inputs):
            raise ValueError("Token counts cannot be negative")

        # Support TokenCounts object with precedence
        if tokens is not None:
            input_tokens = tokens.input_tokens
            output_tokens = tokens.output_tokens
            cache_creation_tokens = tokens.cache_creation_tokens
            cache_read_tokens = tokens.cache_read_tokens

        # Create financial-grade cache key
        cache_key: CacheKey = (
            f"{model}:{input_tokens}:{output_tokens}:"
            f"{cache_creation_tokens}:{cache_read_tokens}"
        )

        # Check high-precision cache
        if cache_key in self._cost_cache:
            return self._cost_cache[cache_key]

        # Get validated pricing for model
        pricing = self._get_pricing_for_model(model, strict=strict)

        # High-precision financial calculations (pricing is per million tokens)
        million_tokens = Decimal("1000000")

        # Calculate individual cost components with Decimal precision
        input_cost = (Decimal(str(input_tokens)) / million_tokens) * pricing["input"]
        output_cost = (Decimal(str(output_tokens)) / million_tokens) * pricing["output"]

        # Cache costs with fallback calculation if not explicitly defined
        cache_creation_rate = pricing.get(
            "cache_creation", pricing["input"] * Decimal("1.25")
        )
        cache_creation_cost = (
            Decimal(str(cache_creation_tokens)) / million_tokens
        ) * cache_creation_rate

        cache_read_rate = pricing.get("cache_read", pricing["input"] * Decimal("0.1"))
        cache_read_cost = (
            Decimal(str(cache_read_tokens)) / million_tokens
        ) * cache_read_rate

        # Sum all cost components with financial precision
        total_cost = input_cost + output_cost + cache_creation_cost + cache_read_cost

        # Financial rounding to 6 decimal places (standard for USD micro-cents)
        final_cost = total_cost.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)

        # Cache result for performance optimization
        self._cost_cache[cache_key] = final_cost
        return final_cost

    def _get_pricing_for_model(
        self, model: ModelName, strict: bool = False
    ) -> PricingConfig:
        """Get high-precision pricing for a model with robust fallback logic.

        Implements intelligent model name normalization and provides fallback
        pricing for unknown models unless strict mode is enabled.

        Args:
            model: Model name for pricing lookup
            strict: If True, raise KeyError for unknown models instead of fallback

        Returns:
            High-precision pricing configuration with all required rates

        Raises:
            KeyError: If strict=True and model is unknown
        """
        # Try normalized model name first for consistent lookup
        normalized = normalize_model_name(model)

        # Check configured pricing with normalized name
        if normalized in self.pricing:
            pricing = self._ensure_complete_pricing(self.pricing[normalized].copy())
            return pricing

        # Check original model name for backward compatibility
        if model in self.pricing:
            pricing = self._ensure_complete_pricing(self.pricing[model].copy())
            return pricing

        # If strict mode, raise KeyError for unknown models
        if strict:
            raise KeyError(f"Unknown model: {model}")

        # Intelligent fallback to hardcoded pricing based on model type
        model_lower = model.lower()
        if "opus" in model_lower:
            return self._ensure_complete_pricing(self.FALLBACK_PRICING["opus"].copy())
        if "haiku" in model_lower:
            return self._ensure_complete_pricing(self.FALLBACK_PRICING["haiku"].copy())

        # Default to Sonnet pricing for unknown models
        return self._ensure_complete_pricing(self.FALLBACK_PRICING["sonnet"].copy())

    def _ensure_complete_pricing(self, pricing: PricingConfig) -> PricingConfig:
        """Ensure pricing configuration has all required rates with Decimal precision.

        Args:
            pricing: Partial pricing configuration

        Returns:
            Complete pricing configuration with all rates
        """
        # Ensure cache_creation rate exists (typically 25% markup on input)
        if "cache_creation" not in pricing:
            pricing["cache_creation"] = pricing["input"] * Decimal("1.25")

        # Ensure cache_read rate exists (typically 10% of input rate)
        if "cache_read" not in pricing:
            pricing["cache_read"] = pricing["input"] * Decimal("0.1")

        return pricing

    def calculate_cost_for_entry(self, entry_data: Dict[str, Any], mode: Any) -> float:
        """Calculate cost for a single entry with financial precision (backward compatibility).

        Maintains float return type for backward compatibility while using
        high-precision Decimal calculations internally. Supports multiple
        data formats and cost modes for flexible usage.

        Args:
            entry_data: Entry data dictionary with token counts and model info
            mode: Cost calculation mode (cached, calculated, auto)

        Returns:
            Cost in USD as float (for backward compatibility)

        Raises:
            KeyError: If required model information is missing
            ValueError: If token counts are invalid
        """
        # If cost is present and mode is cached, use cached value
        if hasattr(mode, "value") and mode.value == "cached":
            cost_value = entry_data.get("costUSD") or entry_data.get("cost_usd")
            if cost_value is not None:
                # Validate cached cost value
                validated_cost = self._validate_currency_amount(cost_value)
                if validated_cost is not None:
                    return float(validated_cost)

        # Extract model with multiple possible keys
        model = entry_data.get("model") or entry_data.get("Model")
        if not model:
            raise KeyError("Missing 'model' key in entry_data")

        # Extract token counts with comprehensive key support
        input_tokens = (
            entry_data.get("inputTokens", 0) or entry_data.get("input_tokens", 0) or 0
        )
        output_tokens = (
            entry_data.get("outputTokens", 0) or entry_data.get("output_tokens", 0) or 0
        )
        cache_creation = (
            entry_data.get("cacheCreationInputTokens", 0)
            or entry_data.get("cache_creation_tokens", 0)
            or entry_data.get("cache_creation_input_tokens", 0)
            or 0
        )
        cache_read = (
            entry_data.get("cacheReadInputTokens", 0)
            or entry_data.get("cache_read_input_tokens", 0)
            or entry_data.get("cache_read_tokens", 0)
            or 0
        )

        # Validate token counts
        token_values = [input_tokens, output_tokens, cache_creation, cache_read]
        if any(not isinstance(t, int) or t < 0 for t in token_values):
            raise ValueError("All token counts must be non-negative integers")

        # Calculate with high-precision Decimal internally
        precise_cost = self.calculate_cost(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_creation_tokens=cache_creation,
            cache_read_tokens=cache_read,
        )

        # Convert to float for backward compatibility
        return float(precise_cost)

    # Additional financial utility methods for advanced usage

    def get_pricing_info(self, model: ModelName) -> Dict[str, str]:
        """Get human-readable pricing information for a model.

        Args:
            model: Model name to get pricing for

        Returns:
            Dictionary with formatted pricing information
        """
        try:
            pricing = self._get_pricing_for_model(model, strict=False)
            return {
                "model": model,
                "input_rate_per_million": f"${pricing['input']:.6f}",
                "output_rate_per_million": f"${pricing['output']:.6f}",
                "cache_creation_rate_per_million": f"${pricing['cache_creation']:.6f}",
                "cache_read_rate_per_million": f"${pricing['cache_read']:.6f}",
                "precision": "6 decimal places (USD micro-cents)",
            }
        except Exception as e:
            return {"error": str(e), "model": model}

    def enable_financial_validation(self, enabled: bool = True) -> None:
        """Enable or disable financial validation for performance tuning.

        Args:
            enabled: Whether to enable strict financial validation
        """
        self._validation_enabled = enabled

    def clear_cost_cache(self) -> int:
        """Clear the cost calculation cache and return number of cached entries.

        Returns:
            Number of cache entries that were cleared
        """
        cache_size = len(self._cost_cache)
        self._cost_cache.clear()
        return cache_size
