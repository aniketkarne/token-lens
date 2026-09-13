"""Tests for the chunk usefulness scorer."""
from token_lens.ablation import score_chunk_usefulness
from token_lens.types import MessageRecord, ZoneKind, ChunkUsefulness, AblationResult


def _chunk(role, content, zone="rag", tokens=None, chunk_id=None):
    return MessageRecord(
        index=0, role=role, content=content, zone=ZoneKind.RAG,
        source="rag", token_count=tokens or len(content.split()),
        metadata={"chunk_id": chunk_id} if chunk_id else {},
    )


def test_score_usefulness_returns_ablation_result():
    chunks = [
        _chunk("system", "The Eiffel Tower is in Paris, built in 1889.", tokens=12, chunk_id="c1"),
        _chunk("system", "Pizza toppings include pineapple controversy.", tokens=10, chunk_id="c2"),
    ]
    r = score_chunk_usefulness(chunks, query="Where is the Eiffel Tower?")
    assert isinstance(r, AblationResult)
    assert len(r.chunks) == 2
    assert all(isinstance(c, ChunkUsefulness) for c in r.chunks)


def test_relevant_chunk_scores_higher_than_irrelevant():
    chunks = [
        _chunk("system", "The Eiffel Tower is in Paris, built in 1889.", tokens=12, chunk_id="c1"),
        _chunk("system", "Pizza toppings include pineapple controversy.", tokens=10, chunk_id="c2"),
    ]
    r = score_chunk_usefulness(chunks, query="Where is the Eiffel Tower?")
    assert r.chunks[0].usefulness >= r.chunks[1].usefulness


def test_chunk_id_propagates_from_metadata():
    chunks = [
        _chunk("system", "The Eiffel Tower is in Paris.", tokens=10, chunk_id="rag-1"),
    ]
    r = score_chunk_usefulness(chunks, query="Where is the Eiffel Tower?")
    assert r.chunks[0].chunk_id == "rag-1"


def test_empty_chunks_returns_empty_result():
    r = score_chunk_usefulness([], query="anything")
    assert r.chunks == []
    assert r.potential_removal_tokens == 0
    assert r.estimated_quality_delta == 0.0


def test_verdict_thresholds():
    chunks = [
        _chunk("system", "Highly relevant content matching the question exactly.", tokens=10, chunk_id="r"),
        _chunk("system", "Tangentially related maybe.", tokens=10, chunk_id="m"),
        _chunk("system", "Completely unrelated pizza toppings.", tokens=10, chunk_id="i"),
    ]
    r = score_chunk_usefulness(chunks, query="Highly relevant content matching the question exactly.")
    verdicts = [c.verdict for c in r.chunks]
    assert "useful" in verdicts or "marginal" in verdicts
    assert "irrelevant" in verdicts
