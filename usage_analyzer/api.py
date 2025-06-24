"""
Simplified main entry point for Claude Usage Analyzer.

This module provides a streamlined interface to generate response_final.json
with only the essential functionality needed.
"""

import json
from datetime import datetime
from pathlib import Path

from usage_analyzer.core.data_loader import DataLoader
from usage_analyzer.core.identifier import SessionBlockIdentifier
from usage_analyzer.core.calculator import BurnRateCalculator
from usage_analyzer.output.json_formatter import JSONFormatter
from usage_analyzer.utils.path_discovery import discover_claude_data_paths
from usage_analyzer.models.data_structures import CostMode


def analyze_usage():
    """Main entry point to generate response_final.json."""

    data_loader = DataLoader()
    identifier = SessionBlockIdentifier(session_duration_hours=5)
    calculator = BurnRateCalculator()
    formatter = JSONFormatter()

    # Load usage data from Claude directories (using AUTO mode by default)
    # print("Loading usage data...")
    entries = data_loader.load_usage_data(mode=CostMode.AUTO)
    # print(f"Loaded {len(entries)} usage entries")

    # Identify session blocks
    # print("Identifying session blocks...")
    blocks = identifier.identify_blocks(entries)

    for block in blocks:
        if block.is_active:
            burn_rate = calculator.calculate_burn_rate(block)
            if burn_rate:
                block.burn_rate_snapshot = burn_rate
                projection = calculator.project_block_usage(block)
                if projection:
                    block.projection_data = {
                        "totalTokens": projection.projected_total_tokens,
                        "totalCost": projection.projected_total_cost,
                        "remainingMinutes": projection.remaining_minutes
                    }

    json_output = formatter.format_blocks(blocks)
#
    return json.loads(json_output)


print(json.dumps(analyze_usage(), indent=2, ensure_ascii=False))
