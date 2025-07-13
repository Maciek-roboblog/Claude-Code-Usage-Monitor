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
        self, cache_ttl: int = 30, hours_back: int = 96, data_path: Optional[str] = None
    ):
        """
        Initializes the DataManager with cache duration, historical data range, and optional data directory.
        
        Parameters:
            cache_ttl (int): Time-to-live for cached data in seconds.
            hours_back (int): Number of hours of historical data to retrieve when fetching.
            data_path (Optional[str]): Optional path to the directory containing data files.
        """
        self.cache_ttl = cache_ttl
        self._cache: Optional[Any] = None
        self._cache_timestamp: Optional[float] = None

        self.hours_back = hours_back
        self.data_path = data_path
        self._last_error: Optional[str] = None
        self._last_successful_fetch: Optional[float] = None

    def get_data(self, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """
        Retrieve monitoring usage data, using cached data when valid and handling errors with retries.
        
        If `force_refresh` is False and the cache is valid, returns cached data. Otherwise, attempts to fetch fresh data up to three times, handling file access and data format errors. Falls back to cached data if available when fetching fails; returns None if no data can be retrieved.
        
        Parameters:
            force_refresh (bool): If True, bypasses the cache and forces a fresh data fetch.
        
        Returns:
            Optional[Dict[str, Any]]: Usage data dictionary if available, otherwise None.
        """
        if not force_refresh and self._is_cache_valid():
            cache_age = time.time() - self._cache_timestamp
            logger.debug(f"Using cached data (age: {cache_age:.1f}s)")
            return self._cache

        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.debug(
                    f"Fetching fresh usage data (attempt {attempt + 1}/{max_retries})"
                )
                data = analyze_usage(
                    hours_back=self.hours_back,
                    quick_start=True,
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
        """
        Clears the cached data and resets the cache timestamp.
        """
        self._cache = None
        self._cache_timestamp = None
        logger.debug("Cache invalidated")

    def _is_cache_valid(self) -> bool:
        """
        Determine whether the cached data exists and is within the configured time-to-live period.
        
        Returns:
            bool: True if the cache is present and not expired; otherwise, False.
        """
        if self._cache is None or self._cache_timestamp is None:
            return False

        cache_age = time.time() - self._cache_timestamp
        return cache_age <= self.cache_ttl

    def _set_cache(self, data: Any) -> None:
        """
        Store the provided data in the cache and update the cache timestamp to the current time.
        """
        self._cache = data
        self._cache_timestamp = time.time()

    @property
    def cache_age(self) -> float:
        """
        Return the age of the cached data in seconds.
        
        Returns:
            float: Number of seconds since the cache was last updated, or infinity if no cache exists.
        """
        if self._cache_timestamp is None:
            return float("inf")
        return time.time() - self._cache_timestamp

    @property
    def last_error(self) -> Optional[str]:
        """
        Returns the last error message encountered during data fetching, or None if no error has occurred.
        """
        return self._last_error

    @property
    def last_successful_fetch_time(self) -> Optional[float]:
        """
        Return the timestamp of the last successful data fetch.
        
        Returns:
            float or None: Unix timestamp of the last successful fetch, or None if no successful fetch has occurred.
        """
        return self._last_successful_fetch
