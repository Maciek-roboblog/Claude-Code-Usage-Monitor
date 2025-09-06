"""Tests for HistoryManager module."""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from claude_monitor.data.history_manager import HistoryManager


class TestHistoryManager:
    """Test suite for HistoryManager."""

    @pytest.fixture
    def temp_dir(self) -> Path:
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def history_manager(self, temp_dir: Path) -> HistoryManager:
        """Create a HistoryManager instance with temporary directory."""
        return HistoryManager(data_dir=temp_dir)

    def test_initialization(
        self, history_manager: HistoryManager, temp_dir: Path
    ) -> None:
        """Test HistoryManager initialization."""
        assert history_manager.data_dir == temp_dir
        assert history_manager.daily_dir == temp_dir / "daily"
        assert history_manager.daily_dir.exists()
        assert history_manager._saved_dates == set()

    def test_get_daily_file_path(self, history_manager: HistoryManager) -> None:
        """Test file path generation for daily data."""
        date_str = "2024-12-15"
        expected_path = history_manager.daily_dir / "2024" / "12" / "2024-12-15.json"
        actual_path = history_manager._get_daily_file_path(date_str)
        assert actual_path == expected_path
        assert actual_path.parent.exists()

    def test_get_daily_file_path_invalid_date(
        self, history_manager: HistoryManager
    ) -> None:
        """Test file path generation with invalid date format."""
        date_str = "invalid-date"
        with pytest.raises(ValueError, match="Invalid date format"):
            history_manager._get_daily_file_path(date_str)

        # Test path traversal attempt
        malicious_str = "../../../etc/passwd"
        with pytest.raises(ValueError, match="Invalid date format"):
            history_manager._get_daily_file_path(malicious_str)

    def test_save_daily_data(self, history_manager: HistoryManager) -> None:
        """Test saving daily data."""
        daily_data = [
            {
                "date": "2024-12-15",
                "input_tokens": 1000,
                "output_tokens": 500,
                "total_cost": 0.015,
                "entries_count": 5,
                "models_used": ["claude-3-opus"],
            }
        ]

        saved_count = history_manager.save_daily_data(daily_data)
        assert saved_count == 1

        # Check file was created
        file_path = history_manager._get_daily_file_path("2024-12-15")
        assert file_path.exists()

        # Verify content
        with open(file_path, "r") as f:
            saved_data = json.load(f)
        assert saved_data == daily_data[0]

    def test_save_daily_data_no_overwrite(
        self, history_manager: HistoryManager
    ) -> None:
        """Test that save_daily_data doesn't overwrite by default."""
        daily_data = [
            {
                "date": "2024-12-15",
                "input_tokens": 1000,
                "output_tokens": 500,
                "total_cost": 0.015,
            }
        ]

        # Save first time
        saved_count = history_manager.save_daily_data(daily_data)
        assert saved_count == 1

        # Modify data and try to save again
        daily_data[0]["input_tokens"] = 2000
        saved_count = history_manager.save_daily_data(daily_data, overwrite=False)
        assert saved_count == 0  # Should not save again

        # Verify original data is preserved
        file_path = history_manager._get_daily_file_path("2024-12-15")
        with open(file_path, "r") as f:
            saved_data = json.load(f)
        assert saved_data["input_tokens"] == 1000

    def test_save_daily_data_with_overwrite(
        self, history_manager: HistoryManager
    ) -> None:
        """Test save_daily_data with overwrite enabled."""
        daily_data = [
            {
                "date": "2024-12-15",
                "input_tokens": 1000,
                "output_tokens": 500,
            }
        ]

        # Save first time
        history_manager.save_daily_data(daily_data)

        # Modify and save with overwrite
        daily_data[0]["input_tokens"] = 2000
        saved_count = history_manager.save_daily_data(daily_data, overwrite=True)
        assert saved_count == 1

        # Verify data was updated
        file_path = history_manager._get_daily_file_path("2024-12-15")
        with open(file_path, "r") as f:
            saved_data = json.load(f)
        assert saved_data["input_tokens"] == 2000

    def test_load_historical_daily_data(self, history_manager: HistoryManager) -> None:
        """Test loading historical daily data."""
        # Save some test data
        test_data = [
            {"date": "2024-12-10", "input_tokens": 100},
            {"date": "2024-12-15", "input_tokens": 200},
            {"date": "2024-12-20", "input_tokens": 300},
        ]

        for data in test_data:
            history_manager.save_daily_data([data])

        # Load all data
        loaded_data = history_manager.load_historical_daily_data()
        assert len(loaded_data) == 3
        assert loaded_data[0]["date"] == "2024-12-10"
        assert loaded_data[2]["date"] == "2024-12-20"

    def test_load_historical_daily_data_with_date_range(
        self, history_manager: HistoryManager
    ) -> None:
        """Test loading historical data with date filters."""
        # Save test data
        test_data = [
            {"date": "2024-12-10", "input_tokens": 100},
            {"date": "2024-12-15", "input_tokens": 200},
            {"date": "2024-12-20", "input_tokens": 300},
        ]

        for data in test_data:
            history_manager.save_daily_data([data])

        # Load data with date range
        start_date = datetime(2024, 12, 12)
        end_date = datetime(2024, 12, 18)
        loaded_data = history_manager.load_historical_daily_data(
            start_date=start_date, end_date=end_date
        )

        assert len(loaded_data) == 1
        assert loaded_data[0]["date"] == "2024-12-15"

    def test_load_historical_daily_data_days_back(
        self, history_manager: HistoryManager
    ) -> None:
        """Test loading historical data with days_back parameter."""
        # Save test data with current date
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        week_ago = today - timedelta(days=7)

        test_data = [
            {"date": week_ago.strftime("%Y-%m-%d"), "input_tokens": 100},
            {"date": yesterday.strftime("%Y-%m-%d"), "input_tokens": 200},
            {"date": today.strftime("%Y-%m-%d"), "input_tokens": 300},
        ]

        for data in test_data:
            history_manager.save_daily_data([data])

        # Load last 3 days
        loaded_data = history_manager.load_historical_daily_data(days_back=3)
        assert len(loaded_data) == 2  # Should get yesterday and today

    def test_merge_with_current_data(self, history_manager: HistoryManager) -> None:
        """Test merging current and historical data."""
        historical_data = [
            {"date": "2024-12-10", "input_tokens": 100, "source": "historical"},
            {"date": "2024-12-15", "input_tokens": 200, "source": "historical"},
        ]

        current_data = [
            {"date": "2024-12-15", "input_tokens": 250, "source": "current"},
            {"date": "2024-12-20", "input_tokens": 300, "source": "current"},
        ]

        merged = history_manager.merge_with_current_data(current_data, historical_data)

        assert len(merged) == 3
        assert merged[0]["date"] == "2024-12-10"
        assert merged[0]["source"] == "historical"
        assert merged[1]["date"] == "2024-12-15"
        assert merged[1]["source"] == "current"  # Current data takes precedence
        assert merged[2]["date"] == "2024-12-20"
        assert merged[2]["source"] == "current"

    def test_aggregate_monthly_from_daily(
        self, history_manager: HistoryManager
    ) -> None:
        """Test aggregating daily data into monthly summaries."""
        daily_data = [
            {
                "date": "2024-11-15",
                "input_tokens": 100,
                "output_tokens": 50,
                "total_cost": 0.01,
                "entries_count": 2,
                "models_used": ["claude-3-opus"],
                "model_breakdowns": {
                    "claude-3-opus": {
                        "input_tokens": 100,
                        "output_tokens": 50,
                        "cost": 0.01,
                        "count": 2,
                    }
                },
            },
            {
                "date": "2024-11-20",
                "input_tokens": 200,
                "output_tokens": 100,
                "total_cost": 0.02,
                "entries_count": 3,
                "models_used": ["claude-3-sonnet"],
                "model_breakdowns": {
                    "claude-3-sonnet": {
                        "input_tokens": 200,
                        "output_tokens": 100,
                        "cost": 0.02,
                        "count": 3,
                    }
                },
            },
            {
                "date": "2024-12-01",
                "input_tokens": 300,
                "output_tokens": 150,
                "total_cost": 0.03,
                "entries_count": 4,
                "models_used": ["claude-3-opus"],
                "model_breakdowns": {
                    "claude-3-opus": {
                        "input_tokens": 300,
                        "output_tokens": 150,
                        "cost": 0.03,
                        "count": 4,
                    }
                },
            },
        ]

        monthly_data = history_manager.aggregate_monthly_from_daily(daily_data)

        assert len(monthly_data) == 2

        # Check November aggregation
        nov_data = monthly_data[0]
        assert nov_data["month"] == "2024-11"
        assert nov_data["input_tokens"] == 300
        assert nov_data["output_tokens"] == 150
        assert nov_data["total_cost"] == 0.03
        assert nov_data["entries_count"] == 5
        assert set(nov_data["models_used"]) == {"claude-3-opus", "claude-3-sonnet"}

        # Check December aggregation
        dec_data = monthly_data[1]
        assert dec_data["month"] == "2024-12"
        assert dec_data["input_tokens"] == 300
        assert dec_data["output_tokens"] == 150
        assert dec_data["total_cost"] == 0.03
        assert dec_data["entries_count"] == 4

    def test_cleanup_old_data(self, history_manager: HistoryManager) -> None:
        """Test cleanup of old historical data."""
        # Create old and recent data
        old_date = (datetime.now() - timedelta(days=400)).strftime("%Y-%m-%d")
        recent_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")

        old_data = [{"date": old_date, "input_tokens": 100}]
        recent_data = [{"date": recent_date, "input_tokens": 200}]

        history_manager.save_daily_data(old_data)
        history_manager.save_daily_data(recent_data)

        # Cleanup data older than 365 days
        deleted_count = history_manager.cleanup_old_data(days_to_keep=365)

        assert deleted_count == 1

        # Verify old data is gone, recent data remains
        old_file = history_manager._get_daily_file_path(old_date)
        recent_file = history_manager._get_daily_file_path(recent_date)

        assert not old_file.exists()
        assert recent_file.exists()

    def test_get_statistics(self, history_manager: HistoryManager) -> None:
        """Test getting statistics about historical data."""
        # Save some test data
        test_data = [
            {"date": "2024-11-15", "input_tokens": 100},
            {"date": "2024-12-15", "input_tokens": 200},
            {"date": "2024-12-20", "input_tokens": 300},
        ]

        for data in test_data:
            history_manager.save_daily_data([data])

        stats = history_manager.get_statistics()

        assert stats["total_files"] == 3
        assert stats["oldest_date"] == "2024-11-15"
        assert stats["newest_date"] == "2024-12-20"
        assert "total_size_mb" in stats
        assert stats["data_directory"] == str(history_manager.daily_dir)

    def test_save_daily_data_missing_date(
        self, history_manager: HistoryManager
    ) -> None:
        """Test handling of data without date field."""
        daily_data = [
            {"input_tokens": 1000, "output_tokens": 500}  # Missing 'date' field
        ]

        saved_count = history_manager.save_daily_data(daily_data)
        assert saved_count == 0

    def test_save_daily_data_with_existing_better_data(
        self, history_manager: HistoryManager
    ) -> None:
        """Test that existing data with more total tokens is preserved."""
        # Save initial data with more total tokens
        initial_data = [
            {
                "date": "2024-12-15",
                "input_tokens": 2000,
                "output_tokens": 1000,
                "cache_creation_tokens": 100,
                "cache_read_tokens": 50,
                "total_cost": 0.10,
                "entries_count": 20,
            }
        ]
        history_manager.save_daily_data(initial_data)

        # Clear saved dates to allow checking existing file
        history_manager._saved_dates.clear()

        # Try to save data with fewer total tokens
        new_data = [
            {
                "date": "2024-12-15",
                "input_tokens": 500,
                "output_tokens": 250,
                "cache_creation_tokens": 50,
                "cache_read_tokens": 25,
                "total_cost": 0.05,
                "entries_count": 10,
            }
        ]
        saved_count = history_manager.save_daily_data(new_data, overwrite=False)
        assert saved_count == 0

        # Verify original data is preserved
        file_path = history_manager._get_daily_file_path("2024-12-15")
        with open(file_path, "r", encoding="utf-8") as f:
            saved_data = json.load(f)
        assert saved_data["input_tokens"] == 2000
        assert saved_data["total_cost"] == 0.10

    def test_save_daily_data_updates_with_more_info(
        self, history_manager: HistoryManager
    ) -> None:
        """Test that new data with more information replaces old data."""
        # Save initial data
        initial_data = [
            {
                "date": "2024-12-16",
                "input_tokens": 1000,
                "output_tokens": 500,
                "cache_creation_tokens": 100,
                "cache_read_tokens": 50,
                "total_cost": 0.05,
                "entries_count": 10,
            }
        ]
        history_manager.save_daily_data(initial_data)

        # Clear saved dates
        history_manager._saved_dates.clear()

        # Save new data with more total tokens
        new_data = [
            {
                "date": "2024-12-16",
                "input_tokens": 900,
                "output_tokens": 600,
                "cache_creation_tokens": 200,
                "cache_read_tokens": 100,
                "total_cost": 0.08,
                "entries_count": 15,
            }
        ]
        saved_count = history_manager.save_daily_data(new_data, overwrite=False)
        assert saved_count == 1

        # Verify new data was saved
        file_path = history_manager._get_daily_file_path("2024-12-16")
        with open(file_path, "r", encoding="utf-8") as f:
            saved_data = json.load(f)
        assert saved_data["input_tokens"] == 900
        assert saved_data["cache_creation_tokens"] == 200
        assert saved_data["total_cost"] == 0.08
