"""token-lens: offline analyzer for LLM prompt token usage zones.

Public API:
    analyze_trace(trace) -> AnalysisReport
    analyze_file(path) -> AnalysisReport
    render_html(report, output_path) -> None
    render_svg(report, output_path) -> None
    build_server(host, port, store) -> ThreadingHTTPServer  (web UI)
"""

from __future__ import annotations

from .types import (
    AnalysisReport,
    ChunkInfo,
    MessageRecord,
    ZoneBreakdown,
    ZoneKind,
)
from .analyze import analyze_file, analyze_trace
from .report import render_html, render_svg
from .server import build_server

__all__ = [
    "AnalysisReport",
    "ChunkInfo",
    "MessageRecord",
    "ZoneBreakdown",
    "ZoneKind",
    "analyze_file",
    "analyze_trace",
    "render_html",
    "render_svg",
    "build_server",
]

__version__ = "0.2.0"
