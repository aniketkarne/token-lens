"""Normalize provider-specific trace JSON into the store shape."""
from __future__ import annotations

import datetime as _dt
from typing import Any


_DEFAULT_PRICE_PER_1K = 0.005


def _coerce_int(v):
    if v is None:
        return 0
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def _extract_tokens(payload, source):
    usage = payload.get("usage") or {}
    if source == "anthropic":
        return _coerce_int(usage.get("input_tokens", 0)) + _coerce_int(usage.get("output_tokens", 0))
    if source == "openai":
        total = usage.get("total_tokens")
        if total is not None:
            return _coerce_int(total)
        return _coerce_int(usage.get("prompt_tokens", 0)) + _coerce_int(usage.get("completion_tokens", 0))
    return _coerce_int(payload.get("total_tokens") or usage.get("total_tokens") or usage.get("input_tokens") or 0)


def _extract_timestamp(payload):
    for key in ("timestamp", "created_at", "created", "ts"):
        if key in payload:
            v = payload[key]
            if isinstance(v, (int, float)):
                return _dt.datetime.fromtimestamp(float(v), tz=_dt.timezone.utc).isoformat()
            if isinstance(v, str):
                return v
    return _dt.datetime.now(tz=_dt.timezone.utc).isoformat()


def _zone_for_message(m):
    meta = m.get("metadata") or {}
    if isinstance(meta, dict) and meta.get("zone"):
        return str(meta["zone"])
    role = (m.get("role") or "").lower()
    if role in ("system", "developer"):
        return "system"
    if role in ("user", "human"):
        return "user"
    if role in ("assistant", "ai", "model"):
        return "assistant"
    if role in ("tool", "function"):
        return "tool_schema"
    return "unknown"


def normalize(line, source="generic"):
    if not isinstance(line, dict):
        return normalize({}, source=source)

    model = str(line.get("model") or "unknown")
    messages = line.get("messages") or []
    if not isinstance(messages, list):
        messages = []
    total_tokens = _extract_tokens(line, source)
    timestamp = _extract_timestamp(line)

    if messages and total_tokens > 0:
        per_msg = max(1, total_tokens // len(messages))
        zone_buckets = {}
        for m in messages:
            if not isinstance(m, dict):
                continue
            z = _zone_for_message(m)
            zone_buckets[z] = zone_buckets.get(z, 0) + per_msg
        zones = [{"zone": z, "tokens": t} for z, t in zone_buckets.items()]
    else:
        zones = [{"zone": "messages", "tokens": total_tokens}]

    cost_usd = round((total_tokens / 1000.0) * _DEFAULT_PRICE_PER_1K, 6)

    return {
        "timestamp": timestamp,
        "model": model,
        "total_tokens": int(total_tokens),
        "cost_usd": float(cost_usd),
        "messages": messages,
        "zones": zones,
    }


__all__ = ["normalize"]
