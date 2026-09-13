"""Tests for cross-trace recommendations (Phase 8.1 + 8.3)."""
import pytest

from token_lens.store import TraceStore
from token_lens.types import CrossTraceRecommendation, ParetoCurve, ParetoPoint
from token_lens.optimize import recommend_across_traces


def test_pareto_point_and_curve_fields():
    p = ParetoPoint(tokens=4000, quality=1.0, label="baseline")
    assert p.tokens == 4000
    assert p.label == "baseline"
    c = ParetoCurve(points=[p])
    assert len(c.points) == 1


def test_cross_trace_recommendation_fields():
    r = CrossTraceRecommendation(
        action="remove_chunks",
        targets=["7", "12", "19"],
        token_reduction=2481,
        cost_reduction_usd=0.0074,
        trace_coverage=0.93,
        quality_delta=-0.002,
        confidence="high",
    )
    assert r.targets == ["7", "12", "19"]
    assert r.token_reduction == 2481
    assert r.confidence == "high"


def test_recommend_across_traces_empty_store(tmp_path):
    db = tmp_path / "tl.db"
    s = TraceStore(str(db))
    recs = recommend_across_traces(s, min_coverage=0.9, min_usefulness=0.2)
    assert recs == []


def test_recommend_detects_consistently_irrelevant_chunk(tmp_path):
    db = tmp_path / "tl.db"
    s = TraceStore(str(db))
    for i in range(100):
        tid = s.insert_trace({"timestamp": "2026-01-01T00:00:00Z", "model": "gpt-4o", "total_tokens": 100, "cost_usd": 0.001, "messages": [], "zones": []})
        usefulness = 0.05 if i < 95 else 0.7
        verdict = "irrelevant" if usefulness < 0.2 else "useful"
        s.insert_ablation(trace_id=tid, chunk_id="7", usefulness=usefulness, verdict=verdict, tokens=100)
        s.insert_ablation(trace_id=tid, chunk_id="8", usefulness=0.8, verdict="useful", tokens=120)
    recs = recommend_across_traces(s, min_coverage=0.9, min_usefulness=0.2)
    chunk7_rec = next((r for r in recs if r.targets == ["7"]), None)
    assert chunk7_rec is not None
    assert chunk7_rec.trace_coverage >= 0.9
    assert chunk7_rec.confidence in ("high", "medium")


def test_recommend_skips_low_coverage_chunks(tmp_path):
    db = tmp_path / "tl.db"
    s = TraceStore(str(db))
    for i in range(100):
        tid = s.insert_trace({"timestamp": "2026-01-01T00:00:00Z", "model": "gpt-4o", "total_tokens": 100, "cost_usd": 0.001, "messages": [], "zones": []})
        if i < 5:
            s.insert_ablation(trace_id=tid, chunk_id="rare", usefulness=0.05, verdict="irrelevant", tokens=200)
        s.insert_ablation(trace_id=tid, chunk_id="common", usefulness=0.05, verdict="irrelevant", tokens=200)
    recs = recommend_across_traces(s, min_coverage=0.5, min_usefulness=0.2)
    targets = [r.targets[0] for r in recs]
    assert "common" in targets
    assert "rare" not in targets


def test_recommend_skips_useful_chunks(tmp_path):
    db = tmp_path / "tl.db"
    s = TraceStore(str(db))
    for i in range(20):
        tid = s.insert_trace({"timestamp": "2026-01-01T00:00:00Z", "model": "gpt-4o", "total_tokens": 100, "cost_usd": 0.001, "messages": [], "zones": []})
        s.insert_ablation(trace_id=tid, chunk_id="useful", usefulness=0.9, verdict="useful", tokens=150)
    recs = recommend_across_traces(s, min_coverage=0.9, min_usefulness=0.2)
    targets = [r.targets[0] for r in recs]
    assert "useful" not in targets


def test_recommend_sorted_by_token_reduction_desc(tmp_path):
    db = tmp_path / "tl.db"
    s = TraceStore(str(db))
    for i in range(50):
        tid = s.insert_trace({"timestamp": "2026-01-01T00:00:00Z", "model": "gpt-4o", "total_tokens": 100, "cost_usd": 0.001, "messages": [], "zones": []})
        s.insert_ablation(trace_id=tid, chunk_id="big", usefulness=0.05, verdict="irrelevant", tokens=1000)
        s.insert_ablation(trace_id=tid, chunk_id="small", usefulness=0.05, verdict="irrelevant", tokens=100)
    recs = recommend_across_traces(s, min_coverage=0.9, min_usefulness=0.2)
    assert len(recs) == 2
    assert recs[0].targets == ["big"]
    assert recs[1].targets == ["small"]
