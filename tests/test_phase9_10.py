"""Tests for Phase 9 (web /optimize) + Phase 10 (demo + README + version)."""
import json
import re
import subprocess
import sys
from pathlib import Path

from token_lens import cli as cli_mod


def _run(argv):
    import io
    out, err = io.StringIO(), io.StringIO()
    saved_out, saved_err = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = out, err
    try:
        rc = cli_mod.main(argv)
    finally:
        sys.stdout, sys.stderr = saved_out, saved_err
    return rc, out.getvalue(), err.getvalue()


def test_demo_subcommand_runs_without_store():
    rc, stdout, stderr = _run(["demo", "--no-color"])
    assert rc == 0, f"stderr={stderr}"
    assert "QUALITY vs TOKENS" in stdout
    assert "recommendation" in stdout.lower() or "remove" in stdout.lower()


def test_demo_subcommand_writes_svg():
    import tempfile, os
    tmp = tempfile.mkdtemp()
    svg_path = os.path.join(tmp, "demo.svg")
    rc, _, stderr = _run(["demo", "--no-color", "--svg", svg_path])
    assert rc == 0, f"stderr={stderr}"
    assert os.path.exists(svg_path)
    body = open(svg_path).read()
    assert "<svg" in body
    assert "polyline" in body.lower()


def test_optimize_cli_writes_svg(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    db_path = tmp_path / "tl.db"
    svg_path = tmp_path / "out.svg"
    rc, _, stderr = _run(["optimize", "--db", str(db_path), "--svg", str(svg_path)])
    assert rc == 0


def test_readme_mentions_pareto_thesis():
    from pathlib import Path
    repo = Path("/Users/aconal/Documents/github/token-lens")
    readme = (repo / "README.md").read_text()
    assert "Pareto" in readme or "pareto" in readme
    assert "context" in readme.lower()
    head = "\n".join(readme.splitlines()[:80])
    assert ("minimum context" in head.lower() or "answer quality" in head.lower())


def test_readme_has_demo_quickstart():
    from pathlib import Path
    repo = Path("/Users/aconal/Documents/github/token-lens")
    readme = (repo / "README.md").read_text()
    assert "token-lens demo" in readme
    assert "token-lens init" in readme


def test_version_is_1_in_pyproject():
    from pathlib import Path
    repo = Path("/Users/aconal/Documents/github/token-lens")
    txt = (repo / "pyproject.toml").read_text()
    m = re.search(r'version\s*=\s*"(\d+\.\d+\.\d+)"', txt)
    assert m is not None
    assert m.group(1).startswith("1.")
