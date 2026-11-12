# Changelog

## Unreleased

- Fixed the packaged wheel: `token_lens.ingest` was missing and `templates/` +
  the demo traces weren't package data, so `token-lens init` and
  `token-lens demo` crashed with FileNotFoundError on any installed copy.
  Demo fixtures now ship inside the package (`token_lens/data/`).
- README truth: install from git (the package is not on PyPI), the
  `[embeddings]` extra now exists (plus a lightweight `[tokenizers]` extra),
  `score_chunk_usefulness` is importable from `token_lens` as documented,
  `__version__` matches pyproject (1.0.0), web UI port corrected to 8765,
  pyproject URLs point at the real repo.
- Pricing table replaced with a small set of current models (verified
  2026-11-12 against OpenAI/Anthropic price sheets and the OpenRouter
  catalog); matching is exact or snapshot-suffix only, so a model merely
  containing a table key no longer inherits its price. Unknown models stay
  unpriced instead of being costed at a guessed default rate — `token-lens
  ingest` now stores NULL cost for them and `stats` reports priced coverage.
  Bundled sample traces now name a current model so the quickstart shows a
  real cost line.
- Tests: tokenizer-backend tests skip when the optional `tokenizers` package
  is absent (bare `pip install -e ".[test]" && pytest` is green again);
  new pricing and packaging-resource regression tests; CI workflow with a
  wheel smoke job (build → clean install → `init`/`demo`/import checks).

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
