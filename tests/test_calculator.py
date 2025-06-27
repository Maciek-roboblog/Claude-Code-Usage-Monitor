"""Tests for BurnRateCalculator.calculate_burn_rate method."""

from datetime import datetime, timezone, timedelta
from usage_analyzer.core.calculator import BurnRateCalculator
from usage_analyzer.models.data_structures import SessionBlock, TokenCounts


class TestBurnRateCalculator:
    """Test the BurnRateCalculator.calculate_burn_rate method."""
    
    def setup_method(self):
        self.calculator = BurnRateCalculator()
        self.base_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    def create_session_block(self, input_tokens, output_tokens, duration_minutes, cost_usd=1.0, is_active=True):
        """Create test session block. Cache tokens are always ignored in calculations."""
        return SessionBlock(
            id="test-session",
            start_time=self.base_time,
            end_time=self.base_time + timedelta(hours=5),
            actual_end_time=self.base_time + timedelta(minutes=duration_minutes),
            is_active=is_active,
            token_counts=TokenCounts(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_creation_tokens=999,  # Should be ignored
                cache_read_tokens=999       # Should be ignored
            ),
            cost_usd=cost_usd
        )
    
    def test_normal_burn_rate_calculation(self):
        """Test basic burn rate calculation: 1500 tokens in 30 minutes = 50 tokens/min."""
        block = self.create_session_block(
            input_tokens=1000, 
            output_tokens=500, 
            duration_minutes=30, 
            cost_usd=1.50
        )
        
        result = self.calculator.calculate_burn_rate(block)
        
        assert result.tokens_per_minute == 50.0  # (1000 + 500) / 30
        assert result.cost_per_hour == 3.0       # 1.50 / 30 * 60
    
    def test_ignores_cache_tokens(self):
        """Test that cache tokens are ignored - only input + output tokens count."""
        block = self.create_session_block(
            input_tokens=600, 
            output_tokens=400, 
            duration_minutes=20
        )
        # Note: cache tokens set to 999 each in helper, but should be ignored
        
        result = self.calculator.calculate_burn_rate(block)
        
        assert result.tokens_per_minute == 50.0  # (600 + 400) / 20, not (600 + 400 + 999 + 999)
