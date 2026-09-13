"""Regression: parse_trace must preserve per-message metadata when given a raw list."""
from token_lens.parse import parse_trace


def test_parse_trace_preserves_metadata_for_raw_message_list():
    """Bug repro: messages passed as a top-level list (not under 'messages' key) lost their metadata."""
    messages = [
        {"role": "system", "content": "be helpful"},
        {"role": "system", "content": "doc", "metadata": {"zone": "rag", "chunk_id": "c1"}},
        {"role": "user", "content": "q"},
    ]
    parsed = parse_trace(messages)
    assert len(parsed) == 3
    rag_msg = parsed[1]
    assert rag_msg.metadata.get("zone") == "rag"
    assert rag_msg.metadata.get("chunk_id") == "c1"
