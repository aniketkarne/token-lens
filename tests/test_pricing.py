"""Tests for the pricing table and model-id matching.

The table is a small set of verified-current models; matching is exact or
snapshot-suffix only. A stale or over-eager match produces a wrong cost
estimate, which is worse than reporting the cost as unknown.
"""
from __future__ import annotations

from token_lens.pricing import DEFAULT_PRICING, estimate_cost


def test_known_model_is_priced():
    cost, label = estimate_cost("claude-sonnet-5-5", 1000, None)
    assert cost == DEFAULT_PRICING["claude-sonnet-5-5"]
    assert label and "claude-sonnet-5-5" in label


def test_dotted_spelling_matches():
    cost, _ = estimate_cost("claude-sonnet-5.5", 1000, None)
    assert cost == DEFAULT_PRICING["claude-sonnet-5-5"]


def test_vendor_prefix_is_stripped():
    cost, label = estimate_cost("openai/gpt-6-luna", 1000, None)
    assert cost == DEFAULT_PRICING["gpt-6-luna"]
    assert label and "gpt-6-luna" in label


def test_snapshot_suffix_matches_base_price():
    cost, _ = estimate_cost("claude-sonnet-5-5-20260928", 1000, None)
    assert cost == DEFAULT_PRICING["claude-sonnet-5-5"]
    cost, _ = estimate_cost("gpt-6-luna:latest", 1000, None)
    assert cost == DEFAULT_PRICING["gpt-6-luna"]


def test_sku_suffixes_do_not_inherit_base_price():
    # -mini/-pro etc. are different SKUs at different prices: never guessed.
    for model in ("gpt-6-luna-mini", "gpt-6.1-sol-pro", "claude-opus-5-5-fast"):
        cost, label = estimate_cost(model, 1000, None)
        assert cost is None, model
        assert label is None, model


def test_no_substring_matching():
    # Regression: the old loop matched anywhere in the string, so a model
    # merely containing a table key inherited its price.
    for model in ("xgpt-6-luna", "my-gpt-6-luna-clone", "prefixclaude-opus-5-5"):
        cost, _ = estimate_cost(model, 1000, None)
        assert cost is None, model


def test_unknown_and_empty_models_are_unpriced():
    for model in ("made-up-model-99", "claude-3-opus", "gpt-4o", ""):
        cost, label = estimate_cost(model, 1000, None)
        assert cost is None, model
        assert label is None, model


def test_override_wins_over_table():
    cost, label = estimate_cost("gpt-6-luna", 1000, 0.01)
    assert cost == 0.01
    assert label == "override@$0.01000/1K"


def test_table_has_no_retired_model_rows():
    # Guard against re-introducing era-gone rows: every shipped key must look
    # like a current-generation id, and retired families are banned outright.
    banned = ("gpt-3.5", "gpt-4", "claude-2", "claude-3", "gemini-1.5", "llama-2")
    for key in DEFAULT_PRICING:
        assert not any(key.startswith(b) or b in key for b in banned), key
        assert DEFAULT_PRICING[key] > 0, key
