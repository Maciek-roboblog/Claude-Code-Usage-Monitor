"""Tests for the opt-in persistent usage warehouse."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from claude_monitor.core.models import UsageEntry
from claude_monitor.data.warehouse import (
    WAREHOUSE_SCHEMA_VERSION,
    UsageWarehouse,
    default_warehouse_path,
)


def _entry(
    timestamp: datetime,
    *,
    message_id: str,
    request_id: str,
    project: str = "/workspace/app",
    model: str = "claude-3-haiku",
    source_account: str = "profile-a",
    input_tokens: int = 100,
    output_tokens: int = 50,
    cache_creation_tokens: int = 10,
    cache_read_tokens: int = 5,
    cost_usd: float = 0.25,
) -> UsageEntry:
    return UsageEntry(
        timestamp=timestamp,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_creation_tokens=cache_creation_tokens,
        cache_read_tokens=cache_read_tokens,
        cost_usd=cost_usd,
        model=model,
        message_id=message_id,
        request_id=request_id,
        project=project,
        source={"kind": "claude_code_jsonl", "account": source_account},
    )


def test_warehouse_roundtrips_versioned_records_atomically(tmp_path: Path) -> None:
    path = tmp_path / "warehouse" / "usage.json"
    entry = _entry(
        datetime(2024, 1, 2, 3, 4, tzinfo=timezone.utc),
        message_id="msg-1",
        request_id="req-1",
    )

    store = UsageWarehouse(path, retention_days=90)
    store.upsert_entries([entry], now=datetime(2024, 1, 2, tzinfo=timezone.utc))

    doc = store.load()
    assert doc["schema_version"] == WAREHOUSE_SCHEMA_VERSION
    assert len(doc["records"]) == 1
    record = doc["records"][0]
    assert record["record_version"] == 1
    assert record["day"] == "2024-01-02"
    assert record["project"] == "/workspace/app"
    assert record["model"] == "claude-3-haiku"
    assert record["message_id"] == "msg-1"
    assert record["request_id"] == "req-1"
    assert record["source"] == {
        "kind": "claude_code_jsonl",
        "account": "profile-a",
    }
    assert record["input_tokens"] == 100
    assert record["output_tokens"] == 50
    assert record["cache_creation_tokens"] == 10
    assert record["cache_read_tokens"] == 5
    assert record["cost_usd"] == 0.25
    assert not list(path.parent.glob("*.tmp"))


def test_warehouse_retention_prunes_old_records(tmp_path: Path) -> None:
    path = tmp_path / "usage.json"
    store = UsageWarehouse(path, retention_days=7)
    now = datetime(2024, 1, 8, 12, 0, tzinfo=timezone.utc)

    store.upsert_entries(
        [
            _entry(
                datetime(2023, 12, 31, 12, 0, tzinfo=timezone.utc),
                message_id="old",
                request_id="old",
            ),
            _entry(
                datetime(2024, 1, 8, 12, 0, tzinfo=timezone.utc),
                message_id="new",
                request_id="new",
            ),
        ],
        now=now,
    )

    assert [record["message_id"] for record in store.load()["records"]] == ["new"]


@pytest.mark.parametrize("retention_days", [99_999_999, 10**10])
def test_warehouse_retention_huge_value_keeps_all_records(
    tmp_path: Path, retention_days: int
) -> None:
    """Retention beyond the representable calendar keeps all records."""
    path = tmp_path / "usage.json"
    store = UsageWarehouse(path, retention_days=retention_days)
    now = datetime(2024, 1, 8, 12, 0, tzinfo=timezone.utc)

    store.upsert_entries(
        [
            _entry(
                datetime(2023, 12, 31, 12, 0, tzinfo=timezone.utc),
                message_id="old",
                request_id="old",
            ),
            _entry(
                datetime(2024, 1, 8, 12, 0, tzinfo=timezone.utc),
                message_id="new",
                request_id="new",
            ),
        ],
        now=now,
    )

    assert [record["message_id"] for record in store.load()["records"]] == [
        "old",
        "new",
    ]


def test_warehouse_query_daily_groups_by_project_model_day(tmp_path: Path) -> None:
    path = tmp_path / "usage.json"
    store = UsageWarehouse(path)
    day = datetime(2024, 1, 2, tzinfo=timezone.utc)

    store.upsert_entries(
        [
            _entry(
                day.replace(hour=9),
                message_id="msg-1",
                request_id="req-1",
                input_tokens=10,
                output_tokens=5,
                cost_usd=0.10,
            ),
            _entry(
                day.replace(hour=10),
                message_id="msg-2",
                request_id="req-2",
                input_tokens=20,
                output_tokens=7,
                cost_usd=0.20,
            ),
            _entry(
                day.replace(hour=11),
                message_id="msg-3",
                request_id="req-3",
                project="/workspace/other",
                input_tokens=99,
                output_tokens=99,
                cost_usd=0.99,
            ),
            _entry(
                day.replace(hour=12),
                message_id="msg-4",
                request_id="req-4",
                model="claude-3-opus",
                input_tokens=88,
                output_tokens=88,
                cost_usd=0.88,
            ),
        ],
        now=day,
    )

    rows = store.query_daily(project="/workspace/app", model="claude-3-haiku")

    assert rows == [
        {
            "day": "2024-01-02",
            "project": "/workspace/app",
            "model": "claude-3-haiku",
            "source_kind": "claude_code_jsonl",
            "source_account": "profile-a",
            "input_tokens": 30,
            "output_tokens": 12,
            "cache_creation_tokens": 20,
            "cache_read_tokens": 10,
            "total_tokens": 72,
            "total_cost": 0.30,
            "entries_count": 2,
        }
    ]


def test_default_warehouse_path_is_under_claude_monitor_config() -> None:
    path = default_warehouse_path()
    assert path.name == "usage.json"
    assert path.parent.name == "warehouse"
    assert path.parent.parent.name == ".claude-monitor"
