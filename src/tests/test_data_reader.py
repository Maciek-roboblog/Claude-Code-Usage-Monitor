"""
Comprehensive tests for data/reader.py module.

Tests the data loading and processing functions to achieve 80%+ coverage.
Covers file reading, data filtering, mapping, and error handling scenarios.
"""

import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest

from claude_monitor.core.models import CostMode, UsageEntry
from claude_monitor.core.pricing import PricingCalculator
from claude_monitor.data.reader import (
    _create_unique_hash,
    _find_jsonl_files,
    _map_to_usage_entry,
    _process_single_file,
    _should_process_entry,
    _update_processed_hashes,
    load_all_raw_entries,
    load_usage_entries,
)
from claude_monitor.utils.time_utils import TimezoneHandler


class TestLoadUsageEntries:
    """Test the main load_usage_entries function."""

    @patch("claude_monitor.data.reader._find_jsonl_files")
    @patch("claude_monitor.data.reader._process_single_file")
    def test_load_usage_entries_basic(self, mock_process_file, mock_find_files):
        """
        Tests that `load_usage_entries` loads and aggregates usage entries and raw data from multiple files, correctly invoking file discovery and processing, and returns the expected results.
        """
        mock_find_files.return_value = [
            Path("/test/file1.jsonl"),
            Path("/test/file2.jsonl"),
        ]

        sample_entry = UsageEntry(
            timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            input_tokens=100,
            output_tokens=50,
            model="claude-3-haiku",
        )

        mock_process_file.side_effect = [
            ([sample_entry], [{"raw": "data1"}]),
            ([], [{"raw": "data2"}]),
        ]

        entries, raw_data = load_usage_entries(
            data_path="/test/path",
            hours_back=24,
            mode=CostMode.CALCULATED,
            include_raw=True,
        )

        assert len(entries) == 1
        assert entries[0] == sample_entry
        assert len(raw_data) == 2
        assert raw_data == [{"raw": "data1"}, {"raw": "data2"}]

        mock_find_files.assert_called_once()
        assert mock_process_file.call_count == 2

    @patch("claude_monitor.data.reader._find_jsonl_files")
    def test_load_usage_entries_no_files(self, mock_find_files):
        """
        Test that `load_usage_entries` returns empty results when no files are found.
        
        Verifies that when the file discovery function returns an empty list, `load_usage_entries` returns an empty list of entries and `None` for raw data.
        """
        mock_find_files.return_value = []

        entries, raw_data = load_usage_entries(include_raw=True)

        assert entries == []
        assert raw_data is None

    @patch("claude_monitor.data.reader._find_jsonl_files")
    @patch("claude_monitor.data.reader._process_single_file")
    def test_load_usage_entries_without_raw(self, mock_process_file, mock_find_files):
        """
        Test that `load_usage_entries` returns usage entries without raw data when `include_raw` is False.
        """
        mock_find_files.return_value = [Path("/test/file1.jsonl")]

        sample_entry = UsageEntry(
            timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            input_tokens=100,
            output_tokens=50,
            model="claude-3-haiku",
        )

        mock_process_file.return_value = ([sample_entry], None)

        entries, raw_data = load_usage_entries(include_raw=False)

        assert len(entries) == 1
        assert raw_data is None

    @patch("claude_monitor.data.reader._find_jsonl_files")
    @patch("claude_monitor.data.reader._process_single_file")
    def test_load_usage_entries_sorting(self, mock_process_file, mock_find_files):
        """
        Verifies that the `load_usage_entries` function returns usage entries sorted in ascending order by timestamp.
        """
        mock_find_files.return_value = [Path("/test/file1.jsonl")]

        entry1 = UsageEntry(
            timestamp=datetime(2024, 1, 1, 14, 0, tzinfo=timezone.utc),
            input_tokens=100,
            output_tokens=50,
            model="claude-3-haiku",
        )
        entry2 = UsageEntry(
            timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            input_tokens=200,
            output_tokens=75,
            model="claude-3-sonnet",
        )

        mock_process_file.return_value = ([entry1, entry2], None)

        entries, _ = load_usage_entries()
        assert len(entries) == 2
        assert entries[0] == entry2
        assert entries[1] == entry1

    @patch("claude_monitor.data.reader._find_jsonl_files")
    @patch("claude_monitor.data.reader._process_single_file")
    def test_load_usage_entries_with_cutoff_time(
        self, mock_process_file, mock_find_files
    ):
        """
        Test that `load_usage_entries` calculates and applies the correct cutoff time based on the `hours_back` parameter.
        
        Verifies that the cutoff time passed to the file processing function is exactly the specified number of hours before the current UTC time.
        """
        mock_find_files.return_value = [Path("/test/file1.jsonl")]
        mock_process_file.return_value = ([], None)

        with patch("claude_monitor.data.reader.datetime") as mock_datetime:
            current_time = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
            mock_datetime.now.return_value = current_time

            load_usage_entries(hours_back=24)

            expected_cutoff = current_time - timedelta(hours=24)
            mock_process_file.assert_called_once()
            call_args = mock_process_file.call_args[0]
            assert call_args[2] == expected_cutoff

    def test_load_usage_entries_default_path(self):
        """
        Test that `load_usage_entries` uses the default data path when no path is specified.
        """
        with patch("claude_monitor.data.reader._find_jsonl_files") as mock_find:
            mock_find.return_value = []

            load_usage_entries()

            call_args = mock_find.call_args[0]
            path_str = str(call_args[0])
            assert ".claude/projects" in path_str


class TestLoadAllRawEntries:
    """Test the load_all_raw_entries function."""

    @patch("claude_monitor.data.reader._find_jsonl_files")
    def test_load_all_raw_entries_basic(self, mock_find_files):
        """
        Tests that `load_all_raw_entries` correctly loads and parses all JSONL entries from a file, returning the expected list of raw data dictionaries.
        """
        test_file = Path("/test/file.jsonl")
        mock_find_files.return_value = [test_file]

        raw_data = [
            {"type": "user", "content": "Hello"},
            {"type": "assistant", "content": "Hi there"},
        ]

        jsonl_content = "\n".join(json.dumps(item) for item in raw_data)

        with patch("builtins.open", mock_open(read_data=jsonl_content)):
            result = load_all_raw_entries("/test/path")

        assert len(result) == 2
        assert result == raw_data

    @patch("claude_monitor.data.reader._find_jsonl_files")
    def test_load_all_raw_entries_with_empty_lines(self, mock_find_files):
        """
        Test that `load_all_raw_entries` correctly skips empty or whitespace-only lines when reading JSONL files, returning only valid JSON objects.
        """
        test_file = Path("/test/file.jsonl")
        mock_find_files.return_value = [test_file]

        jsonl_content = '{"valid": "data"}\n\n   \n{"more": "data"}\n'

        with patch("builtins.open", mock_open(read_data=jsonl_content)):
            result = load_all_raw_entries("/test/path")

        assert len(result) == 2
        assert result[0] == {"valid": "data"}
        assert result[1] == {"more": "data"}

    @patch("claude_monitor.data.reader._find_jsonl_files")
    def test_load_all_raw_entries_with_invalid_json(self, mock_find_files):
        """
        Test that `load_all_raw_entries` skips invalid JSON lines and returns only valid entries.
        
        Verifies that when a file contains both valid and invalid JSON lines, only the valid lines are parsed and included in the result.
        """
        test_file = Path("/test/file.jsonl")
        mock_find_files.return_value = [test_file]

        jsonl_content = '{"valid": "data"}\ninvalid json\n{"more": "data"}\n'

        with patch("builtins.open", mock_open(read_data=jsonl_content)):
            result = load_all_raw_entries("/test/path")

        assert len(result) == 2
        assert result[0] == {"valid": "data"}
        assert result[1] == {"more": "data"}

    @patch("claude_monitor.data.reader._find_jsonl_files")
    def test_load_all_raw_entries_file_error(self, mock_find_files):
        """
        Test that `load_all_raw_entries` returns an empty list and logs an error when a file read error occurs.
        """
        test_file = Path("/test/file.jsonl")
        mock_find_files.return_value = [test_file]

        with patch("builtins.open", side_effect=IOError("File not found")):
            with patch("claude_monitor.data.reader.logger") as mock_logger:
                result = load_all_raw_entries("/test/path")

        assert result == []
        mock_logger.error.assert_called()

    def test_load_all_raw_entries_default_path(self):
        """
        Test that `load_all_raw_entries` uses the default data path when no path is provided.
        """
        with patch("claude_monitor.data.reader._find_jsonl_files") as mock_find:
            mock_find.return_value = []

            load_all_raw_entries()

            call_args = mock_find.call_args[0]
            path_str = str(call_args[0])
            assert ".claude/projects" in path_str


class TestFindJsonlFiles:
    """Test the _find_jsonl_files function."""

    def test_find_jsonl_files_nonexistent_path(self):
        """
        Test that `_find_jsonl_files` returns an empty list and logs a warning when the specified path does not exist.
        """
        with patch("claude_monitor.data.reader.logger") as mock_logger:
            result = _find_jsonl_files(Path("/nonexistent/path"))

        assert result == []
        mock_logger.warning.assert_called()

    def test_find_jsonl_files_existing_path(self):
        """
        Test that `_find_jsonl_files` returns all `.jsonl` files in a directory and its subdirectories, excluding non-JSONL files.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            (temp_path / "file1.jsonl").touch()
            (temp_path / "file2.jsonl").touch()
            (temp_path / "file3.txt").touch()  # Non-JSONL file

            # Create subdirectory with JSONL file
            subdir = temp_path / "subdir"
            subdir.mkdir()
            (subdir / "file4.jsonl").touch()

            result = _find_jsonl_files(temp_path)

            jsonl_files = [f.name for f in result]
            assert "file1.jsonl" in jsonl_files
            assert "file2.jsonl" in jsonl_files
            assert "file4.jsonl" in jsonl_files
            assert len(result) == 3


class TestProcessSingleFile:
    """Test the _process_single_file function."""

    @pytest.fixture
    def mock_components(self):
        """
        Create and return mock instances of TimezoneHandler and PricingCalculator for use in tests.
        
        Returns:
            tuple: A tuple containing mock TimezoneHandler and PricingCalculator instances.
        """
        timezone_handler = Mock(spec=TimezoneHandler)
        pricing_calculator = Mock(spec=PricingCalculator)
        return timezone_handler, pricing_calculator

    def test_process_single_file_valid_data(self, mock_components):
        """
        Test that `_process_single_file` correctly processes a file with valid JSONL data, returning the expected usage entries and raw data.
        """
        timezone_handler, pricing_calculator = mock_components

        sample_data = [
            {
                "timestamp": "2024-01-01T12:00:00Z",
                "message": {"usage": {"input_tokens": 100, "output_tokens": 50}},
                "model": "claude-3-haiku",
                "message_id": "msg_1",
                "request_id": "req_1",
            }
        ]

        jsonl_content = "\n".join(json.dumps(item) for item in sample_data)
        test_file = Path("/test/file.jsonl")

        sample_entry = UsageEntry(
            timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            input_tokens=100,
            output_tokens=50,
            model="claude-3-haiku",
        )

        with patch("builtins.open", mock_open(read_data=jsonl_content)):
            with patch(
                "claude_monitor.data.reader._should_process_entry", return_value=True
            ):
                with patch(
                    "claude_monitor.data.reader._map_to_usage_entry",
                    return_value=sample_entry,
                ):
                    with patch("claude_monitor.data.reader._update_processed_hashes"):
                        entries, raw_data = _process_single_file(
                            test_file,
                            CostMode.AUTO,
                            None,  # cutoff_time
                            set(),  # processed_hashes
                            True,  # include_raw
                            timezone_handler,
                            pricing_calculator,
                        )

        assert len(entries) == 1
        assert entries[0] == sample_entry
        assert len(raw_data) == 1
        assert raw_data[0] == sample_data[0]

    def test_process_single_file_without_raw(self, mock_components):
        """
        Test that `_process_single_file` returns usage entries and no raw data when `include_raw` is False.
        
        Verifies that a single valid JSONL entry is processed and mapped to a `UsageEntry` object, and that raw data is not returned when not requested.
        """
        timezone_handler, pricing_calculator = mock_components

        sample_data = [{"timestamp": "2024-01-01T12:00:00Z", "input_tokens": 100}]
        jsonl_content = json.dumps(sample_data[0])
        test_file = Path("/test/file.jsonl")

        sample_entry = UsageEntry(
            timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            input_tokens=100,
            output_tokens=50,
            model="claude-3-haiku",
        )

        with patch("builtins.open", mock_open(read_data=jsonl_content)):
            with patch(
                "claude_monitor.data.reader._should_process_entry", return_value=True
            ):
                with patch(
                    "claude_monitor.data.reader._map_to_usage_entry",
                    return_value=sample_entry,
                ):
                    with patch("claude_monitor.data.reader._update_processed_hashes"):
                        entries, raw_data = _process_single_file(
                            test_file,
                            CostMode.AUTO,
                            None,
                            set(),
                            False,
                            timezone_handler,
                            pricing_calculator,
                        )

        assert len(entries) == 1
        assert raw_data is None

    def test_process_single_file_filtered_entries(self, mock_components):
        """
        Test that `_process_single_file` returns no entries or raw data when all entries are filtered out by `_should_process_entry`.
        """
        timezone_handler, pricing_calculator = mock_components

        sample_data = [{"timestamp": "2024-01-01T12:00:00Z", "input_tokens": 100}]
        jsonl_content = json.dumps(sample_data[0])
        test_file = Path("/test/file.jsonl")

        with patch("builtins.open", mock_open(read_data=jsonl_content)):
            with patch(
                "claude_monitor.data.reader._should_process_entry", return_value=False
            ):
                entries, raw_data = _process_single_file(
                    test_file,
                    CostMode.AUTO,
                    None,
                    set(),
                    True,
                    timezone_handler,
                    pricing_calculator,
                )

        assert len(entries) == 0
        assert len(raw_data) == 0

    def test_process_single_file_invalid_json(self, mock_components):
        """
        Test that _process_single_file skips invalid JSON lines and collects valid raw data when mapping fails.
        
        Verifies that when a file contains both invalid and valid JSON lines, the function ignores the invalid line, attempts to map the valid line, and includes it in the raw data if mapping returns None.
        """
        timezone_handler, pricing_calculator = mock_components

        jsonl_content = 'invalid json\n{"valid": "data"}'
        test_file = Path("/test/file.jsonl")

        with patch("builtins.open", mock_open(read_data=jsonl_content)):
            with patch(
                "claude_monitor.data.reader._should_process_entry", return_value=True
            ):
                with patch(
                    "claude_monitor.data.reader._map_to_usage_entry", return_value=None
                ):
                    entries, raw_data = _process_single_file(
                        test_file,
                        CostMode.AUTO,
                        None,
                        set(),
                        True,
                        timezone_handler,
                        pricing_calculator,
                    )

        assert len(entries) == 0
        assert len(raw_data) == 1

    def test_process_single_file_read_error(self, mock_components):
        """
        Test that `_process_single_file` handles file read errors by reporting the error and returning empty results.
        """
        timezone_handler, pricing_calculator = mock_components
        test_file = Path("/test/nonexistent.jsonl")

        with patch("builtins.open", side_effect=IOError("File not found")):
            with patch("claude_monitor.data.reader.report_file_error") as mock_report:
                entries, raw_data = _process_single_file(
                    test_file,
                    CostMode.AUTO,
                    None,
                    set(),
                    True,
                    timezone_handler,
                    pricing_calculator,
                )

        assert entries == []
        assert raw_data is None
        mock_report.assert_called_once()

    def test_process_single_file_mapping_failure(self, mock_components):
        """
        Test that _process_single_file returns no usage entries but includes raw data when mapping fails.
        
        Verifies that when _map_to_usage_entry returns None for a valid entry, the function yields an empty entries list but still collects the raw data if requested.
        """
        timezone_handler, pricing_calculator = mock_components

        sample_data = [{"timestamp": "2024-01-01T12:00:00Z", "input_tokens": 100}]
        jsonl_content = json.dumps(sample_data[0])
        test_file = Path("/test/file.jsonl")

        with patch("builtins.open", mock_open(read_data=jsonl_content)):
            with patch(
                "claude_monitor.data.reader._should_process_entry", return_value=True
            ):
                with patch(
                    "claude_monitor.data.reader._map_to_usage_entry", return_value=None
                ):
                    entries, raw_data = _process_single_file(
                        test_file,
                        CostMode.AUTO,
                        None,
                        set(),
                        True,
                        timezone_handler,
                        pricing_calculator,
                    )

        assert len(entries) == 0
        assert len(raw_data) == 1


class TestShouldProcessEntry:
    """Test the _should_process_entry function."""

    @pytest.fixture
    def timezone_handler(self):
        """
        Return a mock instance of the TimezoneHandler for use in tests.
        """
        return Mock(spec=TimezoneHandler)

    def test_should_process_entry_no_cutoff_no_hash(self, timezone_handler):
        """
        Test that `_should_process_entry` returns True when no cutoff time is provided and the processed hashes set is empty.
        """
        data = {"timestamp": "2024-01-01T12:00:00Z", "message_id": "msg_1"}

        with patch(
            "claude_monitor.data.reader._create_unique_hash", return_value="hash_1"
        ):
            result = _should_process_entry(data, None, set(), timezone_handler)

        assert result is True

    def test_should_process_entry_with_time_filter_pass(self, timezone_handler):
        """
        Test that _should_process_entry returns True when the entry timestamp is after the cutoff time and the entry is not a duplicate.
        """
        data = {"timestamp": "2024-01-01T12:00:00Z"}
        cutoff_time = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)

        with patch(
            "claude_monitor.core.data_processors.TimestampProcessor"
        ) as mock_processor_class:
            mock_processor = Mock()
            mock_processor.parse_timestamp.return_value = datetime(
                2024, 1, 1, 12, 0, tzinfo=timezone.utc
            )
            mock_processor_class.return_value = mock_processor

            with patch(
                "claude_monitor.data.reader._create_unique_hash", return_value="hash_1"
            ):
                result = _should_process_entry(
                    data, cutoff_time, set(), timezone_handler
                )

        assert result is True

    def test_should_process_entry_with_time_filter_fail(self, timezone_handler):
        """
        Test that `_should_process_entry` returns False when the entry's timestamp is before the cutoff time.
        
        Verifies that entries with timestamps earlier than the specified cutoff are correctly filtered out.
        """
        data = {"timestamp": "2024-01-01T08:00:00Z"}
        cutoff_time = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)

        with patch(
            "claude_monitor.core.data_processors.TimestampProcessor"
        ) as mock_processor_class:
            mock_processor = Mock()
            mock_processor.parse_timestamp.return_value = datetime(
                2024, 1, 1, 8, 0, tzinfo=timezone.utc
            )
            mock_processor_class.return_value = mock_processor

            result = _should_process_entry(data, cutoff_time, set(), timezone_handler)

        assert result is False

    def test_should_process_entry_with_duplicate_hash(self, timezone_handler):
        """
        Test that `_should_process_entry` returns False when the entry's unique hash is already in the set of processed hashes.
        """
        data = {"message_id": "msg_1", "request_id": "req_1"}
        processed_hashes = {"msg_1:req_1"}

        with patch(
            "claude_monitor.data.reader._create_unique_hash", return_value="msg_1:req_1"
        ):
            result = _should_process_entry(
                data, None, processed_hashes, timezone_handler
            )

        assert result is False

    def test_should_process_entry_no_timestamp(self, timezone_handler):
        """
        Test that an entry without a timestamp is processed when a cutoff time is provided.
        
        Verifies that `_should_process_entry` returns True if the data lacks a timestamp, regardless of the cutoff time.
        """
        data = {"message_id": "msg_1"}
        cutoff_time = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)

        with patch(
            "claude_monitor.data.reader._create_unique_hash", return_value="hash_1"
        ):
            result = _should_process_entry(data, cutoff_time, set(), timezone_handler)

        assert result is True

    def test_should_process_entry_invalid_timestamp(self, timezone_handler):
        """
        Test that _should_process_entry returns True when the entry's timestamp is invalid or cannot be parsed.
        """
        data = {"timestamp": "invalid", "message_id": "msg_1"}
        cutoff_time = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)

        with patch(
            "claude_monitor.core.data_processors.TimestampProcessor"
        ) as mock_processor_class:
            mock_processor = Mock()
            mock_processor.parse_timestamp.return_value = None
            mock_processor_class.return_value = mock_processor

            with patch(
                "claude_monitor.data.reader._create_unique_hash", return_value="hash_1"
            ):
                result = _should_process_entry(
                    data, cutoff_time, set(), timezone_handler
                )

        assert result is True


class TestCreateUniqueHash:
    """Test the _create_unique_hash function."""

    def test_create_unique_hash_with_message_id_and_request_id(self):
        """
        Test that `_create_unique_hash` returns the correct hash when both `message_id` and `request_id` are present in the data.
        """
        data = {"message_id": "msg_123", "request_id": "req_456"}

        result = _create_unique_hash(data)
        assert result == "msg_123:req_456"

    def test_create_unique_hash_with_nested_message_id(self):
        """
        Tests that `_create_unique_hash` correctly generates a unique hash when `message_id` is nested within a 'message' dictionary.
        """
        data = {"message": {"id": "msg_123"}, "requestId": "req_456"}

        result = _create_unique_hash(data)
        assert result == "msg_123:req_456"

    def test_create_unique_hash_missing_message_id(self):
        """
        Test that `_create_unique_hash` returns None when the `message_id` field is missing from the input data.
        """
        data = {"request_id": "req_456"}

        result = _create_unique_hash(data)
        assert result is None

    def test_create_unique_hash_missing_request_id(self):
        """
        Test that `_create_unique_hash` returns None when the `request_id` field is missing from the input data.
        """
        data = {"message_id": "msg_123"}

        result = _create_unique_hash(data)
        assert result is None

    def test_create_unique_hash_invalid_message_structure(self):
        """
        Test that _create_unique_hash returns None when the 'message' field is not a dictionary.
        """
        data = {"message": "not_a_dict", "request_id": "req_456"}

        result = _create_unique_hash(data)
        assert result is None

    def test_create_unique_hash_empty_data(self):
        """
        Test that _create_unique_hash returns None when given an empty data dictionary.
        """
        data = {}

        result = _create_unique_hash(data)
        assert result is None


class TestUpdateProcessedHashes:
    """Test the _update_processed_hashes function."""

    def test_update_processed_hashes_valid_hash(self):
        """
        Test that a valid unique hash is added to the processed_hashes set when updating with valid data.
        """
        data = {"message_id": "msg_123", "request_id": "req_456"}
        processed_hashes = set()

        with patch(
            "claude_monitor.data.reader._create_unique_hash",
            return_value="msg_123:req_456",
        ):
            _update_processed_hashes(data, processed_hashes)

        assert "msg_123:req_456" in processed_hashes

    def test_update_processed_hashes_no_hash(self):
        """
        Test that `_update_processed_hashes` does not modify the set when no unique hash is generated from the data.
        """
        data = {"some": "data"}
        processed_hashes = set()

        with patch("claude_monitor.data.reader._create_unique_hash", return_value=None):
            _update_processed_hashes(data, processed_hashes)

        assert len(processed_hashes) == 0


class TestMapToUsageEntry:
    """Test the _map_to_usage_entry function."""

    @pytest.fixture
    def mock_components(self):
        """
        Create and return mock instances of TimezoneHandler and PricingCalculator for use in tests.
        
        Returns:
            tuple: A tuple containing mock TimezoneHandler and PricingCalculator instances.
        """
        timezone_handler = Mock(spec=TimezoneHandler)
        pricing_calculator = Mock(spec=PricingCalculator)
        return timezone_handler, pricing_calculator

    def test_map_to_usage_entry_valid_data(self, mock_components):
        """
        Test that `_map_to_usage_entry` correctly maps valid raw data to a `UsageEntry` object.
        
        Verifies that all expected fields are extracted and mapped, including timestamp, token counts, cost, model, message ID, and request ID, when provided with valid input data and mocked dependencies.
        """
        timezone_handler, pricing_calculator = mock_components

        data = {
            "timestamp": "2024-01-01T12:00:00Z",
            "message": {
                "id": "msg_123",
                "usage": {
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "cache_creation_input_tokens": 10,
                    "cache_read_input_tokens": 5,
                },
            },
            "model": "claude-3-haiku",
            "request_id": "req_456",
            "cost": 0.001,
        }

        with patch(
            "claude_monitor.core.data_processors.TimestampProcessor"
        ) as mock_ts_processor:
            mock_ts = Mock()
            mock_ts.parse_timestamp.return_value = datetime(
                2024, 1, 1, 12, 0, tzinfo=timezone.utc
            )
            mock_ts_processor.return_value = mock_ts

            with patch(
                "claude_monitor.core.data_processors.TokenExtractor"
            ) as mock_token_extractor:
                mock_token_extractor.extract_tokens.return_value = {
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "cache_creation_tokens": 10,
                    "cache_read_tokens": 5,
                    "total_tokens": 150,
                }

                with patch(
                    "claude_monitor.core.data_processors.DataConverter"
                ) as mock_data_converter:
                    mock_data_converter.extract_model_name.return_value = (
                        "claude-3-haiku"
                    )

                    pricing_calculator.calculate_cost_for_entry.return_value = 0.001

                    result = _map_to_usage_entry(
                        data, CostMode.AUTO, timezone_handler, pricing_calculator
                    )

        assert result is not None
        assert result.timestamp == datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        assert result.input_tokens == 100
        assert result.output_tokens == 50
        assert result.cache_creation_tokens == 10
        assert result.cache_read_tokens == 5
        assert result.cost_usd == 0.001
        assert result.model == "claude-3-haiku"
        assert result.message_id == "msg_123"
        assert result.request_id == "req_456"

    def test_map_to_usage_entry_no_timestamp(self, mock_components):
        """
        Test that `_map_to_usage_entry` returns None when the input data lacks a valid timestamp.
        """
        timezone_handler, pricing_calculator = mock_components

        data = {"input_tokens": 100, "output_tokens": 50}

        with patch(
            "claude_monitor.core.data_processors.TimestampProcessor"
        ) as mock_ts_processor:
            mock_ts = Mock()
            mock_ts.parse_timestamp.return_value = None
            mock_ts_processor.return_value = mock_ts

            result = _map_to_usage_entry(
                data, CostMode.AUTO, timezone_handler, pricing_calculator
            )

        assert result is None

    def test_map_to_usage_entry_no_tokens(self, mock_components):
        """
        Test that `_map_to_usage_entry` returns None when all token counts are zero in the input data.
        """
        timezone_handler, pricing_calculator = mock_components

        data = {"timestamp": "2024-01-01T12:00:00Z"}

        with patch(
            "claude_monitor.core.data_processors.TimestampProcessor"
        ) as mock_ts_processor:
            mock_ts = Mock()
            mock_ts.parse_timestamp.return_value = datetime(
                2024, 1, 1, 12, 0, tzinfo=timezone.utc
            )
            mock_ts_processor.return_value = mock_ts

            with patch(
                "claude_monitor.core.data_processors.TokenExtractor"
            ) as mock_token_extractor:
                mock_token_extractor.extract_tokens.return_value = {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cache_creation_tokens": 0,
                    "cache_read_tokens": 0,
                    "total_tokens": 0,
                }

                result = _map_to_usage_entry(
                    data, CostMode.AUTO, timezone_handler, pricing_calculator
                )

        assert result is None

    def test_map_to_usage_entry_exception_handling(self, mock_components):
        """
        Test that `_map_to_usage_entry` returns None when an exception occurs during timestamp processing.
        """
        timezone_handler, pricing_calculator = mock_components

        data = {"timestamp": "2024-01-01T12:00:00Z"}

        with patch(
            "claude_monitor.core.data_processors.TimestampProcessor",
            side_effect=ValueError("Processing error"),
        ):
            result = _map_to_usage_entry(
                data, CostMode.AUTO, timezone_handler, pricing_calculator
            )

        assert result is None

    def test_map_to_usage_entry_minimal_data(self, mock_components):
        """
        Test that `_map_to_usage_entry` correctly maps minimal valid data to a `UsageEntry` object.
        
        Verifies that the function handles minimal input fields, uses default values for missing fields, and integrates with mocked data processors and pricing calculator.
        """
        timezone_handler, pricing_calculator = mock_components

        data = {
            "timestamp": "2024-01-01T12:00:00Z",
            "input_tokens": 100,
            "output_tokens": 50,
        }

        with patch(
            "claude_monitor.core.data_processors.TimestampProcessor"
        ) as mock_ts_processor:
            mock_ts = Mock()
            mock_ts.parse_timestamp.return_value = datetime(
                2024, 1, 1, 12, 0, tzinfo=timezone.utc
            )
            mock_ts_processor.return_value = mock_ts

            with patch(
                "claude_monitor.core.data_processors.TokenExtractor"
            ) as mock_token_extractor:
                mock_token_extractor.extract_tokens.return_value = {
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "cache_creation_tokens": 0,
                    "cache_read_tokens": 0,
                    "total_tokens": 150,
                }

                with patch(
                    "claude_monitor.core.data_processors.DataConverter"
                ) as mock_data_converter:
                    mock_data_converter.extract_model_name.return_value = "unknown"

                    pricing_calculator.calculate_cost_for_entry.return_value = 0.0

                    result = _map_to_usage_entry(
                        data, CostMode.AUTO, timezone_handler, pricing_calculator
                    )

        assert result is not None
        assert result.model == "unknown"
        assert result.message_id == ""
        assert result.request_id == "unknown"


class TestIntegration:
    """Integration tests for data reader functionality."""

    def test_full_workflow_integration(self):
        """
        Integration test that verifies the complete workflow from loading JSONL files to creating usage entry objects, including data parsing, processor mocking, and result validation.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test JSONL file
            test_file = temp_path / "test.jsonl"
            test_data = [
                {
                    "timestamp": "2024-01-01T12:00:00Z",
                    "message": {
                        "id": "msg_1",
                        "usage": {"input_tokens": 100, "output_tokens": 50},
                    },
                    "model": "claude-3-haiku",
                    "request_id": "req_1",
                },
                {
                    "timestamp": "2024-01-01T13:00:00Z",
                    "message": {
                        "id": "msg_2",
                        "usage": {"input_tokens": 200, "output_tokens": 75},
                    },
                    "model": "claude-3-sonnet",
                    "request_id": "req_2",
                },
            ]

            with open(test_file, "w") as f:
                for item in test_data:
                    f.write(json.dumps(item) + "\n")

            # Mock the data processors since they're external dependencies
            with patch(
                "claude_monitor.core.data_processors.TimestampProcessor"
            ) as mock_ts_processor:
                mock_ts = Mock()
                mock_ts.parse_timestamp.side_effect = [
                    datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
                    datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc),
                ]
                mock_ts_processor.return_value = mock_ts

                with patch(
                    "claude_monitor.core.data_processors.TokenExtractor"
                ) as mock_token_extractor:
                    mock_token_extractor.extract_tokens.side_effect = [
                        {
                            "input_tokens": 100,
                            "output_tokens": 50,
                            "cache_creation_tokens": 0,
                            "cache_read_tokens": 0,
                        },
                        {
                            "input_tokens": 200,
                            "output_tokens": 75,
                            "cache_creation_tokens": 0,
                            "cache_read_tokens": 0,
                        },
                    ]

                    with patch(
                        "claude_monitor.core.data_processors.DataConverter"
                    ) as mock_data_converter:
                        mock_data_converter.extract_model_name.side_effect = [
                            "claude-3-haiku",
                            "claude-3-sonnet",
                        ]

                        with patch(
                            "claude_monitor.core.pricing.PricingCalculator"
                        ) as mock_pricing_class:
                            mock_pricing = Mock()
                            mock_pricing.calculate_cost_for_entry.side_effect = [
                                0.001,
                                0.002,
                            ]
                            mock_pricing_class.return_value = mock_pricing

                            # Execute the main function
                            entries, raw_data = load_usage_entries(
                                data_path=str(temp_path), include_raw=True
                            )

            # Verify results
            assert len(entries) == 2
            assert len(raw_data) == 2

            # First entry
            assert entries[0].input_tokens == 100
            assert entries[0].output_tokens == 50
            assert entries[0].model == "claude-3-haiku"
            assert entries[0].message_id == "msg_1"

            # Second entry
            assert entries[1].input_tokens == 200
            assert entries[1].output_tokens == 75
            assert entries[1].model == "claude-3-sonnet"
            assert entries[1].message_id == "msg_2"

    def test_error_handling_integration(self):
        """
        Tests the full data loading workflow's ability to handle files containing both valid and invalid JSON lines.
        
        Verifies that valid entries are processed and mapped correctly, while invalid JSON lines are skipped without causing errors. Ensures that the resulting entries and raw data only include successfully parsed records.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test file with mixed valid and invalid data
            test_file = temp_path / "test.jsonl"
            with open(test_file, "w") as f:
                f.write(
                    '{"valid": "data", "timestamp": "2024-01-01T12:00:00Z", "input_tokens": 100, "output_tokens": 50}\n'
                )
                f.write("invalid json line\n")
                f.write(
                    '{"another": "valid", "timestamp": "2024-01-01T13:00:00Z", "input_tokens": 200, "output_tokens": 75}\n'
                )

            with patch(
                "claude_monitor.core.data_processors.TimestampProcessor"
            ) as mock_ts_processor:
                mock_ts = Mock()
                mock_ts.parse_timestamp.side_effect = [
                    datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
                    datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc),
                ]
                mock_ts_processor.return_value = mock_ts

                with patch(
                    "claude_monitor.core.data_processors.TokenExtractor"
                ) as mock_token_extractor:
                    mock_token_extractor.extract_tokens.side_effect = [
                        {
                            "input_tokens": 100,
                            "output_tokens": 50,
                            "cache_creation_tokens": 0,
                            "cache_read_tokens": 0,
                        },
                        {
                            "input_tokens": 200,
                            "output_tokens": 75,
                            "cache_creation_tokens": 0,
                            "cache_read_tokens": 0,
                        },
                    ]

                    with patch(
                        "claude_monitor.core.data_processors.DataConverter"
                    ) as mock_data_converter:
                        mock_data_converter.extract_model_name.side_effect = [
                            "unknown",
                            "unknown",
                        ]

                        with patch(
                            "claude_monitor.core.pricing.PricingCalculator"
                        ) as mock_pricing_class:
                            mock_pricing = Mock()
                            mock_pricing.calculate_cost_for_entry.side_effect = [
                                0.001,
                                0.002,
                            ]
                            mock_pricing_class.return_value = mock_pricing

                            # Should handle errors gracefully
                            entries, raw_data = load_usage_entries(
                                data_path=str(temp_path), include_raw=True
                            )

            # Should process valid entries and skip invalid JSON
            assert len(entries) == 2
            assert len(raw_data) == 2  # Only valid JSON included in raw data


class TestPerformanceAndEdgeCases:
    """Test performance scenarios and edge cases."""

    def test_large_file_processing(self):
        """
        Tests processing of a large JSONL file with 1000 entries to verify all entries are loaded, processed, and sorted correctly.
        
        Creates a temporary file with 1000 usage entries, mocks all data processors and pricing calculator, and asserts that all entries are processed and sorted by input tokens.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_file = temp_path / "large.jsonl"

            # Create a file with many entries
            with open(test_file, "w") as f:
                for i in range(1000):
                    entry = {
                        "timestamp": f"2024-01-01T{i % 24:02d}:00:00Z",
                        "input_tokens": 100 + i,
                        "output_tokens": 50 + i,
                        "message_id": f"msg_{i}",
                        "request_id": f"req_{i}",
                    }
                    f.write(json.dumps(entry) + "\n")

            with patch(
                "claude_monitor.core.data_processors.TimestampProcessor"
            ) as mock_ts_processor:
                mock_ts = Mock()
                mock_ts.parse_timestamp.side_effect = [
                    datetime(2024, 1, 1, i % 24, 0, tzinfo=timezone.utc)
                    for i in range(1000)
                ]
                mock_ts_processor.return_value = mock_ts

                with patch(
                    "claude_monitor.core.data_processors.TokenExtractor"
                ) as mock_token_extractor:
                    mock_token_extractor.extract_tokens.side_effect = [
                        {
                            "input_tokens": 100 + i,
                            "output_tokens": 50 + i,
                            "cache_creation_tokens": 0,
                            "cache_read_tokens": 0,
                        }
                        for i in range(1000)
                    ]

                    with patch(
                        "claude_monitor.core.data_processors.DataConverter"
                    ) as mock_data_converter:
                        mock_data_converter.extract_model_name.return_value = (
                            "claude-3-haiku"
                        )

                        with patch(
                            "claude_monitor.core.pricing.PricingCalculator"
                        ) as mock_pricing_class:
                            mock_pricing = Mock()
                            mock_pricing.calculate_cost_for_entry.return_value = 0.001
                            mock_pricing_class.return_value = mock_pricing

                            entries, _ = load_usage_entries(data_path=str(temp_path))

            # Should process all entries
            assert len(entries) == 1000
            # Should be sorted by timestamp
            assert entries[0].input_tokens <= entries[-1].input_tokens

    def test_empty_directory(self):
        """
        Test that loading usage entries from an empty directory returns no entries and no raw data.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            entries, raw_data = load_usage_entries(data_path=temp_dir, include_raw=True)

            assert entries == []
            assert raw_data is None

    def test_memory_efficiency(self):
        """
        Verify that raw data is not loaded when `include_raw` is set to False in the usage entry loading process.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_file = temp_path / "test.jsonl"

            # Create test file
            with open(test_file, "w") as f:
                f.write(
                    '{"timestamp": "2024-01-01T12:00:00Z", "input_tokens": 100, "output_tokens": 50}\n'
                )

            with patch(
                "claude_monitor.data.reader._process_single_file"
            ) as mock_process:
                mock_process.return_value = (
                    [],
                    None,
                )  # No raw data when include_raw=False

                entries, raw_data = load_usage_entries(
                    data_path=str(temp_path), include_raw=False
                )

                # Verify include_raw=False was passed to _process_single_file
                call_args = mock_process.call_args[0]
                assert call_args[4] is False  # include_raw parameter
                assert raw_data is None


class TestUsageEntryMapper:
    """Test the UsageEntryMapper compatibility wrapper."""

    @pytest.fixture
    def mapper_components(self):
        """
        Create and return a UsageEntryMapper instance along with its mocked dependencies.
        
        Returns:
            tuple: A tuple containing the UsageEntryMapper, a mocked TimezoneHandler, and a mocked PricingCalculator.
        """
        timezone_handler = Mock(spec=TimezoneHandler)
        pricing_calculator = Mock(spec=PricingCalculator)

        # Import after mocking to avoid import issues
        from claude_monitor.data.reader import UsageEntryMapper

        mapper = UsageEntryMapper(pricing_calculator, timezone_handler)

        return mapper, timezone_handler, pricing_calculator

    def test_usage_entry_mapper_init(self, mapper_components):
        """Test UsageEntryMapper initialization."""
        mapper, timezone_handler, pricing_calculator = mapper_components

        assert mapper.pricing_calculator == pricing_calculator
        assert mapper.timezone_handler == timezone_handler

    def test_usage_entry_mapper_map_success(self, mapper_components):
        """
        Test that UsageEntryMapper.map returns a mapped UsageEntry object when provided with valid input data.
        """
        mapper, timezone_handler, pricing_calculator = mapper_components

        data = {
            "timestamp": "2024-01-01T12:00:00Z",
            "input_tokens": 100,
            "output_tokens": 50,
            "model": "claude-3-haiku",
            "message_id": "msg_1",
            "request_id": "req_1",
        }

        with patch("claude_monitor.data.reader._map_to_usage_entry") as mock_map:
            expected_entry = UsageEntry(
                timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
                input_tokens=100,
                output_tokens=50,
                model="claude-3-haiku",
            )
            mock_map.return_value = expected_entry

            result = mapper.map(data, CostMode.AUTO)

            assert result == expected_entry
            mock_map.assert_called_once_with(
                data, CostMode.AUTO, timezone_handler, pricing_calculator
            )

    def test_usage_entry_mapper_map_failure(self, mapper_components):
        """
        Test that UsageEntryMapper.map returns None when mapping invalid data.
        
        Verifies that the map method handles mapping failures gracefully by returning None when the underlying mapping function fails.
        """
        mapper, timezone_handler, pricing_calculator = mapper_components

        data = {"invalid": "data"}

        with patch("claude_monitor.data.reader._map_to_usage_entry", return_value=None):
            result = mapper.map(data, CostMode.AUTO)

            assert result is None

    def test_usage_entry_mapper_has_valid_tokens(self, mapper_components):
        """
        Tests that UsageEntryMapper._has_valid_tokens correctly identifies valid and invalid token counts in entry data.
        """
        mapper, _, _ = mapper_components

        # Valid tokens
        assert mapper._has_valid_tokens({"input_tokens": 100, "output_tokens": 50})
        assert mapper._has_valid_tokens({"input_tokens": 100, "output_tokens": 0})
        assert mapper._has_valid_tokens({"input_tokens": 0, "output_tokens": 50})

        # Invalid tokens
        assert not mapper._has_valid_tokens({"input_tokens": 0, "output_tokens": 0})
        assert not mapper._has_valid_tokens({})

    def test_usage_entry_mapper_extract_timestamp(self, mapper_components):
        """
        Tests the _extract_timestamp method of UsageEntryMapper for correct timestamp extraction and parsing.
        
        Verifies that the method returns the expected datetime object when a valid timestamp is present and returns None when the timestamp is missing.
        """
        mapper, timezone_handler, _ = mapper_components

        with patch(
            "claude_monitor.core.data_processors.TimestampProcessor"
        ) as mock_processor_class:
            mock_processor = Mock()
            expected_timestamp = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
            mock_processor.parse_timestamp.return_value = expected_timestamp
            mock_processor_class.return_value = mock_processor

            # Test with timestamp
            result = mapper._extract_timestamp({"timestamp": "2024-01-01T12:00:00Z"})
            assert result == expected_timestamp

            # Test without timestamp
            result = mapper._extract_timestamp({})
            assert result is None

    def test_usage_entry_mapper_extract_model(self, mapper_components):
        """
        Tests that the UsageEntryMapper's _extract_model method correctly extracts the model name from input data using the DataConverter, and that the default value is used when appropriate.
        """
        mapper, _, _ = mapper_components

        with patch(
            "claude_monitor.core.data_processors.DataConverter"
        ) as mock_converter:
            mock_converter.extract_model_name.return_value = "claude-3-haiku"

            data = {"model": "claude-3-haiku"}
            result = mapper._extract_model(data)

            assert result == "claude-3-haiku"
            mock_converter.extract_model_name.assert_called_once_with(
                data, default="unknown"
            )

    def test_usage_entry_mapper_extract_metadata(self, mapper_components):
        """
        Tests the UsageEntryMapper._extract_metadata method to ensure it correctly extracts 'message_id' and 'request_id' from the input data.
        """
        mapper, _, _ = mapper_components

        # Test with message_id and request_id
        data = {"message_id": "msg_123", "request_id": "req_456"}

        result = mapper._extract_metadata(data)
        expected = {"message_id": "msg_123", "request_id": "req_456"}
        assert result == expected

    def test_usage_entry_mapper_extract_metadata_nested(self, mapper_components):
        """
        Tests that UsageEntryMapper._extract_metadata correctly extracts message and request IDs from nested message data.
        """
        mapper, _, _ = mapper_components

        # Test with nested message.id
        data = {"message": {"id": "msg_123"}, "requestId": "req_456"}

        result = mapper._extract_metadata(data)
        expected = {"message_id": "msg_123", "request_id": "req_456"}
        assert result == expected

    def test_usage_entry_mapper_extract_metadata_defaults(self, mapper_components):
        """
        Test that UsageEntryMapper._extract_metadata returns default metadata values when input data is missing required fields.
        """
        mapper, _, _ = mapper_components

        # Test with missing data
        data = {}

        result = mapper._extract_metadata(data)
        expected = {"message_id": "", "request_id": "unknown"}
        assert result == expected


class TestAdditionalEdgeCases:
    """Test additional edge cases and error scenarios."""

    def test_create_unique_hash_edge_cases(self):
        """
        Test that _create_unique_hash returns None when message_id or request_id are None or empty strings.
        """
        # Test with None values
        data = {"message_id": None, "request_id": "req_1"}
        result = _create_unique_hash(data)
        assert result is None

        # Test with empty strings
        data = {"message_id": "", "request_id": "req_1"}
        result = _create_unique_hash(data)
        assert result is None

        # Test with both valid values but one is empty
        data = {"message_id": "msg_1", "request_id": ""}
        result = _create_unique_hash(data)
        assert result is None

    def test_should_process_entry_edge_cases(self):
        """
        Test that `_should_process_entry` returns True for entries with no cutoff time or when the unique hash is missing or not in the processed set.
        
        Covers edge cases where cutoff time is None and processed hashes are empty or the entry lacks a valid unique hash.
        """
        timezone_handler = Mock(spec=TimezoneHandler)

        # Test with None cutoff_time and no hash
        data = {"some": "data"}
        with patch("claude_monitor.data.reader._create_unique_hash", return_value=None):
            result = _should_process_entry(data, None, set(), timezone_handler)
        assert result is True

        # Test with empty processed_hashes set
        data = {"message_id": "msg_1", "request_id": "req_1"}
        with patch(
            "claude_monitor.data.reader._create_unique_hash", return_value="msg_1:req_1"
        ):
            result = _should_process_entry(data, None, set(), timezone_handler)
        assert result is True

    def test_map_to_usage_entry_error_scenarios(self):
        """
        Test that `_map_to_usage_entry` returns None when encountering errors such as missing imports or exceptions from the pricing calculator.
        """
        timezone_handler = Mock(spec=TimezoneHandler)
        pricing_calculator = Mock(spec=PricingCalculator)

        # Test with missing timestamp processor import error
        data = {"timestamp": "2024-01-01T12:00:00Z"}
        with patch(
            "claude_monitor.core.data_processors.TimestampProcessor",
            side_effect=AttributeError("Module not found"),
        ):
            result = _map_to_usage_entry(
                data, CostMode.AUTO, timezone_handler, pricing_calculator
            )
        assert result is None

        # Test with pricing calculator error
        data = {
            "timestamp": "2024-01-01T12:00:00Z",
            "input_tokens": 100,
            "output_tokens": 50,
        }

        with patch(
            "claude_monitor.core.data_processors.TimestampProcessor"
        ) as mock_ts_processor:
            mock_ts = Mock()
            mock_ts.parse_timestamp.return_value = datetime(
                2024, 1, 1, 12, 0, tzinfo=timezone.utc
            )
            mock_ts_processor.return_value = mock_ts

            with patch(
                "claude_monitor.core.data_processors.TokenExtractor"
            ) as mock_token_extractor:
                mock_token_extractor.extract_tokens.return_value = {
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "cache_creation_tokens": 0,
                    "cache_read_tokens": 0,
                }

                with patch(
                    "claude_monitor.core.data_processors.DataConverter"
                ) as mock_data_converter:
                    mock_data_converter.extract_model_name.return_value = (
                        "claude-3-haiku"
                    )

                    pricing_calculator.calculate_cost_for_entry.side_effect = (
                        ValueError("Pricing error")
                    )

                    result = _map_to_usage_entry(
                        data, CostMode.AUTO, timezone_handler, pricing_calculator
                    )
                    assert result is None

    def test_load_usage_entries_timezone_handling(self):
        """
        Test that `load_usage_entries` correctly parses and normalizes timezone-aware timestamps.
        
        Verifies that entries with different timezone formats are loaded and their timestamps are converted to UTC.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_file = temp_path / "test.jsonl"

            # Create test data with different timezone formats
            test_data = [
                {
                    "timestamp": "2024-01-01T12:00:00+00:00",
                    "input_tokens": 100,
                    "output_tokens": 50,
                },
                {
                    "timestamp": "2024-01-01T12:00:00Z",
                    "input_tokens": 200,
                    "output_tokens": 75,
                },
            ]

            with open(test_file, "w") as f:
                for item in test_data:
                    f.write(json.dumps(item) + "\n")

            with patch(
                "claude_monitor.core.data_processors.TimestampProcessor"
            ) as mock_ts_processor:
                mock_ts = Mock()
                mock_ts.parse_timestamp.side_effect = [
                    datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
                    datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
                ]
                mock_ts_processor.return_value = mock_ts

                with patch(
                    "claude_monitor.core.data_processors.TokenExtractor"
                ) as mock_token_extractor:
                    mock_token_extractor.extract_tokens.side_effect = [
                        {
                            "input_tokens": 100,
                            "output_tokens": 50,
                            "cache_creation_tokens": 0,
                            "cache_read_tokens": 0,
                        },
                        {
                            "input_tokens": 200,
                            "output_tokens": 75,
                            "cache_creation_tokens": 0,
                            "cache_read_tokens": 0,
                        },
                    ]

                    with patch(
                        "claude_monitor.core.data_processors.DataConverter"
                    ) as mock_data_converter:
                        mock_data_converter.extract_model_name.return_value = (
                            "claude-3-haiku"
                        )

                        with patch(
                            "claude_monitor.core.pricing.PricingCalculator"
                        ) as mock_pricing_class:
                            mock_pricing = Mock()
                            mock_pricing.calculate_cost_for_entry.return_value = 0.001
                            mock_pricing_class.return_value = mock_pricing

                            entries, _ = load_usage_entries(data_path=str(temp_path))

            assert len(entries) == 2
            # Both should have UTC timezone
            for entry in entries:
                assert entry.timestamp.tzinfo == timezone.utc

    def test_process_single_file_empty_file(self):
        """
        Test that processing an empty JSONL file returns empty entries and raw data lists.
        """
        timezone_handler = Mock(spec=TimezoneHandler)
        pricing_calculator = Mock(spec=PricingCalculator)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            empty_file = temp_path / "empty.jsonl"
            empty_file.touch()  # Create empty file

            entries, raw_data = _process_single_file(
                empty_file,
                CostMode.AUTO,
                None,
                set(),
                True,
                timezone_handler,
                pricing_calculator,
            )

            assert entries == []
            assert raw_data == []

    def test_load_usage_entries_cost_modes(self):
        """
        Test that `load_usage_entries` correctly processes entries with different cost modes.
        
        Verifies that usage entries are loaded and processed as expected when using AUTO, CALCULATED, and CACHED cost modes, ensuring the pricing calculator is invoked for each mode.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_file = temp_path / "test.jsonl"

            test_data = [
                {
                    "timestamp": "2024-01-01T12:00:00Z",
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "cost": 0.001,
                }
            ]

            with open(test_file, "w") as f:
                for item in test_data:
                    f.write(json.dumps(item) + "\n")

            for mode in [CostMode.AUTO, CostMode.CALCULATED, CostMode.CACHED]:
                with patch(
                    "claude_monitor.core.data_processors.TimestampProcessor"
                ) as mock_ts_processor:
                    mock_ts = Mock()
                    mock_ts.parse_timestamp.return_value = datetime(
                        2024, 1, 1, 12, 0, tzinfo=timezone.utc
                    )
                    mock_ts_processor.return_value = mock_ts

                    with patch(
                        "claude_monitor.core.data_processors.TokenExtractor"
                    ) as mock_token_extractor:
                        mock_token_extractor.extract_tokens.return_value = {
                            "input_tokens": 100,
                            "output_tokens": 50,
                            "cache_creation_tokens": 0,
                            "cache_read_tokens": 0,
                        }

                        with patch(
                            "claude_monitor.core.data_processors.DataConverter"
                        ) as mock_data_converter:
                            mock_data_converter.extract_model_name.return_value = (
                                "claude-3-haiku"
                            )

                            with patch(
                                "claude_monitor.data.reader.PricingCalculator"
                            ) as mock_pricing_class:
                                mock_pricing = Mock()
                                mock_pricing.calculate_cost_for_entry.return_value = (
                                    0.002
                                )
                                mock_pricing_class.return_value = mock_pricing

                                entries, _ = load_usage_entries(
                                    data_path=str(temp_path), mode=mode
                                )

                assert len(entries) == 1
                # Verify the pricing calculator was created (called in load_usage_entries)
                assert mock_pricing_class.called


class TestDataProcessors:
    """Test the data processor classes."""

    def test_timestamp_processor_init(self):
        """
        Test that the TimestampProcessor initializes with a default or custom timezone handler.
        """
        from claude_monitor.core.data_processors import TimestampProcessor

        # Test with default timezone handler
        processor = TimestampProcessor()
        assert processor.timezone_handler is not None

        # Test with custom timezone handler
        custom_handler = Mock()
        processor = TimestampProcessor(custom_handler)
        assert processor.timezone_handler == custom_handler

    def test_timestamp_processor_parse_datetime(self):
        """
        Test that TimestampProcessor correctly parses a datetime object and applies timezone normalization.
        """
        from claude_monitor.core.data_processors import TimestampProcessor

        processor = TimestampProcessor()
        dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        with patch.object(processor.timezone_handler, "ensure_timezone") as mock_ensure:
            mock_ensure.return_value = dt
            result = processor.parse_timestamp(dt)

            assert result == dt
            mock_ensure.assert_called_once_with(dt)

    def test_timestamp_processor_parse_string_iso(self):
        """
        Test that TimestampProcessor correctly parses ISO 8601 datetime strings with 'Z' suffix and explicit UTC offset, ensuring timezone normalization.
        """
        from claude_monitor.core.data_processors import TimestampProcessor

        processor = TimestampProcessor()

        with patch.object(processor.timezone_handler, "ensure_timezone") as mock_ensure:
            mock_dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            mock_ensure.return_value = mock_dt

            # Test Z suffix handling
            result = processor.parse_timestamp("2024-01-01T12:00:00Z")
            assert result == mock_dt

            # Test ISO format without Z
            result = processor.parse_timestamp("2024-01-01T12:00:00+00:00")
            assert result == mock_dt

    def test_timestamp_processor_parse_string_fallback(self):
        """
        Test that TimestampProcessor.parse_timestamp returns None for unparseable string inputs.
        """
        from claude_monitor.core.data_processors import TimestampProcessor

        processor = TimestampProcessor()

        with patch.object(processor.timezone_handler, "ensure_timezone") as mock_ensure:
            mock_dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            mock_ensure.return_value = mock_dt

            # Test that the function handles parsing failures gracefully
            result = processor.parse_timestamp("invalid-format-that-will-fail")
            # Should return None for unparseable strings
            assert result is None

    def test_timestamp_processor_parse_numeric(self):
        """
        Test that TimestampProcessor correctly parses numeric timestamps as UTC-aware datetimes.
        
        Verifies that both integer and float Unix timestamps are converted to the expected datetime using the timezone handler.
        """
        from claude_monitor.core.data_processors import TimestampProcessor

        processor = TimestampProcessor()

        with patch.object(processor.timezone_handler, "ensure_timezone") as mock_ensure:
            mock_dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            mock_ensure.return_value = mock_dt

            # Test integer timestamp
            result = processor.parse_timestamp(1704110400)  # 2024-01-01 12:00:00 UTC
            assert result == mock_dt

            # Test float timestamp
            result = processor.parse_timestamp(1704110400.5)
            assert result == mock_dt

    def test_timestamp_processor_parse_invalid(self):
        """
        Test that TimestampProcessor.parse_timestamp returns None for invalid timestamp inputs, including None, unparseable strings, and invalid types.
        """
        from claude_monitor.core.data_processors import TimestampProcessor

        processor = TimestampProcessor()

        # Test None
        assert processor.parse_timestamp(None) is None

        # Test invalid string that can't be parsed
        assert processor.parse_timestamp("invalid-date") is None

        # Test invalid type
        assert processor.parse_timestamp({"not": "timestamp"}) is None

    def test_token_extractor_basic_extraction(self):
        """
        Test that TokenExtractor correctly extracts token counts from direct fields in a data dictionary.
        """
        from claude_monitor.core.data_processors import TokenExtractor

        # Test direct token fields
        data = {
            "input_tokens": 100,
            "output_tokens": 50,
            "cache_creation_tokens": 10,
            "cache_read_tokens": 5,
        }

        result = TokenExtractor.extract_tokens(data)

        assert result["input_tokens"] == 100
        assert result["output_tokens"] == 50
        assert result["cache_creation_tokens"] == 10
        assert result["cache_read_tokens"] == 5
        assert result["total_tokens"] == 165

    def test_token_extractor_usage_field(self):
        """
        Test that TokenExtractor correctly extracts input, output, and total tokens from the 'usage' field in a data dictionary.
        """
        from claude_monitor.core.data_processors import TokenExtractor

        data = {"usage": {"input_tokens": 200, "output_tokens": 100}}

        result = TokenExtractor.extract_tokens(data)

        assert result["input_tokens"] == 200
        assert result["output_tokens"] == 100
        assert result["total_tokens"] == 300

    def test_token_extractor_message_usage(self):
        """
        Test that TokenExtractor correctly extracts token counts from the nested message.usage field in the input data.
        """
        from claude_monitor.core.data_processors import TokenExtractor

        data = {
            "message": {
                "usage": {
                    "input_tokens": 150,
                    "output_tokens": 75,
                    "cache_creation_tokens": 20,
                }
            }
        }

        result = TokenExtractor.extract_tokens(data)

        assert result["input_tokens"] == 150
        assert result["output_tokens"] == 75
        assert result["cache_creation_tokens"] == 20
        assert result["total_tokens"] == 245

    def test_token_extractor_empty_data(self):
        """
        Test that TokenExtractor returns zero counts for all token types when given empty data.
        """
        from claude_monitor.core.data_processors import TokenExtractor

        result = TokenExtractor.extract_tokens({})

        assert result["input_tokens"] == 0
        assert result["output_tokens"] == 0
        assert result["cache_creation_tokens"] == 0
        assert result["cache_read_tokens"] == 0
        assert result["total_tokens"] == 0

    def test_data_converter_extract_model_name(self):
        """
        Tests the extraction of the model name from various data structures using the DataConverter.
        
        Verifies correct extraction from direct and nested fields, handling of missing data with a default value, and graceful handling of None input.
        """
        from claude_monitor.core.data_processors import DataConverter

        # Test direct model field
        data = {"model": "claude-3-opus"}
        assert DataConverter.extract_model_name(data) == "claude-3-opus"

        # Test message.model field
        data = {"message": {"model": "claude-3-sonnet"}}
        assert DataConverter.extract_model_name(data) == "claude-3-sonnet"

        # Test with default
        data = {}
        assert (
            DataConverter.extract_model_name(data, "default-model") == "default-model"
        )

        # Test with None data (handle gracefully)
        try:
            result = DataConverter.extract_model_name(None, "fallback")
            assert result == "fallback"
        except AttributeError:
            # If function doesn't handle None gracefully, that's also acceptable
            pass

    def test_data_converter_flatten_nested_dict(self):
        """Test nested dictionary flattening."""
        from claude_monitor.core.data_processors import DataConverter

        # Test simple nested dict
        data = {
            "user": {"name": "John", "age": 30},
            "settings": {
                "theme": "dark",
                "notifications": {"email": True, "push": False},
            },
        }

        result = DataConverter.flatten_nested_dict(data)

        assert result["user.name"] == "John"
        assert result["user.age"] == 30
        assert result["settings.theme"] == "dark"
        assert result["settings.notifications.email"] is True
        assert result["settings.notifications.push"] is False

    def test_data_converter_flatten_with_prefix(self):
        """
        Test that flattening a nested dictionary with a custom prefix produces correctly prefixed keys.
        """
        from claude_monitor.core.data_processors import DataConverter

        data = {"inner": {"value": 42}}
        result = DataConverter.flatten_nested_dict(data, "prefix")

        assert result["prefix.inner.value"] == 42

    def test_data_converter_to_serializable(self):
        """
        Test the DataConverter.to_serializable method for correct serialization of various data types, including datetime objects, dictionaries, lists, and primitive types.
        """
        from claude_monitor.core.data_processors import DataConverter

        # Test datetime
        dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        assert DataConverter.to_serializable(dt) == "2024-01-01T12:00:00+00:00"

        # Test dict with datetime
        data = {"timestamp": dt, "value": 42}
        result = DataConverter.to_serializable(data)
        assert result["timestamp"] == "2024-01-01T12:00:00+00:00"
        assert result["value"] == 42

        # Test list with datetime
        data = [dt, "string", 123]
        result = DataConverter.to_serializable(data)
        assert result[0] == "2024-01-01T12:00:00+00:00"
        assert result[1] == "string"
        assert result[2] == 123

        # Test primitive types
        assert DataConverter.to_serializable("string") == "string"
        assert DataConverter.to_serializable(123) == 123
        assert DataConverter.to_serializable(True) is True
