"""Tests for the trace parser and zone classification."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from token_lens.parse import _classify_key, _zone_for_role, load_trace, parse_trace
from token_lens.types import ZoneKind


def test_classify_key_tool_schema():
    assert _classify_key("tool_definitions") == ZoneKind.TOOL_SCHEMA
    assert _classify_key("functions") == ZoneKind.TOOL_SCHEMA
    assert _classify_key("parameters") == ZoneKind.TOOL_SCHEMA


def test_classify_key_rag():
    assert _classify_key("context_docs") == ZoneKind.RAG
    assert _classify_key("search_results") == ZoneKind.RAG


def test_classify_key_unknown():
    assert _classify_key("random_key") is None


def test_zone_for_role():
    assert _zone_for_role("system") == ZoneKind.SYSTEM
    assert _zone_for_role("user") == ZoneKind.USER
    assert _zone_for_role("assistant") == ZoneKind.ASSISTANT
    assert _zone_for_role("tool") == ZoneKind.TOOL_SCHEMA
    assert _zone_for_role("narrator") == ZoneKind.UNKNOWN


def test_parse_messages_list(sample_trace):
    msgs = parse_trace(sample_trace)
    # Expect: 1 tool schema, 2 few-shot, 3 rag, 2 history, 1 user = 9
    assert len(msgs) >= 9, f"expected >=9 messages, got {len(msgs)}"
    zones = {m.zone for m in msgs}
    assert ZoneKind.TOOL_SCHEMA in zones
    assert ZoneKind.FEW_SHOT in zones
    assert ZoneKind.RAG in zones
    assert ZoneKind.HISTORY in zones
    assert ZoneKind.USER in zones


def test_parse_indexes_are_sequential(sample_trace):
    msgs = parse_trace(sample_trace)
    assert [m.index for m in msgs] == list(range(len(msgs)))


def test_parse_handles_string_content():
    msgs = parse_trace({"messages": [{"role": "user", "content": "hello"}]})
    assert len(msgs) == 1
    assert msgs[0].content == "hello"
    assert msgs[0].zone == ZoneKind.USER


def test_parse_handles_content_list():
    msgs = parse_trace(
        {"messages": [{"role": "user", "content": [{"type": "text", "text": "hello"}]}]}
    )
    assert msgs[0].content == "hello"


def test_parse_handles_nested_messages():
    payload = {"thread": {"messages": [{"role": "user", "content": "deep"}]}}
    msgs = parse_trace(payload)
    assert any(m.content == "deep" for m in msgs)


def test_parse_handles_rag_doc_dicts():
    payload = {"context_docs": [{"text": "doc one"}, {"text": "doc two"}]}
    msgs = parse_trace(payload)
    rag = [m for m in msgs if m.zone == ZoneKind.RAG]
    assert len(rag) == 2
    assert rag[0].content == "doc one"


def test_parse_empty_returns_empty():
    assert parse_trace({}) == []
    assert parse_trace({"messages": []}) == []
    assert parse_trace({"messages": "not a list"}) == []


def test_load_trace_round_trip(tmp_path: Path, sample_trace):
    p = tmp_path / "trace.json"
    p.write_text(json.dumps(sample_trace), encoding="utf-8")
    loaded = load_trace(p)
    assert loaded == sample_trace
