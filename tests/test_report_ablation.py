"""Tests for RAG ablation rendering in HTML reports."""
from token_lens.report import render_html
from token_lens.types import (
    AnalysisReport,
    AblationResult,
    BoilerplateStats,
    ChunkUsefulness,
    TokenizerBackend,
    ZoneKind,
    ZoneBreakdown,
)


def _minimal_report(*, ablation):
    return AnalysisReport(
        model="gpt-4o",
        encoder_label="cl100k_base",
        tokenizer_source="tiktoken",
        total_tokens=2000,
        total_chars=8000,
        message_count=4,
        estimated_cost_usd=0.01,
        cost_model_label="openai:gpt-4o",
        zones=[
            ZoneBreakdown(zone=ZoneKind.SYSTEM, message_count=3, token_count=1800, char_count=7200, pct_of_total=0.9),
            ZoneBreakdown(zone=ZoneKind.USER, message_count=1, token_count=200, char_count=800, pct_of_total=0.1),
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
        ablation=ablation,
    )


def test_html_report_renders_ablation_when_present():
    ablation = AblationResult(
        chunks=[
            ChunkUsefulness(index=0, chunk_id="rag-1", tokens=812, query_similarity=0.71, redundancy=0.2, usefulness=0.6, verdict="useful"),
            ChunkUsefulness(index=1, chunk_id="rag-2", tokens=744, query_similarity=0.2, redundancy=0.1, usefulness=0.18, verdict="irrelevant"),
        ],
        potential_removal_tokens=744,
        estimated_quality_delta=-0.05,
    )
    rep = _minimal_report(ablation=ablation)
    html = render_html(rep)
    assert "RAG context" in html
    assert "rag-1" in html
    assert "rag-2" in html
    assert "useful" in html
    assert "irrelevant" in html


def test_html_report_omits_ablation_section_when_none():
    rep = _minimal_report(ablation=None)
    html = render_html(rep)
    assert "RAG context" not in html


def test_html_report_shows_potential_removal_summary():
    ablation = AblationResult(
        chunks=[
            ChunkUsefulness(index=0, chunk_id="rag-1", tokens=500, query_similarity=0.1, redundancy=0.0, usefulness=0.1, verdict="irrelevant"),
        ],
        potential_removal_tokens=500,
        estimated_quality_delta=-0.05,
    )
    rep = _minimal_report(ablation=ablation)
    html = render_html(rep)
    assert "500" in html
    assert "potential_removal" in html.lower() or "removal" in html.lower()


def test_html_report_renders_chunk_with_no_chunk_id():
    ablation = AblationResult(
        chunks=[
            ChunkUsefulness(index=0, chunk_id=None, tokens=100, query_similarity=0.5, redundancy=0.0, usefulness=0.5, verdict="useful"),
        ],
        potential_removal_tokens=0,
        estimated_quality_delta=0.0,
    )
    rep = _minimal_report(ablation=ablation)
    html = render_html(rep)
    assert "RAG context" in html
    assert "-" in html or "no id" in html.lower() or "(no" in html.lower()
