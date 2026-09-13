"""Tests for the `token-lens check` CLI subcommand."""
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


def _minimal_trace():
    return {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": "x" * 1000},
            {"role": "system", "content": "y" * 1000, "metadata": {"zone": "rag"}},
            {"role": "user", "content": "hi"},
        ],
    }


def test_check_exits_nonzero_on_breach(tmp_path):
    cfg = tmp_path / "tl.yaml"
    cfg.write_text("budgets:\n  total_tokens: 10\n")
    trace = tmp_path / "trace.json"
    trace.write_text(json.dumps(_minimal_trace()))
    rc, _, stderr = _run(["check", "--config", str(cfg), str(trace)])
    assert rc != 0, f"expected non-zero exit; stderr={stderr}"


def test_check_exits_zero_when_under_budget(tmp_path):
    cfg = tmp_path / "tl.yaml"
    cfg.write_text("budgets:\n  total_tokens: 100000\n")
    trace = tmp_path / "trace.json"
    trace.write_text(json.dumps(_minimal_trace()))
    rc, stdout, stderr = _run(["check", "--config", str(cfg), str(trace)])
    assert rc == 0, f"stderr={stderr}\nstdout={stdout}"


def test_check_handles_missing_config(tmp_path):
    trace = tmp_path / "trace.json"
    trace.write_text(json.dumps(_minimal_trace()))
    rc, _, stderr = _run(["check", "--config", str(tmp_path / "nope.yaml"), str(trace)])
    assert rc != 0
    assert "config" in stderr.lower() or "not found" in stderr.lower()


def test_check_processes_jsonl_file(tmp_path):
    cfg = tmp_path / "tl.yaml"
    cfg.write_text("budgets:\n  total_tokens: 100000\n")
    log = tmp_path / "logs.jsonl"
    lines = []
    for _ in range(3):
        lines.append(json.dumps(_minimal_trace()))
    log.write_text("\n".join(lines) + "\n")
    rc, stdout, stderr = _run(["check", "--config", str(cfg), str(log)])
    assert rc == 0, f"stderr={stderr}"
    assert "3" in stdout or "lines" in stdout.lower()


def test_check_writes_json_report_when_flagged(tmp_path):
    cfg = tmp_path / "tl.yaml"
    cfg.write_text("budgets:\n  total_tokens: 10\n")
    trace = tmp_path / "trace.json"
    trace.write_text(json.dumps(_minimal_trace()))
    out_json = tmp_path / "report.json"
    rc, _, _ = _run(["check", "--config", str(cfg), "--json", str(out_json), str(trace)])
    assert rc != 0
    assert out_json.exists()
    body = json.loads(out_json.read_text())
    assert "files" in body and len(body["files"]) == 1
    assert len(body["files"][0]["breaches"]) >= 1
