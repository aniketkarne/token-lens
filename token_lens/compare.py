"""Compare two ``AnalysisReport`` instances and surface savings-first output.

The :func:`compare_reports` helper takes two reports and returns a
:class:`CompareResult` with per-zone deltas plus a top-line savings summary.
Output supports ``text``, ``json`` and ``markdown`` rendering.

The compare CLI ships with token-lens::

    token-lens compare before.json after.json

There are no runtime dependencies.

Heuristics note: token counts depend on the encoder that produced the report.
If ``before`` and ``after`` were analyzed with different encoders (e.g.
``tiktoken`` vs. ``heuristic-bpe-lite``) the absolute counts are not directly
comparable. :meth:`CompareResult.summary` will print a banner warning if the
encoder labels differ.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Iterable

from .recommend import Recommendation, build_recommendations, total_estimated_savings
from .types import AnalysisReport, ZoneKind


# Sentinel for "key not found in one side". ``_ABSENT`` is always narrowed
# back to ``int`` before use.
_ABSENT: int = -1  # sentinel; values are always replaced before use


@dataclass
class ZoneDelta:
    zone: str
    before_tokens: int | None
    after_tokens: int | None
    delta_tokens: int
    delta_pct: float  # signed, fraction of BEFORE (0.0 if before=0)
    direction: str  # "down" | "up" | "same" | "absent_before" | "absent_after" | "new" | "removed"


@dataclass
class CompareResult:
    """The result of comparing two ``AnalysisReport`` objects."""

    before_total_tokens: int
    after_total_tokens: int
    delta_tokens: int
    delta_pct: float  # signed fraction of before_total
    before_encoder: str
    after_encoder: str
    before_cost_usd: float | None
    after_cost_usd: float | None
    delta_cost_usd: float | None
    zones: list[ZoneDelta] = field(default_factory=list)
    boilerplate_before: dict[str, Any] = field(default_factory=dict)
    boilerplate_after: dict[str, Any] = field(default_factory=dict)
    recommendations_after: list[Recommendation] = field(default_factory=list)

    def summary(self) -> str:
        """Human-readable, savings-first text summary."""

        out: list[str] = []
        encoders_match = self.before_encoder == self.after_encoder
        if not encoders_match:
            out.append(
                "NOTE: encoders differ (before=%r, after=%r); counts are "
                "approximate." % (self.before_encoder, self.after_encoder)
            )
        out.append(
            f"tokens:  {self.before_total_tokens:,} -> {self.after_total_tokens:,}  "
            f"({self.delta_tokens:+,}, {self.delta_pct * 100:+.1f}%)"
        )
        if (
            self.before_cost_usd is not None
            and self.after_cost_usd is not None
            and self.delta_cost_usd is not None
        ):
            out.append(
                f"cost:    ${self.before_cost_usd:.6f} -> ${self.after_cost_usd:.6f}  "
                f"(${self.delta_cost_usd:+.6f})"
            )
        else:
            out.append("cost:    n/a (no per-1K price on one side)")
        changed = [
            z
            for z in self.zones
            if z.direction in {"down", "up", "new", "removed"}
        ]
        if changed:
            out.append("zones:")
            for z in changed:
                arrow = {"down": "↓", "up": "↑", "new": "+", "removed": "-"}[z.direction]
                b = "—" if z.before_tokens is None else f"{z.before_tokens:,}"
                a = "—" if z.after_tokens is None else f"{z.after_tokens:,}"
                out.append(
                    f"  {arrow} {z.zone:<12} {b:>8} -> {a:<8} ({z.delta_tokens:+,} tok)"
                )
        if self.boilerplate_after or self.boilerplate_before:
            bf = self.boilerplate_before.get("flagged_chunk_count", 0)
            af = self.boilerplate_after.get("flagged_chunk_count", 0)
            if bf or af:
                out.append(
                    f"boilerplate risk: flagged_chunks {bf} -> {af}"
                )
        if self.recommendations_after:
            tok_save, usd_save = total_estimated_savings(self.recommendations_after)
            out.append(
                f"recommendations for after: {len(self.recommendations_after)}  "
                f"(~{tok_save:,} tok more savings possible)"
            )
            for rec in self.recommendations_after[:3]:
                usd = (
                    f"~${rec.estimated_savings_usd:.6f}"
                    if rec.estimated_savings_usd is not None
                    else "n/a"
                )
                out.append(
                    f"  • {rec.title} (~{rec.estimated_savings_tokens:,} tok, {usd})"
                )
        return "\n".join(out)

    def to_dict(self) -> dict[str, Any]:
        return {
            "before_total_tokens": self.before_total_tokens,
            "after_total_tokens": self.after_total_tokens,
            "delta_tokens": self.delta_tokens,
            "delta_pct": self.delta_pct,
            "before_encoder": self.before_encoder,
            "after_encoder": self.after_encoder,
            "before_cost_usd": self.before_cost_usd,
            "after_cost_usd": self.after_cost_usd,
            "delta_cost_usd": self.delta_cost_usd,
            "zones": [
                {
                    "zone": z.zone,
                    "before_tokens": z.before_tokens,
                    "after_tokens": z.after_tokens,
                    "delta_tokens": z.delta_tokens,
                    "delta_pct": z.delta_pct,
                    "direction": z.direction,
                }
                for z in self.zones
            ],
            "boilerplate_before": dict(self.boilerplate_before),
            "boilerplate_after": dict(self.boilerplate_after),
            "recommendations_after": [
                r.to_dict() for r in self.recommendations_after
            ],
        }


# ---------------------------------------------------------------------------
# Comparison logic
# ---------------------------------------------------------------------------


def _zone_index(report: AnalysisReport) -> dict[str, int]:
    return {z.zone.value: z.token_count for z in report.zones}


def _zone_delta(before: int | None, after: int | None) -> ZoneDelta:
    if before is None and after is None:
        return ZoneDelta("?", None, None, 0, 0.0, "same")
    if before is None:
        return ZoneDelta(
            zone="?",
            before_tokens=None,
            after_tokens=after,
            delta_tokens=after,
            delta_pct=1.0,
            direction="new",
        )
    if after is None:
        return ZoneDelta(
            zone="?",
            before_tokens=before,
            after_tokens=None,
            delta_tokens=-before,
            delta_pct=-1.0,
            direction="removed",
        )
    delta = after - before
    if before == 0:
        pct = 1.0 if after > 0 else 0.0
    else:
        pct = delta / before
    if delta < 0:
        direction = "down"
    elif delta > 0:
        direction = "up"
    else:
        direction = "same"
    return ZoneDelta(
        zone="?",
        before_tokens=before,
        after_tokens=after,
        delta_tokens=delta,
        delta_pct=pct,
        direction=direction,
    )


_ZONE_ORDER = [z.value for z in [
    ZoneKind.SYSTEM,
    ZoneKind.TOOL_SCHEMA,
    ZoneKind.FEW_SHOT,
    ZoneKind.RAG,
    ZoneKind.HISTORY,
    ZoneKind.USER,
    ZoneKind.ASSISTANT,
    ZoneKind.UNKNOWN,
]]


def compare_reports(before: AnalysisReport, after: AnalysisReport) -> CompareResult:
    """Return a :class:`CompareResult` between two reports."""

    b_map = _zone_index(before)
    a_map = _zone_index(after)
    zones: list[ZoneDelta] = []
    for z in _ZONE_ORDER:
        b_v = b_map.get(z, _ABSENT)
        a_v = a_map.get(z, _ABSENT)
        b_arg: int | None = None if b_v == _ABSENT else int(b_v)
        a_arg: int | None = None if a_v == _ABSENT else int(a_v)
        zd = _zone_delta(b_arg, a_arg)
        zd.zone = z
        if zd.before_tokens is None and zd.after_tokens is None:
            continue
        zones.append(zd)
    # any zones not in _ZONE_ORDER (defensive)
    extras = (set(b_map) | set(a_map)) - set(_ZONE_ORDER)
    for z in sorted(extras):
        b_v = b_map.get(z, _ABSENT)
        a_v = a_map.get(z, _ABSENT)
        b_arg = None if b_v == _ABSENT else int(b_v)
        a_arg = None if a_v == _ABSENT else int(a_v)
        zd = _zone_delta(b_arg, a_arg)
        zd.zone = z
        if zd.before_tokens is None and zd.after_tokens is None:
            continue
        zones.append(zd)

    delta = after.total_tokens - before.total_tokens
    pct = delta / before.total_tokens if before.total_tokens else 0.0
    b_cost = before.estimated_cost_usd
    a_cost = after.estimated_cost_usd
    d_cost = (
        round(a_cost - b_cost, 6)
        if (b_cost is not None and a_cost is not None)
        else None
    )

    b_boil = {
        "flagged_chunk_count": before.boilerplate.flagged_chunk_count,
        "flagged_token_total": before.boilerplate.flagged_token_total,
        "avg_boilerplate_ratio": round(before.boilerplate.avg_boilerplate_ratio, 4),
        "high_risk": before.boilerplate.high_risk,
    }
    a_boil = {
        "flagged_chunk_count": after.boilerplate.flagged_chunk_count,
        "flagged_token_total": after.boilerplate.flagged_token_total,
        "avg_boilerplate_ratio": round(after.boilerplate.avg_boilerplate_ratio, 4),
        "high_risk": after.boilerplate.high_risk,
    }

    return CompareResult(
        before_total_tokens=before.total_tokens,
        after_total_tokens=after.total_tokens,
        delta_tokens=delta,
        delta_pct=pct,
        before_encoder=before.encoder_label,
        after_encoder=after.encoder_label,
        before_cost_usd=b_cost,
        after_cost_usd=a_cost,
        delta_cost_usd=d_cost,
        zones=zones,
        boilerplate_before=b_boil,
        boilerplate_after=a_boil,
        recommendations_after=build_recommendations(after),
    )


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------


def render_compare_markdown(cmp: CompareResult) -> str:
    """Render a markdown summary (suitable for PR comments / issues)."""

    lines: list[str] = []
    lines.append("# token-lens compare")
    lines.append("")
    lines.append(
        f"**tokens:** `{cmp.before_total_tokens:,}` → "
        f"`{cmp.after_total_tokens:,}` ({cmp.delta_tokens:+,}, "
        f"{cmp.delta_pct * 100:+.1f}%)"
    )
    if cmp.delta_cost_usd is not None:
        lines.append(
            f"**cost:** `${cmp.before_cost_usd:.6f}` → "
            f"`${cmp.after_cost_usd:.6f}` (`${cmp.delta_cost_usd:+.6f}`)"
        )
    lines.append("")
    if cmp.zones:
        lines.append("| zone | before | after | Δ |")
        lines.append("|---|---:|---:|---:|")
        for z in cmp.zones:
            b = "—" if z.before_tokens is None else f"{z.before_tokens:,}"
            a = "—" if z.after_tokens is None else f"{z.after_tokens:,}"
            lines.append(f"| {z.zone} | {b} | {a} | {z.delta_tokens:+,} |")
    lines.append("")
    if cmp.recommendations_after:
        lines.append("## Recommendations to push `after` further")
        lines.append("")
        for r in cmp.recommendations_after:
            usd = (
                f" (~${r.estimated_savings_usd:.6f})"
                if r.estimated_savings_usd is not None
                else ""
            )
            lines.append(
                f"- **{r.title}** — ~{r.estimated_savings_tokens:,} tok{usd}. "
                f"{r.why}"
            )
            lines.append(f"  - *how:* {r.how}")
    return "\n".join(lines) + "\n"


__all__ = [
    "CompareResult",
    "ZoneDelta",
    "compare_reports",
    "render_compare_markdown",
]
