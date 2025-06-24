"""
Simplified Burn Rate Calculator

Basic calculator for token consumption rates and usage projections.
"""

from datetime import datetime, timezone
from typing import Optional

from usage_analyzer.models.data_structures import SessionBlock, BurnRate, UsageProjection


class BurnRateCalculator:
    """Calculates burn rates and usage projections for session blocks."""
    
    def calculate_burn_rate(self, block: SessionBlock) -> Optional[BurnRate]:
        """Calculate current consumption rate for active blocks."""
        if not block.is_active or block.duration_minutes < 1:
            return None
        
        # Use only input + output tokens for burn rate calculation
        total_tokens = block.token_counts.input_tokens + block.token_counts.output_tokens
        if total_tokens == 0:
            return None
        
        # Calculate rates
        tokens_per_minute = total_tokens / block.duration_minutes
        cost_per_hour = (block.cost_usd / block.duration_minutes) * 60 if block.duration_minutes > 0 else 0
        
        return BurnRate(
            tokens_per_minute=tokens_per_minute,
            cost_per_hour=cost_per_hour
        )
    
    def project_block_usage(self, block: SessionBlock) -> Optional[UsageProjection]:
        """Project total usage if current rate continues."""
        burn_rate = self.calculate_burn_rate(block)
        if not burn_rate:
            return None
        
        # Calculate remaining time
        now = datetime.now(timezone.utc)
        remaining_seconds = (block.end_time - now).total_seconds()
        
        if remaining_seconds <= 0:
            return None
        
        remaining_minutes = remaining_seconds / 60
        remaining_hours = remaining_minutes / 60
        
        # Current usage (input + output tokens only)
        current_tokens = block.token_counts.input_tokens + block.token_counts.output_tokens
        current_cost = block.cost_usd
        
        # Projected usage
        projected_additional_tokens = burn_rate.tokens_per_minute * remaining_minutes
        projected_total_tokens = current_tokens + projected_additional_tokens
        
        projected_additional_cost = burn_rate.cost_per_hour * remaining_hours
        projected_total_cost = current_cost + projected_additional_cost
        
        return UsageProjection(
            projected_total_tokens=int(projected_total_tokens),
            projected_total_cost=projected_total_cost,
            remaining_minutes=int(remaining_minutes)
        )