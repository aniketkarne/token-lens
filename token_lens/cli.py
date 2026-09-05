"""Command-line interface for token-lens.

Subcommands:

* ``token-lens analyze TRACE [options]`` - analyze a trace, write HTML/SVG/JSON.
* ``token-lens compare BEFORE.json AFTER.json [options]`` - diff two reports,
  print a savings-first summary, optionally write a markdown or JSON diff.
* ``token-lens serve [options]`` - run the local stdlib web server.
* ``token-lens demo [options]`` - one-command dramatic before/after demo using
  the bundled ``bloated_trace.json`` and ``lean_trace.json`` examples.

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
from .recommend import total_estimated_savings
from .report import write_html, write_svg


# Where the bundled demo fixtures live. Resolved relative to this file so it
# works no matter where the package is installed.
_HERE = Path(__file__).resolve().parent
_EXAMPLES_DIR = _HERE.parent / "examples"


def _examples_path(*parts: str) -> Path:
    return _EXAMPLES_DIR.joinpath(*parts)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="token-lens",
        description="Offline analyzer for LLM prompt token usage zones.",
    )

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
    p_an.add_argument("--md", default=None,
                      help="Also write a markdown savings summary to this path")
    p_an.add_argument("--open", dest="open_after", action="store_true",
                      help="Open the HTML report in the default browser")
    p_an.add_argument("--quiet", action="store_true",
                      help="Print only the savings-first one-liner")

    # compare
    p_cmp = sub.add_parser(
        "compare",
        parents=[common],
        help="Diff two trace JSON files and print savings-first output",
    )
    p_cmp.add_argument("before", help="Path to the BEFORE trace JSON")
    p_cmp.add_argument("after", help="Path to the AFTER trace JSON")
    p_cmp.add_argument(
        "--md", default=None,
        help="Write a markdown summary to this path",
    )
    p_cmp.add_argument(
        "--json", default=None,
        help="Write a JSON diff to this path",
    )
    p_cmp.add_argument(
        "--no-color", action="store_true",
        help="Disable ANSI color in output",
    )

    # demo
    p_dmo = sub.add_parser(
        "demo",
        help="Run the bundled before/after demo and print a savings one-liner",
    )
    p_dmo.add_argument(
        "--before", default=None,
        help="Override path to the BEFORE trace (default: examples/bloated_trace.json)",
    )
    p_dmo.add_argument(
        "--after", default=None,
        help="Override path to the AFTER trace (default: examples/lean_trace.json)",
    )
    p_dmo.add_argument(
        "--open", dest="open_after", action="store_true",
        help="Open the AFTER HTML report in the default browser after the demo",
    )
    p_dmo.add_argument(
        "--model", default="gpt-4o",
        help="Model identifier to drive tokenization + pricing (default: gpt-4o)",
    )
    p_dmo.add_argument(
        "--out-dir", default=None,
        help="Directory for written artifacts (default: cwd)",
    )
    p_dmo.add_argument(
        "--no-color", action="store_true",
        help="Disable ANSI color in output",
    )

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
    p.add_argument("--md", default=None,
                   help="Also write a markdown savings summary to this path")
    p.add_argument("--open", dest="open_after", action="store_true",
                   help="Open the HTML report in the default browser")
    p.add_argument("--quiet", action="store_true",
                   help="Print only the savings-first one-liner")
    return p


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _c(use_color: bool, code: str) -> str:
    if not use_color:
        return ""
    return code


_BOLD = "\x1b[1m"
_DIM = "\x1b[2m"
_RESET = "\x1b[0m"
_RED = "\x1b[31m"
_GREEN = "\x1b[32m"
_YELLOW = "\x1b[33m"
_CYAN = "\x1b[36m"


def _fmt_tokens(n: int) -> str:
    return f"{n:,}"


def _fmt_cost(c: float | None) -> str:
    if c is None:
        return "n/a"
    return f"${c:.6f}"


def _analyze_print_savings(report, use_color: bool = True, quiet: bool = False) -> None:
    """Print a savings-first summary for one analysis report."""
    recs = report.recommendations or []
    tok_save, usd_save = total_estimated_savings(recs)
    has_cost = report.estimated_cost_usd is not None
    pct = (tok_save / report.total_tokens * 100) if report.total_tokens else 0.0

    if quiet:
        line = (
            f"token-lens: {_fmt_tokens(report.total_tokens)} tokens, "
            f"{_fmt_cost(report.estimated_cost_usd)} cost, "
            f"savings available: ~{_fmt_tokens(tok_save)} tok "
        )
        if has_cost and usd_save is not None:
            line += f"(~${usd_save:.6f}) "
        line += f"[{len(recs)} recommendation(s)]"
        print(line)
        return

    print(_c(use_color, _BOLD) + "token-lens analyze" + _c(use_color, _RESET))
    print(f"  trace:        {report.config.get('__trace_path', '(unknown)')}" if "__trace_path" in report.config else "")
    print(f"  model:        {report.model or '(unknown)'}")
    print(f"  encoder:      {report.encoder_label} ({report.tokenizer_source})")
    print(
        f"  total:        {_c(use_color, _CYAN)}{_fmt_tokens(report.total_tokens)} tokens"
        f"{_c(use_color, _RESET)} across {report.message_count} messages"
    )
    if has_cost:
        print(f"  cost:         {_fmt_cost(report.estimated_cost_usd)} ({report.cost_model_label})")
    else:
        print("  cost:         n/a")
    print(
        f"  savings:      {_c(use_color, _GREEN)}~{_fmt_tokens(tok_save)} tok ({pct:.1f}%){_c(use_color, _RESET)}"
        + (
            f"  /  ~${usd_save:.6f}"
            if has_cost and usd_save is not None
            else ""
        )
    )
    print()
    if recs:
        print(_c(use_color, _BOLD) + "Top recommendations" + _c(use_color, _RESET))
        for i, r in enumerate(recs[:5], start=1):
            usd = (
                f" (~${r.estimated_savings_usd:.6f})"
                if r.estimated_savings_usd is not None
                else ""
            )
            print(
                f"  {i}. {_c(use_color, _GREEN)}{r.title}{_c(use_color, _RESET)}\n"
                f"     ~{_fmt_tokens(r.estimated_savings_tokens)} tok{usd} [{r.confidence}]\n"
                f"     why: {r.why}\n"
                f"     how: {r.how}"
            )
        if len(recs) > 5:
            print(f"  ... and {len(recs) - 5} more")
    else:
        print(_c(use_color, _GREEN) + "  no mechanical savings found — your prompt is already tight!" + _c(use_color, _RESET))


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

    # Echo the source path so the savings summary can include it.
    try:
        # ``AnalysisReport.config`` is a Mapping; clone before mutating.
        report.config = {**report.config, "__trace_path": str(Path(args.trace).resolve())}
    except Exception:  # pragma: no cover
        pass

    write_html(report, args.output)
    if args.svg:
        write_svg(report, args.svg)
    if args.json:
        Path(args.json).write_text(
            json.dumps(report.to_dict(), indent=2), encoding="utf-8"
        )
    if args.md:
        Path(args.md).write_text(_analyze_markdown(report), encoding="utf-8")

    if getattr(args, "quiet", False):
        _analyze_print_savings(report, use_color=True, quiet=True)
    else:
        _analyze_print_savings(report, use_color=True, quiet=False)

    print()
    print(f"  wrote:        {args.output}")
    if args.svg:
        print(f"  svg:          {args.svg}")
    if args.json:
        print(f"  json:         {args.json}")
    if args.md:
        print(f"  md:           {args.md}")

    if args.open_after:
        url = Path(args.output).resolve().as_uri()
        try:
            webbrowser.open(url)
        except Exception as exc:  # pragma: no cover
            print(f"warning: could not open browser: {exc}", file=sys.stderr)
    return 0


def _analyze_markdown(report) -> str:
    """Markdown savings summary for a single report."""
    recs = report.recommendations or []
    tok_save, usd_save = total_estimated_savings(recs)
    lines = [
        f"# token-lens: {Path(str(report.config.get('__trace_path', 'trace.json'))).name}",
        "",
        f"- tokens: **{_fmt_tokens(report.total_tokens)}**",
        f"- model: `{report.model or '(unknown)'}`",
        f"- encoder: `{report.encoder_label}` ({report.tokenizer_source})",
    ]
    if report.estimated_cost_usd is not None:
        lines.append(f"- cost: `${report.estimated_cost_usd:.6f}` ({report.cost_model_label})")
    lines += [
        f"- savings available: **~{_fmt_tokens(tok_save)} tok**"
        + (f" (~${usd_save:.6f})" if usd_save is not None else ""),
        "",
        "## Recommendations",
        "",
    ]
    if not recs:
        lines.append("_No mechanical savings found._")
    else:
        for r in recs:
            usd = (
                f" (~${r.estimated_savings_usd:.6f})"
                if r.estimated_savings_usd is not None
                else ""
            )
            lines += [
                f"### {r.title}",
                "",
                f"- ~{_fmt_tokens(r.estimated_savings_tokens)} tok{usd}  -  confidence: {r.confidence}",
                f"- why: {r.why}",
                f"- how: {r.how}",
                "",
            ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# compare
# ---------------------------------------------------------------------------


def _run_compare(args: argparse.Namespace) -> int:
    from .compare import compare_reports, render_compare_markdown

    config = {"model": args.model, "price_per_1k": args.price_per_1k}
    try:
        before = analyze_file(args.before, config=config)
    except FileNotFoundError:
        print(f"error: trace not found: {args.before}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(f"error: invalid JSON in {args.before}: {exc}", file=sys.stderr)
        return 2

    try:
        after = analyze_file(args.after, config=config)
    except FileNotFoundError:
        print(f"error: trace not found: {args.after}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(f"error: invalid JSON in {args.after}: {exc}", file=sys.stderr)
        return 2

    cmp = compare_reports(before, after)
    use_color = not getattr(args, "no_color", False)

    # Top-line savings one-liner (always), colored.
    saving_tok = -cmp.delta_tokens  # positive when after < before
    saving_usd = (
        -(cmp.delta_cost_usd or 0.0) if cmp.delta_cost_usd is not None else None
    )
    print(_c(use_color, _BOLD) + "token-lens compare" + _c(use_color, _RESET))
    if saving_tok > 0:
        verb = _c(use_color, _GREEN) + "saved" + _c(use_color, _RESET)
        extra = (
            f" (${saving_usd:.6f})" if saving_usd is not None and saving_usd > 0 else ""
        )
        print(
            f"  {verb}: {_fmt_tokens(saving_tok)} tokens "
            f"({cmp.delta_pct * 100:+.1f}%){extra}"
        )
    elif saving_tok < 0:
        verb = _c(use_color, _RED) + "added" + _c(use_color, _RESET)
        print(
            f"  {verb}: {_fmt_tokens(-saving_tok)} tokens "
            f"({cmp.delta_pct * 100:+.1f}%)"
        )
    else:
        print("  no change")
    print()
    print(cmp.summary())

    if args.md:
        Path(args.md).write_text(render_compare_markdown(cmp), encoding="utf-8")
        print(f"  md:     {args.md}")
    if args.json:
        Path(args.json).write_text(
            json.dumps(cmp.to_dict(), indent=2), encoding="utf-8"
        )
        print(f"  json:   {args.json}")

    return 0


# ---------------------------------------------------------------------------
# demo
# ---------------------------------------------------------------------------


def _run_demo(args: argparse.Namespace) -> int:
    from .analyze import analyze_file
    from .compare import compare_reports, render_compare_markdown
    from .report import write_html

    before_path = Path(args.before) if args.before else _examples_path("bloated_trace.json")
    after_path = Path(args.after) if args.after else _examples_path("lean_trace.json")
    out_dir = Path(args.out_dir) if args.out_dir else Path.cwd()
    out_dir.mkdir(parents=True, exist_ok=True)
    use_color = not getattr(args, "no_color", False)

    config = {"model": args.model, "price_per_1k": None}
    before = analyze_file(str(before_path), config=config)
    after = analyze_file(str(after_path), config=config)
    cmp = compare_reports(before, after)

    before_html = out_dir / "demo-before.html"
    after_html = out_dir / "demo-after.html"
    write_html(before, str(before_html))
    write_html(after, str(after_html))
    md_path = out_dir / "demo-compare.md"
    md_path.write_text(render_compare_markdown(cmp), encoding="utf-8")

    # One-liner.
    saving_tok = -cmp.delta_tokens
    saving_usd = -(cmp.delta_cost_usd or 0.0) if cmp.delta_cost_usd is not None else None
    if saving_tok > 0:
        verb = _c(use_color, _GREEN) + "saved" + _c(use_color, _RESET)
        usd_part = (
            f" ({_c(use_color, _GREEN)}${saving_usd:.6f}{_c(use_color, _RESET)})"
            if saving_usd is not None and saving_usd > 0
            else ""
        )
    else:
        verb = _c(use_color, _RED) + "added" + _c(use_color, _RESET)
        usd_part = ""
    print(
        _c(use_color, _BOLD)
        + "token-lens demo"
        + _c(use_color, _RESET)
        + f"  ({args.model})"
    )
    print(
        f"  before: {_fmt_tokens(before.total_tokens)} tokens  "
        f"({_fmt_cost(before.estimated_cost_usd)})"
    )
    print(
        f"  after:  {_fmt_tokens(after.total_tokens)} tokens  "
        f"({_fmt_cost(after.estimated_cost_usd)})"
    )
    print(
        f"  {verb}: {_fmt_tokens(saving_tok)} tokens "
        f"({cmp.delta_pct * 100:+.1f}%){usd_part}"
    )
    print()
    # Brief zone breakdown.
    print(_c(use_color, _DIM) + "  zone delta" + _c(use_color, _RESET))
    for z in cmp.zones:
        if z.direction in {"same"}:
            continue
        arrow = {"down": "↓", "up": "↑", "new": "+", "removed": "-"}[z.direction]
        b = "—" if z.before_tokens is None else f"{z.before_tokens:,}"
        a = "—" if z.after_tokens is None else f"{z.after_tokens:,}"
        color = _GREEN if z.direction == "down" else (_YELLOW if z.direction == "up" else _DIM)
        print(
            f"    {arrow} {z.zone:<12} {b:>8} -> {a:<8} "
            f"({_c(use_color, color)}{z.delta_tokens:+,}{_c(use_color, _RESET)} tok)"
        )
    print()
    print(f"  wrote:")
    print(f"    before html: {before_html}")
    print(f"    after  html: {after_html}")
    print(f"    compare md:  {md_path}")

    if args.open_after:
        url = after_html.resolve().as_uri()
        try:
            webbrowser.open(url)
        except Exception as exc:  # pragma: no cover
            print(f"warning: could not open browser: {exc}", file=sys.stderr)
    return 0


# ---------------------------------------------------------------------------
# serve + entry
# ---------------------------------------------------------------------------


def _run_serve(args: argparse.Namespace) -> int:
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

    if argv and argv[0] in {"analyze", "serve", "compare", "demo", "-h", "--help"}:
        parser = _build_parser()
        args = parser.parse_args(argv)
        if args.cmd == "analyze":
            return _run_analyze(args)
        if args.cmd == "compare":
            return _run_compare(args)
        if args.cmd == "demo":
            return _run_demo(args)
        if args.cmd == "serve":
            return _run_serve(args)
        parser.print_help()
        return 1

    legacy = _build_legacy_parser()
    try:
        args = legacy.parse_args(argv)
    except SystemExit:
        raise
    return _run_analyze(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
