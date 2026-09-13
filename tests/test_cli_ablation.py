"""Tests for the `token-lens ablation` CLI subcommand."""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

from token_lens import cli as cli_mod


def _run(argv):
    out = io.StringIO()
    err = io.StringIO()
    saved_out, saved_err = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = out, err
    try:
        rc = cli_mod.main(argv)
    finally:
        sys.stdout, sys.stderr = saved_out, saved_err
    return rc, out.getvalue(), err.getvalue()


def _trace_with_rag():
    return {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": "be helpful"},
            {"role": "system", "content": "The Eiffel Tower is in Paris.", "metadata": {"zone": "rag", "chunk_id": "rag-1"}},
            {"role": "system", "content": "Pizza toppings are controversial.", "metadata": {"zone": "rag", "chunk_id": "rag-2"}},
            {"role": "user", "content": "Where is the Eiffel Tower?"},
        ]
    }


def test_cli_ablation_prints_table(tmp_path: Path):
    trace = tmp_path / "trace.json"
    trace.write_text(json.dumps(_trace_with_rag()))
    rc, stdout, stderr = _run(["ablation", str(trace), "--no-color"])
    assert rc == 0, f"stderr={stderr}"
    assert "rag-1" in stdout
    assert "rag-2" in stdout
    assert "verdict" in stdout.lower() or "useful" in stdout.lower()


def test_cli_ablation_shows_summary(tmp_path: Path):
    trace = tmp_path / "trace.json"
    trace.write_text(json.dumps(_trace_with_rag()))
    rc, stdout, stderr = _run(["ablation", str(trace), "--no-color"])
    assert rc == 0
    assert "potential_removal" in stdout.lower() or "removal_tokens" in stdout.lower()


def test_cli_ablation_handles_no_rag(tmp_path: Path):
    trace = tmp_path / "trace.json"
    trace.write_text(json.dumps({"model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}]}))
    rc, stdout, stderr = _run(["ablation", str(trace), "--no-color"])
    assert rc == 0, f"stderr={stderr}"
    assert "no rag" in stdout.lower() or "ablation" in stdout.lower()
