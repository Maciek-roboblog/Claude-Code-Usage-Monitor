"""Historical data management for preserving daily usage beyond Claude's 30-day cleanup.

This module provides functionality to:
- Automatically save daily aggregated data
- Read historical data from saved files
- Merge historical and current data for comprehensive views
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class HistoryManager:
    """Manages historical usage data storage and retrieval."""

    def __init__(self, data_dir: Optional[Path] = None):
        """Initialize the history manager.

        Args:
            data_dir: Directory to store historical data. Defaults to ~/.claude-monitor/history
        """
        self.data_dir = data_dir or Path.home() / ".claude-monitor" / "history"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.daily_dir = self.data_dir / "daily"
        self.daily_dir.mkdir(parents=True, exist_ok=True)
        
        # Keep track of which dates have been saved this session to avoid duplicates
        self._saved_dates: Set[str] = set()

    def _get_daily_file_path(self, date_str: str) -> Path:
        """Get the file path for a specific date's data.

        Args:
            date_str: Date string in YYYY-MM-DD format

        Returns:
            Path to the daily data file
        """
        # Organize by year and month for better file management
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d")
            year = date.strftime("%Y")
            month = date.strftime("%m")
            
            month_dir = self.daily_dir / year / month
            month_dir.mkdir(parents=True, exist_ok=True)
            
            return month_dir / f"{date_str}.json"
        except ValueError:
            # Fallback for invalid date formats
            return self.daily_dir / f"{date_str}.json"

    def save_daily_data(self, daily_data: List[Dict[str, Any]], overwrite: bool = False) -> int:
        """Save daily aggregated data to historical storage.

        Args:
            daily_data: List of daily aggregated data dictionaries
            overwrite: Whether to overwrite existing data for the same date

        Returns:
            Number of days saved
        """
        saved_count = 0
        
        for day_data in daily_data:
            date_str = day_data.get("date")
            if not date_str:
                logger.warning("Daily data missing 'date' field, skipping")
                continue
            
            # Skip if already saved in this session (unless overwrite)
            if not overwrite and date_str in self._saved_dates:
                continue
            
            file_path = self._get_daily_file_path(date_str)
            
            # Check if file exists and whether to overwrite
            if file_path.exists() and not overwrite:
                # Load existing data to check if it needs updating
                try:
                    with open(file_path, "r") as f:
                        existing_data = json.load(f)
                    
                    # If the data is identical, skip
                    if existing_data == day_data:
                        self._saved_dates.add(date_str)
                        continue
                    
                    # If existing data has more information, keep it
                    existing_tokens = existing_data.get("input_tokens", 0) + existing_data.get("output_tokens", 0)
                    new_tokens = day_data.get("input_tokens", 0) + day_data.get("output_tokens", 0)
                    
                    if existing_tokens >= new_tokens:
                        self._saved_dates.add(date_str)
                        continue
                        
                except Exception as e:
                    logger.warning(f"Error reading existing data for {date_str}: {e}")
            
            # Save the data
            try:
                temp_file = file_path.with_suffix(".tmp")
                with open(temp_file, "w") as f:
                    json.dump(day_data, f, indent=2, default=str)
                temp_file.replace(file_path)
                
                self._saved_dates.add(date_str)
                saved_count += 1
                logger.debug(f"Saved historical data for {date_str}")
                
            except Exception as e:
                logger.error(f"Failed to save historical data for {date_str}: {e}")
        
        if saved_count > 0:
            logger.info(f"Saved historical data for {saved_count} days")
        
        return saved_count

    def load_historical_daily_data(
        self, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        days_back: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Load historical daily data within the specified range.

        Args:
            start_date: Start date for data retrieval
            end_date: End date for data retrieval
            days_back: Alternative to date range - get last N days of data

        Returns:
            List of historical daily data dictionaries
        """
        historical_data = []
        
        # Determine date range
        if days_back:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
        elif not start_date:
            # Default to loading all available data
            start_date = datetime(2020, 1, 1)  # Arbitrary old date
        
        if not end_date:
            end_date = datetime.now()
        
        # Scan for files in the date range
        for year_dir in sorted(self.daily_dir.iterdir()):
            if not year_dir.is_dir():
                continue
                
            try:
                year = int(year_dir.name)
                
                # Skip years outside our range
                if year < start_date.year or year > end_date.year:
                    continue
                    
                for month_dir in sorted(year_dir.iterdir()):
                    if not month_dir.is_dir():
                        continue
                        
                    for file_path in sorted(month_dir.glob("*.json")):
                        try:
                            # Extract date from filename
                            date_str = file_path.stem
                            file_date = datetime.strptime(date_str, "%Y-%m-%d")
                            
                            # Make file_date timezone-naive for comparison
                            # Convert start_date and end_date to naive if they're aware
                            compare_start = start_date.replace(tzinfo=None) if start_date and start_date.tzinfo else start_date
                            compare_end = end_date.replace(tzinfo=None) if end_date and end_date.tzinfo else end_date
                            
                            # Check if within range
                            if compare_start and file_date < compare_start:
                                continue
                            if compare_end and file_date > compare_end:
                                continue
                            
                            # Load the data
                            with open(file_path, "r") as f:
                                data = json.load(f)
                                historical_data.append(data)
                                
                        except (ValueError, json.JSONDecodeError) as e:
                            logger.warning(f"Error loading {file_path}: {e}")
                            
            except ValueError:
                # Not a year directory, skip
                continue
        
        # Sort by date
        historical_data.sort(key=lambda x: x.get("date", ""))
        
        logger.info(f"Loaded {len(historical_data)} days of historical data")
        return historical_data

    def merge_with_current_data(
        self,
        current_data: List[Dict[str, Any]],
        historical_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Merge current and historical daily data, preferring current data for overlapping dates.

        Args:
            current_data: Current daily aggregated data
            historical_data: Historical daily data

        Returns:
            Merged list of daily data, sorted by date
        """
        # Create a dictionary keyed by date for efficient merging
        merged_dict = {}
        
        # Add historical data first
        for data in historical_data:
            date_str = data.get("date")
            if date_str:
                merged_dict[date_str] = data
        
        # Add/overwrite with current data (more recent/accurate)
        for data in current_data:
            date_str = data.get("date")
            if date_str:
                merged_dict[date_str] = data
        
        # Convert back to sorted list
        merged_data = list(merged_dict.values())
        merged_data.sort(key=lambda x: x.get("date", ""))
        
        logger.debug(f"Merged data contains {len(merged_data)} days")
        return merged_data

    def cleanup_old_data(self, days_to_keep: int = 365) -> int:
        """Clean up historical data older than specified days.

        Args:
            days_to_keep: Number of days of historical data to keep

        Returns:
            Number of files deleted
        """
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        deleted_count = 0
        
        for year_dir in self.daily_dir.iterdir():
            if not year_dir.is_dir():
                continue
                
            for month_dir in year_dir.iterdir():
                if not month_dir.is_dir():
                    continue
                    
                for file_path in month_dir.glob("*.json"):
                    try:
                        date_str = file_path.stem
                        file_date = datetime.strptime(date_str, "%Y-%m-%d")
                        
                        if file_date < cutoff_date:
                            file_path.unlink()
                            deleted_count += 1
                            
                    except (ValueError, OSError) as e:
                        logger.warning(f"Error processing {file_path}: {e}")
                
                # Remove empty month directories
                if not any(month_dir.iterdir()):
                    month_dir.rmdir()
            
            # Remove empty year directories
            if not any(year_dir.iterdir()):
                year_dir.rmdir()
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old historical files")
        
        return deleted_count

    def aggregate_monthly_from_daily(
        self,
        daily_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Aggregate daily data into monthly summaries.

        Args:
            daily_data: List of daily aggregated data dictionaries

        Returns:
            List of monthly aggregated data dictionaries
        """
        from collections import defaultdict
        
        monthly_dict = {}
        
        for day in daily_data:
            # Extract month key from date "2024-12-01" -> "2024-12"
            date_str = day.get("date", "")
            if not date_str or len(date_str) < 7:
                continue
                
            month_key = date_str[:7]  # "YYYY-MM"
            
            # Initialize month data if not exists
            if month_key not in monthly_dict:
                monthly_dict[month_key] = {
                    "month": month_key,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cache_creation_tokens": 0,
                    "cache_read_tokens": 0,
                    "total_cost": 0.0,
                    "entries_count": 0,
                    "models_used": set(),
                    "model_breakdowns": defaultdict(lambda: {
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "cache_creation_tokens": 0,
                        "cache_read_tokens": 0,
                        "cost": 0.0,
                        "count": 0
                    })
                }
            
            # Accumulate statistics
            month_data = monthly_dict[month_key]
            month_data["input_tokens"] += day.get("input_tokens", 0)
            month_data["output_tokens"] += day.get("output_tokens", 0)
            month_data["cache_creation_tokens"] += day.get("cache_creation_tokens", 0)
            month_data["cache_read_tokens"] += day.get("cache_read_tokens", 0)
            month_data["total_cost"] += day.get("total_cost", 0.0)
            month_data["entries_count"] += day.get("entries_count", 0)
            
            # Accumulate models used
            models = day.get("models_used", [])
            if isinstance(models, list):
                month_data["models_used"].update(models)
            
            # Accumulate model breakdowns
            model_breakdowns = day.get("model_breakdowns", {})
            if isinstance(model_breakdowns, dict):
                for model, stats in model_breakdowns.items():
                    breakdown = month_data["model_breakdowns"][model]
                    breakdown["input_tokens"] += stats.get("input_tokens", 0)
                    breakdown["output_tokens"] += stats.get("output_tokens", 0)
                    breakdown["cache_creation_tokens"] += stats.get("cache_creation_tokens", 0)
                    breakdown["cache_read_tokens"] += stats.get("cache_read_tokens", 0)
                    breakdown["cost"] += stats.get("cost", 0.0)
                    breakdown["count"] += stats.get("count", 0)
        
        # Convert to list format
        result = []
        for month_key in sorted(monthly_dict.keys()):
            month_data = monthly_dict[month_key]
            # Convert set to sorted list for models_used
            month_data["models_used"] = sorted(list(month_data["models_used"]))
            # Convert defaultdict to regular dict for model_breakdowns
            month_data["model_breakdowns"] = dict(month_data["model_breakdowns"])
            result.append(month_data)
        
        return result

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about stored historical data.

        Returns:
            Dictionary with statistics about historical data
        """
        total_files = 0
        oldest_date = None
        newest_date = None
        total_size = 0
        
        for year_dir in self.daily_dir.iterdir():
            if not year_dir.is_dir():
                continue
                
            for month_dir in year_dir.iterdir():
                if not month_dir.is_dir():
                    continue
                    
                for file_path in month_dir.glob("*.json"):
                    total_files += 1
                    total_size += file_path.stat().st_size
                    
                    try:
                        date_str = file_path.stem
                        file_date = datetime.strptime(date_str, "%Y-%m-%d")
                        
                        if oldest_date is None or file_date < oldest_date:
                            oldest_date = file_date
                        if newest_date is None or file_date > newest_date:
                            newest_date = file_date
                            
                    except ValueError:
                        continue
        
        return {
            "total_files": total_files,
            "oldest_date": oldest_date.strftime("%Y-%m-%d") if oldest_date else None,
            "newest_date": newest_date.strftime("%Y-%m-%d") if newest_date else None,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "data_directory": str(self.daily_dir),
        }