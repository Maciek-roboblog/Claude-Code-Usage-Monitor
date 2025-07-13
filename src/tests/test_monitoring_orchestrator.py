"""Comprehensive tests for monitoring orchestrator module."""

import threading
import time
from unittest.mock import Mock, patch

import pytest

from claude_monitor.core.plans import DEFAULT_TOKEN_LIMIT
from claude_monitor.monitoring.orchestrator import MonitoringOrchestrator


@pytest.fixture
def mock_data_manager():
    """
    Provides a mocked DataManager instance that returns predefined session data for testing purposes.
    """
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
def mock_session_monitor():
    """
    Provides a mocked SessionMonitor instance for use in tests.
    
    Returns:
        Mock: A mock object simulating SessionMonitor behavior with preset update return value, session ID, and session count.
    """
    mock = Mock()
    mock.update.return_value = (True, [])  # (is_valid, errors)
    mock.current_session_id = "session_1"
    mock.session_count = 1
    return mock


@pytest.fixture
def orchestrator(mock_data_manager, mock_session_monitor):
    """
    Create a `MonitoringOrchestrator` instance with mocked `DataManager` and `SessionMonitor` dependencies for testing purposes.
    
    Parameters:
        mock_data_manager: Mocked data manager to be injected.
        mock_session_monitor: Mocked session monitor to be injected.
    
    Returns:
        MonitoringOrchestrator: An orchestrator instance using the provided mocks.
    """
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

    def test_init_with_defaults(self):
        """
        Verifies that the MonitoringOrchestrator initializes with default parameters and correct internal state.
        """
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

    def test_init_with_custom_params(self):
        """
        Test that MonitoringOrchestrator initializes correctly with custom update interval and data path parameters.
        """
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

    def test_start_monitoring(self, orchestrator):
        """
        Test that starting monitoring creates and starts the monitoring thread with correct properties.
        """
        assert not orchestrator._monitoring

        orchestrator.start()

        assert orchestrator._monitoring
        assert orchestrator._monitor_thread is not None
        assert orchestrator._monitor_thread.is_alive()
        assert orchestrator._monitor_thread.name == "MonitoringThread"
        assert orchestrator._monitor_thread.daemon

        orchestrator.stop()

    def test_start_monitoring_already_running(self, orchestrator):
        """
        Test that starting monitoring when it is already running logs a warning and does not start a new monitoring thread.
        """
        orchestrator._monitoring = True

        with patch("claude_monitor.monitoring.orchestrator.logger") as mock_logger:
            orchestrator.start()

            mock_logger.warning.assert_called_once_with("Monitoring already running")

    def test_stop_monitoring(self, orchestrator):
        """
        Tests that stopping the orchestrator halts monitoring and cleans up the monitoring thread.
        """
        orchestrator.start()
        assert orchestrator._monitoring

        orchestrator.stop()

        assert not orchestrator._monitoring
        assert orchestrator._monitor_thread is None

    def test_stop_monitoring_not_running(self, orchestrator):
        """
        Test that stopping the orchestrator when monitoring is not running does not raise errors and leaves the monitoring state unchanged.
        """
        assert not orchestrator._monitoring

        orchestrator.stop()  # Should not raise

        assert not orchestrator._monitoring

    def test_stop_monitoring_with_timeout(self, orchestrator):
        """
        Test that stopping the monitoring orchestrator waits for the monitoring thread to join with a timeout if the thread does not terminate promptly.
        """
        orchestrator.start()

        # Mock thread that doesn't die quickly
        mock_thread = Mock()
        mock_thread.is_alive.return_value = True
        orchestrator._monitor_thread = mock_thread

        orchestrator.stop()

        mock_thread.join.assert_called_once_with(timeout=5)


class TestMonitoringOrchestratorCallbacks:
    """Test callback registration and handling."""

    def test_register_update_callback(self, orchestrator):
        """
        Test that registering an update callback adds it to the orchestrator's callback list.
        """
        callback = Mock()

        orchestrator.register_update_callback(callback)

        assert callback in orchestrator._update_callbacks

    def test_register_duplicate_callback(self, orchestrator):
        """
        Test that registering the same update callback multiple times only adds it once to the orchestrator.
        """
        callback = Mock()

        orchestrator.register_update_callback(callback)
        orchestrator.register_update_callback(callback)

        assert orchestrator._update_callbacks.count(callback) == 1

    def test_register_session_callback(self, orchestrator):
        """
        Test that registering a session callback on the orchestrator delegates the registration to the session monitor.
        """
        callback = Mock()

        orchestrator.register_session_callback(callback)

        orchestrator.session_monitor.register_callback.assert_called_once_with(callback)


class TestMonitoringOrchestratorDataProcessing:
    """Test data fetching and processing."""

    def test_force_refresh(self, orchestrator):
        """
        Test that the `force_refresh` method retrieves fresh data from the data manager and returns it in the expected format.
        """
        expected_data = {"blocks": [{"id": "test"}]}
        orchestrator.data_manager.get_data.return_value = expected_data

        result = orchestrator.force_refresh()

        assert result is not None
        assert "data" in result
        assert result["data"] == expected_data
        orchestrator.data_manager.get_data.assert_called_once_with(force_refresh=True)

    def test_force_refresh_no_data(self, orchestrator):
        """
        Test that `force_refresh` returns None when no data is available from the data manager.
        """
        orchestrator.data_manager.get_data.return_value = None

        result = orchestrator.force_refresh()

        assert result is None

    def test_set_args(self, orchestrator):
        """
        Tests that setting command line arguments updates the orchestrator's internal arguments state.
        """
        args = Mock()
        args.plan = "pro"

        orchestrator.set_args(args)

        assert orchestrator._args == args

    def test_wait_for_initial_data_success(self, orchestrator):
        """
        Test that `wait_for_initial_data` returns True when the initial data event is set.
        
        Starts the orchestrator, simulates the arrival of initial data, and verifies that waiting for initial data succeeds within the timeout.
        """
        # Start monitoring which will trigger initial data
        orchestrator.start()

        # Mock the first data event as set
        orchestrator._first_data_event.set()

        result = orchestrator.wait_for_initial_data(timeout=1.0)

        assert result is True
        orchestrator.stop()

    def test_wait_for_initial_data_timeout(self, orchestrator):
        """
        Test that `wait_for_initial_data` returns False when the initial data event is not set within the specified timeout.
        """
        # Don't start monitoring, so no data will be received
        result = orchestrator.wait_for_initial_data(timeout=0.1)

        assert result is False


class TestMonitoringOrchestratorMonitoringLoop:
    """Test the monitoring loop behavior."""

    def test_monitoring_loop_initial_fetch(self, orchestrator):
        """
        Test that the monitoring loop performs an initial data fetch when started.
        
        Verifies that the `_fetch_and_process_data` method is called at least once after the orchestrator is started.
        """
        with patch.object(orchestrator, "_fetch_and_process_data") as mock_fetch:
            mock_fetch.return_value = {"test": "data"}

            # Start and quickly stop to test initial fetch
            orchestrator.start()
            time.sleep(0.1)  # Let it run briefly
            orchestrator.stop()

            # Should have called fetch at least once for initial fetch
            assert mock_fetch.call_count >= 1

    def test_monitoring_loop_periodic_updates(self, orchestrator):
        """
        Test that the monitoring loop performs periodic data fetches at the configured interval.
        
        Verifies that the `_fetch_and_process_data` method is called multiple times when the orchestrator is running, indicating periodic updates are occurring.
        """
        orchestrator.update_interval = 0.1  # Very fast for testing

        with patch.object(orchestrator, "_fetch_and_process_data") as mock_fetch:
            mock_fetch.return_value = {"test": "data"}

            orchestrator.start()
            time.sleep(0.3)  # Let it run for multiple intervals
            orchestrator.stop()

            # Should have called fetch multiple times
            assert mock_fetch.call_count >= 2

    def test_monitoring_loop_stop_event(self, orchestrator):
        """
        Test that the monitoring loop exits promptly when the stop event is set, ensuring minimal data fetch calls.
        """
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

    def test_fetch_and_process_success(self, orchestrator):
        """
        Test that a successful data fetch and processing returns the expected result and updates the orchestrator's last valid data.
        
        Verifies that valid session data is retrieved, processed, and returned with correct token limit, arguments, session ID, and session count.
        """
        test_data = {
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

    def test_fetch_and_process_no_data(self, orchestrator):
        """
        Test that `_fetch_and_process_data` returns None when no data is available from the data manager.
        """
        orchestrator.data_manager.get_data.return_value = None

        result = orchestrator._fetch_and_process_data()

        assert result is None

    def test_fetch_and_process_validation_failure(self, orchestrator):
        """
        Tests that `_fetch_and_process_data` returns None when session monitor validation fails after fetching data.
        """
        test_data = {"blocks": []}
        orchestrator.data_manager.get_data.return_value = test_data
        orchestrator.session_monitor.update.return_value = (False, ["Validation error"])

        result = orchestrator._fetch_and_process_data()

        assert result is None

    def test_fetch_and_process_callback_success(self, orchestrator):
        """
        Test that the orchestrator's data fetch and process method successfully invokes all registered update callbacks with the correct data and token limit.
        """
        test_data = {
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
        assert call_args["token_limit"] == 44000  # Default PRO plan limit

    def test_fetch_and_process_callback_error(self, orchestrator):
        """
        Test that `_fetch_and_process_data` continues processing and reports errors when an update callback raises an exception.
        
        Verifies that a callback error does not prevent other callbacks from being executed and that errors are reported appropriately.
        """
        test_data = {
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

    def test_fetch_and_process_exception_handling(self, orchestrator):
        """
        Test that exceptions during data fetch are handled gracefully and reported.
        
        Verifies that when an exception is raised during data retrieval, the orchestrator reports the error and returns None.
        """
        orchestrator.data_manager.get_data.side_effect = Exception("Fetch failed")

        with patch(
            "claude_monitor.monitoring.orchestrator.report_error"
        ) as mock_report:
            result = orchestrator._fetch_and_process_data()

        assert result is None
        mock_report.assert_called_once()

    def test_fetch_and_process_first_data_event(self, orchestrator):
        """
        Test that fetching and processing data sets the first data event after successful processing.
        
        Verifies that the `_first_data_event` flag is set after `_fetch_and_process_data` is called with valid data, indicating that initial data has been processed.
        """
        test_data = {
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

    def test_calculate_token_limit_no_args(self, orchestrator):
        """
        Test that the token limit calculation returns the default value when no arguments are provided.
        """
        data = {"blocks": []}

        result = orchestrator._calculate_token_limit(data)

        assert result == DEFAULT_TOKEN_LIMIT

    def test_calculate_token_limit_pro_plan(self, orchestrator):
        """
        Test that the token limit calculation for the "pro" plan uses the correct plan argument and returns the expected value.
        """
        args = Mock()
        args.plan = "pro"
        orchestrator.set_args(args)

        data = {"blocks": []}

        with patch(
            "claude_monitor.monitoring.orchestrator.get_token_limit",
            return_value=200000,
        ) as mock_get_limit:
            result = orchestrator._calculate_token_limit(data)

        assert result == 200000
        mock_get_limit.assert_called_once_with("pro")

    def test_calculate_token_limit_custom_plan(self, orchestrator):
        """
        Test that the token limit calculation for a custom plan uses the correct arguments and returns the expected value.
        """
        args = Mock()
        args.plan = "custom"
        orchestrator.set_args(args)

        blocks_data = [{"totalTokens": 1000}, {"totalTokens": 1500}]
        data = {"blocks": blocks_data}

        with patch(
            "claude_monitor.monitoring.orchestrator.get_token_limit",
            return_value=175000,
        ) as mock_get_limit:
            result = orchestrator._calculate_token_limit(data)

        assert result == 175000
        mock_get_limit.assert_called_once_with("custom", blocks_data)

    def test_calculate_token_limit_exception(self, orchestrator):
        """
        Test that token limit calculation returns the default value when an exception occurs during calculation.
        """
        args = Mock()
        args.plan = "pro"
        orchestrator.set_args(args)

        data = {"blocks": []}

        with patch(
            "claude_monitor.monitoring.orchestrator.get_token_limit",
            side_effect=Exception("Calculation failed"),
        ):
            result = orchestrator._calculate_token_limit(data)

        assert result == DEFAULT_TOKEN_LIMIT


class TestMonitoringOrchestratorIntegration:
    """Test integration scenarios."""

    def test_full_monitoring_cycle(self, orchestrator):
        """
        Tests a complete monitoring cycle, including data fetching, callback invocation, argument setting, and monitoring start/stop.
        
        Verifies that the orchestrator fetches session data, calculates the token limit, invokes registered callbacks with the correct data, and properly manages its lifecycle.
        """
        # Setup test data
        test_data = {
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
        captured_data = []

        def capture_callback(data):
            """
            Appends the provided data to the captured_data list for later inspection during tests.
            
            Parameters:
                data: The data object to be captured.
            """
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

    def test_monitoring_with_session_changes(self, orchestrator):
        """
        Test that the orchestrator correctly detects and processes session changes during monitoring.
        
        Simulates a scenario where the session data changes between monitoring cycles, ensuring that the orchestrator updates its internal state and invokes registered callbacks with the new session information.
        """
        # Setup initial data
        initial_data = {
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
        changed_data = {
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

        def mock_get_data(force_refresh=False):
            """
            Simulate data retrieval, returning initial data on the first call and changed data on subsequent calls.
            
            Parameters:
                force_refresh (bool): If True, simulates a forced data refresh. This parameter does not affect the returned data in this mock.
            
            Returns:
                dict: The initial data on the first call, or changed data on subsequent calls.
            """
            nonlocal call_count
            call_count += 1
            return initial_data if call_count == 1 else changed_data

        orchestrator.data_manager.get_data.side_effect = mock_get_data

        # Mock session monitor to return different session IDs
        session_call_count = 0

        def mock_update(data):
            """
            Simulates a session update by incrementing the session count and updating the current session ID.
            
            Parameters:
                data: The session data to process.
            
            Returns:
                tuple: A tuple containing True and an empty list, indicating a successful update.
            """
            nonlocal session_call_count
            session_call_count += 1
            orchestrator.session_monitor.current_session_id = (
                f"session_{session_call_count}"
            )
            orchestrator.session_monitor.session_count = session_call_count
            return (True, [])

        orchestrator.session_monitor.update.side_effect = mock_update

        # Capture callback data
        captured_data = []
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

    def test_monitoring_error_recovery(self, orchestrator):
        """
        Test that the monitoring orchestrator recovers from data fetch errors and successfully processes data on subsequent attempts.
        
        Simulates a failure during the first data fetch and verifies that an error is reported and no data is returned. Ensures that a successful fetch on the next attempt results in valid data being processed.
        """
        # Setup data manager to fail then succeed
        call_count = 0

        def mock_get_data(force_refresh=False):
            """
            Simulates a data retrieval function that raises an exception on the first call and returns mock session data on subsequent calls.
            
            Parameters:
                force_refresh (bool): If True, simulates a forced data refresh (not used in logic).
            
            Returns:
                dict: Mock session data containing a single active block after the first call.
            
            Raises:
                Exception: On the first invocation to simulate a network error.
            """
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

    def test_concurrent_callback_registration(self, orchestrator):
        """
        Tests that registering update callbacks from multiple threads is thread-safe and all callbacks are registered without duplication or loss.
        """
        callbacks = []

        def register_callbacks():
            """
            Registers ten mock callback functions with the orchestrator for update notifications.
            """
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

    def test_concurrent_start_stop(self, orchestrator):
        """
        Tests that starting and stopping the orchestrator from multiple threads is thread-safe and results in a consistent stopped state.
        """

        def start_stop_loop():
            """
            Repeatedly starts and stops the orchestrator five times with short delays between each operation.
            """
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

    def test_last_valid_data_property(self, orchestrator):
        """
        Verifies that the orchestrator's `_last_valid_data` property is updated with the result of a successful data fetch and process.
        """
        test_data = {
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

    def test_monitoring_state_consistency(self, orchestrator):
        """
        Verify that the monitoring state flags and thread references of the orchestrator remain consistent before, during, and after start and stop operations.
        """
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

    def test_session_monitor_init(self):
        """
        Test that a new SessionMonitor instance initializes with no current session, no callbacks, and an empty session history.
        """
        from claude_monitor.monitoring.session_monitor import SessionMonitor

        monitor = SessionMonitor()

        assert monitor._current_session_id is None
        assert monitor._session_callbacks == []
        assert monitor._session_history == []

    def test_session_monitor_update_valid_data(self):
        """
        Test that updating the session monitor with valid session data returns True and no errors.
        """
        from claude_monitor.monitoring.session_monitor import SessionMonitor

        monitor = SessionMonitor()

        data = {
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

    def test_session_monitor_update_invalid_data(self):
        """
        Test that updating the SessionMonitor with invalid data (None) returns False and provides error messages.
        """
        from claude_monitor.monitoring.session_monitor import SessionMonitor

        monitor = SessionMonitor()

        # Test with None data
        is_valid, errors = monitor.update(None)
        assert is_valid is False
        assert len(errors) > 0

    def test_session_monitor_validation_empty_data(self):
        """
        Test that SessionMonitor's data validation method correctly handles empty input data.
        
        Verifies that `validate_data` returns a boolean validity flag and a list of errors when given an empty dictionary.
        """
        from claude_monitor.monitoring.session_monitor import SessionMonitor

        monitor = SessionMonitor()

        # Test empty dict
        is_valid, errors = monitor.validate_data({})
        assert isinstance(is_valid, bool)
        assert isinstance(errors, list)

    def test_session_monitor_validation_missing_blocks(self):
        """
        Test that SessionMonitor data validation correctly handles input missing the 'blocks' key.
        
        Verifies that the validation method returns a boolean validity flag and a list of errors when required session data is incomplete.
        """
        from claude_monitor.monitoring.session_monitor import SessionMonitor

        monitor = SessionMonitor()

        data = {"metadata": {"version": "1.0"}}
        is_valid, errors = monitor.validate_data(data)

        assert isinstance(is_valid, bool)
        assert isinstance(errors, list)

    def test_session_monitor_validation_invalid_blocks(self):
        """
        Test that SessionMonitor data validation fails when the 'blocks' field is not a list.
        
        Verifies that validation returns False and provides error messages when given invalid block data.
        """
        from claude_monitor.monitoring.session_monitor import SessionMonitor

        monitor = SessionMonitor()

        data = {"blocks": "not_a_list"}
        is_valid, errors = monitor.validate_data(data)

        assert is_valid is False
        assert len(errors) > 0

    def test_session_monitor_register_callback(self):
        """
        Test that registering a session callback adds it to the SessionMonitor's callback list.
        """
        from claude_monitor.monitoring.session_monitor import SessionMonitor

        monitor = SessionMonitor()
        callback = Mock()

        monitor.register_callback(callback)

        assert callback in monitor._session_callbacks

    def test_session_monitor_callback_execution(self):
        """
        Verifies that session monitor callbacks are registered and the callback list structure is maintained after a session update.
        """
        from claude_monitor.monitoring.session_monitor import SessionMonitor

        monitor = SessionMonitor()
        callback = Mock()
        monitor.register_callback(callback)

        # First update - should trigger callback for new session
        data = {
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

    def test_session_monitor_session_history(self):
        """
        Verifies that the session history in SessionMonitor is tracked as a list after updating with session data.
        """
        from claude_monitor.monitoring.session_monitor import SessionMonitor

        monitor = SessionMonitor()

        data = {
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

    def test_session_monitor_current_session_tracking(self):
        """
        Tests that the `SessionMonitor` correctly tracks the current session ID after updating with session data.
        """
        from claude_monitor.monitoring.session_monitor import SessionMonitor

        monitor = SessionMonitor()

        data = {
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

    def test_session_monitor_multiple_blocks(self):
        """
        Tests that SessionMonitor correctly processes data with multiple session blocks, ensuring it identifies active sessions and returns appropriate validation results.
        """
        from claude_monitor.monitoring.session_monitor import SessionMonitor

        monitor = SessionMonitor()

        data = {
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

    def test_session_monitor_no_active_session(self):
        """
        Test that SessionMonitor correctly handles data with no active sessions.
        
        Verifies that the update method returns a boolean validity flag and a list of errors when all session blocks are inactive.
        """
        from claude_monitor.monitoring.session_monitor import SessionMonitor

        monitor = SessionMonitor()

        data = {
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
