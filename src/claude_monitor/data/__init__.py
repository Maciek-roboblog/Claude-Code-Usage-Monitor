"""Data package for Claude Monitor.

Provides data loading from multiple sources:
- Claude Code (~/.claude/projects/*.jsonl)
- OpenCode (~/.local/share/opencode/storage/message/*.json)
"""

from claude_monitor.data.reader import (
    DataSource,
    detect_available_sources,
    detect_data_source,
    get_data_source_info,
    load_usage_entries,
    load_usage_entries_unified,
)

__all__ = [
    "DataSource",
    "detect_available_sources",
    "detect_data_source",
    "get_data_source_info",
    "load_usage_entries",
    "load_usage_entries_unified",
]
