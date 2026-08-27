"""Opt-in persistent usage warehouse.

The warehouse is intentionally small and dependency-free: JSON on disk with a
versioned schema, atomic replace writes, and dimensions that can survive Claude
Code's source-file cleanup. DuckDB-style analytics can consume this file later
without becoming a runtime dependency.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

from claude_monitor.core.models import UsageEntry
from claude_monitor.output.formatters import format_json

WAREHOUSE_SCHEMA_VERSION = "1.0"
WAREHOUSE_RECORD_VERSION = 1


def default_warehouse_path() -> Path:
    """Default warehouse path used when --warehouse has no explicit file."""
    return Path.home() / ".claude-monitor" / "warehouse" / "usage.json"


class UsageWarehouse:
    """Versioned JSON usage warehouse with retention and dimension queries."""

    def __init__(self, path: Union[str, Path], retention_days: int = 365) -> None:
        if retention_days < 1:
            raise ValueError("retention_days must be >= 1")
        self.path = Path(path).expanduser()
        self.retention_days = retention_days

    def load(self) -> Dict[str, Any]:
        """Load the warehouse document, returning an empty versioned document if absent."""
        if not self.path.exists():
            return self._empty_document()

        doc = self.path.read_text(encoding="utf-8")
        data = json.loads(doc)
        if data.get("schema_version") != WAREHOUSE_SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported warehouse schema_version: {data.get('schema_version')}"
            )
        records = data.get("records")
        if not isinstance(records, list):
            raise ValueError("Warehouse records must be a list")
        limit_events = data.get("limit_events", [])
        if not isinstance(limit_events, list):
            raise ValueError("Warehouse limit_events must be a list")
        return {
            "schema_version": WAREHOUSE_SCHEMA_VERSION,
            "records": records,
            "limit_events": limit_events,
        }

    def upsert_entries(
        self, entries: Iterable[UsageEntry], now: Optional[datetime] = None
    ) -> None:
        """Upsert usage entries, prune by retention, and atomically replace the file."""
        records_by_key = {
            record["key"]: record
            for record in self.load()["records"]
            if isinstance(record, dict) and isinstance(record.get("key"), str)
        }

        for entry in entries:
            record = self._entry_to_record(entry)
            records_by_key[record["key"]] = record

        records = self._prune_records(records_by_key.values(), now=now)
        records.sort(
            key=lambda record: (
                record["day"],
                record["project"],
                record["model"],
                record["timestamp"],
                record["key"],
            )
        )
        self._write_document(
            {
                "schema_version": WAREHOUSE_SCHEMA_VERSION,
                "records": records,
                "limit_events": self.load()["limit_events"],
            }
        )

    def upsert_limit_events(self, events: Iterable[Dict[str, Any]]) -> None:
        """Upsert detected limit events for session-ended-by-limit reports."""
        doc = self.load()
        events_by_key = {
            event["key"]: event
            for event in doc["limit_events"]
            if isinstance(event, dict) and isinstance(event.get("key"), str)
        }
        for event in events:
            stored = self._limit_event_to_record(event)
            events_by_key[stored["key"]] = stored

        limit_events = list(events_by_key.values())
        limit_events.sort(key=lambda event: (event["timestamp"], event["key"]))
        self._write_document(
            {
                "schema_version": WAREHOUSE_SCHEMA_VERSION,
                "records": doc["records"],
                "limit_events": limit_events,
            }
        )

    def query_daily(
        self,
        *,
        project: Optional[str] = None,
        model: Optional[str] = None,
        source_account: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Aggregate records by day/project/model/source dimensions."""
        groups: Dict[Tuple[str, str, str, str, Optional[str]], Dict[str, Any]] = {}

        for record in self.load()["records"]:
            if project is not None and record.get("project") != project:
                continue
            if model is not None and record.get("model") != model:
                continue
            source = record.get("source") or {}
            account = source.get("account")
            if source_account is not None and account != source_account:
                continue

            key = (
                record.get("day", ""),
                record.get("project", "unknown"),
                record.get("model", "unknown"),
                source.get("kind", "unknown"),
                account,
            )
            aggregate = groups.setdefault(
                key,
                {
                    "day": key[0],
                    "project": key[1],
                    "model": key[2],
                    "source_kind": key[3],
                    "source_account": key[4],
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cache_creation_tokens": 0,
                    "cache_read_tokens": 0,
                    "total_tokens": 0,
                    "total_cost": 0.0,
                    "entries_count": 0,
                },
            )
            aggregate["input_tokens"] += int(record.get("input_tokens", 0))
            aggregate["output_tokens"] += int(record.get("output_tokens", 0))
            aggregate["cache_creation_tokens"] += int(
                record.get("cache_creation_tokens", 0)
            )
            aggregate["cache_read_tokens"] += int(record.get("cache_read_tokens", 0))
            aggregate["total_tokens"] += int(record.get("total_tokens", 0))
            aggregate["total_cost"] += float(record.get("cost_usd", 0.0))
            aggregate["entries_count"] += 1

        rows = list(groups.values())
        for row in rows:
            row["total_cost"] = round(row["total_cost"], 10)
        rows.sort(
            key=lambda row: (
                row["day"],
                row["project"],
                row["model"],
                row["source_kind"],
                row["source_account"] or "",
            )
        )
        return rows

    def _entry_to_record(self, entry: UsageEntry) -> Dict[str, Any]:
        timestamp = entry.timestamp
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        timestamp_utc = timestamp.astimezone(timezone.utc)
        source = dict(entry.source or {})
        total_tokens = (
            entry.input_tokens
            + entry.output_tokens
            + entry.cache_creation_tokens
            + entry.cache_read_tokens
        )
        record = {
            "record_version": WAREHOUSE_RECORD_VERSION,
            "timestamp": timestamp_utc.isoformat(),
            "day": timestamp_utc.date().isoformat(),
            "project": entry.project or "unknown",
            "model": entry.model or "unknown",
            "message_id": entry.message_id,
            "request_id": entry.request_id,
            "source": {
                "kind": source.get("kind", "unknown"),
                "account": source.get("account"),
            },
            "input_tokens": int(entry.input_tokens),
            "output_tokens": int(entry.output_tokens),
            "cache_creation_tokens": int(entry.cache_creation_tokens),
            "cache_read_tokens": int(entry.cache_read_tokens),
            "total_tokens": total_tokens,
            "cost_usd": float(entry.cost_usd),
        }
        record["key"] = self._record_key(record)
        return record

    def _prune_records(
        self, records: Iterable[Dict[str, Any]], now: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        now = now or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        try:
            cutoff = now.astimezone(timezone.utc).date() - timedelta(
                days=self.retention_days
            )
        except OverflowError:
            # Retention longer than the representable calendar means nothing
            # can be old enough to prune; keep every record.
            return list(records)
        return [
            record
            for record in records
            if str(record.get("day", "")) >= cutoff.isoformat()
        ]

    def _write_document(self, doc: Dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(f"{self.path.name}.{os.getpid()}.tmp")
        tmp.write_text(format_json(doc), encoding="utf-8")
        os.replace(tmp, self.path)

    def _limit_event_to_record(self, event: Dict[str, Any]) -> Dict[str, Any]:
        timestamp = self._coerce_datetime(event["timestamp"])
        reset_time = event.get("reset_time")
        source = dict(event.get("source") or {})
        stored = {
            "record_version": WAREHOUSE_RECORD_VERSION,
            "type": event.get("type", "limit"),
            "timestamp": timestamp.isoformat(),
            "reset_time": (
                self._coerce_datetime(reset_time).isoformat() if reset_time else None
            ),
            "project": self._limit_event_project(event),
            "content": event.get("content", ""),
            "source": {
                "kind": source.get("kind", "unknown"),
                "account": source.get("account"),
            },
        }
        stored["key"] = self._limit_event_key(stored)
        return stored

    @staticmethod
    def _record_key(record: Dict[str, Any]) -> str:
        source = record["source"]
        raw_key = "|".join(
            [
                str(source.get("kind")),
                str(source.get("account")),
                record["timestamp"],
                record["project"],
                record["model"],
                record.get("message_id") or "",
                record.get("request_id") or "",
            ]
        )
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    @staticmethod
    def _limit_event_key(event: Dict[str, Any]) -> str:
        source = event["source"]
        raw_key = "|".join(
            [
                str(source.get("kind")),
                str(source.get("account")),
                event["timestamp"],
                event.get("type") or "",
                event.get("content") or "",
            ]
        )
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    @staticmethod
    def _coerce_datetime(value: Any) -> datetime:
        if isinstance(value, datetime):
            dt = value
        elif isinstance(value, str):
            dt = datetime.fromisoformat(value)
        else:
            raise TypeError("Expected datetime or ISO timestamp string")
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    @staticmethod
    def _limit_event_project(event: Dict[str, Any]) -> str:
        value = event.get("project")
        if isinstance(value, str) and value.strip():
            return value.strip()

        raw_data = event.get("raw_data")
        if isinstance(raw_data, dict):
            for key in ("cwd", "project", "project_path", "projectPath"):
                raw_value = raw_data.get(key)
                if isinstance(raw_value, str) and raw_value.strip():
                    return raw_value.strip()
        return "unknown"

    @staticmethod
    def _empty_document() -> Dict[str, Any]:
        return {
            "schema_version": WAREHOUSE_SCHEMA_VERSION,
            "records": [],
            "limit_events": [],
        }
