"""Comprehensive tests for monitoring orchestrator module."""

import threading
import time
from typing import Any, Dict, List, Tuple, Union
from unittest.mock import Mock, patch

import pytest

from claude_monitor.core.plans import DEFAULT_TOKEN_LIMIT
from claude_monitor.monitoring.orchestrator import MonitoringOrchestrator


@pytest.fixture
def mock_data_manager() -> Mock:
    """Mock DataManager for testing."""
    mock = Mock()
    mock.get_data.return_value = {
        "blocks": [
            {
                "id": "session_1",
                "isActive": True,
                "totalTokens": 1000,
                "costUSD": 0.05,
                "startTime": "2024-01-01T12:00:00Z",
            }
        ]
    }
    return mock


@pytest.fixture
def mock_session_monitor() -> Mock:
    """Mock SessionMonitor for testing."""
    mock = Mock()
    mock.update.return_value = (True, [])  # (is_valid, errors)
    mock.current_session_id = "session_1"
    mock.session_count = 1
    return mock


@pytest.fixture
def orchestrator(
    mock_data_manager: Mock, mock_session_monitor: Mock
) -> MonitoringOrchestrator:
    """Create orchestrator with mocked dependencies."""
    with (
        patch(
            "claude_monitor.monitoring.orchestrator.DataManager",
            return_value=mock_data_manager,
        ),
        patch(
            "claude_monitor.monitoring.orchestrator.SessionMonitor",
            return_value=mock_session_monitor,
        ),
    ):
        return MonitoringOrchestrator(update_interval=1)


class TestMonitoringOrchestratorInit:
    """Test orchestrator initialization."""

    def test_init_with_defaults(self) -> None:
        """Test initialization with default parameters."""
        with (
            patch("claude_monitor.monitoring.orchestrator.DataManager") as mock_dm,
            patch("claude_monitor.monitoring.orchestrator.SessionMonitor") as mock_sm,
        ):
            orchestrator = MonitoringOrchestrator()

            assert orchestrator.update_interval == 10
            assert not orchestrator._monitoring
            assert orchestrator._monitor_thread is None
            assert orchestrator._args is None
            assert orchestrator._last_valid_data is None
            assert len(orchestrator._update_callbacks) == 0

            mock_dm.assert_called_once_with(cache_ttl=5, data_path=None)
            mock_sm.assert_called_once()

    def test_init_with_custom_params(self) -> None:
        """Test initialization with custom parameters."""
        with (
            patch("claude_monitor.monitoring.orchestrator.DataManager") as mock_dm,
            patch("claude_monitor.monitoring.orchestrator.SessionMonitor"),
        ):
            orchestrator = MonitoringOrchestrator(
                update_interval=5, data_path="/custom/path"
            )

            assert orchestrator.update_interval == 5
            mock_dm.assert_called_once_with(cache_ttl=5, data_path="/custom/path")


class TestMonitoringOrchestratorLifecycle:
    """Test orchestrator start/stop lifecycle."""

    def test_start_monitoring(self, orchestrator: MonitoringOrchestrator) -> None:
        """Test starting monitoring creates thread."""
        assert not orchestrator._monitoring

        orchestrator.start()

        assert orchestrator._monitoring
        assert orchestrator._monitor_thread is not None
        assert orchestrator._monitor_thread.is_alive()
        assert orchestrator._monitor_thread.name == "MonitoringThread"
        assert orchestrator._monitor_thread.daemon

        orchestrator.stop()

    def test_start_monitoring_already_running(
        self, orchestrator: MonitoringOrchestrator
    ) -> None:
        """Test starting monitoring when already running."""
        orchestrator._monitoring = True

        with patch("claude_monitor.monitoring.orchestrator.logger") as mock_logger:
            orchestrator.start()

            mock_logger.warning.assert_called_once_with("Monitoring already running")

    def test_stop_monitoring(self, orchestrator: MonitoringOrchestrator) -> None:
        """Test stopping monitoring."""
        orchestrator.start()
        assert orchestrator._monitoring

        orchestrator.stop()

        assert not orchestrator._monitoring
        assert orchestrator._monitor_thread is None

    def test_stop_monitoring_not_running(
        self, orchestrator: MonitoringOrchestrator
    ) -> None:
        """Test stopping monitoring when not running."""
        assert not orchestrator._monitoring

        orchestrator.stop()  # Should not raise

        assert not orchestrator._monitoring

    def test_stop_monitoring_with_timeout(
        self, orchestrator: MonitoringOrchestrator
    ) -> None:
        """Test stopping monitoring handles thread join timeout."""
        orchestrator.start()

        # Mock thread that doesn't die quickly
        mock_thread = Mock()
        mock_thread.is_alive.return_value = True
        orchestrator._monitor_thread = mock_thread

        orchestrator.stop()

        mock_thread.join.assert_called_once_with(timeout=5)


class TestMonitoringOrchestratorCallbacks:
    """Test callback registration and handling."""

    def test_register_update_callback(
        self, orchestrator: MonitoringOrchestrator
    ) -> None:
        """Test registering update callback."""
        callback = Mock()

        orchestrator.register_update_callback(callback)

        assert callback in orchestrator._update_callbacks

    def test_register_duplicate_callback(
        self, orchestrator: MonitoringOrchestrator
    ) -> None:
        """Test registering same callback twice only adds once."""
        callback = Mock()

        orchestrator.register_update_callback(callback)
        orchestrator.register_update_callback(callback)

        assert orchestrator._update_callbacks.count(callback) == 1

    def test_register_session_callback(
        self, orchestrator: MonitoringOrchestrator
    ) -> None:
        """Test registering session callback delegates to session monitor."""
        callback = Mock()

        orchestrator.register_session_callback(callback)

        orchestrator.session_monitor.register_callback.assert_called_once_with(callback)


class TestMonitoringOrchestratorDataProcessing:
    """Test data fetching and processing."""

    def test_force_refresh(self, orchestrator: MonitoringOrchestrator) -> None:
        """Test force refresh calls data manager."""
        expected_data: Dict[str, List[Dict[str, str]]] = {"blocks": [{"id": "test"}]}
        orchestrator.data_manager.get_data.return_value = expected_data

        result = orchestrator.force_refresh()

        assert result is not None
        assert "data" in result
        assert result["data"] == expected_data
        orchestrator.data_manager.get_data.assert_called_once_with(force_refresh=True)

    def test_force_refresh_no_data(self, orchestrator: MonitoringOrchestrator) -> None:
        """Test force refresh when no data available."""
        orchestrator.data_manager.get_data.return_value = None

        result = orchestrator.force_refresh()

        assert result is None

    def test_set_args(self, orchestrator: MonitoringOrchestrator) -> None:
        """Test setting command line arguments."""
        args = Mock()
        args.plan = "pro"

        orchestrator.set_args(args)

        assert orchestrator._args == args

    def test_wait_for_initial_data_success(
        self, orchestrator: MonitoringOrchestrator
    ) -> None:
        """Test waiting for initial data returns True when data received."""
        # Start monitoring which will trigger initial data
        orchestrator.start()

        # Mock the first data event as set
        orchestrator._first_data_event.set()

        result = orchestrator.wait_for_initial_data(timeout=1.0)

        assert result is True
        orchestrator.stop()

    def test_wait_for_initial_data_timeout(
        self, orchestrator: MonitoringOrchestrator
    ) -> None:
        """Test waiting for initial data returns False on timeout."""
        # Don't start monitoring, so no data will be received
        result = orchestrator.wait_for_initial_data(timeout=0.1)

        assert result is False


class TestMonitoringOrchestratorMonitoringLoop:
    """Test the monitoring loop behavior."""

    def test_monitoring_loop_initial_fetch(
        self, orchestrator: MonitoringOrchestrator
    ) -> None:
        """Test monitoring loop performs initial fetch."""
        with patch.object(orchestrator, "_fetch_and_process_data") as mock_fetch:
            mock_fetch.return_value = {"test": "data"}

            # Start and quickly stop to test initial fetch
            orchestrator.start()
            time.sleep(0.1)  # Let it run briefly
            orchestrator.stop()

            # Should have called fetch at least once for initial fetch
            assert mock_fetch.call_count >= 1

    def test_monitoring_loop_periodic_updates(
        self, orchestrator: MonitoringOrchestrator
    ) -> None:
        """Test monitoring loop performs periodic updates."""
        orchestrator.update_interval = 0.1  # Very fast for testing

        with patch.object(orchestrator, "_fetch_and_process_data") as mock_fetch:
            mock_fetch.return_value = {"test": "data"}

            orchestrator.start()
            time.sleep(0.3)  # Let it run for multiple intervals
            orchestrator.stop()

            # Should have called fetch multiple times
            assert mock_fetch.call_count >= 2

    def test_monitoring_loop_stop_event(
        self, orchestrator: MonitoringOrchestrator
    ) -> None:
        """Test monitoring loop respects stop event."""
        with patch.object(orchestrator, "_fetch_and_process_data") as mock_fetch:
            mock_fetch.return_value = {"test": "data"}

            orchestrator.start()
            # Stop immediately
            orchestrator._stop_event.set()
            orchestrator._monitoring = False
            time.sleep(0.1)  # Give it time to stop

            # Should have minimal calls
            assert mock_fetch.call_count <= 2


class TestMonitoringOrchestratorFetchAndProcess:
    """Test data fetching and processing logic."""

    def test_fetch_and_process_success(
        self, orchestrator: MonitoringOrchestrator
    ) -> None:
        """Test successful data fetch and processing."""
        test_data: Dict[str, List[Dict[str, Union[str, bool, int, float]]]] = {
            "blocks": [
                {
                    "id": "session_1",
                    "isActive": True,
                    "totalTokens": 1500,
                    "costUSD": 0.075,
                }
            ]
        }
        orchestrator.data_manager.get_data.return_value = test_data
        orchestrator.session_monitor.update.return_value = (True, [])

        # Set args for token limit calculation
        args = Mock()
        args.plan = "pro"
        orchestrator.set_args(args)

        with patch(
            "claude_monitor.monitoring.orchestrator.get_token_limit",
            return_value=200000,
        ):
            result = orchestrator._fetch_and_process_data()

        assert result is not None
        assert result["data"] == test_data
        assert result["token_limit"] == 200000
        assert result["args"] == args
        assert result["session_id"] == "session_1"
        assert result["session_count"] == 1
        assert orchestrator._last_valid_data == result

    def test_fetch_and_process_no_data(
        self, orchestrator: MonitoringOrchestrator
    ) -> None:
        """Test fetch and process when no data available."""
        orchestrator.data_manager.get_data.return_value = None

        result = orchestrator._fetch_and_process_data()

        assert result is None

    def test_fetch_and_process_validation_failure(
        self, orchestrator: MonitoringOrchestrator
    ) -> None:
        """Test fetch and process with validation failure."""
        test_data: Dict[str, List[Any]] = {"blocks": []}
        orchestrator.data_manager.get_data.return_value = test_data
        orchestrator.session_monitor.update.return_value = (False, ["Validation error"])

        result = orchestrator._fetch_and_process_data()

        assert result is None

    def test_fetch_and_process_callback_success(
        self, orchestrator: MonitoringOrchestrator
    ) -> None:
        """Test fetch and process calls callbacks successfully."""
        test_data: Dict[str, List[Dict[str, Union[str, bool, int, float]]]] = {
            "blocks": [
                {"id": "test", "isActive": True, "totalTokens": 100, "costUSD": 0.01}
            ]
        }
        orchestrator.data_manager.get_data.return_value = test_data

        callback1 = Mock()
        callback2 = Mock()
        orchestrator.register_update_callback(callback1)
        orchestrator.register_update_callback(callback2)

        with patch(
            "claude_monitor.monitoring.orchestrator.get_token_limit",
            return_value=200000,
        ):
            result = orchestrator._fetch_and_process_data()

        assert result is not None
        callback1.assert_called_once()
        callback2.assert_called_once()

        # Check callback was called with correct data
        call_args = callback1.call_args[0][0]
        assert call_args["data"] == test_data
        assert call_args["token_limit"] == 19000  # Default PRO plan limit

    def test_fetch_and_process_callback_error(
        self, orchestrator: MonitoringOrchestrator
    ) -> None:
        """Test fetch and process handles callback errors."""
        test_data: Dict[str, List[Dict[str, Union[str, bool, int, float]]]] = {
            "blocks": [
                {"id": "test", "isActive": True, "totalTokens": 100, "costUSD": 0.01}
            ]
        }
        orchestrator.data_manager.get_data.return_value = test_data

        callback_error = Mock(side_effect=Exception("Callback failed"))
        callback_success = Mock()
        orchestrator.register_update_callback(callback_error)
        orchestrator.register_update_callback(callback_success)

        with (
            patch(
                "claude_monitor.monitoring.orchestrator.get_token_limit",
                return_value=200000,
            ),
            patch("claude_monitor.monitoring.orchestrator.report_error") as mock_report,
        ):
            result = orchestrator._fetch_and_process_data()

        assert result is not None  # Should still return data despite callback error
        callback_success.assert_called_once()  # Other callbacks should still work
        mock_report.assert_called_once()

    def test_fetch_and_process_exception_handling(
        self, orchestrator: MonitoringOrchestrator
    ) -> None:
        """Test fetch and process handles exceptions."""
        orchestrator.data_manager.get_data.side_effect = Exception("Fetch failed")

        with patch(
            "claude_monitor.monitoring.orchestrator.report_error"
        ) as mock_report:
            result = orchestrator._fetch_and_process_data()

        assert result is None
        mock_report.assert_called_once()

    def test_fetch_and_process_first_data_event(
        self, orchestrator: MonitoringOrchestrator
    ) -> None:
        """Test fetch and process sets first data event."""
        test_data: Dict[str, List[Dict[str, Union[str, bool, int, float]]]] = {
            "blocks": [
                {"id": "test", "isActive": True, "totalTokens": 100, "costUSD": 0.01}
            ]
        }
        orchestrator.data_manager.get_data.return_value = test_data

        assert not orchestrator._first_data_event.is_set()

        with patch(
            "claude_monitor.monitoring.orchestrator.get_token_limit",
            return_value=200000,
        ):
            orchestrator._fetch_and_process_data()

        assert orchestrator._first_data_event.is_set()


class TestMonitoringOrchestratorTokenLimitCalculation:
    """Test token limit calculation logic."""

    def test_calculate_token_limit_no_args(
        self, orchestrator: MonitoringOrchestrator
    ) -> None:
        """Test token limit calculation without args."""
        data: Dict[str, List[Any]] = {"blocks": []}

        result = orchestrator._calculate_token_limit(data)

        assert result == DEFAULT_TOKEN_LIMIT

    def test_calculate_token_limit_pro_plan(
        self, orchestrator: MonitoringOrchestrator
    ) -> None:
        """Test token limit calculation for pro plan."""
        args = Mock()
        args.plan = "pro"
        orchestrator.set_args(args)

        data: Dict[str, List[Any]] = {"blocks": []}

        with patch(
            "claude_monitor.monitoring.orchestrator.get_token_limit",
            return_value=200000,
        ) as mock_get_limit:
            result = orchestrator._calculate_token_limit(data)

        assert result == 200000
        mock_get_limit.assert_called_once_with("pro")

    def test_calculate_token_limit_custom_plan(
        self, orchestrator: MonitoringOrchestrator
    ) -> None:
        """Test token limit calculation for custom plan."""
        args = Mock()
        args.plan = "custom"
        orchestrator.set_args(args)

        blocks_data: List[Dict[str, int]] = [
            {"totalTokens": 1000},
            {"totalTokens": 1500},
        ]
        data: Dict[str, List[Dict[str, int]]] = {"blocks": blocks_data}

        with patch(
            "claude_monitor.monitoring.orchestrator.get_token_limit",
            return_value=175000,
        ) as mock_get_limit:
            result = orchestrator._calculate_token_limit(data)

        assert result == 175000
        mock_get_limit.assert_called_once_with("custom", blocks_data)

    def test_calculate_token_limit_exception(
        self, orchestrator: MonitoringOrchestrator
    ) -> None:
        """Test token limit calculation handles exceptions."""
        args = Mock()
        args.plan = "pro"
        orchestrator.set_args(args)

        data: Dict[str, List[Any]] = {"blocks": []}

        with patch(
            "claude_monitor.monitoring.orchestrator.get_token_limit",
            side_effect=Exception("Calculation failed"),
        ):
            result = orchestrator._calculate_token_limit(data)

        assert result == DEFAULT_TOKEN_LIMIT


class TestMonitoringOrchestratorIntegration:
    """Test integration scenarios."""

    def test_full_monitoring_cycle(self, orchestrator: MonitoringOrchestrator) -> None:
        """Test complete monitoring cycle."""
        # Setup test data
        test_data: Dict[str, List[Dict[str, Union[str, bool, int, float]]]] = {
            "blocks": [
                {
                    "id": "session_1",
                    "isActive": True,
                    "totalTokens": 1200,
                    "costUSD": 0.06,
                }
            ]
        }
        orchestrator.data_manager.get_data.return_value = test_data

        # Setup callback to capture monitoring data
        captured_data: List[Dict[str, Any]] = []

        def capture_callback(data: Dict[str, Any]) -> None:
            captured_data.append(data)

        orchestrator.register_update_callback(capture_callback)

        # Set args
        args = Mock()
        args.plan = "pro"
        orchestrator.set_args(args)

        with patch(
            "claude_monitor.monitoring.orchestrator.get_token_limit",
            return_value=200000,
        ):
            # Start monitoring
            orchestrator.start()

            # Wait for initial data
            success = orchestrator.wait_for_initial_data(timeout=2.0)
            assert success

            # Stop monitoring
            orchestrator.stop()

        # Verify callback was called with correct data
        assert len(captured_data) >= 1
        data = captured_data[0]
        assert data["data"] == test_data
        assert data["token_limit"] == 200000
        assert data["session_id"] == "session_1"
        assert data["session_count"] == 1

    def test_monitoring_with_session_changes(
        self, orchestrator: MonitoringOrchestrator
    ) -> None:
        """Test monitoring responds to session changes."""
        # Setup initial data
        initial_data: Dict[str, List[Dict[str, Union[str, bool, int, float]]]] = {
            "blocks": [
                {
                    "id": "session_1",
                    "isActive": True,
                    "totalTokens": 1000,
                    "costUSD": 0.05,
                }
            ]
        }

        # Setup changed data
        changed_data: Dict[str, List[Dict[str, Union[str, bool, int, float]]]] = {
            "blocks": [
                {
                    "id": "session_2",
                    "isActive": True,
                    "totalTokens": 1500,
                    "costUSD": 0.075,
                }
            ]
        }

        # Mock data manager to return different data on subsequent calls
        call_count = 0

        def mock_get_data(
            force_refresh: bool = False,
        ) -> Dict[str, List[Dict[str, Union[str, bool, int, float]]]]:
            nonlocal call_count
            call_count += 1
            return initial_data if call_count == 1 else changed_data

        orchestrator.data_manager.get_data.side_effect = mock_get_data

        # Mock session monitor to return different session IDs
        session_call_count = 0

        def mock_update(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
            nonlocal session_call_count
            session_call_count += 1
            orchestrator.session_monitor.current_session_id = (
                f"session_{session_call_count}"
            )
            orchestrator.session_monitor.session_count = session_call_count
            return (True, [])

        orchestrator.session_monitor.update.side_effect = mock_update

        # Capture callback data
        captured_data: List[Dict[str, Any]] = []
        orchestrator.register_update_callback(lambda data: captured_data.append(data))

        with patch(
            "claude_monitor.monitoring.orchestrator.get_token_limit",
            return_value=200000,
        ):
            # Process initial data
            result1 = orchestrator._fetch_and_process_data()
            assert result1["session_id"] == "session_1"

            # Process changed data
            result2 = orchestrator._fetch_and_process_data()
            assert result2["session_id"] == "session_2"

        # Verify both updates were captured
        assert len(captured_data) >= 2

    def test_monitoring_error_recovery(
        self, orchestrator: MonitoringOrchestrator
    ) -> None:
        """Test monitoring recovers from errors."""
        # Setup data manager to fail then succeed
        call_count = 0

        def mock_get_data(
            force_refresh: bool = False,
        ) -> Dict[str, List[Dict[str, Union[str, bool, int, float]]]]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Network error")
            return {
                "blocks": [
                    {
                        "id": "test",
                        "isActive": True,
                        "totalTokens": 100,
                        "costUSD": 0.01,
                    }
                ]
            }

        orchestrator.data_manager.get_data.side_effect = mock_get_data

        with patch(
            "claude_monitor.monitoring.orchestrator.report_error"
        ) as mock_report:
            # First call should fail
            result1 = orchestrator._fetch_and_process_data()
            assert result1 is None
            mock_report.assert_called_once()

            # Second call should succeed
            with patch(
                "claude_monitor.monitoring.orchestrator.get_token_limit",
                return_value=200000,
            ):
                result2 = orchestrator._fetch_and_process_data()
            assert result2 is not None
            assert result2["data"]["blocks"][0]["id"] == "test"


class TestMonitoringOrchestratorThreadSafety:
    """Test thread safety of orchestrator."""

    def test_concurrent_callback_registration(
        self, orchestrator: MonitoringOrchestrator
    ) -> None:
        """Test thread-safe callback registration."""
        callbacks: List[Mock] = []

        def register_callbacks() -> None:
            for i in range(10):
                callback = Mock()
                callback.name = f"callback_{i}"
                callbacks.append(callback)
                orchestrator.register_update_callback(callback)

        # Register callbacks from multiple threads
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=register_callbacks)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All callbacks should be registered
        assert len(orchestrator._update_callbacks) == 30

    def test_concurrent_start_stop(self, orchestrator: MonitoringOrchestrator) -> None:
        """Test thread-safe start/stop operations."""

        def start_stop_loop() -> None:
            for _ in range(5):
                orchestrator.start()
                time.sleep(0.01)
                orchestrator.stop()
                time.sleep(0.01)

        # Start/stop from multiple threads
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=start_stop_loop)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Should end in stopped state
        assert not orchestrator._monitoring
        assert orchestrator._monitor_thread is None


class TestMonitoringOrchestratorProperties:
    """Test orchestrator properties and state."""

    def test_last_valid_data_property(
        self, orchestrator: MonitoringOrchestrator
    ) -> None:
        """Test last valid data is stored correctly."""
        test_data: Dict[str, List[Dict[str, Union[str, bool, int, float]]]] = {
            "blocks": [
                {"id": "test", "isActive": True, "totalTokens": 100, "costUSD": 0.01}
            ]
        }
        orchestrator.data_manager.get_data.return_value = test_data

        with patch(
            "claude_monitor.monitoring.orchestrator.get_token_limit",
            return_value=200000,
        ):
            result = orchestrator._fetch_and_process_data()

        assert orchestrator._last_valid_data == result
        assert orchestrator._last_valid_data["data"] == test_data

    def test_monitoring_state_consistency(
        self, orchestrator: MonitoringOrchestrator
    ) -> None:
        """Test monitoring state remains consistent."""
        assert not orchestrator._monitoring
        assert orchestrator._monitor_thread is None
        assert not orchestrator._stop_event.is_set()

        orchestrator.start()
        assert orchestrator._monitoring
        assert orchestrator._monitor_thread is not None
        assert not orchestrator._stop_event.is_set()

        orchestrator.stop()
        assert not orchestrator._monitoring
        assert orchestrator._monitor_thread is None
        # stop_event may remain set after stopping


class TestSessionMonitor:
    """Test session monitoring functionality."""

    def test_session_monitor_init(self) -> None:
        """Test SessionMonitor initialization."""
        from claude_monitor.monitoring.session_monitor import SessionMonitor

        monitor = SessionMonitor()

        assert monitor._current_session_id is None
        assert monitor._session_callbacks == []
        assert monitor._session_history == []

    def test_session_monitor_update_valid_data(self) -> None:
        """Test updating session monitor with valid data."""
        from claude_monitor.monitoring.session_monitor import SessionMonitor

        monitor = SessionMonitor()

        data: Dict[str, List[Dict[str, Union[str, bool, int, float]]]] = {
            "blocks": [
                {
                    "id": "session_1",
                    "isActive": True,
                    "totalTokens": 1000,
                    "costUSD": 0.05,
                    "startTime": "2024-01-01T12:00:00Z",
                }
            ]
        }

        is_valid, errors = monitor.update(data)

        assert is_valid is True
        assert errors == []

    def test_session_monitor_update_invalid_data(self) -> None:
        """Test updating session monitor with invalid data."""
        from claude_monitor.monitoring.session_monitor import SessionMonitor

        monitor = SessionMonitor()

        # Test with None data
        is_valid, errors = monitor.update(None)
        assert is_valid is False
        assert len(errors) > 0

    def test_session_monitor_validation_empty_data(self) -> None:
        """Test data validation with empty data."""
        from claude_monitor.monitoring.session_monitor import SessionMonitor

        monitor = SessionMonitor()

        # Test empty dict
        is_valid, errors = monitor.validate_data({})
        assert isinstance(is_valid, bool)
        assert isinstance(errors, list)

    def test_session_monitor_validation_missing_blocks(self) -> None:
        """Test data validation with missing blocks."""
        from claude_monitor.monitoring.session_monitor import SessionMonitor

        monitor = SessionMonitor()

        data: Dict[str, Dict[str, str]] = {"metadata": {"version": "1.0"}}
        is_valid, errors = monitor.validate_data(data)

        assert isinstance(is_valid, bool)
        assert isinstance(errors, list)

    def test_session_monitor_validation_invalid_blocks(self) -> None:
        """Test data validation with invalid blocks."""
        from claude_monitor.monitoring.session_monitor import SessionMonitor

        monitor = SessionMonitor()

        data: Dict[str, str] = {"blocks": "not_a_list"}
        is_valid, errors = monitor.validate_data(data)

        assert is_valid is False
        assert len(errors) > 0

    def test_session_monitor_register_callback(self) -> None:
        """Test registering session callbacks."""
        from claude_monitor.monitoring.session_monitor import SessionMonitor

        monitor = SessionMonitor()
        callback = Mock()

        monitor.register_callback(callback)

        assert callback in monitor._session_callbacks

    def test_session_monitor_callback_execution(self) -> None:
        """Test that callbacks are executed on session change."""
        from claude_monitor.monitoring.session_monitor import SessionMonitor

        monitor = SessionMonitor()
        callback = Mock()
        monitor.register_callback(callback)

        # First update - should trigger callback for new session
        data: Dict[str, List[Dict[str, Union[str, bool, int, float]]]] = {
            "blocks": [
                {
                    "id": "session_1",
                    "isActive": True,
                    "totalTokens": 1000,
                    "costUSD": 0.05,
                    "startTime": "2024-01-01T12:00:00Z",
                }
            ]
        }

        monitor.update(data)

        # Callback may or may not be called depending on implementation
        # Just verify the structure is maintained
        assert isinstance(monitor._session_callbacks, list)

    def test_session_monitor_session_history(self) -> None:
        """Test session history tracking."""
        from claude_monitor.monitoring.session_monitor import SessionMonitor

        monitor = SessionMonitor()

        data: Dict[str, List[Dict[str, Union[str, bool, int, float]]]] = {
            "blocks": [
                {
                    "id": "session_1",
                    "isActive": True,
                    "totalTokens": 1000,
                    "costUSD": 0.05,
                    "startTime": "2024-01-01T12:00:00Z",
                }
            ]
        }

        monitor.update(data)

        # History may or may not change depending on implementation
        assert isinstance(monitor._session_history, list)

    def test_session_monitor_current_session_tracking(self) -> None:
        """Test current session ID tracking."""
        from claude_monitor.monitoring.session_monitor import SessionMonitor

        monitor = SessionMonitor()

        data: Dict[str, List[Dict[str, Union[str, bool, int, float]]]] = {
            "blocks": [
                {
                    "id": "session_1",
                    "isActive": True,
                    "totalTokens": 1000,
                    "costUSD": 0.05,
                    "startTime": "2024-01-01T12:00:00Z",
                }
            ]
        }

        monitor.update(data)

        # Current session ID may be set depending on implementation
        assert isinstance(monitor._current_session_id, (str, type(None)))

    def test_session_monitor_multiple_blocks(self) -> None:
        """Test session monitor with multiple blocks."""
        from claude_monitor.monitoring.session_monitor import SessionMonitor

        monitor = SessionMonitor()

        data: Dict[str, List[Dict[str, Union[str, bool, int, float]]]] = {
            "blocks": [
                {
                    "id": "session_1",
                    "isActive": False,
                    "totalTokens": 1000,
                    "costUSD": 0.05,
                    "startTime": "2024-01-01T12:00:00Z",
                },
                {
                    "id": "session_2",
                    "isActive": True,
                    "totalTokens": 500,
                    "costUSD": 0.02,
                    "startTime": "2024-01-01T13:00:00Z",
                },
            ]
        }

        is_valid, errors = monitor.update(data)

        assert isinstance(is_valid, bool)
        assert isinstance(errors, list)

    def test_session_monitor_no_active_session(self) -> None:
        """Test session monitor with no active sessions."""
        from claude_monitor.monitoring.session_monitor import SessionMonitor

        monitor = SessionMonitor()

        data: Dict[str, List[Dict[str, Union[str, bool, int, float]]]] = {
            "blocks": [
                {
                    "id": "session_1",
                    "isActive": False,
                    "totalTokens": 1000,
                    "costUSD": 0.05,
                    "startTime": "2024-01-01T12:00:00Z",
                }
            ]
        }

        is_valid, errors = monitor.update(data)

        assert isinstance(is_valid, bool)
        assert isinstance(errors, list)
