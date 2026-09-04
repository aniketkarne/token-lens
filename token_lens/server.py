"""Tiny stdlib web server for token-lens.

Exposes three JSON endpoints that drive the same analyzer the CLI uses:

* ``POST /api/upload``  – accept a JSON trace in the request body and return
  a ``report_id`` with persisted artifacts (HTML, SVG, JSON).
* ``GET  /api/report/<report_id>`` – JSON summary of a previously uploaded
  report.
* ``GET  /api/download/<report_id>/<format>`` – download the rendered
  artifact (``html``, ``svg`` or ``json``).

Plus the UI routes:

* ``GET  /`` – the upload form / landing page (HTML, no JS, no CDN).
* ``GET  /reports/<report_id>`` – the rendered HTML report.
* ``GET  /healthz`` – plain ``ok`` liveness probe.

The whole thing runs on :mod:`http.server` from the standard library so it
works in any Python 3.9+ environment with no extra dependencies.

Example::

    python -m token_lens.server --port 8765
    # then in another shell:
    curl -F file=@examples/sample_trace.json http://localhost:8765/api/upload
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import re
import secrets
import shutil
import sys
import threading
import urllib.parse
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .analyze import analyze_trace
from .report import render_html, render_svg

__all__ = ["build_server", "create_handler", "main"]


# ---------------------------------------------------------------------------
# Storage: in-memory + on-disk cache
# ---------------------------------------------------------------------------


@dataclass
class _StoredReport:
    report_id: str
    trace: dict[str, Any]
    report: Any  # AnalysisReport
    html: str
    svg: str
    summary: str  # JSON text


class _ReportStore:
    """Thread-safe registry of generated reports.

    The store keeps both an in-memory copy (for /api/report lookups) and
    rendered artifacts on disk under ``root``. Disk paths are returned by
    ``/api/download/<id>/<format>``.
    """

    def __init__(self, root: Path):
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._items: dict[str, _StoredReport] = {}

    @property
    def root(self) -> Path:
        return self._root

    def store(self, trace: dict[str, Any]) -> _StoredReport:
        from .analyze import analyze_trace as _analyze

        report = _analyze(trace)
        report_id = secrets.token_urlsafe(8)
        folder = self._root / report_id
        folder.mkdir(parents=True, exist_ok=True)

        html = render_html(report)
        svg = render_svg(report)
        summary = json.dumps(report.to_dict(), indent=2)

        (folder / "report.html").write_text(html, encoding="utf-8")
        (folder / "treemap.svg").write_text(svg, encoding="utf-8")
        (folder / "summary.json").write_text(summary, encoding="utf-8")
        (folder / "trace.json").write_text(
            json.dumps(trace, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        item = _StoredReport(
            report_id=report_id,
            trace=trace,
            report=report,
            html=html,
            svg=svg,
            summary=summary,
        )
        with self._lock:
            self._items[report_id] = item
        return item

    def get(self, report_id: str) -> _StoredReport | None:
        with self._lock:
            return self._items.get(report_id)

    def path_for(self, report_id: str, fmt: str) -> Path | None:
        folder = self._root / report_id
        if not folder.is_dir():
            return None
        mapping = {
            "html": folder / "report.html",
            "svg": folder / "treemap.svg",
            "json": folder / "summary.json",
            "trace": folder / "trace.json",
        }
        path = mapping.get(fmt)
        return path if path and path.exists() else None


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------


_INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>token-lens · live analyzer</title>
<style>
:root { color-scheme: dark; }
* { box-sizing: border-box; }
body {
  margin: 0;
  background: #0f172a;
  color: #e2e8f0;
  font: 15px/1.55 ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
}
.hero {
  padding: 48px 32px 32px;
  background: radial-gradient(1200px 400px at 80% 0%, rgba(56,189,248,0.18), transparent 70%),
              linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
  border-bottom: 1px solid #334155;
}
.hero-inner { max-width: 1100px; margin: 0 auto; display: flex; gap: 32px; align-items: center; flex-wrap: wrap; }
.hero-text { flex: 1 1 380px; }
.hero-art  { flex: 0 0 auto; max-width: 420px; width: 100%; }
.hero h1 { margin: 0 0 8px; font-size: 30px; letter-spacing: -0.02em; }
.hero .lede { color: #94a3b8; font-size: 16px; max-width: 60ch; }
.hero .badge {
  display: inline-block; margin-top: 12px; font: 11px ui-monospace,monospace;
  padding: 4px 10px; border-radius: 999px; background: rgba(34,197,94,0.15);
  color: #22c55e; border: 1px solid rgba(34,197,94,0.3);
}
.shell {
  max-width: 1100px; margin: 32px auto; padding: 0 32px;
}
.card {
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 20px;
}
.card h2 {
  margin: 0 0 12px; font-size: 13px; text-transform: uppercase;
  letter-spacing: 0.08em; color: #94a3b8;
}
.row { display: flex; gap: 12px; flex-wrap: wrap; }
.row > * { flex: 1 1 220px; }
label { display: block; font-size: 12px; color: #94a3b8; margin-bottom: 6px; }
input[type=text], input[type=file], select, textarea {
  width: 100%; background: #0b1322; color: #e2e8f0; border: 1px solid #334155;
  border-radius: 8px; padding: 10px 12px; font: 13px ui-sans-serif,system-ui;
}
textarea { font-family: ui-monospace, "JetBrains Mono", monospace; min-height: 180px; }
button {
  background: #38bdf8; color: #0b1322; border: 0; border-radius: 8px;
  padding: 10px 18px; font: 600 14px ui-sans-serif,system-ui; cursor: pointer;
}
button.secondary { background: #334155; color: #e2e8f0; }
button:hover { filter: brightness(1.05); }
.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px,1fr)); gap: 12px; }
.kpi { background: #0b1322; border: 1px solid #334155; border-radius: 8px; padding: 12px 14px; }
.kpi .k { font-size: 11px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; }
.kpi .v { font-size: 22px; font-weight: 600; margin-top: 4px; font-variant-numeric: tabular-nums; }
.kpi .v.danger { color: #ef4444; }
.kpi .v.ok { color: #22c55e; }
a.dl { color: #38bdf8; text-decoration: none; }
a.dl:hover { text-decoration: underline; }
pre { background: #0b1322; border: 1px solid #334155; border-radius: 8px; padding: 12px; overflow: auto; font-size: 12px; }
.err { color: #f97316; }
.zone-row { display: flex; align-items: center; gap: 12px; padding: 6px 0; border-bottom: 1px dashed #334155; }
.zone-row:last-child { border-bottom: 0; }
.zone-swatch { width: 12px; height: 12px; border-radius: 3px; display: inline-block; }
.zone-name { width: 110px; font-family: ui-monospace,monospace; font-size: 12px; }
.zone-bar { flex: 1; background: #0b1322; border-radius: 4px; height: 10px; overflow: hidden; border: 1px solid #334155; }
.zone-bar > span { display: block; height: 100%; }
.zone-pct { width: 70px; text-align: right; font-variant-numeric: tabular-nums; }
.zone-tok { width: 90px; text-align: right; font-variant-numeric: tabular-nums; color: #94a3b8; }
footer { padding: 32px; color: #64748b; text-align: center; font-size: 12px; }
@media (max-width: 720px) {
  .hero { padding: 32px 20px 24px; }
  .shell { padding: 0 20px; }
}
</style>
</head>
<body>
<section class="hero">
  <div class="hero-inner">
    <div class="hero-text">
      <h1>token-lens</h1>
      <p class="lede">Offline analyzer for LLM prompt token usage. Drop in a trace JSON, see the treemap, the per-zone breakdown, and an offline HTML report.</p>
      <span class="badge">local · stdlib only · zero CDN</span>
    </div>
    <div class="hero-art">
      __HERO_ART__
    </div>
  </div>
</section>

<div class="shell">
  <div class="card">
    <h2>1. Pick a trace</h2>
    <div class="row">
      <div>
        <label for="file">Upload a JSON trace file</label>
        <input id="file" type="file" accept=".json,application/json">
      </div>
      <div>
        <label for="model">Model (optional)</label>
        <input id="model" type="text" placeholder="gpt-4o, claude-3-haiku, ...">
      </div>
      <div>
        <label for="price">Price per 1K tokens (optional USD)</label>
        <input id="price" type="text" placeholder="e.g. 0.005">
      </div>
    </div>
    <p style="color:#94a3b8;font-size:13px;">Or paste JSON below — both go to <code>/api/upload</code>.</p>
    <label for="paste">Paste trace JSON</label>
    <textarea id="paste" placeholder='{"model":"gpt-4o","messages":[{"role":"user","content":"hi"}]}'></textarea>
    <div class="row" style="margin-top:16px;">
      <div><button id="submit">Analyze trace</button></div>
      <div><button class="secondary" id="sample">Load sample</button></div>
      <div><a class="dl" href="/api/sample" style="margin-left:8px;font-size:13px;">Download bundled sample trace →</a></div>
    </div>
  </div>

  <div class="card" id="result" style="display:none;">
    <h2>2. Result</h2>
    <div id="result-body"></div>
  </div>

  <div class="card">
    <h2>API</h2>
    <pre>POST /api/upload            # multipart file=@trace.json or raw JSON body
GET  /api/sample            # bundled example trace (application/json)
GET  /api/report/&lt;id&gt;       # JSON summary
GET  /api/download/&lt;id&gt;/html # rendered offline report
GET  /api/download/&lt;id&gt;/svg  # standalone treemap SVG
GET  /api/download/&lt;id&gt;/json # machine summary
GET  /api/download/&lt;id&gt;/trace# original trace echo
GET  /reports/&lt;id&gt;          # inline HTML report (same as html download)
GET  /healthz                # liveness</pre>
  </div>
</div>

<footer>token-lens · offline prompt analyzer · runs on Python stdlib</footer>

<script>
// Single-shot client: read file OR textarea, POST JSON to /api/upload, render summary.
(function() {
  const $ = (id) => document.getElementById(id);
  const fileEl = $("file");
  const pasteEl = $("paste");
  const modelEl = $("model");
  const priceEl = $("price");
  const resultEl = $("result");
  const bodyEl = $("result-body");

  $("sample").addEventListener("click", async () => {
    const r = await fetch("/api/sample");
    const j = await r.json();
    pasteEl.value = JSON.stringify(j, null, 2);
  });

  $("submit").addEventListener("click", async () => {
    bodyEl.innerHTML = '<p class="err">analyzing…</p>';
    resultEl.style.display = "block";
    let payload;
    try {
      if (fileEl.files && fileEl.files[0]) {
        payload = await fileEl.files[0].text();
      } else if (pasteEl.value.trim()) {
        payload = pasteEl.value;
      } else {
        bodyEl.innerHTML = '<p class="err">Provide a file or paste JSON.</p>';
        return;
      }
      const trace = JSON.parse(payload);
      if (modelEl.value) trace.model = modelEl.value;
      if (priceEl.value) {
        const n = Number(priceEl.value);
        if (!Number.isNaN(n)) trace.__price_per_1k = n;
      }
      const r = await fetch("/api/upload", {
        method: "POST",
        headers: {"content-type": "application/json"},
        body: JSON.stringify(trace),
      });
      const data = await r.json();
      if (!r.ok) {
        bodyEl.innerHTML = '<p class="err">' + (data.error || "upload failed") + '</p>';
        return;
      }
      render(data);
    } catch (e) {
      bodyEl.innerHTML = '<p class="err">' + (e && e.message || e) + '</p>';
    }
  });

  function render(data) {
    const r = data.report;
    const cost = r.estimated_cost_usd != null
      ? "$" + r.estimated_cost_usd.toFixed(6)
      : "n/a";
    const riskCls = r.boilerplate.high_risk ? "danger" : "ok";
    const zones = r.zones.map(z =>
      '<div class="zone-row">' +
        '<span class="zone-swatch" style="background:' + zoneColor(z.zone) + '"></span>' +
        '<span class="zone-name">' + z.zone + '</span>' +
        '<span class="zone-bar"><span style="width:' + (z.pct_of_total*100).toFixed(1) + '%;background:' + zoneColor(z.zone) + '"></span></span>' +
        '<span class="zone-pct">' + (z.pct_of_total*100).toFixed(1) + '%</span>' +
        '<span class="zone-tok">' + z.token_count.toLocaleString() + ' tok</span>' +
      '</div>'
    ).join("");
    bodyEl.innerHTML =
      '<div class="kpis">' +
        kpi("Total tokens", r.total_tokens.toLocaleString()) +
        kpi("Total chars", r.total_chars.toLocaleString()) +
        kpi("Messages", r.message_count) +
        kpi("Encoder", r.encoder_label) +
        kpi("Est. cost", cost) +
        kpi("Risk", r.boilerplate.high_risk ? "HIGH" : "OK", riskCls) +
      '</div>' +
      '<h3 style="margin-top:18px;font-size:13px;color:#94a3b8;text-transform:uppercase;letter-spacing:0.06em;">Zones</h3>' +
      '<div>' + zones + '</div>' +
      '<p style="margin-top:18px;">' +
        '<a class="dl" href="/reports/' + data.report_id + '">Open HTML report →</a> &nbsp;·&nbsp; ' +
        '<a class="dl" href="/api/download/' + data.report_id + '/html">download .html</a> &nbsp;·&nbsp; ' +
        '<a class="dl" href="/api/download/' + data.report_id + '/svg">download .svg</a> &nbsp;·&nbsp; ' +
        '<a class="dl" href="/api/download/' + data.report_id + '/json">download .json</a>' +
      '</p>';
  }
  function kpi(k, v, cls) {
    return '<div class="kpi"><div class="k">' + k + '</div><div class="v ' + (cls||"") + '">' + v + '</div></div>';
  }
  function zoneColor(z) {
    const m = {
      system:"#3b82f6", tool_schema:"#a855f7", few_shot:"#ec4899",
      rag:"#10b981", history:"#f59e0b", user:"#06b6d4",
      assistant:"#64748b", unknown:"#94a3b8",
    };
    return m[z] || "#475569";
  }
})();
</script>
</body>
</html>
"""


def _hero_asset_path() -> Path | None:
    """Return the on-disk path of ``assets/hero.svg`` if it is available.

    The asset ships in the repository (and in the sdist) next to the package;
    when it is missing we fall back to the inline art in :func:`_hero_art`.
    """
    here = Path(__file__).resolve().parent
    for candidate in (
        here.parent / "assets" / "hero.svg",   # repo checkout / sdist
        here / "assets" / "hero.svg",          # packaged inside token_lens/
    ):
        if candidate.is_file():
            return candidate
    return None


def _hero_art() -> str:
    """Return the token-lens-specific hero SVG.

    Hand-authored, inline, no external fonts. Three concentric zone slices
    labelled SYSTEM / RAG / USER to communicate the zone-classifier idea.
    """
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 420 260" '
        'role="img" aria-label="token-lens treemap illustration" '
        'style="width:100%;height:auto;display:block;">'
        '<defs>'
        '<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="#1e293b"/>'
        '<stop offset="1" stop-color="#0f172a"/>'
        '</linearGradient>'
        '<linearGradient id="rag" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="#10b981"/><stop offset="1" stop-color="#059669"/>'
        '</linearGradient>'
        '<linearGradient id="sys" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="#3b82f6"/><stop offset="1" stop-color="#1d4ed8"/>'
        '</linearGradient>'
        '<linearGradient id="user" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="#06b6d4"/><stop offset="1" stop-color="#0891b2"/>'
        '</linearGradient>'
        '</defs>'
        '<rect x="0" y="0" width="420" height="260" rx="14" fill="url(#bg)"/>'
        # largest slice: RAG
        '<rect x="20" y="20" width="380" height="150" rx="10" fill="url(#rag)"/>'
        '<text x="36" y="56" font="600 18px ui-sans-serif,system-ui" fill="#ecfdf5">rag · 62%</text>'
        '<text x="36" y="78" font="500 12px ui-monospace,monospace" fill="#d1fae5">'
        "context_docs[0..n]  ·  3,420 tokens</text>"
        # system strip
        '<rect x="20" y="180" width="170" height="60" rx="10" fill="url(#sys)"/>'
        '<text x="34" y="210" font="600 14px ui-sans-serif,system-ui" fill="#eff6ff">system · 14%</text>'
        '<text x="34" y="228" font="500 11px ui-monospace,monospace" fill="#dbeafe">'
        "instructions</text>"
        # user slice
        '<rect x="200" y="180" width="200" height="60" rx="10" fill="url(#user)"/>'
        '<text x="214" y="210" font="600 14px ui-sans-serif,system-ui" fill="#ecfeff">user · 9%</text>'
        '<text x="214" y="228" font="500 11px ui-monospace,monospace" fill="#cffafe">'
        "live message</text>"
        # token dots
        '<g fill="#f8fafc" opacity="0.85">'
        + "".join(
            f'<rect x="{50 + i*8}" y="100" width="4" height="4" rx="1"/>'
            for i in range(38)
        )
        + '</g>'
        '</svg>'
    )


def _index_html() -> str:
    """Render the landing page, preferring the on-disk hero asset."""
    p = _hero_asset_path()
    if p is not None:
        try:
            art = p.read_text(encoding="utf-8")
        except OSError:  # pragma: no cover - defensive
            art = _hero_art()
    else:
        art = _hero_art()
    return _INDEX_HTML.replace("__HERO_ART__", art)


# ---------------------------------------------------------------------------
# Request handler
# ---------------------------------------------------------------------------


# Match /api/report/<id>  and  /api/download/<id>/<fmt>
_REPORT_ID = r"[A-Za-z0-9_\-]{4,32}"
_API_REPORT_RE = re.compile(rf"^/api/report/({_REPORT_ID})$")
_API_DOWNLOAD_RE = re.compile(rf"^/api/download/({_REPORT_ID})/([a-z]+)$")


class _Handler(BaseHTTPRequestHandler):
    server_version = "token-lens/0.2"

    # The store and the route table are bound in build_server().
    store: _ReportStore = None  # type: ignore[assignment]

    # Reduce noise in test logs.
    def log_message(self, format: str, *args: Any) -> None:  # noqa: D401
        sys.stderr.write("[token-lens] " + (format % args) + "\n")

    # -- helpers ---------------------------------------------------------
    def _send(self, status: int, body: bytes, content_type: str = "application/json") -> None:
        self.send_response(status)
        self.send_header("content-type", content_type)
        self.send_header("content-length", str(len(body)))
        self.send_header("cache-control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status: int, payload: Any) -> None:
        body = json.dumps(payload, default=str).encode("utf-8")
        self._send(status, body, "application/json; charset=utf-8")

    def _send_file(self, path: Path, download: bool = True) -> None:
        data = path.read_bytes()
        mt, _ = mimetypes.guess_type(str(path))
        ct = mt or "application/octet-stream"
        self.send_response(200)
        self.send_header("content-type", ct)
        self.send_header("content-length", str(len(data)))
        if download:
            self.send_header(
                "content-disposition",
                f'attachment; filename="{path.name}"',
            )
        self.end_headers()
        self.wfile.write(data)

    # -- routing ---------------------------------------------------------
    def do_GET(self) -> None:  # noqa: N802 (BaseHTTPRequestHandler API)
        url = urllib.parse.urlsplit(self.path)
        path = url.path

        if path == "/":
            html = _index_html().encode("utf-8")
            self._send(200, html, "text/html; charset=utf-8")
            return

        if path == "/healthz":
            self._send(200, b"ok", "text/plain; charset=utf-8")
            return

        if path == "/assets/hero.svg":
            p = _hero_asset_path()
            if p is None:
                # Fall back to the inline art so the route always works.
                self._send(
                    200,
                    _hero_art().encode("utf-8"),
                    "image/svg+xml; charset=utf-8",
                )
                return
            self._send(
                200,
                p.read_bytes(),
                "image/svg+xml; charset=utf-8",
            )
            return

        if path == "/api/sample":
            sample = _load_sample_trace()
            self._send_json(200, sample)
            return

        m = _API_REPORT_RE.match(path)
        if m:
            (report_id,) = m.groups()
            item = self.store.get(report_id)
            if item is None:
                self._send_json(404, {"error": "unknown report_id"})
                return
            self._send_json(200, item.report.to_dict())
            return

        m = _API_DOWNLOAD_RE.match(path)
        if m:
            report_id, fmt = m.groups()
            if fmt not in {"html", "svg", "json", "trace"}:
                self._send_json(400, {"error": f"unsupported format: {fmt}"})
                return
            p = self.store.path_for(report_id, fmt)
            if p is None:
                self._send_json(404, {"error": "unknown report_id"})
                return
            self._send_file(p)
            return

        # inline HTML report route
        m = re.match(rf"^/reports/({_REPORT_ID})$", path)
        if m:
            (report_id,) = m.groups()
            p = self.store.path_for(report_id, "html")
            if p is None:
                self._send_json(404, {"error": "unknown report_id"})
                return
            # No content-disposition for inline view.
            data = p.read_bytes()
            self.send_response(200)
            self.send_header("content-type", "text/html; charset=utf-8")
            self.send_header("content-length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        self._send_json(404, {"error": "not found", "path": path})

    def do_POST(self) -> None:  # noqa: N802
        url = urllib.parse.urlsplit(self.path)
        path = url.path

        if path == "/api/upload":
            return self._handle_upload()

        self._send_json(404, {"error": "not found", "path": path})

    # -- upload ----------------------------------------------------------
    def _handle_upload(self) -> None:
        length = int(self.headers.get("content-length", "0") or 0)
        if length <= 0:
            self._send_json(400, {"error": "empty body"})
            return
        if length > 32 * 1024 * 1024:
            self._send_json(413, {"error": "payload too large (>32MB)"})
            return

        ctype = (self.headers.get("content-type") or "").lower()
        raw = self.rfile.read(length)
        try:
            if "multipart/form-data" in ctype:
                trace = _parse_multipart_trace(ctype, raw)
            else:
                trace = json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, ValueError, KeyError) as exc:
            self._send_json(400, {"error": f"invalid JSON: {exc}"})
            return
        except Exception as exc:  # pragma: no cover - defensive
            self._send_json(400, {"error": str(exc)})
            return

        if not isinstance(trace, dict):
            self._send_json(400, {"error": "trace must be a JSON object"})
            return

        # Per-request overrides via __price_per_1k / model keys are honored
        # by analyze_trace by reading top-level "model"; price override is
        # applied via the analyzer's config path. Keep this small adapter.
        overrides: dict[str, Any] = {}
        if "model" in trace:
            overrides["model"] = trace.get("model")
        if "__price_per_1k" in trace:
            try:
                overrides["price_per_1k"] = float(trace["__price_per_1k"])
            except (TypeError, ValueError):
                pass

        try:
            report = analyze_trace(trace, config=overrides or None)
        except Exception as exc:  # pragma: no cover - defensive
            self._send_json(500, {"error": f"analysis failed: {exc}"})
            return

        # Persist via the store so /api/report/<id> works.
        item = self.store.store(trace)
        # Re-run with overrides if needed by replacing the in-memory copy.
        if overrides:
            item.report = report
            item.summary = json.dumps(report.to_dict(), indent=2)
            folder = self.store.root / item.report_id
            (folder / "summary.json").write_text(item.summary, encoding="utf-8")
            item.html = render_html(report)
            item.svg = render_svg(report)
            (folder / "report.html").write_text(item.html, encoding="utf-8")
            (folder / "treemap.svg").write_text(item.svg, encoding="utf-8")

        self._send_json(
            200,
            {
                "report_id": item.report_id,
                "report": report.to_dict(),
            },
        )


# ---------------------------------------------------------------------------
# Multipart parsing (stdlib only)
# ---------------------------------------------------------------------------


def _parse_multipart_trace(content_type: str, body: bytes) -> dict[str, Any]:
    """Extract a JSON trace from a ``multipart/form-data`` upload.

    Looks for the first form field; if it's a file with a JSON filename, parse
    its bytes; otherwise treat its value as a JSON string.
    """
    m = re.search(r'boundary=(?:"([^"]+)"|([^;]+))', content_type, flags=re.IGNORECASE)
    if not m:
        raise ValueError("multipart boundary missing")
    boundary = (m.group(1) or m.group(2)).encode("ascii")
    sep = b"--" + boundary
    chunks = body.split(sep)
    for chunk in chunks:
        if not chunk or chunk in (b"\r\n", b"--\r\n", b"--"):
            continue
        if chunk.startswith(b"\r\n"):
            chunk = chunk[2:]
        head, _, body_bytes = chunk.partition(b"\r\n\r\n")
        if not head:
            continue
        try:
            head_text = head.decode("utf-8", errors="replace")
        except Exception:
            continue
        if "filename=" in head_text or 'name="file"' in head_text:
            stripped = body_bytes.rstrip(b"\r\n")
            return json.loads(stripped.decode("utf-8"))
        # Plain field: name="trace", value is JSON
        try:
            value = body_bytes.rstrip(b"\r\n").decode("utf-8")
            return json.loads(value)
        except Exception:
            continue
    raise ValueError("no usable field found in multipart payload")


def _load_sample_trace() -> dict[str, Any]:
    """Return the bundled example trace (read once, cached)."""
    global _SAMPLE_CACHE
    try:
        return _SAMPLE_CACHE  # type: ignore[name-defined]
    except NameError:
        pass
    here = Path(__file__).resolve().parent.parent
    candidates = [
        here / "examples" / "sample_trace.json",
        here.parent / "examples" / "sample_trace.json",
    ]
    for c in candidates:
        if c.exists():
            data = json.loads(c.read_text(encoding="utf-8"))
            _SAMPLE_CACHE = data
            return data
    _SAMPLE_CACHE = {}
    return {}


# ---------------------------------------------------------------------------
# Server factory + CLI
# ---------------------------------------------------------------------------


def create_handler(store: _ReportStore):  # type: ignore[no-untyped-def]
    """Build a handler class bound to a particular report store."""
    cls = type(
        "_BoundHandler",
        (_Handler,),
        {"store": store},
    )
    return cls


def build_server(host: str, port: int, store: _ReportStore) -> ThreadingHTTPServer:
    handler_cls = create_handler(store)
    return ThreadingHTTPServer((host, port), handler_cls)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="token-lens serve",
        description="Run the token-lens local web UI on a stdlib HTTP server.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="bind host (default 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8765, help="bind port (default 8765)")
    parser.add_argument(
        "--cache",
        default=None,
        help="directory to persist rendered artifacts (default: a temp dir)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="serve a single request then exit (used by smoke tests)",
    )
    args = parser.parse_args(argv)

    if args.cache:
        cache_dir = Path(args.cache).resolve()
    else:
        import tempfile

        cache_dir = Path(tempfile.mkdtemp(prefix="token-lens-"))
    cache_dir.mkdir(parents=True, exist_ok=True)

    store = _ReportStore(cache_dir)
    httpd = build_server(args.host, args.port, store)

    print(f"token-lens serve: http://{args.host}:{args.port}/")
    print(f"  cache: {cache_dir}")
    print(f"  health: http://{args.host}:{args.port}/healthz")

    if args.once:
        httpd.handle_request()
        httpd.server_close()
        return 0

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\ntoken-lens serve: shutting down")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
