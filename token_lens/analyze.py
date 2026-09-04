"""Top-level analyzer: turns a trace into an AnalysisReport."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from .boilerplate import aggregate_risk, boilerplate_ratio, positional_penalty
from .parse import load_trace, parse_trace
from .pricing import estimate_cost
from .score import best_score
from .tokenize import resolve_encoder
from .types import (
    AnalysisReport,
    ChunkInfo,
    MessageRecord,
    ZoneBreakdown,
    ZoneKind,
)


_ZONE_ORDER: list[ZoneKind] = [
    ZoneKind.SYSTEM,
    ZoneKind.TOOL_SCHEMA,
    ZoneKind.FEW_SHOT,
    ZoneKind.RAG,
    ZoneKind.HISTORY,
    ZoneKind.USER,
    ZoneKind.ASSISTANT,
    ZoneKind.UNKNOWN,
]


def _zone_breakdown(messages: list[MessageRecord]) -> list[ZoneBreakdown]:
    total = sum(m.token_count for m in messages) or 1
    by_zone: dict[ZoneKind, dict[str, int]] = {}
    for m in messages:
        d = by_zone.setdefault(m.zone, {"tokens": 0, "chars": 0, "msgs": 0})
        d["tokens"] += m.token_count
        d["chars"] += m.char_count
        d["msgs"] += 1
    out: list[ZoneBreakdown] = []
    for z in _ZONE_ORDER:
        if z not in by_zone:
            continue
        d = by_zone[z]
        out.append(
            ZoneBreakdown(
                zone=z,
                message_count=d["msgs"],
                token_count=d["tokens"],
                char_count=d["chars"],
                pct_of_total=d["tokens"] / total,
            )
        )
    return out


def _find_query_text(messages: list[MessageRecord]) -> str:
    # Use the last user message as the canonical query text. If none, use the
    # last non-system message; otherwise empty.
    for m in reversed(messages):
        if m.zone == ZoneKind.USER:
            return m.content
    for m in reversed(messages):
        if m.zone not in (ZoneKind.SYSTEM, ZoneKind.TOOL_SCHEMA):
            return m.content
    return ""


def _build_chunks(
    messages: list[MessageRecord], encoder
) -> tuple[list[ChunkInfo], str]:
    """Score every RAG / chunk-like message against the inferred query."""

    rag = [m for m in messages if m.zone == ZoneKind.RAG]
    if not rag:
        return [], ""
    query = _find_query_text(messages)
    out: list[ChunkInfo] = []
    for i, m in enumerate(rag):
        score, method = best_score(query, m.content) if query else (0.0, "ngram")
        out.append(
            ChunkInfo(
                index=i,
                text=m.content,
                token_count=m.token_count,
                char_count=m.char_count,
                position=i,
                score=score,
                method=method,
                boilerplate_ratio=boilerplate_ratio(m.content),
                positional_penalty=positional_penalty(i, len(rag)),
            )
        )
    return out, query


def analyze_trace(trace: Any, config: Mapping[str, Any] | None = None) -> AnalysisReport:
    """Analyze an already-parsed trace object."""

    cfg = dict(config or {})
    model = str(cfg.get("model") or (trace.get("model") if isinstance(trace, dict) else "") or "")
    price_override = cfg.get("price_per_1k")

    encoder = resolve_encoder(model)
    warnings: list[str] = []
    messages = parse_trace(trace)
    if not messages:
        warnings.append("No messages parsed from trace.")

    # Tokenize each message
    for m in messages:
        m.token_count = encoder.tokens(m.content)

    total_tokens = sum(m.token_count for m in messages)
    total_chars = sum(m.char_count for m in messages)

    zones = _zone_breakdown(messages)
    chunks, _query = _build_chunks(messages, encoder)
    boiler = aggregate_risk(chunks) if chunks else aggregate_risk([])

    cost, cost_label = estimate_cost(model, total_tokens, price_override)

    return AnalysisReport(
        model=model,
        encoder_label=encoder.name,
        tokenizer_source=encoder.source,
        total_tokens=total_tokens,
        total_chars=total_chars,
        message_count=len(messages),
        estimated_cost_usd=cost,
        cost_model_label=cost_label,
        zones=zones,
        chunks=chunks,
        messages=messages,
        boilerplate=boiler,
        config=cfg,
        warnings=warnings,
    )


def analyze_file(path: str | Path, config: Mapping[str, Any] | None = None) -> AnalysisReport:
    """Load and analyze a JSON trace file."""

    return analyze_trace(load_trace(path), config=config)


__all__ = ["analyze_trace", "analyze_file"]
