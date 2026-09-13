"""Cross-trace recommendation engine."""
from __future__ import annotations

from .store import TraceStore
from .types import CrossTraceRecommendation


_DEFAULT_COST_PER_1K = 0.005


def _confidence(coverage, mean_usefulness):
    if coverage >= 0.95 and mean_usefulness < 0.1:
        return "high"
    if coverage >= 0.9:
        return "medium"
    return "low"


def recommend_across_traces(store, min_coverage=0.9, min_usefulness=0.2, cost_per_1k=_DEFAULT_COST_PER_1K):
    aggregates = store.aggregate_ablations()
    if not aggregates:
        return []
    total_traces = max((a.get("trace_count") or 0) for a in aggregates) or 1
    recs = []
    for agg in aggregates:
        chunk_id = str(agg.get("chunk_id", ""))
        if not chunk_id:
            continue
        trace_count = int(agg.get("trace_count") or 0)
        mean_use = float(agg.get("mean_usefulness") or 0.0)
        total_tokens = int(agg.get("total_tokens") or 0)
        coverage = trace_count / total_traces if total_traces else 0.0
        if coverage < min_coverage:
            continue
        if mean_use >= min_usefulness:
            continue
        token_reduction = int(total_tokens * coverage)
        cost_reduction = round((token_reduction / 1000.0) * cost_per_1k, 6)
        quality_delta = round(mean_use - 1.0, 4)
        recs.append(CrossTraceRecommendation(
            action="remove_chunks",
            targets=[chunk_id],
            token_reduction=token_reduction,
            cost_reduction_usd=cost_reduction,
            trace_coverage=round(coverage, 4),
            quality_delta=quality_delta,
            confidence=_confidence(coverage, mean_use),
        ))
    recs.sort(key=lambda r: r.token_reduction, reverse=True)
    return recs


__all__ = ["recommend_across_traces"]
