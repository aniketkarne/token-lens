"""Tests for ChunkUsefulness and AblationResult dataclasses."""
from token_lens.types import ChunkUsefulness, AblationResult


def test_chunk_usefulness_fields():
    cu = ChunkUsefulness(
        index=0, chunk_id="rag-1", tokens=812,
        query_similarity=0.71, redundancy=0.2,
        usefulness=0.6, verdict="useful",
    )
    assert cu.index == 0
    assert cu.chunk_id == "rag-1"
    assert cu.tokens == 812
    assert cu.usefulness == 0.6
    assert cu.verdict == "useful"


def test_ablation_result_fields():
    ar = AblationResult(
        chunks=[
            ChunkUsefulness(index=0, tokens=812, query_similarity=0.9, redundancy=0.1, usefulness=0.85, verdict="useful"),
            ChunkUsefulness(index=1, tokens=744, query_similarity=0.2, redundancy=0.1, usefulness=0.18, verdict="irrelevant"),
        ],
        potential_removal_tokens=744,
        estimated_quality_delta=-0.01,
    )
    assert len(ar.chunks) == 2
    assert ar.potential_removal_tokens == 744
    assert abs(ar.estimated_quality_delta + 0.01) < 1e-9