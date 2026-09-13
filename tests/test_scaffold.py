"""Tests for the `token-lens init` scaffold."""
from __future__ import annotations

import io
import sys
from pathlib import Path

from token_lens import cli as cli_mod
from token_lens.scaffold import scaffold, FileExists


def _run(argv: list[str]) -> tuple[int, str, str]:
    out = io.StringIO()
    err = io.StringIO()
    saved_out, saved_err = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = out, err
    try:
        rc = cli_mod.main(argv)
    finally:
        sys.stdout, sys.stderr = saved_out, saved_err
    return rc, out.getvalue(), err.getvalue()


def test_scaffold_writes_four_files(tmp_path: Path):
    written = scaffold(tmp_path, force=False)
    assert (tmp_path / "token-lens.yaml").exists()
    assert (tmp_path / ".github" / "workflows" / "token-lens.yml").exists()
    assert (tmp_path / "examples" / "sample_trace.json").exists()
    assert (tmp_path / "README_TOKENLENS.md").exists()
    assert len(written) == 4


def test_scaffold_refuses_to_overwrite(tmp_path: Path):
    (tmp_path / "token-lens.yaml").write_text("existing: true\n")
    try:
        scaffold(tmp_path, force=False)
    except FileExists:
        return
    raise AssertionError("expected FileExists to be raised")


def test_scaffold_with_force_overwrites(tmp_path: Path):
    (tmp_path / "token-lens.yaml").write_text("existing: true\n")
    scaffold(tmp_path, force=True)
    body = (tmp_path / "token-lens.yaml").read_text()
    assert "budgets:" in body


def test_cli_init_writes_files(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rc, stdout, stderr = _run(["init"])
    assert rc == 0, f"stderr={stderr}"
    assert (tmp_path / "token-lens.yaml").exists()
    assert (tmp_path / "examples" / "sample_trace.json").exists()
    assert (tmp_path / ".github" / "workflows" / "token-lens.yml").exists()
    assert (tmp_path / "README_TOKENLENS.md").exists()


def test_cli_init_force_flag_overwrites(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "token-lens.yaml").write_text("existing: true\n")
    rc, _, stderr = _run(["init", "--force"])
    assert rc == 0, f"stderr={stderr}"
    body = (tmp_path / "token-lens.yaml").read_text()
    assert "budgets:" in body