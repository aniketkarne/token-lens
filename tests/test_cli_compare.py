"""Smoke tests for the new CLI subcommands (compare, demo)."""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest

from token_lens import cli as cli_mod


def _run(argv: list[str]) -> tuple[int, str, str]:
    """Invoke cli.main(argv), capturing stdout/stderr."""
    out = io.StringIO()
    err = io.StringIO()
    saved_out, saved_err = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = out, err
    try:
        rc = cli_mod.main(argv)
    finally:
        sys.stdout, sys.stderr = saved_out, saved_err
    return rc, out.getvalue(), err.getvalue()


def test_cli_demo_writes_artifacts(repo_root: Path, tmp_path: Path):
    rc, stdout, stderr = _run(
        [
            "demo",
            "--no-color",
            "--model", "gpt-4o",
            "--out-dir", str(tmp_path),
        ]
    )
    assert rc == 0, stderr
    assert "token-lens demo" in stdout
    assert (tmp_path / "demo-before.html").exists()
    assert (tmp_path / "demo-after.html").exists()
    assert (tmp_path / "demo-compare.md").exists()


def test_cli_compare_prints_savings_one_liner(repo_root: Path):
    rc, stdout, stderr = _run(
        [
            "compare",
            str(repo_root / "examples" / "bloated_trace.json"),
            str(repo_root / "examples" / "lean_trace.json"),
            "--no-color",
        ]
    )
    assert rc == 0, stderr
    assert "saved" in stdout
    assert "%" in stdout


def test_cli_compare_writes_json_and_md(repo_root: Path, tmp_path: Path):
    rc, stdout, stderr = _run(
        [
            "compare",
            str(repo_root / "examples" / "bloated_trace.json"),
            str(repo_root / "examples" / "lean_trace.json"),
            "--no-color",
            "--json", str(tmp_path / "c.json"),
            "--md", str(tmp_path / "c.md"),
        ]
    )
    assert rc == 0, stderr
    j = json.loads((tmp_path / "c.json").read_text(encoding="utf-8"))
    assert "before_total_tokens" in j
    assert "delta_tokens" in j
    md = (tmp_path / "c.md").read_text(encoding="utf-8")
    assert "# token-lens compare" in md


def test_cli_compare_missing_file_returns_error(repo_root: Path, tmp_path: Path):
    rc, stdout, stderr = _run(
        [
            "compare",
            str(repo_root / "examples" / "bloated_trace.json"),
            str(tmp_path / "does-not-exist.json"),
            "--no-color",
        ]
    )
    assert rc == 2
    assert "not found" in stderr.lower()