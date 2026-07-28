"""One-shot usage snapshot builder — the single machine-readable contract (#126).

Builds a versioned, source-labeled snapshot from the local JSONL analysis. Local
numbers are estimates (``confidence="local_estimate"``). When the caller passes
official statusline ``rate_limits`` (see ``official.py``), the ``limits`` block —
shaped exactly like ``rate_limits.{five_hour,seven_day}`` — flips to
``confidence="official"`` for that window and the five-hour value drives the exit
status. Opt-in experimental API limits may fill the same windows only when fresh
official limits are unavailable. No I/O and no network — the same builder
``--write-state`` (#184) reuses.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from claude_monitor._version import __version__
from claude_monitor.core.models import is_anthropic_model
from claude_monitor.core.plans import Plans

SNAPSHOT_SCHEMA_VERSION = "1.0"

_KIND = "claude_code_jsonl"
_STATUSLINE = "statusline"
_API = "anthropic_oauth_usage_api"
_LOCAL = "local_estimate"
_OFFICIAL = "official"
_EXPERIMENTAL = "experimental"
_UNKNOWN = "unknown"
_PACE_TOLERANCE_POINTS = 10.0
_FIVE_HOUR_SECONDS = 5 * 60 * 60


def _coerce_now(now: Optional[datetime]) -> datetime:
    if now is None:
        return datetime.now(timezone.utc)
    if now.tzinfo is None:
        return now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone.utc)


def _external_block(
    window: Dict[str, Any], source_kind: str, confidence: str
) -> Dict[str, Any]:
    """A ``limits.*`` block sourced outside the local JSONL estimate."""
    epoch = window.get("resets_at_epoch")
    resets_at = (
        datetime.fromtimestamp(epoch, timezone.utc).isoformat()
        if epoch is not None
        else None
    )
    return {
        "used_percentage": window.get("used_percentage"),
        "tokens_used": None,
        "token_limit": None,
        "resets_at": resets_at,
        "resets_at_epoch": epoch,
        "source": {"kind": source_kind},
        "confidence": confidence,
    }


def _official_block(window: Dict[str, Any]) -> Dict[str, Any]:
    """A ``limits.*`` block sourced from the official statusline ``rate_limits``."""
    return _external_block(window, _STATUSLINE, _OFFICIAL)


def _api_block(window: Dict[str, Any]) -> Dict[str, Any]:
    """A ``limits.*`` block sourced from the experimental OAuth usage API."""
    return _external_block(window, _API, _EXPERIMENTAL)


def _family_of(model: str) -> str:
    if not is_anthropic_model(model):
        return "other"

    name = model.lower()
    if "sonnet" in name:
        return "sonnet"
    if "opus" in name:
        return "opus"
    if "fable" in name:
        return "fable"
    if "mythos" in name:
        return "mythos"
    if "haiku" in name:
        return "haiku"
    return "other"


def _block_total_tokens(block: dict) -> int:
    """Cache-inclusive token total for a block (input + output + both cache kinds)."""
    tc = block.get("tokenCounts") or {}
    return (
        tc.get("inputTokens", 0)
        + tc.get("outputTokens", 0)
        + tc.get("cacheCreationInputTokens", 0)
        + tc.get("cacheReadInputTokens", 0)
    )


def _epoch(iso: Optional[str]) -> Optional[int]:
    if not iso:
        return None
    try:
        return int(datetime.fromisoformat(iso).timestamp())
    except (ValueError, TypeError):
        return None


def _format_forecast_display(
    exhausted_at: Optional[datetime], now: datetime, confidence: str
) -> Optional[str]:
    if exhausted_at is None:
        return None

    local_day = exhausted_at.date()
    current_day = now.date()
    if local_day == current_day:
        prefix = "Today"
    elif local_day == (current_day + timedelta(days=1)):
        prefix = "Tomorrow"
    else:
        prefix = exhausted_at.strftime("%Y-%m-%d")

    suffix = " (estimated)" if confidence == _LOCAL else ""
    return f"{prefix} {exhausted_at:%H:%M}{suffix}"


def _pace_from_window(window: Dict[str, Any], now: datetime) -> Dict[str, Any]:
    used_pct = window.get("used_percentage")
    reset_epoch = window.get("resets_at_epoch")
    if reset_epoch is None:
        reset_epoch = _epoch(window.get("resets_at"))
    source = window.get("source") or {"kind": _KIND}
    confidence = window.get("confidence") or _UNKNOWN

    if used_pct is None or reset_epoch is None:
        return {
            "label": "unknown",
            "used_percentage": used_pct,
            "elapsed_percentage": None,
            "resets_at": window.get("resets_at"),
            "resets_at_epoch": reset_epoch,
            "source": source,
            "confidence": _UNKNOWN,
        }

    reset_at = datetime.fromtimestamp(reset_epoch, timezone.utc)
    window_start = reset_at - timedelta(seconds=_FIVE_HOUR_SECONDS)
    elapsed_seconds = (now - window_start).total_seconds()
    elapsed_ratio = min(1.0, max(0.0, elapsed_seconds / _FIVE_HOUR_SECONDS))
    elapsed_pct = round(elapsed_ratio * 100, 1)
    delta = float(used_pct) - elapsed_pct

    if delta > _PACE_TOLERANCE_POINTS:
        label = "slow down"
    elif delta < -_PACE_TOLERANCE_POINTS:
        label = "speed up"
    else:
        label = "on track"

    return {
        "label": label,
        "used_percentage": used_pct,
        "elapsed_percentage": elapsed_pct,
        "resets_at": window.get("resets_at"),
        "resets_at_epoch": reset_epoch,
        "source": source,
        "confidence": confidence,
    }


def _status(active: Optional[dict], used_pct: Optional[float]) -> tuple[int, str]:
    # A known utilization (e.g. an official limit) drives the status even with no
    # local active block; only when utilization is unknown does the lack of a
    # local session make the result indeterminate.
    if used_pct is None:
        return 20, "no_active_session" if active is None else "indeterminate"
    if (active and active.get("limitMessages")) or used_pct >= 100.0:
        return 11, "limit_hit"
    if used_pct >= Plans.LIMIT_DETECTION_THRESHOLD * 100:
        return 10, "near_limit"
    return 0, "ok"


def _model_distribution(per_model: Optional[dict]) -> List[Dict[str, Any]]:
    families: Dict[str, Dict[str, Any]] = {}
    for model, stats in (per_model or {}).items():
        agg = families.setdefault(
            _family_of(model),
            {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0},
        )
        agg["input_tokens"] += stats.get("input_tokens", 0)
        agg["output_tokens"] += stats.get("output_tokens", 0)
        agg["cost_usd"] += stats.get("cost_usd", 0.0) or 0.0
    # Percentages are relative to the model token sum (input+output) so they sum
    # to ~100 — NOT the cache-inclusive total, which cache reads would dominate.
    model_total = sum(a["input_tokens"] + a["output_tokens"] for a in families.values())
    out: List[Dict[str, Any]] = []
    for family, agg in families.items():
        fam_tokens = agg["input_tokens"] + agg["output_tokens"]
        pct = round(100 * fam_tokens / model_total, 1) if model_total else 0.0
        out.append(
            {
                "family": family,
                "percentage": pct,
                "input_tokens": agg["input_tokens"],
                "output_tokens": agg["output_tokens"],
                "cost_usd": round(agg["cost_usd"], 4),
            }
        )
    out.sort(key=lambda m: m["percentage"], reverse=True)
    return out


def build_snapshot(
    data: Optional[dict],
    args: Any,
    token_limit: int,
    official: Optional[dict] = None,
    api_limits: Optional[dict] = None,
    now: Optional[datetime] = None,
) -> dict:
    """Build the one-shot snapshot dict from a single analysis payload.

    Args:
        data: the inner monitoring payload (has a ``blocks`` list of 5h blocks).
        args: parsed CLI namespace (uses ``plan``, optional ``data_path``).
        token_limit: the active token limit (plan or P90) for utilization.
        official: optional official statusline limits (from
            ``read_official_limits``). When a window carries a real
            ``used_percentage`` it overrides the local estimate for that window
            and becomes ``confidence="official"``; the five-hour value also
            drives the exit-code status.
        api_limits: optional opt-in experimental OAuth usage API limits. Fresh
            official limits win; otherwise fresh API windows override local
            estimates with ``confidence="experimental"``.

    Returns:
        The versioned snapshot dict (see module docstring).
    """
    blocks = (data or {}).get("blocks", []) or []
    active = next((b for b in blocks if b.get("isActive")), None)
    current_time = _coerce_now(now)

    plan = getattr(args, "plan", "custom")
    plan_info = Plans.get_plan_info(plan)
    data_path = getattr(args, "data_path", None)
    data_paths = getattr(args, "data_paths", None) or ([data_path] if data_path else [])
    has_limit = token_limit > 0

    if active is not None:
        tc = active.get("tokenCounts") or {}
        tokens = {
            "input_tokens": tc.get("inputTokens", 0),
            "output_tokens": tc.get("outputTokens", 0),
            "cache_creation_input_tokens": tc.get("cacheCreationInputTokens", 0),
            "cache_read_input_tokens": tc.get("cacheReadInputTokens", 0),
        }
        tokens["total_tokens"] = sum(tokens.values())  # cache-inclusive honest total
        used = active.get("totalTokens", 0)  # input+output, matches displayed util
        # Real (unclamped) ratio drives the exit code so rounding can't false-fire;
        # a local estimate may legitimately exceed 100% (over the P90/plan limit).
        raw_pct = (100 * used / token_limit) if has_limit else None
        used_pct = round(raw_pct, 1) if raw_pct is not None else None
        burn = active.get("burnRate") or {}
        local = {
            "is_active": True,
            "session_start": active.get("startTime"),
            "session_end": active.get("endTime"),
            "tokens": tokens,
            "cost_usd": active.get("costUSD", 0.0),
            "sent_messages": active.get("sentMessagesCount", 0),
            "burn_rate_tokens_per_minute": burn.get("tokensPerMinute"),
            "burn_rate_cost_per_hour": burn.get("costPerHour"),
            "model_distribution": _model_distribution(active.get("perModelStats")),
        }
        # Prefer a reset time parsed from a limit message (what Claude actually
        # told the user) over the start+5h estimate (#114, #106).
        local_reset = active.get("usageLimitResetTime") or active.get("endTime")
        five_hour = {
            "used_percentage": used_pct,
            "tokens_used": used,
            "token_limit": token_limit if has_limit else None,
            "resets_at": local_reset,
            "resets_at_epoch": _epoch(local_reset),
            "source": {"kind": _KIND},
            "confidence": _LOCAL,
        }
        tokens_remaining = max(0, token_limit - used) if has_limit else None
        # Forecast on an input+output burn rate (used / duration) so the basis
        # matches tokens_remaining; the cache-inclusive burn rate would be wrong here.
        duration = active.get("durationMinutes") or 0
        io_burn = used / duration if duration else 0
        minutes_remaining = (
            round(tokens_remaining / io_burn, 1)
            if io_burn and tokens_remaining is not None
            else None
        )
        exhausted_at = exhausted_epoch = None
        exhausted_dt = None
        if minutes_remaining is not None:
            dt = current_time + timedelta(minutes=minutes_remaining)
            exhausted_dt = dt
            exhausted_at = dt.isoformat()
            exhausted_epoch = int(dt.timestamp())
        forecast = {
            "predicted_tokens_exhausted_at": exhausted_at,
            "predicted_tokens_exhausted_epoch": exhausted_epoch,
            "tokens_remaining": tokens_remaining,
            "minutes_remaining": minutes_remaining,
            "basis": "input_output_tokens_per_minute",
            "confidence": _LOCAL,
            "display": _format_forecast_display(exhausted_dt, current_time, _LOCAL),
        }
    else:
        raw_pct = None
        local = {
            "is_active": False,
            "session_start": None,
            "session_end": None,
            "tokens": {
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_creation_input_tokens": 0,
                "cache_read_input_tokens": 0,
                "total_tokens": 0,
            },
            "cost_usd": 0.0,
            "sent_messages": 0,
            "burn_rate_tokens_per_minute": None,
            "burn_rate_cost_per_hour": None,
            "model_distribution": [],
        }
        five_hour = {
            "used_percentage": None,
            "tokens_used": None,  # no active session: utilization is unknown, not 0
            "token_limit": token_limit if has_limit else None,
            "resets_at": None,
            "resets_at_epoch": None,
            "source": {"kind": _KIND},
            "confidence": _UNKNOWN,
        }
        forecast = {
            "predicted_tokens_exhausted_at": None,
            "predicted_tokens_exhausted_epoch": None,
            "tokens_remaining": None,
            "minutes_remaining": None,
            "basis": "burn_rate_tokens_per_minute",
            "confidence": _UNKNOWN,
            "display": None,
        }

    real_blocks = [b for b in blocks if not b.get("isGap")]
    # Cache-inclusive total so local_history agrees with local.tokens.total_tokens
    # (block["totalTokens"] is the input+output display-utilization value only).
    hist_tokens = sum(_block_total_tokens(b) for b in real_blocks)
    hist_cost = round(sum(b.get("costUSD", 0.0) or 0.0 for b in real_blocks), 4)

    # seven_day is the OFFICIAL weekly slot, deferred until the statusline keystone
    # fills it. It is NOT the local window sum (that lives in local_history, and the
    # analysis window is ~8 days, not 7).
    seven_day = {
        "used_percentage": None,
        "tokens_used": None,
        "token_limit": None,
        "resets_at": None,
        "resets_at_epoch": None,
        "source": {"kind": _KIND},
        "confidence": _UNKNOWN,
    }

    # Trust keystone: when the official statusline reports a real used_percentage,
    # it is the truth about the live limit — override the local estimate for that
    # window and let the five-hour value drive the exit-code status.
    headline_confidence = _LOCAL
    snapshot_stale = False
    status_pct = raw_pct
    # A stale capture (older than the freshness TTL) must NOT drive status/display
    # as current truth — treat it like an expired window and fall back to the local
    # estimate, keeping the stale flag only as a transparency signal.
    official_had_percentage = False
    if official and not official.get("stale"):
        off_five = official.get("five_hour") or {}
        if off_five.get("used_percentage") is not None:
            five_hour = _official_block(off_five)
            status_pct = off_five["used_percentage"]
            headline_confidence = _OFFICIAL
            official_had_percentage = True
        off_seven = official.get("seven_day") or {}
        if off_seven.get("used_percentage") is not None:
            seven_day = _official_block(off_seven)
            # Weekly exhaustion limits usage too: let the higher of the two
            # official windows drive the exit status.
            seven_pct = off_seven["used_percentage"]
            status_pct = seven_pct if status_pct is None else max(status_pct, seven_pct)
            official_had_percentage = True
    if not official_had_percentage and api_limits and not api_limits.get("stale"):
        api_five = api_limits.get("five_hour") or {}
        if api_five.get("used_percentage") is not None:
            five_hour = _api_block(api_five)
            status_pct = api_five["used_percentage"]
            headline_confidence = _EXPERIMENTAL
        api_seven = api_limits.get("seven_day") or {}
        if api_seven.get("used_percentage") is not None:
            seven_day = _api_block(api_seven)
            seven_pct = api_seven["used_percentage"]
            status_pct = seven_pct if status_pct is None else max(status_pct, seven_pct)
            headline_confidence = _EXPERIMENTAL

    if (
        official
        and official.get("stale")
        and not (api_limits and not api_limits.get("stale"))
    ):
        snapshot_stale = True
    if api_limits and api_limits.get("stale") and not official_had_percentage:
        snapshot_stale = True

    code, label = _status(active, status_pct)
    if label == "limit_hit":
        forecast = {
            **forecast,
            "predicted_tokens_exhausted_at": None,
            "predicted_tokens_exhausted_epoch": None,
            "tokens_remaining": 0,
            "minutes_remaining": 0,
            "display": "limit hit",
        }

    pace = _pace_from_window(five_hour, current_time)

    return {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "generated_at": current_time.isoformat(),
        "tool": {"name": "claude-monitor", "version": __version__},
        "source": {
            "kind": _KIND,
            "account": None,
            "data_paths": list(data_paths),
        },
        "confidence": headline_confidence,
        "stale": snapshot_stale,
        "plan": plan,
        "plan_info": plan_info,
        "limits": {
            "five_hour": five_hour,
            "seven_day": seven_day,
        },
        "local": local,
        "local_history": {
            "label": "local_history",
            "total_tokens": hist_tokens,
            "total_cost_usd": hist_cost,
            "source": {"kind": _KIND},
            "confidence": _LOCAL,
        },
        "pace": pace,
        "forecast": forecast,
        "status": {"code": code, "label": label},
    }
