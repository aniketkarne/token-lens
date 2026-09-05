# token-lens

> **Offline token analyzer for LLM prompts.** Classify zones, count tokens,
> score chunk utilization, flag boilerplate, recommend concrete savings,
> compare before/after, and render self-contained HTML treemaps — from a CLI,
> a Python API, or a local web UI.
> Zero network. Zero CDN. Python stdlib only.

<p align="center">
 <img width="1195" height="596" alt="image" src="https://github.com/user-attachments/assets/2d9824be-3df0-4272-a760-e3820f6dfcb7" />

</p>

```
+-----------------------+        +-------------------------+        +----------------------+
|  trace.json           |        |  token-lens             |        |  report.html         |
|  (model + messages    | -----> |  classify + tokenize    | -----> |  - inline SVG        |
|   + tools + RAG docs) |        |  + score + boilerplate  |        |  - zone breakdown    |
+-----------------------+        |  + cost estimate        |        |  - chunk scores      |
                                 +-------------------------+        |  - per-message list  |
        ^                                     |                     +----------------------+
        |                                     v
   web UI upload                   +-------------------------+
   (token-lens serve)  <---------- |  local HTTP server      |
                                   |  UI + JSON API          |
                                   +-------------------------+
```

---

## Why token-lens?

LLM prompts aren't a single blob. A modern prompt is a stack of **zones**
that compete for the same context window:

* `system`      — the operating instructions
* `tool_schema` — function/tool definitions
* `few_shot`    — worked examples
* `rag`         — retrieved document chunks
* `history`     — earlier turns
* `user` / `assistant` — the live exchange

Each zone costs tokens. Some zones (RAG, history) often dominate the budget
yet contribute the least useful signal per token. **token-lens** turns that
into a number, a score, and a visualization.

---

## Quickstart

```bash
# 1. Install
pip install -e .

# 2a. One-shot analysis (writes a self-contained HTML report)
token-lens analyze examples/sample_trace.json --model gpt-4o --open

# 2b. Or run the local web UI and drop traces in from the browser
token-lens serve                      # http://127.0.0.1:8765/

# 2c. See the wow-factor demo: before/after in one command
token-lens demo                       # writes demo-before.html, demo-after.html, demo-compare.md
```

All three paths use exactly the same analyzer. Nothing leaves your machine.

---

## ⚡ 60-second wow factor: `token-lens demo`

This is the killer use-case. Drop a real prompt in, drop a tightened version
in, and ask **how much did you save?** — in one command, no config:

```bash
$ token-lens demo
token-lens demo  (gpt-4o)
  before: 1,496 tokens  ($0.007480)
  after:  160 tokens  ($0.000800)
  saved: 1,336 tokens (-89.3%) ($0.006680)

  zone delta
    ↓ tool_schema       444 -> 93       (-351 tok)
    ↓ few_shot          103 -> 17       (-86 tok)
    ↓ rag               835 -> 32       (-803 tok)
    - history            96 -> —        (-96 tok)
```

The `before` trace (`examples/bloated_trace.json`) is deliberately noisy:
redundant system instructions, four overlapping tool schemas, six redundant
few-shot examples, eight RAG chunks with three that are completely off-topic,
eight turns of verbatim chat history, and a lot of marketing/legal filler.

The `after` trace (`examples/lean_trace.json`) is the same question answered
with a tight prompt. The demo command does the analysis, the comparison, and
the saving — and writes `demo-before.html`, `demo-after.html`, and
`demo-compare.md` so you can drop them straight into a PR.

### Bring your own before/after

```bash
token-lens demo --before path/to/old.json --after path/to/new.json \
    --model gpt-4o --out-dir ./demo-out --open
```

### Just want the numbers? `--quiet`

```bash
$ token-lens analyze examples/bloated_trace.json --quiet --model gpt-4o
token-lens: 1,496 tokens, $0.007480 cost, savings available: ~915 tok (~$0.004575) [2 recommendation(s)]
```

---

## Three ways to run it

### 1. `token-lens analyze` — batch / CI

```
token-lens analyze TRACE [options]

  TRACE                       Path to a JSON trace file.
  --model NAME                Model identifier (drives tokenizer + price table).
  --price-per-1k USD          Override price per 1K input tokens.
  -o, --output PATH           HTML output path (default: token-lens-report.html).
  --svg PATH                  Also write a standalone SVG treemap.
  --json PATH                 Also write a JSON summary.
  --open                      Open the HTML report in the default browser.
```

```bash
token-lens analyze examples/sample_trace.json --model gpt-4o \
    -o report.html --svg treemap.svg --json summary.json
```

The bare legacy form is still supported for backward compatibility:

```bash
token-lens examples/sample_trace.json --model gpt-4o
```

### 3. `token-lens compare` — diff two traces, savings-first

```
token-lens compare BEFORE.json AFTER.json [options]

  BEFORE.json          Path to the BEFORE trace JSON.
  AFTER.json           Path to the AFTER trace JSON.
  --model NAME         Model identifier (drives tokenizer + price table).
  --price-per-1k USD   Override price per 1K input tokens.
  --md PATH            Write a markdown summary to this path (PR-comment ready).
  --json PATH          Write a JSON diff to this path.
  --no-color           Disable ANSI color in output.
```

```bash
$ token-lens compare examples/bloated_trace.json examples/lean_trace.json --no-color
token-lens compare
  saved: 1,336 tokens (-89.3%) ($0.006680)

tokens:  1,496 -> 160  (-1,336, -89.3%)
cost:    $0.007480 -> $0.000800  ($-0.006680)
zones:
  ↓ tool_schema       444 -> 93       (-351 tok)
  ↓ few_shot          103 -> 17       (-86 tok)
  ↓ rag               835 -> 32       (-803 tok)
  - history            96 -> —        (-96 tok)
boilerplate risk: flagged_chunks 2 -> 0
recommendations for after: 1  (~32 tok more savings possible)
  • Drop 2 low-scoring RAG chunk(s) (~32 tok, ~$0.000160)
```

The compare output is **savings-first**: the first line is always the
headline savings in tokens (+ USD), and the zone table walks you through
**where** the bytes went.

### 4. `token-lens demo` — the 60-second wow-factor demo

```
token-lens demo [options]

  --before PATH        Override the BEFORE trace (default: examples/bloated_trace.json).
  --after PATH         Override the AFTER  trace (default: examples/lean_trace.json).
  --model NAME         Model identifier (default: gpt-4o).
  --out-dir DIR        Directory for written artifacts (default: cwd).
  --open               Open the AFTER HTML report in the browser.
  --no-color           Disable ANSI color.
```

The demo command runs the bundled before/after pair end-to-end, prints the
savings one-liner, and writes three artifacts you can drop into a PR:

* `demo-before.html` — self-contained HTML treemap of the bloated trace
* `demo-after.html`  — self-contained HTML treemap of the tight trace
* `demo-compare.md`  — markdown summary (zone table + recommendations)

### 2. `token-lens serve` — local web app

```
token-lens serve [options]

  --host HOST       Bind host (default: 127.0.0.1).
  --port PORT       Bind port (default: 8765).
  --cache DIR       Directory to persist rendered artifacts (default: temp dir).
  --once            Serve a single request then exit (smoke tests / CI).
```

```bash
token-lens serve --port 8765 --cache ./.token-lens-cache
# equivalent entry points:
token-lens-serve --port 8765
python -m token_lens.server --port 8765
```

The server is built on `http.server` from the standard library — **no Flask,
no FastAPI, no uvicorn, no npm, no CDN**. The UI is a single HTML page with
inline CSS and one inline script; the hero illustration is served from
`assets/hero.svg`.

What the UI does:

* upload a `.json` trace **or** paste JSON directly into the page
* optionally override `model` and `price per 1K tokens` per request
* load the bundled sample trace with one click
* show KPIs (total tokens, chars, messages, encoder, estimated cost, risk)
* show a per-zone bar breakdown with token counts and percentages
* link to the rendered report and to `.html` / `.svg` / `.json` downloads

### HTTP API

| Method | Route                          | Purpose                                            |
| ------ | ------------------------------ | -------------------------------------------------- |
| `POST` | `/api/upload`                  | Raw JSON body **or** `multipart/form-data` `file=@trace.json`. Returns `{report_id, report}`. |
| `GET`  | `/api/sample`                  | The bundled example trace as JSON.                 |
| `GET`  | `/api/report/<id>`             | JSON summary of a previously uploaded trace.       |
| `GET`  | `/api/download/<id>/html`      | Rendered self-contained HTML report (attachment).  |
| `GET`  | `/api/download/<id>/svg`       | Standalone SVG treemap.                            |
| `GET`  | `/api/download/<id>/json`      | Machine-readable summary.                          |
| `GET`  | `/api/download/<id>/trace`     | Echo of the original uploaded trace.               |
| `GET`  | `/reports/<id>`                | The HTML report rendered inline (no download).     |
| `GET`  | `/assets/hero.svg`             | The hero illustration (`image/svg+xml`).           |
| `GET`  | `/healthz`                     | Plain-text `ok` liveness probe.                    |

Per-request overrides are read from the uploaded JSON itself: a top-level
`"model"` key selects the tokenizer/price, and `"__price_per_1k"` overrides
the price table.

```bash
# start it
token-lens serve --port 8765 &

# health
curl -s http://127.0.0.1:8765/healthz            # -> ok

# analyze a trace and capture the report id
RID=$(curl -s -X POST -H 'content-type: application/json' \
        --data-binary @examples/sample_trace.json \
        http://127.0.0.1:8765/api/upload | python3 -c 'import sys,json;print(json.load(sys.stdin)["report_id"])')

# fetch the summary and the artifacts
curl -s http://127.0.0.1:8765/api/report/$RID
curl -sO http://127.0.0.1:8765/api/download/$RID/html

# multipart upload works too
curl -s -F file=@examples/sample_trace.json http://127.0.0.1:8765/api/upload
```

Uploads larger than 32 MB are rejected with `413`; malformed JSON returns
`400`; unknown report ids return `404`.

---

## Architecture

```
              +------------------+
              |   trace.json     |
              +---------+--------+
                        |
                        v
              +------------------+         +----------------------+
              |  parse.py        |  -----> |  MessageRecord       |
              |  (zone class.)   |         |  role, zone, content |
              +---------+--------+         +----------------------+
                        |
                        v
              +------------------+         +----------------------+
              |  tokenize.py     |  -----> |  TokenEncoder        |
              |  tiktoken/       |         |  - tiktoken          |
              |  transformers/   |         |  - transformers      |
              |  heuristic       |         |  - heuristic-bpe-lite|
              +---------+--------+         +----------------------+
                        |
                        v
              +------------------+         +----------------------+
              |  score.py        |  -----> |  ngram / LCS /       |
              |  (chunk util.)   |         |  containment         |
              +---------+--------+         +----------------------+
                        |
                        v
              +------------------+         +----------------------+
              |  boilerplate.py  |  -----> |  BoilerplateStats    |
              |  (filler + lost- |         |  risk + flagged      |
              |   in-the-middle) |         |  token totals        |
              +---------+--------+         +----------------------+
                        |
                        v
              +------------------+         +----------------------+
              |  report.py       |  -----> |  HTML + inline SVG   |
              |  (treemap + UI)  |         |  treemap             |
              +---------+--------+         +----------------------+
                        |
                        v
              +------------------+         +----------------------+
              |  server.py       |  -----> |  local UI + JSON API |
              |  (http.server)   |         |  artifact cache      |
              +------------------+         +----------------------+
```

---

## What you get in the HTML report

| Section            | What it tells you                                     |
| ------------------ | ------------------------------------------------------ |
| **Treemap**        | At-a-glance share of context window per zone          |
| **Zone breakdown** | Per-zone message count, tokens, characters, %          |
| **Chunk utilization** | RAG chunk score (n-gram / LCS / containment), boilerplate ratio, positional penalty |
| **Messages**       | Per-message role, zone, token count, content preview  |
| **Totals**         | Total tokens, chars, estimated USD cost, risk verdict |
| **Config**         | Echoed back for reproducibility                       |
| **Warnings**       | Anything noteworthy (e.g., empty trace, unknown zone) |

The HTML is **self-contained** — no `<script src=…>`, no `<link rel="stylesheet" href=…>`, no fonts. It works offline, behind a firewall, in air-gapped environments.

---

## Trace format

`token-lens` walks the JSON and classifies by **key name** (e.g., `tools`, `context_docs`, `few_shot_examples`, `chat_history`, `system_prompt`) and by **role** inside `messages` lists. The minimum you need:

```json
{
  "model": "gpt-4o",
  "system_prompt": "You are a helpful assistant.",
  "tools": [{"type": "function", "function": {"name": "search", "parameters": {}}}],
  "few_shot_examples": [{"input": "What is 2+2?", "output": "4"}],
  "context_docs": [{"text": "Apples are red fruits."}],
  "messages": [{"role": "user", "content": "Tell me about apples."}]
}
```

Unrecognized keys are still walked; messages are picked up by `role` + `content` anywhere they appear.

---

## Python API

```python
from token_lens import (
    analyze_file,
    render_html,
    render_svg,
    build_server,
    build_recommendations,
    compare_reports,
    render_compare_markdown,
)

report = analyze_file(
    "trace.json",
    config={"model": "gpt-4o", "price_per_1k": None},
)
print(report.total_tokens, report.zones)

# Heuristic, mechanical recommendations attached to every report
for r in report.recommendations:
    print(r.title, r.estimated_savings_tokens, r.confidence)

html = render_html(report)             # str, self-contained
svg = render_svg(report)               # str, standalone treemap
# or: from token_lens.report import write_html, write_svg

# Diff two reports, savings-first
before = analyze_file("before.json", config={"model": "gpt-4o"})
after = analyze_file("after.json", config={"model": "gpt-4o"})
cmp = compare_reports(before, after)
print(cmp.summary())
md = render_compare_markdown(cmp)
```

### Recommendations API

Every `AnalysisReport` carries a `recommendations: list[Recommendation]`
field. Each recommendation has a `kind`, `zone`, `estimated_savings_tokens`,
`estimated_savings_usd`, `confidence` (`high|medium|low`), `why`, and `how`:

| `kind`                            | Targets zone  | Trigger                                       |
| --------------------------------- | ------------- | --------------------------------------------- |
| `drop_low_score_chunks`           | `rag`         | Chunks scoring < 0.20 vs. last user query     |
| `drop_high_boilerplate_chunks`    | `rag`         | Chunks with boilerplate ratio >= 0.55         |
| `reorder_around_lost_in_middle`   | `rag`         | 5+ chunks: middle ones likely wasted         |
| `summarize_history`               | `history`     | History > 1,500 tokens                        |
| `trim_tool_schema`                | `tool_schema` | Tool zone > 600 tokens                        |
| `trim_few_shot`                   | `few_shot`    | Few-shot zone > 800 tokens                    |
| `shorten_system_prompt`           | `system`      | System zone > 800 tokens                      |
| `global_boilerplate_sweep`        | `rag`         | Aggregate boilerplate flagged                 |

Use them directly:

```python
from token_lens import build_recommendations
recs = build_recommendations(report)        # sorted by savings desc
top3 = recs[:3]
```

Or, from the CLI:

```bash
token-lens analyze examples/bloated_trace.json --model gpt-4o --quiet
# token-lens: 1,496 tokens, $0.007480 cost, savings available: ~915 tok (~$0.004575) [2 recommendation(s)]
```

Embedding the server:

```python
from pathlib import Path
from token_lens.server import _ReportStore, build_server

store = _ReportStore(Path("./.token-lens-cache"))
httpd = build_server("127.0.0.1", 8765, store)
httpd.serve_forever()
```

---

## Scoring

Every RAG chunk is scored against the inferred query (last `user` message) by
**three** normalized scorers and the best wins:

* **n-gram Jaccard** over 1- to 3-gram sets
* **LCS ratio** (`len(lcs) / max(|query|, |chunk|)`)
* **containment** (fraction of chunk tokens present in the query)

All scores are in `[0, 1]`.

### Boilerplate & positional risk

* **Boilerplate ratio** — share of stop-words / URL / template markers / repeated n-grams in a chunk.
* **Positional penalty** — parabolic weighting across the chunk list, peaking in the middle (lost-in-the-middle effect).

A chunk is flagged when **either** signal crosses a threshold; the report's "Boilerplate risk" KPI turns red if the aggregate is high.

---

## Tokenizers

Resolution order, with deterministic fallback:

1. **tiktoken** — when model name matches a known encoding (`gpt-4 → cl100k_base`, `gpt-4o → o200k_base`, …)
2. **transformers** — when a `transformers` model identifier is installed locally
3. **heuristic-bpe-lite** — pure-Python, byte-pair-ish whitespace + length-based splitter, **deterministic** across machines

The fallback is intentionally reproducible — given identical input it returns identical counts on every machine, every time, without any provider dependency.

Optional extras:

```bash
pip install -e ".[tiktoken]"       # exact OpenAI counts
pip install -e ".[transformers]"   # HF tokenizers
```

---

## Configuration reference

| Config key        | CLI flag           | API field          | Default          | Notes                            |
| ----------------- | ------------------ | ------------------ | ---------------- | -------------------------------- |
| `model`           | `--model`          | `"model"`          | (read from trace)| Drives tokenizer + price lookup  |
| `price_per_1k`    | `--price-per-1k`   | `"__price_per_1k"` | (from table)     | Overrides built-in pricing       |

Built-in pricing (per 1K input tokens, USD):

```
gpt-4o          $0.005
gpt-4o-mini     $0.00015
gpt-4           $0.03
gpt-3.5-turbo   $0.0015
claude-3-opus   $0.015
claude-3-sonnet $0.003
claude-3-haiku  $0.00025
gemini-1.5-pro  $0.0035
gemini-1.5-flash$0.00035
```

---

## Development

```bash
git clone https://github.com/aniketkarne-com/token-lens
cd token-lens
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[test]"
pytest                    # 81 tests
```

Smoke-test the server without leaving a process running:

```bash
token-lens serve --port 8765 --once   # handles one request, then exits
```

Layout:

```
token_lens/
  __init__.py     # public API (analyze, render, server, recommend, compare)
  types.py        # dataclasses (MessageRecord, AnalysisReport, ChunkInfo, ...)
  parse.py        # trace walker + zone classifier
  tokenize.py     # tiktoken / transformers / heuristic fallback
  score.py        # n-gram / LCS / containment scorers
  boilerplate.py  # boilerplate ratio + positional penalty
  pricing.py      # cost lookup table
  analyze.py      # analyze_trace + analyze_file (+ builds recommendations)
  report.py       # HTML + SVG treemap renderer (self-contained)
  recommend.py    # heuristic, savings-first recommendation engine
  compare.py      # CompareResult + render_compare_markdown
  server.py       # stdlib HTTP server: web UI + JSON API + artifact cache
  cli.py          # argparse CLI: analyze / compare / demo / serve
  py.typed        # PEP 561 marker
assets/           # hero.svg (served at /assets/hero.svg, used in this README)
tests/            # 81 tests across parser, tokenizers, scoring, report, analyze, server, recommend, compare, cli
examples/         # sample_trace.json, bloated_trace.json, lean_trace.json, summary.json, treemap.svg
```

---

## License

MIT
