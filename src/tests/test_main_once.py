"""Integration tests for one-shot mode `_run_once` (#126)."""

import argparse
import importlib
import json
from pathlib import Path
from typing import Any, Optional
from unittest.mock import patch

import pytest

cli_main = importlib.import_module("claude_monitor.cli.main")


def _args(output: str = "json") -> argparse.Namespace:
    return argparse.Namespace(output=output, plan="pro", refresh_rate=10, theme="dark")


def _payload(active: bool = True, total: int = 12008) -> dict:
    return {
        "token_limit": 19000,
        "data": {
            "blocks": [
                {
                    "id": "b1",
                    "isActive": active,
                    "isGap": False,
                    "startTime": "2026-06-27T12:00:00+00:00",
                    "endTime": "2026-06-27T17:00:00+00:00",
                    "tokenCounts": {
                        "inputTokens": 8500,
                        "outputTokens": 3508,
                        "cacheCreationInputTokens": 5000,
                        "cacheReadInputTokens": 2000,
                    },
                    "totalTokens": total,
                    "costUSD": 4.27,
                    "perModelStats": {
                        "claude-opus-4-8": {"input_tokens": 6200, "output_tokens": 2900}
                    },
                    "sentMessagesCount": 42,
                    "burnRate": {"tokensPerMinute": 158.4, "costPerHour": 1.31},
                }
            ]
        },
    }


class _FakeOrch:
    payload: Optional[dict] = None
    init_kwargs: list[dict[str, Any]] = []

    def __init__(self, **kwargs: Any) -> None:
        type(self).init_kwargs.append(kwargs)

    def set_args(self, _args: Any) -> None:
        pass

    def force_refresh(self) -> Optional[dict]:
        return type(self).payload

    def stop(self) -> None:
        pass


def _run(
    args: argparse.Namespace,
    payload: Optional[dict],
    paths=(Path("/x"),),
    official=None,
):
    _FakeOrch.payload = payload
    _FakeOrch.init_kwargs = []
    with (
        patch.object(cli_main, "discover_claude_data_paths", return_value=list(paths)),
        patch.object(cli_main, "MonitoringOrchestrator", _FakeOrch),
        # Isolate from the real ~/.claude-monitor capture file on the test host.
        patch.object(cli_main, "read_official_limits", return_value=official),
    ):
        return cli_main._run_once(args)


def test_once_json_prints_valid_json_and_exit_0(capsys: pytest.CaptureFixture) -> None:
    rc = _run(_args("json"), _payload())
    doc = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert doc["schema_version"] == "1.0"
    assert doc["status"]["code"] == 0
    assert doc["limits"]["five_hour"]["confidence"] == "local_estimate"


def test_once_text_greppable(capsys: pytest.CaptureFixture) -> None:
    rc = _run(_args("text"), _payload())
    out = capsys.readouterr().out
    assert rc == 0
    assert "schema_version=1.0" in out
    assert "status.code=0" in out


def test_once_csv_without_report_view_exits_30(
    capsys: pytest.CaptureFixture,
) -> None:
    rc = _run(_args("csv"), _payload())
    captured = capsys.readouterr()
    assert rc == 30
    assert "warehouse report" in captured.err.lower()


def test_once_limit_hit_exit_11(capsys: pytest.CaptureFixture) -> None:
    rc = _run(_args("json"), _payload(total=20000))  # >100% of 19000
    capsys.readouterr()
    assert rc == 11


def test_once_no_active_exit_20(capsys: pytest.CaptureFixture) -> None:
    rc = _run(_args("json"), _payload(active=False))
    capsys.readouterr()
    assert rc == 20


def test_once_no_paths_exit_30(capsys: pytest.CaptureFixture) -> None:
    rc = _run(_args("json"), _payload(), paths=())
    err = capsys.readouterr().err
    assert rc == 30
    assert "No Claude data directory" in err


def test_once_force_refresh_none_exit_30(capsys: pytest.CaptureFixture) -> None:
    rc = _run(_args("json"), None)
    capsys.readouterr()
    assert rc == 30


def test_once_honors_custom_limit_tokens(capsys: pytest.CaptureFixture) -> None:
    """--plan custom --custom-limit-tokens N is used, not the P90 estimate (codex P1)."""
    args = argparse.Namespace(
        output="json",
        plan="custom",
        refresh_rate=10,
        theme="dark",
        custom_limit_tokens=50000,
    )
    _run(args, _payload())  # payload token_limit is 19000; custom override wins
    doc = json.loads(capsys.readouterr().out)
    assert doc["limits"]["five_hour"]["token_limit"] == 50000


def test_once_write_state_writes_file(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """--write-state writes the snapshot to the state file in one-shot mode (#184)."""
    state = tmp_path / "state" / "latest.json"
    args = argparse.Namespace(
        output="json",
        plan="pro",
        refresh_rate=10,
        theme="dark",
        write_state=True,
        state_file=str(state),
    )
    _run(args, _payload())
    capsys.readouterr()
    assert json.loads(state.read_text())["schema_version"] == "1.0"


def test_once_write_state_failure_exits_30(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """A requested --write-state that fails is surfaced (exit 30), not swallowed."""
    args = argparse.Namespace(
        output="json",
        plan="pro",
        refresh_rate=10,
        theme="dark",
        write_state=True,
        state_file=str(tmp_path / "x.json"),
    )
    with patch.object(cli_main, "write_state_file", side_effect=OSError("disk full")):
        rc = _run(args, _payload())
    err = capsys.readouterr().err
    assert rc == 30
    assert "state file" in err.lower()


def test_once_consumes_official_limits(capsys: pytest.CaptureFixture) -> None:
    """When official statusline limits exist, the snapshot uses them (trust keystone)."""
    official = {
        "five_hour": {"used_percentage": 88.0, "resets_at_epoch": 1782579600},
        "seven_day": None,
        "captured_at_epoch": 1782570000,
        "stale": False,
    }
    _run(_args("json"), _payload(), official=official)
    doc = json.loads(capsys.readouterr().out)
    assert doc["limits"]["five_hour"]["confidence"] == "official"
    assert doc["limits"]["five_hour"]["used_percentage"] == 88.0
    assert doc["confidence"] == "official"


def test_once_api_usage_is_opt_in_experimental(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """--api uses experimental OAuth usage data when no fresh official limit exists."""
    args = _args("json")
    args.api = True
    args.api_cache_file = str(tmp_path / "api.json")
    args.api_ttl_seconds = 180
    api_limits = {
        "five_hour": {"used_percentage": 96.0, "resets_at_epoch": 1782579600},
        "seven_day": None,
        "captured_at_epoch": 1782570000,
        "stale": False,
        "source": {"kind": "anthropic_oauth_usage_api"},
    }

    with patch.object(
        cli_main, "read_api_limits", return_value=api_limits, create=True
    ):
        rc = _run(args, _payload(total=1000))

    doc = json.loads(capsys.readouterr().out)
    assert rc == 10
    assert doc["confidence"] == "experimental"
    assert doc["limits"]["five_hour"]["confidence"] == "experimental"
    assert doc["limits"]["five_hour"]["used_percentage"] == 96.0


def test_once_fresh_official_skips_experimental_api(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """Fresh statusline data stays authoritative even when --api is enabled."""
    args = _args("json")
    args.api = True
    args.api_cache_file = str(tmp_path / "api.json")
    args.api_ttl_seconds = 180
    official = {
        "five_hour": {"used_percentage": 12.0, "resets_at_epoch": 1782579600},
        "seven_day": None,
        "captured_at_epoch": 1782570000,
        "stale": False,
    }

    with patch.object(cli_main, "read_api_limits", create=True) as read_api:
        rc = _run(args, _payload(total=1000), official=official)

    doc = json.loads(capsys.readouterr().out)
    assert read_api.call_count == 0
    assert rc == 0
    assert doc["confidence"] == "official"
    assert doc["limits"]["five_hour"]["confidence"] == "official"
    assert doc["limits"]["five_hour"]["used_percentage"] == 12.0


def test_once_uses_all_discovered_data_paths(capsys: pytest.CaptureFixture) -> None:
    """One-shot mode must not collapse discovery to data_paths[0] (#127, #196)."""
    paths = (Path("/profiles/home/projects"), Path("/profiles/work/projects"))

    _run(_args("json"), _payload(), paths=paths)
    doc = json.loads(capsys.readouterr().out)

    assert _FakeOrch.init_kwargs[-1]["data_path"] == [str(p) for p in paths]
    assert doc["source"]["data_paths"] == [str(p) for p in paths]


def test_once_compact_prints_single_line(capsys: pytest.CaptureFixture) -> None:
    """--once --compact prints one glanceable line, not the full TUI or JSON (#65)."""
    args = argparse.Namespace(
        output="rich", plan="pro", refresh_rate=10, theme="dark", compact=True
    )
    _run(args, _payload())
    out = capsys.readouterr().out.strip()
    assert "\n" not in out
    assert out.startswith("claude") and "%" in out and "reset" in out


def test_once_warns_on_warehouse_error_but_keeps_exit_code(
    capsys: pytest.CaptureFixture,
) -> None:
    """A warehouse write failure warns on stderr without hijacking the exit code."""
    payload = _payload()
    payload["data"]["metadata"] = {"warehouse_error": "disk full"}

    rc = _run(_args("json"), payload)

    captured = capsys.readouterr()
    assert rc == 0
    assert "Warning: usage warehouse was not updated: disk full" in captured.err
