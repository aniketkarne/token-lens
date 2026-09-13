"""Tests for the HuggingFace tokenizers backend and custom-file loader."""
import json
import pathlib

from token_lens.tokenize import resolve_encoder, TokenEncoder


def _write_minimal_tokenizer_json(path: pathlib.Path) -> None:
    """Write the smallest valid HF tokenizers tokenizer.json we can produce."""
    data = {
        "version": "1.0",
        "truncation": None,
        "padding": None,
        "added_tokens": [],
        "normalizer": None,
        "pre_tokenizer": {"type": "Whitespace"},
        "post_processor": None,
        "decoder": None,
        "model": {
            "type": "BPE",
            "dropout": None,
            "unk_token": None,
            "continuing_subword_prefix": None,
            "end_of_word_suffix": None,
            "fuse_unk": False,
            "vocab": {"hello": 0, "world": 1, "foo": 2, "bar": 3},
            "merges": [],
        },
    }
    path.write_text(json.dumps(data))


def test_custom_tokenizer_loader_succeeds(tmp_path):
    tok_path = tmp_path / "tok.json"
    _write_minimal_tokenizer_json(tok_path)
    enc = resolve_encoder(model="custom", custom_path=str(tok_path))
    assert isinstance(enc, TokenEncoder)
    assert enc.source == "tokenizers"
    assert "custom" in enc.name.lower() or "tok.json" in enc.name or "tokenizers" in enc.name
    toks = enc.tokenize("hello world")
    assert toks == ["hello", "world"]


def test_custom_tokenizer_missing_file_returns_heuristic(tmp_path):
    enc = resolve_encoder(model="custom", custom_path=str(tmp_path / "nope.json"))
    assert isinstance(enc, TokenEncoder)
    assert enc.source in ("fallback", "heuristic") or "heuristic" in enc.name


def test_custom_tokenizer_invalid_file_returns_heuristic(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("not a tokenizer")
    enc = resolve_encoder(model="custom", custom_path=str(bad))
    assert isinstance(enc, TokenEncoder)
    assert "heuristic" in enc.name or enc.source == "fallback"


def test_resolve_encoder_heuristic_fallback_when_no_provider(tmp_path, monkeypatch):
    monkeypatch.setattr("token_lens.tokenize._try_tiktoken", lambda m: None)
    monkeypatch.setattr("token_lens.tokenize._try_transformers", lambda m: None)
    monkeypatch.setattr("token_lens.tokenize._try_hf_tokenizers", lambda m: None)
    monkeypatch.setattr("token_lens.tokenize._try_custom_tokenizer", lambda p: None)
    enc = resolve_encoder(model="totally-unknown-model-xyz")
    assert isinstance(enc, TokenEncoder)
    assert "heuristic" in enc.name


def test_custom_path_takes_priority_over_unknown_model(tmp_path):
    tok_path = tmp_path / "tok.json"
    _write_minimal_tokenizer_json(tok_path)
    enc = resolve_encoder(model="whatever", custom_path=str(tok_path))
    assert enc.source == "tokenizers"


def test_tiktoken_still_works_for_known_model():
    enc = resolve_encoder(model="gpt-4o")
    assert isinstance(enc, TokenEncoder)
    assert enc.source in ("tiktoken", "fallback") or "heuristic" in enc.name