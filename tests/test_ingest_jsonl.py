"""Tests for JSONL tail ingestion."""
from __future__ import annotations

import json
from pathlib import Path

from token_lens.ingest.jsonl import tail_jsonl
from token_lens.store import TraceStore


def test_tail_jsonl_ingests_existing_lines(tmp_path: Path):
    log = tmp_path / "req.jsonl"
    log.write_text(json.dumps({"model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}], "usage": {"total_tokens": 5}}) + "\n")
    db = tmp_path / "tl.db"
    store = TraceStore(str(db))
    n = tail_jsonl(str(log), store, source="generic", follow=False)
    assert n == 1
    assert len(store.recent_traces()) == 1


def test_tail_jsonl_only_ingests_new_lines(tmp_path: Path):
    log = tmp_path / "req.jsonl"
    log.write_text(json.dumps({"model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}], "usage": {"total_tokens": 5}}) + "\n")
    db = tmp_path / "tl.db"
    store = TraceStore(str(db))
    tail_jsonl(str(log), store, source="generic", follow=False)
    with open(log, "a") as f:
        f.write(json.dumps({"model": "gpt-4o", "messages": [{"role": "user", "content": "yo"}], "usage": {"total_tokens": 3}}) + "\n")
    n2 = tail_jsonl(str(log), store, source="generic", follow=False)
    assert n2 == 1
    assert len(store.recent_traces()) == 2


def test_tail_jsonl_skips_blank_and_invalid_lines(tmp_path: Path):
    log = tmp_path / "req.jsonl"
    log.write_text(
        "\n"
        + json.dumps({"model": "gpt-4o", "messages": [{"role": "user", "content": "a"}], "usage": {"total_tokens": 1}}) + "\n"
        + "not valid json\n"
        + "\n"
    )
    db = tmp_path / "tl.db"
    store = TraceStore(str(db))
    n = tail_jsonl(str(log), store, source="generic", follow=False)
    assert n == 1
    assert len(store.recent_traces()) == 1


def test_tail_jsonl_persists_offset(tmp_path: Path):
    log = tmp_path / "req.jsonl"
    log.write_text(json.dumps({"model": "gpt-4o", "messages": [], "usage": {"total_tokens": 5}}) + "\n")
    db = tmp_path / "tl.db"
    store = TraceStore(str(db))
    tail_jsonl(str(log), store, source="generic", follow=False)
    offset_file = log.parent / (log.name + ".offset")
    assert offset_file.exists()
    assert int(offset_file.read_text()) > 0


def test_tail_jsonl_returns_zero_for_empty_file(tmp_path: Path):
    log = tmp_path / "req.jsonl"
    log.write_text("")
    db = tmp_path / "tl.db"
    store = TraceStore(str(db))
    n = tail_jsonl(str(log), store, source="generic", follow=False)
    assert n == 0
