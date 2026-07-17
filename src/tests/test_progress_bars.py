"""Tests for progress bars and display-width handling."""

from claude_monitor.ui.progress_bars import ModelUsageBar, TokenProgressBar


def _tokens(n: int) -> dict[str, int]:
    return {"input_tokens": n // 2, "output_tokens": n - n // 2}


def test_render_shows_haiku_family_not_just_sonnet_opus() -> None:
    """Sonnet + Haiku must both show; Haiku must not vanish into a hidden 'other'."""
    bar = ModelUsageBar(width=50)
    out = bar.render(
        {
            "claude-sonnet-4-5": _tokens(60),
            "claude-haiku-4-5": _tokens(40),
        }
    )
    assert "Sonnet" in out and "60.0%" in out
    assert "Haiku" in out and "40.0%" in out


def test_render_lists_every_present_family() -> None:
    """Three families present -> all three named in the summary."""
    bar = ModelUsageBar(width=50)
    out = bar.render(
        {
            "claude-sonnet-4-5": _tokens(50),
            "claude-opus-4-5": _tokens(30),
            "claude-haiku-4-5": _tokens(20),
        }
    )
    for family in ("Sonnet", "Opus", "Haiku"):
        assert family in out


def test_render_fable_family_recognized_not_other() -> None:
    """Fable 5 usage shows under its own family name, not as 'Other'."""
    bar = ModelUsageBar(width=50)
    out = bar.render(
        {
            "claude-fable-5": _tokens(70),
            "claude-sonnet-4-5": _tokens(30),
        }
    )
    assert "Fable" in out and "70.0%" in out
    assert "Sonnet" in out and "30.0%" in out
    assert "Other" not in out


def test_render_unknown_family_shown_as_other_not_dropped() -> None:
    """An unmapped family still appears (as 'Other'); its share is not silently lost."""
    bar = ModelUsageBar(width=50)
    out = bar.render(
        {
            "claude-sonnet-4-5": _tokens(50),
            "some-future-model": _tokens(50),
        }
    )
    assert "Sonnet" in out and "50.0%" in out
    assert "Other" in out


def test_display_width_counts_clock_emoji_as_two_columns() -> None:
    """Clock emoji are two terminal cells even when Python len() sees one codepoint."""
    from claude_monitor.utils.display_width import display_width

    assert display_width("⏰") == 2
    assert display_width("⏱️") == 2
    assert len("⏰") == 1


def test_pad_to_display_width_uses_terminal_cells_not_codepoints() -> None:
    """Padding must align by terminal display width, not Python string length."""
    from claude_monitor.utils.display_width import display_width, pad_to_display_width

    padded = pad_to_display_width("⏱️  Time to Reset:", 25)

    assert display_width(padded) == 25
    assert padded.endswith(" " * 7)


def test_ascii_fallback_progress_bar_uses_plain_characters(
    monkeypatch,
) -> None:
    """ASCII fallback avoids emoji and block glyphs on non-UTF-8 consoles (#160)."""
    from claude_monitor.utils.display_width import strip_rich_markup

    monkeypatch.setenv("CLAUDE_MONITOR_ASCII", "1")

    out = TokenProgressBar(width=10).render(10)
    plain = strip_rich_markup(out)

    assert "#" in plain and "-" in plain
    assert all(ord(ch) < 128 for ch in plain)
