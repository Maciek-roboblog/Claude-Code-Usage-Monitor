"""Tests for data/analysis.py module."""

from datetime import datetime, timezone
from unittest.mock import Mock, patch

from claude_monitor.core.models import (
    BurnRate,
    CostMode,
    SessionBlock,
    TokenCounts,
    UsageEntry,
    UsageProjection,
)
from claude_monitor.data.analysis import (
    _add_optional_block_data,
    _convert_blocks_to_dict_format,
    _create_base_block_dict,
    _create_result,
    _format_block_entries,
    _format_limit_info,
    _is_limit_in_block_timerange,
    _process_burn_rates,
    analyze_usage,
)


class TestAnalyzeUsage:
    """Test the main analyze_usage function."""

    @patch("claude_monitor.data.analysis.load_usage_entries")
    @patch("claude_monitor.data.analysis.SessionAnalyzer")
    @patch("claude_monitor.data.analysis.BurnRateCalculator")
    def test_analyze_usage_basic(
        self, mock_calc_class: Mock, mock_analyzer_class: Mock, mock_load: Mock
    ) -> None:
        """Test basic analyze_usage functionality."""
        sample_entry = UsageEntry(
            timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.001,
            model="claude-3-haiku",
        )

        sample_block = SessionBlock(
            id="block_1",
            start_time=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 1, 17, 0, tzinfo=timezone.utc),
            token_counts=TokenCounts(input_tokens=100, output_tokens=50),
            cost_usd=0.001,
            entries=[sample_entry],
        )

        mock_load.return_value = ([sample_entry], [{"raw": "data"}])

        mock_analyzer = Mock()
        mock_analyzer.transform_to_blocks.return_value = [sample_block]
        mock_analyzer.detect_limits.return_value = []
        mock_analyzer_class.return_value = mock_analyzer

        mock_calculator = Mock()
        mock_calc_class.return_value = mock_calculator
        result = analyze_usage(hours_back=24, use_cache=True)
        assert "blocks" in result
        assert "metadata" in result
        assert "entries_count" in result
        assert "total_tokens" in result
        assert "total_cost" in result

        assert result["entries_count"] == 1
        assert result["total_tokens"] == 150
        assert result["total_cost"] == 0.001
        mock_load.assert_called_once()
        mock_analyzer.transform_to_blocks.assert_called_once_with([sample_entry])
        mock_analyzer.detect_limits.assert_called_once_with([{"raw": "data"}])

    @patch("claude_monitor.data.analysis.load_usage_entries")
    @patch("claude_monitor.data.analysis.SessionAnalyzer")
    @patch("claude_monitor.data.analysis.BurnRateCalculator")
    def test_analyze_usage_quick_start_no_hours(
        self, mock_calc_class: Mock, mock_analyzer_class: Mock, mock_load: Mock
    ) -> None:
        """Test analyze_usage with quick_start=True and hours_back=None."""
        mock_load.return_value = ([], [])
        mock_analyzer = Mock()
        mock_analyzer.transform_to_blocks.return_value = []
        mock_analyzer.detect_limits.return_value = []
        mock_analyzer_class.return_value = mock_analyzer
        mock_calc_class.return_value = Mock()

        result = analyze_usage(quick_start=True, hours_back=None)
        mock_load.assert_called_once_with(
            data_path=None, hours_back=24, mode=CostMode.AUTO, include_raw=True
        )

        assert result["metadata"]["quick_start"] is True
        assert result["metadata"]["hours_analyzed"] == 24

    @patch("claude_monitor.data.analysis.load_usage_entries")
    @patch("claude_monitor.data.analysis.SessionAnalyzer")
    @patch("claude_monitor.data.analysis.BurnRateCalculator")
    def test_analyze_usage_quick_start_with_hours(
        self, mock_calc_class: Mock, mock_analyzer_class: Mock, mock_load: Mock
    ) -> None:
        """Test analyze_usage with quick_start=True and specific hours_back."""
        mock_load.return_value = ([], [])
        mock_analyzer = Mock()
        mock_analyzer.transform_to_blocks.return_value = []
        mock_analyzer.detect_limits.return_value = []
        mock_analyzer_class.return_value = mock_analyzer
        mock_calc_class.return_value = Mock()

        result = analyze_usage(quick_start=True, hours_back=48)
        mock_load.assert_called_once_with(
            data_path=None, hours_back=48, mode=CostMode.AUTO, include_raw=True
        )

        assert result["metadata"]["quick_start"] is True
        assert result["metadata"]["hours_analyzed"] == 48

    @patch("claude_monitor.data.analysis.load_usage_entries")
    @patch("claude_monitor.data.analysis.SessionAnalyzer")
    @patch("claude_monitor.data.analysis.BurnRateCalculator")
    def test_analyze_usage_with_limits(
        self, mock_calc_class: Mock, mock_analyzer_class: Mock, mock_load: Mock
    ) -> None:
        """Test analyze_usage with limit detection."""
        sample_entry = UsageEntry(
            timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.001,
            model="claude-3-haiku",
        )

        sample_block = SessionBlock(
            id="block_1",
            start_time=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 1, 17, 0, tzinfo=timezone.utc),
            token_counts=TokenCounts(input_tokens=100, output_tokens=50),
            cost_usd=0.001,
            entries=[sample_entry],
        )

        limit_info = {
            "type": "rate_limit",
            "timestamp": datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc),
            "content": "Rate limit exceeded",
            "reset_time": datetime(2024, 1, 1, 14, 0, tzinfo=timezone.utc),
        }

        mock_load.return_value = ([sample_entry], [{"raw": "data"}])

        mock_analyzer = Mock()
        mock_analyzer.transform_to_blocks.return_value = [sample_block]
        mock_analyzer.detect_limits.return_value = [limit_info]
        mock_analyzer_class.return_value = mock_analyzer

        mock_calc_class.return_value = Mock()

        result = analyze_usage()

        assert result["metadata"]["limits_detected"] == 1
        assert hasattr(sample_block, "limit_messages")

    @patch("claude_monitor.data.analysis.load_usage_entries")
    @patch("claude_monitor.data.analysis.SessionAnalyzer")
    @patch("claude_monitor.data.analysis.BurnRateCalculator")
    def test_analyze_usage_no_raw_entries(
        self, mock_calc_class: Mock, mock_analyzer_class: Mock, mock_load: Mock
    ) -> None:
        """Test analyze_usage when no raw entries are provided."""
        sample_entry = UsageEntry(
            timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.001,
            model="claude-3-haiku",
        )

        sample_block = SessionBlock(
            id="block_1",
            start_time=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 1, 17, 0, tzinfo=timezone.utc),
            token_counts=TokenCounts(input_tokens=100, output_tokens=50),
            cost_usd=0.001,
            entries=[sample_entry],
        )

        mock_load.return_value = ([sample_entry], None)

        mock_analyzer = Mock()
        mock_analyzer.transform_to_blocks.return_value = [sample_block]
        mock_analyzer_class.return_value = mock_analyzer

        mock_calc_class.return_value = Mock()

        result = analyze_usage()

        assert result["metadata"]["limits_detected"] == 0
        mock_analyzer.detect_limits.assert_not_called()


class TestProcessBurnRates:
    """Test the _process_burn_rates function."""

    def test_process_burn_rates_active_block(self) -> None:
        """Test burn rate processing for active blocks."""
        active_block = SessionBlock(
            id="active_block",
            start_time=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 1, 17, 0, tzinfo=timezone.utc),
            is_active=True,
            token_counts=TokenCounts(input_tokens=100, output_tokens=50),
            cost_usd=0.001,
        )
        inactive_block = SessionBlock(
            id="inactive_block",
            start_time=datetime(2024, 1, 1, 8, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc),
            is_active=False,
            token_counts=TokenCounts(input_tokens=200, output_tokens=100),
            cost_usd=0.002,
        )

        blocks = [active_block, inactive_block]
        calculator = Mock()
        burn_rate = BurnRate(tokens_per_minute=5.0, cost_per_hour=1.0)
        projection = UsageProjection(
            projected_total_tokens=500, projected_total_cost=0.005, remaining_minutes=60
        )

        calculator.calculate_burn_rate.return_value = burn_rate
        calculator.project_block_usage.return_value = projection
        _process_burn_rates(blocks, calculator)
        calculator.calculate_burn_rate.assert_called_once_with(active_block)
        calculator.project_block_usage.assert_called_once_with(active_block)
        assert hasattr(active_block, "burn_rate_snapshot")
        assert active_block.burn_rate_snapshot == burn_rate
        assert hasattr(active_block, "projection_data")
        assert active_block.projection_data == {
            "totalTokens": 500,
            "totalCost": 0.005,
            "remainingMinutes": 60,
        }
        assert inactive_block.burn_rate_snapshot is None

    def test_process_burn_rates_no_burn_rate(self) -> None:
        """Test burn rate processing when calculator returns None."""
        active_block = SessionBlock(
            id="active_block",
            start_time=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 1, 17, 0, tzinfo=timezone.utc),
            is_active=True,
            token_counts=TokenCounts(input_tokens=0, output_tokens=0),  # No tokens
            cost_usd=0.0,
        )

        calculator = Mock()
        calculator.calculate_burn_rate.return_value = None

        _process_burn_rates([active_block], calculator)
        assert active_block.burn_rate_snapshot is None
        assert active_block.projection_data is None

    def test_process_burn_rates_no_projection(self) -> None:
        """Test burn rate processing when projection returns None."""
        active_block = SessionBlock(
            id="active_block",
            start_time=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 1, 17, 0, tzinfo=timezone.utc),
            is_active=True,
            token_counts=TokenCounts(input_tokens=100, output_tokens=50),
            cost_usd=0.001,
        )

        calculator = Mock()
        burn_rate = BurnRate(tokens_per_minute=5.0, cost_per_hour=1.0)
        calculator.calculate_burn_rate.return_value = burn_rate
        calculator.project_block_usage.return_value = None

        _process_burn_rates([active_block], calculator)
        assert active_block.burn_rate_snapshot == burn_rate
        assert active_block.projection_data is None


class TestCreateResult:
    """Test the _create_result function."""

    @patch("claude_monitor.data.analysis._convert_blocks_to_dict_format")
    def test_create_result_basic(self, mock_convert: Mock) -> None:
        """Test basic _create_result functionality."""
        # Create test blocks
        block1 = Mock()
        block1.total_tokens = 100
        block1.cost_usd = 0.001

        block2 = Mock()
        block2.total_tokens = 200
        block2.cost_usd = 0.002

        blocks = [block1, block2]
        entries = [Mock(), Mock(), Mock()]
        metadata = {"test": "metadata"}

        mock_convert.return_value = [{"block": "data1"}, {"block": "data2"}]

        result = _create_result(blocks, entries, metadata)

        assert result == {
            "blocks": [{"block": "data1"}, {"block": "data2"}],
            "metadata": {"test": "metadata"},
            "entries_count": 3,
            "total_tokens": 300,
            "total_cost": 0.003,
        }

        mock_convert.assert_called_once_with(blocks)

    def test_create_result_empty(self) -> None:
        """Test _create_result with empty data."""
        result = _create_result([], [], {})

        assert result == {
            "blocks": [],
            "metadata": {},
            "entries_count": 0,
            "total_tokens": 0,
            "total_cost": 0,
        }


class TestLimitFunctions:
    """Test limit-related functions."""

    def test_is_limit_in_block_timerange_within_range(self) -> None:
        """Test _is_limit_in_block_timerange when limit is within block."""
        block = SessionBlock(
            id="test_block",
            start_time=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 1, 17, 0, tzinfo=timezone.utc),
        )

        limit_info = {"timestamp": datetime(2024, 1, 1, 14, 0, tzinfo=timezone.utc)}

        assert _is_limit_in_block_timerange(limit_info, block) is True

    def test_is_limit_in_block_timerange_outside_range(self) -> None:
        """Test _is_limit_in_block_timerange when limit is outside block."""
        block = SessionBlock(
            id="test_block",
            start_time=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 1, 17, 0, tzinfo=timezone.utc),
        )

        limit_info = {"timestamp": datetime(2024, 1, 1, 18, 0, tzinfo=timezone.utc)}

        assert _is_limit_in_block_timerange(limit_info, block) is False

    def test_is_limit_in_block_timerange_no_timezone(self) -> None:
        """Test _is_limit_in_block_timerange with naive datetime."""
        block = SessionBlock(
            id="test_block",
            start_time=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 1, 17, 0, tzinfo=timezone.utc),
        )

        limit_info = {"timestamp": datetime(2024, 1, 1, 14, 0)}

        assert _is_limit_in_block_timerange(limit_info, block) is True

    def test_format_limit_info_complete(self) -> None:
        """Test _format_limit_info with all fields."""
        limit_info = {
            "type": "rate_limit",
            "timestamp": datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            "content": "Rate limit exceeded",
            "reset_time": datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc),
        }

        result = _format_limit_info(limit_info)

        assert result == {
            "type": "rate_limit",
            "timestamp": "2024-01-01T12:00:00+00:00",
            "content": "Rate limit exceeded",
            "reset_time": "2024-01-01T13:00:00+00:00",
        }

    def test_format_limit_info_no_reset_time(self) -> None:
        """Test _format_limit_info without reset_time."""
        limit_info = {
            "type": "general_limit",
            "timestamp": datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            "content": "Limit reached",
        }

        result = _format_limit_info(limit_info)

        assert result == {
            "type": "general_limit",
            "timestamp": "2024-01-01T12:00:00+00:00",
            "content": "Limit reached",
            "reset_time": None,
        }


class TestBlockConversion:
    """Test block conversion functions."""

    def test_format_block_entries(self) -> None:
        """Test _format_block_entries function."""
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
            timestamp=datetime(2024, 1, 1, 12, 30, tzinfo=timezone.utc),
            input_tokens=200,
            output_tokens=100,
            cache_creation_tokens=0,
            cache_read_tokens=0,
            cost_usd=0.002,
            model="claude-3-sonnet",
            message_id="msg_2",
            request_id="req_2",
        )

        result = _format_block_entries([entry1, entry2])

        assert len(result) == 2
        assert result[0] == {
            "timestamp": "2024-01-01T12:00:00+00:00",
            "inputTokens": 100,
            "outputTokens": 50,
            "cacheCreationTokens": 10,
            "cacheReadInputTokens": 5,
            "costUSD": 0.001,
            "model": "claude-3-haiku",
            "messageId": "msg_1",
            "requestId": "req_1",
        }

    def test_create_base_block_dict(self) -> None:
        """Test _create_base_block_dict function."""
        entry = UsageEntry(
            timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.001,
            model="claude-3-haiku",
        )

        block = SessionBlock(
            id="test_block",
            start_time=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 1, 17, 0, tzinfo=timezone.utc),
            actual_end_time=datetime(2024, 1, 1, 12, 30, tzinfo=timezone.utc),
            is_active=True,
            is_gap=False,
            token_counts=TokenCounts(
                input_tokens=100,
                output_tokens=50,
                cache_creation_tokens=10,
                cache_read_tokens=5,
            ),
            cost_usd=0.001,
            models=["claude-3-haiku"],
            per_model_stats={"claude-3-haiku": {"input_tokens": 100}},
            sent_messages_count=1,
            entries=[entry],
        )

        result = _create_base_block_dict(block)

        expected_keys = [
            "id",
            "isActive",
            "isGap",
            "startTime",
            "endTime",
            "actualEndTime",
            "tokenCounts",
            "totalTokens",
            "costUSD",
            "models",
            "perModelStats",
            "sentMessagesCount",
            "durationMinutes",
            "entries",
            "entries_count",
        ]

        for key in expected_keys:
            assert key in result

        assert result["id"] == "test_block"
        assert result["isActive"] is True
        assert result["isGap"] is False
        assert result["totalTokens"] == 150
        assert result["entries_count"] == 1

    def test_add_optional_block_data_all_fields(self) -> None:
        """Test _add_optional_block_data with all optional fields."""
        block = Mock()
        block.burn_rate_snapshot = BurnRate(tokens_per_minute=5.0, cost_per_hour=1.0)
        block.projection_data = {
            "totalTokens": 500,
            "totalCost": 0.005,
            "remainingMinutes": 60,
        }
        block.limit_messages = [{"type": "rate_limit", "content": "Limit reached"}]

        block_dict = {}
        _add_optional_block_data(block, block_dict)

        assert "burnRate" in block_dict
        assert block_dict["burnRate"] == {"tokensPerMinute": 5.0, "costPerHour": 1.0}

        assert "projection" in block_dict
        assert block_dict["projection"] == {
            "totalTokens": 500,
            "totalCost": 0.005,
            "remainingMinutes": 60,
        }

        assert "limitMessages" in block_dict
        assert block_dict["limitMessages"] == [
            {"type": "rate_limit", "content": "Limit reached"}
        ]

    def test_add_optional_block_data_no_fields(self) -> None:
        """Test _add_optional_block_data with no optional fields."""
        block = Mock()
        # Remove all optional attributes
        if hasattr(block, "burn_rate_snapshot"):
            del block.burn_rate_snapshot
        if hasattr(block, "projection_data"):
            del block.projection_data
        if hasattr(block, "limit_messages"):
            del block.limit_messages

        block_dict = {}
        _add_optional_block_data(block, block_dict)

        assert "burnRate" not in block_dict
        assert "projection" not in block_dict
        assert "limitMessages" not in block_dict

    @patch("claude_monitor.data.analysis._create_base_block_dict")
    @patch("claude_monitor.data.analysis._add_optional_block_data")
    def test_convert_blocks_to_dict_format(
        self, mock_add_optional: Mock, mock_create_base: Mock
    ) -> None:
        """Test _convert_blocks_to_dict_format function."""
        block1 = Mock()
        block2 = Mock()
        blocks = [block1, block2]

        mock_create_base.side_effect = [{"base": "block1"}, {"base": "block2"}]

        result = _convert_blocks_to_dict_format(blocks)

        assert len(result) == 2
        assert result == [{"base": "block1"}, {"base": "block2"}]

        assert mock_create_base.call_count == 2
        assert mock_add_optional.call_count == 2

        mock_create_base.assert_any_call(block1)
        mock_create_base.assert_any_call(block2)
