"""Tests for data aggregator module."""

from datetime import datetime, timezone, timedelta
from typing import List
from unittest.mock import Mock, patch

import pytest

from claude_monitor.core.models import UsageEntry
from claude_monitor.data.aggregator import (
    AggregatedStats,
    AggregatedPeriod,
    UsageAggregator,
)


class TestAggregatedStats:
    """Test cases for AggregatedStats dataclass."""

    def test_init_default_values(self) -> None:
        """Test default initialization of AggregatedStats."""
        stats = AggregatedStats()
        assert stats.input_tokens == 0
        assert stats.output_tokens == 0
        assert stats.cache_creation_tokens == 0
        assert stats.cache_read_tokens == 0
        assert stats.cost == 0.0
        assert stats.count == 0

    def test_add_entry_single(self, sample_usage_entry: UsageEntry) -> None:
        """Test adding a single entry to stats."""
        stats = AggregatedStats()
        stats.add_entry(sample_usage_entry)
        
        assert stats.input_tokens == 100
        assert stats.output_tokens == 50
        assert stats.cache_creation_tokens == 10
        assert stats.cache_read_tokens == 5
        assert stats.cost == 0.001
        assert stats.count == 1

    def test_add_entry_multiple(self) -> None:
        """Test adding multiple entries to stats."""
        stats = AggregatedStats()
        
        # Create multiple entries
        entry1 = UsageEntry(
            timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            input_tokens=100,
            output_tokens=50,
            cache_creation_tokens=10,
            cache_read_tokens=5,
            cost_usd=0.001,
            model="claude-3-haiku",
            message_id="msg_1",
            request_id="req_1",
        )
        
        entry2 = UsageEntry(
            timestamp=datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc),
            input_tokens=200,
            output_tokens=100,
            cache_creation_tokens=20,
            cache_read_tokens=10,
            cost_usd=0.002,
            model="claude-3-sonnet",
            message_id="msg_2",
            request_id="req_2",
        )
        
        stats.add_entry(entry1)
        stats.add_entry(entry2)
        
        assert stats.input_tokens == 300
        assert stats.output_tokens == 150
        assert stats.cache_creation_tokens == 30
        assert stats.cache_read_tokens == 15
        assert stats.cost == 0.003
        assert stats.count == 2

    def test_to_dict(self) -> None:
        """Test converting AggregatedStats to dictionary."""
        stats = AggregatedStats(
            input_tokens=1000,
            output_tokens=500,
            cache_creation_tokens=100,
            cache_read_tokens=50,
            cost=0.05,
            count=10
        )
        
        result = stats.to_dict()
        
        assert result == {
            "input_tokens": 1000,
            "output_tokens": 500,
            "cache_creation_tokens": 100,
            "cache_read_tokens": 50,
            "cost": 0.05,
            "count": 10,
        }


class TestAggregatedPeriod:
    """Test cases for AggregatedPeriod dataclass."""

    def test_init_default_values(self) -> None:
        """Test default initialization of AggregatedPeriod."""
        period = AggregatedPeriod(period_key="2024-01-01")
        
        assert period.period_key == "2024-01-01"
        assert isinstance(period.stats, AggregatedStats)
        assert period.stats.count == 0
        assert len(period.models_used) == 0
        assert len(period.model_breakdowns) == 0

    def test_add_entry_single(self, sample_usage_entry: UsageEntry) -> None:
        """Test adding a single entry to period."""
        period = AggregatedPeriod(period_key="2024-01-01")
        period.add_entry(sample_usage_entry)
        
        # Check overall stats
        assert period.stats.input_tokens == 100
        assert period.stats.output_tokens == 50
        assert period.stats.cost == 0.001
        assert period.stats.count == 1
        
        # Check models tracking
        assert "claude-3-haiku" in period.models_used
        assert len(period.models_used) == 1
        
        # Check model breakdown
        assert "claude-3-haiku" in period.model_breakdowns
        assert period.model_breakdowns["claude-3-haiku"].input_tokens == 100

    def test_add_entry_multiple_models(self) -> None:
        """Test adding entries with different models."""
        period = AggregatedPeriod(period_key="2024-01-01")
        
        # Add entries with different models
        entry1 = UsageEntry(
            timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            input_tokens=100,
            output_tokens=50,
            cache_creation_tokens=0,
            cache_read_tokens=0,
            cost_usd=0.001,
            model="claude-3-haiku",
            message_id="msg_1",
            request_id="req_1",
        )
        
        entry2 = UsageEntry(
            timestamp=datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc),
            input_tokens=200,
            output_tokens=100,
            cache_creation_tokens=0,
            cache_read_tokens=0,
            cost_usd=0.002,
            model="claude-3-sonnet",
            message_id="msg_2",
            request_id="req_2",
        )
        
        entry3 = UsageEntry(
            timestamp=datetime(2024, 1, 1, 14, 0, tzinfo=timezone.utc),
            input_tokens=150,
            output_tokens=75,
            cache_creation_tokens=0,
            cache_read_tokens=0,
            cost_usd=0.0015,
            model="claude-3-haiku",
            message_id="msg_3",
            request_id="req_3",
        )
        
        period.add_entry(entry1)
        period.add_entry(entry2)
        period.add_entry(entry3)
        
        # Check overall stats
        assert period.stats.input_tokens == 450
        assert period.stats.output_tokens == 225
        assert abs(period.stats.cost - 0.0045) < 0.0000001  # Handle floating point precision
        assert period.stats.count == 3
        
        # Check models
        assert len(period.models_used) == 2
        assert "claude-3-haiku" in period.models_used
        assert "claude-3-sonnet" in period.models_used
        
        # Check model breakdowns
        assert period.model_breakdowns["claude-3-haiku"].input_tokens == 250
        assert period.model_breakdowns["claude-3-haiku"].count == 2
        assert period.model_breakdowns["claude-3-sonnet"].input_tokens == 200
        assert period.model_breakdowns["claude-3-sonnet"].count == 1

    def test_add_entry_with_unknown_model(self) -> None:
        """Test adding entry with None or empty model."""
        period = AggregatedPeriod(period_key="2024-01-01")
        
        entry = UsageEntry(
            timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            input_tokens=100,
            output_tokens=50,
            cache_creation_tokens=0,
            cache_read_tokens=0,
            cost_usd=0.001,
            model=None,
            message_id="msg_1",
            request_id="req_1",
        )
        
        period.add_entry(entry)
        
        assert "unknown" in period.models_used
        assert "unknown" in period.model_breakdowns

    def test_to_dict_daily(self) -> None:
        """Test converting AggregatedPeriod to dictionary for daily view."""
        period = AggregatedPeriod(period_key="2024-01-01")
        period.stats = AggregatedStats(
            input_tokens=1000,
            output_tokens=500,
            cache_creation_tokens=100,
            cache_read_tokens=50,
            cost=0.05,
            count=10
        )
        period.models_used = {"claude-3-haiku", "claude-3-sonnet"}
        period.model_breakdowns["claude-3-haiku"] = AggregatedStats(
            input_tokens=600,
            output_tokens=300,
            cache_creation_tokens=60,
            cache_read_tokens=30,
            cost=0.03,
            count=6
        )
        period.model_breakdowns["claude-3-sonnet"] = AggregatedStats(
            input_tokens=400,
            output_tokens=200,
            cache_creation_tokens=40,
            cache_read_tokens=20,
            cost=0.02,
            count=4
        )
        
        result = period.to_dict("date")
        
        assert result["date"] == "2024-01-01"
        assert result["input_tokens"] == 1000
        assert result["output_tokens"] == 500
        assert result["cache_creation_tokens"] == 100
        assert result["cache_read_tokens"] == 50
        assert result["total_cost"] == 0.05
        assert result["entries_count"] == 10
        assert set(result["models_used"]) == {"claude-3-haiku", "claude-3-sonnet"}
        assert "claude-3-haiku" in result["model_breakdowns"]
        assert result["model_breakdowns"]["claude-3-haiku"]["input_tokens"] == 600

    def test_to_dict_monthly(self) -> None:
        """Test converting AggregatedPeriod to dictionary for monthly view."""
        period = AggregatedPeriod(period_key="2024-01")
        period.stats = AggregatedStats(
            input_tokens=10000,
            output_tokens=5000,
            cache_creation_tokens=1000,
            cache_read_tokens=500,
            cost=0.5,
            count=100
        )
        period.models_used = {"claude-3-haiku"}
        
        result = period.to_dict("month")
        
        assert result["month"] == "2024-01"
        assert result["input_tokens"] == 10000
        assert result["total_cost"] == 0.5


class TestUsageAggregator:
    """Test cases for UsageAggregator class."""

    @pytest.fixture
    def aggregator(self) -> UsageAggregator:
        """Create a UsageAggregator instance."""
        return UsageAggregator()

    @pytest.fixture
    def sample_entries(self) -> List[UsageEntry]:
        """Create sample usage entries spanning multiple days and months."""
        entries = []
        
        # January 2024 entries
        for day in [1, 1, 2, 2, 15, 15, 31]:
            for hour in [10, 14]:
                entry = UsageEntry(
                    timestamp=datetime(2024, 1, day, hour, 0, tzinfo=timezone.utc),
                    input_tokens=100,
                    output_tokens=50,
                    cache_creation_tokens=10,
                    cache_read_tokens=5,
                    cost_usd=0.001,
                    model="claude-3-haiku" if hour == 10 else "claude-3-sonnet",
                    message_id=f"msg_{day}_{hour}",
                    request_id=f"req_{day}_{hour}",
                )
                entries.append(entry)
        
        # February 2024 entries
        for day in [1, 15, 29]:
            entry = UsageEntry(
                timestamp=datetime(2024, 2, day, 12, 0, tzinfo=timezone.utc),
                input_tokens=200,
                output_tokens=100,
                cache_creation_tokens=20,
                cache_read_tokens=10,
                cost_usd=0.002,
                model="claude-3-opus",
                message_id=f"msg_feb_{day}",
                request_id=f"req_feb_{day}",
            )
            entries.append(entry)
        
        return entries

    def test_aggregate_daily_basic(self, aggregator: UsageAggregator, sample_entries: List[UsageEntry]) -> None:
        """Test basic daily aggregation."""
        result = aggregator.aggregate_daily(sample_entries)
        
        # Should have entries for each unique day
        assert len(result) == 7  # Days: Jan 1, 2, 15, 31, Feb 1, 15, 29
        
        # Check first day (Jan 1 - 4 entries: 2 at 10AM, 2 at 2PM)
        jan1 = result[0]
        assert jan1["date"] == "2024-01-01"
        assert jan1["input_tokens"] == 400  # 4 entries * 100
        assert jan1["output_tokens"] == 200  # 4 entries * 50
        assert jan1["total_cost"] == 0.004  # 4 entries * 0.001
        assert jan1["entries_count"] == 4
        assert set(jan1["models_used"]) == {"claude-3-haiku", "claude-3-sonnet"}

    def test_aggregate_daily_with_date_filter(self, aggregator: UsageAggregator, sample_entries: List[UsageEntry]) -> None:
        """Test daily aggregation with date filters."""
        start_date = datetime(2024, 1, 15, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, 23, 59, 59, tzinfo=timezone.utc)  # Include the whole day
        
        result = aggregator.aggregate_daily(sample_entries, start_date, end_date)
        
        # Should have Jan 15 and Jan 31 (entries on those days are within the filter)
        assert len(result) == 2
        assert result[0]["date"] == "2024-01-15"
        assert result[1]["date"] == "2024-01-31"

    def test_aggregate_monthly_basic(self, aggregator: UsageAggregator, sample_entries: List[UsageEntry]) -> None:
        """Test basic monthly aggregation."""
        result = aggregator.aggregate_monthly(sample_entries)
        
        # Should have 2 months
        assert len(result) == 2
        
        # Check January
        jan = result[0]
        assert jan["month"] == "2024-01"
        assert jan["input_tokens"] == 1400  # 14 entries * 100
        assert jan["output_tokens"] == 700   # 14 entries * 50
        assert abs(jan["total_cost"] - 0.014) < 0.0000001  # Handle floating point precision
        assert jan["entries_count"] == 14
        assert set(jan["models_used"]) == {"claude-3-haiku", "claude-3-sonnet"}
        
        # Check February
        feb = result[1]
        assert feb["month"] == "2024-02"
        assert feb["input_tokens"] == 600   # 3 entries * 200
        assert feb["output_tokens"] == 300  # 3 entries * 100
        assert feb["total_cost"] == 0.006  # 3 entries * 0.002
        assert feb["entries_count"] == 3
        assert feb["models_used"] == ["claude-3-opus"]

    def test_aggregate_monthly_with_date_filter(self, aggregator: UsageAggregator, sample_entries: List[UsageEntry]) -> None:
        """Test monthly aggregation with date filters."""
        start_date = datetime(2024, 2, 1, tzinfo=timezone.utc)
        
        result = aggregator.aggregate_monthly(sample_entries, start_date)
        
        # Should only have February
        assert len(result) == 1
        assert result[0]["month"] == "2024-02"

    def test_aggregate_from_blocks_daily(self, aggregator: UsageAggregator, sample_entries: List[UsageEntry]) -> None:
        """Test aggregating from session blocks for daily view."""
        # Create mock session blocks
        from claude_monitor.core.models import SessionBlock
        
        block1 = SessionBlock(
            id="block1",
            start_time=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 1, 15, 0, tzinfo=timezone.utc),
            entries=sample_entries[:5],
            is_gap=False
        )
        
        block2 = SessionBlock(
            id="block2",
            start_time=datetime(2024, 1, 2, 10, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 2, 15, 0, tzinfo=timezone.utc),
            entries=sample_entries[5:10],
            is_gap=False
        )
        
        # Gap block should be ignored
        gap_block = SessionBlock(
            id="gap",
            start_time=datetime(2024, 1, 3, 10, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 3, 15, 0, tzinfo=timezone.utc),
            entries=[],
            is_gap=True
        )
        
        blocks = [block1, block2, gap_block]
        result = aggregator.aggregate_from_blocks(blocks, "daily")
        
        assert len(result) >= 2  # At least 2 days of data
        assert result[0]["date"] == "2024-01-01"

    def test_aggregate_from_blocks_monthly(self, aggregator: UsageAggregator, sample_entries: List[UsageEntry]) -> None:
        """Test aggregating from session blocks for monthly view."""
        from claude_monitor.core.models import SessionBlock
        
        block = SessionBlock(
            id="block1",
            start_time=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 1, 15, 0, tzinfo=timezone.utc),
            entries=sample_entries,
            is_gap=False
        )
        
        result = aggregator.aggregate_from_blocks([block], "monthly")
        
        assert len(result) == 2  # Jan and Feb
        assert result[0]["month"] == "2024-01"
        assert result[1]["month"] == "2024-02"

    def test_aggregate_from_blocks_invalid_view_type(self, aggregator: UsageAggregator) -> None:
        """Test aggregate_from_blocks with invalid view type."""
        from claude_monitor.core.models import SessionBlock
        
        block = SessionBlock(
            id="block1",
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            entries=[],
            is_gap=False
        )
        
        with pytest.raises(ValueError, match="Invalid view type"):
            aggregator.aggregate_from_blocks([block], "weekly")

    def test_calculate_totals_empty(self, aggregator: UsageAggregator) -> None:
        """Test calculating totals with empty data."""
        result = aggregator.calculate_totals([])
        
        assert result["input_tokens"] == 0
        assert result["output_tokens"] == 0
        assert result["cache_creation_tokens"] == 0
        assert result["cache_read_tokens"] == 0
        assert result["total_tokens"] == 0
        assert result["total_cost"] == 0.0
        assert result["entries_count"] == 0

    def test_calculate_totals_with_data(self, aggregator: UsageAggregator) -> None:
        """Test calculating totals with aggregated data."""
        aggregated_data = [
            {
                "date": "2024-01-01",
                "input_tokens": 1000,
                "output_tokens": 500,
                "cache_creation_tokens": 100,
                "cache_read_tokens": 50,
                "total_cost": 0.05,
                "entries_count": 10,
            },
            {
                "date": "2024-01-02",
                "input_tokens": 2000,
                "output_tokens": 1000,
                "cache_creation_tokens": 200,
                "cache_read_tokens": 100,
                "total_cost": 0.10,
                "entries_count": 20,
            },
        ]
        
        result = aggregator.calculate_totals(aggregated_data)
        
        assert result["input_tokens"] == 3000
        assert result["output_tokens"] == 1500
        assert result["cache_creation_tokens"] == 300
        assert result["cache_read_tokens"] == 150
        assert result["total_tokens"] == 4950
        assert abs(result["total_cost"] - 0.15) < 0.0000001  # Handle floating point precision
        assert result["entries_count"] == 30

    def test_aggregate_daily_empty_entries(self, aggregator: UsageAggregator) -> None:
        """Test daily aggregation with empty entries list."""
        result = aggregator.aggregate_daily([])
        assert result == []

    def test_aggregate_monthly_empty_entries(self, aggregator: UsageAggregator) -> None:
        """Test monthly aggregation with empty entries list."""
        result = aggregator.aggregate_monthly([])
        assert result == []

    def test_period_sorting(self, aggregator: UsageAggregator) -> None:
        """Test that periods are sorted correctly."""
        # Create entries in non-chronological order
        entries = [
            UsageEntry(
                timestamp=datetime(2024, 1, 15, 12, 0, tzinfo=timezone.utc),
                input_tokens=100,
                output_tokens=50,
                cache_creation_tokens=0,
                cache_read_tokens=0,
                cost_usd=0.001,
                model="claude-3-haiku",
                message_id="msg_3",
                request_id="req_3",
            ),
            UsageEntry(
                timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
                input_tokens=100,
                output_tokens=50,
                cache_creation_tokens=0,
                cache_read_tokens=0,
                cost_usd=0.001,
                model="claude-3-haiku",
                message_id="msg_1",
                request_id="req_1",
            ),
            UsageEntry(
                timestamp=datetime(2024, 1, 10, 12, 0, tzinfo=timezone.utc),
                input_tokens=100,
                output_tokens=50,
                cache_creation_tokens=0,
                cache_read_tokens=0,
                cost_usd=0.001,
                model="claude-3-haiku",
                message_id="msg_2",
                request_id="req_2",
            ),
        ]
        
        # Test daily sorting
        daily_result = aggregator.aggregate_daily(entries)
        assert len(daily_result) == 3
        assert daily_result[0]["date"] == "2024-01-01"
        assert daily_result[1]["date"] == "2024-01-10"
        assert daily_result[2]["date"] == "2024-01-15"
        
        # Test monthly sorting
        monthly_entries = [
            UsageEntry(
                timestamp=datetime(2024, 3, 1, 12, 0, tzinfo=timezone.utc),
                input_tokens=100,
                output_tokens=50,
                cache_creation_tokens=0,
                cache_read_tokens=0,
                cost_usd=0.001,
                model="claude-3-haiku",
                message_id="msg_3",
                request_id="req_3",
            ),
            UsageEntry(
                timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
                input_tokens=100,
                output_tokens=50,
                cache_creation_tokens=0,
                cache_read_tokens=0,
                cost_usd=0.001,
                model="claude-3-haiku",
                message_id="msg_1",
                request_id="req_1",
            ),
            UsageEntry(
                timestamp=datetime(2024, 2, 1, 12, 0, tzinfo=timezone.utc),
                input_tokens=100,
                output_tokens=50,
                cache_creation_tokens=0,
                cache_read_tokens=0,
                cost_usd=0.001,
                model="claude-3-haiku",
                message_id="msg_2",
                request_id="req_2",
            ),
        ]
        
        monthly_result = aggregator.aggregate_monthly(monthly_entries)
        assert len(monthly_result) == 3
        assert monthly_result[0]["month"] == "2024-01"
        assert monthly_result[1]["month"] == "2024-02"
        assert monthly_result[2]["month"] == "2024-03"