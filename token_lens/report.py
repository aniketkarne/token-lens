"""Self-contained HTML and SVG reports.

No external network requests, no CDN, no fonts. All CSS is inlined. The
treemap is generated server-side as inline SVG.
"""

from __future__ import annotations

import html
import json
import math
from pathlib import Path
from typing import Iterable

from .types import AnalysisReport, ChunkInfo, ZoneBreakdown, ZoneKind


_ZONE_COLORS = {
    ZoneKind.SYSTEM: "#3b82f6",
    ZoneKind.TOOL_SCHEMA: "#a855f7",
    ZoneKind.FEW_SHOT: "#ec4899",
    ZoneKind.RAG: "#10b981",
    ZoneKind.HISTORY: "#f59e0b",
    ZoneKind.USER: "#06b6d4",
    ZoneKind.ASSISTANT: "#64748b",
    ZoneKind.UNKNOWN: "#94a3b8",
}


# ----- Treemap (slice-and-dice) ----------------------------------------------


def _treemap_rects(items: list[tuple[str, float]], width: int, height: int) -> list[dict]:
    """Slice-and-dice treemap layout. ``items`` is list of (label, value)."""

    rects: list[dict] = []
    if not items:
        return rects
    total = sum(v for _, v in items) or 1.0
    items_sorted = sorted(items, key=lambda x: -x[1])
    # Recursive slice
    def slice(items_slice: list[tuple[str, float]], x: float, y: float, w: float, h: float, horizontal: bool) -> None:
        if not items_slice:
            return
        if len(items_slice) == 1:
            label, val = items_slice[0]
            rects.append(
                {
                    "label": label,
                    "value": val,
                    "x": x,
                    "y": y,
                    "w": w,
                    "h": h,
                    "pct": val / total,
                }
            )
            return
        total_local = sum(v for _, v in items_slice)
        if total_local <= 0:
            return
        acc = 0.0
        split_idx = 1
        for i in range(1, len(items_slice)):
            acc += items_slice[i - 1][1]
            if acc >= total_local / 2:
                split_idx = i
                break
        left = items_slice[:split_idx]
        right = items_slice[split_idx:]
        left_sum = sum(v for _, v in left)
        frac = left_sum / total_local if total_local else 0.5
        if horizontal:
            lw = w * frac
            slice(left, x, y, lw, h, False)
            slice(right, x + lw, y, w - lw, h, True)
        else:
            lh = h * frac
            slice(left, x, y, w, lh, True)
            slice(right, x, y + lh, w, h - lh, False)

    slice(items_sorted, 0.0, 0.0, float(width), float(height), width >= height)
    return rects


def _treemap_svg(report: AnalysisReport, width: int = 720, height: int = 360) -> str:
    items = [(z.zone.value, max(1.0, z.token_count)) for z in report.zones]
    rects = _treemap_rects(items, width, height)
    parts: list[str] = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'role="img" aria-label="Token usage treemap" width="100%" height="auto" '
        f'style="background:#0f172a;border-radius:8px;">'
    )
    parts.append(
        '<style>.tl-cell{stroke:#0f172a;stroke-width:2;cursor:default;}'
        '.tl-label{fill:#f8fafc;font:600 12px ui-sans-serif,system-ui,sans-serif;}'
        '.tl-sub{fill:#cbd5e1;font:500 10px ui-monospace,monospace;}</style>'
    )
    for r in rects:
        color = _ZONE_COLORS.get(
            ZoneKind(r["label"]) if r["label"] in {z.value for z in ZoneKind} else ZoneKind.UNKNOWN,
            "#475569",
        )
        parts.append(
            f'<rect class="tl-cell" x="{r["x"]:.1f}" y="{r["y"]:.1f}" '
            f'width="{r["w"]:.1f}" height="{r["h"]:.1f}" fill="{color}" rx="4">'
            f'<title>{html.escape(r["label"])}: {r["value"]:.0f} tokens '
            f'({r["pct"] * 100:.1f}%)</title></rect>'
        )
        if r["w"] > 60 and r["h"] > 26:
            cx = r["x"] + 8
            cy = r["y"] + 16
            parts.append(
                f'<text class="tl-label" x="{cx:.1f}" y="{cy:.1f}">{html.escape(r["label"])}</text>'
            )
            parts.append(
                f'<text class="tl-sub" x="{cx:.1f}" y="{cy + 12:.1f}">{r["value"]:.0f} tok ({r["pct"] * 100:.1f}%)</text>'
            )
    parts.append("</svg>")
    return "".join(parts)


# ----- HTML report -----------------------------------------------------------


_CSS = """
:root {
  color-scheme: dark;
  --bg: #0f172a;
  --bg-2: #1e293b;
  --fg: #e2e8f0;
  --muted: #94a3b8;
  --accent: #38bdf8;
  --warn: #f97316;
  --danger: #ef4444;
  --ok: #22c55e;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--fg);
  font: 14px/1.5 ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
}
header {
  padding: 24px 32px;
  background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
  border-bottom: 1px solid #334155;
}
header h1 {
  margin: 0 0 6px;
  font-size: 22px;
  letter-spacing: -0.01em;
}
header .meta {
  color: var(--muted);
  font: 12px/1.5 ui-monospace, "JetBrains Mono", monospace;
}
main {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 24px;
  padding: 24px 32px;
  max-width: 1280px;
  margin: 0 auto;
}
section {
  background: var(--bg-2);
  border: 1px solid #334155;
  border-radius: 10px;
  padding: 20px;
  margin-bottom: 20px;
}
section h2 {
  margin: 0 0 12px;
  font-size: 14px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--muted);
}
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 12px;
}
.kpi {
  background: #0b1322;
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 14px;
}
.kpi .k {
  color: var(--muted);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.kpi .v {
  font-size: 22px;
  font-weight: 600;
  margin-top: 4px;
  font-variant-numeric: tabular-nums;
}
table {
  width: 100%;
  border-collapse: collapse;
  font-variant-numeric: tabular-nums;
}
th, td {
  padding: 8px 10px;
  text-align: left;
  border-bottom: 1px solid #334155;
}
th {
  color: var(--muted);
  font-weight: 600;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.bar {
  display: inline-block;
  height: 8px;
  border-radius: 4px;
  background: var(--accent);
  vertical-align: middle;
}
.zone-swatch {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 2px;
  margin-right: 8px;
  vertical-align: middle;
}
.warn { color: var(--warn); }
.danger { color: var(--danger); }
.ok { color: var(--ok); }
.chunk-row.flagged {
  background: rgba(239, 68, 68, 0.08);
}
details summary {
  cursor: pointer;
  color: var(--muted);
}
code {
  background: #0b1322;
  padding: 1px 6px;
  border-radius: 4px;
  font: 12px ui-monospace, "JetBrains Mono", monospace;
}
@media (max-width: 920px) {
  main { grid-template-columns: 1fr; }
}
"""


def _zone_swatch(zone: ZoneKind) -> str:
    color = _ZONE_COLORS.get(zone, "#475569")
    return f'<span class="zone-swatch" style="background:{color}"></span>'


def _zone_table(report: AnalysisReport) -> str:
    rows: list[str] = []
    for z in report.zones:
        rows.append(
            "<tr>"
            f"<td>{_zone_swatch(z.zone)}{html.escape(z.zone.value)}</td>"
            f"<td>{z.message_count}</td>"
            f'<td><span class="bar" style="width:{max(8, z.pct_of_total * 200):.1f}px"></span> '
            f"{z.token_count:,}</td>"
            f"<td>{z.pct_of_total * 100:.1f}%</td>"
            f"<td>{z.char_count:,}</td>"
            "</tr>"
        )
    return (
        "<table><thead><tr>"
        "<th>Zone</th><th>Messages</th><th>Tokens</th><th>%</th><th>Chars</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
    )


def _chunk_table(report: AnalysisReport) -> str:
    if not report.chunks:
        return "<p class=\"warn\">No RAG chunks detected in this trace.</p>"
    rows: list[str] = []
    for c in report.chunks:
        flagged = c.boilerplate_ratio >= 0.55 or c.positional_penalty >= 0.5
        cls = "chunk-row flagged" if flagged else "chunk-row"
        preview = html.escape(c.text.replace("\n", " ")[:120])
        rows.append(
            f"<tr class=\"{cls}\">"
            f"<td>{c.index}</td>"
            f"<td>{c.position}</td>"
            f"<td>{c.token_count:,}</td>"
            f"<td>{c.score:.3f}</td>"
            f"<td><code>{c.method}</code></td>"
            f"<td>{c.boilerplate_ratio:.2f}</td>"
            f"<td>{c.positional_penalty:.2f}</td>"
            f'<td><span title="{html.escape(c.text[:200])}">{preview}</span></td>'
            "</tr>"
        )
    return (
        "<table><thead><tr>"
        "<th>#</th><th>Pos</th><th>Tokens</th><th>Score</th><th>Method</th>"
        "<th>Boilerplate</th><th>Pos. penalty</th><th>Preview</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
    )


def _kpi(report: AnalysisReport, label: str, value: str, tone: str = "") -> str:
    cls = tone if tone else ""
    return (
        f'<div class="kpi"><div class="k">{html.escape(label)}</div>'
        f'<div class="v {cls}">{html.escape(value)}</div></div>'
    )


def _messages_table(report: AnalysisReport) -> str:
    rows: list[str] = []
    for m in report.messages:
        preview = html.escape(m.content.replace("\n", " ")[:160])
        rows.append(
            "<tr>"
            f"<td>{m.index}</td>"
            f"<td>{_zone_swatch(m.zone)}{html.escape(m.zone.value)}</td>"
            f"<td><code>{html.escape(m.role)}</code></td>"
            f"<td>{m.token_count:,}</td>"
            f"<td>{m.char_count:,}</td>"
            f'<td><code>{html.escape(m.source)}</code></td>'
            f'<td><span title="{html.escape(m.content[:300])}">{preview}</span></td>'
            "</tr>"
        )
    return (
        "<table><thead><tr>"
        "<th>#</th><th>Zone</th><th>Role</th><th>Tokens</th><th>Chars</th><th>Source</th><th>Preview</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
    )


def render_html(report: AnalysisReport) -> str:
    """Return the full self-contained HTML report as a string."""

    zones_t = _zone_table(report)
    chunks_t = _chunk_table(report)
    messages_t = _messages_table(report)
    treemap = _treemap_svg(report)
    cost = (
        f"${report.estimated_cost_usd:.6f}"
        if report.estimated_cost_usd is not None
        else "n/a"
    )
    cost_label = report.cost_model_label or "unknown"
    high_risk = report.boilerplate.high_risk
    risk_class = "danger" if high_risk else "ok"
    risk_label = "HIGH" if high_risk else "OK"

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>token-lens report — {html.escape(report.model or 'unknown model')}</title>
<style>{_CSS}</style>
</head>
<body>
<header>
  <h1>token-lens report</h1>
  <div class="meta">
    model: <code>{html.escape(report.model or 'unknown')}</code> ·
    encoder: <code>{html.escape(report.encoder_label)}</code> ·
    tokenizer_source: <code>{html.escape(report.tokenizer_source)}</code> ·
    messages: {report.message_count} ·
    generated: token-lens v0.2.0
  </div>
</header>
<main>
<div>
  <section>
    <h2>Token Usage Treemap</h2>
    {treemap}
  </section>
  <section>
    <h2>Zone Breakdown</h2>
    {zones_t}
  </section>
  <section>
    <h2>Chunk Utilization</h2>
    {chunks_t}
  </section>
  <section>
    <h2>Messages ({report.message_count})</h2>
    {messages_t}
  </section>
</div>
<aside>
  <section>
    <h2>Totals</h2>
    <div class="kpi-grid">
      {_kpi(report, 'Total tokens', f"{report.total_tokens:,}")}
      {_kpi(report, 'Total chars', f"{report.total_chars:,}")}
      {_kpi(report, 'Messages', str(report.message_count))}
      {_kpi(report, 'Est. cost', cost)}
      {_kpi(report, 'Price model', cost_label)}
      {_kpi(report, 'Boilerplate risk', risk_label, risk_class)}
      {_kpi(report, 'Flagged chunks', str(report.boilerplate.flagged_chunk_count))}
      {_kpi(report, 'Flagged tokens', f"{report.boilerplate.flagged_token_total:,}")}
    </div>
  </section>
  <section>
    <h2>Config</h2>
    <pre style="white-space:pre-wrap;color:var(--muted);font:12px ui-monospace,monospace;">{html.escape(json.dumps(dict(report.config), indent=2, default=str))}</pre>
  </section>
  {('<section><h2>Warnings</h2><ul>' + ''.join(f'<li class="warn">{html.escape(w)}</li>' for w in report.warnings) + '</ul></section>') if report.warnings else ''}
</aside>
</main>
</body>
</html>
"""


def render_svg(report: AnalysisReport) -> str:
    """Return a standalone SVG treemap (no HTML wrapper)."""

    return _treemap_svg(report)


def write_html(report: AnalysisReport, output: str | Path) -> None:
    Path(output).write_text(render_html(report), encoding="utf-8")


def write_svg(report: AnalysisReport, output: str | Path) -> None:
    Path(output).write_text(render_svg(report), encoding="utf-8")


__all__ = [
    "render_html",
    "render_svg",
    "write_html",
    "write_svg",
    "_treemap_svg",
]
