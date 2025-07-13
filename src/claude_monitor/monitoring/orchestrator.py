"""Orchestrator for monitoring components."""

import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from claude_monitor.core.plans import DEFAULT_TOKEN_LIMIT, get_token_limit
from claude_monitor.error_handling import report_error
from claude_monitor.monitoring.data_manager import DataManager
from claude_monitor.monitoring.session_monitor import SessionMonitor

logger = logging.getLogger(__name__)


class MonitoringOrchestrator:
    """Orchestrates monitoring components following SRP."""

    def __init__(self, update_interval: int = 10, data_path: Optional[str] = None):
        """
        Initialize the MonitoringOrchestrator with data management and session monitoring components.
        
        Parameters:
            update_interval (int): Interval in seconds between monitoring updates.
            data_path (Optional[str]): Path to the Claude data directory, if specified.
        """
        self.update_interval = update_interval

        self.data_manager = DataManager(cache_ttl=5, data_path=data_path)
        self.session_monitor = SessionMonitor()

        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._update_callbacks: List[Callable] = []
        self._last_valid_data: Optional[Dict[str, Any]] = None
        self._args = None
        self._first_data_event = threading.Event()

    def start(self) -> None:
        """
        Starts the monitoring process in a background thread if it is not already running.
        
        If monitoring is already active, this method does nothing.
        """
        if self._monitoring:
            logger.warning("Monitoring already running")
            return

        logger.info(f"Starting monitoring with {self.update_interval}s interval")
        self._monitoring = True
        self._stop_event.clear()

        # Start monitoring thread
        self._monitor_thread = threading.Thread(
            target=self._monitoring_loop, name="MonitoringThread", daemon=True
        )
        self._monitor_thread.start()

    def stop(self) -> None:
        """
        Stops the monitoring process and terminates the background monitoring thread if running.
        """
        if not self._monitoring:
            return

        logger.info("Stopping monitoring")
        self._monitoring = False
        self._stop_event.set()

        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5)

        self._monitor_thread = None
        self._first_data_event.clear()

    def set_args(self, args: Any) -> None:
        """
        Store command-line arguments for use in token limit calculations.
        """
        self._args = args

    def register_update_callback(self, callback: Callable) -> None:
        """
        Registers a callback function to be invoked whenever monitoring data is updated.
        
        The callback will receive the latest monitoring data as its argument. Duplicate callbacks are ignored.
        """
        if callback not in self._update_callbacks:
            self._update_callbacks.append(callback)
            logger.debug("Registered update callback")

    def register_session_callback(self, callback: Callable) -> None:
        """
        Register a callback function to be invoked when session changes occur.
        
        The callback should accept three arguments: event type, session ID, and session data.
        """
        self.session_monitor.register_callback(callback)

    def force_refresh(self) -> Optional[Dict[str, Any]]:
        """
        Immediately fetches and processes the latest monitoring data, bypassing any cached results.
        
        Returns:
            dict or None: The most recent monitoring data if successful, or None if the fetch or processing fails.
        """
        return self._fetch_and_process_data(force_refresh=True)

    def wait_for_initial_data(self, timeout: float = 10.0) -> bool:
        """
        Block execution until the initial monitoring data is available or a timeout occurs.
        
        Parameters:
            timeout (float): Maximum number of seconds to wait for the initial data.
        
        Returns:
            bool: True if initial data was received within the timeout period, False otherwise.
        """
        return self._first_data_event.wait(timeout=timeout)

    def _monitoring_loop(self) -> None:
        """
        Runs the background monitoring loop, periodically fetching and processing monitoring data until stopped.
        """
        logger.info("Monitoring loop started")

        # Initial fetch
        self._fetch_and_process_data()

        while self._monitoring:
            # Wait for interval or stop
            if self._stop_event.wait(timeout=self.update_interval):
                if not self._monitoring:
                    break

            # Fetch and process
            self._fetch_and_process_data()

        logger.info("Monitoring loop ended")

    def _fetch_and_process_data(
        self, force_refresh: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Fetches monitoring data, validates it, calculates token limits, and notifies registered update callbacks.
        
        Parameters:
            force_refresh (bool): If True, bypasses the cache and forces fresh data retrieval.
        
        Returns:
            dict or None: The processed monitoring data dictionary if successful, or None if data fetching or validation fails.
        """
        try:
            # Fetch data
            start_time = time.time()
            data = self.data_manager.get_data(force_refresh=force_refresh)

            if data is None:
                logger.warning("No data fetched")
                return None

            # Validate and update session tracking
            is_valid, errors = self.session_monitor.update(data)
            if not is_valid:
                logger.error(f"Data validation failed: {errors}")
                return None

            # Calculate token limit
            token_limit = self._calculate_token_limit(data)

            # Prepare monitoring data
            monitoring_data = {
                "data": data,
                "token_limit": token_limit,
                "args": self._args,
                "session_id": self.session_monitor.current_session_id,
                "session_count": self.session_monitor.session_count,
            }

            # Store last valid data
            self._last_valid_data = monitoring_data

            # Signal that first data has been received
            if not self._first_data_event.is_set():
                self._first_data_event.set()

            # Notify callbacks
            for callback in self._update_callbacks:
                try:
                    callback(monitoring_data)
                except Exception as e:
                    logger.error(f"Callback error: {e}", exc_info=True)
                    report_error(
                        exception=e,
                        component="orchestrator",
                        context_name="callback_error",
                    )

            elapsed = time.time() - start_time
            logger.debug(f"Data processing completed in {elapsed:.3f}s")

            return monitoring_data

        except Exception as e:
            logger.error(f"Error in monitoring cycle: {e}", exc_info=True)
            report_error(
                exception=e, component="orchestrator", context_name="monitoring_cycle"
            )
            return None

    def _calculate_token_limit(self, data: Dict[str, Any]) -> int:
        """
        Determine the token limit based on the current plan and monitoring data.
        
        If no arguments are set, returns the default token limit. For a "custom" plan, calculates the token limit using the provided data blocks; otherwise, uses the plan name. Returns the default token limit if an error occurs during calculation.
        
        Parameters:
            data (dict): The current monitoring data used for token limit calculation.
        
        Returns:
            int: The calculated token limit.
        """
        if not self._args:
            return DEFAULT_TOKEN_LIMIT

        plan = getattr(self._args, "plan", "pro")

        try:
            if plan == "custom":
                return get_token_limit(plan, data.get("blocks", []))
            return get_token_limit(plan)
        except Exception as e:
            logger.error(f"Error calculating token limit: {e}")
            return DEFAULT_TOKEN_LIMIT
