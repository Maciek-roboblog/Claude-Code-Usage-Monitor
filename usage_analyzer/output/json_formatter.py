"""
Simplified JSON Output Formatter

Basic JSON formatting for session blocks to match response_final.json structure.
"""

import json
from typing import Any, Dict, List

from usage_analyzer.models.data_structures import SessionBlock
from usage_analyzer.core.calculator import BurnRateCalculator
from usage_analyzer.utils.pricing_fetcher import ClaudePricingFetcher


class JSONFormatter:
    """Handle JSON output generation for session blocks."""

    def __init__(self):
        """Initialize formatter."""
        self.calculator = BurnRateCalculator()
        self.pricing_fetcher = ClaudePricingFetcher()

    def format_blocks(self, blocks: List[SessionBlock]) -> str:
        """Format blocks as JSON string matching response_final.json structure."""
        output = {
            "blocks": [self._block_to_dict(block) for block in blocks]
        }
        return json.dumps(output, indent=2, default=str)

    from typing import Dict, Any

    def _calculate_total_tokens(
            self,
            per_model_stats: Dict[str, Dict[str, Any]]
    ) -> int:
        """
        Iterate over per_model_stats and compute a total token count:
        - For model names containing "opus": add 5 × (inputTokens + outputTokens)
        - For model names containing "sonnet": add (inputTokens + outputTokens)
        Returns the cumulative total.
        """
        total_tokens = 0

        for model_name, stats in per_model_stats.items():
            input_tokens = stats.get("input_tokens", 0)
            output_tokens = stats.get("output_tokens", 0)

            if "opus" in model_name:
                total_tokens += 5 * (input_tokens + output_tokens)
            elif "sonnet" in model_name:
                total_tokens += input_tokens + output_tokens

        return total_tokens

    def _block_to_dict(self, block: SessionBlock) -> Dict[str, Any]:
        """Convert a block to dictionary representation with correct per-model costs."""
        # Recalculate costs per model using correct pricing
        per_model_costs = self.pricing_fetcher.recalculate_per_model_costs(block.per_model_stats)
        corrected_total_cost = sum(per_model_costs.values())

        calculated_total_tokens = self._calculate_total_tokens(block.per_model_stats)

        result = {
            "id": block.id,
            "startTime": self._format_timestamp(block.start_time),
            "endTime": self._format_timestamp(block.end_time),
            "actualEndTime": self._format_timestamp(block.actual_end_time) if block.actual_end_time else None,
            "isActive": block.is_active,
            "isGap": block.is_gap,
            "entries": len([e for e in block.entries if (e.input_tokens > 0 or e.output_tokens > 0 or e.cache_creation_tokens > 0 or e.cache_read_tokens > 0) or e.model == '<synthetic>']),
            "tokenCounts": {
                "inputTokens": block.token_counts.input_tokens,
                "outputTokens": block.token_counts.output_tokens,
                "cacheCreationInputTokens": block.token_counts.cache_creation_tokens,
                "cacheReadInputTokens": block.token_counts.cache_read_tokens
            },
            "totalTokens": calculated_total_tokens,
            "totalTokensOld": block.token_counts.total_tokens,
            "costUSD": corrected_total_cost,  # Use corrected per-model cost
            "models": block.models,
            # TODO IMPORTANT FOR DEBUG
            # "perModelStats": self._format_per_model_stats(block.per_model_stats, per_model_costs),
            "burnRate": None,
            "projection": None
        }

        # Add burn rate and projection for active blocks
        if block.is_active:
            # Temporarily update block cost for accurate burn rate calculation
            original_cost = block.cost_usd
            block.cost_usd = corrected_total_cost

            burn_rate = self.calculator.calculate_burn_rate(block)
            if burn_rate:
                result["burnRate"] = {
                    "tokensPerMinute": burn_rate.tokens_per_minute,
                    "costPerHour": burn_rate.cost_per_hour
                }

                projection = self.calculator.project_block_usage(block)
                if projection:
                    result["projection"] = {
                        "totalTokens": projection.projected_total_tokens,
                        "totalCost": round(projection.projected_total_cost, 2),
                        "remainingMinutes": projection.remaining_minutes
                    }

            # Restore original cost
            block.cost_usd = original_cost

        return result

    def _format_per_model_stats(self, per_model_stats: Dict[str, Dict[str, Any]], per_model_costs: Dict[str, float]) -> Dict[str, Any]:
        """Format per-model statistics with corrected costs."""
        formatted_stats = {}
        
        for model, stats in per_model_stats.items():
            formatted_stats[model] = {
                "tokenCounts": {
                    "inputTokens": stats.get('input_tokens', 0),
                    "outputTokens": stats.get('output_tokens', 0),
                    "cacheCreationTokens": stats.get('cache_creation_tokens', 0),
                    "cacheReadTokens": stats.get('cache_read_tokens', 0),
                    "totalTokens": stats.get('input_tokens', 0) + stats.get('output_tokens', 0)
                },
                "costUSD": per_model_costs.get(model, 0.0),
                "entriesCount": stats.get('entries_count', 0)
            }
        
        return formatted_stats

    def _format_timestamp(self, timestamp) -> str:
        """Format datetime to match format with milliseconds precision."""
        if timestamp is None:
            return None
        # Convert to UTC if needed
        if timestamp.tzinfo is not None:
            from datetime import timezone
            utc_timestamp = timestamp.astimezone(timezone.utc).replace(tzinfo=None)
        else:
            utc_timestamp = timestamp
        
        # Format with milliseconds precision (.XXXZ)
        milliseconds = utc_timestamp.microsecond // 1000
        return utc_timestamp.strftime(f'%Y-%m-%dT%H:%M:%S.{milliseconds:03d}Z')