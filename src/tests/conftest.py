"""Shared pytest fixtures for Claude Monitor tests."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Set
from unittest.mock import Mock

import pytest

from claude_monitor.core.models import CostMode, UsageEntry


@pytest.fixture
def mock_pricing_calculator() -> Mock:
    """Mock PricingCalculator for testing."""
    mock = Mock()
    mock.calculate_cost_for_entry.return_value = 0.001
    return mock


@pytest.fixture
def mock_timezone_handler() -> Mock:
    """Mock TimezoneHandler for testing."""
    mock = Mock()
    mock.parse_timestamp.return_value = datetime(
        2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc
    )
    mock.ensure_utc.return_value = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    return mock


@pytest.fixture
def sample_usage_entry() -> UsageEntry:
    """Sample UsageEntry for testing."""
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
def sample_valid_data() -> Dict[str, Any]:
    """Sample valid data structure for testing."""
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
def sample_assistant_data() -> Dict[str, Any]:
    """Sample assistant-type data for testing."""
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
def sample_user_data() -> Dict[str, Any]:
    """Sample user-type data for testing."""
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
def sample_malformed_data() -> Dict[str, Any]:
    """Sample malformed data for testing error handling."""
    return {
        "timestamp": "invalid_timestamp",
        "message": "not_a_dict",
        "usage": {"input_tokens": "not_a_number", "output_tokens": None},
    }


@pytest.fixture
def sample_minimal_data() -> Dict[str, Any]:
    """Sample minimal valid data for testing."""
    return {
        "timestamp": "2024-01-01T12:00:00Z",
        "usage": {"input_tokens": 100, "output_tokens": 50},
        "request_id": "req_456",
    }


@pytest.fixture
def sample_empty_tokens_data() -> Dict[str, Any]:
    """Sample data with empty/zero tokens for testing."""
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
def sample_duplicate_data() -> List[Dict[str, Any]]:
    """Sample data for testing duplicate detection."""
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
def all_cost_modes() -> List[CostMode]:
    """All available cost modes for testing."""
    return [CostMode.AUTO]


@pytest.fixture
def sample_cutoff_time() -> datetime:
    """Sample cutoff time for testing."""
    return datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def sample_processed_hashes() -> Set[str]:
    """Sample processed hashes set for testing."""
    return {"msg_existing:req_existing", "msg_old:req_old"}


@pytest.fixture
def mock_file_reader() -> Mock:
    """Mock JsonlFileReader for testing."""
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
def mock_data_filter() -> Mock:
    """Mock DataFilter for testing."""
    mock = Mock()
    mock.calculate_cutoff_time.return_value = datetime(
        2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc
    )
    mock.should_process_entry.return_value = True
    mock.update_processed_hashes.return_value = None
    return mock


@pytest.fixture
def mock_usage_entry_mapper() -> Mock:
    """Mock UsageEntryMapper for testing."""
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
def mock_data_processor() -> Mock:
    """Mock DataProcessor for testing."""
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
def mock_data_manager() -> Mock:
    """Mock DataManager for monitoring tests."""
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
def mock_session_monitor() -> Mock:
    """Mock SessionMonitor for monitoring tests."""
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
def sample_monitoring_data() -> Dict[str, Any]:
    """Sample monitoring data structure for testing."""
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
def sample_session_data() -> Dict[str, Any]:
    """Sample session data for testing."""
    return {
        "id": "session_1",
        "isActive": True,
        "totalTokens": 1000,
        "costUSD": 0.05,
        "startTime": "2024-01-01T12:00:00Z",
    }


@pytest.fixture
def sample_invalid_monitoring_data() -> Dict[str, Any]:
    """Sample invalid monitoring data for testing."""
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
def mock_orchestrator_args() -> Mock:
    """Mock command line arguments for orchestrator testing."""
    args = Mock()
    args.plan = "pro"
    args.timezone = "UTC"
    args.refresh_rate = 10
    args.custom_limit_tokens = None
    return args
