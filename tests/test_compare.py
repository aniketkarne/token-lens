"""Tests for the compare_reports / CompareResult / render_compare_markdown API."""

from __future__ import annotations

import json
from pathlib import Path

from token_lens.analyze import analyze_file
from token_lens.compare import (
    CompareResult,
    ZoneDelta,
    compare_reports,
    render_compare_markdown,
)


def test_compare_two_reports(repo_root: Path):
    a = analyze_file(repo_root / "examples" / "bloated_trace.json", config={"model": "gpt-4o"})
    b = analyze_file(repo_root / "examples" / "lean_trace.json", config={"model": "gpt-4o"})
    cmp = compare_reports(a, b)
    assert isinstance(cmp, CompareResult)
    assert cmp.before_total_tokens == a.total_tokens
    assert cmp.after_total_tokens == b.total_tokens
    assert cmp.delta_tokens == b.total_tokens - a.total_tokens
    # The lean trace must save tokens vs. the bloated one.
    assert cmp.delta_tokens < 0


def test_compare_zones_have_deltas(repo_root: Path):
    a = analyze_file(repo_root / "examples" / "bloated_trace.json", config={"model": "gpt-4o"})
    b = analyze_file(repo_root / "examples" / "lean_trace.json", config={"model": "gpt-4o"})
    cmp = compare_reports(a, b)
    # The bloated trace has history, the lean one does not.
    zones_by_name = {z.zone: z for z in cmp.zones}
    assert "history" in zones_by_name
    hist = zones_by_name["history"]
    assert isinstance(hist, ZoneDelta)
    assert hist.after_tokens is None
    assert hist.direction == "removed"


def test_compare_summary_is_human_readable(repo_root: Path):
    a = analyze_file(repo_root / "examples" / "bloated_trace.json", config={"model": "gpt-4o"})
    b = analyze_file(repo_root / "examples" / "lean_trace.json", config={"model": "gpt-4o"})
    cmp = compare_reports(a, b)
    s = cmp.summary()
    assert "tokens:" in s
    assert "->" in s
    assert "cost:" in s
    assert "zones:" in s


def test_compare_to_dict_is_json_serializable(repo_root: Path):
    a = analyze_file(repo_root / "examples" / "bloated_trace.json", config={"model": "gpt-4o"})
    b = analyze_file(repo_root / "examples" / "lean_trace.json", config={"model": "gpt-4o"})
    cmp = compare_reports(a, b)
    json.dumps(cmp.to_dict())  # must not raise


def test_render_compare_markdown_contains_savings_table(repo_root: Path):
    a = analyze_file(repo_root / "examples" / "bloated_trace.json", config={"model": "gpt-4o"})
    b = analyze_file(repo_root / "examples" / "lean_trace.json", config={"model": "gpt-4o"})
    cmp = compare_reports(a, b)
    md = render_compare_markdown(cmp)
    assert "# token-lens compare" in md
    assert "**tokens:**" in md
    assert "| zone |" in md
    assert "→" in md


def test_compare_same_trace_is_zero_delta(repo_root: Path):
    a = analyze_file(repo_root / "examples" / "lean_trace.json", config={"model": "gpt-4o"})
    b = analyze_file(repo_root / "examples" / "lean_trace.json", config={"model": "gpt-4o"})
    cmp = compare_reports(a, b)
    assert cmp.delta_tokens == 0
    assert cmp.delta_pct == 0.0


def test_compare_encoder_mismatch_warning(repo_root: Path, tmp_path: Path):
    """Compare banners a warning when before/after use different encoders."""
    a = analyze_file(repo_root / "examples" / "bloated_trace.json", config={"model": "gpt-4o"})
    b = analyze_file(repo_root / "examples" / "lean_trace.json", config={"model": "gpt-4o"})
    # Force a fake encoder label mismatch.
    object.__setattr__(a, "encoder_label", "tiktoken-cl100k")
    object.__setattr__(b, "encoder_label", "heuristic-bpe-lite")
    cmp = compare_reports(a, b)
    summary = cmp.summary()
    assert "encoders differ" in summary.lower()