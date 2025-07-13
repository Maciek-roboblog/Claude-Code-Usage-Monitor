import time
from dataclasses import dataclass
from functools import lru_cache
from statistics import quantiles
from typing import Any, Callable, Dict, List, Optional, Sequence


@dataclass(frozen=True)
class P90Config:
    common_limits: Sequence[int]
    limit_threshold: float
    default_min_limit: int
    cache_ttl_seconds: int


def _did_hit_limit(tokens: int, common_limits: Sequence[int], threshold: float) -> bool:
    """
    Determine if the token count meets or exceeds any of the configured limits scaled by the threshold.
    
    Returns:
        True if the token count is greater than or equal to any limit multiplied by the threshold; otherwise, False.
    """
    return any(tokens >= limit * threshold for limit in common_limits)


def _extract_sessions(
    blocks: Sequence[Dict[str, Any]], filter_fn: Callable[[Dict[str, Any]], bool]
) -> List[int]:
    """
    Extracts the `totalTokens` values from blocks that satisfy a filter function and have a positive token count.
    
    Parameters:
        blocks: A sequence of session block dictionaries.
        filter_fn: A callable that returns True for blocks to include.
    
    Returns:
        A list of `totalTokens` integers from blocks passing the filter and with `totalTokens` > 0.
    """
    return [
        block["totalTokens"]
        for block in blocks
        if filter_fn(block) and block.get("totalTokens", 0) > 0
    ]


def _calculate_p90_from_blocks(blocks: Sequence[Dict[str, Any]], cfg: P90Config) -> int:
    """
    Compute the 90th percentile token limit from session blocks using the provided configuration.
    
    Filters blocks to sessions that are neither gaps nor active and that have hit a configured token limit threshold. If no such sessions exist, considers all non-gap, non-active sessions. Returns the greater of the computed 90th percentile token count and the configured default minimum limit.
    
    Parameters:
        blocks (Sequence[Dict[str, Any]]): List of session block dictionaries to analyze.
        cfg (P90Config): Configuration specifying token limits, threshold, and minimum limit.
    
    Returns:
        int: The computed 90th percentile token limit, or the default minimum limit if no sessions are found.
    """
    hits = _extract_sessions(
        blocks,
        lambda b: (
            not b.get("isGap", False)
            and not b.get("isActive", False)
            and _did_hit_limit(
                b.get("totalTokens", 0), cfg.common_limits, cfg.limit_threshold
            )
        ),
    )
    if not hits:
        hits = _extract_sessions(
            blocks, lambda b: not b.get("isGap", False) and not b.get("isActive", False)
        )
    if not hits:
        return cfg.default_min_limit
    q = quantiles(hits, n=10)[8]
    return max(int(q), cfg.default_min_limit)


class P90Calculator:
    def __init__(self, config: Optional[P90Config] = None):
        """
        Initialize a P90Calculator instance with the specified configuration.
        
        If no configuration is provided, uses default token limits, threshold, minimum limit, and cache TTL values.
        """
        if config is None:
            from claude_monitor.core.plans import (
                COMMON_TOKEN_LIMITS,
                DEFAULT_TOKEN_LIMIT,
                LIMIT_DETECTION_THRESHOLD,
            )

            config = P90Config(
                common_limits=COMMON_TOKEN_LIMITS,
                limit_threshold=LIMIT_DETECTION_THRESHOLD,
                default_min_limit=DEFAULT_TOKEN_LIMIT,
                cache_ttl_seconds=60 * 60,
            )
        self._cfg = config

    @lru_cache(maxsize=1)
    def _cached_calc(self, key: int, blocks_tuple: tuple) -> int:
        """
        Compute the P90 token limit from a tuple of session block data, using the stored configuration.
        
        Parameters:
            key (int): Cache key, typically derived from the current time and cache TTL.
            blocks_tuple (tuple): Tuple of (isGap, isActive, totalTokens) representing session blocks.
        
        Returns:
            int: The calculated 90th percentile token limit.
        """
        blocks = [
            {"isGap": g, "isActive": a, "totalTokens": t} for g, a, t in blocks_tuple
        ]
        return _calculate_p90_from_blocks(blocks, self._cfg)

    def calculate_p90_limit(
        self,
        blocks: Optional[List[Dict[str, Any]]] = None,
        use_cache: bool = True,
    ) -> Optional[int]:
        """
        Compute the 90th percentile (P90) token usage limit from a list of session blocks, with optional caching.
        
        Parameters:
            blocks (Optional[List[Dict[str, Any]]]): List of session block dictionaries to analyze. If None or empty, returns None.
            use_cache (bool): Whether to use cached results based on block content and a time-based expiration key.
        
        Returns:
            Optional[int]: The computed P90 token limit, or None if no blocks are provided.
        """
        if not blocks:
            return None
        if not use_cache:
            return _calculate_p90_from_blocks(blocks, self._cfg)
        ttl = self._cfg.cache_ttl_seconds
        expire_key = int(time.time() // ttl)
        blocks_tuple = tuple(
            (
                b.get("isGap", False),
                b.get("isActive", False),
                b.get("totalTokens", 0),
            )
            for b in blocks
        )
        return self._cached_calc(expire_key, blocks_tuple)
