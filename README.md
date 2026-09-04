# token-lens

> **Offline token analyzer for LLM prompts.** Classify zones, count tokens,
> score chunk utilization, flag boilerplate, and render self-contained HTML
> treemaps. Zero network. Zero CDN.

```
+-----------------------+        +-------------------------+        +----------------------+
|  trace.json           |        |  token-lens             |        |  report.html         |
|  (model + messages    | -----> |  classify + tokenize    | -----> |  - inline SVG        |
|   + tools + RAG docs) |        |  + score + boilerplate  |        |  - zone breakdown    |
+-----------------------+        |  + cost estimate        |        |  - chunk scores      |
                                 +-------------------------+        |  - per-message list  |
                                                                    +----------------------+
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

## Quickstart (3 steps)

```bash
# 1. Install
pip install -e .

# 2. Analyze a trace
token-lens examples/sample_trace.json --model gpt-4o --open

# 3. (Optional) Export machine-readable summary or standalone SVG
token-lens examples/sample_trace.json --model gpt-4o \
    --svg treemap.svg --json summary.json
```

That's it — open the HTML in any browser; no internet required.

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
              |  score.py        |  -----> |  ngram / LCS /      |
              |  (chunk util.)   |         |  containment        |
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

## CLI

```
token-lens TRACE [options]

  TRACE                       Path to a JSON trace file.
  --model NAME                Model identifier (drives tokenizer + price table).
  --price-per-1k USD          Override price per 1K input tokens.
  -o, --output PATH           HTML output path (default: token-lens-report.html).
  --svg PATH                  Also write a standalone SVG treemap.
  --json PATH                 Also write a JSON summary.
  --open                      Open the HTML report in the default browser.
```

### Trace format

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
from token_lens import analyze_file, render_html

report = analyze_file(
    "trace.json",
    config={"model": "gpt-4o", "price_per_1k": None},
)
print(report.total_tokens, report.zones)
render_html(report)             # returns str
# or: write_html(report, "report.html")
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

---

## Configuration reference

| Config key        | CLI flag           | Default          | Notes                                  |
| ----------------- | ------------------ | ---------------- | -------------------------------------- |
| `model`           | `--model`          | (read from trace)| Drives tokenizer + price lookup        |
| `price_per_1k`    | `--price-per-1k`   | (from table)     | Overrides built-in pricing             |

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
pytest                    # 50 tests, ~0.04s
```

Layout:

```
token_lens/
  __init__.py     # public API
  types.py        # dataclasses (MessageRecord, AnalysisReport, ChunkInfo, ...)
  parse.py        # trace walker + zone classifier
  tokenize.py     # tiktoken / transformers / heuristic fallback
  score.py        # n-gram / LCS / containment scorers
  boilerplate.py  # boilerplate ratio + positional penalty
  pricing.py      # cost lookup table
  analyze.py      # analyze_trace + analyze_file
  report.py       # HTML + SVG treemap renderer (self-contained)
  cli.py          # argparse CLI + --open
  py.typed        # PEP 561 marker
tests/            # 50 tests across parser, tokenizers, scoring, report, analyze
examples/         # sample_trace.json
```

---

## License

MIT
