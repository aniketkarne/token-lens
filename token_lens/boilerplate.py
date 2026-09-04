"""Boilerplate and positional risk detection.

* Boilerplate ratio: fraction of tokens that are common stop-words, fillers,
  template markers (``{{...}}``), repeated boilerplate phrases, or URLs.
* Positional penalty: applied to the bottom of the chunk list under the
  lost-in-the-middle assumption. Score uses a parabolic weighting that
  penalizes the middle and rewards near the start/end slightly.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Iterable

_FILLER = {
    "the", "a", "an", "and", "or", "but", "if", "then", "of", "to", "in", "on",
    "for", "with", "as", "is", "are", "was", "were", "be", "been", "being",
    "this", "that", "these", "those", "it", "its", "by", "from", "at", "into",
    "about", "over", "under", "than", "so", "such", "also", "too", "very",
}
_URL = re.compile(r"https?://\S+|www\.\S+")
_TEMPLATE = re.compile(r"\{\{[^}]*\}\}|\{[^}]+\}|\[\[[^]]+\]\]")
_WS = re.compile(r"\s+")
_WORD = re.compile(r"\w+", flags=re.UNICODE)


def _tokens(text: str) -> list[str]:
    return [w.lower() for w in _WORD.findall(text)]


def boilerplate_ratio(text: str) -> float:
    """Return fraction of ``text`` that looks like boilerplate / filler."""

    toks = _tokens(text)
    if not toks:
        return 0.0
    counter = Counter(toks)
    boiler = 0
    for tok in toks:
        if tok in _FILLER:
            boiler += 1
        elif len(tok) <= 2:
            boiler += 1
    text_len = max(len(text), 1)
    boiler_chars = 0
    boiler_chars += sum(len(m.group(0)) for m in _URL.finditer(text))
    boiler_chars += sum(len(m.group(0)) for m in _TEMPLATE.finditer(text))
    # Repeated phrase detection: any 3-gram that appears >2 times across text
    trigrams = [tuple(toks[i : i + 3]) for i in range(len(toks) - 2)]
    if trigrams:
        tri_counter = Counter(trigrams)
        repeated = sum(1 for g, c in tri_counter.items() if c >= 2)
        boiler_chars += repeated * 18  # rough weight per repeated 3-gram
    filler_ratio = boiler / len(toks)
    char_ratio = min(1.0, boiler_chars / text_len)
    return max(0.0, min(1.0, 0.6 * filler_ratio + 0.4 * char_ratio))


def positional_penalty(position: int, total: int) -> float:
    """Return a penalty in [0, 1] where 1 = strongest lost-in-middle risk."""

    if total <= 1:
        return 0.0
    # Normalized depth from either edge; 0 at extremes, 1 in the middle
    norm = min(position, total - 1 - position) / ((total - 1) / 2)
    norm = max(0.0, min(1.0, norm))
    # Parabolic: stronger penalty near center
    return norm ** 2


def aggregate_risk(
    chunks: Iterable, threshold: float = 0.55, positional_threshold: float = 0.5
):
    from .types import BoilerplateStats

    flagged = [c for c in chunks if c.boilerplate_ratio >= threshold or c.positional_penalty >= positional_threshold]
    flagged_tokens = sum(c.token_count for c in flagged)
    avg_b = sum(c.boilerplate_ratio for c in chunks) / max(1, sum(1 for _ in chunks))
    avg_p = sum(c.positional_penalty for c in chunks) / max(1, sum(1 for _ in chunks))
    return BoilerplateStats(
        flagged_chunk_count=len(flagged),
        flagged_token_total=flagged_tokens,
        avg_boilerplate_ratio=avg_b,
        avg_positional_penalty=avg_p,
        high_risk=len(flagged) > 0 and (avg_b > 0.5 or avg_p > 0.4),
    )


__all__ = ["boilerplate_ratio", "positional_penalty", "aggregate_risk"]
