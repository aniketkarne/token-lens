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
import os
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


def _default_db_path():
    """Default TraceStore path: ~/.local/share/token-lens/store.db (override via TOKEN_LENS_DB)."""
    override = os.environ.get("TOKEN_LENS_DB")
    if override:
        return Path(override)
    return Path.home() / ".local" / "share" / "token-lens" / "store.db"


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
    p_an.add_argument(
        "--tokenizer", default=None,
        help="Explicit tokenizer name (overrides --model for tokenizer selection)",
    )
    p_an.add_argument(
        "--custom-tokenizer", default=None,
        help="Path to a local HF-format tokenizer.json (overrides --tokenizer and --model)",
    )
    p_an.add_argument(
        "--no-color", action="store_true",
        help="Disable ANSI color in output",
    )

    # init
    p_init = sub.add_parser(
        "init",
        help="Scaffold token-lens.yaml, sample trace, and CI workflow into the current directory",
    )
    p_init.add_argument(
        "--force", action="store_true",
        help="Overwrite existing files (refuses by default)",
    )

    # check
    p_chk = sub.add_parser(
        "check",
        help="Compare trace files against a YAML budget; exit non-zero on breach",
    )
    p_chk.add_argument("--config", default="token-lens.yaml", help="Path to budget YAML (default: token-lens.yaml)")
    p_chk.add_argument("--json", default=None, help="Write a JSON breach report to this path")
    p_chk.add_argument("trace", nargs="+", help="One or more trace files (JSON or JSONL); globs are expanded")

    # ablation
    p_abl = sub.add_parser(
        "ablation",
        help="Show per-chunk RAG ablation scoring for a trace",
    )
    p_abl.add_argument("trace", help="Path to a trace JSON file")
    p_abl.add_argument("--no-color", action="store_true", help="Disable ANSI color in output")

    # ingest
    p_ing = sub.add_parser(
        "ingest",
        help="Ingest a JSONL log file into the local trace store",
    )
    p_ing.add_argument("--jsonl", required=True, help="Path to JSONL log file")
    p_ing.add_argument("--source", default="generic", choices=["generic", "openai", "anthropic"], help="Provider shape")
    p_ing.add_argument("--follow", action="store_true", help="Follow the file (poll for new lines)")
    p_ing.add_argument("--once", action="store_true", help="Run a single pass then exit (default)")
    p_ing.add_argument("--db", default=None, help="Path to the SQLite store")

    # stats
    p_st = sub.add_parser(
        "stats",
        help="Show aggregate stats across ingested traces",
    )
    p_st.add_argument("--last", type=int, default=100, help="Lookback window in traces (default: 100)")
    p_st.add_argument("--db", default=None, help="Path to the SQLite store")

    # optimize
    p_opt = sub.add_parser(
        "optimize",
        help="Aggregate stats and show cross-trace Pareto frontier + recommendations",
    )
    p_opt.add_argument("--db", default=None, help="Path to the SQLite store")
    p_opt.add_argument("--max-points", type=int, default=10, help="Max points on the Pareto curve (default: 10)")
    p_opt.add_argument("--min-coverage", type=float, default=0.9, help="Min trace coverage to recommend a chunk (default: 0.9)")
    p_opt.add_argument("--min-usefulness", type=float, default=0.2, help="Max mean usefulness to flag a chunk (default: 0.2)")
    p_opt.add_argument("--svg", default=None, help="Also write the Pareto SVG to this path")

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
    p_dmo.add_argument(
        "--svg", default=None,
        help="Also write the Pareto SVG (from the synthetic demo store) to this path",
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


def _run_init(args: argparse.Namespace) -> int:
    from .scaffold import scaffold, FileExists
    target = Path.cwd()
    try:
        written = scaffold(target, force=getattr(args, "force", False))
    except FileExists as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"token-lens: scaffolded {len(written)} file(s) into {target}")
    for p in written:
        try:
            rel = p.relative_to(target)
        except ValueError:
            rel = p
        print(f"  wrote: {rel}")
    return 0


def _run_ablation(args: argparse.Namespace) -> int:
    from .analyze import analyze_file

    trace_path = Path(args.trace)
    if not trace_path.exists():
        print("error: trace file not found: " + str(trace_path), file=sys.stderr)
        return 2
    try:
        report = analyze_file(str(trace_path))
    except Exception as exc:
        print("error: failed to analyze trace: " + str(exc), file=sys.stderr)
        return 2

    if report.ablation is None or not report.ablation.chunks:
        print("token-lens ablation: " + str(trace_path))
        print("  no RAG chunks found — nothing to score.")
        return 0

    abl = report.ablation
    print("token-lens ablation: " + str(trace_path))
    print("  " + "chunk_id".ljust(14) + " " + "tokens".rjust(8) + "  " + "useful".rjust(6) + "  verdict")
    for c in abl.chunks:
        cid = c.chunk_id or "(no id)"
        print("  " + cid.ljust(14) + " " + str(c.tokens).rjust(8) + "  " + ("%.2f" % c.usefulness).rjust(6) + "  " + c.verdict)
    print()
    print("  potential_removal_tokens=" + str(abl.potential_removal_tokens) + "  estimated_quality_delta=" + ("%+.3f" % abl.estimated_quality_delta))
    return 0


def _run_ingest(args):
    from .store import TraceStore
    from .ingest.jsonl import tail_jsonl

    log = Path(args.jsonl)
    db_path = Path(args.db) if args.db else _default_db_path()
    store = TraceStore(str(db_path))
    if not log.exists():
        print("warning: log file not found, nothing to ingest: " + str(log), file=sys.stderr)
        store.close()
        return 0
    n = tail_jsonl(str(log), store, source=args.source, follow=args.follow)
    print("ingested " + str(n) + " trace(s) from " + str(log) + " into " + str(db_path))
    store.close()
    return 0


def _run_stats(args):
    import statistics as _stats
    from .store import TraceStore

    db_path = Path(args.db) if args.db else _default_db_path()
    if not db_path.exists():
        print("token-lens stats: no store found at " + str(db_path) + " — run `token-lens ingest` first.")
        return 0
    store = TraceStore(str(db_path))
    rows = store.recent_traces(limit=args.last)
    if not rows:
        print("token-lens stats: store is empty — no traces ingested yet.")
        store.close()
        return 0
    tokens = [r["total_tokens"] for r in rows]
    costs = [r["cost_usd"] for r in rows]
    avg_tokens = sum(tokens) / len(tokens)
    p95 = _stats.quantiles(tokens, n=20)[18] if len(tokens) >= 20 else max(tokens)
    total_cost = sum(costs)
    print("token-lens stats  (last " + str(len(rows)) + " traces)")
    print("  avg total tokens:  " + str(int(avg_tokens)))
    print("  p95 total tokens:  " + str(int(p95)))
    print("  max total tokens:  " + str(max(tokens)))
    print("  total cost (USD):  $" + ("%.6f" % total_cost))
    print()
    print("  zone breakdown:")
    by_zone = store.zone_breakdown(lookback_traces=args.last)
    total_zone = sum(by_zone.values()) or 1
    for zone in sorted(by_zone.keys(), key=lambda z: -by_zone[z]):
        pct = 100.0 * by_zone[zone] / total_zone
        print("    " + zone.ljust(14) + " " + str(by_zone[zone]).rjust(8) + " tokens  (" + ("%.1f" % pct) + "%)")
    store.close()
    return 0


def _run_analyze(args: argparse.Namespace) -> int:
    config = {
        "model": args.model,
        "price_per_1k": args.price_per_1k,
        "tokenizer": getattr(args, "tokenizer", None),
        "custom_tokenizer_path": getattr(args, "custom_tokenizer", None),
    }
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


def _run_optimize(args):
    from .optimize import recommend_across_traces, compute_pareto
    from .pareto_render import render_pareto_ascii, render_pareto_svg
    from .store import TraceStore

    db_path = Path(args.db) if args.db else _default_db_path()
    if not db_path.exists():
        print("token-lens optimize: no store found at " + str(db_path) + " — run `token-lens ingest` first.")
        return 0
    store = TraceStore(str(db_path))
    aggregates = store.aggregate_ablations()
    if not aggregates:
        print("token-lens optimize: store has no ablation data yet — analyze traces with RAG chunks first.")
        store.close()
        return 0
    recs = recommend_across_traces(store, min_coverage=args.min_coverage, min_usefulness=args.min_usefulness)
    curve = compute_pareto(store, max_points=args.max_points)
    print("token-lens optimize  (" + str(db_path) + ")")
    print("")
    print("  " + str(len(aggregates)) + " unique chunks across " + str(max((a.get("trace_count") or 0) for a in aggregates)) + " traces")
    print("  " + str(len(recs)) + " recommendation(s):")
    for r in recs[:10]:
        print("    - remove " + ",".join(r.targets) + "  saves " + str(r.token_reduction) + " tok (~$" + ("%.4f" % r.cost_reduction_usd) + "/req)  coverage=" + ("%.1f%%" % (r.trace_coverage * 100)) + "  conf=" + r.confidence)
    print("")
    print(render_pareto_ascii(curve))
    if getattr(args, "svg", None):
        render_pareto_svg(curve, args.svg)
        print("wrote: " + str(args.svg))
    store.close()
    return 0


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
# check
# ---------------------------------------------------------------------------


def _run_check(args: argparse.Namespace) -> int:
    import glob as _glob
    from .budget import load_budget, check_budget
    from .analyze import analyze_trace

    try:
        cfg = load_budget(args.config)
    except FileNotFoundError as exc:
        print(f"error: config not found: {exc}", file=sys.stderr)
        return 2

    paths = []
    for raw in args.trace:
        expanded = _glob.glob(raw)
        if expanded:
            paths.extend(Path(p) for p in expanded)
        else:
            paths.append(Path(raw))

    all_files = []
    any_breach = False

    for p in paths:
        if not p.exists():
            print(f"error: trace file not found: {p}", file=sys.stderr)
            any_breach = True
            continue

        is_jsonl = p.suffix.lower() in (".jsonl", ".ndjson")
        records = []
        if is_jsonl:
            for lineno, raw in enumerate(p.read_text(encoding="utf-8").splitlines(), start=1):
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    records.append((f"{p}:{lineno}", json.loads(raw)))
                except json.JSONDecodeError as exc:
                    print(f"error: invalid JSON at {p}:{lineno}: {exc}", file=sys.stderr)
                    any_breach = True
        else:
            try:
                records.append((str(p), json.loads(p.read_text(encoding="utf-8"))))
            except json.JSONDecodeError as exc:
                print(f"error: invalid JSON in {p}: {exc}", file=sys.stderr)
                any_breach = True

        file_breaches = []
        for label, trace in records:
            try:
                report = analyze_trace(trace, config={"model": trace.get("model", "gpt-4o")})
            except Exception as exc:
                print(f"error: failed to analyze {label}: {exc}", file=sys.stderr)
                any_breach = True
                continue
            breaches = check_budget(cfg, report)
            file_breaches.append({"record": label, "breaches": [
                {"code": b.code, "actual": b.actual, "limit": b.limit, "severity": b.severity}
                for b in breaches
            ]})
            if breaches:
                any_breach = True
                for b in breaches:
                    print(f"  ✗ {label}: {b.code}  actual={b.actual:.0f}  limit={b.limit:.0f}")
            else:
                print(f"  ✓ {label}: under budget ({report.total_tokens} tokens)")

        if records:
            all_files.append({"path": str(p), "breaches": file_breaches})

    if args.json:
        Path(args.json).write_text(json.dumps({"config": args.config, "files": all_files}, indent=2), encoding="utf-8")
        print(f"  wrote: {args.json}")

    return 1 if any_breach else 0


# ---------------------------------------------------------------------------
# demo
# ---------------------------------------------------------------------------


def _build_demo_store():
    """Build an in-memory TraceStore seeded with synthetic RAG traces.

    30 traces. 12 chunks per trace: 4 highly useful, 8 progressively less
    useful. Aggregates are designed to surface at least one chunk with high
    coverage and low mean usefulness so the Pareto curve has a visible knee.
    """
    import tempfile

    from .store import TraceStore

    fd, path = tempfile.mkstemp(prefix="tl_demo_", suffix=".db")
    os.close(fd)
    store = TraceStore(path)

    # (chunk_id, usefulness, tokens_per_trace). Per-trace total tokens scales
    # across all chunks so a Pareto curve has multiple knee points.
    chunks = [
        # highly useful (kept).
        ("system_prompt", 0.92, 80),
        ("product_docs", 0.85, 140),
        ("user_history", 0.78, 110),
        ("tools_schema", 0.72, 60),
        # borderline.
        ("few_shot_examples", 0.45, 90),
        ("tone_guidance", 0.55, 40),
        # redundant / low-value.
        ("marketing_filler", 0.05, 180),
        ("legal_disclaimer", 0.04, 150),
        ("duplicate_footer", 0.03, 120),
        ("stale_release_notes", 0.06, 95),
        # off-topic (worst).
        ("offtopic_blog_excerpt", 0.02, 200),
        ("random_documentation", 0.01, 160),
    ]

    n_traces = 30
    for i in range(n_traces):
        trace_id = store.insert_trace({
            "timestamp": "2026-09-13T00:00:%02dZ" % i,
            "model": "gpt-4o",
            "total_tokens": sum(t for _, _, t in chunks),
            "cost_usd": 0.005,
            "messages": [],
            "zones": [],
        })
        for chunk_id, usefulness, tokens in chunks:
            verdict = "useful" if usefulness >= 0.2 else "irrelevant"
            store.insert_ablation(trace_id=trace_id, chunk_id=chunk_id, usefulness=usefulness, verdict=verdict, tokens=tokens)

    return store, path


def _run_demo(args: argparse.Namespace) -> int:
    from .analyze import analyze_file
    from .compare import compare_reports, render_compare_markdown
    from .optimize import compute_pareto, recommend_across_traces
    from .pareto_render import render_pareto_ascii, render_pareto_svg
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

    # Phase 10 — Pareto + cross-trace recommendations from a synthetic store.
    store, store_path = _build_demo_store()
    try:
        curve = compute_pareto(store, max_points=8)
        recs = recommend_across_traces(store, min_coverage=0.9, min_usefulness=0.2)
    finally:
        try:
            store.close()
            os.unlink(store_path)
        except OSError:  # pragma: no cover
            pass

    print()
    print(_c(use_color, _BOLD) + "QUALITY vs TOKENS — Pareto frontier" + _c(use_color, _RESET))
    print()
    print(render_pareto_ascii(curve))
    if recs:
        print()
        print(_c(use_color, _BOLD) + "Top cross-trace recommendations" + _c(use_color, _RESET))
        for i, r in enumerate(recs[:5], start=1):
            print(
                f"  {i}. remove " + ",".join(r.targets)
                + f"  saves {r.token_reduction:,} tok"
                + f" (${r.cost_reduction_usd:.4f}/req)"
                + f"  coverage={r.trace_coverage*100:.1f}%"
                + f"  conf={r.confidence}"
            )
    else:
        print()
        print(_c(use_color, _GREEN) + "  no mechanical savings found — your prompt is already tight!" + _c(use_color, _RESET))

    if getattr(args, "svg", None):
        from .store import TraceStore as _TS
        store2, store_path2 = _build_demo_store()
        try:
            curve2 = compute_pareto(store2, max_points=8)
            render_pareto_svg(curve2, args.svg)
        finally:
            try:
                store2.close()
                os.unlink(store_path2)
            except OSError:  # pragma: no cover
                pass
        print()
        print(f"  svg: {args.svg}")

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

    if argv and argv[0] in {"analyze", "serve", "compare", "demo", "init", "check", "ablation", "ingest", "stats", "optimize", "-h", "--help"}:
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
        if args.cmd == "init":
            return _run_init(args)
        elif args.cmd == "check":
            return _run_check(args)
        elif args.cmd == "ablation":
            return _run_ablation(args)
        elif args.cmd == "ingest":
            return _run_ingest(args)
        elif args.cmd == "stats":
            return _run_stats(args)
        elif args.cmd == "optimize":
            return _run_optimize(args)
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
