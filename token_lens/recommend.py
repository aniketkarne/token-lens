"""Actionable, savings-first recommendations derived from an ``AnalysisReport``.

The recommendations are *heuristics* with explicit thresholds. They are designed
to be obvious, mechanical, and cheap to apply — they do not call any model and
they do not touch the network. Each recommendation carries:

* a ``kind`` — short identifier (``drop_low_score_chunks`` etc.)
* a ``zone`` — the ``ZoneKind`` that the recommendation targets
* an estimated token savings (best-effort, rounded, defensive)
* an estimated dollar savings when a cost is known
* a ``why`` — a one-line justification based on the report data
* a ``how`` — concrete instructions for applying it

The function :func:`build_recommendations` is the public entry point. It is
pure (no I/O, no globals) and returns a list of :class:`Recommendation`
objects sorted by estimated token savings (descending).

No runtime dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, List

from .boilerplate import aggregate_risk
from .types import AnalysisReport, ZoneKind


# ---------------------------------------------------------------------------
# Public dataclass
# ---------------------------------------------------------------------------


@dataclass
class Recommendation:
    """One concrete, mechanical change a user can apply to the prompt."""

    kind: str
    title: str
    zone: str  # ZoneKind.value
    estimated_savings_tokens: int
    estimated_savings_usd: float | None
    confidence: str  # "high" | "medium" | "low"
    why: str
    how: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "title": self.title,
            "zone": self.zone,
            "estimated_savings_tokens": self.estimated_savings_tokens,
            "estimated_savings_usd": (
                round(self.estimated_savings_usd, 6)
                if self.estimated_savings_usd is not None
                else None
            ),
            "confidence": self.confidence,
            "why": self.why,
            "how": self.how,
        }


# ---------------------------------------------------------------------------
# Heuristic thresholds — explicit and conservative
# ---------------------------------------------------------------------------


#: Chunks scoring below this n-gram/LCS/containment score are weak matches.
_WEAK_CHUNK_THRESHOLD = 0.20

#: Chunks with boilerplate ratio above this are considered filler-heavy.
_BOILERPLATE_CHUNK_THRESHOLD = 0.55

#: Zones above this share of total tokens are candidates for trimming.
_LARGE_ZONE_PCT = 0.30

#: Tool schemas above this token count are flagged as oversized.
_LARGE_TOOL_SCHEMA_TOKENS = 600

#: History zones above this token count are flagged for summarization.
_LARGE_HISTORY_TOKENS = 1500

#: If few-shot examples exceed this token count we recommend trimming a few.
_LARGE_FEW_SHOT_TOKENS = 800


def _zone_report(report: AnalysisReport, kind: ZoneKind):
    """Return the ZoneBreakdown for ``kind`` or ``None``."""

    return report.zone(kind)


def _zone_tokens(report: AnalysisReport, kind: ZoneKind) -> int:
    zb = _zone_report(report, kind)
    return zb.token_count if zb else 0


def _zone_pct(report: AnalysisReport, kind: ZoneKind) -> float:
    zb = _zone_report(report, kind)
    return zb.pct_of_total if zb else 0.0


def _cost_per_token(report: AnalysisReport) -> float | None:
    """Return USD per token for the active cost model, or None if unknown."""

    if report.estimated_cost_usd is None or report.total_tokens <= 0:
        return None
    return report.estimated_cost_usd / report.total_tokens


def _savings(rec_tokens: int, cpt: float | None) -> float | None:
    if cpt is None:
        return None
    return round(rec_tokens * cpt, 6)


# ---------------------------------------------------------------------------
# Individual rule engines
# ---------------------------------------------------------------------------


def _rec_drop_low_score_chunks(
    report: AnalysisReport, cpt: float | None
) -> List[Recommendation]:
    """Recommend dropping RAG chunks that don't actually relate to the query."""

    if not report.chunks:
        return []
    weak = [c for c in report.chunks if c.score < _WEAK_CHUNK_THRESHOLD]
    if not weak:
        return []
    tokens = sum(c.token_count for c in weak)
    if tokens <= 0:
        return []
    sample_idx = weak[0].index
    how = (
        "Re-rank or filter your retriever: drop chunks with score < "
        f"{_WEAK_CHUNK_THRESHOLD:.2f}; start with index #{sample_idx}."
    )
    return [
        Recommendation(
            kind="drop_low_score_chunks",
            title=f"Drop {len(weak)} low-scoring RAG chunk(s)",
            zone=ZoneKind.RAG.value,
            estimated_savings_tokens=tokens,
            estimated_savings_usd=_savings(tokens, cpt),
            confidence="high" if len(weak) >= 2 else "medium",
            why=(
                f"{len(weak)} of {len(report.chunks)} RAG chunks score below "
                f"{_WEAK_CHUNK_THRESHOLD:.2f} vs. your last user query "
                f"(best-of n-gram/LCS/containment)."
            ),
            how=how,
        )
    ]


def _rec_drop_high_boilerplate(
    report: AnalysisReport, cpt: float | None
) -> List[Recommendation]:
    """Recommend dropping chunks that are mostly stop-words / URLs / templates."""

    if not report.chunks:
        return []
    heavy = [c for c in report.chunks if c.boilerplate_ratio >= _BOILERPLATE_CHUNK_THRESHOLD]
    if not heavy:
        return []
    tokens = sum(c.token_count for c in heavy)
    if tokens <= 0:
        return []
    pct = sum(c.boilerplate_ratio for c in heavy) / len(heavy)
    return [
        Recommendation(
            kind="drop_high_boilerplate_chunks",
            title=f"Refactor {len(heavy)} filler-heavy RAG chunk(s)",
            zone=ZoneKind.RAG.value,
            estimated_savings_tokens=tokens,
            estimated_savings_usd=_savings(tokens, cpt),
            confidence="medium",
            why=(
                f"{len(heavy)} chunk(s) average {pct * 100:.0f}% boilerplate "
                "(stop-words/URLs/templates/repeated n-grams)."
            ),
            how=(
                "Replace each flagged chunk with a 2-3 sentence summary or drop "
                "it; URLs and templated filler consume tokens without evidence."
            ),
        )
    ]


def _rec_move_middle_chunks(report: AnalysisReport, cpt: float | None):
    """In long-context RAG lists, the middle is least attended."""
    if not report.chunks or len(report.chunks) < 5:
        return []
    n = len(report.chunks)
    middle = [
        c
        for c in report.chunks
        if min(c.position, n - 1 - c.position) >= n // 4
    ]
    if len(middle) < 2:
        return []
    tokens = sum(c.token_count for c in middle)
    if tokens <= 0:
        return []
    return [
        Recommendation(
            kind="reorder_around_lost_in_middle",
            title=f"Re-order or trim {len(middle)} middle RAG chunk(s)",
            zone=ZoneKind.RAG.value,
            estimated_savings_tokens=tokens,
            estimated_savings_usd=_savings(tokens, cpt),
            confidence="low",
            why=(
                f"With {n} chunks, the {len(middle)} middle ones (positions "
                f"{middle[0].position}..{middle[-1].position}) suffer from "
                "the 'lost-in-the-middle' effect and contribute little."
            ),
            how=(
                "Re-rank your retriever to put the most relevant chunks first "
                "and last; or cap the list to top-3."
            ),
        )
    ]


def _rec_shorten_history(report: AnalysisReport, cpt: float | None):
    """Suggest summarizing or pruning long chat history."""
    toks = _zone_tokens(report, ZoneKind.HISTORY)
    if toks < _LARGE_HISTORY_TOKENS:
        return []
    pct = _zone_pct(report, ZoneKind.HISTORY)
    # Propose ~60% reduction: aggressive but common with summarization.
    save = int(toks * 0.6)
    if save <= 0:
        return []
    return [
        Recommendation(
            kind="summarize_history",
            title="Summarize or window the chat history",
            zone=ZoneKind.HISTORY.value,
            estimated_savings_tokens=save,
            estimated_savings_usd=_savings(save, cpt),
            confidence="medium",
            why=(
                f"history zone is {toks} tokens ({pct * 100:.0f}% of total), "
                "well above the 1,500-token soft budget."
            ),
            how=(
                "Replace verbatim history with a 3-5 bullet rolling summary; "
                "keep only the last user/assistant turn verbatim."
            ),
        )
    ]


def _rec_trim_tool_schema(report: AnalysisReport, cpt: float | None):
    """Suggest tightening oversized tool/function schemas."""
    msgs = [m for m in report.messages if m.zone == ZoneKind.TOOL_SCHEMA]
    if not msgs:
        return []
    toks = sum(m.token_count for m in msgs)
    if toks < _LARGE_TOOL_SCHEMA_TOKENS:
        return []
    save = int(toks * 0.4)
    if save <= 0:
        return []
    return [
        Recommendation(
            kind="trim_tool_schema",
            title="Tighten tool/function schemas",
            zone=ZoneKind.TOOL_SCHEMA.value,
            estimated_savings_tokens=save,
            estimated_savings_usd=_savings(save, cpt),
            confidence="medium",
            why=(
                f"tool schema zone is {toks} tokens; verbose descriptions and "
                "examples inflate every request."
            ),
            how=(
                "Shorten tool descriptions to one sentence; drop optional "
                "parameters; remove redundant examples from JSON Schema."
            ),
        )
    ]


def _rec_trim_few_shot(report: AnalysisReport, cpt: float | None):
    """Suggest dropping or shrinking few-shot examples when zone is large."""
    toks = _zone_tokens(report, ZoneKind.FEW_SHOT)
    if toks < _LARGE_FEW_SHOT_TOKENS:
        return []
    save = int(toks * 0.5)
    if save <= 0:
        return []
    return [
        Recommendation(
            kind="trim_few_shot",
            title="Trim few-shot examples",
            zone=ZoneKind.FEW_SHOT.value,
            estimated_savings_tokens=save,
            estimated_savings_usd=_savings(save, cpt),
            confidence="low",
            why=(
                f"few_shot zone is {toks} tokens; modern chat models rarely "
                "need more than 1-2 worked examples."
            ),
            how=(
                "Keep the 1-2 highest-signal examples; drop the rest, or move "
                "them to a system-prompt footnote."
            ),
        )
    ]


def _rec_shorten_system(report: AnalysisReport, cpt: float | None):
    """Flag bloated system prompts that exceed the budget."""
    toks = _zone_tokens(report, ZoneKind.SYSTEM)
    if toks < 800:
        return []
    save = int(toks * 0.25)
    if save <= 0:
        return []
    return [
        Recommendation(
            kind="shorten_system_prompt",
            title="Tighten the system prompt",
            zone=ZoneKind.SYSTEM.value,
            estimated_savings_tokens=save,
            estimated_savings_usd=_savings(save, cpt),
            confidence="low",
            why=(
                f"system zone is {toks} tokens; long instruction lists "
                "degrade after the first ~20 lines."
            ),
            how=(
                "Consolidate bullets into a single short paragraph; remove "
                "redundant safety boilerplate if already covered by the API."
            ),
        )
    ]


def _rec_high_boilerplate_global(report: AnalysisReport, cpt: float | None):
    """If the aggregate boilerplate risk is high, recommend a global sweep."""
    if not report.boilerplate.high_risk:
        return []
    avg_b = report.boilerplate.avg_boilerplate_ratio
    # Avoid double-counting: only fire if no per-chunk rule already fired.
    # We estimate globally as flagged tokens * 0.5 (we already cheaply
    # trimmed weak chunks above, so use remaining flagged tokens).
    flagged = report.boilerplate.flagged_token_total
    if flagged <= 0:
        return []
    save = int(flagged * 0.3)
    if save <= 0:
        return []
    return [
        Recommendation(
            kind="global_boilerplate_sweep",
            title="Run a boilerplate sweep across RAG + history",
            zone=ZoneKind.RAG.value,
            estimated_savings_tokens=save,
            estimated_savings_usd=_savings(save, cpt),
            confidence="low",
            why=(
                f"Average boilerplate ratio is {avg_b * 100:.0f}% across the "
                "prompt; lost-in-the-middle and filler are piling up."
            ),
            how=(
                "Strip URLs/stop-words from retrieved chunks; rewrite history "
                "as bullets; dedupe repeated phrases."
            ),
        )
    ]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def build_recommendations(report: AnalysisReport) -> list[Recommendation]:
    """Return a list of :class:`Recommendation` sorted by savings desc."""

    cpt = _cost_per_token(report)
    recs: list[Recommendation] = []
    recs.extend(_rec_drop_low_score_chunks(report, cpt))
    recs.extend(_rec_drop_high_boilerplate(report, cpt))
    recs.extend(_rec_move_middle_chunks(report, cpt))
    recs.extend(_rec_shorten_history(report, cpt))
    recs.extend(_rec_trim_tool_schema(report, cpt))
    recs.extend(_rec_trim_few_shot(report, cpt))
    recs.extend(_rec_shorten_system(report, cpt))
    recs.extend(_rec_high_boilerplate_global(report, cpt))
    recs.sort(key=lambda r: r.estimated_savings_tokens, reverse=True)
    return recs


def total_estimated_savings(recs: Iterable[Recommendation]) -> tuple[int, float | None]:
    """Return ``(tokens_saved, usd_saved_or_None)`` for an iterable of recs."""

    tokens = sum(r.estimated_savings_tokens for r in recs)
    usd_total: float | None = 0.0
    saw_usd = False
    for r in recs:
        if r.estimated_savings_usd is None:
            continue
        saw_usd = True
        usd_total = (usd_total or 0.0) + r.estimated_savings_usd
    return tokens, (usd_total if saw_usd else None)


__all__ = [
    "Recommendation",
    "build_recommendations",
    "total_estimated_savings",
]
