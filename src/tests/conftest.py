"""Shared pytest fixtures for Claude Monitor tests."""

from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from claude_monitor.core.models import CostMode, UsageEntry


@pytest.fixture
def mock_pricing_calculator():
    """
    Provides a mock PricingCalculator with a fixed cost calculation for testing purposes.
    
    Returns:
        Mock: A mock object with `calculate_cost_for_entry` always returning 0.001.
    """
    mock = Mock()
    mock.calculate_cost_for_entry.return_value = 0.001
    return mock


@pytest.fixture
def mock_timezone_handler():
    """
    Provides a mock TimezoneHandler with fixed UTC datetime responses for testing purposes.
    
    Returns:
        Mock: A mock object with `parse_timestamp` and `ensure_utc` methods returning a preset UTC datetime.
    """
    mock = Mock()
    mock.parse_timestamp.return_value = datetime(
        2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc
    )
    mock.ensure_utc.return_value = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    return mock


@pytest.fixture
def sample_usage_entry():
    """
    Return a UsageEntry instance with preset values for timestamp, token counts, cost, model, message ID, and request ID for use in tests.
    """
    return UsageEntry(
        timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        input_tokens=100,
        output_tokens=50,
        cache_creation_tokens=10,
        cache_read_tokens=5,
        cost_usd=0.001,
        model="claude-3-haiku",
        message_id="msg_123",
        request_id="req_456",
    )


@pytest.fixture
def sample_valid_data():
    """
    Return a dictionary representing a valid structured usage data entry for testing.
    
    The returned data includes a timestamp, message details with model and token usage, a request ID, and type "assistant".
    """
    return {
        "timestamp": "2024-01-01T12:00:00Z",
        "message": {
            "id": "msg_123",
            "model": "claude-3-haiku",
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
                "cache_creation_input_tokens": 10,
                "cache_read_input_tokens": 5,
            },
        },
        "request_id": "req_456",
        "type": "assistant",
    }


@pytest.fixture
def sample_assistant_data():
    """
    Return a dictionary representing a sample assistant-type usage data entry for testing purposes.
    
    The returned data includes a timestamp, type "assistant", message details with model and token usage, and a request ID.
    """
    return {
        "timestamp": "2024-01-01T12:00:00Z",
        "type": "assistant",
        "message": {
            "id": "msg_123",
            "model": "claude-3-haiku",
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
                "cache_creation_input_tokens": 10,
                "cache_read_input_tokens": 5,
            },
        },
        "request_id": "req_456",
    }


@pytest.fixture
def sample_user_data():
    """
    Return a sample dictionary representing user-type usage data for testing purposes.
    
    The returned data includes a timestamp, type "user", usage token counts, model name, message ID, and request ID.
    """
    return {
        "timestamp": "2024-01-01T12:00:00Z",
        "type": "user",
        "usage": {
            "input_tokens": 200,
            "output_tokens": 75,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        },
        "model": "claude-3-haiku",
        "message_id": "msg_123",
        "request_id": "req_456",
    }


@pytest.fixture
def sample_malformed_data():
    """
    Return a dictionary containing intentionally malformed usage data for testing error handling scenarios.
    
    The returned data includes an invalid timestamp string, a non-dictionary message field, and usage tokens with incorrect types.
    """
    return {
        "timestamp": "invalid_timestamp",
        "message": "not_a_dict",
        "usage": {"input_tokens": "not_a_number", "output_tokens": None},
    }


@pytest.fixture
def sample_minimal_data():
    """
    Return a minimal valid usage data dictionary for testing, containing only timestamp, usage tokens, and request ID.
    """
    return {
        "timestamp": "2024-01-01T12:00:00Z",
        "usage": {"input_tokens": 100, "output_tokens": 50},
        "request_id": "req_456",
    }


@pytest.fixture
def sample_empty_tokens_data():
    """
    Return a sample usage data dictionary where all token counts are set to zero.
    
    This fixture is useful for testing scenarios involving empty or zero token usage.
    """
    return {
        "timestamp": "2024-01-01T12:00:00Z",
        "usage": {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        },
        "request_id": "req_456",
    }


@pytest.fixture
def sample_duplicate_data():
    """
    Return a list of usage entry dictionaries containing duplicate message and request IDs for testing deduplication logic.
    
    Returns:
        List[dict]: Usage entries with intentional duplicates to simulate repeated data scenarios.
    """
    return [
        {
            "timestamp": "2024-01-01T12:00:00Z",
            "message_id": "msg_1",
            "request_id": "req_1",
            "usage": {"input_tokens": 100, "output_tokens": 50},
        },
        {
            "timestamp": "2024-01-01T13:00:00Z",
            "message_id": "msg_1",
            "request_id": "req_1",
            "usage": {"input_tokens": 150, "output_tokens": 60},
        },
        {
            "timestamp": "2024-01-01T14:00:00Z",
            "message_id": "msg_2",
            "request_id": "req_2",
            "usage": {"input_tokens": 200, "output_tokens": 75},
        },
    ]


@pytest.fixture
def all_cost_modes():
    """
    Return a list of all available cost modes for testing purposes.
    
    Returns:
        List of CostMode values included in the test environment.
    """
    return [CostMode.AUTO]


@pytest.fixture
def sample_cutoff_time():
    """
    Provides a fixed UTC datetime representing a sample cutoff time for testing purposes.
    
    Returns:
        datetime: The cutoff time set to 2024-01-01 10:00:00 UTC.
    """
    return datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def sample_processed_hashes():
    """
    Return a set of sample processed message-request ID hashes for deduplication testing.
    """
    return {"msg_existing:req_existing", "msg_old:req_old"}


@pytest.fixture
def mock_file_reader():
    """
    Provides a mock JsonlFileReader with preset return values for file reading and discovery methods, used for testing file processing logic.
    """
    mock = Mock()
    mock.read_jsonl_file.return_value = [
        {
            "timestamp": "2024-01-01T12:00:00Z",
            "message_id": "msg_1",
            "request_id": "req_1",
            "usage": {"input_tokens": 100, "output_tokens": 50},
        }
    ]
    mock.load_all_entries.return_value = [
        {"raw_data": "entry1"},
        {"raw_data": "entry2"},
    ]
    mock.find_jsonl_files.return_value = [
        "/path/to/file1.jsonl",
        "/path/to/file2.jsonl",
    ]
    return mock


@pytest.fixture
def mock_data_filter():
    """
    Return a mock DataFilter object with preset behaviors for testing.
    
    The mock provides fixed return values for `calculate_cutoff_time`, `should_process_entry`, and `update_processed_hashes` methods to facilitate predictable test scenarios.
    """
    mock = Mock()
    mock.calculate_cutoff_time.return_value = datetime(
        2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc
    )
    mock.should_process_entry.return_value = True
    mock.update_processed_hashes.return_value = None
    return mock


@pytest.fixture
def mock_usage_entry_mapper():
    """
    Provides a mock UsageEntryMapper with a preset map method for testing.
    
    The returned mock's `map` method always returns a UsageEntry instance with fixed values, enabling predictable behavior in tests that require usage entry mapping.
    """
    mock = Mock()
    mock.map.return_value = UsageEntry(
        timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        input_tokens=100,
        output_tokens=50,
        cache_creation_tokens=0,
        cache_read_tokens=0,
        cost_usd=0.001,
        model="claude-3-haiku",
        message_id="msg_123",
        request_id="req_456",
    )
    return mock


@pytest.fixture
def mock_data_processor():
    """
    Provides a mock DataProcessor with preset return values for process_files and load_all_raw_entries methods, used for testing.
    """
    mock = Mock()
    mock.process_files.return_value = (
        [
            UsageEntry(
                timestamp=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                input_tokens=100,
                output_tokens=50,
                cache_creation_tokens=0,
                cache_read_tokens=0,
                cost_usd=0.001,
                model="claude-3-haiku",
                message_id="msg_123",
                request_id="req_456",
            )
        ],
        None,
    )
    mock.load_all_raw_entries.return_value = [
        {"raw_data": "entry1"},
        {"raw_data": "entry2"},
    ]
    return mock


@pytest.fixture
def mock_data_manager():
    """
    Provides a mock DataManager instance with preset monitoring data for use in tests.
    
    Returns:
        Mock: A mock object simulating DataManager behavior, including a sample session block and attributes for cache age, last error, and last successful fetch time.
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
    mock.cache_age = 0.0
    mock.last_error = None
    mock.last_successful_fetch_time = None
    return mock


@pytest.fixture
def mock_session_monitor():
    """
    Provides a mock SessionMonitor object with preset session data and update behavior for use in monitoring-related tests.
    
    Returns:
        Mock: A mock SessionMonitor with predefined session ID, session count, session history, and update method.
    """
    mock = Mock()
    mock.update.return_value = (True, [])
    mock.current_session_id = "session_1"
    mock.session_count = 1
    mock.session_history = [
        {
            "id": "session_1",
            "started_at": "2024-01-01T12:00:00Z",
            "tokens": 1000,
            "cost": 0.05,
        }
    ]
    return mock


@pytest.fixture
def sample_monitoring_data():
    """
    Return a sample monitoring data dictionary with two session blocks for testing purposes.
    
    Returns:
        dict: Monitoring data containing two session records with session ID, activity status, token count, cost, and start time.
    """
    return {
        "blocks": [
            {
                "id": "session_1",
                "isActive": True,
                "totalTokens": 1000,
                "costUSD": 0.05,
                "startTime": "2024-01-01T12:00:00Z",
            },
            {
                "id": "session_2",
                "isActive": False,
                "totalTokens": 500,
                "costUSD": 0.025,
                "startTime": "2024-01-01T11:00:00Z",
            },
        ]
    }


@pytest.fixture
def sample_session_data():
    """
    Return a dictionary representing a single active session with preset tokens, cost, and start time for testing purposes.
    """
    return {
        "id": "session_1",
        "isActive": True,
        "totalTokens": 1000,
        "costUSD": 0.05,
        "startTime": "2024-01-01T12:00:00Z",
    }


@pytest.fixture
def sample_invalid_monitoring_data():
    """
    Return a dictionary representing monitoring data with intentionally invalid field types for testing error handling scenarios.
    """
    return {
        "blocks": [
            {
                "id": "session_1",
                "isActive": "not_boolean",
                "totalTokens": "not_number",
                "costUSD": None,
            }
        ]
    }


@pytest.fixture
def mock_orchestrator_args():
    """
    Return a mock object simulating command-line arguments for orchestrator tests.
    
    The mock includes attributes for plan, timezone, refresh rate, and custom token limit.
    """
    args = Mock()
    args.plan = "pro"
    args.timezone = "UTC"
    args.refresh_rate = 10
    args.custom_limit_tokens = None
    return args
