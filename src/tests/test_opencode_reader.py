"""Tests for OpenCode data reader module."""

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch

import pytest

from claude_monitor.core.models import CostMode
from claude_monitor.data.opencode_reader import (
    OPENCODE_STORAGE_PATH,
    _find_message_files,
    _process_message_file,
    detect_opencode_installation,
    get_opencode_storage_path,
    load_opencode_entries,
    load_opencode_raw_entries,
)


class TestOpenCodeDetection:
    """Tests for OpenCode installation detection."""

    def test_detect_opencode_installation_exists(self, tmp_path: Path) -> None:
        """Test detection when OpenCode storage exists."""
        message_dir = tmp_path / "message"
        message_dir.mkdir(parents=True)
        (message_dir / "ses_test").mkdir()

        # Patch OPENCODE_STORAGE_PATH to use the tmp_path directly (no ~ expansion needed)
        with patch(
            "claude_monitor.data.opencode_reader.OPENCODE_STORAGE_PATH",
            str(tmp_path),
        ):
            result = detect_opencode_installation()
            assert result is True, "Should detect OpenCode when message dir exists"

    def test_detect_opencode_installation_not_exists(self) -> None:
        """Test detection when OpenCode storage doesn't exist."""
        with patch(
            "claude_monitor.data.opencode_reader.OPENCODE_STORAGE_PATH",
            "/nonexistent/path",
        ):
            result = detect_opencode_installation()
            assert result is False

    def test_get_opencode_storage_path(self) -> None:
        """Test getting OpenCode storage path."""
        path = get_opencode_storage_path()
        assert isinstance(path, Path)
        assert "opencode" in str(path)


class TestFindMessageFiles:
    """Tests for finding message files."""

    def test_find_message_files_empty_directory(self, tmp_path: Path) -> None:
        """Test finding files in empty directory."""
        result = _find_message_files(tmp_path)
        assert result == []

    def test_find_message_files_nonexistent(self) -> None:
        """Test finding files in nonexistent directory."""
        result = _find_message_files(Path("/nonexistent"))
        assert result == []

    def test_find_message_files_with_messages(self, tmp_path: Path) -> None:
        """Test finding message files in valid structure."""
        # Create session directory with message files
        session_dir = tmp_path / "ses_abc123"
        session_dir.mkdir()
        (session_dir / "msg_001.json").write_text("{}")
        (session_dir / "msg_002.json").write_text("{}")
        (session_dir / "other.txt").write_text("not a message")

        result = _find_message_files(tmp_path)
        assert len(result) == 2
        assert all(f.name.startswith("msg_") for f in result)


class TestProcessMessageFile:
    """Tests for processing individual message files."""

    @pytest.fixture
    def sample_message_data(self) -> Dict[str, Any]:
        """Create sample OpenCode message data."""
        return {
            "id": "msg_test123",
            "sessionID": "ses_abc",
            "role": "assistant",
            "time": {
                "created": 1766649366187,
                "completed": 1766649369986,
            },
            "modelID": "claude-opus-4-5",
            "providerID": "anthropic",
            "tokens": {
                "input": 100,
                "output": 500,
                "reasoning": 50,
                "cache": {"read": 1000, "write": 200},
            },
            "finish": "end_turn",
        }

    def test_process_valid_message(
        self, tmp_path: Path, sample_message_data: Dict[str, Any]
    ) -> None:
        """Test processing a valid assistant message."""
        from claude_monitor.core.pricing import PricingCalculator

        msg_file = tmp_path / "msg_test.json"
        msg_file.write_text(json.dumps(sample_message_data))

        pricing = PricingCalculator()
        processed_ids: set = set()

        entry, raw = _process_message_file(
            msg_file,
            CostMode.AUTO,
            None,
            processed_ids,
            True,
            pricing,
        )

        assert entry is not None
        assert entry.input_tokens == 100
        assert entry.output_tokens == 550  # output + reasoning
        assert entry.cache_read_tokens == 1000
        assert entry.cache_creation_tokens == 200
        assert entry.model == "claude-opus-4-5"
        assert entry.message_id == "msg_test123"
        assert raw is not None

    def test_process_user_message_skipped(self, tmp_path: Path) -> None:
        """Test that user messages are skipped."""
        from claude_monitor.core.pricing import PricingCalculator

        msg_data = {"id": "msg_user", "role": "user", "tokens": {"input": 100}}
        msg_file = tmp_path / "msg_user.json"
        msg_file.write_text(json.dumps(msg_data))

        pricing = PricingCalculator()
        entry, _ = _process_message_file(
            msg_file,
            CostMode.AUTO,
            None,
            set(),
            False,
            pricing,
        )

        assert entry is None

    def test_process_message_without_tokens_skipped(self, tmp_path: Path) -> None:
        """Test that messages without tokens are skipped."""
        from claude_monitor.core.pricing import PricingCalculator

        msg_data = {"id": "msg_no_tokens", "role": "assistant"}
        msg_file = tmp_path / "msg_no_tokens.json"
        msg_file.write_text(json.dumps(msg_data))

        pricing = PricingCalculator()
        entry, _ = _process_message_file(
            msg_file,
            CostMode.AUTO,
            None,
            set(),
            False,
            pricing,
        )

        assert entry is None

    def test_process_duplicate_message_skipped(
        self, tmp_path: Path, sample_message_data: Dict[str, Any]
    ) -> None:
        """Test that duplicate messages are skipped."""
        from claude_monitor.core.pricing import PricingCalculator

        msg_file = tmp_path / "msg_dup.json"
        msg_file.write_text(json.dumps(sample_message_data))

        pricing = PricingCalculator()
        processed_ids = {"msg_test123"}  # Already processed

        entry, _ = _process_message_file(
            msg_file,
            CostMode.AUTO,
            None,
            processed_ids,
            False,
            pricing,
        )

        assert entry is None

    def test_process_old_message_filtered_by_cutoff(
        self, tmp_path: Path, sample_message_data: Dict[str, Any]
    ) -> None:
        """Test that old messages are filtered by cutoff time."""
        from claude_monitor.core.pricing import PricingCalculator

        msg_file = tmp_path / "msg_old.json"
        msg_file.write_text(json.dumps(sample_message_data))

        pricing = PricingCalculator()
        # Set cutoff to future
        future_cutoff_ms = int(datetime.now(timezone.utc).timestamp() * 1000) + 1000000

        entry, _ = _process_message_file(
            msg_file,
            CostMode.AUTO,
            future_cutoff_ms,
            set(),
            False,
            pricing,
        )

        assert entry is None

    def test_process_invalid_json_handled(self, tmp_path: Path) -> None:
        """Test that invalid JSON is handled gracefully."""
        from claude_monitor.core.pricing import PricingCalculator

        msg_file = tmp_path / "msg_invalid.json"
        msg_file.write_text("not valid json")

        pricing = PricingCalculator()
        entry, _ = _process_message_file(
            msg_file,
            CostMode.AUTO,
            None,
            set(),
            False,
            pricing,
        )

        assert entry is None


class TestLoadOpenCodeEntries:
    """Tests for loading OpenCode entries."""

    def test_load_from_nonexistent_path(self) -> None:
        """Test loading from nonexistent path returns empty list."""
        entries, raw = load_opencode_entries(
            data_path="/nonexistent/path",
            hours_back=24,
        )
        assert entries == []
        assert raw is None

    def test_load_with_real_structure(self, tmp_path: Path) -> None:
        """Test loading from realistic directory structure."""
        # Create message directory structure
        storage = tmp_path / "storage"
        message_dir = storage / "message"
        session_dir = message_dir / "ses_test123"
        session_dir.mkdir(parents=True)

        # Create sample message files
        msg1 = {
            "id": "msg_001",
            "sessionID": "ses_test123",
            "role": "assistant",
            "time": {"created": int(datetime.now(timezone.utc).timestamp() * 1000)},
            "modelID": "claude-sonnet-4-5",
            "tokens": {
                "input": 10,
                "output": 100,
                "reasoning": 0,
                "cache": {"read": 0, "write": 0},
            },
        }
        msg2 = {
            "id": "msg_002",
            "sessionID": "ses_test123",
            "role": "assistant",
            "time": {"created": int(datetime.now(timezone.utc).timestamp() * 1000)},
            "modelID": "claude-sonnet-4-5",
            "tokens": {
                "input": 20,
                "output": 200,
                "reasoning": 0,
                "cache": {"read": 50, "write": 10},
            },
        }

        (session_dir / "msg_001.json").write_text(json.dumps(msg1))
        (session_dir / "msg_002.json").write_text(json.dumps(msg2))

        entries, raw = load_opencode_entries(
            data_path=str(storage),
            hours_back=24,
            include_raw=True,
        )

        assert len(entries) == 2
        assert raw is not None
        assert len(raw) == 2

        # Verify entries are sorted by timestamp
        assert entries[0].timestamp <= entries[1].timestamp


class TestLoadOpenCodeRawEntries:
    """Tests for loading raw OpenCode entries."""

    def test_load_raw_from_nonexistent_path(self) -> None:
        """Test loading raw from nonexistent path returns empty list."""
        entries = load_opencode_raw_entries(data_path="/nonexistent/path")
        assert entries == []

    def test_load_raw_filters_non_token_messages(self, tmp_path: Path) -> None:
        """Test that messages without tokens are filtered."""
        storage = tmp_path / "storage"
        message_dir = storage / "message"
        session_dir = message_dir / "ses_test"
        session_dir.mkdir(parents=True)

        # Message with tokens
        msg_with_tokens = {
            "id": "msg_001",
            "role": "assistant",
            "tokens": {"input": 10, "output": 100},
        }
        # Message without tokens
        msg_no_tokens = {"id": "msg_002", "role": "user"}

        (session_dir / "msg_001.json").write_text(json.dumps(msg_with_tokens))
        (session_dir / "msg_002.json").write_text(json.dumps(msg_no_tokens))

        entries = load_opencode_raw_entries(data_path=str(storage))

        assert len(entries) == 1
        assert entries[0]["id"] == "msg_001"


class TestDataSourceIntegration:
    """Tests for data source detection and unified loading."""

    def test_data_source_enum_values(self) -> None:
        """Test DataSource enum has expected values."""
        from claude_monitor.data.reader import DataSource

        assert DataSource.AUTO.value == "auto"
        assert DataSource.CLAUDE.value == "claude"
        assert DataSource.OPENCODE.value == "opencode"

    def test_get_data_source_info_opencode(self) -> None:
        """Test getting info for OpenCode source."""
        from claude_monitor.data.reader import DataSource, get_data_source_info

        info = get_data_source_info(DataSource.OPENCODE)
        assert info["source"] == "opencode"
        assert "opencode" in info["description"].lower()

    def test_get_data_source_info_claude(self) -> None:
        """Test getting info for Claude source."""
        from claude_monitor.data.reader import DataSource, get_data_source_info

        info = get_data_source_info(DataSource.CLAUDE)
        assert info["source"] == "claude"
        assert "claude" in info["description"].lower()
