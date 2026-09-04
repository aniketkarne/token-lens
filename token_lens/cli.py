"""Command-line interface for token-lens."""

from __future__ import annotations

import argparse
import json
import sys
import webbrowser
from pathlib import Path

from .analyze import analyze_file
from .report import write_html, write_svg


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="token-lens",
        description="Offline analyzer for LLM prompt token usage zones.",
    )
    p.add_argument("trace", help="Path to a trace JSON file")
    p.add_argument(
        "--model",
        default=None,
        help="Model identifier (e.g. gpt-4o, claude-3-haiku). Used to pick a tokenizer and price.",
    )
    p.add_argument(
        "--price-per-1k",
        type=float,
        default=None,
        help="Override USD price per 1K input tokens (skips the default pricing table).",
    )
    p.add_argument(
        "--output",
        "-o",
        default="token-lens-report.html",
        help="Output HTML path (default: token-lens-report.html).",
    )
    p.add_argument(
        "--svg",
        default=None,
        help="Also write a standalone SVG treemap to this path.",
    )
    p.add_argument(
        "--json",
        default=None,
        help="Also write a machine-readable JSON summary to this path.",
    )
    p.add_argument(
        "--open",
        dest="open_after",
        action="store_true",
        help="Open the HTML report in the default browser after generation.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

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
        Path(args.json).write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")

    # Console summary
    print(f"token-lens: {report.total_tokens} tokens across {report.message_count} messages")
    print(f"  model: {report.model or '(unknown)'}")
    print(f"  encoder: {report.encoder_label}")
    print(f"  zones: " + ", ".join(f"{z.zone.value}={z.token_count}" for z in report.zones))
    if report.estimated_cost_usd is not None:
        print(f"  estimated cost: ${report.estimated_cost_usd:.6f} ({report.cost_model_label})")
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


if __name__ == "__main__":
    raise SystemExit(main())
