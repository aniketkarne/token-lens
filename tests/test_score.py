"""Tests for chunk scoring, boilerplate, and positional penalty."""

from __future__ import annotations

from token_lens.boilerplate import boilerplate_ratio, positional_penalty
from token_lens.score import best_score, containment, lcs_ratio, ngram_overlap


def test_ngram_overlap_identical():
    s = ngram_overlap("apples are red fruits", "apples are red fruits")
    assert s == pytest.approx(1.0)


def test_ngram_overlap_disjoint():
    s = ngram_overlap("apples are red", "bananas are yellow")
    # 1-gram overlap on "are" only -> small but > 0
    assert 0.0 < s < 0.5


def test_ngram_overlap_empty():
    assert ngram_overlap("", "anything") == 0.0
    assert ngram_overlap("anything", "") == 0.0


def test_lcs_ratio_identical():
    assert lcs_ratio("hello world", "hello world") == pytest.approx(1.0)


def test_lcs_ratio_zero_when_disjoint():
    # Single-word each, no common tokens -> 0
    assert lcs_ratio("apples", "bananas") == 0.0


def test_containment_full():
    # Query is a strict superset of the chunk -> every chunk word is contained
    s = containment("apples and bananas are fruits", "apples bananas")
    assert s == pytest.approx(1.0)


def test_containment_zero():
    assert containment("xyz", "apples bananas") == 0.0


def test_best_score_picks_max():
    score, method = best_score("apples are fruits", "apples are tasty fruits")
    assert score > 0.5
    assert method in {"ngram", "lcs", "containment"}


def test_boilerplate_ratio_increases_with_filler():
    clean = "Quantum mechanics describes nature at the smallest scales."
    filler = "The the the the the the the the the the the the."
    assert boilerplate_ratio(filler) > boilerplate_ratio(clean)


def test_boilerplate_ratio_template_markers():
    template = "Hello {{name}}, your order {{order_id}} is ready at {{url}}."
    clean = "Quantum chromodynamics is the theory of strong interactions."
    assert boilerplate_ratio(template) > boilerplate_ratio(clean)


def test_positional_penalty_extremes_low():
    n = 5
    assert positional_penalty(0, n) == 0.0
    assert positional_penalty(n - 1, n) == 0.0


def test_positional_penalty_middle_high():
    n = 5
    assert positional_penalty(2, n) > 0.0


def test_positional_penalty_single_chunk():
    assert positional_penalty(0, 1) == 0.0


# import pytest locally so the linter stays happy
import pytest  # noqa: E402
