"""Tests for BudgetConfig dataclass and YAML loader."""
from __future__ import annotations

import textwrap

import pytest

from token_lens.budget import BudgetConfig, load_budget


def test_load_budget_parses_yaml(tmp_path):
    cfg = tmp_path / "tl.yaml"
    cfg.write_text(textwrap.dedent("""
        budgets:
          total_tokens: 1000
          zones:
            rag: 400
            history: 300
          cost_usd: 0.01
    """))
    b = load_budget(str(cfg))
    assert b.total_tokens == 1000
    assert b.zones["rag"] == 400
    assert b.zones["history"] == 300
    assert b.cost_usd == 0.01


def test_load_budget_handles_missing_optional_fields(tmp_path):
    cfg = tmp_path / "tl.yaml"
    cfg.write_text("budgets:\n  total_tokens: 500\n")
    b = load_budget(str(cfg))
    assert b.total_tokens == 500
    assert b.zones == {}
    assert b.cost_usd is None


def test_load_budget_accepts_empty_yaml(tmp_path):
    cfg = tmp_path / "tl.yaml"
    cfg.write_text("")
    b = load_budget(str(cfg))
    assert b.total_tokens is None
    assert b.zones == {}
    assert b.cost_usd is None


def test_load_budget_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        load_budget("/nonexistent/path/tl.yaml")


def test_load_budget_top_level_or_nested(tmp_path):
    cfg1 = tmp_path / "tl_nested.yaml"
    cfg1.write_text(textwrap.dedent("""
        budgets:
          total_tokens: 1000
    """))
    b1 = load_budget(str(cfg1))
    assert b1.total_tokens == 1000

    cfg2 = tmp_path / "tl_top.yaml"
    cfg2.write_text("total_tokens: 2000\n")
    b2 = load_budget(str(cfg2))
    assert b2.total_tokens == 2000