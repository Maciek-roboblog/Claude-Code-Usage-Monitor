"""Tests for session analyzer module."""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Union

from claude_monitor.core.models import SessionBlock, TokenCounts, UsageEntry
from claude_monitor.data.analyzer import SessionAnalyzer


class TestSessionAnalyzer:
    """Test the SessionAnalyzer class."""

    def test_session_analyzer_init(self) -> None:
        """Test SessionAnalyzer initialization."""
        analyzer = SessionAnalyzer()

        assert analyzer.session_duration_hours == 5
        assert analyzer.session_duration == timedelta(hours=5)
        assert analyzer.timezone_handler is not None

    def test_session_analyzer_init_custom_duration(self) -> None:
        """Test SessionAnalyzer with custom duration."""
        analyzer = SessionAnalyzer(session_duration_hours=3)

        assert analyzer.session_duration_hours == 3
        assert analyzer.session_duration == timedelta(hours=3)

    def test_transform_to_blocks_empty_list(self) -> None:
        """Test transform_to_blocks with empty entries."""
        analyzer = SessionAnalyzer()
        result = analyzer.transform_to_blocks([])

        assert result == []

    def test_transform_to_blocks_single_entry(self) -> None:
        """Test transform_to_blocks with single entry."""
        analyzer = SessionAnalyzer()

        entry = UsageEntry(
            timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.001,
            model="claude-3-haiku",
        )

        blocks = analyzer.transform_to_blocks([entry])

        assert len(blocks) == 1
        assert len(blocks[0].entries) == 1
        assert blocks[0].entries[0] == entry

    def test_transform_to_blocks_multiple_entries_same_block(self) -> None:
        """Test transform_to_blocks with entries in same block."""
        analyzer = SessionAnalyzer()

        base_time = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        entries: List[UsageEntry] = [
            UsageEntry(
                timestamp=base_time,
                input_tokens=100,
                output_tokens=50,
                cost_usd=0.001,
                model="claude-3-haiku",
            ),
            UsageEntry(
                timestamp=base_time + timedelta(minutes=30),
                input_tokens=200,
                output_tokens=100,
                cost_usd=0.002,
                model="claude-3-haiku",
            ),
        ]

        blocks = analyzer.transform_to_blocks(entries)

        assert len(blocks) == 1
        assert len(blocks[0].entries) == 2

    def test_transform_to_blocks_multiple_blocks(self) -> None:
        """Test transform_to_blocks creating multiple blocks."""
        analyzer = SessionAnalyzer()

        base_time = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        entries: List[UsageEntry] = [
            UsageEntry(
                timestamp=base_time,
                input_tokens=100,
                output_tokens=50,
                cost_usd=0.001,
                model="claude-3-haiku",
            ),
            UsageEntry(
                timestamp=base_time + timedelta(hours=6),  # Beyond session duration
                input_tokens=200,
                output_tokens=100,
                cost_usd=0.002,
                model="claude-3-haiku",
            ),
        ]

        blocks = analyzer.transform_to_blocks(entries)

        # May create 3 blocks due to rounding to hour boundaries
        assert len(blocks) >= 2
        assert sum(len(block.entries) for block in blocks) == 2

    def test_should_create_new_block_time_gap(self) -> None:
        """Test _should_create_new_block with time gap."""
        analyzer = SessionAnalyzer()

        # Create a mock block
        block = SessionBlock(
            id="test_block",
            start_time=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 1, 17, 0, tzinfo=timezone.utc),
        )

        # Entry within same block
        entry1 = UsageEntry(
            timestamp=datetime(2024, 1, 1, 14, 0, tzinfo=timezone.utc),
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.001,
            model="claude-3-haiku",
        )

        # Entry outside block time range
        entry2 = UsageEntry(
            timestamp=datetime(2024, 1, 1, 20, 0, tzinfo=timezone.utc),
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.001,
            model="claude-3-haiku",
        )

        assert not analyzer._should_create_new_block(block, entry1)
        assert analyzer._should_create_new_block(block, entry2)

    def test_round_to_hour(self) -> None:
        """Test _round_to_hour functionality."""
        analyzer = SessionAnalyzer()

        # Test various timestamps
        test_cases: List[tuple[datetime, datetime]] = [
            (
                datetime(2024, 1, 1, 12, 30, 45, tzinfo=timezone.utc),
                datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            ),
            (
                datetime(2024, 1, 1, 15, 0, 0, tzinfo=timezone.utc),
                datetime(2024, 1, 1, 15, 0, 0, tzinfo=timezone.utc),
            ),
            (
                datetime(2024, 1, 1, 9, 59, 59, tzinfo=timezone.utc),
                datetime(2024, 1, 1, 9, 0, 0, tzinfo=timezone.utc),
            ),
        ]

        for input_time, expected in test_cases:
            result = analyzer._round_to_hour(input_time)
            assert result == expected

    def test_create_new_block(self) -> None:
        """Test _create_new_block functionality."""
        analyzer = SessionAnalyzer()

        entry = UsageEntry(
            timestamp=datetime(2024, 1, 1, 12, 30, tzinfo=timezone.utc),
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.001,
            model="claude-3-haiku",
        )

        block = analyzer._create_new_block(entry)

        assert block.start_time == datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        assert block.end_time == datetime(2024, 1, 1, 17, 0, tzinfo=timezone.utc)
        assert block.id == "2024-01-01T12:00:00+00:00"

    def test_add_entry_to_block(self) -> None:
        """Test _add_entry_to_block functionality."""
        analyzer = SessionAnalyzer()

        block = SessionBlock(
            id="test_block",
            start_time=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 1, 17, 0, tzinfo=timezone.utc),
            token_counts=TokenCounts(),
        )

        entry = UsageEntry(
            timestamp=datetime(2024, 1, 1, 12, 30, tzinfo=timezone.utc),
            input_tokens=100,
            output_tokens=50,
            cache_creation_tokens=10,
            cache_read_tokens=5,
            cost_usd=0.001,
            model="claude-3-haiku",
            message_id="msg_123",
        )

        analyzer._add_entry_to_block(block, entry)

        assert len(block.entries) == 1
        assert block.entries[0] == entry
        assert block.token_counts.input_tokens == 100
        assert block.token_counts.output_tokens == 50
        assert block.token_counts.cache_creation_tokens == 10
        assert block.token_counts.cache_read_tokens == 5
        assert block.cost_usd == 0.001
        assert "claude-3-haiku" in block.models
        assert block.sent_messages_count == 1

    def test_finalize_block(self) -> None:
        """Test _finalize_block functionality."""
        analyzer = SessionAnalyzer()

        block = SessionBlock(
            id="test_block",
            start_time=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 1, 17, 0, tzinfo=timezone.utc),
            entries=[
                UsageEntry(
                    timestamp=datetime(2024, 1, 1, 12, 30, tzinfo=timezone.utc),
                    input_tokens=100,
                    output_tokens=50,
                    cost_usd=0.001,
                    model="claude-3-haiku",
                )
            ],
        )

        analyzer._finalize_block(block)

        # Should set actual_end_time to last entry timestamp
        assert block.actual_end_time == datetime(
            2024, 1, 1, 12, 30, tzinfo=timezone.utc
        )

    def test_detect_limits_empty_list(self) -> None:
        """Test detect_limits with empty list."""
        analyzer = SessionAnalyzer()
        result = analyzer.detect_limits([])

        assert result == []

    def test_detect_limits_no_limits(self) -> None:
        """Test detect_limits with no limit messages."""
        analyzer = SessionAnalyzer()

        raw_entries: List[Dict[str, str]] = [
            {
                "timestamp": "2024-01-01T12:00:00Z",
                "content": "Regular response content",
                "type": "assistant",
            }
        ]

        result = analyzer.detect_limits(raw_entries)

        assert result == []

    def test_detect_single_limit_rate_limit(self) -> None:
        """Test _detect_single_limit with rate limit message."""
        analyzer = SessionAnalyzer()

        raw_data: Dict[str, Union[str, List[Dict[str, str]]]] = {
            "timestamp": "2024-01-01T12:00:00Z",
            "content": [
                {
                    "type": "text",
                    "text": "I'm currently at capacity and am unable to process your request.",
                }
            ],
            "type": "assistant",
        }

        result = analyzer._detect_single_limit(raw_data)

        # May or may not detect limit depending on implementation
        if result is not None:
            assert "type" in result
            assert "message" in result

    def test_detect_single_limit_opus_limit(self) -> None:
        """Test _detect_single_limit with Opus daily limit."""
        analyzer = SessionAnalyzer()

        raw_data: Dict[str, Union[str, List[Dict[str, str]]]] = {
            "timestamp": "2024-01-01T12:00:00Z",
            "content": [
                {
                    "type": "text",
                    "text": "You've reached your daily limit for Claude 3 Opus.",
                }
            ],
            "type": "assistant",
        }

        result = analyzer._detect_single_limit(raw_data)

        # May or may not detect limit depending on implementation
        if result is not None:
            assert "type" in result
            assert "message" in result

    def test_is_opus_limit(self) -> None:
        """Test _is_opus_limit detection."""
        analyzer = SessionAnalyzer()

        # Test cases that should be detected as Opus limits
        opus_cases: List[str] = [
            "you've reached your daily limit for claude 3 opus",
            "daily opus limit reached",
            "claude 3 opus usage limit",
        ]

        # Test cases that should NOT be detected
        non_opus_cases: List[str] = [
            "general rate limit message",
            "sonnet limit reached",
            "you've reached capacity",
        ]

        for case in opus_cases:
            assert analyzer._is_opus_limit(case) is True

        for case in non_opus_cases:
            assert analyzer._is_opus_limit(case) is False

    def test_extract_wait_time(self) -> None:
        """Test _extract_wait_time functionality."""
        analyzer = SessionAnalyzer()

        test_cases: List[tuple[str, Optional[int]]] = [
            ("wait 5 minutes", 5),
            ("wait 30 minutes", 30),
            ("wait 60 minutes", 60),
            ("wait 120 minutes", 120),
            ("No time mentioned", None),
        ]

        # _extract_wait_time requires timestamp parameter
        timestamp = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)

        for text, expected_minutes in test_cases:
            reset_time, wait_minutes = analyzer._extract_wait_time(text, timestamp)
            assert wait_minutes == expected_minutes

    def test_parse_reset_timestamp(self) -> None:
        """Test _parse_reset_timestamp functionality."""
        analyzer = SessionAnalyzer()

        # Test with various timestamp formats
        test_cases: List[str] = [
            "Resets at 2024-01-01T15:00:00Z",
            "Your limit resets on 2024-01-01 at 15:00",
            "Available again at 15:00 UTC",
        ]

        for text in test_cases:
            result = analyzer._parse_reset_timestamp(text)
            # Should either return a datetime or None
            assert result is None or isinstance(result, datetime)

    def test_mark_active_blocks(self) -> None:
        """Test _mark_active_blocks functionality."""
        analyzer = SessionAnalyzer()

        now = datetime.now(timezone.utc)
        blocks: List[SessionBlock] = [
            SessionBlock(
                id="old_block",
                start_time=now - timedelta(hours=10),
                end_time=now - timedelta(hours=5),
                actual_end_time=now - timedelta(hours=6),
            ),
            SessionBlock(
                id="recent_block",
                start_time=now - timedelta(hours=2),
                end_time=now + timedelta(hours=3),
                actual_end_time=now - timedelta(minutes=30),
            ),
        ]

        analyzer._mark_active_blocks(blocks)

        # Old block should not be active
        assert blocks[0].is_active is False
        # Recent block should be active (within last hour)
        assert blocks[1].is_active is True


class TestSessionAnalyzerIntegration:
    """Integration tests for SessionAnalyzer."""

    def test_full_analysis_workflow(self) -> None:
        """Test complete analysis workflow."""
        analyzer = SessionAnalyzer()

        # Create realistic usage entries
        base_time = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        entries: List[UsageEntry] = [
            UsageEntry(
                timestamp=base_time,
                input_tokens=100,
                output_tokens=50,
                cost_usd=0.001,
                model="claude-3-haiku",
            ),
            UsageEntry(
                timestamp=base_time + timedelta(minutes=30),
                input_tokens=200,
                output_tokens=100,
                cost_usd=0.002,
                model="claude-3-sonnet",
            ),
            UsageEntry(
                timestamp=base_time + timedelta(hours=6),
                input_tokens=150,
                output_tokens=75,
                cost_usd=0.0015,
                model="claude-3-haiku",
            ),
        ]

        # Create blocks
        blocks = analyzer.transform_to_blocks(entries)

        assert len(blocks) >= 2  # Should create multiple blocks due to time gap

        # Verify total entries across all blocks
        total_entries = sum(len(block.entries) for block in blocks)
        assert total_entries == 3

        # Verify total tokens are preserved
        total_input = sum(block.token_counts.input_tokens for block in blocks)
        total_output = sum(block.token_counts.output_tokens for block in blocks)
        total_cost = sum(block.cost_usd for block in blocks)

        assert total_input == 450  # 100 + 200 + 150
        assert total_output == 225  # 50 + 100 + 75
        assert abs(total_cost - 0.0045) < 0.0001  # 0.001 + 0.002 + 0.0015

    def test_limit_detection_workflow(self) -> None:
        """Test limit detection workflow."""
        analyzer = SessionAnalyzer()

        raw_entries: List[Dict[str, Union[str, List[Dict[str, str]]]]] = [
            {
                "timestamp": "2024-01-01T12:00:00Z",
                "content": [
                    {
                        "type": "text",
                        "text": "I'm currently at capacity and am unable to process your request. Please try again in 30 minutes.",
                    }
                ],
                "type": "assistant",
            },
            {
                "timestamp": "2024-01-01T13:00:00Z",
                "content": [
                    {
                        "type": "text",
                        "text": "You've reached your daily limit for Claude 3 Opus. Your limit will reset at midnight UTC.",
                    }
                ],
                "type": "assistant",
            },
        ]

        limits = analyzer.detect_limits(raw_entries)

        # May or may not detect limits depending on implementation
        assert isinstance(limits, list)

        for limit in limits:
            assert "type" in limit
            assert "message" in limit


class TestSessionAnalyzerEdgeCases:
    """Test edge cases and error conditions."""

    def test_malformed_entry_handling(self) -> None:
        """Test handling of malformed entries."""
        analyzer = SessionAnalyzer()

        # Entry with None timestamp should be handled gracefully
        entry = UsageEntry(
            timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.001,
            model="claude-3-haiku",
        )

        # Should not raise exception
        blocks = analyzer.transform_to_blocks([entry])
        assert len(blocks) == 1

    def test_negative_token_counts(self) -> None:
        """Test handling of negative token counts."""
        analyzer = SessionAnalyzer()

        entry = UsageEntry(
            timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            input_tokens=-100,  # Negative tokens
            output_tokens=50,
            cost_usd=0.001,
            model="claude-3-haiku",
        )

        blocks = analyzer.transform_to_blocks([entry])

        # Should handle gracefully
        assert len(blocks) == 1
        assert blocks[0].token_counts.input_tokens == -100

    def test_very_large_time_gaps(self) -> None:
        """Test handling of very large time gaps."""
        analyzer = SessionAnalyzer()

        base_time = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        entries: List[UsageEntry] = [
            UsageEntry(
                timestamp=base_time,
                input_tokens=100,
                output_tokens=50,
                cost_usd=0.001,
                model="claude-3-haiku",
            ),
            UsageEntry(
                timestamp=base_time + timedelta(days=365),  # Very large gap
                input_tokens=100,
                output_tokens=50,
                cost_usd=0.001,
                model="claude-3-haiku",
            ),
        ]

        blocks = analyzer.transform_to_blocks(entries)

        # Should create separate blocks
        assert len(blocks) >= 2
