"""Tests for the heuristic recommendation engine."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from token_lens.analyze import analyze_file
from token_lens.recommend import (
    Recommendation,
    build_recommendations,
    total_estimated_savings,
)
from token_lens.types import ZoneKind


def test_recommendations_attached_to_report(repo_root: Path):
    """analyze_file must populate .recommendations on the AnalysisReport."""
    p = repo_root / "examples" / "bloated_trace.json"
    report = analyze_file(p, config={"model": "gpt-4o"})
    assert hasattr(report, "recommendations")
    assert isinstance(report.recommendations, list)
    assert len(report.recommendations) >= 1


def test_recommendations_have_required_fields(repo_root: Path):
    p = repo_root / "examples" / "bloated_trace.json"
    report = analyze_file(p, config={"model": "gpt-4o"})
    for r in report.recommendations:
        assert isinstance(r, Recommendation)
        assert r.kind
        assert r.title
        assert r.zone in {z.value for z in ZoneKind}
        assert r.estimated_savings_tokens >= 0
        assert r.confidence in {"high", "medium", "low"}
        assert r.why
        assert r.how


def test_recommendations_sorted_by_savings_desc(repo_root: Path):
    p = repo_root / "examples" / "bloated_trace.json"
    report = analyze_file(p, config={"model": "gpt-4o"})
    recs = report.recommendations
    savings = [r.estimated_savings_tokens for r in recs]
    assert savings == sorted(savings, reverse=True)


def test_to_dict_is_json_serializable(repo_root: Path):
    p = repo_root / "examples" / "bloated_trace.json"
    report = analyze_file(p, config={"model": "gpt-4o"})
    json.dumps([r.to_dict() for r in report.recommendations])  # no exception


def test_recommendations_appear_in_summary_dict(repo_root: Path):
    p = repo_root / "examples" / "bloated_trace.json"
    report = analyze_file(p, config={"model": "gpt-4o"})
    d = report.to_dict()
    assert "recommendations" in d
    assert isinstance(d["recommendations"], list)
    assert d["recommendations"]  # non-empty


def test_total_estimated_savings_sums_tokens():
    rs = [
        Recommendation(
            kind="x",
            title="x",
            zone="rag",
            estimated_savings_tokens=100,
            estimated_savings_usd=0.01,
            confidence="high",
            why="",
            how="",
        ),
        Recommendation(
            kind="y",
            title="y",
            zone="history",
            estimated_savings_tokens=50,
            estimated_savings_usd=0.005,
            confidence="medium",
            why="",
            how="",
        ),
    ]
    tok, usd = total_estimated_savings(rs)
    assert tok == 150
    assert usd is not None and usd == pytest.approx(0.015)


def test_total_estimated_savings_handles_no_usd():
    rs = [
        Recommendation(
            kind="x",
            title="x",
            zone="rag",
            estimated_savings_tokens=10,
            estimated_savings_usd=None,
            confidence="low",
            why="",
            how="",
        ),
    ]
    tok, usd = total_estimated_savings(rs)
    assert tok == 10
    assert usd is None


def test_lean_trace_has_few_or_no_recommendations(repo_root: Path):
    p = repo_root / "examples" / "lean_trace.json"
    report = analyze_file(p, config={"model": "gpt-4o"})
    # Lean trace is already tight; recommendations may be empty or short.
    for r in report.recommendations:
        assert r.estimated_savings_tokens >= 0