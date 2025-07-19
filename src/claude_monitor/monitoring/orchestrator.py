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

    def __init__(
        self, update_interval: int = 10, data_path: Optional[str] = None
    ) -> None:
        """Initialize orchestrator with components.

        Args:
            update_interval: Seconds between updates
            data_path: Optional path to Claude data directory
        """
        self.update_interval: int = update_interval

        self.data_manager: DataManager = DataManager(cache_ttl=5, data_path=data_path)
        self.session_monitor: SessionMonitor = SessionMonitor()

        self._monitoring: bool = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event: threading.Event = threading.Event()
        self._update_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self._last_valid_data: Optional[Dict[str, Any]] = None
        self._args: Optional[Any] = None
        self._first_data_event: threading.Event = threading.Event()

    def start(self) -> None:
        """Start monitoring."""
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
        """Stop monitoring."""
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
        """Set command line arguments for token limit calculation.

        Args:
            args: Command line arguments
        """
        self._args = args

    def register_update_callback(
        self, callback: Callable[[Dict[str, Any]], None]
    ) -> None:
        """Register callback for data updates.

        Args:
            callback: Function to call with monitoring data
        """
        if callback not in self._update_callbacks:
            self._update_callbacks.append(callback)
            logger.debug("Registered update callback")

    def register_session_callback(
        self, callback: Callable[[str, str, Optional[Dict[str, Any]]], None]
    ) -> None:
        """Register callback for session changes.

        Args:
            callback: Function(event_type, session_id, session_data)
        """
        self.session_monitor.register_callback(callback)

    def force_refresh(self) -> Optional[Dict[str, Any]]:
        """Force immediate data refresh.

        Returns:
            Fresh data or None if fetch fails
        """
        return self._fetch_and_process_data(force_refresh=True)

    def wait_for_initial_data(self, timeout: float = 10.0) -> bool:
        """Wait for initial data to be fetched.

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            True if data was received, False if timeout
        """
        return self._first_data_event.wait(timeout=timeout)

    def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
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
        """Fetch data and notify callbacks.

        Args:
            force_refresh: Force cache refresh

        Returns:
            Processed data or None if failed
        """
        try:
            # Fetch data
            start_time: float = time.time()
            data: Optional[Dict[str, Any]] = self.data_manager.get_data(
                force_refresh=force_refresh
            )

            if data is None:
                logger.warning("No data fetched")
                return None

            # Validate and update session tracking
            is_valid: bool
            errors: List[str]
            is_valid, errors = self.session_monitor.update(data)
            if not is_valid:
                logger.error(f"Data validation failed: {errors}")
                return None

            # Calculate token limit
            token_limit: int = self._calculate_token_limit(data)

            # Prepare monitoring data
            monitoring_data: Dict[str, Any] = {
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

            elapsed: float = time.time() - start_time
            logger.debug(f"Data processing completed in {elapsed:.3f}s")

            return monitoring_data

        except Exception as e:
            logger.error(f"Error in monitoring cycle: {e}", exc_info=True)
            report_error(
                exception=e, component="orchestrator", context_name="monitoring_cycle"
            )
            return None

    def _calculate_token_limit(self, data: Dict[str, Any]) -> int:
        """Calculate token limit based on plan and data.

        Args:
            data: Monitoring data

        Returns:
            Token limit
        """
        if not self._args:
            return DEFAULT_TOKEN_LIMIT

        plan: str = getattr(self._args, "plan", "pro")

        try:
            if plan == "custom":
                blocks: List[Any] = data.get("blocks", [])
                return get_token_limit(plan, blocks)
            return get_token_limit(plan)
        except Exception as e:
            logger.exception(f"Error calculating token limit: {e}")
            return DEFAULT_TOKEN_LIMIT
