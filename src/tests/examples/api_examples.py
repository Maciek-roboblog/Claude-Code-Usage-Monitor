"""Usage examples for the Claude Monitor API wrapper.

This module demonstrates how to use the backward compatibility API wrapper
to analyze Claude usage data in various ways.
"""

import json

# Import functions directly from the analysis module
from claude_monitor.data.analysis import analyze_usage
from claude_monitor.utils.formatting import format_currency, format_time


# Create helper functions that replace the removed facade functions
def analyze_usage_with_metadata(
    hours_back=96, use_cache=True, quick_start=False, data_path=None
):
    """Enhanced analyze_usage with comprehensive metadata."""
    return analyze_usage(
        hours_back=hours_back,
        use_cache=use_cache,
        quick_start=quick_start,
        data_path=data_path,
    )


def analyze_usage_json(hours_back=96, use_cache=True, data_path=None, indent=2):
    """Analyze usage and return JSON string."""
    result = analyze_usage(
        hours_back=hours_back, use_cache=use_cache, data_path=data_path
    )
    return json.dumps(result, indent=indent, default=str)


def get_usage_summary(hours_back=96, use_cache=True, data_path=None):
    """Get high-level usage summary statistics."""
    result = analyze_usage(
        hours_back=hours_back, use_cache=use_cache, data_path=data_path
    )
    blocks = result.get("blocks", [])
    return _create_summary_stats(blocks)


def print_usage_json(hours_back=96, use_cache=True, data_path=None):
    """Print usage analysis as JSON to stdout."""
    json_result = analyze_usage_json(
        hours_back=hours_back, use_cache=use_cache, data_path=data_path
    )
    print(json_result)


def print_usage_summary(hours_back=96, use_cache=True, data_path=None):
    """Print human-readable usage summary."""
    summary = get_usage_summary(
        hours_back=hours_back, use_cache=use_cache, data_path=data_path
    )

    if summary.get("error"):
        print(f"Error: {summary.get('error_details', 'Unknown error')}")
        return

    print(f"Claude Usage Summary (Last {hours_back} Hours)")
    print("=" * 50)
    print(f"Total Sessions: {summary.get('total_sessions', 0)}")
    print(f"Total Cost: {format_currency(summary.get('total_cost', 0))}")
    print(f"Total Tokens: {summary.get('total_tokens', 0):,}")
    print(
        f"Average Session Cost: {format_currency(summary.get('average_session_cost', 0))}"
    )

    if summary.get("active_sessions", 0) > 0:
        print(f"Active Sessions: {summary['active_sessions']}")

    if summary.get("total_duration_minutes", 0) > 0:
        print(f"Total Duration: {format_time(summary['total_duration_minutes'])}")


def _create_summary_stats(blocks):
    """Create summary statistics from session blocks."""
    if not blocks:
        return {
            "total_sessions": 0,
            "total_cost": 0.0,
            "total_tokens": 0,
            "average_session_cost": 0.0,
            "active_sessions": 0,
            "total_duration_minutes": 0,
        }

    total_sessions = len(blocks)
    total_cost = sum(block.get("cost", 0) for block in blocks)
    total_tokens = sum(block.get("tokens", {}).get("total", 0) for block in blocks)
    active_sessions = sum(1 for block in blocks if block.get("is_active", False))
    total_duration_minutes = sum(block.get("duration_minutes", 0) for block in blocks)

    average_session_cost = total_cost / total_sessions if total_sessions > 0 else 0

    return {
        "total_sessions": total_sessions,
        "total_cost": total_cost,
        "total_tokens": total_tokens,
        "average_session_cost": average_session_cost,
        "active_sessions": active_sessions,
        "total_duration_minutes": total_duration_minutes,
    }


# For backward compatibility
analyze_usage_direct = analyze_usage


def example_basic_usage():
    """Example 1: Basic usage (backward compatibility with original API)

    This example shows how to use the API in the same way as the original
    usage_analyzer.api.analyze_usage() function.
    """
    print("=== Example 1: Basic Usage ===")

    try:
        # Simple usage - returns list of blocks just like the original
        blocks = analyze_usage()

        print(f"Found {len(blocks)} session blocks")

        # Process blocks just like the original API
        for block in blocks:
            print(
                f"Block {block['id']}: {block['totalTokens']} tokens, ${block['costUSD']:.2f}"
            )

            if block["isActive"]:
                print(f"  - Active block with {block['durationMinutes']:.1f} minutes")

                # Check for burn rate data
                if "burnRate" in block:
                    print(
                        f"  - Burn rate: {block['burnRate']['tokensPerMinute']:.1f} tokens/min"
                    )

                # Check for projections
                if "projection" in block:
                    proj = block["projection"]
                    print(
                        f"  - Projected: {proj['totalTokens']} tokens, ${proj['totalCost']:.2f}"
                    )

    except Exception as e:
        print(f"Error: {e}")


def example_advanced_usage():
    """Example 2: Advanced usage with metadata and time filtering

    This example shows how to use the enhanced features of the new API
    while maintaining backward compatibility.
    """
    print("\n=== Example 2: Advanced Usage ===")

    try:
        # Get full results with metadata
        result = analyze_usage_with_metadata(
            hours_back=24,  # Only last 24 hours
            quick_start=True,  # Fast analysis
        )

        blocks = result["blocks"]
        metadata = result["metadata"]

        print(f"Analysis completed in {metadata['load_time_seconds']:.3f}s")
        print(f"Processed {metadata['entries_processed']} entries")
        print(f"Created {metadata['blocks_created']} blocks")

        # Find active blocks
        active_blocks = [b for b in blocks if b["isActive"]]
        print(f"Active blocks: {len(active_blocks)}")

        # Calculate total usage
        total_cost = sum(b["costUSD"] for b in blocks)
        total_tokens = sum(b["totalTokens"] for b in blocks)

        print(f"Total usage: {total_tokens:,} tokens, ${total_cost:.2f}")

    except Exception as e:
        print(f"Error: {e}")


def example_json_output():
    """Example 3: JSON output (same as original API when used as script)

    This example shows how to get JSON output exactly like the original API.
    """
    print("\n=== Example 3: JSON Output ===")

    try:
        # Get JSON string (same format as original)
        json_output = analyze_usage_json(hours_back=48)

        # Parse it back to verify
        blocks = json.loads(json_output)
        print(f"JSON contains {len(blocks)} blocks")

        # Print a formatted sample
        if blocks:
            sample_block = blocks[0]
            print("\nSample block structure:")
            print(json.dumps(sample_block, indent=2)[:500] + "...")

    except Exception as e:
        print(f"Error: {e}")


def example_usage_summary():
    """Example 4: Usage summary and statistics

    This example shows how to get high-level statistics about usage.
    """
    print("\n=== Example 4: Usage Summary ===")

    try:
        # Get summary statistics
        summary = get_usage_summary(hours_back=168)  # Last week

        print(f"Total Cost: ${summary['total_cost']:.2f}")
        print(f"Total Tokens: {summary['total_tokens']:,}")
        print(f"Total Blocks: {summary['total_blocks']}")
        print(f"Active Blocks: {summary['active_blocks']}")

        # Model breakdown
        print("\nModel usage:")
        for model, stats in summary["model_stats"].items():
            print(f"  {model}: {stats['tokens']:,} tokens, ${stats['cost']:.2f}")

        # Performance info
        perf = summary["performance"]
        print(f"\nPerformance: {perf['load_time_seconds']:.3f}s load time")

    except Exception as e:
        print(f"Error: {e}")


def example_custom_data_path():
    """Example 5: Using custom data path

    This example shows how to analyze data from a custom location.
    """
    print("\n=== Example 5: Custom Data Path ===")

    try:
        # You can specify a custom path to Claude data
        custom_path = "/path/to/claude/data"  # Replace with actual path

        # This will use the custom path instead of default ~/.claude/projects
        blocks = analyze_usage(
            data_path=custom_path,
            hours_back=24,
            quick_start=True,
        )

        print(f"Analyzed {len(blocks)} blocks from custom path")

    except Exception as e:
        print(f"Error (expected if path doesn't exist): {e}")


def example_direct_import():
    """Example 6: Direct import from main module

    This example shows how to import the function directly from the main module.
    """
    print("\n=== Example 6: Direct Import ===")

    try:
        # You can import directly from claude_monitor module
        blocks = analyze_usage_direct()

        print(f"Direct import worked! Found {len(blocks)} blocks")

    except Exception as e:
        print(f"Error: {e}")


def example_error_handling():
    """Example 7: Error handling patterns

    This example shows how the API handles errors gracefully.
    """
    print("\n=== Example 7: Error Handling ===")

    try:
        # This might fail if no data is available
        blocks = analyze_usage(
            data_path="/nonexistent/path",
            hours_back=1,
        )

        print(f"Success: {len(blocks)} blocks")

    except Exception as e:
        print(f"Handled error gracefully: {e}")
        print("The API reports errors to logging")


def example_print_functions():
    """Example 8: Print functions for direct output

    This example shows the convenience print functions.
    """
    print("\n=== Example 8: Print Functions ===")

    try:
        # Print JSON directly (like original API as script)
        print("JSON output:")
        print_usage_json(hours_back=24)

        print("\nSummary output:")
        print_usage_summary(hours_back=24)

    except Exception as e:
        print(f"Error: {e}")


def example_compatibility_check():
    """Example 9: Compatibility check with original API

    This example shows how to verify the output is compatible with the original.
    """
    print("\n=== Example 9: Compatibility Check ===")

    try:
        # Get data in original format
        blocks = analyze_usage()

        # Check structure matches original expectations
        if blocks:
            block = blocks[0]
            required_fields = [
                "id",
                "isActive",
                "isGap",
                "startTime",
                "endTime",
                "totalTokens",
                "costUSD",
                "models",
                "durationMinutes",
            ]

            missing_fields = [field for field in required_fields if field not in block]

            if missing_fields:
                print(f"Missing fields: {missing_fields}")
            else:
                print("All required fields present - compatible with original API")

            # Check for enhanced fields
            enhanced_fields = ["burnRate", "projection", "limitMessages"]
            present_enhanced = [field for field in enhanced_fields if field in block]

            if present_enhanced:
                print(f"Enhanced fields available: {present_enhanced}")

    except Exception as e:
        print(f"Error: {e}")


def run_all_examples():
    """Run all examples to demonstrate the API functionality."""
    print("Claude Monitor API Examples")
    print("=" * 50)

    examples = [
        example_basic_usage,
        example_advanced_usage,
        example_json_output,
        example_usage_summary,
        example_custom_data_path,
        example_direct_import,
        example_error_handling,
        example_print_functions,
        example_compatibility_check,
    ]

    for example in examples:
        try:
            example()
        except Exception as e:
            print(f"Example {example.__name__} failed: {e}")

    print("\n" + "=" * 50)
    print("All examples completed!")


if __name__ == "__main__":
    run_all_examples()
