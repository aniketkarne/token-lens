"""Cross-trace recommendation engine."""
from __future__ import annotations

from .store import TraceStore
from .types import CrossTraceRecommendation, ParetoCurve, ParetoPoint


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


def compute_pareto(store, max_points=10):
    aggregates = store.aggregate_ablations()
    if not aggregates:
        return ParetoCurve(points=[ParetoPoint(tokens=0, quality=1.0, label="baseline")])
    candidates = sorted(aggregates, key=lambda a: float(a.get("mean_usefulness", 1.0)))
    total_tokens = sum(int(a.get("total_tokens", 0)) for a in candidates) or 1
    weighted_sum = sum(float(a.get("mean_usefulness", 0.0)) * int(a.get("total_tokens", 0)) for a in candidates)
    base_quality = weighted_sum / total_tokens
    points = [ParetoPoint(tokens=int(total_tokens), quality=round(base_quality, 4), label="baseline")]
    cumulative_removed_tokens = 0
    cumulative_removed_weight = 0.0
    n = len(candidates)
    sample_at = sorted(set([0, n - 1] + [int(n * (i + 1) / max_points) for i in range(max_points - 1)]))
    cum_removed_count = 0
    for idx, agg in enumerate(candidates):
        tokens = int(agg.get("total_tokens", 0))
        use = float(agg.get("mean_usefulness", 0.0))
        cumulative_removed_tokens += tokens
        cumulative_removed_weight += use * tokens
        cum_removed_count += 1
        if idx in sample_at:
            new_tokens = total_tokens - cumulative_removed_tokens
            new_quality = (weighted_sum - cumulative_removed_weight) / max(new_tokens, 1)
            points.append(ParetoPoint(tokens=int(new_tokens), quality=round(new_quality, 4), label="remove " + str(cum_removed_count)))
    filtered = [points[0]]
    for p in points[1:]:
        if p.quality < filtered[-1].quality - 0.001:
            filtered.append(p)
    return ParetoCurve(points=filtered)


__all__ = ["recommend_across_traces", "compute_pareto"]
