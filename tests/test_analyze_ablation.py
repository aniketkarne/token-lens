"""Tests that analyze_trace populates the ablation field."""
from token_lens.analyze import analyze_trace
from token_lens.types import AblationResult, ChunkUsefulness


def _trace_with_rag_chunks():
    return {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": "be helpful"},
            {
                "role": "system",
                "content": "The Eiffel Tower is in Paris, completed in 1889.",
                "metadata": {"zone": "rag", "chunk_id": "rag-1"},
            },
            {
                "role": "system",
                "content": "Pizza toppings include pineapple, controversial.",
                "metadata": {"zone": "rag", "chunk_id": "rag-2"},
            },
            {"role": "user", "content": "Where is the Eiffel Tower?"},
        ]
    }


def test_analyze_trace_populates_ablation_when_rag_present():
    rep = analyze_trace(_trace_with_rag_chunks())
    assert rep.ablation is not None
    assert isinstance(rep.ablation, AblationResult)
    assert len(rep.ablation.chunks) == 2


def test_analyze_trace_ablation_is_none_when_no_rag():
    rep = analyze_trace({
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": "be helpful"},
            {"role": "user", "content": "hi"},
        ],
    })
    assert rep.ablation is None


def test_analyze_trace_to_dict_includes_ablation():
    rep = analyze_trace(_trace_with_rag_chunks())
    d = rep.to_dict()
    assert "ablation" in d
    assert d["ablation"] is not None
    assert "chunks" in d["ablation"]