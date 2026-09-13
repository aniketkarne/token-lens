"""Verify the four template files ship inside the package and have the expected shape."""
from __future__ import annotations

import importlib.resources as resources
import json


def _read_template(name: str) -> str:
    return resources.files("token_lens").joinpath(f"templates/{name}").read_text(encoding="utf-8")


def test_token_lens_yaml_template_exists_and_has_budgets():
    body = _read_template("token-lens.yaml")
    assert "budgets:" in body
    assert "total_tokens" in body
    assert "tokenizer:" in body or "tokenizer " in body


def test_github_actions_template_exists_and_runs_check():
    body = _read_template("github-actions.yml")
    assert "token-lens check" in body
    assert "pip install" in body
    assert "on:" in body


def test_sample_trace_template_is_valid_json():
    body = _read_template("sample_trace.json")
    parsed = json.loads(body)
    assert "messages" in parsed
    assert isinstance(parsed["messages"], list) and parsed["messages"]
    assert "role" in parsed["messages"][0]
    assert "content" in parsed["messages"][0]


def test_tokenlens_readme_template_explains_init():
    body = _read_template("README_TOKENLENS.md")
    assert "token-lens" in body
    assert "budget" in body.lower() or "tokenizer" in body.lower() or "rag" in body.lower()