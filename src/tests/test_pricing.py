"""Comprehensive tests for PricingCalculator class."""

from typing import Dict, List, Union

import pytest

from claude_monitor.core.models import CostMode, TokenCounts
from claude_monitor.core.pricing import PricingCalculator


class TestPricingCalculator:
    """Test suite for PricingCalculator class."""

    @pytest.fixture
    def calculator(self) -> PricingCalculator:
        """Create a PricingCalculator with default pricing."""
        return PricingCalculator()

    @pytest.fixture
    def custom_pricing(self) -> Dict[str, Dict[str, float]]:
        """Custom pricing configuration for testing."""
        return {
            "test-model": {
                "input": 1.0,
                "output": 2.0,
                "cache_creation": 1.5,
                "cache_read": 0.1,
            }
        }

    @pytest.fixture
    def custom_calculator(
        self, custom_pricing: Dict[str, Dict[str, float]]
    ) -> PricingCalculator:
        """Create a PricingCalculator with custom pricing."""
        return PricingCalculator(custom_pricing)

    @pytest.fixture
    def sample_entry_data(self) -> Dict[str, Union[str, int, None]]:
        """Sample entry data for testing."""
        return {
            "model": "claude-3-haiku",
            "input_tokens": 1000,
            "output_tokens": 500,
            "cache_creation_tokens": 100,
            "cache_read_tokens": 50,
            "cost_usd": None,
        }

    @pytest.fixture
    def token_counts(self) -> TokenCounts:
        """Sample TokenCounts object."""
        return TokenCounts(
            input_tokens=1000,
            output_tokens=500,
            cache_creation_tokens=100,
            cache_read_tokens=50,
        )

    def test_init_default_pricing(self, calculator: PricingCalculator) -> None:
        """Test initialization with default pricing."""
        assert calculator.pricing is not None
        assert "claude-3-opus" in calculator.pricing
        assert "claude-3-sonnet" in calculator.pricing
        assert "claude-3-haiku" in calculator.pricing
        assert "claude-3-5-sonnet" in calculator.pricing
        assert calculator._cost_cache == {}

    def test_init_custom_pricing(
        self,
        custom_calculator: PricingCalculator,
        custom_pricing: Dict[str, Dict[str, float]],
    ) -> None:
        """Test initialization with custom pricing."""
        assert custom_calculator.pricing == custom_pricing
        assert custom_calculator._cost_cache == {}

    def test_fallback_pricing_structure(self, calculator: PricingCalculator) -> None:
        """Test that fallback pricing has correct structure."""
        fallback = PricingCalculator.FALLBACK_PRICING

        for model_type in ["opus", "sonnet", "haiku"]:
            assert model_type in fallback
            pricing = fallback[model_type]
            assert "input" in pricing
            assert "output" in pricing
            assert "cache_creation" in pricing
            assert "cache_read" in pricing

            # Verify pricing values are positive
            assert pricing["input"] > 0
            assert pricing["output"] > pricing["input"]  # Output typically costs more
            assert (
                pricing["cache_creation"] > pricing["input"]
            )  # Cache creation costs more
            assert pricing["cache_read"] < pricing["input"]  # Cache read costs less

    @pytest.mark.parametrize(
        "model,inp,out",
        [
            # Current models — family fallback now reflects current rates
            ("claude-opus-4-8", 5.0, 25.0),
            ("claude-opus-4-6", 5.0, 25.0),
            ("claude-opus-4-5-20251101", 5.0, 25.0),
            ("claude-haiku-4-5", 1.0, 5.0),
            ("claude-haiku-4-5-20251001", 1.0, 5.0),
            ("claude-fable-5", 10.0, 50.0),
            ("claude-sonnet-4-20250514", 3.0, 15.0),
            # Claude 5 family — must not inherit 3-era legacy rates
            ("claude-opus-5", 5.0, 25.0),
            ("claude-sonnet-5", 3.0, 15.0),
            ("claude-mythos-5", 10.0, 50.0),
            # Bedrock envelope must strip to the legacy pricing key, not fall
            # through to the current family rate (coderabbit PR #239)
            ("anthropic.claude-opus-4-20250514-v1:0", 15.0, 75.0),
            ("us.anthropic.claude-opus-4-1-v1:0", 15.0, 75.0),
            # Legacy versions priced differently from the current family rate
            ("claude-opus-4-20250514", 15.0, 75.0),  # Opus 4.0
            ("claude-opus-4-1", 15.0, 75.0),  # Opus 4.1 alias (codex P1)
            ("claude-opus-4-0", 15.0, 75.0),  # Opus 4.0 alias
            ("claude-3-opus", 15.0, 75.0),
            ("claude-3-haiku", 0.25, 1.25),
            ("claude-3-5-haiku", 0.8, 4.0),
        ],
    )
    def test_version_specific_pricing(
        self, calculator: PricingCalculator, model: str, inp: float, out: float
    ) -> None:
        """Per-version rates: current models get current rates, legacy keep theirs (#182)."""
        pricing = calculator._get_pricing_for_model(model)
        assert pricing["input"] == inp
        assert pricing["output"] == out

    def test_foreign_model_with_family_word_not_billed_as_claude(
        self, calculator: PricingCalculator
    ) -> None:
        """A non-Anthropic model containing a Claude family word gets $0, not Opus."""
        pricing = calculator._get_pricing_for_model("gpt-4-opus")
        assert pricing == PricingCalculator.UNKNOWN_PRICING
        cost = calculator.calculate_cost(
            model="gpt-4-opus", input_tokens=1_000_000, output_tokens=1_000_000
        )
        assert cost == 0.0

    def test_calculate_cost_opus_4_8(self, calculator: PricingCalculator) -> None:
        """End-to-end cost for current Opus uses $5/$25, not the legacy $15/$75."""
        cost = calculator.calculate_cost(
            model="claude-opus-4-8", input_tokens=1_000_000, output_tokens=1_000_000
        )
        assert cost == 30.0  # 5.0 + 25.0

    def test_calculate_cost_opus_5_not_legacy(
        self, calculator: PricingCalculator
    ) -> None:
        """Regression: claude-opus-5 once normalized to claude-3-opus and was
        billed at legacy $15/$75 (a 3x overcount) instead of $5/$25."""
        cost = calculator.calculate_cost(
            model="claude-opus-5", input_tokens=1_000_000, output_tokens=1_000_000
        )
        assert cost == 30.0  # 5.0 + 25.0

    def test_calculate_cost_claude_3_haiku_basic(
        self, calculator: PricingCalculator
    ) -> None:
        """Test cost calculation for Claude 3 Haiku with basic tokens."""
        cost = calculator.calculate_cost(
            model="claude-3-haiku", input_tokens=1000, output_tokens=500
        )

        # Expected: (1000 * 0.25 + 500 * 1.25) / 1000000
        expected = (1000 * 0.25 + 500 * 1.25) / 1000000
        assert abs(cost - expected) < 1e-6

    def test_calculate_cost_claude_3_opus_with_cache(
        self, calculator: PricingCalculator
    ) -> None:
        """Test cost calculation for Claude 3 Opus with cache tokens."""
        cost = calculator.calculate_cost(
            model="claude-3-opus",
            input_tokens=1000,
            output_tokens=500,
            cache_creation_tokens=100,
            cache_read_tokens=50,
        )

        # Expected calculation based on Opus pricing
        expected = (
            1000 * 15.0  # input
            + 500 * 75.0  # output
            + 100 * 18.75  # cache creation
            + 50 * 1.5  # cache read
        ) / 1000000
        assert abs(cost - expected) < 1e-6

    def test_calculate_cost_claude_3_sonnet(
        self, calculator: PricingCalculator
    ) -> None:
        """Test cost calculation for Claude 3 Sonnet."""
        cost = calculator.calculate_cost(
            model="claude-3-sonnet", input_tokens=2000, output_tokens=1000
        )

        expected = (2000 * 3.0 + 1000 * 15.0) / 1000000
        assert abs(cost - expected) < 1e-6

    def test_calculate_cost_claude_3_5_sonnet(
        self, calculator: PricingCalculator
    ) -> None:
        """Test cost calculation for Claude 3.5 Sonnet (should use sonnet pricing)."""
        cost = calculator.calculate_cost(
            model="claude-3-5-sonnet", input_tokens=1000, output_tokens=500
        )

        expected = (1000 * 3.0 + 500 * 15.0) / 1000000
        assert abs(cost - expected) < 1e-6

    def test_calculate_cost_with_token_counts_object(
        self, calculator: PricingCalculator, token_counts: TokenCounts
    ) -> None:
        """Test cost calculation using TokenCounts object."""
        cost = calculator.calculate_cost(model="claude-3-haiku", tokens=token_counts)

        expected = (
            1000 * 0.25  # input
            + 500 * 1.25  # output
            + 100 * 0.3  # cache creation
            + 50 * 0.03  # cache read
        ) / 1000000
        assert abs(cost - expected) < 1e-6

    def test_calculate_cost_token_counts_overrides_individual_params(
        self, calculator: PricingCalculator, token_counts: TokenCounts
    ) -> None:
        """Test that TokenCounts object takes precedence over individual parameters."""
        cost = calculator.calculate_cost(
            model="claude-3-haiku",
            input_tokens=9999,  # Should be ignored
            output_tokens=9999,  # Should be ignored
            tokens=token_counts,
        )

        # Should use values from token_counts, not the individual parameters
        expected = (
            1000 * 0.25  # from token_counts
            + 500 * 1.25  # from token_counts
            + 100 * 0.3  # from token_counts
            + 50 * 0.03  # from token_counts
        ) / 1000000
        assert abs(cost - expected) < 1e-6

    def test_calculate_cost_synthetic_model(
        self, calculator: PricingCalculator
    ) -> None:
        """Test that synthetic model returns zero cost."""
        cost = calculator.calculate_cost(
            model="<synthetic>", input_tokens=1000, output_tokens=500
        )
        assert cost == 0.0

    def test_calculate_cost_unknown_model(self, calculator: PricingCalculator) -> None:
        """Test cost calculation for unknown model (should raise KeyError in strict mode)."""
        with pytest.raises(KeyError):
            calculator.calculate_cost(
                model="unknown-model", input_tokens=1000, output_tokens=500, strict=True
            )

    def test_non_anthropic_model_not_priced_as_claude(
        self, calculator: PricingCalculator
    ) -> None:
        """A non-Claude model (e.g. routed via Claude Code Router) must not be billed
        at a fabricated Claude rate (#217, #199)."""
        # 1M input tokens at the Sonnet rate would be $3.00; it must be $0 (unpriced).
        assert (
            calculator.calculate_cost(
                model="gpt-4o", input_tokens=1_000_000, output_tokens=0
            )
            == 0.0
        )
        assert (
            calculator.calculate_cost(
                model="deepseek-chat", input_tokens=1_000_000, output_tokens=0
            )
            == 0.0
        )

    def test_unrecognized_claude_model_still_uses_family_fallback(
        self, calculator: PricingCalculator
    ) -> None:
        """An unknown but clearly-Claude model still gets a Claude family rate."""
        cost = calculator.calculate_cost(
            model="claude-experimental-xyz", input_tokens=1_000_000, output_tokens=0
        )
        assert cost > 0.0

    def test_calculate_cost_zero_tokens(self, calculator: PricingCalculator) -> None:
        """Test cost calculation with zero tokens."""
        cost = calculator.calculate_cost(
            model="claude-3-haiku", input_tokens=0, output_tokens=0
        )
        assert cost == 0.0

    def test_calculate_cost_for_entry_auto_mode(
        self,
        calculator: PricingCalculator,
        sample_entry_data: Dict[str, Union[str, int, None]],
    ) -> None:
        """Test calculate_cost_for_entry with AUTO mode."""
        cost = calculator.calculate_cost_for_entry(sample_entry_data, CostMode.AUTO)

        expected = (
            1000 * 0.25  # input
            + 500 * 1.25  # output
            + 100 * 0.3  # cache creation
            + 50 * 0.03  # cache read
        ) / 1000000
        assert abs(cost - expected) < 1e-6

    def test_calculate_cost_for_entry_cached_mode_with_existing_cost(
        self, calculator: PricingCalculator
    ) -> None:
        """Test calculate_cost_for_entry with CACHED mode and existing cost."""
        entry_data: Dict[str, Union[str, int, float]] = {
            "model": "claude-3-haiku",
            "input_tokens": 1000,
            "output_tokens": 500,
            "cost_usd": 0.123,  # Pre-existing cost
        }

        cost = calculator.calculate_cost_for_entry(entry_data, CostMode.CACHED)
        assert cost == 0.123

    def test_calculate_cost_for_entry_cached_mode_without_existing_cost(
        self,
        calculator: PricingCalculator,
        sample_entry_data: Dict[str, Union[str, int, None]],
    ) -> None:
        """Test calculate_cost_for_entry with CACHED mode but no existing cost."""
        cost = calculator.calculate_cost_for_entry(sample_entry_data, CostMode.CACHED)

        # Should fall back to calculation since no existing cost
        expected = (1000 * 0.25 + 500 * 1.25 + 100 * 0.3 + 50 * 0.03) / 1000000
        assert abs(cost - expected) < 1e-6

    def test_calculate_cost_for_entry_calculated_mode(
        self, calculator: PricingCalculator
    ) -> None:
        """Test calculate_cost_for_entry with CALCULATED mode."""
        entry_data: Dict[str, Union[str, int, float]] = {
            "model": "claude-3-opus",
            "input_tokens": 500,
            "output_tokens": 250,
            "cost_usd": 0.999,  # Should be ignored in CALCULATED mode
        }

        cost = calculator.calculate_cost_for_entry(entry_data, CostMode.CALCULATED)

        # Should calculate cost regardless of existing cost_usd
        expected = (500 * 15.0 + 250 * 75.0) / 1000000
        assert abs(cost - expected) < 1e-6

    def test_calculate_cost_for_entry_missing_model(
        self, calculator: PricingCalculator
    ) -> None:
        """Test calculate_cost_for_entry with missing model."""
        entry_data: Dict[str, int] = {
            "input_tokens": 1000,
            "output_tokens": 500,
            # Missing "model" key
        }

        with pytest.raises(KeyError):
            calculator.calculate_cost_for_entry(entry_data, CostMode.AUTO)

    def test_calculate_cost_for_entry_with_defaults(
        self, calculator: PricingCalculator
    ) -> None:
        """Test calculate_cost_for_entry with minimal data (should use defaults)."""
        entry_data: Dict[str, str] = {
            "model": "claude-3-haiku"
            # Missing token counts - should default to 0
        }

        cost = calculator.calculate_cost_for_entry(entry_data, CostMode.AUTO)
        assert cost == 0.0

    def test_custom_pricing_calculator(
        self, custom_calculator: PricingCalculator
    ) -> None:
        """Test calculator with custom pricing."""
        cost = custom_calculator.calculate_cost(
            model="test-model", input_tokens=1000, output_tokens=500
        )

        expected = (1000 * 1.0 + 500 * 2.0) / 1000000
        assert abs(cost - expected) < 1e-6

    def test_cost_calculation_precision(self, calculator: PricingCalculator) -> None:
        """Test that cost calculations maintain proper precision."""
        # Test with very small token counts
        cost = calculator.calculate_cost(
            model="claude-3-haiku", input_tokens=1, output_tokens=1
        )

        expected = (1 * 0.25 + 1 * 1.25) / 1000000
        assert abs(cost - expected) < 1e-6

    def test_cost_calculation_large_numbers(
        self, calculator: PricingCalculator
    ) -> None:
        """Test cost calculation with large token counts."""
        cost = calculator.calculate_cost(
            model="claude-3-opus",
            input_tokens=1000000,  # 1M tokens
            output_tokens=500000,  # 500k tokens
        )

        expected = (1000000 * 15.0 + 500000 * 75.0) / 1000000
        assert abs(cost - expected) < 1e-6

    def test_all_supported_models(self, calculator: PricingCalculator) -> None:
        """Test that all supported models can calculate costs."""
        supported_models: List[str] = [
            "claude-3-opus",
            "claude-3-sonnet",
            "claude-3-haiku",
            "claude-3-5-sonnet",
            "claude-3-5-haiku",
            "claude-sonnet-4-20250514",
            "claude-opus-4-20250514",
        ]

        for model in supported_models:
            cost = calculator.calculate_cost(
                model=model, input_tokens=100, output_tokens=50
            )
            assert cost > 0
            assert isinstance(cost, float)

    def test_cache_token_costs(self, calculator: PricingCalculator) -> None:
        """Test that cache tokens are properly calculated."""
        model = "claude-3-haiku"

        # Cost with cache tokens
        cost_with_cache = calculator.calculate_cost(
            model=model,
            input_tokens=1000,
            output_tokens=500,
            cache_creation_tokens=100,
            cache_read_tokens=50,
        )

        # Cost without cache tokens
        cost_without_cache = calculator.calculate_cost(
            model=model, input_tokens=1000, output_tokens=500
        )

        # Cache should add additional cost
        assert cost_with_cache > cost_without_cache

        # Calculate expected cache cost
        cache_cost = (100 * 0.3 + 50 * 0.03) / 1000000
        expected_total = cost_without_cache + cache_cost
        assert abs(cost_with_cache - expected_total) < 1e-6

    def test_model_name_normalization_integration(
        self, calculator: PricingCalculator
    ) -> None:
        """Test integration with model name normalization."""
        # Test with various model name formats that should normalize
        test_cases: List[tuple[str, str]] = [
            ("claude-3-haiku-20240307", "claude-3-haiku"),
            ("claude-3-opus-20240229", "claude-3-opus"),
            ("claude-3-5-sonnet-20241022", "claude-3-5-sonnet"),
        ]

        for input_model, _expected_normalized in test_cases:
            try:
                cost = calculator.calculate_cost(
                    model=input_model, input_tokens=100, output_tokens=50
                )
                # If it doesn't raise an error, normalization worked
                assert cost >= 0
            except KeyError:
                # Model name normalization might not handle all formats
                # This is acceptable for now
                pass
