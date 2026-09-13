"""Tests for the `token-lens ingest` and `token-lens stats` CLI subcommands."""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

from token_lens import cli as cli_mod


def _run(argv):
    out = io.StringIO()
    err = io.StringIO()
    saved_out, saved_err = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = out, err
    try:
        rc = cli_mod.main(argv)
    finally:
        sys.stdout, sys.stderr = saved_out, saved_err
    return rc, out.getvalue(), err.getvalue()


def test_cli_ingest_writes_to_db(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    log = tmp_path / "req.jsonl"
    log.write_text(json.dumps({"model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}], "usage": {"total_tokens": 100}}) + "\n")
    db = tmp_path / "tl.db"
    rc, stdout, stderr = _run(["ingest", "--jsonl", str(log), "--source", "generic", "--once", "--db", str(db)])
    assert rc == 0, f"stderr={stderr}"
    assert db.exists()
    assert "ingested" in stdout.lower() or "1" in stdout


def test_cli_ingest_skips_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    db = tmp_path / "tl.db"
    rc, _, stderr = _run(["ingest", "--jsonl", str(tmp_path / "nope.jsonl"), "--source", "generic", "--once", "--db", str(db)])
    assert rc == 0


def test_cli_stats_renders_summary(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    log = tmp_path / "req.jsonl"
    lines = []
    for i in range(20):
        lines.append(json.dumps({"model": "gpt-4o", "messages": [{"role": "user", "content": "x"}], "usage": {"total_tokens": 100 + i * 10}}))
    log.write_text("\n".join(lines) + "\n")
    db = tmp_path / "tl.db"
    rc1, _, _ = _run(["ingest", "--jsonl", str(log), "--source", "generic", "--once", "--db", str(db)])
    rc2, stdout, _ = _run(["stats", "--last", "20", "--db", str(db)])
    assert rc1 == 0 and rc2 == 0
    assert "avg" in stdout.lower() or "p95" in stdout.lower()


def test_cli_stats_shows_zone_breakdown(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    log = tmp_path / "req.jsonl"
    lines = [
        json.dumps({"model": "gpt-4o", "messages": [
            {"role": "system", "content": "x"},
            {"role": "system", "content": "doc", "metadata": {"zone": "rag"}},
            {"role": "user", "content": "q"},
        ], "usage": {"total_tokens": 300}})
    ] * 5
    log.write_text("\n".join(lines) + "\n")
    db = tmp_path / "tl.db"
    _run(["ingest", "--jsonl", str(log), "--source", "generic", "--once", "--db", str(db)])
    rc, stdout, _ = _run(["stats", "--last", "5", "--db", str(db)])
    assert rc == 0
    assert "system" in stdout.lower() or "rag" in stdout.lower() or "user" in stdout.lower()


def test_cli_stats_handles_empty_db(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    db = tmp_path / "tl.db"
    rc, stdout, _ = _run(["stats", "--db", str(db)])
    assert rc == 0
    assert "no" in stdout.lower() or "0" in stdout or "empty" in stdout.lower()
