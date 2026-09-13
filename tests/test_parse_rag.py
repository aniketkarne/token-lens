"""Tests for RAG chunk metadata propagation through the parser."""
from token_lens.parse import parse_trace
from token_lens.types import ZoneKind


def test_inline_message_metadata_is_preserved():
    trace = {
        "messages": [
            {"role": "system", "content": "you are helpful"},
            {
                "role": "system",
                "content": "doc 1 content",
                "metadata": {"zone": "rag", "chunk_id": "rag-1"},
            },
            {"role": "user", "content": "what is doc 1?"},
        ]
    }
    parsed = parse_trace(trace)
    assert len(parsed) == 3
    rag_msg = parsed[1]
    assert rag_msg.metadata.get("chunk_id") == "rag-1"


def test_metadata_chunk_id_propagates_for_rag_chunks():
    trace = {
        "messages": [
            {"role": "system", "content": "be helpful"},
            {"role": "system", "content": "first chunk", "metadata": {"chunk_id": "c1", "zone": "rag"}},
            {"role": "system", "content": "second chunk", "metadata": {"chunk_id": "c2", "zone": "rag"}},
            {"role": "user", "content": "question"},
        ]
    }
    parsed = parse_trace(trace)
    rag_msgs = [m for m in parsed if m.metadata.get("zone") == "rag"]
    assert len(rag_msgs) == 2
    assert {m.metadata.get("chunk_id") for m in rag_msgs} == {"c1", "c2"}


def test_top_level_message_with_metadata():
    trace = {
        "role": "system",
        "content": "rag doc text",
        "metadata": {"chunk_id": "doc-42", "zone": "rag"},
    }
    parsed = parse_trace(trace)
    assert len(parsed) == 1
    assert parsed[0].metadata.get("chunk_id") == "doc-42"


def test_message_without_metadata_still_parses():
    trace = {
        "messages": [
            {"role": "system", "content": "no metadata here"},
            {"role": "user", "content": "hi"},
        ]
    }
    parsed = parse_trace(trace)
    assert len(parsed) == 2
    assert isinstance(parsed[0].metadata, dict)