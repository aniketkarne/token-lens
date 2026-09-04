"""Command-line interface for token-lens.

Two entry points:

* ``token-lens analyze TRACE [options]`` – analyze a trace, write HTML/SVG/JSON.
* ``token-lens serve [options]`` – run the local stdlib web server.

The bare ``token-lens TRACE.json`` form (no subcommand) is still supported for
backward compatibility.
"""

from __future__ import annotations

import argparse
import json
import sys
import webbrowser
from pathlib import Path
from typing import Sequence

from .analyze import analyze_file
from .report import write_html, write_svg


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="token-lens",
        description="Offline analyzer for LLM prompt token usage zones.",
    )

    # Common options applied to whichever mode the user is in.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--model", default=None, help="Model identifier")
    common.add_argument(
        "--price-per-1k",
        type=float,
        default=None,
        help="Override USD price per 1K input tokens",
    )

    sub = p.add_subparsers(dest="cmd")

    # analyze
    p_an = sub.add_parser(
        "analyze",
        parents=[common],
        help="Analyze a trace JSON file and emit HTML/SVG/JSON",
    )
    p_an.add_argument("trace", help="Path to a trace JSON file")
    p_an.add_argument(
        "-o", "--output",
        default="token-lens-report.html",
        help="Output HTML path (default: token-lens-report.html)",
    )
    p_an.add_argument("--svg", default=None,
                      help="Also write a standalone SVG treemap to this path")
    p_an.add_argument("--json", default=None,
                      help="Also write a JSON summary to this path")
    p_an.add_argument("--open", dest="open_after", action="store_true",
                      help="Open the HTML report in the default browser")

    # serve
    p_sv = sub.add_parser(
        "serve",
        help="Run the local stdlib web server (UI + API)",
    )
    p_sv.add_argument("--host", default="127.0.0.1",
                      help="bind host (default 127.0.0.1)")
    p_sv.add_argument("--port", type=int, default=8765,
                      help="bind port (default 8765)")
    p_sv.add_argument("--cache", default=None,
                      help="directory to persist rendered artifacts")
    p_sv.add_argument("--once", action="store_true",
                      help="serve a single request then exit (smoke test)")

    return p


def _build_legacy_parser() -> argparse.ArgumentParser:
    """Bare ``token-lens TRACE.json`` form, kept for backward compatibility."""
    p = argparse.ArgumentParser(
        prog="token-lens",
        description="Offline analyzer for LLM prompt token usage zones "
                    "(legacy single-file form).",
    )
    p.add_argument("trace", help="Path to a trace JSON file")
    p.add_argument("--model", default=None, help="Model identifier")
    p.add_argument("--price-per-1k", type=float, default=None,
                   help="Override USD price per 1K input tokens")
    p.add_argument("-o", "--output", default="token-lens-report.html",
                   help="Output HTML path (default: token-lens-report.html)")
    p.add_argument("--svg", default=None,
                   help="Also write a standalone SVG treemap to this path")
    p.add_argument("--json", default=None,
                   help="Also write a JSON summary to this path")
    p.add_argument("--open", dest="open_after", action="store_true",
                   help="Open the HTML report in the default browser")
    return p


def _run_analyze(args: argparse.Namespace) -> int:
    config = {"model": args.model, "price_per_1k": args.price_per_1k}
    try:
        report = analyze_file(args.trace, config=config)
    except FileNotFoundError:
        print(f"error: trace file not found: {args.trace}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(f"error: invalid JSON in trace file: {exc}", file=sys.stderr)
        return 2

    write_html(report, args.output)
    if args.svg:
        write_svg(report, args.svg)
    if args.json:
        Path(args.json).write_text(
            json.dumps(report.to_dict(), indent=2), encoding="utf-8"
        )

    print(f"token-lens: {report.total_tokens} tokens across {report.message_count} messages")
    print(f"  model: {report.model or '(unknown)'}")
    print(f"  encoder: {report.encoder_label}")
    print(f"  zones: " + ", ".join(
        f"{z.zone.value}={z.token_count}" for z in report.zones
    ))
    if report.estimated_cost_usd is not None:
        print(
            f"  estimated cost: ${report.estimated_cost_usd:.6f} "
            f"({report.cost_model_label})"
        )
    else:
        print("  estimated cost: n/a")
    print(f"  report: {args.output}")
    if args.svg:
        print(f"  svg: {args.svg}")
    if args.json:
        print(f"  json: {args.json}")

    if args.open_after:
        url = Path(args.output).resolve().as_uri()
        try:
            webbrowser.open(url)
        except Exception as exc:  # pragma: no cover
            print(f"warning: could not open browser: {exc}", file=sys.stderr)
    return 0


def _run_serve(args: argparse.Namespace) -> int:
    # Import here so the analyze path stays lightweight.
    from .server import main as serve_main

    argv: list[str] = ["--host", str(args.host), "--port", str(args.port)]
    if args.cache:
        argv.extend(["--cache", str(args.cache)])
    if args.once:
        argv.append("--once")
    return serve_main(argv)


def main(argv: Sequence[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    # If the user gave a subcommand, use the modern parser.
    if argv and argv[0] in {"analyze", "serve", "-h", "--help"}:
        parser = _build_parser()
        args = parser.parse_args(argv)
        if args.cmd == "analyze":
            return _run_analyze(args)
        if args.cmd == "serve":
            return _run_serve(args)
        parser.print_help()
        return 1

    # Otherwise, fall through to the legacy single-file form.
    legacy = _build_legacy_parser()
    try:
        args = legacy.parse_args(argv)
    except SystemExit:
        raise
    return _run_analyze(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
