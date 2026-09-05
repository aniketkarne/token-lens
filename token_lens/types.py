"""Typed data structures for token-lens."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


class ZoneKind(str, Enum):
    """Classification of a prompt segment."""

    SYSTEM = "system"
    FEW_SHOT = "few_shot"
    HISTORY = "history"
    TOOL_SCHEMA = "tool_schema"
    RAG = "rag"
    USER = "user"
    ASSISTANT = "assistant"
    UNKNOWN = "unknown"


@dataclass
class MessageRecord:
    """A single prompt message after parsing."""

    index: int
    role: str
    content: str
    zone: ZoneKind
    source: str  # raw origin tag (e.g., "messages[3]")
    token_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def char_count(self) -> int:
        return len(self.content)


@dataclass
class ZoneBreakdown:
    """Per-zone aggregate statistics."""

    zone: ZoneKind
    message_count: int
    token_count: int
    char_count: int
    pct_of_total: float


@dataclass
class ChunkInfo:
    """A scored chunk (e.g., a RAG chunk) relative to a query."""

    index: int
    text: str
    token_count: int
    char_count: int
    position: int  # ordinal within the zone (0-based)
    score: float  # normalized 0..1
    method: str  # "ngram" | "lcs" | "containment"
    boilerplate_ratio: float = 0.0
    positional_penalty: float = 0.0


@dataclass
class BoilerplateStats:
    """Aggregate boilerplate/positional risk stats."""

    flagged_chunk_count: int
    flagged_token_total: int
    avg_boilerplate_ratio: float
    avg_positional_penalty: float
    high_risk: bool


@dataclass
class AnalysisReport:
    """Top-level analysis result."""

    model: str
    encoder_label: str
    tokenizer_source: str  # "tiktoken", "transformers", "heuristic", "fallback"
    total_tokens: int
    total_chars: int
    message_count: int
    estimated_cost_usd: float | None
    cost_model_label: str | None
    zones: list[ZoneBreakdown]
    chunks: list[ChunkInfo]
    messages: list[MessageRecord]
    boilerplate: BoilerplateStats
    config: Mapping[str, Any]
    warnings: list[str] = field(default_factory=list)
    recommendations: list[Any] = field(default_factory=list)  # list[Recommendation], lazy-imported

    def zone(self, kind: ZoneKind) -> ZoneBreakdown | None:
        for z in self.zones:
            if z.zone == kind:
                return z
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "encoder_label": self.encoder_label,
            "tokenizer_source": self.tokenizer_source,
            "total_tokens": self.total_tokens,
            "total_chars": self.total_chars,
            "message_count": self.message_count,
            "estimated_cost_usd": self.estimated_cost_usd,
            "cost_model_label": self.cost_model_label,
            "zones": [
                {
                    "zone": z.zone.value,
                    "message_count": z.message_count,
                    "token_count": z.token_count,
                    "char_count": z.char_count,
                    "pct_of_total": z.pct_of_total,
                }
                for z in self.zones
            ],
            "chunks": [
                {
                    "index": c.index,
                    "text_preview": c.text[:200],
                    "token_count": c.token_count,
                    "char_count": c.char_count,
                    "position": c.position,
                    "score": c.score,
                    "method": c.method,
                    "boilerplate_ratio": c.boilerplate_ratio,
                    "positional_penalty": c.positional_penalty,
                }
                for c in self.chunks
            ],
            "messages": [
                {
                    "index": m.index,
                    "role": m.role,
                    "zone": m.zone.value,
                    "source": m.source,
                    "char_count": m.char_count,
                    "token_count": m.token_count,
                }
                for m in self.messages
            ],
            "boilerplate": {
                "flagged_chunk_count": self.boilerplate.flagged_chunk_count,
                "flagged_token_total": self.boilerplate.flagged_token_total,
                "avg_boilerplate_ratio": self.boilerplate.avg_boilerplate_ratio,
                "avg_positional_penalty": self.boilerplate.avg_positional_penalty,
                "high_risk": self.boilerplate.high_risk,
            },
            "warnings": list(self.warnings),
            "recommendations": [
                r.to_dict() for r in (self.recommendations or [])
            ],
        }
