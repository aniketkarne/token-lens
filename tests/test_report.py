"""Tests for the report renderer (HTML + SVG)."""

from __future__ import annotations

import re
from pathlib import Path

from token_lens.analyze import analyze_file
from token_lens.report import render_html, render_svg, write_html, write_svg


def test_render_html_self_contained(sample_trace_path: Path):
    report = analyze_file(sample_trace_path, config={"model": "gpt-4o"})
    html = render_html(report)
    # No external script or link tags
    assert "<script" not in html.lower()
    assert "rel=\"stylesheet\"" not in html.lower()
    # Contains inline SVG treemap
    assert "<svg" in html
    assert "Token Usage Treemap" in html
    # Contains zone breakdown
    assert "Zone Breakdown" in html
    # Contains chunk utilization
    assert "Chunk Utilization" in html


def test_render_svg_contains_rects(sample_trace_path: Path):
    report = analyze_file(sample_trace_path, config={"model": "gpt-4o"})
    svg = render_svg(report)
    assert svg.startswith("<svg")
    assert "</svg>" in svg
    assert "<rect" in svg


def test_write_html_writes_file(sample_trace_path: Path, tmp_path: Path):
    report = analyze_file(sample_trace_path, config={"model": "gpt-4o"})
    out = tmp_path / "report.html"
    write_html(report, out)
    assert out.exists()
    assert out.stat().st_size > 1000
    text = out.read_text(encoding="utf-8")
    assert "token-lens report" in text


def test_write_svg_writes_file(sample_trace_path: Path, tmp_path: Path):
    report = analyze_file(sample_trace_path, config={"model": "gpt-4o"})
    out = tmp_path / "treemap.svg"
    write_svg(report, out)
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert text.startswith("<svg")


def test_html_escapes_user_content(sample_trace_path: Path, tmp_path: Path):
    # Inject HTML to ensure escaping works
    trace = {
        "model": "gpt-4o",
        "messages": [
            {"role": "user", "content": "<script>alert('xss')</script>"},
        ],
    }
    p = tmp_path / "trace.json"
    import json
    p.write_text(json.dumps(trace), encoding="utf-8")
    report = analyze_file(p)
    html = render_html(report)
    # The script tag should appear escaped (as text), not as raw HTML
    assert "<script>alert" not in html
    assert "&lt;script&gt;" in html


def test_svg_has_reasonable_dimensions(sample_trace_path: Path):
    report = analyze_file(sample_trace_path, config={"model": "gpt-4o"})
    svg = render_svg(report)
    m = re.search(r'viewBox="0 0 (\d+) (\d+)"', svg)
    assert m is not None
    w, h = int(m.group(1)), int(m.group(2))
    assert w > 0 and h > 0
