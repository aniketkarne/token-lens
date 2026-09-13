"""Tests for tokenizer backend display in rendered reports."""
from token_lens.report import render_html
from token_lens.types import (
    AnalysisReport,
    BoilerplateStats,
    TokenizerBackend,
    ZoneKind,
    ZoneBreakdown,
)


def _minimal_report(**overrides):
    kwargs = dict(
        model="gpt-4o",
        encoder_label="cl100k_base",
        tokenizer_source="tiktoken",
        total_tokens=100,
        total_chars=400,
        message_count=2,
        estimated_cost_usd=0.001,
        cost_model_label="openai:gpt-4o",
        zones=[
            ZoneBreakdown(zone=ZoneKind.SYSTEM, message_count=1, token_count=60, char_count=240, pct_of_total=0.6),
            ZoneBreakdown(zone=ZoneKind.USER, message_count=1, token_count=40, char_count=160, pct_of_total=0.4),
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
    kwargs.update(overrides)
    return AnalysisReport(**kwargs)


def test_html_report_shows_tokenizer_backend_name():
    r = _minimal_report(
        tokenizer_backend=TokenizerBackend.TIKTOKEN,
        tokenizer_name="cl100k_base",
        is_approximate=False,
    )
    html = render_html(r)
    assert "cl100k_base" in html
    assert "approximate" not in html.lower()


def test_html_report_shows_approximate_badge_when_fallback():
    r = _minimal_report(
        tokenizer_backend=TokenizerBackend.HEURISTIC,
        tokenizer_name="heuristic-bpe-lite",
        is_approximate=True,
    )
    html = render_html(r)
    assert "heuristic" in html.lower()
    assert "approximate" in html.lower() or "⚠" in html


def test_html_report_shows_huggingface_backend_label():
    r = _minimal_report(
        tokenizer_backend=TokenizerBackend.HUGGINGFACE,
        tokenizer_name="bert-base-uncased",
        is_approximate=False,
    )
    html = render_html(r)
    assert "bert-base-uncased" in html


def test_html_report_shows_custom_backend_label():
    r = _minimal_report(
        tokenizer_backend=TokenizerBackend.CUSTOM,
        tokenizer_name="my-tokenizer.json",
        is_approximate=False,
    )
    html = render_html(r)
    assert "my-tokenizer.json" in html


def test_to_dict_includes_new_tokenizer_fields():
    r = _minimal_report(
        tokenizer_backend=TokenizerBackend.TIKTOKEN,
        tokenizer_name="cl100k_base",
        is_approximate=False,
    )
    d = r.to_dict()
    assert d["tokenizer_backend"] == "tiktoken"
    assert d["tokenizer_name"] == "cl100k_base"
    assert d["is_approximate"] is False


def test_to_dict_tokenizer_backend_serializes_as_string():
    r = _minimal_report(
        tokenizer_backend=TokenizerBackend.HEURISTIC,
        tokenizer_name="heuristic-bpe-lite",
        is_approximate=True,
    )
    d = r.to_dict()
    assert d["tokenizer_backend"] == "heuristic"
    assert isinstance(d["tokenizer_backend"], str)
