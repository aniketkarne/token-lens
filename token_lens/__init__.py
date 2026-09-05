"""token-lens: offline analyzer for LLM prompt token usage zones.

Public API:

    analyze_trace(trace)        -> AnalysisReport
    analyze_file(path)          -> AnalysisReport
    render_html(report, path)   -> None
    render_svg(report, path)    -> None
    build_server(host, port, s) -> ThreadingHTTPServer (web UI)
    build_recommendations(r)    -> list[Recommendation]
    compare_reports(b, a)       -> CompareResult
    render_compare_markdown(c)  -> str
"""

from typing import Any

from .types import (
    AnalysisReport,
    ChunkInfo,
    MessageRecord,
    ZoneBreakdown,
    ZoneKind,
)
from .analyze import analyze_file, analyze_trace
from .report import render_html, render_svg


def build_server(*args: Any, **kwargs: Any) -> Any:
    """Build the local web server with a lazy import."""
    from .server import build_server as _build_server

    return _build_server(*args, **kwargs)


def build_recommendations(*args: Any, **kwargs: Any) -> Any:
    """Build recommendations from an AnalysisReport (lazy import)."""
    from .recommend import build_recommendations as _build

    return _build(*args, **kwargs)


def compare_reports(*args: Any, **kwargs: Any) -> Any:
    """Compare two AnalysisReports (lazy import)."""
    from .compare import compare_reports as _cmp

    return _cmp(*args, **kwargs)


def render_compare_markdown(*args: Any, **kwargs: Any) -> Any:
    """Render a markdown compare summary (lazy import)."""
    from .compare import render_compare_markdown as _r

    return _r(*args, **kwargs)


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
    "build_recommendations",
    "compare_reports",
    "render_compare_markdown",
]

__version__ = "0.3.0"
