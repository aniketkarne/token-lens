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


def test_near_duplicate_chunks_have_high_redundancy():
    from token_lens.ablation import score_chunk_usefulness
    from token_lens.types import MessageRecord, ZoneKind

    def _m(content, tokens):
        return MessageRecord(index=0, role="system", content=content, zone=ZoneKind.RAG,
                            source="rag", token_count=tokens, metadata={})

    chunks = [
        _m("The capital of France is Paris.", 8),
        _m("The capital city of France is Paris.", 9),
        _m("Bananas are yellow tropical fruits.", 6),
    ]
    r = score_chunk_usefulness(chunks, query="What is the capital of France?")
    assert r.chunks[0].redundancy > 0.5 or r.chunks[1].redundancy > 0.5
    verdicts = {r.chunks[0].verdict, r.chunks[1].verdict}
    assert "marginal" in verdicts or "irrelevant" in verdicts


def test_unique_chunk_has_low_redundancy():
    from token_lens.ablation import score_chunk_usefulness
    from token_lens.types import MessageRecord, ZoneKind

    def _m(content, tokens):
        return MessageRecord(index=0, role="system", content=content, zone=ZoneKind.RAG,
                            source="rag", token_count=tokens, metadata={})

    chunks = [
        _m("Apples are red fruits that grow on trees.", 10),
        _m("Completely unrelated quantum mechanics paper from 1973.", 8),
    ]
    r = score_chunk_usefulness(chunks, query="Tell me about apples")
    assert r.chunks[0].redundancy < 0.5


def test_single_chunk_has_zero_redundancy():
    from token_lens.ablation import score_chunk_usefulness
    from token_lens.types import MessageRecord, ZoneKind

    def _m(content, tokens):
        return MessageRecord(index=0, role="system", content=content, zone=ZoneKind.RAG,
                            source="rag", token_count=tokens, metadata={})

    chunks = [_m("The only chunk here.", 6)]
    r = score_chunk_usefulness(chunks, query="anything")
    assert r.chunks[0].redundancy == 0.0
