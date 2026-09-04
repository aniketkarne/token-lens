"""Tests for the tokenizer layer."""

from __future__ import annotations

from token_lens.tokenize import (
    _heuristic_tokens,
    _try_tiktoken,
    resolve_encoder,
)


def test_heuristic_deterministic():
    text = "Hello, world! This is a test of the heuristic tokenizer."
    a = _heuristic_tokens(text)
    b = _heuristic_tokens(text)
    assert a == b


def test_heuristic_empty():
    assert _heuristic_tokens("") == []


def test_heuristic_splits_long_tokens():
    text = "antidisestablishmentarianism"
    toks = _heuristic_tokens(text)
    assert len(toks) > 1  # long word split into chunks


def test_resolve_encoder_fallback_returns_heuristic():
    enc = resolve_encoder("nonexistent-model-xyz")
    assert enc.source == "fallback"
    assert enc.tokens("hello world") > 0


def test_resolve_encoder_no_model_returns_heuristic():
    enc = resolve_encoder(None)
    assert enc.source == "fallback"
    assert enc.tokens("hello") >= 1


def test_resolve_encoder_known_alias_attempts_provider():
    # Even if tiktoken is missing, fallback should be heuristic.
    enc = resolve_encoder("gpt-4o")
    # source may be tiktoken if installed, otherwise fallback
    assert enc.source in {"tiktoken", "transformers", "fallback"}
    assert enc.tokens("hello world") > 0


def test_fallback_is_deterministic_across_instances():
    e1 = resolve_encoder(None)
    e2 = resolve_encoder(None)
    text = "Determinism test. Same input. Same output."
    assert e1.tokens(text) == e2.tokens(text)
