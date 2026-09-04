"""Tokenizer adapters.

Tries, in order:
  1. tiktoken (if installed and model name matches)
  2. transformers AutoTokenizer (if installed and model identifier matches)
  3. Deterministic heuristic fallback (whitespace + BPE-lite byte-pair approximation)

The heuristic is intentionally deterministic: given identical input it returns
the same token count every run, so reports are reproducible across machines
without provider dependencies.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Iterable

# ----- provider tokenizers ----------------------------------------------------


_TIKTOKEN_MODEL_ALIASES = {
    "gpt-4": "cl100k_base",
    "gpt-4o": "o200k_base",
    "gpt-4o-mini": "o200k_base",
    "gpt-3.5-turbo": "cl100k_base",
    "claude": "cl100k_base",
    "claude-3": "cl100k_base",
}


def _try_tiktoken(model: str) -> tuple[Callable[[str], list[str]], str] | None:
    try:
        import tiktoken  # type: ignore
    except Exception:
        return None
    name = _TIKTOKEN_MODEL_ALIASES.get(model.lower(), None)
    if name is None:
        # Try to find a matching encoding directly
        try:
            enc = tiktoken.encoding_for_model(model)
            return (lambda s: [enc.decode([t]) for t in enc.encode(s)]), f"tiktoken:{enc.name}"
        except Exception:
            return None
    try:
        enc = tiktoken.get_encoding(name)
    except Exception:
        return None
    return (lambda s: [enc.decode([t]) for t in enc.encode(s)]), f"tiktoken:{name}"


def _try_transformers(model: str) -> tuple[Callable[[str], list[str]], str] | None:
    try:
        from transformers import AutoTokenizer  # type: ignore
    except Exception:
        return None
    try:
        tok = AutoTokenizer.from_pretrained(model)
    except Exception:
        return None

    def encode(s: str) -> list[str]:
        ids = tok.encode(s, add_special_tokens=False)
        return tok.convert_ids_to_tokens(ids)

    return encode, f"transformers:{model}"


# ----- deterministic heuristic fallback ---------------------------------------


_WS = re.compile(r"\s+")
_WORD = re.compile(r"\w+|[^\w\s]")


def _heuristic_tokens(text: str) -> list[str]:
    """Approximate BPE-lite tokenization.

    Splits on word/punctuation boundaries, then further splits any token longer
    than 12 characters into ~6-char chunks. Adds a 1-token overhead per message
    boundary by leaving a sentinel "" between segments.
    """

    if not text:
        return []
    tokens: list[str] = []
    for m in _WORD.finditer(text):
        tok = m.group(0)
        if len(tok) <= 12:
            tokens.append(tok)
        else:
            # crude byte-pair-ish split
            step = 6
            for i in range(0, len(tok), step):
                tokens.append(tok[i : i + step])
    return tokens


# ----- facade -----------------------------------------------------------------


@dataclass
class TokenEncoder:
    """A resolved encoder with metadata about its provenance."""

    name: str
    source: str
    encode: Callable[[str], list[str]]
    count: Callable[[str], int]

    def tokenize(self, text: str) -> list[str]:
        return self.encode(text)

    def tokens(self, text: str) -> int:
        return self.count(text)


def resolve_encoder(model: str | None) -> TokenEncoder:
    """Pick the best available encoder for ``model``.

    Falls back deterministically if no provider tokenizer is available.
    """

    if model:
        for factory in (_try_tiktoken, _try_transformers):
            res = factory(model)
            if res is not None:
                enc_fn, label = res
                return TokenEncoder(
                    name=label,
                    source=label.split(":")[0],
                    encode=enc_fn,
                    count=lambda s, _f=enc_fn: len(_f(s)),
                )

    enc = _heuristic_tokens
    return TokenEncoder(
        name="heuristic-bpe-lite",
        source="fallback",
        encode=enc,
        count=lambda s: len(enc(s)),
    )


__all__ = ["resolve_encoder", "TokenEncoder", "_heuristic_tokens"]
