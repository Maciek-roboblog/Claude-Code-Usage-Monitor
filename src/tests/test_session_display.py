"""Tests for SessionDisplayComponent pace advice."""

from claude_monitor.ui.session_display import SessionDisplayComponent


def _pace(burn_rate, tokens_used, token_limit, time_remaining):
    """Render the pace line for the given inputs."""
    return SessionDisplayComponent()._render_pace(
        burn_rate, tokens_used, token_limit, time_remaining
    )


def test_slow_down_when_burning_faster_than_sustainable():
    """Burning faster than sustainable should advise slowing down."""
    # 5000 tokens left over 50 min -> sustainable 100/min; burning 200/min.
    result = _pace(200, 5000, 10000, 50)
    assert "Slow down" in result
    assert "before reset" in result


def test_room_to_spare_when_burning_slower():
    """Burning slower than sustainable should report spare headroom."""
    # sustainable 100/min, burning 40/min.
    result = _pace(40, 5000, 10000, 50)
    assert "Room to spare" in result


def test_on_pace_within_tolerance():
    """A rate within 10% of sustainable should read as on pace."""
    # sustainable 100/min, burning 105/min (within 10%).
    result = _pace(105, 5000, 10000, 50)
    assert "On pace" in result


def test_limit_reached_when_no_tokens_left():
    """No tokens left should report the limit has been reached."""
    result = _pace(100, 10000, 10000, 50)
    assert "Limit reached" in result


def test_no_advice_without_time_window():
    """No remaining time means no pace advice can be given."""
    assert "—" in _pace(100, 5000, 10000, 0)


def test_no_advice_without_known_limit():
    """An unknown token limit means no pace advice can be given."""
    assert "—" in _pace(100, 5000, 0, 50)
