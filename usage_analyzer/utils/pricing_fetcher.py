"""
Simplified Claude Pricing Fetcher

Basic pricing calculation with fallback rates.
"""

from typing import Optional, Dict, Any

try:
    import litellm
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False

from usage_analyzer.models.data_structures import CostMode


class ClaudePricingFetcher:
    """Advanced pricing calculator with LiteLLM integration and mode support."""
    
    def __init__(self):
        """Initialize with LiteLLM integration and fallback pricing."""
        # Fallback pricing based on Claude Sonnet rates
        self.fallback_pricing = {
            "input_cost_per_token": 3.0e-6,    # $3.00 per 1M input tokens
            "output_cost_per_token": 15.0e-6,  # $15.00 per 1M output tokens  
            "cache_creation_input_token_cost": 3.75e-6,  # $3.75 per 1M cache creation tokens
            "cache_read_input_token_cost": 0.3e-6   # $0.30 per 1M cache read tokens
        }
        
        # Cache for LiteLLM pricing to avoid repeated API calls
        self.pricing_cache: Dict[str, Dict[str, float]] = {}
        
        # LiteLLM availability flag
        self.litellm_available = LITELLM_AVAILABLE
    
    def calculateCostForEntry(self, 
                             entry_data: Dict[str, Any], 
                             mode: CostMode) -> float:
        """Calculate cost for entry based on specified mode.
        
        Args:
            entry_data: Dictionary containing usage data with keys:
                       'model', 'input_tokens', 'output_tokens', 
                       'cache_creation_tokens', 'cache_read_tokens', 'costUSD'
            mode: Cost calculation mode (AUTO, CALCULATE, DISPLAY)
            
        Returns:
            Calculated cost in USD
        """
        model = entry_data.get('model', '')
        cost_usd = entry_data.get('costUSD') or entry_data.get('cost')
        
        # Handle different modes
        if mode == CostMode.DISPLAY:
            # Always use costUSD, show 0 if missing
            return cost_usd if cost_usd is not None else 0.0
            
        elif mode == CostMode.CALCULATE:
            # Always calculate from tokens using LiteLLM prices
            return self._calculate_from_tokens(
                model=model,
                input_tokens=entry_data.get('input_tokens', 0) or 0,
                output_tokens=entry_data.get('output_tokens', 0) or 0,
                cache_creation_tokens=entry_data.get('cache_creation_tokens', 0) or 0,
                cache_read_tokens=entry_data.get('cache_read_tokens', 0) or 0
            )
            
        else:  # CostMode.AUTO (default)
            # Use costUSD if available, otherwise calculate from tokens
            if cost_usd is not None:
                return cost_usd
            else:
                return self._calculate_from_tokens(
                    model=model,
                    input_tokens=entry_data.get('input_tokens', 0) or 0,
                    output_tokens=entry_data.get('output_tokens', 0) or 0,
                    cache_creation_tokens=entry_data.get('cache_creation_tokens', 0) or 0,
                    cache_read_tokens=entry_data.get('cache_read_tokens', 0) or 0
                )
    
    def _calculate_from_tokens(self, 
                              model: str,
                              input_tokens: int = 0, 
                              output_tokens: int = 0,
                              cache_creation_tokens: int = 0, 
                              cache_read_tokens: int = 0) -> float:
        """Calculate cost from token counts using LiteLLM or fallback pricing."""
        if model == '<synthetic>':
            return 0.0
        
        # Use model-specific pricing
        pricing = self.get_model_specific_pricing(model)
        
        # Calculate cost using the formula:
        # cost = input_tokens * input_cost_per_token +
        #        output_tokens * output_cost_per_token +
        #        cache_creation_tokens * cache_creation_cost_per_token +
        #        cache_read_tokens * cache_read_cost_per_token
        cost = (
            input_tokens * pricing.get("input_cost_per_token", 0) +
            output_tokens * pricing.get("output_cost_per_token", 0) +
            cache_creation_tokens * pricing.get("cache_creation_input_token_cost", 0) +
            cache_read_tokens * pricing.get("cache_read_input_token_cost", 0)
        )
        
        return round(cost, 6)  # Round to 6 decimal places
    
    def _get_litellm_pricing(self, model: str) -> Optional[Dict[str, float]]:
        """Get pricing information from LiteLLM with caching."""
        if not self.litellm_available:
            return None
            
        # Check cache first
        if model in self.pricing_cache:
            return self.pricing_cache[model]
        
        try:
            # Get pricing from LiteLLM
            model_info = litellm.get_model_info(model)
            if not model_info:
                return None
                
            pricing = {
                "input_cost_per_token": model_info.get("input_cost_per_token", 0),
                "output_cost_per_token": model_info.get("output_cost_per_token", 0),
                "cache_creation_input_token_cost": model_info.get("cache_creation_input_token_cost", 0),
                "cache_read_input_token_cost": model_info.get("cache_read_input_token_cost", 0)
            }
            
            # Cache the result
            self.pricing_cache[model] = pricing
            return pricing
            
        except Exception:
            # If LiteLLM fails, return None to fall back to default pricing
            return None
    
    def get_model_specific_pricing(self, model: str) -> Dict[str, float]:
        """Get model-specific pricing, with fallbacks for known Claude models."""
        # Try LiteLLM first
        pricing = self._get_litellm_pricing(model)
        if pricing:
            return pricing
        
        # Fallback to known Claude model pricing
        if 'opus' in model.lower():
            return {
                "input_cost_per_token": 15.0e-6,    # $15.00 per 1M input tokens
                "output_cost_per_token": 75.0e-6,   # $75.00 per 1M output tokens
                "cache_creation_input_token_cost": 18.75e-6,  # $18.75 per 1M cache creation tokens
                "cache_read_input_token_cost": 1.5e-6   # $1.50 per 1M cache read tokens
            }
        elif 'sonnet' in model.lower():
            return {
                "input_cost_per_token": 3.0e-6,     # $3.00 per 1M input tokens
                "output_cost_per_token": 15.0e-6,   # $15.00 per 1M output tokens
                "cache_creation_input_token_cost": 3.75e-6,  # $3.75 per 1M cache creation tokens
                "cache_read_input_token_cost": 0.3e-6   # $0.30 per 1M cache read tokens
            }
        elif 'haiku' in model.lower():
            return {
                "input_cost_per_token": 0.25e-6,    # $0.25 per 1M input tokens
                "output_cost_per_token": 1.25e-6,   # $1.25 per 1M output tokens
                "cache_creation_input_token_cost": 0.3e-6,   # $0.30 per 1M cache creation tokens
                "cache_read_input_token_cost": 0.03e-6  # $0.03 per 1M cache read tokens
            }
        else:
            # Default to Sonnet pricing for unknown models
            return self.fallback_pricing
    
    def recalculate_per_model_costs(self, per_model_stats: Dict[str, Dict[str, Any]]) -> Dict[str, float]:
        """Recalculate costs per model using correct pricing for each model.
        
        Args:
            per_model_stats: Dictionary with model stats containing token counts
            
        Returns:
            Dictionary mapping model name to recalculated cost
        """
        per_model_costs = {}
        
        for model, stats in per_model_stats.items():
            # Recalculate cost using model-specific pricing
            cost = self._calculate_from_tokens(
                model=model,
                input_tokens=stats.get('input_tokens', 0),
                output_tokens=stats.get('output_tokens', 0),
                cache_creation_tokens=stats.get('cache_creation_tokens', 0),
                cache_read_tokens=stats.get('cache_read_tokens', 0)
            )
            per_model_costs[model] = cost
            
        return per_model_costs
    
    def calculate_cost(self, 
                      model: str,
                      input_tokens: int = 0, 
                      output_tokens: int = 0,
                      cache_creation_tokens: int = 0, 
                      cache_read_tokens: int = 0) -> float:
        """Legacy method for backward compatibility."""
        return self._calculate_from_tokens(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_creation_tokens=cache_creation_tokens,
            cache_read_tokens=cache_read_tokens
        )