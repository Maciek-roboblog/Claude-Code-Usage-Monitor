"""Unified data management for monitoring - combines caching and fetching."""

import logging
import time
from typing import Any, Dict, Optional

from claude_monitor.data.analysis import analyze_usage
from claude_monitor.error_handling import report_error

logger = logging.getLogger(__name__)


class DataManager:
    """Manages data fetching and caching for monitoring."""

    def __init__(
        self,
        cache_ttl: int = 30,
        hours_back: int = 192,
        data_path: Optional[str] = None,
    ) -> None:
        """Initialize data manager with cache and fetch settings.

        Args:
            cache_ttl: Cache time-to-live in seconds
            hours_back: Hours of historical data to fetch
            data_path: Path to data directory
        """
        self.cache_ttl: int = cache_ttl
        self._cache: Optional[Dict[str, Any]] = None
        self._cache_timestamp: Optional[float] = None

        self.hours_back: int = hours_back
        self.data_path: Optional[str] = data_path
        self._last_error: Optional[str] = None
        self._last_successful_fetch: Optional[float] = None

    def get_data(self, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """Get monitoring data with caching and error handling.

        Args:
            force_refresh: Force refresh ignoring cache

        Returns:
            Usage data dictionary or None if fetch fails
        """
        if not force_refresh and self._is_cache_valid():
            cache_age: float = time.time() - self._cache_timestamp  # type: ignore
            logger.debug(f"Using cached data (age: {cache_age:.1f}s)")
            return self._cache

        max_retries: int = 3
        for attempt in range(max_retries):
            try:
                logger.debug(
                    f"Fetching fresh usage data (attempt {attempt + 1}/{max_retries})"
                )
                data: Optional[Dict[str, Any]] = analyze_usage(
                    hours_back=self.hours_back,
                    quick_start=False,
                    use_cache=False,
                    data_path=self.data_path,
                )

                if data is not None:
                    self._set_cache(data)
                    self._last_successful_fetch = time.time()
                    self._last_error = None
                    return data

                logger.warning("No data returned from analyze_usage")
                break

            except (FileNotFoundError, PermissionError, OSError) as e:
                logger.exception(f"Data access error (attempt {attempt + 1}): {e}")
                self._last_error = str(e)
                report_error(
                    exception=e, component="data_manager", context_name="access_error"
                )
                if attempt < max_retries - 1:
                    time.sleep(0.1 * (2**attempt))
                    continue

            except (ValueError, TypeError, KeyError) as e:
                logger.exception(f"Data format error: {e}")
                self._last_error = str(e)
                report_error(
                    exception=e, component="data_manager", context_name="format_error"
                )
                break

            except Exception as e:
                logger.exception(f"Unexpected error (attempt {attempt + 1}): {e}")
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

    def _set_cache(self, data: Dict[str, Any]) -> None:
        """Set cache with current timestamp."""
        self._cache = data
        self._cache_timestamp = time.time()

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
