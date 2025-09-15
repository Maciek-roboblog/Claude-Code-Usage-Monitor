"""Data aggregator for daily and monthly statistics.

This module provides functionality to aggregate Claude usage data
by day and month, similar to ccusage's functionality.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from claude_monitor.core.models import SessionBlock, UsageEntry, normalize_model_name
from claude_monitor.utils.time_utils import TimezoneHandler

logger = logging.getLogger(__name__)


@dataclass
class AggregatedStats:
    """Statistics for aggregated usage data."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    cost: float = 0.0
    count: int = 0

    def add_entry(self, entry: UsageEntry) -> None:
        """Add an entry's statistics to this aggregate."""
        self.input_tokens += entry.input_tokens
        self.output_tokens += entry.output_tokens
        self.cache_creation_tokens += entry.cache_creation_tokens
        self.cache_read_tokens += entry.cache_read_tokens
        self.cost += entry.cost_usd
        self.count += 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_creation_tokens": self.cache_creation_tokens,
            "cache_read_tokens": self.cache_read_tokens,
            "cost": self.cost,
            "count": self.count,
        }


@dataclass
class AggregatedPeriod:
    """Aggregated data for a time period (day or month)."""

    period_key: str
    stats: AggregatedStats = field(default_factory=AggregatedStats)
    models_used: set = field(default_factory=set)
    model_breakdowns: Dict[str, AggregatedStats] = field(
        default_factory=lambda: defaultdict(AggregatedStats)
    )

    def add_entry(self, entry: UsageEntry) -> None:
        """Add an entry to this period's aggregate."""
        # Add to overall stats
        self.stats.add_entry(entry)

        # Track model
        model = normalize_model_name(entry.model) if entry.model else "unknown"
        self.models_used.add(model)

        # Add to model-specific stats
        self.model_breakdowns[model].add_entry(entry)

    def to_dict(self, period_type: str) -> Dict[str, Any]:
        """Convert to dictionary format for display."""
        result = {
            period_type: self.period_key,
            "input_tokens": self.stats.input_tokens,
            "output_tokens": self.stats.output_tokens,
            "cache_creation_tokens": self.stats.cache_creation_tokens,
            "cache_read_tokens": self.stats.cache_read_tokens,
            "total_cost": self.stats.cost,
            "models_used": sorted(list(self.models_used)),
            "model_breakdowns": {
                model: stats.to_dict() for model, stats in self.model_breakdowns.items()
            },
            "entries_count": self.stats.count,
        }
        return result


class UsageAggregator:
    """Aggregates usage data for daily and monthly reports."""

    def __init__(
        self, data_path: str, aggregation_mode: str = "daily", timezone: str = "UTC"
    ):
        """Initialize the aggregator.

        Args:
            data_path: Path to the data directory
            aggregation_mode: Mode of aggregation ('daily' or 'monthly')
            timezone: Timezone string for date formatting
        """
        self.data_path = data_path
        self.aggregation_mode = aggregation_mode
        self.timezone = timezone
        self.timezone_handler = TimezoneHandler()

    def _aggregate_by_period(
        self,
        entries: List[UsageEntry],
        period_key_func: Callable[[datetime], str],
        period_type: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Generic aggregation by time period.

        Args:
            entries: List of usage entries
            period_key_func: Function to extract period key from timestamp
            period_type: Type of period ('date' or 'month')
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List of aggregated data dictionaries
        """
        period_data: Dict[str, AggregatedPeriod] = {}

        for entry in entries:
            # Apply date filters
            if start_date and entry.timestamp < start_date:
                continue
            if end_date and entry.timestamp > end_date:
                continue

            # Get period key
            period_key = period_key_func(entry.timestamp)

            # Get or create period aggregate
            if period_key not in period_data:
                period_data[period_key] = AggregatedPeriod(period_key)

            # Add entry to period
            period_data[period_key].add_entry(entry)

        # Convert to list and sort
        result = []
        for period_key in sorted(period_data.keys()):
            period = period_data[period_key]
            result.append(period.to_dict(period_type))

        return result

    def aggregate_daily(
        self,
        entries: List[UsageEntry],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Aggregate usage data by day.

        Args:
            entries: List of usage entries
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List of daily aggregated data
        """
        return self._aggregate_by_period(
            entries,
            lambda timestamp: timestamp.strftime("%Y-%m-%d"),
            "date",
            start_date,
            end_date,
        )

    def aggregate_monthly(
        self,
        entries: List[UsageEntry],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Aggregate usage data by month.

        Args:
            entries: List of usage entries
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List of monthly aggregated data
        """
        return self._aggregate_by_period(
            entries,
            lambda timestamp: timestamp.strftime("%Y-%m"),
            "month",
            start_date,
            end_date,
        )

    def aggregate_from_blocks(
        self, blocks: List[SessionBlock], view_type: str = "daily"
    ) -> List[Dict[str, Any]]:
        """Aggregate data from session blocks.

        Args:
            blocks: List of session blocks
            view_type: Type of aggregation ('daily' or 'monthly')

        Returns:
            List of aggregated data
        """
        # Validate view type
        if view_type not in ["daily", "monthly"]:
            raise ValueError(
                f"Invalid view type: {view_type}. Must be 'daily' or 'monthly'"
            )

        # Extract all entries from blocks
        all_entries = []
        for block in blocks:
            if not block.is_gap:
                all_entries.extend(block.entries)

        # Aggregate based on view type
        if view_type == "daily":
            return self.aggregate_daily(all_entries)
        else:
            return self.aggregate_monthly(all_entries)

    def calculate_totals(self, aggregated_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate totals from aggregated data.

        Args:
            aggregated_data: List of aggregated daily or monthly data

        Returns:
            Dictionary with total statistics
        """
        total_stats = AggregatedStats()

        for data in aggregated_data:
            total_stats.input_tokens += data.get("input_tokens", 0)
            total_stats.output_tokens += data.get("output_tokens", 0)
            total_stats.cache_creation_tokens += data.get("cache_creation_tokens", 0)
            total_stats.cache_read_tokens += data.get("cache_read_tokens", 0)
            total_stats.cost += data.get("total_cost", 0.0)
            total_stats.count += data.get("entries_count", 0)

        return {
            "input_tokens": total_stats.input_tokens,
            "output_tokens": total_stats.output_tokens,
            "cache_creation_tokens": total_stats.cache_creation_tokens,
            "cache_read_tokens": total_stats.cache_read_tokens,
            "total_tokens": (
                total_stats.input_tokens
                + total_stats.output_tokens
                + total_stats.cache_creation_tokens
                + total_stats.cache_read_tokens
            ),
            "total_cost": total_stats.cost,
            "entries_count": total_stats.count,
        }

    def aggregate(self) -> List[Dict[str, Any]]:
        """Main aggregation method that reads data and returns aggregated results.

        Returns:
            List of aggregated data based on aggregation_mode
        """
        from claude_monitor.data.reader import load_usage_entries

        logger.info(f"Starting aggregation in {self.aggregation_mode} mode")

        # Load usage entries
        entries, _ = load_usage_entries(data_path=self.data_path)

        if not entries:
            logger.warning("No usage entries found")
            return []

        # Apply timezone to entries
        for entry in entries:
            if entry.timestamp.tzinfo is None:
                entry.timestamp = self.timezone_handler.ensure_timezone(entry.timestamp)

        # Aggregate based on mode
        if self.aggregation_mode == "daily":
            return self.aggregate_daily(entries)
        elif self.aggregation_mode == "monthly":
            return self.aggregate_monthly(entries)
        else:
            raise ValueError(f"Invalid aggregation mode: {self.aggregation_mode}")
