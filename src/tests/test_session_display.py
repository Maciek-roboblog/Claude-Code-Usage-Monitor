"""Tests for SessionDisplayComponent model-distribution visibility (issue #161)."""

from typing import Any

from claude_monitor.ui.session_display import SessionDisplayComponent


def _screen_kwargs(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "plan": "pro",
        "timezone": "UTC",
        "tokens_used": 100,
        "token_limit": 1000,
        "usage_percentage": 10.0,
        "tokens_left": 900,
        "elapsed_session_minutes": 5.0,
        "total_session_minutes": 300.0,
        "burn_rate": 1.0,
        "session_cost": 0.5,
        "per_model_stats": {
            "claude-sonnet-4-5": {"input_tokens": 50, "output_tokens": 50}
        },
        "sent_messages": 3,
        "entries": [],
        "predicted_end_str": "13:00",
        "reset_time_str": "14:00",
        "current_time_str": "10:00",
    }
    base.update(overrides)
    return base


def test_model_distribution_shown_by_default() -> None:
    lines = SessionDisplayComponent().format_active_session_screen(**_screen_kwargs())
    assert any("Model Distribution" in line for line in lines)


def test_hide_model_distribution_omits_the_bar() -> None:
    lines = SessionDisplayComponent().format_active_session_screen(
        **_screen_kwargs(), hide_model_distribution=True
    )
    assert not any("Model Distribution" in line for line in lines)
    assert not any("Model Usage" in line for line in lines)


def test_no_header_produces_fewer_lines() -> None:
    comp = SessionDisplayComponent()
    full = comp.format_active_session_screen(**_screen_kwargs())
    without = comp.format_active_session_screen(**_screen_kwargs(), no_header=True)
    assert len(without) < len(full)


def test_team_plan_shows_unverified_estimate_label() -> None:
    lines = SessionDisplayComponent().format_active_session_screen(
        **_screen_kwargs(plan="team", no_header=True)
    )
    joined = "\n".join(lines)

    assert "Token Usage" in joined
    assert "Team limits are unverified estimates" in joined
    assert "statusline" in joined
    assert "--plan custom" in joined


def test_custom_plan_limit_is_marked_as_auto_estimate() -> None:
    """The P90-derived custom limit is labelled so it reads as an estimate."""
    lines = SessionDisplayComponent().format_active_session_screen(
        **_screen_kwargs(plan="custom", no_header=True)
    )
    joined = "\n".join(lines)

    token_line = next(line for line in lines if "Token Usage" in line)
    assert "(auto P90)" in token_line
    assert "Auto-estimated from your own usage history (P90)" in joined

    # Cost and message limits are P90 estimates on the custom plan too
    cost_line = next(line for line in lines if "Cost Usage" in line)
    assert "(auto P90)" in cost_line
    messages_line = next(line for line in lines if "Messages Usage" in line)
    assert "(auto P90)" in messages_line


def test_fixed_plans_are_not_marked_as_auto_estimate() -> None:
    for plan in ("pro", "max5", "max20"):
        lines = SessionDisplayComponent().format_active_session_screen(
            **_screen_kwargs(plan=plan, no_header=True)
        )
        assert "auto P90" not in "\n".join(lines)


def test_explicit_custom_limit_is_not_marked_as_auto_estimate() -> None:
    """--custom-limit-tokens bypasses P90 for tokens only; cost stays a P90."""
    lines = SessionDisplayComponent().format_active_session_screen(
        **_screen_kwargs(plan="custom", no_header=True), limit_is_p90=False
    )
    token_line = next(line for line in lines if "Token Usage" in line)
    assert "auto P90" not in token_line
    cost_line = next(line for line in lines if "Cost Usage" in line)
    assert "(auto P90)" in cost_line


def test_official_limit_is_not_marked_as_auto_estimate() -> None:
    """Official token confidence drops the token qualifier; cost stays a P90."""
    lines = SessionDisplayComponent().format_active_session_screen(
        **_screen_kwargs(plan="custom", no_header=True), limit_confidence="official"
    )
    token_line = next(line for line in lines if "Token Usage" in line)
    assert "auto P90" not in token_line
    cost_line = next(line for line in lines if "Cost Usage" in line)
    assert "(auto P90)" in cost_line


def test_time_to_reset_prefix_uses_wide_hourglass(monkeypatch) -> None:
    """U+23F1 (stopwatch) is narrow per wcwidth but 2 cells in some terminals,
    which skewed the bar alignment; the hourglass (U+23F3) is wide everywhere."""
    monkeypatch.delenv("CLAUDE_MONITOR_ASCII", raising=False)
    lines = SessionDisplayComponent().format_active_session_screen(
        **_screen_kwargs(plan="custom", no_header=True)
    )
    time_line = next(line for line in lines if "Time to Reset" in line)
    assert "⏳" in time_line
    assert "⏱" not in time_line


def test_no_active_screen_marks_custom_limit_as_auto_estimate() -> None:
    import argparse

    comp = SessionDisplayComponent()
    args = argparse.Namespace(timezone="UTC", no_header=True, custom_limit_tokens=None)
    custom = comp.format_no_active_session_screen(
        plan="custom", timezone="UTC", token_limit=1000, args=args
    )
    pro = comp.format_no_active_session_screen(
        plan="pro", timezone="UTC", token_limit=1000, args=args
    )

    assert "(auto P90)" in next(line for line in custom if "Tokens:" in line)
    assert "auto P90" not in "\n".join(pro)


def test_no_emoji_strips_emoji_from_output() -> None:
    lines = SessionDisplayComponent().format_active_session_screen(
        **_screen_kwargs(), no_emoji=True
    )
    joined = "".join(lines)
    for ch in ("💰", "📊", "🤖", "🔥", "💲", "🎯", "📨", "⏰", "🟢"):
        assert ch not in joined


def test_no_active_screen_respects_no_header_and_no_emoji() -> None:
    """The no-active-session screen honors --no-header / --no-emoji too (#57)."""
    import argparse

    comp = SessionDisplayComponent()
    args = argparse.Namespace(timezone="UTC", no_header=True, no_emoji=True)
    lines = comp.format_no_active_session_screen(
        plan="pro", timezone="UTC", token_limit=1000, current_time=None, args=args
    )
    joined = "".join(lines)
    for ch in ("📊", "🎯", "🔥", "💲", "📨", "⏰", "🟨"):
        assert ch not in joined
    assert not any(
        "CLAUDE" in line.upper() and "MONITOR" in line.upper() for line in lines
    )


def test_time_to_reset_bar_aligns_with_other_wide_bars(monkeypatch) -> None:
    """Emoji width must not shift the Time to Reset bar left or right (#144)."""
    from claude_monitor.utils.display_width import display_width, strip_rich_markup

    monkeypatch.delenv("CLAUDE_MONITOR_ASCII", raising=False)

    lines = SessionDisplayComponent().format_active_session_screen(
        **_screen_kwargs(), no_header=True
    )

    prefixes = []
    for label in ("Cost Usage", "Token Usage", "Messages Usage", "Time to Reset"):
        line = next(line for line in lines if label in line)
        prefix = strip_rich_markup(line).split("🟢 [", 1)[0]
        prefixes.append(display_width(prefix))

    assert prefixes == [25, 25, 25, 25]


def test_ascii_fallback_active_screen_uses_ascii_glyphs(monkeypatch) -> None:
    """Fallback mode pairs with --no-emoji and avoids box/progress glyphs (#160)."""
    from claude_monitor.utils.display_width import strip_rich_markup

    monkeypatch.setenv("CLAUDE_MONITOR_ASCII", "1")

    lines = SessionDisplayComponent().format_active_session_screen(
        **_screen_kwargs(), no_header=True
    )
    plain = "\n".join(strip_rich_markup(line) for line in lines)

    assert all(ord(ch) < 128 for ch in plain)
    assert "#" in plain and "-" in plain
