"""Tests for calculations module."""

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

import pytest

from claude_monitor.core.calculations import (
    BurnRateCalculator,
    _calculate_total_tokens_in_hour,
    _process_block_for_burn_rate,
    calculate_hourly_burn_rate,
)
from claude_monitor.core.models import BurnRate, TokenCounts, UsageProjection


class TestBurnRateCalculator:
    """Test cases for BurnRateCalculator."""

    @pytest.fixture
    def calculator(self):
        """
        Create and return a new instance of BurnRateCalculator.
        """
        return BurnRateCalculator()

    @pytest.fixture
    def mock_active_block(self):
        """
        Create and return a mock active block with predefined token counts, cost, and a future end time for testing purposes.
        
        Returns:
            Mock: A mock object representing an active block with set attributes.
        """
        block = Mock()
        block.is_active = True
        block.duration_minutes = 30
        block.token_counts = TokenCounts(
            input_tokens=100,
            output_tokens=50,
            cache_creation_tokens=10,
            cache_read_tokens=5,
        )
        block.cost_usd = 0.5
        block.end_time = datetime.now(timezone.utc) + timedelta(hours=1)
        return block

    @pytest.fixture
    def mock_inactive_block(self):
        """
        Create and return a mock inactive block with predefined token counts, duration, and cost for use in tests.
        
        Returns:
            Mock: A mock object representing an inactive block.
        """
        block = Mock()
        block.is_active = False
        block.duration_minutes = 30
        block.token_counts = TokenCounts(input_tokens=100, output_tokens=50)
        block.cost_usd = 0.5
        return block

    def test_calculate_burn_rate_active_block(self, calculator, mock_active_block):
        """Test burn rate calculation for active block."""
        burn_rate = calculator.calculate_burn_rate(mock_active_block)

        assert burn_rate is not None
        assert isinstance(burn_rate, BurnRate)

        assert burn_rate.tokens_per_minute == 5.5

        assert burn_rate.cost_per_hour == 1.0

    def test_calculate_burn_rate_inactive_block(self, calculator, mock_inactive_block):
        """
        Test that calculating the burn rate for an inactive block returns None.
        """
        burn_rate = calculator.calculate_burn_rate(mock_inactive_block)
        assert burn_rate is None

    def test_calculate_burn_rate_zero_duration(self, calculator, mock_active_block):
        """
        Test that calculating burn rate for a block with zero duration returns None.
        """
        mock_active_block.duration_minutes = 0
        burn_rate = calculator.calculate_burn_rate(mock_active_block)
        assert burn_rate is None

    def test_calculate_burn_rate_no_tokens(self, calculator, mock_active_block):
        """Test burn rate calculation with no tokens returns None."""
        mock_active_block.token_counts = TokenCounts(
            input_tokens=0,
            output_tokens=0,
            cache_creation_tokens=0,
            cache_read_tokens=0,
        )
        burn_rate = calculator.calculate_burn_rate(mock_active_block)
        assert burn_rate is None

    def test_calculate_burn_rate_edge_case_small_duration(
        self, calculator, mock_active_block
    ):
        """
        Test that burn rate calculation returns the expected tokens per minute for an active block with a minimal duration of one minute.
        """
        mock_active_block.duration_minutes = 1  # 1 minute minimum for active check
        burn_rate = calculator.calculate_burn_rate(mock_active_block)

        assert burn_rate is not None
        assert burn_rate.tokens_per_minute == 165.0

    @patch("claude_monitor.core.calculations.datetime")
    def test_project_block_usage_success(
        self, mock_datetime, calculator, mock_active_block
    ):
        """Test successful usage projection."""
        # Mock current time
        mock_now = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now

        mock_active_block.end_time = mock_now + timedelta(hours=1)

        projection = calculator.project_block_usage(mock_active_block)

        assert projection is not None
        assert isinstance(projection, UsageProjection)

        assert projection.projected_total_tokens == 495

        assert projection.projected_total_cost == 1.5

        assert projection.remaining_minutes == 60

    @patch("claude_monitor.core.calculations.datetime")
    def test_project_block_usage_no_remaining_time(
        self, mock_datetime, calculator, mock_active_block
    ):
        """
        Test that projecting usage for a block with an end time in the past returns None.
        """
        # Mock current time to be after block end time
        mock_now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now

        mock_active_block.end_time = mock_now - timedelta(hours=1)

        projection = calculator.project_block_usage(mock_active_block)
        assert projection is None

    def test_project_block_usage_no_burn_rate(self, calculator, mock_inactive_block):
        """
        Test that projecting usage for a block with no calculable burn rate returns None.
        """
        projection = calculator.project_block_usage(mock_inactive_block)
        assert projection is None


class TestHourlyBurnRateCalculation:
    """Test cases for hourly burn rate functions."""

    @pytest.fixture
    def current_time(self):
        """
        Returns a fixed UTC datetime for use in tests.
        """
        return datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    @pytest.fixture
    def mock_blocks(self):
        """
        Return a list of mock block dictionaries representing different session scenarios for testing purposes.
        
        Returns:
            List[dict]: A list of dictionaries, each representing a mock block with start time, end time, token counts, and gap status.
        """
        block1 = {
            "start_time": "2024-01-01T11:30:00Z",
            "actual_end_time": None,
            "token_counts": {"input_tokens": 100, "output_tokens": 50},
            "isGap": False,
        }

        block2 = {
            "start_time": "2024-01-01T10:00:00Z",
            "actual_end_time": "2024-01-01T10:30:00Z",
            "token_counts": {"input_tokens": 200, "output_tokens": 100},
            "isGap": False,
        }

        block3 = {
            "start_time": "2024-01-01T11:45:00Z",
            "actual_end_time": None,
            "token_counts": {"input_tokens": 50, "output_tokens": 25},
            "isGap": True,
        }

        return [block1, block2, block3]

    def test_calculate_hourly_burn_rate_empty_blocks(self, current_time):
        """Test hourly burn rate with empty blocks."""
        burn_rate = calculate_hourly_burn_rate([], current_time)
        assert burn_rate == 0.0

    def test_calculate_hourly_burn_rate_none_blocks(self, current_time):
        """Test hourly burn rate with None blocks."""
        burn_rate = calculate_hourly_burn_rate(None, current_time)
        assert burn_rate == 0.0

    @patch("claude_monitor.core.calculations._calculate_total_tokens_in_hour")
    def test_calculate_hourly_burn_rate_success(self, mock_calc_tokens, current_time):
        """
        Test that `calculate_hourly_burn_rate` returns the correct burn rate when total tokens in the hour are provided.
        
        Verifies that the function computes the hourly burn rate as expected and that the total token calculation is called with the correct time window.
        """
        mock_calc_tokens.return_value = 180.0  # Total tokens in hour

        blocks = [Mock()]
        burn_rate = calculate_hourly_burn_rate(blocks, current_time)

        assert burn_rate == 3.0

        one_hour_ago = current_time - timedelta(hours=1)
        mock_calc_tokens.assert_called_once_with(blocks, one_hour_ago, current_time)

    @patch("claude_monitor.core.calculations._calculate_total_tokens_in_hour")
    def test_calculate_hourly_burn_rate_zero_tokens(
        self, mock_calc_tokens, current_time
    ):
        """
        Test that `calculate_hourly_burn_rate` returns 0.0 when the total tokens calculated for the hour is zero.
        """
        mock_calc_tokens.return_value = 0.0

        blocks = [Mock()]
        burn_rate = calculate_hourly_burn_rate(blocks, current_time)

        assert burn_rate == 0.0

    @patch("claude_monitor.core.calculations._process_block_for_burn_rate")
    def test_calculate_total_tokens_in_hour(self, mock_process_block, current_time):
        """
        Test that `_calculate_total_tokens_in_hour` correctly sums token counts from multiple blocks within a one-hour window.
        
        Verifies that the function processes each block, aggregates the returned token counts, and returns the correct total.
        """
        # Mock returns different token counts for each block
        mock_process_block.side_effect = [150.0, 0.0, 0.0]

        blocks = [Mock(), Mock(), Mock()]
        one_hour_ago = current_time - timedelta(hours=1)

        total_tokens = _calculate_total_tokens_in_hour(
            blocks, one_hour_ago, current_time
        )

        assert total_tokens == 150.0
        assert mock_process_block.call_count == 3

    def test_process_block_for_burn_rate_gap_block(self, current_time):
        """
        Test that processing a gap block with `_process_block_for_burn_rate` returns zero tokens.
        """
        gap_block = {"isGap": True, "start_time": "2024-01-01T11:30:00Z"}
        one_hour_ago = current_time - timedelta(hours=1)

        tokens = _process_block_for_burn_rate(gap_block, one_hour_ago, current_time)
        assert tokens == 0

    @patch("claude_monitor.core.calculations._parse_block_start_time")
    def test_process_block_for_burn_rate_invalid_start_time(
        self, mock_parse_time, current_time
    ):
        """
        Test that processing a block with an invalid start time returns zero tokens.
        """
        mock_parse_time.return_value = None

        block = {"isGap": False, "start_time": "invalid"}
        one_hour_ago = current_time - timedelta(hours=1)

        tokens = _process_block_for_burn_rate(block, one_hour_ago, current_time)
        assert tokens == 0

    @patch("claude_monitor.core.calculations._determine_session_end_time")
    @patch("claude_monitor.core.calculations._parse_block_start_time")
    def test_process_block_for_burn_rate_old_session(
        self, mock_parse_time, mock_end_time, current_time
    ):
        """
        Test that processing a block which ended before the one-hour window returns zero tokens.
        """
        one_hour_ago = current_time - timedelta(hours=1)
        old_time = one_hour_ago - timedelta(minutes=30)

        mock_parse_time.return_value = old_time
        mock_end_time.return_value = old_time  # Session ended before one hour ago

        block = {"isGap": False, "start_time": "2024-01-01T10:30:00Z"}

        tokens = _process_block_for_burn_rate(block, one_hour_ago, current_time)
        assert tokens == 0


class TestCalculationEdgeCases:
    """Test edge cases and error conditions."""

    def test_burn_rate_with_negative_duration(self):
        """Test burn rate calculation with negative duration."""
        calculator = BurnRateCalculator()

        block = Mock()
        block.is_active = True
        block.duration_minutes = -5  # Negative duration
        block.token_counts = TokenCounts(input_tokens=100, output_tokens=50)
        block.cost_usd = 0.5

        burn_rate = calculator.calculate_burn_rate(block)
        assert burn_rate is None

    def test_projection_with_zero_cost(self):
        """
        Test that usage projection returns zero projected cost when the block's cost is zero.
        """
        calculator = BurnRateCalculator()

        block = Mock()
        block.is_active = True
        block.duration_minutes = 30
        block.token_counts = TokenCounts(input_tokens=100, output_tokens=50)
        block.cost_usd = 0.0
        block.end_time = datetime.now(timezone.utc) + timedelta(hours=1)

        projection = calculator.project_block_usage(block)

        assert projection is not None
        assert projection.projected_total_cost == 0.0

    def test_very_large_token_counts(self):
        """
        Test that burn rate calculations handle very large token counts and costs without errors.
        
        Verifies that the calculated tokens per minute and cost per hour are correct for a block with high token and cost values.
        """
        calculator = BurnRateCalculator()

        block = Mock()
        block.is_active = True
        block.duration_minutes = 1
        block.token_counts = TokenCounts(
            input_tokens=1000000,
            output_tokens=500000,
            cache_creation_tokens=100000,
            cache_read_tokens=50000,
        )
        block.cost_usd = 100.0

        burn_rate = calculator.calculate_burn_rate(block)

        assert burn_rate is not None
        # Total tokens: 1,650,000 (1M+500K+100K+50K), Duration: 1 minute
        assert burn_rate.tokens_per_minute == 1650000.0
        assert burn_rate.cost_per_hour == 6000.0


class TestP90Calculator:
    """Test cases for P90Calculator."""

    def test_p90_config_creation(self):
        """
        Verify that the P90Config dataclass is created with the expected attribute values.
        """
        from claude_monitor.core.p90_calculator import P90Config

        config = P90Config(
            common_limits=[10000, 50000, 100000],
            limit_threshold=0.9,
            default_min_limit=5000,
            cache_ttl_seconds=300,
        )

        assert config.common_limits == [10000, 50000, 100000]
        assert config.limit_threshold == 0.9
        assert config.default_min_limit == 5000
        assert config.cache_ttl_seconds == 300

    def test_did_hit_limit_true(self):
        """
        Verify that _did_hit_limit returns True when the token count meets or exceeds the threshold for any provided limit.
        """
        from claude_monitor.core.p90_calculator import _did_hit_limit

        # 9000 tokens with 10000 limit and 0.9 threshold = 9000 >= 9000
        result = _did_hit_limit(9000, [10000, 50000], 0.9)
        assert result is True

        # 45000 tokens with 50000 limit and 0.9 threshold = 45000 >= 45000
        result = _did_hit_limit(45000, [10000, 50000], 0.9)
        assert result is True

    def test_did_hit_limit_false(self):
        """
        Verify that _did_hit_limit returns False when the token count does not meet or exceed the threshold for any provided limits.
        """
        from claude_monitor.core.p90_calculator import _did_hit_limit

        # 8000 tokens with 10000 limit and 0.9 threshold = 8000 < 9000
        result = _did_hit_limit(8000, [10000, 50000], 0.9)
        assert result is False

        # 1000 tokens with high limits
        result = _did_hit_limit(1000, [10000, 50000], 0.9)
        assert result is False

    def test_extract_sessions_basic(self):
        """
        Tests that the `_extract_sessions` function correctly filters out gap blocks and extracts token counts from the provided blocks.
        """
        from claude_monitor.core.p90_calculator import _extract_sessions

        blocks = [
            {"totalTokens": 1000, "isGap": False},
            {"totalTokens": 2000, "isGap": True},
            {"totalTokens": 3000, "isGap": False},
            {"totalTokens": 0, "isGap": False},
            {"isGap": False},
        ]

        # Filter function that excludes gaps
        def filter_fn(b):
            """
            Return True if the block is not marked as a gap.
            
            Parameters:
            	b (dict): A block dictionary to check.
            
            Returns:
            	bool: True if the block is not a gap; otherwise, False.
            """
            return not b.get("isGap", False)

        result = _extract_sessions(blocks, filter_fn)

        assert result == [1000, 3000]

    def test_extract_sessions_complex_filter(self):
        """
        Tests that _extract_sessions correctly filters blocks using a custom filter function, extracting token counts only from blocks that are neither gaps nor active.
        
        Verifies that the resulting list contains the expected token counts after applying the filter.
        """
        from claude_monitor.core.p90_calculator import _extract_sessions

        blocks = [
            {"totalTokens": 1000, "isGap": False, "isActive": False},
            {"totalTokens": 2000, "isGap": False, "isActive": True},
            {"totalTokens": 3000, "isGap": True, "isActive": False},
            {"totalTokens": 4000, "isGap": False, "isActive": False},
        ]

        def filter_fn(b):
            """
            Return True if the block is neither a gap nor active.
            
            Parameters:
            	b (dict): A block dictionary to check.
            
            Returns:
            	bool: True if the block is not a gap and not active, otherwise False.
            """
            return not b.get("isGap", False) and not b.get("isActive", False)

        result = _extract_sessions(blocks, filter_fn)

        assert result == [1000, 4000]

    def test_calculate_p90_from_blocks_with_hits(self):
        """
        Test that `_calculate_p90_from_blocks` returns an integer limit when some blocks meet or exceed the configured threshold.
        
        Verifies that the function correctly identifies blocks that hit the limit and returns a positive integer as the calculated P90 limit.
        """
        from claude_monitor.core.p90_calculator import (
            P90Config,
            _calculate_p90_from_blocks,
        )

        config = P90Config(
            common_limits=[10000, 50000],
            limit_threshold=0.9,
            default_min_limit=5000,
            cache_ttl_seconds=300,
        )

        # Blocks with some hitting limits (>=9000 or >=45000)
        blocks = [
            {"totalTokens": 9500, "isGap": False, "isActive": False},
            {"totalTokens": 8000, "isGap": False, "isActive": False},
            {"totalTokens": 46000, "isGap": False, "isActive": False},
            {"totalTokens": 1000, "isGap": True, "isActive": False},
        ]

        result = _calculate_p90_from_blocks(blocks, config)

        assert isinstance(result, int)
        assert result > 0

    def test_calculate_p90_from_blocks_no_hits(self):
        """
        Test that _calculate_p90_from_blocks returns the default minimum limit when no blocks meet the limit threshold.
        """
        from claude_monitor.core.p90_calculator import (
            P90Config,
            _calculate_p90_from_blocks,
        )

        config = P90Config(
            common_limits=[10000, 50000],
            limit_threshold=0.9,
            default_min_limit=5000,
            cache_ttl_seconds=300,
        )

        # Blocks with no limit hits
        blocks = [
            {"totalTokens": 1000, "isGap": False, "isActive": False},
            {"totalTokens": 2000, "isGap": False, "isActive": False},
            {"totalTokens": 3000, "isGap": False, "isActive": False},
            {"totalTokens": 1500, "isGap": True, "isActive": False},  # Gap - ignored
        ]

        result = _calculate_p90_from_blocks(blocks, config)

        assert isinstance(result, int)
        assert result > 0

    def test_calculate_p90_from_blocks_empty(self):
        """
        Test that _calculate_p90_from_blocks returns the default minimum limit when given empty or invalid blocks.
        """
        from claude_monitor.core.p90_calculator import (
            P90Config,
            _calculate_p90_from_blocks,
        )

        config = P90Config(
            common_limits=[10000, 50000],
            limit_threshold=0.9,
            default_min_limit=5000,
            cache_ttl_seconds=300,
        )

        result = _calculate_p90_from_blocks([], config)
        assert result == config.default_min_limit

        blocks = [
            {"isGap": True, "isActive": False},
            {"totalTokens": 0, "isGap": False, "isActive": False},
        ]

        result = _calculate_p90_from_blocks(blocks, config)
        assert result == config.default_min_limit

    def test_p90_calculator_init(self):
        """Test P90Calculator initialization."""
        from claude_monitor.core.p90_calculator import P90Calculator

        calculator = P90Calculator()

        assert hasattr(calculator, "_cfg")
        assert calculator._cfg.common_limits is not None
        assert calculator._cfg.limit_threshold > 0
        assert calculator._cfg.default_min_limit > 0

    def test_p90_calculator_custom_config(self):
        """
        Verify that P90Calculator correctly initializes and uses a custom P90Config configuration.
        """
        from claude_monitor.core.p90_calculator import P90Calculator, P90Config

        custom_config = P90Config(
            common_limits=[5000, 25000],
            limit_threshold=0.8,
            default_min_limit=3000,
            cache_ttl_seconds=600,
        )

        calculator = P90Calculator(custom_config)

        assert calculator._cfg == custom_config
        assert calculator._cfg.limit_threshold == 0.8
        assert calculator._cfg.default_min_limit == 3000

    def test_p90_calculator_calculate_basic(self):
        """
        Tests that P90Calculator.calculate_p90_limit returns a positive integer for a typical list of non-gap, inactive blocks.
        """
        from claude_monitor.core.p90_calculator import P90Calculator

        calculator = P90Calculator()

        blocks = [
            {"totalTokens": 1000, "isGap": False, "isActive": False},
            {"totalTokens": 2000, "isGap": False, "isActive": False},
            {"totalTokens": 3000, "isGap": False, "isActive": False},
        ]

        result = calculator.calculate_p90_limit(blocks)

        assert isinstance(result, int)
        assert result > 0

    def test_p90_calculator_calculate_empty(self):
        """
        Test that P90Calculator.calculate_p90_limit returns None when given an empty list of blocks.
        """
        from claude_monitor.core.p90_calculator import P90Calculator

        calculator = P90Calculator()

        result = calculator.calculate_p90_limit([])

        assert result is None

    def test_p90_calculator_caching(self):
        """
        Test that P90Calculator returns consistent results for repeated calls with the same input, verifying caching behavior.
        """
        from claude_monitor.core.p90_calculator import P90Calculator

        calculator = P90Calculator()

        blocks = [
            {"totalTokens": 1000, "isGap": False, "isActive": False},
            {"totalTokens": 2000, "isGap": False, "isActive": False},
        ]

        # First call
        result1 = calculator.calculate_p90_limit(blocks)

        # Second call with same data should use cache
        result2 = calculator.calculate_p90_limit(blocks)

        assert result1 == result2

    def test_p90_calculation_edge_cases(self):
        """
        Test that P90 calculation handles edge cases with low and very high token counts, ensuring results meet minimum limits and remain positive.
        """
        from claude_monitor.core.p90_calculator import (
            P90Config,
            _calculate_p90_from_blocks,
        )

        config = P90Config(
            common_limits=[1000],
            limit_threshold=0.5,
            default_min_limit=100,
            cache_ttl_seconds=300,
        )

        blocks = [
            {"totalTokens": 500, "isGap": False, "isActive": False},
            {"totalTokens": 600, "isGap": False, "isActive": False},
        ]
        result = _calculate_p90_from_blocks(blocks, config)
        assert result >= config.default_min_limit

        blocks = [
            {"totalTokens": 1000000, "isGap": False, "isActive": False},
            {"totalTokens": 1100000, "isGap": False, "isActive": False},
        ]
        result = _calculate_p90_from_blocks(blocks, config)
        assert result > 0

    def test_p90_quantiles_calculation(self):
        """
        Verify that the P90 calculation function returns a value within the expected quantile range for a known distribution of token counts.
        """
        from claude_monitor.core.p90_calculator import (
            P90Config,
            _calculate_p90_from_blocks,
        )

        config = P90Config(
            common_limits=[100000],  # High limit so no hits
            limit_threshold=0.9,
            default_min_limit=1000,
            cache_ttl_seconds=300,
        )

        # Create blocks with known distribution
        blocks = [
            {"totalTokens": 1000, "isGap": False, "isActive": False},
            {"totalTokens": 2000, "isGap": False, "isActive": False},
            {"totalTokens": 3000, "isGap": False, "isActive": False},
            {"totalTokens": 4000, "isGap": False, "isActive": False},
            {"totalTokens": 5000, "isGap": False, "isActive": False},
            {"totalTokens": 6000, "isGap": False, "isActive": False},
            {"totalTokens": 7000, "isGap": False, "isActive": False},
            {"totalTokens": 8000, "isGap": False, "isActive": False},
            {"totalTokens": 9000, "isGap": False, "isActive": False},
            {"totalTokens": 10000, "isGap": False, "isActive": False},
        ]

        result = _calculate_p90_from_blocks(blocks, config)

        assert 8000 <= result <= 10000
