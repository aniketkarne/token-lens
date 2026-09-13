"""Tests for --tokenizer and --custom-tokenizer CLI flags on token-lens analyze."""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

from token_lens import cli as cli_mod
from token_lens import analyze as analyze_mod


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


def _minimal_trace() -> dict:
    return {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello there."},
        ],
    }


def test_analyze_custom_tokenizer_flag_uses_custom_backend(repo_root: Path, tmp_path: Path):
    import json as _json
    tok_path = tmp_path / "tok.json"
    tok_path.write_text(_json.dumps({
        "version": "1.0", "truncation": None, "padding": None, "added_tokens": [],
        "normalizer": None, "pre_tokenizer": {"type": "Whitespace"},
        "post_processor": None, "decoder": None,
        "model": {
            "type": "BPE", "dropout": None, "unk_token": None,
            "continuing_subword_prefix": None, "end_of_word_suffix": None,
            "fuse_unk": False,
            "vocab": {"hello": 0, "world": 1}, "merges": [],
        },
    }))
    trace_path = tmp_path / "trace.json"
    trace_path.write_text(json.dumps(_minimal_trace()))
    out_json = tmp_path / "report.json"
    out_html = tmp_path / "report.html"
    rc, _, stderr = _run([
        "analyze", "--no-color", "--model", "gpt-4o",
        "--custom-tokenizer", str(tok_path),
        "--json", str(out_json),
        "-o", str(out_html),
        str(trace_path),
    ])
    assert rc == 0, f"stderr={stderr}"
    body = json.loads(out_json.read_text())
    assert body["tokenizer_backend"] == "custom"
    assert body["is_approximate"] is False


def test_analyze_tokenizer_flag_overrides_model(tmp_path: Path):
    trace_path = tmp_path / "trace.json"
    trace_path.write_text(json.dumps(_minimal_trace()))
    out_json = tmp_path / "report.json"
    out_html = tmp_path / "report.html"
    rc, _, stderr = _run([
        "analyze", "--no-color", "--model", "gpt-4o",
        "--tokenizer", "cl100k_base",
        "--json", str(out_json),
        "-o", str(out_html),
        str(trace_path),
    ])
    assert rc == 0, f"stderr={stderr}"
    body = json.loads(out_json.read_text())
    assert isinstance(body["tokenizer_name"], str) and body["tokenizer_name"]


def test_analyze_report_serializes_backend_as_string(tmp_path: Path):
    trace_path = tmp_path / "trace.json"
    trace_path.write_text(json.dumps(_minimal_trace()))
    out_json = tmp_path / "report.json"
    out_html = tmp_path / "report.html"
    rc, _, stderr = _run([
        "analyze", "--no-color", "--model", "gpt-4o",
        "--json", str(out_json),
        "-o", str(out_html),
        str(trace_path),
    ])
    assert rc == 0, f"stderr={stderr}"
    body = json.loads(out_json.read_text())
    assert body["tokenizer_backend"] in ("tiktoken", "huggingface", "custom", "heuristic")
    assert isinstance(body["tokenizer_backend"], str)


def test_analyze_file_accepts_custom_tokenizer_key(tmp_path: Path):
    import json as _json
    tok_path = tmp_path / "tok.json"
    tok_path.write_text(_json.dumps({
        "version": "1.0", "truncation": None, "padding": None, "added_tokens": [],
        "normalizer": None, "pre_tokenizer": {"type": "Whitespace"},
        "post_processor": None, "decoder": None,
        "model": {
            "type": "BPE", "dropout": None, "unk_token": None,
            "continuing_subword_prefix": None, "end_of_word_suffix": None,
            "fuse_unk": False,
            "vocab": {"a": 0, "b": 1}, "merges": [],
        },
    }))
    trace_path = tmp_path / "trace.json"
    trace_path.write_text(json.dumps(_minimal_trace()))
    report = analyze_mod.analyze_file(
        str(trace_path),
        config={"model": "gpt-4o", "custom_tokenizer_path": str(tok_path)},
    )
    assert report.tokenizer_backend.value == "custom"
    assert report.is_approximate is False