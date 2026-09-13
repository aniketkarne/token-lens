"""Tests for budget breach detection against an AnalysisReport."""
from token_lens.budget import BudgetConfig, check_budget, BudgetBreach
from token_lens.types import (
    AnalysisReport,
    BoilerplateStats,
    ZoneBreakdown,
    ZoneKind,
)


def _minimal_report(*, total_tokens=1500, zones=None, cost_usd=None):
    return AnalysisReport(
        model="gpt-4o",
        encoder_label="cl100k_base",
        tokenizer_source="tiktoken",
        total_tokens=total_tokens,
        total_chars=total_tokens * 4,
        message_count=2,
        estimated_cost_usd=cost_usd,
        cost_model_label="openai:gpt-4o" if cost_usd is not None else None,
        zones=zones if zones is not None else [
            ZoneBreakdown(zone=ZoneKind.SYSTEM, message_count=1, token_count=500, char_count=2000, pct_of_total=0.5),
            ZoneBreakdown(zone=ZoneKind.RAG, message_count=3, token_count=600, char_count=2400, pct_of_total=0.4),
            ZoneBreakdown(zone=ZoneKind.USER, message_count=1, token_count=400, char_count=1600, pct_of_total=0.1),
        ],
        chunks=[],
        messages=[],
        boilerplate=BoilerplateStats(
            flagged_chunk_count=0,
            flagged_token_total=0,
            avg_boilerplate_ratio=0.0,
            avg_positional_penalty=0.0,
            high_risk=False,
        ),
        config={},
    )


def test_check_budget_detects_total_tokens_overage():
    cfg = BudgetConfig(total_tokens=1000)
    rep = _minimal_report(total_tokens=1500)
    breaches = check_budget(cfg, rep)
    assert "total_tokens" in {b.code for b in breaches}


def test_check_budget_detects_zone_overage():
    cfg = BudgetConfig(zones={"rag": 500})
    rep = _minimal_report()
    breaches = check_budget(cfg, rep)
    assert "rag" in {b.code for b in breaches}


def test_check_budget_detects_cost_overage():
    cfg = BudgetConfig(cost_usd=0.01)
    rep = _minimal_report(cost_usd=0.05)
    breaches = check_budget(cfg, rep)
    assert "cost_usd" in {b.code for b in breaches}


def test_check_budget_returns_empty_when_under_all_limits():
    cfg = BudgetConfig(total_tokens=10000, zones={"rag": 1000}, cost_usd=0.10)
    rep = _minimal_report(total_tokens=1500, cost_usd=0.05)
    assert check_budget(cfg, rep) == []


def test_check_budget_multiple_breaches_at_once():
    cfg = BudgetConfig(total_tokens=1000, zones={"rag": 500}, cost_usd=0.01)
    rep = _minimal_report(total_tokens=1500, cost_usd=0.05)
    breaches = check_budget(cfg, rep)
    codes = {b.code for b in breaches}
    assert "total_tokens" in codes and "rag" in codes and "cost_usd" in codes
    assert len(breaches) == 3


def test_budget_breach_dataclass_fields():
    cfg = BudgetConfig(total_tokens=1000)
    rep = _minimal_report(total_tokens=1500)
    breaches = check_budget(cfg, rep)
    assert len(breaches) == 1
    b = breaches[0]
    assert isinstance(b, BudgetBreach)
    assert b.code == "total_tokens"
    assert b.actual == 1500
    assert b.limit == 1000
    assert b.severity == "error"