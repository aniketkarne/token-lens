# token-lens

> **Find the minimum context needed to preserve answer quality.**
> Heuristic ablation, cross-trace Pareto frontier, and a CLI budget CI
> for LLM prompts — offline, stdlib-only, no cloud.

## The thesis

Every RAG prompt has chunks that don't earn their tokens. token-lens finds them — and shows you the **frontier** between quality and cost.

```
$ token-lens demo

QUALITY vs TOKENS  (Pareto frontier)

      *..
         ...
            .....
                 ...
                    .....
                         ...
                            .....
                                 ....
                                     ....
                                         ...
                                            .....
                                                 .

  tokens: 0                                   42750

Top cross-trace recommendations
  1. remove offtopic_blog_excerpt  saves 6,000 tok ($0.0300/req)  coverage=100.0%  conf=high
  2. remove marketing_filler       saves 5,400 tok ($0.0270/req)  coverage=100.0%  conf=high
  3. remove random_documentation   saves 4,800 tok ($0.0240/req)  coverage=100.0%  conf=high
  4. remove legal_disclaimer       saves 4,500 tok ($0.0225/req)  coverage=100.0%  conf=high
  5. remove duplicate_footer       saves 3,600 tok ($0.0180/req)  coverage=100.0%  conf=high
```

That chart is the **whole product in one picture**. The curve says: *"here's how much quality you keep at every context budget."* No other tool does this.

## Quickstart

```bash
pip install token-lens
token-lens init                 # scaffold token-lens.yaml + GitHub Actions workflow
token-lens demo                 # see the Pareto chart with synthetic data
token-lens analyze your_trace.json     # analyze a real trace
token-lens ingest --jsonl logs/req.jsonl     # tail a real log
token-lens optimize --db ~/.local/share/token-lens/store.db     # Pareto from real traces
token-lens check --config token-lens.yaml logs/*.jsonl   # CI budget check
token-lens serve               # local web UI at http://127.0.0.1:8793
```

## What it does

- **Real tokenizers** — tiktoken (cl100k_base, o200k_base), HuggingFace `tokenizers` (your local `.json` files), and a deterministic heuristic fallback. Every report carries the tokenizer name and an honest `⚠ approximate` badge when the heuristic is in play.
- **Per-chunk RAG ablation** — for every chunk in your trace: query similarity, cross-chunk redundancy, usefulness verdict (`useful` / `marginal` / `irrelevant`), and an estimated quality delta if you removed it.
- **Cross-trace Pareto frontier** — across many traces, aggregate by chunk_id and compute a quality-vs-tokens frontier. Confidence-rated recommendations: *remove these N chunks, save X tokens, costs $Y/request, covered in Z% of traces*.
- **Token budget CI** — `token-lens check --config token-lens.yaml` exits non-zero on breach. Drop the GitHub Actions workflow into `.github/workflows/` and your PR fails when a trace exceeds the budget.
- **Live trace ingest** — `token-lens ingest --jsonl logs/req.jsonl --source openai` tails a JSONL log into a local SQLite store with byte-offset checkpointing. Then `token-lens stats --last 100` prints avg/p95/zone breakdown.
- **Local web UI** — `token-lens serve` starts an stdlib HTTP server with an `upload trace → see report` flow and a `/optimize` page that renders the Pareto SVG.

## Honest limitations (v1.0)

- **Heuristic ablation, not real eval.** Quality values are token-weighted cosine-similarity estimates between chunks and the query. Real LLM-judge eval-mode (per-chunk WITH/WITHOUT answer-quality deltas) ships in v1.1. Every output is labeled with this caveat.
- **Hash embedder by default.** When `sentence-transformers` isn't installed, the chunk usefulness scorer uses a 64-dim char-trigram feature-hashing embedder — fine for sanity checks, dumb for semantic relevance. Install with `pip install token-lens[embeddings]` for real sentence-transformer scoring.
- **Single-machine, local-only.** token-lens does not phone home. There is no hosted version. Your traces stay on disk.

## CLI reference

| command | description |
|---------|-------------|
| `token-lens init` | scaffold `token-lens.yaml` + GitHub Actions workflow |
| `token-lens demo` | show the Pareto chart with synthetic data |
| `token-lens analyze TRACE` | analyze a trace JSON, emit HTML/SVG/JSON/MD |
| `token-lens ablation TRACE` | per-chunk RAG ablation scoring table |
| `token-lens check --config FILE TRACE…` | budget CI; exits non-zero on breach |
| `token-lens ingest --jsonl LOG --source PROVIDER` | tail a JSONL log into the store |
| `token-lens stats --last N` | aggregate stats from the store |
| `token-lens optimize --db PATH` | Pareto frontier + recommendations from the store |
| `token-lens compare BEFORE.json AFTER.json` | diff two traces, show savings |
| `token-lens serve` | local web UI at `http://127.0.0.1:8793` |

## Python API

```python
from token_lens import analyze_file, score_chunk_usefulness
from token_lens.optimize import compute_pareto, recommend_across_traces

report = analyze_file("trace.json")           # AnalysisReport
abl = report.ablation                          # AblationResult with per-chunk scores
print(abl.chunks[0].verdict, abl.chunks[0].usefulness)

# From a populated store:
recs = recommend_across_traces(store, min_coverage=0.9, min_usefulness=0.2)
curve = compute_pareto(store)
for r in recs[:5]:
    print(f"remove {r.targets}  saves {r.token_reduction} tok  conf={r.confidence}")
```

## Roadmap

This is **v1.0 — the core thesis.** Live in [`ROADMAP.md`](ROADMAP.md).

Deferred to **v1.1** (see ROADMAP.md for the full list):
- Real LLM-judge eval-mode (the WITH/WITHOUT quality deltas)
- Langfuse pull ingestion
- OpenTelemetry / OTLP receiver
- Full multi-page web UI (`/budget`, `/live`, full `/optimize`)
