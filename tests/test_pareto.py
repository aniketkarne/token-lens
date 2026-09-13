"""Tests for Pareto frontier computation and rendering (Phase 8.4 + 8.6)."""
from token_lens.optimize import compute_pareto
from token_lens.pareto_render import render_pareto_svg, render_pareto_ascii
from token_lens.store import TraceStore
from token_lens.types import ParetoCurve, ParetoPoint


def _store_with_ablations(tmp_path, chunks_data):
    db = tmp_path / "tl.db"
    s = TraceStore(str(db))
    n_traces = max(c[1] for c in chunks_data)
    for i in range(n_traces):
        tid = s.insert_trace({"timestamp": "2026-01-01T00:00:00Z", "model": "gpt-4o", "total_tokens": 100, "cost_usd": 0.001, "messages": [], "zones": []})
        for cid, tc, mu, tk in chunks_data:
            if i < tc:
                verdict = "irrelevant" if mu < 0.2 else ("marginal" if mu < 0.5 else "useful")
                s.insert_ablation(trace_id=tid, chunk_id=cid, usefulness=mu, verdict=verdict, tokens=tk)
    return s


def test_compute_pareto_empty_store(tmp_path):
    s = TraceStore(str(tmp_path / "tl.db"))
    curve = compute_pareto(s)
    assert isinstance(curve, ParetoCurve)
    assert len(curve.points) >= 1


def test_compute_pareto_quality_decreases_with_tokens_removed(tmp_path):
    s = _store_with_ablations(tmp_path, [
        ("good", 10, 0.9, 100),
        ("bad", 10, 0.1, 100),
    ])
    curve = compute_pareto(s, max_points=5)
    qualities = [p.quality for p in curve.points]
    for a, b in zip(qualities, qualities[1:]):
        assert b <= a + 1e-9


def test_compute_pareto_tokens_decrease(tmp_path):
    s = _store_with_ablations(tmp_path, [
        ("a", 10, 0.9, 100),
        ("b", 10, 0.8, 200),
        ("c", 10, 0.1, 300),
    ])
    curve = compute_pareto(s, max_points=5)
    tokens = [p.tokens for p in curve.points]
    for a, b in zip(tokens, tokens[1:]):
        assert b <= a


def test_render_pareto_ascii_contains_quality_and_tokens(tmp_path):
    s = _store_with_ablations(tmp_path, [
        ("a", 5, 0.9, 100),
        ("b", 5, 0.5, 200),
    ])
    curve = compute_pareto(s)
    art = render_pareto_ascii(curve)
    assert isinstance(art, str)
    assert "quality" in art.lower() or "tokens" in art.lower()
    assert len(art) > 20


def test_render_pareto_svg_writes_file(tmp_path):
    s = _store_with_ablations(tmp_path, [
        ("a", 5, 0.9, 100),
        ("b", 5, 0.5, 200),
    ])
    curve = compute_pareto(s)
    out = tmp_path / "pareto.svg"
    render_pareto_svg(curve, str(out))
    assert out.exists()
    body = out.read_text()
    assert "<svg" in body
    assert "polyline" in body.lower() or "circle" in body.lower() or "path" in body.lower()


def test_cli_optimize_renders_chart_and_recs(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    chunks = [
        ("a", 10, 0.9, 100),
        ("bad1", 10, 0.1, 200),
        ("bad2", 10, 0.05, 300),
    ]
    s = _store_with_ablations(tmp_path, chunks)
    db_path = tmp_path / "tl.db"
    s.close()
    
    from token_lens import cli as cli_mod
    import io, sys
    out, err = io.StringIO(), io.StringIO()
    saved_out, saved_err = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = out, err
    try:
        rc = cli_mod.main(["optimize", "--db", str(db_path), "--min-coverage", "0.9"])
    finally:
        sys.stdout, sys.stderr = saved_out, saved_err
    assert rc == 0
    body = out.getvalue()
    assert "Pareto" in body or "pareto" in body or "recommend" in body.lower() or "remove" in body.lower()


def test_cli_optimize_handles_empty_db(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    db_path = tmp_path / "tl.db"
    
    from token_lens import cli as cli_mod
    import io, sys
    out, err = io.StringIO(), io.StringIO()
    saved_out, saved_err = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = out, err
    try:
        rc = cli_mod.main(["optimize", "--db", str(db_path)])
    finally:
        sys.stdout, sys.stderr = saved_out, saved_err
    assert rc == 0
    body = out.getvalue()
    assert "no" in body.lower() or "0" in body or "empty" in body.lower()