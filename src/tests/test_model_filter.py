"""Tests for the Anthropic-model predicate behind --filter-models (#113)."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from claude_monitor.core.models import is_anthropic_model
from claude_monitor.data.reader import load_usage_entries


def _jsonl_entry(model: str, ts: str) -> dict:
    return {
        "timestamp": ts,
        "message": {
            "usage": {"input_tokens": 100, "output_tokens": 50},
            "model": model,
            "id": f"{model}-id",
        },
        "model": model,
        "requestId": f"{model}-req",
    }


def _write_mixed(tmp_path: Path) -> None:
    now = datetime.now(timezone.utc)
    rows = [
        _jsonl_entry("claude-opus-4-8", (now - timedelta(minutes=3)).isoformat()),
        _jsonl_entry("gpt-4o", (now - timedelta(minutes=2)).isoformat()),
    ]
    (tmp_path / "session.jsonl").write_text("\n".join(json.dumps(r) for r in rows))


def test_filter_models_all_keeps_foreign(tmp_path: Path) -> None:
    _write_mixed(tmp_path)
    entries, _ = load_usage_entries(data_path=str(tmp_path), filter_models="all")
    models = {e.model for e in entries}
    assert any("opus" in (m or "") for m in models)
    assert any("gpt" in (m or "") for m in models)


def test_filter_models_anthropic_drops_foreign(tmp_path: Path) -> None:
    _write_mixed(tmp_path)
    entries, _ = load_usage_entries(data_path=str(tmp_path), filter_models="anthropic")
    models = {e.model for e in entries}
    assert any("opus" in (m or "") for m in models)
    assert not any("gpt" in (m or "") for m in models)


def test_claude_models_are_anthropic() -> None:
    for m in [
        "claude-opus-4-8",
        "claude-sonnet-4-20250514",
        "claude-3-5-haiku-20241022",
        "claude-3-opus-20240229",
        "Claude 3.5 Sonnet",
        "claude-fable-5",
        "claude-sonnet-5",
        "claude-mythos-5",
    ]:
        assert is_anthropic_model(m), m


def test_foreign_models_are_not_anthropic() -> None:
    for m in ["gpt-4o", "gpt-4", "deepseek-chat", "gemini-2.0-flash", "qwen-2.5"]:
        assert not is_anthropic_model(m), m


def test_foreign_models_with_family_substring_are_not_anthropic() -> None:
    # A bare family word in a foreign name must not count as Claude.
    for m in ["gpt-4-opus", "openrouter/sonnet-compatible", "not-haiku-model"]:
        assert not is_anthropic_model(m), m


def test_bedrock_and_vertex_forms_are_anthropic() -> None:
    assert is_anthropic_model("anthropic.claude-3-sonnet-20240229-v1:0")
    assert is_anthropic_model("claude-3-opus@20240229")


def test_synthetic_marker_is_kept() -> None:
    # Claude-internal synthetic entries must not be dropped by the filter.
    assert is_anthropic_model("<synthetic>") is True


def test_empty_or_missing_model_is_not_anthropic() -> None:
    assert is_anthropic_model("") is False
    assert is_anthropic_model(None) is False  # type: ignore[arg-type]
