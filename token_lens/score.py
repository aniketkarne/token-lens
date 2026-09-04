"""Chunk utilization scoring.

Three normalized scorers (each in [0, 1]):

  * n-gram overlap (Jaccard over word n-grams of size 1..3)
  * longest-common-subsequence ratio (LCS / max(len(query), len(chunk)))
  * containment (fraction of chunk tokens also in the query)

The final score is the maximum of the three (best-of-three) and tagged with
the method that produced it. All scorers operate on whitespace- and
case-normalized text.
"""

from __future__ import annotations

import re
from typing import Iterable

_WORD = re.compile(r"\w+", flags=re.UNICODE)


def _normalize(text: str) -> list[str]:
    return [w.lower() for w in _WORD.findall(text)]


def _ngrams(tokens: list[str], n: int) -> set[tuple[str, ...]]:
    return {tuple(tokens[i : i + n]) for i in range(0, max(0, len(tokens) - n + 1))}


def ngram_overlap(query: str, chunk: str) -> float:
    """Jaccard over n-gram sets (n=1..3). 0 if both sides empty."""

    qt = _normalize(query)
    ct = _normalize(chunk)
    if not qt and not ct:
        return 0.0
    grams_q: set[tuple[str, ...]] = set()
    grams_c: set[tuple[str, ...]] = set()
    for n in (1, 2, 3):
        grams_q |= _ngrams(qt, n)
        grams_c |= _ngrams(ct, n)
    if not grams_q and not grams_c:
        return 0.0
    inter = len(grams_q & grams_c)
    union = len(grams_q | grams_c) or 1
    return inter / union


def lcs_ratio(query: str, chunk: str) -> float:
    """LCS length divided by max(len(q), len(c))."""

    a = _normalize(query)
    b = _normalize(chunk)
    if not a or not b:
        return 0.0
    # Compact LCS via rolling rows; O(min(n,m)*m)
    if len(a) < len(b):
        a, b = b, a
    prev = [0] * (len(b) + 1)
    curr = [0] * (len(b) + 1)
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            if a[i - 1] == b[j - 1]:
                curr[j] = prev[j - 1] + 1
            else:
                curr[j] = max(prev[j], curr[j - 1])
        prev, curr = curr, prev
    lcs_len = prev[-1]
    return lcs_len / max(len(a), len(b))


def containment(query: str, chunk: str) -> float:
    """Fraction of chunk tokens that appear at least once in the query."""

    qt = set(_normalize(query))
    ct = _normalize(chunk)
    if not ct:
        return 0.0
    if not qt:
        return 0.0
    hits = sum(1 for t in ct if t in qt)
    return hits / len(ct)


def best_score(query: str, chunk: str) -> tuple[float, str]:
    """Return (score, method) where score is max of the three scorers."""

    s_ng = ngram_overlap(query, chunk)
    s_lcs = lcs_ratio(query, chunk)
    s_co = containment(query, chunk)
    best = max(s_ng, s_lcs, s_co)
    if best == s_ng and best > 0:
        return s_ng, "ngram"
    if best == s_lcs and best > 0:
        return s_lcs, "lcs"
    if best == s_co and best > 0:
        return s_co, "containment"
    return best, "ngram"


__all__ = ["ngram_overlap", "lcs_ratio", "containment", "best_score"]
