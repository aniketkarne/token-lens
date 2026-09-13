"""RAG chunk usefulness scoring: which chunks earn their tokens?"""
from __future__ import annotations

import math
from typing import Sequence

from .embeddings import get_embedder
from .types import AblationResult, ChunkUsefulness, MessageRecord


def _cosine(a, b):
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(x * x for x in b)) or 1.0
    return sum(x * y for x, y in zip(a, b)) / (na * nb)


def _clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def _verdict(usefulness):
    if usefulness >= 0.5:
        return "useful"
    if usefulness >= 0.2:
        return "marginal"
    return "irrelevant"


def score_chunk_usefulness(chunks, query, embedder_model="all-MiniLM-L6-v2"):
    if not chunks:
        return AblationResult()

    embedder = get_embedder(model=embedder_model)
    texts = [query] + [c.content for c in chunks]
    vectors = embedder.encode(texts)
    if not vectors or len(vectors) != len(texts):
        return AblationResult()

    query_vec = vectors[0]
    chunk_vecs = vectors[1:]

    scored = []
    for i, (msg, vec) in enumerate(zip(chunks, chunk_vecs)):
        query_sim = _cosine(query_vec, vec)
        redundancy = 0.0
        for j, other in enumerate(chunk_vecs):
            if j == i:
                continue
            sim = _cosine(vec, other)
            if sim > redundancy:
                redundancy = sim
        usefulness = _clamp(query_sim - redundancy * 0.5)
        chunk_id = None
        meta = msg.metadata if isinstance(msg.metadata, dict) else {}
        if "chunk_id" in meta:
            chunk_id = str(meta["chunk_id"])
        scored.append(ChunkUsefulness(
            index=i, chunk_id=chunk_id, tokens=msg.token_count,
            query_similarity=float(query_sim), redundancy=float(redundancy),
            usefulness=float(usefulness), verdict=_verdict(usefulness),
        ))

    removal_tokens = sum(c.tokens for c in scored if c.verdict in ("marginal", "irrelevant"))
    total_tokens = sum(c.tokens for c in scored) or 1
    removed = [c for c in scored if c.verdict in ("marginal", "irrelevant")]
    quality_delta = -sum((c.usefulness * c.tokens / total_tokens) for c in removed) if removed else 0.0

    return AblationResult(
        chunks=scored,
        potential_removal_tokens=int(removal_tokens),
        estimated_quality_delta=float(quality_delta),
    )


__all__ = ["score_chunk_usefulness"]
