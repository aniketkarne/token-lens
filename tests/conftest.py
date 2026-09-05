"""Shared fixtures for token-lens tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """Path to the repo root (tests/ lives one level below)."""
    return Path(__file__).resolve().parent.parent


@pytest.fixture
def sample_trace() -> dict:
    return {
        "model": "gpt-4o",
        "system_prompt": "You are a helpful assistant.",
        "tools": [
            {"type": "function", "function": {"name": "search", "parameters": {"type": "object"}}}
        ],
        "few_shot_examples": [
            {"input": "What is 2+2?", "output": "4"},
            {"input": "What is 3+3?", "output": "6"},
        ],
        "context_docs": [
            {"text": "Apples are red fruits that grow on trees. They are rich in fiber."},
            {"text": "Bananas are yellow tropical fruits. Bananas are high in potassium."},
            {"text": "Oranges are citrus fruits. Oranges contain vitamin C and are juicy."},
        ],
        "chat_history": [
            {"role": "user", "content": "Earlier: what is a fruit?"},
            {"role": "assistant", "content": "A fruit is the seed-bearing structure of a flowering plant."},
        ],
        "messages": [
            {"role": "user", "content": "Tell me about apples and bananas."},
        ],
    }


@pytest.fixture
def sample_trace_path(tmp_path: Path, sample_trace: dict) -> Path:
    p = tmp_path / "trace.json"
    p.write_text(json.dumps(sample_trace), encoding="utf-8")
    return p


@pytest.fixture
def small_trace() -> dict:
    return {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "Be concise."},
            {"role": "user", "content": "hi"},
        ],
    }
