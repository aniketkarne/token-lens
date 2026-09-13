# Changelog

## 1.0.0 — context optimizer (2026-09-13)

First major release. token-lens ships as a **context optimizer**: find the minimum context needed to preserve answer quality.

- Real tokenizers (tiktoken, HuggingFace `tokenizers`, custom `.json` files) with honest "approximate" badges
- Per-chunk RAG ablation with redundant-chunk detection (heuristic embedding + cosine sim)
- Cross-trace Pareto frontier + confidence-rated recommendations
- Token budget CI (`token-lens check --config token-lens.yaml` exits non-zero on breach)
- Live JSONL trace ingest (`token-lens ingest --jsonl logs/req.jsonl`) + SQLite store + `stats`
- Local web UI (`token-lens serve`) with budget + optimize endpoints
- `token-lens init` scaffolds config + CI workflow into your project
- `token-lens demo` shows the Pareto chart with synthetic data — no setup needed

Deferred to v1.1: real LLM-judge eval, Langfuse pull, OTLP receiver, multi-page web UI.

## 0.3.0 — earlier (pre-v1.0)

Heuristic token zone classification, boilerplate detection, recommendations, HTML/SVG report rendering, local web server, before/after comparison.
