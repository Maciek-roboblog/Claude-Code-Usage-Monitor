"""Tests for calculations module."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
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
    def calculator(self) -> BurnRateCalculator:
        """Create a BurnRateCalculator instance."""
        return BurnRateCalculator()

    @pytest.fixture
    def mock_active_block(self) -> Mock:
        """Create a mock active block for testing."""
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
    def mock_inactive_block(self) -> Mock:
        """Create a mock inactive block for testing."""
        block = Mock()
        block.is_active = False
        block.duration_minutes = 30
        block.token_counts = TokenCounts(input_tokens=100, output_tokens=50)
        block.cost_usd = 0.5
        return block

    def test_calculate_burn_rate_active_block(
        self, calculator: BurnRateCalculator, mock_active_block: Mock
    ) -> None:
        """Test burn rate calculation for active block."""
        burn_rate = calculator.calculate_burn_rate(mock_active_block)

        assert burn_rate is not None
        assert isinstance(burn_rate, BurnRate)

        assert burn_rate.tokens_per_minute == 5.5

        assert burn_rate.cost_per_hour == 1.0

    def test_calculate_burn_rate_inactive_block(
        self, calculator: BurnRateCalculator, mock_inactive_block: Mock
    ) -> None:
        """Test burn rate calculation for inactive block returns None."""
        burn_rate = calculator.calculate_burn_rate(mock_inactive_block)
        assert burn_rate is None

    def test_calculate_burn_rate_zero_duration(
        self, calculator: BurnRateCalculator, mock_active_block: Mock
    ) -> None:
        """Test burn rate calculation with zero duration returns None."""
        mock_active_block.duration_minutes = 0
        burn_rate = calculator.calculate_burn_rate(mock_active_block)
        assert burn_rate is None

    def test_calculate_burn_rate_no_tokens(
        self, calculator: BurnRateCalculator, mock_active_block: Mock
    ) -> None:
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
        self, calculator: BurnRateCalculator, mock_active_block: Mock
    ) -> None:
        """Test burn rate calculation with very small duration."""
        mock_active_block.duration_minutes = 1  # 1 minute minimum for active check
        burn_rate = calculator.calculate_burn_rate(mock_active_block)

        assert burn_rate is not None
        assert burn_rate.tokens_per_minute == 165.0

    @patch("claude_monitor.core.calculations.datetime")
    def test_project_block_usage_success(
        self,
        mock_datetime: Mock,
        calculator: BurnRateCalculator,
        mock_active_block: Mock,
    ) -> None:
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
        self,
        mock_datetime: Mock,
        calculator: BurnRateCalculator,
        mock_active_block: Mock,
    ) -> None:
        """Test projection when block has already ended."""
        # Mock current time to be after block end time
        mock_now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now

        mock_active_block.end_time = mock_now - timedelta(hours=1)

        projection = calculator.project_block_usage(mock_active_block)
        assert projection is None

    def test_project_block_usage_no_burn_rate(
        self, calculator: BurnRateCalculator, mock_inactive_block: Mock
    ) -> None:
        """Test projection when burn rate cannot be calculated."""
        projection = calculator.project_block_usage(mock_inactive_block)
        assert projection is None


class TestHourlyBurnRateCalculation:
    """Test cases for hourly burn rate functions."""

    @pytest.fixture
    def current_time(self) -> datetime:
        """Current time for testing."""
        return datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    @pytest.fixture
    def mock_blocks(self) -> List[Dict[str, Any]]:
        """Create mock blocks for testing."""
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

    def test_calculate_hourly_burn_rate_empty_blocks(
        self, current_time: datetime
    ) -> None:
        """Test hourly burn rate with empty blocks."""
        burn_rate = calculate_hourly_burn_rate([], current_time)
        assert burn_rate == 0.0

    def test_calculate_hourly_burn_rate_none_blocks(
        self, current_time: datetime
    ) -> None:
        """Test hourly burn rate with None blocks."""
        burn_rate = calculate_hourly_burn_rate(None, current_time)
        assert burn_rate == 0.0

    @patch("claude_monitor.core.calculations._calculate_total_tokens_in_hour")
    def test_calculate_hourly_burn_rate_success(
        self, mock_calc_tokens: Mock, current_time: datetime
    ) -> None:
        """Test successful hourly burn rate calculation."""
        mock_calc_tokens.return_value = 180.0  # Total tokens in hour

        blocks = [Mock()]
        burn_rate = calculate_hourly_burn_rate(blocks, current_time)

        assert burn_rate == 3.0

        one_hour_ago = current_time - timedelta(hours=1)
        mock_calc_tokens.assert_called_once_with(blocks, one_hour_ago, current_time)

    @patch("claude_monitor.core.calculations._calculate_total_tokens_in_hour")
    def test_calculate_hourly_burn_rate_zero_tokens(
        self, mock_calc_tokens: Mock, current_time: datetime
    ) -> None:
        """Test hourly burn rate calculation with zero tokens."""
        mock_calc_tokens.return_value = 0.0

        blocks = [Mock()]
        burn_rate = calculate_hourly_burn_rate(blocks, current_time)

        assert burn_rate == 0.0

    @patch("claude_monitor.core.calculations._process_block_for_burn_rate")
    def test_calculate_total_tokens_in_hour(
        self, mock_process_block: Mock, current_time: datetime
    ) -> None:
        """Test total tokens calculation for hour."""
        # Mock returns different token counts for each block
        mock_process_block.side_effect = [150.0, 0.0, 0.0]

        blocks = [Mock(), Mock(), Mock()]
        one_hour_ago = current_time - timedelta(hours=1)

        total_tokens = _calculate_total_tokens_in_hour(
            blocks, one_hour_ago, current_time
        )

        assert total_tokens == 150.0
        assert mock_process_block.call_count == 3

    def test_process_block_for_burn_rate_gap_block(
        self, current_time: datetime
    ) -> None:
        """Test processing gap block returns zero."""
        gap_block = {"isGap": True, "start_time": "2024-01-01T11:30:00Z"}
        one_hour_ago = current_time - timedelta(hours=1)

        tokens = _process_block_for_burn_rate(gap_block, one_hour_ago, current_time)
        assert tokens == 0

    @patch("claude_monitor.core.calculations._parse_block_start_time")
    def test_process_block_for_burn_rate_invalid_start_time(
        self, mock_parse_time: Mock, current_time: datetime
    ) -> None:
        """Test processing block with invalid start time returns zero."""
        mock_parse_time.return_value = None

        block = {"isGap": False, "start_time": "invalid"}
        one_hour_ago = current_time - timedelta(hours=1)

        tokens = _process_block_for_burn_rate(block, one_hour_ago, current_time)
        assert tokens == 0

    @patch("claude_monitor.core.calculations._determine_session_end_time")
    @patch("claude_monitor.core.calculations._parse_block_start_time")
    def test_process_block_for_burn_rate_old_session(
        self, mock_parse_time: Mock, mock_end_time: Mock, current_time: datetime
    ) -> None:
        """Test processing block that ended before the hour window."""
        one_hour_ago = current_time - timedelta(hours=1)
        old_time = one_hour_ago - timedelta(minutes=30)

        mock_parse_time.return_value = old_time
        mock_end_time.return_value = old_time  # Session ended before one hour ago

        block = {"isGap": False, "start_time": "2024-01-01T10:30:00Z"}

        tokens = _process_block_for_burn_rate(block, one_hour_ago, current_time)
        assert tokens == 0


class TestCalculationEdgeCases:
    """Test edge cases and error conditions."""

    def test_burn_rate_with_negative_duration(self) -> None:
        """Test burn rate calculation with negative duration."""
        calculator = BurnRateCalculator()

        block = Mock()
        block.is_active = True
        block.duration_minutes = -5  # Negative duration
        block.token_counts = TokenCounts(input_tokens=100, output_tokens=50)
        block.cost_usd = 0.5

        burn_rate = calculator.calculate_burn_rate(block)
        assert burn_rate is None

    def test_projection_with_zero_cost(self) -> None:
        """Test projection calculation with zero cost."""
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

    def test_very_large_token_counts(self) -> None:
        """Test calculations with very large token counts."""
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

    def test_p90_config_creation(self) -> None:
        """Test P90Config dataclass creation."""
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

    def test_did_hit_limit_true(self) -> None:
        """Test _did_hit_limit returns True when limit is hit."""
        from claude_monitor.core.p90_calculator import _did_hit_limit

        # 9000 tokens with 10000 limit and 0.9 threshold = 9000 >= 9000
        result = _did_hit_limit(9000, [10000, 50000], 0.9)
        assert result is True

        # 45000 tokens with 50000 limit and 0.9 threshold = 45000 >= 45000
        result = _did_hit_limit(45000, [10000, 50000], 0.9)
        assert result is True

    def test_did_hit_limit_false(self) -> None:
        """Test _did_hit_limit returns False when limit is not hit."""
        from claude_monitor.core.p90_calculator import _did_hit_limit

        # 8000 tokens with 10000 limit and 0.9 threshold = 8000 < 9000
        result = _did_hit_limit(8000, [10000, 50000], 0.9)
        assert result is False

        # 1000 tokens with high limits
        result = _did_hit_limit(1000, [10000, 50000], 0.9)
        assert result is False

    def test_extract_sessions_basic(self) -> None:
        """Test _extract_sessions with basic filtering."""
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
            return not b.get("isGap", False)

        result = _extract_sessions(blocks, filter_fn)

        assert result == [1000, 3000]

    def test_extract_sessions_complex_filter(self) -> None:
        """Test _extract_sessions with complex filtering."""
        from claude_monitor.core.p90_calculator import _extract_sessions

        blocks = [
            {"totalTokens": 1000, "isGap": False, "isActive": False},
            {"totalTokens": 2000, "isGap": False, "isActive": True},
            {"totalTokens": 3000, "isGap": True, "isActive": False},
            {"totalTokens": 4000, "isGap": False, "isActive": False},
        ]

        def filter_fn(b):
            return not b.get("isGap", False) and not b.get("isActive", False)

        result = _extract_sessions(blocks, filter_fn)

        assert result == [1000, 4000]

    def test_calculate_p90_from_blocks_with_hits(self) -> None:
        """Test _calculate_p90_from_blocks when limit hits are found."""
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

    def test_calculate_p90_from_blocks_no_hits(self) -> None:
        """Test _calculate_p90_from_blocks when no limit hits are found."""
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

    def test_calculate_p90_from_blocks_empty(self) -> None:
        """Test _calculate_p90_from_blocks with empty or invalid blocks."""
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

    def test_p90_calculator_init(self) -> None:
        """Test P90Calculator initialization."""
        from claude_monitor.core.p90_calculator import P90Calculator

        calculator = P90Calculator()

        assert hasattr(calculator, "_cfg")
        assert calculator._cfg.common_limits is not None
        assert calculator._cfg.limit_threshold > 0
        assert calculator._cfg.default_min_limit > 0

    def test_p90_calculator_custom_config(self) -> None:
        """Test P90Calculator with custom configuration."""
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

    def test_p90_calculator_calculate_basic(self) -> None:
        """Test P90Calculator.calculate with basic blocks."""
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

    def test_p90_calculator_calculate_empty(self) -> None:
        """Test P90Calculator.calculate with empty blocks."""
        from claude_monitor.core.p90_calculator import P90Calculator

        calculator = P90Calculator()

        result = calculator.calculate_p90_limit([])

        assert result is None

    def test_p90_calculator_caching(self) -> None:
        """Test P90Calculator caching behavior."""
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

    def test_p90_calculation_edge_cases(self) -> None:
        """Test P90 calculation with edge cases."""
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

    def test_p90_quantiles_calculation(self) -> None:
        """Test that P90 uses proper quantiles calculation."""
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
