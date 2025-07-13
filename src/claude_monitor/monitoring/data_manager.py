"""Unified data management for monitoring - combines caching and fetching.

Provides sophisticated type-safe data pipeline management with intelligent caching,
error handling, and memory optimization for Claude usage monitoring.
"""

import logging
import time
from typing import Any, Dict, List, Optional, TypedDict, Union

from claude_monitor.data.analysis import analyze_usage
from claude_monitor.error_handling import report_error

logger = logging.getLogger(__name__)


class AnalysisMetadata(TypedDict):
    """Type-safe structure for analysis metadata."""

    generated_at: str
    hours_analyzed: Union[int, str]
    entries_processed: int
    blocks_created: int
    limits_detected: int
    load_time_seconds: float
    transform_time_seconds: float
    cache_used: bool
    quick_start: bool


class TokenCountsDict(TypedDict):
    """Type-safe structure for token count data."""

    inputTokens: int
    outputTokens: int
    cacheCreationInputTokens: int
    cacheReadInputTokens: int


class BurnRateDict(TypedDict):
    """Type-safe structure for burn rate data."""

    tokensPerMinute: float
    costPerHour: float


class ProjectionDict(TypedDict):
    """Type-safe structure for usage projection data."""

    totalTokens: int
    totalCost: float
    remainingMinutes: float


class LimitMessageDict(TypedDict):
    """Type-safe structure for limit message data."""

    type: str
    timestamp: str
    content: str
    reset_time: Optional[str]


class BlockEntryDict(TypedDict):
    """Type-safe structure for block entry data."""

    timestamp: str
    inputTokens: int
    outputTokens: int
    cacheCreationTokens: int
    cacheReadInputTokens: int
    costUSD: float
    model: str
    messageId: str
    requestId: str


class SessionBlockDict(TypedDict, total=False):
    """Type-safe structure for session block data with optional fields."""

    # Required fields
    id: str
    isActive: bool
    isGap: bool
    startTime: str
    endTime: str
    actualEndTime: Optional[str]
    tokenCounts: TokenCountsDict
    totalTokens: int
    costUSD: float
    models: List[str]
    perModelStats: Dict[str, Dict[str, Union[int, float]]]
    sentMessagesCount: int
    durationMinutes: float
    entries: List[BlockEntryDict]
    entries_count: int

    # Optional fields (total=False makes these not required)
    burnRate: BurnRateDict
    projection: ProjectionDict
    limitMessages: List[LimitMessageDict]


class AnalysisResult(TypedDict):
    """Type-safe structure for complete analysis result."""

    blocks: List[SessionBlockDict]
    metadata: AnalysisMetadata
    entries_count: int
    total_tokens: int
    total_cost: float


# Type alias for cache data
CacheData = AnalysisResult


class CacheValidationError(Exception):
    """Raised when cached data fails validation."""

    pass


class DataPipelineError(Exception):
    """Raised when data pipeline operations fail."""

    pass


class DataManager:
    """Type-safe data management for monitoring with advanced caching and error handling.

    Provides sophisticated data pipeline management with:
    - Type-safe caching with validation
    - Intelligent error handling and retry logic
    - Memory-optimized data structures
    - Comprehensive logging and metrics
    """

    def __init__(
        self,
        cache_ttl: int = 30,
        hours_back: int = 96,
        data_path: Optional[str] = None,
        enable_cache_validation: bool = True,
    ) -> None:
        """Initialize data manager with advanced cache and fetch settings.

        Args:
            cache_ttl: Cache time-to-live in seconds
            hours_back: Hours of historical data to fetch
            data_path: Path to data directory
            enable_cache_validation: Whether to validate cached data structure
        """
        self.cache_ttl: int = cache_ttl
        self._cache: Optional[CacheData] = None
        self._cache_timestamp: Optional[float] = None
        self._enable_cache_validation: bool = enable_cache_validation

        self.hours_back: int = hours_back
        self.data_path: Optional[str] = data_path
        self._last_error: Optional[str] = None
        self._last_successful_fetch: Optional[float] = None
        self._cache_hits: int = 0
        self._cache_misses: int = 0
        self._validation_failures: int = 0

    def get_data(self, force_refresh: bool = False) -> Optional[AnalysisResult]:
        """Get monitoring data with type-safe caching and comprehensive error handling.

        Args:
            force_refresh: Force refresh ignoring cache

        Returns:
            Type-safe analysis result or None if fetch fails

        Raises:
            DataPipelineError: When data pipeline operations fail
            CacheValidationError: When cached data fails validation
        """
        if not force_refresh and self._is_cache_valid():
            cache_age = time.time() - (self._cache_timestamp or 0)
            logger.debug(
                f"Using cached data (age: {cache_age:.1f}s, hits: {self._cache_hits}, "
                f"misses: {self._cache_misses})"
            )

            if self._enable_cache_validation and self._cache is not None:
                try:
                    self._validate_cache_data(self._cache)
                    self._cache_hits += 1
                    return self._cache
                except CacheValidationError as e:
                    logger.warning(f"Cache validation failed: {e}")
                    self._validation_failures += 1
                    self.invalidate_cache()
                    # Fall through to fresh fetch
            else:
                self._cache_hits += 1
                return self._cache

        self._cache_misses += 1

        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.debug(
                    f"Fetching fresh usage data (attempt {attempt + 1}/{max_retries})"
                )
                raw_data = analyze_usage(
                    hours_back=self.hours_back,
                    quick_start=True,
                    use_cache=False,
                    data_path=self.data_path,
                )

                # Type-safe data processing
                data = self._process_analysis_result(raw_data)

                if data is not None:
                    try:
                        self._set_cache(data)
                        self._last_successful_fetch = time.time()
                        self._last_error = None
                        logger.debug(
                            f"Successfully fetched and cached {len(data['blocks'])} blocks, "
                            f"{data['entries_count']} entries"
                        )
                        return data
                    except (CacheValidationError, DataPipelineError) as e:
                        logger.error(f"Data processing failed: {e}")
                        self._last_error = str(e)
                        report_error(
                            exception=e,
                            component="data_manager",
                            context_name="processing_error",
                        )
                        break

                logger.warning("No data returned from analyze_usage")
                break

            except (FileNotFoundError, PermissionError, OSError) as e:
                logger.error(f"Data access error (attempt {attempt + 1}): {e}")
                self._last_error = str(e)
                report_error(
                    exception=e, component="data_manager", context_name="access_error"
                )
                if attempt < max_retries - 1:
                    time.sleep(0.1 * (2**attempt))
                    continue

            except (ValueError, TypeError, KeyError) as e:
                logger.error(f"Data format error: {e}")
                self._last_error = str(e)
                report_error(
                    exception=e, component="data_manager", context_name="format_error"
                )
                break

            except Exception as e:
                logger.error(f"Unexpected error (attempt {attempt + 1}): {e}")
                self._last_error = str(e)
                report_error(
                    exception=e,
                    component="data_manager",
                    context_name="unexpected_error",
                )
                if attempt < max_retries - 1:
                    time.sleep(0.1 * (2**attempt))
                    continue
                break

        if self._is_cache_valid():
            logger.info("Using cached data due to fetch error")
            return self._cache

        logger.error("Failed to get usage data - no cache fallback available")
        return None

    def invalidate_cache(self) -> None:
        """Invalidate the cache."""
        self._cache = None
        self._cache_timestamp = None
        logger.debug("Cache invalidated")

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if self._cache is None or self._cache_timestamp is None:
            return False

        cache_age = time.time() - self._cache_timestamp
        return cache_age <= self.cache_ttl

    def _set_cache(self, data: AnalysisResult) -> None:
        """Set cache with current timestamp and optional validation.

        Args:
            data: Type-safe analysis result to cache

        Raises:
            CacheValidationError: If data validation fails
        """
        if self._enable_cache_validation:
            self._validate_cache_data(data)

        self._cache = data
        self._cache_timestamp = time.time()

        # Log cache metrics
        cache_size_mb = self._estimate_cache_size_mb(data)
        logger.debug(
            f"Cache updated: {len(data['blocks'])} blocks, "
            f"~{cache_size_mb:.2f}MB, TTL: {self.cache_ttl}s"
        )

    @property
    def cache_age(self) -> float:
        """Get age of cached data in seconds."""
        if self._cache_timestamp is None:
            return float("inf")
        return time.time() - self._cache_timestamp

    @property
    def last_error(self) -> Optional[str]:
        """Get last error message."""
        return self._last_error

    @property
    def last_successful_fetch_time(self) -> Optional[float]:
        """Get timestamp of last successful fetch."""
        return self._last_successful_fetch

    @property
    def cache_metrics(self) -> Dict[str, Union[int, float]]:
        """Get comprehensive cache performance metrics."""
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / total_requests if total_requests > 0 else 0.0

        return {
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate": hit_rate,
            "validation_failures": self._validation_failures,
            "cache_age_seconds": self.cache_age,
            "cache_valid": self._is_cache_valid(),
            "estimated_size_mb": (
                self._estimate_cache_size_mb(self._cache)
                if self._cache is not None
                else 0.0
            ),
        }

    def _validate_cache_data(self, data: AnalysisResult) -> None:
        """Validate cached data structure for type safety.

        Args:
            data: Analysis result to validate

        Raises:
            CacheValidationError: If validation fails
        """
        try:
            # Validate top-level structure
            if not isinstance(data, dict):
                raise CacheValidationError("Cache data is not a dictionary")

            required_keys = {
                "blocks",
                "metadata",
                "entries_count",
                "total_tokens",
                "total_cost",
            }
            if not required_keys.issubset(data.keys()):
                missing = required_keys - data.keys()
                raise CacheValidationError(f"Missing required keys: {missing}")

            # Validate blocks structure
            blocks = data.get("blocks")
            if not isinstance(blocks, list):
                raise CacheValidationError("Blocks must be a list")

            # Validate metadata structure
            metadata = data.get("metadata")
            if not isinstance(metadata, dict):
                raise CacheValidationError("Metadata must be a dictionary")

            # Validate numeric fields
            if not isinstance(data.get("entries_count"), int):
                raise CacheValidationError("entries_count must be an integer")

            if not isinstance(data.get("total_tokens"), int):
                raise CacheValidationError("total_tokens must be an integer")

            if not isinstance(data.get("total_cost"), (int, float)):
                raise CacheValidationError("total_cost must be numeric")

        except (KeyError, TypeError, AttributeError) as e:
            raise CacheValidationError(f"Cache validation failed: {e}") from e

    def _process_analysis_result(
        self, raw_data: Dict[str, Any]
    ) -> Optional[AnalysisResult]:
        """Process raw analysis data into type-safe structure.

        Args:
            raw_data: Raw data from analyze_usage function

        Returns:
            Type-safe analysis result or None if processing fails

        Raises:
            DataPipelineError: If data processing fails
        """
        try:
            # Validate and cast the raw data to our typed structure
            # This is where we'd implement any necessary data transformations
            if not isinstance(raw_data, dict):
                raise DataPipelineError("Raw data is not a dictionary")

            # For now, we assume the analyze_usage function returns correctly structured data
            # In a more sophisticated implementation, we'd perform detailed validation and transformation
            return raw_data  # type: ignore[return-value]

        except (KeyError, TypeError, ValueError) as e:
            raise DataPipelineError(f"Failed to process analysis result: {e}") from e

    def _estimate_cache_size_mb(self, data: Optional[AnalysisResult]) -> float:
        """Estimate cache size in megabytes for memory monitoring.

        Args:
            data: Cached analysis result

        Returns:
            Estimated size in megabytes
        """
        if data is None:
            return 0.0

        # Rough estimation based on data structure
        try:
            blocks_count = len(data.get("blocks", []))
            entries_count = data.get("entries_count", 0)

            # Estimate based on typical sizes
            # Each block: ~1KB, each entry: ~200 bytes, metadata: ~500 bytes
            estimated_bytes = (blocks_count * 1024) + (entries_count * 200) + 500
            return estimated_bytes / (1024 * 1024)  # Convert to MB

        except (TypeError, AttributeError):
            return 0.0
