"""Tests for the one-shot usage snapshot builder (#126)."""

import argparse
from datetime import datetime, timezone
from typing import Any

from claude_monitor.output.snapshots import (
    SNAPSHOT_SCHEMA_VERSION,
    _family_of,
    build_snapshot,
)


def _args(plan: str = "pro") -> argparse.Namespace:
    return argparse.Namespace(plan=plan, output="json", once=True)


def _data(active: bool = True, **over: Any) -> dict:
    block: dict[str, Any] = {
        "id": "2026-06-27T12:00:00+00:00",
        "isActive": active,
        "isGap": False,
        "startTime": "2026-06-27T12:00:00+00:00",
        "endTime": "2026-06-27T17:00:00+00:00",
        "actualEndTime": None,
        "tokenCounts": {
            "inputTokens": 8500,
            "outputTokens": 3508,
            "cacheCreationInputTokens": 5000,
            "cacheReadInputTokens": 2000,
        },
        "totalTokens": 12008,  # input + output only (matches displayed utilization)
        "costUSD": 4.27,
        "models": ["claude-opus-4-8", "claude-sonnet-4-6"],
        "perModelStats": {
            "claude-opus-4-8": {
                "input_tokens": 6200,
                "output_tokens": 2900,
                "cost_usd": 3.91,
            },
            "claude-sonnet-4-6": {
                "input_tokens": 1900,
                "output_tokens": 540,
                "cost_usd": 0.31,
            },
        },
        "sentMessagesCount": 42,
        "durationMinutes": 100.0,
        "burnRate": {"tokensPerMinute": 158.4, "costPerHour": 1.31},
        "entries": [],
        "entries_count": 0,
    }
    block.update(over)
    return {"blocks": [block]}


def test_build_snapshot_active_block_shape() -> None:
    snap = build_snapshot(_data(), _args(), token_limit=19000)
    for key in (
        "schema_version",
        "generated_at",
        "source",
        "confidence",
        "stale",
        "plan",
        "limits",
        "local",
        "local_history",
        "pace",
        "forecast",
        "status",
    ):
        assert key in snap, f"missing top-level key {key}"


def test_schema_version_constant() -> None:
    snap = build_snapshot(_data(), _args(), token_limit=19000)
    assert snap["schema_version"] == SNAPSHOT_SCHEMA_VERSION == "1.0"


def test_top_level_confidence_local_estimate() -> None:
    snap = build_snapshot(_data(), _args(), token_limit=19000)
    assert snap["confidence"] == "local_estimate"
    assert snap["source"]["kind"] == "claude_code_jsonl"


def test_team_plan_is_labeled_unverified_estimate() -> None:
    snap = build_snapshot(_data(), _args("team"), token_limit=19000)
    info = snap["plan_info"]

    assert snap["plan"] == "team"
    assert info["name"] == "team"
    assert info["confidence"] == "local_estimate"
    assert info["unverified"] is True
    assert "statusline" in info["guidance"]
    assert "--plan custom" in info["guidance"]


def test_total_tokens_is_cache_inclusive() -> None:
    snap = build_snapshot(_data(), _args(), token_limit=19000)
    # 8500 + 3508 + 5000 + 2000
    assert snap["local"]["tokens"]["total_tokens"] == 19008


def test_five_hour_used_percentage_local_estimate() -> None:
    snap = build_snapshot(_data(), _args(), token_limit=19000)
    five = snap["limits"]["five_hour"]
    assert five["confidence"] == "local_estimate"
    assert five["used_percentage"] == 63.2  # round(100 * 12008 / 19000, 1)


def test_seven_day_deferred_null_unknown() -> None:
    snap = build_snapshot(_data(), _args(), token_limit=19000)
    seven = snap["limits"]["seven_day"]
    assert seven["used_percentage"] is None
    assert seven["confidence"] == "unknown"


def test_local_history_is_labeled_history_not_weekly_quota() -> None:
    snap = build_snapshot(_data(), _args(), token_limit=19000)

    assert snap["local_history"]["label"] == "local_history"
    assert snap["local_history"]["confidence"] == "local_estimate"
    assert snap["limits"]["seven_day"]["confidence"] == "unknown"


def test_no_active_block_status_20() -> None:
    snap = build_snapshot(_data(active=False), _args(), token_limit=19000)
    assert snap["status"]["code"] == 20
    assert snap["local"]["is_active"] is False


def test_forecast_token_based_not_cost() -> None:
    snap = build_snapshot(_data(), _args(), token_limit=19000)
    fc = snap["forecast"]
    assert fc["tokens_remaining"] == 6992  # 19000 - 12008
    assert fc["basis"] == "input_output_tokens_per_minute"


def test_forecast_has_today_display_context() -> None:
    snap = build_snapshot(
        _data(),
        _args(),
        token_limit=19000,
        now=datetime(2026, 6, 27, 12, 0, tzinfo=timezone.utc),
    )

    assert snap["forecast"]["display"] == "Today 12:58 (estimated)"
    assert snap["forecast"]["confidence"] == "local_estimate"


def test_forecast_has_tomorrow_display_context() -> None:
    snap = build_snapshot(
        _data(totalTokens=1000, durationMinutes=60),
        _args(),
        token_limit=19000,
        now=datetime(2026, 6, 27, 12, 0, tzinfo=timezone.utc),
    )

    assert snap["forecast"]["display"] == "Tomorrow 06:00 (estimated)"


def test_forecast_freezes_after_limit_hit() -> None:
    snap = build_snapshot(
        _data(totalTokens=20000),
        _args(),
        token_limit=19000,
        now=datetime(2026, 6, 27, 12, 0, tzinfo=timezone.utc),
    )

    assert snap["status"]["label"] == "limit_hit"
    assert snap["forecast"]["tokens_remaining"] == 0
    assert snap["forecast"]["minutes_remaining"] == 0
    assert snap["forecast"]["predicted_tokens_exhausted_at"] is None
    assert snap["forecast"]["predicted_tokens_exhausted_epoch"] is None
    assert snap["forecast"]["display"] == "limit hit"


def test_local_pace_fallback_is_labeled_estimate() -> None:
    snap = build_snapshot(
        _data(totalTokens=4750),
        _args(),
        token_limit=19000,
        now=datetime(2026, 6, 27, 14, 30, tzinfo=timezone.utc),
    )

    assert snap["pace"]["label"] == "speed up"
    assert snap["pace"]["confidence"] == "local_estimate"
    assert snap["pace"]["source"]["kind"] == "claude_code_jsonl"


def test_over_100_reports_real_pct_and_limit_hit() -> None:
    snap = build_snapshot(_data(totalTokens=20000), _args(), token_limit=19000)
    # real overage is reported (not clamped), and the exit code is limit_hit
    assert snap["limits"]["five_hour"]["used_percentage"] == 105.3
    assert snap["status"]["code"] == 11


def test_rounding_does_not_false_fire_limit_hit() -> None:
    # 18992/19000 = 99.96% -> rounds to 100.0 for display but is NOT a limit hit
    snap = build_snapshot(_data(totalTokens=18992), _args(), token_limit=19000)
    assert snap["status"]["code"] == 10  # near_limit, not 11


def test_no_limit_status_indeterminate() -> None:
    snap = build_snapshot(_data(), _args(), token_limit=0)
    assert snap["limits"]["five_hour"]["used_percentage"] is None
    assert snap["status"]["code"] == 20


def test_limit_messages_force_limit_hit() -> None:
    snap = build_snapshot(
        _data(limitMessages=[{"type": "rate_limit"}]), _args(), token_limit=19000
    )
    assert snap["status"]["code"] == 11


def test_model_distribution_includes_all_families() -> None:
    per_model_stats = {
        model: {"input_tokens": 10, "output_tokens": 10, "cost_usd": 0.01}
        for model in (
            "claude-opus-4-8",
            "claude-sonnet-5",
            "claude-haiku-4-5",
            "claude-fable-5",
            "claude-mythos-5",
            "some-future-model",
        )
    }
    snap = build_snapshot(
        _data(perModelStats=per_model_stats), _args(), token_limit=19000
    )
    dist = snap["local"]["model_distribution"]
    families = {m["family"] for m in dist}
    assert families == {"opus", "sonnet", "haiku", "fable", "mythos", "other"}
    # Percentages are model-relative (input+output), so they sum to ~100 — not
    # diluted by cache-read tokens.
    assert round(sum(m["percentage"] for m in dist)) == 100


def test_model_distribution_rejects_foreign_family_lookalikes() -> None:
    """Foreign model names remain in Other even when they contain family words."""
    for model in (
        "gpt-sonnet-5",
        "gpt-mythos-adapter",
        "openrouter/fable-compatible",
    ):
        assert _family_of(model) == "other"
