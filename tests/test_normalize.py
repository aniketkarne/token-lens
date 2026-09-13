"""Tests for the provider normalizer."""
from token_lens.ingest.normalize import normalize


def test_normalize_openai_style():
    line = {
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": "hi"}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        "created": 1700000000,
    }
    out = normalize(line, source="openai")
    assert out["model"] == "gpt-4o"
    assert out["total_tokens"] == 150
    assert "timestamp" in out
    assert out["messages"] == [{"role": "user", "content": "hi"}]
    assert isinstance(out["zones"], list) and out["zones"]


def test_normalize_anthropic_style():
    line = {
        "model": "claude-3-5-sonnet",
        "messages": [{"role": "user", "content": "hi"}],
        "usage": {"input_tokens": 100, "output_tokens": 50},
    }
    out = normalize(line, source="anthropic")
    assert out["model"] == "claude-3-5-sonnet"
    assert out["total_tokens"] == 150


def test_normalize_generic_shape():
    line = {"messages": [{"role": "user", "content": "hi"}], "total_tokens": 42}
    out = normalize(line, source="generic")
    assert out["total_tokens"] == 42


def test_normalize_generates_timestamp_when_missing():
    line = {"model": "gpt-4o", "messages": [], "usage": {"total_tokens": 10}}
    out = normalize(line, source="generic")
    assert "timestamp" in out
    assert "T" in out["timestamp"]


def test_normalize_includes_cost_usd():
    line = {"model": "gpt-4o", "messages": [], "usage": {"total_tokens": 1000}}
    out = normalize(line, source="generic")
    assert "cost_usd" in out
    assert out["cost_usd"] > 0


def test_normalize_handles_rag_metadata():
    line = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": "doc", "metadata": {"zone": "rag", "chunk_id": "c1"}},
            {"role": "user", "content": "question"},
        ],
        "usage": {"total_tokens": 200},
    }
    out = normalize(line, source="generic")
    zones = {z["zone"]: z["tokens"] for z in out["zones"]}
    assert "rag" in zones
