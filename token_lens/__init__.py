"""token-lens: offline analyzer for LLM prompt token usage zones.

Public API:
    analyze_trace(trace) -> AnalysisReport
    analyze_file(path) -> AnalysisReport
    render_html(report, output_path) -> None
    render_svg(report, output_path) -> None
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
]

__version__ = "0.1.0"
