"""Tests for TokenizerBackend enum and AnalysisReport tokenizer fields."""
from token_lens.types import (
    TokenizerBackend,
    AnalysisReport,
    BoilerplateStats,
)


def _minimal_report(**overrides):
    """Build a valid AnalysisReport with sensible defaults for the new tokenizer fields."""
    kwargs = dict(
        model="gpt-4o",
        encoder_label="cl100k_base",
        tokenizer_source="tiktoken",
        total_tokens=10,
        total_chars=40,
        message_count=2,
        estimated_cost_usd=0.001,
        cost_model_label="openai:gpt-4o",
        zones=[],
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


def test_tokenizer_backend_values():
    assert TokenizerBackend.TIKTOKEN.value == "tiktoken"
    assert TokenizerBackend.HUGGINGFACE.value == "huggingface"
    assert TokenizerBackend.CUSTOM.value == "custom"
    assert TokenizerBackend.HEURISTIC.value == "heuristic"


def test_analysis_report_carries_backend():
    r = _minimal_report(
        tokenizer_backend=TokenizerBackend.TIKTOKEN,
        tokenizer_name="cl100k_base",
        is_approximate=False,
    )
    assert r.tokenizer_backend == TokenizerBackend.TIKTOKEN
    assert r.tokenizer_name == "cl100k_base"
    assert r.is_approximate is False


def test_analysis_report_defaults_to_heuristic():
    """Existing callers construct AnalysisReport without tokenizer args. Defaults must keep them working."""
    r = _minimal_report()
    assert r.tokenizer_backend == TokenizerBackend.HEURISTIC
    assert r.is_approximate is True
    assert isinstance(r.tokenizer_name, str) and r.tokenizer_name


def test_legacy_tokenizer_source_field_unchanged():
    """The pre-existing tokenizer_source: str field must still exist alongside the new enum."""
    r = _minimal_report(tokenizer_source="transformers")
    assert r.tokenizer_source == "transformers"
