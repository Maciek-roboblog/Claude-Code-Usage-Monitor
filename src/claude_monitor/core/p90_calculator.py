import time
from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache
from statistics import quantiles
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class P90Config:
    common_limits: Sequence[int]
    limit_threshold: float
    default_min_limit: int
    cache_ttl_seconds: int


def _did_hit_limit(tokens: int, common_limits: Sequence[int], threshold: float) -> bool:
    return any(tokens >= limit * threshold for limit in common_limits)


def _extract_sessions(
    blocks: Sequence[Dict[str, Any]], filter_fn: Callable[[Dict[str, Any]], bool]
) -> List[int]:
    return [
        block["totalTokens"]
        for block in blocks
        if filter_fn(block) and block.get("totalTokens", 0) > 0
    ]


def _calculate_p90_from_blocks(blocks: Sequence[Dict[str, Any]], cfg: P90Config) -> int:
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
    q: float = quantiles(hits, n=10)[8]
    return max(int(q), cfg.default_min_limit)


class P90Calculator:
    def __init__(self, config: Optional[P90Config] = None) -> None:
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
        self._cfg: P90Config = config

    @lru_cache(maxsize=1)
    def _cached_calc(
        self, key: int, blocks_tuple: Tuple[Tuple[bool, bool, int], ...]
    ) -> int:
        blocks: List[Dict[str, Any]] = [
            {"isGap": g, "isActive": a, "totalTokens": t} for g, a, t in blocks_tuple
        ]
        return _calculate_p90_from_blocks(blocks, self._cfg)

    def calculate_p90_limit(
        self,
        blocks: Optional[List[Dict[str, Any]]] = None,
        use_cache: bool = True,
    ) -> Optional[int]:
        if not blocks:
            return None
        if not use_cache:
            return _calculate_p90_from_blocks(blocks, self._cfg)
        ttl: int = self._cfg.cache_ttl_seconds
        expire_key: int = int(time.time() // ttl)
        blocks_tuple: Tuple[Tuple[bool, bool, int], ...] = tuple(
            (
                b.get("isGap", False),
                b.get("isActive", False),
                b.get("totalTokens", 0),
            )
            for b in blocks
        )
        return self._cached_calc(expire_key, blocks_tuple)
