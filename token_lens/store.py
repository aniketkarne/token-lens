"""SQLite-backed store for ingested traces."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path


_SCHEMA = """
CREATE TABLE IF NOT EXISTS traces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    model TEXT NOT NULL,
    total_tokens INTEGER NOT NULL,
    cost_usd REAL NOT NULL,
    messages_json TEXT NOT NULL,
    zones_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS traces_timestamp ON traces(timestamp);
"""


class TraceStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path))
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def insert_trace(self, trace):
        cur = self._conn.execute(
            "INSERT INTO traces (timestamp, model, total_tokens, cost_usd, messages_json, zones_json) VALUES (?, ?, ?, ?, ?, ?)",
            (
                str(trace.get("timestamp", "")),
                str(trace.get("model", "")),
                int(trace.get("total_tokens", 0)),
                float(trace.get("cost_usd", 0.0)),
                json.dumps(trace.get("messages", [])),
                json.dumps(trace.get("zones", [])),
            ),
        )
        self._conn.commit()
        return cur.lastrowid

    def recent_traces(self, limit=100):
        cur = self._conn.execute(
            "SELECT id, timestamp, model, total_tokens, cost_usd, messages_json, zones_json FROM traces ORDER BY id DESC LIMIT ?",
            (int(limit),),
        )
        out = []
        for row in cur.fetchall():
            d = dict(row)
            d["messages"] = json.loads(d.pop("messages_json"))
            d["zones"] = json.loads(d.pop("zones_json"))
            out.append(d)
        return out

    def zone_breakdown(self, lookback_traces=100):
        cur = self._conn.execute(
            "SELECT id, zones_json FROM (SELECT id, zones_json FROM traces ORDER BY id DESC LIMIT ?) ORDER BY id ASC",
            (int(lookback_traces),),
        )
        out = {}
        for row in cur.fetchall():
            for z in json.loads(row["zones_json"]):
                zone_name = str(z.get("zone", "unknown"))
                tokens = int(z.get("tokens", 0))
                out[zone_name] = out.get(zone_name, 0) + tokens
        return out

    def close(self):
        self._conn.close()


__all__ = ["TraceStore"]