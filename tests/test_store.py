"""Tests for the SQLite-backed TraceStore."""
from __future__ import annotations

from pathlib import Path

from token_lens.store import TraceStore


def _trace(model="gpt-4o", tokens=100, cost=0.001, zones=None, messages=None, timestamp="2026-01-01T00:00:00Z"):
    return {
        "timestamp": timestamp,
        "model": model,
        "total_tokens": tokens,
        "cost_usd": cost,
        "messages": messages if messages is not None else [{"role": "user", "content": "hi"}],
        "zones": zones if zones is not None else [{"zone": "user", "tokens": tokens}],
    }


def test_store_inserts_and_retrieves(tmp_path: Path):
    db = tmp_path / "tl.db"
    s = TraceStore(str(db))
    s.insert_trace(_trace())
    rows = s.recent_traces(limit=10)
    assert len(rows) == 1
    assert rows[0]["model"] == "gpt-4o"
    assert rows[0]["total_tokens"] == 100


def test_store_zones_breakdown(tmp_path: Path):
    db = tmp_path / "tl.db"
    s = TraceStore(str(db))
    s.insert_trace(_trace(tokens=350, zones=[
        {"zone": "system", "tokens": 100},
        {"zone": "rag", "tokens": 200},
        {"zone": "user", "tokens": 50},
    ]))
    s.insert_trace(_trace(tokens=150, timestamp="2026-01-01T00:01:00Z", zones=[
        {"zone": "system", "tokens": 100},
        {"zone": "user", "tokens": 50},
    ]))
    by_zone = s.zone_breakdown(lookback_traces=10)
    assert by_zone["system"] == 200
    assert by_zone["rag"] == 200
    assert by_zone["user"] == 100


def test_store_recent_traces_limit(tmp_path: Path):
    db = tmp_path / "tl.db"
    s = TraceStore(str(db))
    for i in range(5):
        s.insert_trace(_trace(tokens=i + 1, timestamp="2026-01-01T00:0" + str(i) + ":00Z"))
    rows = s.recent_traces(limit=2)
    assert len(rows) == 2


def test_store_persists_zones_in_json(tmp_path: Path):
    db = tmp_path / "tl.db"
    s = TraceStore(str(db))
    s.insert_trace(_trace(zones=[{"zone": "rag", "tokens": 200}, {"zone": "user", "tokens": 50}]))
    rows = s.recent_traces(limit=1)
    assert isinstance(rows[0]["zones"], list)
    by_zone = {z["zone"]: z["tokens"] for z in rows[0]["zones"]}
    assert by_zone["rag"] == 200
    assert by_zone["user"] == 50