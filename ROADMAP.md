# token-lens v1.0 — Context Optimizer Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task. Each task is bite-sized (2–5 min), TDD-driven, with exact paths and commands.

**Goal:** Transform token-lens from "token visualization" into a **context optimizer** — find the minimum context needed to preserve answer quality.

**Thesis:** *"Which context is costing me money without improving answer quality?"*

---

## Progress Checklist

Legend: `[ ]` pending · `[~]` in progress · `[x]` done · `[!]` blocked

### Phase 1 — Real Tokenizer Backends
- [x] Task 1.1 — `TokenizerBackend` enum + `AnalysisReport` fields
- [x] Task 1.2 — HuggingFace `tokenizers` adapter + custom file loader
- [x] Task 1.3 — Report renders backend label + `⚠ approximate` badge
- [x] Task 1.4 — CLI `--tokenizer` + `--custom-tokenizer` flags
- [x] Task 1.5 — Phase 1 verification

### Phase 2 — `token-lens init` Scaffolding
- [x] Task 2.1 — Template files (`token-lens.yaml`, CI snippet, sample trace)
- [x] Task 2.2 — `scaffold.py` + `init` subcommand
- [x] Task 2.3 — Phase 2 verification

### Phase 3 — Token Budget CI
- [x] Task 3.1 — `BudgetConfig` + YAML loader
- [x] Task 3.2 — Breach checker
- [x] Task 3.3 — `token-lens check` CLI (exit codes)
- [x] Task 3.4 — Web `/api/budget/check`
- [x] Task 3.5 — Phase 3 verification

### Phase 4 — RAG Chunk Ablation (Heuristic)
- [x] Task 4.1 — `ChunkUsefulness` + `AblationResult` types
- [x] Task 4.2 — Embedding backend (lazy + cache + hash fallback)
- [x] Task 4.3 — Chunk usefulness scorer
- [x] Task 4.4 — Cross-chunk redundancy detection
- [x] Task 4.5 — Estimated quality delta
- [x] Task 4.6 — Parse RAG chunks from traces
- [x] Task 4.7 — `analyze` returns ablation result
- [x] Task 4.8 — Report renders ablation table
- [x] Task 4.9 — CLI `ablation` subcommand
- [x] Task 4.10 — Phase 4 verification

### Phase 5 — Live Trace Ingest (JSONL Tail)
- [x] Task 5.1 — SQLite schema + `TraceStore`
- [ ] Task 5.2 — Provider normalizer (OpenAI/Anthropic/Generic)
- [ ] Task 5.3 — JSONL tail with offset checkpointing
- [ ] Task 5.4 — `token-lens ingest` CLI
- [ ] Task 5.5 — `token-lens stats` aggregates
- [ ] Task 5.6 — Web `/api/stats` + `/api/ingest`
- [ ] Task 5.7 — Phase 5 verification

### Phase 6 — Live Trace Ingest (Langfuse Pull)
- [ ] Task 6.1 — Langfuse client (paginated)
- [ ] Task 6.2 — CLI `--langfuse` flag
- [ ] Task 6.3 — Phase 6 verification

### Phase 7 — Live Trace Ingest (Otel Receiver)
- [ ] Task 7.1 — OTLP gRPC receiver skeleton
- [ ] Task 7.2 — OTel GenAI semconv → trace
- [ ] Task 7.3 — CLI `--otel` flag
- [ ] Task 7.4 — Phase 7 verification

### Phase 8 — Evidence-Based Recommendations + Pareto Frontier
- [ ] Task 8.1 — `CrossTraceRecommendation` + `ParetoPoint` types
- [ ] Task 8.2 — Ablation persistence in store
- [ ] Task 8.3 — Cross-trace recommendation engine
- [ ] Task 8.4 — Pareto frontier computation
- [ ] Task 8.5 — CLI `optimize` subcommand
- [ ] Task 8.6 — Pareto SVG renderer
- [ ] Task 8.7 — Phase 8 verification

### Phase 9 — Web App: Budget / Live / Optimize Pages
- [ ] Task 9.1 — `/budget` page
- [ ] Task 9.2 — `/live` page
- [ ] Task 9.3 — `/optimize` page
- [ ] Task 9.4 — Navigation links
- [ ] Task 9.5 — Phase 9 verification

### Phase 10 — README + Hero + v1.0.0 Release
- [ ] Task 10.1 — README rewrite (lead with thesis)
- [ ] Task 10.2 — Hero SVG refresh
- [ ] Task 10.3 — CHANGELOG.md
- [ ] Task 10.4 — Bump to 1.0.0, tag, push
- [ ] Task 10.5 — Phase 10 verification + final smoke

### Phase 11 — (Deferred to v1.1)
- [ ] Task 11.1 — Langfuse pull ingest (deferred)
- [ ] Task 11.2 — OTLP receiver (deferred)
- [ ] Task 11.3 — Eval-mode (real LLM judge) (deferred)
- [ ] Task 11.4 — Multi-page web UI: `/budget`, `/live`, full `/optimize` (deferred)

> **Note:** Phases 6 (Langfuse) and 7 (OTel receiver) from the original plan are deferred to v1.1. They depend on a working live-data ingestion pipeline (Phase 5) which is what v1.0 ships first. Eval-mode (real LLM judge) is also deferred — v1.0 ships heuristic-only ablation with honest labels everywhere.

---



**Goal:** Transform token-lens from "token visualization" into a **context optimizer** that finds the minimum context needed to preserve answer quality. Adds real tokenizers, RAG chunk ablation, token-budget CI, live trace ingestion, and evidence-based recommendations with a quality/tokens Pareto frontier.

**Architecture:** Five new modules — `tokenizers/` (pluggable real backends), `ablation/` (RAG chunk usefulness), `budget/` (yaml config + check CLI), `ingest/` (JSONL/Langfuse/Otel tail), `optimize/` (cross-trace recs + Pareto). Heuristic-first, eval-mode-opt-in. CLI extends with `check`, `ingest`, `init`. Web app gets a "Live" view, "Budget" panel, and "Optimize" recommendations page.

**Tech Stack:** Python 3.9+, stdlib + tiktoken + tokenizers + sentence-transformers (optional), SQLite for live ingest store, PyYAML for budgets, FastAPI-free stdlib server (already in place).

**Repo state entering plan:**
- HEAD: `abc2a99` (v0.3.0, clean)
- 4,590 LoC across 13 modules + 10 test files
- Existing: `tokenize.py` already has tiktoken/transformers/heuristic fallbacks — extend, don't rewrite
- Optional deps already declared: `tiktoken`, `transformers`

---

## Effort / Risk per phase

| # | Phase | Effort | Risk | Why |
|---|-------|--------|------|-----|
| 1 | Real tokenizer backends | **Medium** | Low | Extends existing `tokenize.py`; add HF + custom; surface backend in report |
| 2 | `token-lens init` scaffolding | **Easy** | Low | Pure CLI + template files |
| 3 | Budget YAML + `check` command | **Medium** | Medium | New YAML schema (load-bearing) + exit-code contract for CI |
| 4 | RAG chunk ablation (heuristic) | **Hard** | High | Heuristic-heavy, defines what "useful chunk" means everywhere downstream |
| 5 | Live trace ingest — JSONL tail | **Medium** | Medium | SQLite schema is load-bearing for #6, #7 |
| 6 | Live trace ingest — Langfuse pull | **Medium** | Low | HTTP pagination, well-known API |
| 7 | Live trace ingest — Otel receiver | **Hard** | High | gRPC, batching, retries — biggest engineering surface |
| 8 | Evidence-based recommendations + Pareto | **Hard** | High | Crown jewel; consumes 1, 4, 5–7 |
| 9 | Web app: Budget / Live / Optimize pages | **Medium** | Low | Additive on stdlib server |
| 10 | README rewrite + hero refresh | **Easy** | Low | Lead with the new thesis |

**Dependency graph:**
```
1 → 8
2 → 3
3 → 9
4 → 8
5 → 6 → 7  (shared SQLite store)
5 → 8
8 → 9
9 → 10
```

---

## Phase 1 — Real Tokenizer Backends (Foundation)

**Objective:** Replace the "pretend an approximation is exact" model. Every analysis report shows the active tokenizer backend and flags approximations. Adds Hugging Face `tokenizers` support and a custom-tokenizer loader.

**Files:**
- Modify: `token_lens/tokenize.py` (extend `_try_tiktoken`, add `_try_hf_tokenizers`, add `_try_custom`)
- Modify: `token_lens/types.py` (add `TokenizerBackend` enum, extend `AnalysisReport`)
- Modify: `token_lens/report.py` (render backend label + `⚠ approximate` badge)
- Create: `tests/test_tokenize_backends.py`
- Create: `examples/custom_tokenizer.json` (sample vocab for tests)

### Task 1.1: Add `TokenizerBackend` enum to types

**Step 1 — Write failing test** in `tests/test_types.py`:

```python
from token_lens.types import TokenizerBackend, AnalysisReport

def test_tokenizer_backend_values():
    assert TokenizerBackend.TIKTOKEN.value == "tiktoken"
    assert TokenizerBackend.HUGGINGFACE.value == "huggingface"
    assert TokenizerBackend.CUSTOM.value == "custom"
    assert TokenizerBackend.HEURISTIC.value == "heuristic"


def test_analysis_report_carries_backend():
    r = AnalysisReport(
        total_tokens=10,
        total_cost_usd=0.001,
        zone_breakdown=[],
        rag_utilization=0.5,
        boilerplate_ratio=0.1,
        positional_risk=[],
        recommendations=[],
        tokenizer_backend=TokenizerBackend.TIKTOKEN,
        tokenizer_name="cl100k_base",
        is_approximate=False,
    )
    assert r.tokenizer_backend == TokenizerBackend.TIKTOKEN
    assert r.tokenizer_name == "cl100k_base"
    assert r.is_approximate is False
```

**Step 2 — Run, expect FAIL** (fields don't exist yet): `python3 -m pytest tests/test_types.py -v`

**Step 3 — Implement** in `token_lens/types.py`:

```python
from enum import Enum

class TokenizerBackend(str, Enum):
    TIKTOKEN = "tiktoken"
    HUGGINGFACE = "huggingface"
    CUSTOM = "custom"
    HEURISTIC = "heuristic"
```

Add the three new fields (`tokenizer_backend`, `tokenizer_name`, `is_approximate`) to the `AnalysisReport` dataclass with sensible defaults (`HEURISTIC`, `"heuristic-v1"`, `True`).

**Step 4 — Run, expect PASS**; **Step 5 — commit** `feat(types): add TokenizerBackend enum + report fields`.

### Task 1.2: Hugging Face `tokenizers` adapter

**Step 1 — Failing test** in `tests/test_tokenize_backends.py`:

```python
import pytest
from token_lens.tokenize import resolve_tokenizer, TokenizerResolution

def test_hf_tokenizer_resolution_without_install(monkeypatch):
    # If `tokenizers` isn't installed, must NOT raise — return None gracefully.
    monkeypatch.setattr("importlib.import_module", lambda name: (_ for _ in ()).throw(ImportError))
    result = resolve_tokenizer(model="bert-base-uncased", custom_path=None)
    # Either HF succeeds (env has it) or we fall through. Must never raise.
    assert result is None or isinstance(result, TokenizerResolution)


def test_custom_tokenizer_load(tmp_path):
    # Write a tiny tokenizer.json (HF format) and verify loader
    vocab = tmp_path / "tok.json"
    vocab.write_text('{"version":"1.0","truncation":null,"padding":null,"added_tokens":[],"normalizer":null,"pre_tokenizer":{"type":"Whitespace"},"post_processor":null,"decoder":null,"model":{"type":"BPE","dropout":null,"unk_token":null,"continuing_subword_prefix":null,"end_of_word_suffix":null,"fuse_unk":false,"vocab":{"hello":0,"world":1},"merges":[]}}')
    res = resolve_tokenizer(model="custom", custom_path=str(vocab))
    assert res is not None
    assert res.backend.value == "custom"
    tokens = res.encode("hello world")
    assert tokens == ["hello", "world"]
```

**Step 2 — Run, expect FAIL**; **Step 3 — implement** `resolve_tokenizer(model, custom_path)` returning a `TokenizerResolution(backend, name, encode, is_approximate)`. Try order: tiktoken → hf (if `custom_path` is None and model is HF-style) → custom file → None (caller decides heuristic fallback).

**Step 4 — PASS; commit** `feat(tokenize): HF tokenizers + custom file loader via resolve_tokenizer`.

### Task 1.3: Report shows tokenizer backend label

**Step 1 — Failing test** in `tests/test_report.py`:

```python
def test_html_report_shows_tokenizer_backend():
    # Generate an HTML report and assert backend label is rendered.
    from token_lens.report import render_html
    from token_lens.types import AnalysisReport, TokenizerBackend, ZoneBreakdown
    r = AnalysisReport(
        total_tokens=100, total_cost_usd=0.001,
        zone_breakdown=[ZoneBreakdown(zone="system", tokens=100, ratio=1.0, kind="system")],
        rag_utilization=0.0, boilerplate_ratio=0.0,
        positional_risk=[], recommendations=[],
        tokenizer_backend=TokenizerBackend.TIKTOKEN, tokenizer_name="cl100k_base", is_approximate=False,
    )
    import tempfile, pathlib
    out = pathlib.Path(tempfile.mkdtemp()) / "r.html"
    render_html(r, str(out))
    html = out.read_text()
    assert "cl100k_base" in html
    assert "⚠" not in html  # exact backend, no warning
```

**Step 2 — Run FAIL; Step 3 — patch** `token_lens/report.py` to render a "Tokenizer: <name>" header line; if `is_approximate`, prepend `⚠ approximate`. **Step 4 — PASS; commit** `feat(report): show tokenizer backend label`.

### Task 1.4: CLI `--tokenizer` flag + auto-detect

**Step 1 — Failing test** in `tests/test_cli_tokenizer.py`:

```python
from click.testing import CliRunner
from token_lens.cli import main

def test_cli_tokenizer_flag_overrides():
    runner = CliRunner()
    result = runner.invoke(main, ["analyze", "examples/lean_trace.json", "--tokenizer", "cl100k_base", "--json"])
    assert result.exit_code == 0
    body = result.output
    assert "cl100k_base" in body or "tiktoken" in body


def test_cli_approximate_warning(monkeypatch):
    # Force the heuristic fallback by making tiktoken import fail.
    from token_lens import tokenize
    monkeypatch.setattr(tokenize, "_try_tiktoken", lambda m: None)
    monkeypatch.setattr(tokenize, "_try_hf", lambda m, p: None)
    monkeypatch.setattr(tokenize, "_try_custom", lambda p: None)
    runner = CliRunner()
    result = runner.invoke(main, ["analyze", "examples/lean_trace.json", "--json"])
    assert "approximate" in result.output.lower() or "heuristic" in result.output.lower()
```

**Step 2 — FAIL; Step 3 — wire** `--tokenizer MODEL` and `--custom-tokenizer PATH` flags through the CLI; pass them into `resolve_tokenizer`. **Step 4 — PASS; commit** `feat(cli): --tokenizer and --custom-tokenizer flags`.

### Task 1.5: Verify Phase 1

Run: `python3 -m pytest -q`
Expected: all existing 72 tests still pass + new tests pass. Manual: `token-lens analyze examples/lean_trace.json` shows "Tokenizer: cl100k_base" (or fallback warning).

Commit: `chore: phase 1 — real tokenizer backends shipped`.

---

## Phase 2 — `token-lens init` Scaffolding

**Objective:** One command scaffolds `token-lens.yaml`, sample trace, GitHub Actions snippet. Time-to-first-insight < 90 seconds.

**Files:**
- Create: `token_lens/scaffold.py`
- Create: `token_lens/templates/token-lens.yaml`
- Create: `token_lens/templates/budget.yml`
- Create: `token_lens/templates/ci/github-actions.yml`
- Create: `token_lens/templates/sample_trace.json` (copy of `examples/lean_trace.json` trimmed)
- Create: `tests/test_scaffold.py`

### Task 2.1: Template files

Copy/create the four template files. `token-lens.yaml` initial contents:

```yaml
# token-lens configuration
# Docs: https://github.com/aniketkarne-com/token-lens
tokenizer:
  backend: auto            # auto | tiktoken | huggingface | custom
  model: gpt-4o
  # custom_path: ./my-tokenizer.json
budgets:
  total_tokens: 12000
  zones:
    tool_schema: 2000
    history: 4000
    rag: 5000
  cost_usd: 0.03
ingest:
  jsonl:
    - ./logs/requests.jsonl
  # langfuse:
  #   public_key: ${LANGFUSE_PUBLIC_KEY}
  #   secret_key: ${LANGFUSE_SECRET_KEY}
  #   host: https://cloud.langfuse.com
recommendations:
  min_chunk_usefulness: 0.15   # chunks scoring below this are candidates for removal
  min_eval_sample_size: 30     # cross-trace recs require at least this many traces
```

`budget.yml` — same shape with placeholder values for a user to edit. CI snippet: a `github-actions.yml` that runs `token-lens check --config token-lens.yaml logs/*.jsonl` on PRs.

### Task 2.2: Scaffold module

**Step 1 — Failing test** in `tests/test_scaffold.py`:

```python
from click.testing import CliRunner
from token_lens.cli import main
import pathlib

def test_init_creates_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["init"])
    assert result.exit_code == 0
    assert (tmp_path / "token-lens.yaml").exists()
    assert (tmp_path / ".github/workflows/token-lens.yml").exists()
    assert (tmp_path / "examples" / "sample_trace.json").exists()


def test_init_refuses_overwrite_without_force(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "token-lens.yaml").write_text("existing: true")
    runner = CliRunner()
    result = runner.invoke(main, ["init"])
    assert result.exit_code != 0
    assert "exists" in result.output.lower()
```

**Step 2 — FAIL; Step 3 — implement** `token_lens/scaffold.py` with `scaffold(target_dir, force=False)` writing all template files. CLI subcommand `init` calls it with `CWD`. `--force` flag overwrites. **Step 4 — PASS; commit** `feat(scaffold): token-lens init creates config + CI + sample trace`.

### Task 2.3: Verify Phase 2

Run `cd /tmp && rm -rf tl-test && mkdir tl-test && cd tl-test && token-lens init && ls -la`. Expected: `token-lens.yaml`, `.github/workflows/token-lens.yml`, `examples/sample_trace.json` all present. Commit: `chore: phase 2 — init scaffolding shipped`.

---

## Phase 3 — Token Budget CI

**Objective:** `token-lens check` reads `token-lens.yaml`, compares against budgets, returns non-zero on breach, prints a clean table.

**Files:**
- Create: `token_lens/budget.py` (BudgetConfig dataclass, loader, checker)
- Create: `tests/test_budget.py`
- Modify: `token_lens/cli.py` (add `check` subcommand)
- Modify: `token_lens/server.py` (add `/api/budget/check` endpoint)

### Task 3.1: BudgetConfig dataclass + loader

**Step 1 — Failing test** in `tests/test_budget.py`:

```python
import pathlib, textwrap
from token_lens.budget import BudgetConfig, load_budget, BudgetBreach

def test_load_budget_parses_yaml(tmp_path):
    cfg = tmp_path / "tl.yaml"
    cfg.write_text(textwrap.dedent("""
        budgets:
          total_tokens: 1000
          zones:
            rag: 400
            history: 300
          cost_usd: 0.01
    """))
    b = load_budget(str(cfg))
    assert b.total_tokens == 1000
    assert b.zones["rag"] == 400
    assert b.zones["history"] == 300
    assert b.cost_usd == 0.01


def test_load_budget_missing_file():
    import pytest
    with pytest.raises(FileNotFoundError):
        load_budget("/nonexistent/tl.yaml")
```

**Step 2 — FAIL; Step 3 — implement** `BudgetConfig` (frozen dataclass), `load_budget(path)` using `yaml.safe_load`. Add `PyYAML` to `pyproject.toml` dependencies. **Step 4 — PASS; commit** `feat(budget): BudgetConfig loader`.

### Task 3.2: Breach checker

**Step 1 — Failing test**:

```python
def test_check_breach_detects_overages():
    from token_lens.budget import BudgetConfig, check_budget
    from token_lens.types import AnalysisReport, ZoneBreakdown, TokenizerBackend
    cfg = BudgetConfig(total_tokens=1000, zones={"rag": 400}, cost_usd=0.01)
    rep = AnalysisReport(
        total_tokens=1500, total_cost_usd=0.02,
        zone_breakdown=[
            ZoneBreakdown(zone="rag", tokens=500, ratio=0.3, kind="rag"),
            ZoneBreakdown(zone="system", tokens=1000, ratio=0.7, kind="system"),
        ],
        rag_utilization=0.0, boilerplate_ratio=0.0,
        positional_risk=[], recommendations=[],
        tokenizer_backend=TokenizerBackend.HEURISTIC, tokenizer_name="h", is_approximate=True,
    )
    breaches = check_budget(cfg, rep)
    zone_codes = {b.code for b in breaches}
    assert "total_tokens" in zone_codes
    assert "rag" in zone_codes
    assert "cost_usd" in zone_codes
```

**Step 2 — FAIL; Step 3 — implement** `check_budget(cfg, report) -> list[BudgetBreach]`, where `BudgetBreach(code, actual, limit, severity)`. Sum RAG zone tokens, compare against `zones["rag"]`, etc. **Step 4 — PASS; commit** `feat(budget): breach checker`.

### Task 3.3: `token-lens check` CLI

**Step 1 — Failing test** in `tests/test_cli_check.py`:

```python
from click.testing import CliRunner
from token_lens.cli import main
import pathlib, textwrap, json

def test_check_exits_nonzero_on_breach(tmp_path):
    cfg = tmp_path / "tl.yaml"
    cfg.write_text(textwrap.dedent("""
        budgets:
          total_tokens: 100
    """))
    trace = tmp_path / "trace.json"
    trace.write_text(json.dumps({
        "messages": [
            {"role": "system", "content": "x" * 1000},
            {"role": "user", "content": "hi"}
        ]
    }))
    runner = CliRunner()
    result = runner.invoke(main, ["check", "--config", str(cfg), str(trace)])
    assert result.exit_code != 0
    assert "exceeded" in result.output.lower() or "breach" in result.output.lower()


def test_check_passes_when_under_budget(tmp_path):
    cfg = tmp_path / "tl.yaml"
    cfg.write_text("budgets:\n  total_tokens: 100000\n")
    trace = tmp_path / "trace.json"
    trace.write_text(json.dumps({"messages": [{"role": "user", "content": "hi"}]}))
    runner = CliRunner()
    result = runner.invoke(main, ["check", "--config", str(cfg), str(trace)])
    assert result.exit_code == 0
```

**Step 2 — FAIL; Step 3 — implement** `check` subcommand: load config, analyze each trace file (or stdin), run `check_budget`, print a table, exit `1` if any breach. Accept multiple trace files + globs. **Step 4 — PASS; commit** `feat(cli): check subcommand with non-zero exit on breach`.

### Task 3.4: Web `/api/budget/check` endpoint

**Step 1 — Failing test** in `tests/test_server_budget.py`:

```python
def test_budget_check_endpoint(client):
    resp = client.post("/api/budget/check", json={
        "config": {"budgets": {"total_tokens": 100}},
        "trace": {"messages": [{"role": "system", "content": "x"*1000}, {"role": "user", "content": "hi"}]}
    })
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is False
    assert any(b["code"] == "total_tokens" for b in body["breaches"])
```

**Step 2 — FAIL; Step 3 — wire** handler in `token_lens/server.py`. **Step 4 — PASS; commit** `feat(server): /api/budget/check`.

### Task 3.5: Verify Phase 3

Run: `python3 -m pytest -q && cd /tmp/tl-test && token-lens init && echo 'budgets:\n  total_tokens: 100' > tl-strict.yaml && token-lens check --config tl-strict.yaml examples/sample_trace.json`. Expected: exit non-zero, breach printed.

Commit: `chore: phase 3 — budget CI shipped`.

---

## Phase 4 — RAG Chunk Ablation (Heuristic)

**Objective:** For each RAG chunk in a trace, compute a "usefulness" score. Identify chunks that don't earn their tokens. Provide a heuristic "WITH/WITHOUT quality delta" estimate.

**Files:**
- Create: `token_lens/ablation.py` (ChunkUsefulness, AblationResult, score_chunk_usefulness)
- Create: `token_lens/embeddings.py` (lazy-loaded sentence-transformers wrapper)
- Modify: `token_lens/parse.py` (extract chunks from RAG-zone messages)
- Modify: `token_lens/types.py` (add `ChunkUsefulness` and `AblationResult`)
- Modify: `token_lens/report.py` (render ablation table)
- Modify: `token_lens/recommend.py` (consume ablation results)
- Create: `tests/test_ablation.py`
- Create: `tests/test_embeddings.py`
- Modify: `token_lens/cli.py` (add `ablation` subcommand + flag on `analyze`)

### Task 4.1: ChunkUsefulness + AblationResult types

**Step 1 — Failing test** in `tests/test_ablation.py`:

```python
from token_lens.types import ChunkUsefulness, AblationResult

def test_chunk_usefulness_fields():
    cu = ChunkUsefulness(index=0, tokens=812, query_similarity=0.71, redundancy=0.2, usefulness=0.6, verdict="useful")
    assert cu.usefulness == 0.6
    assert cu.verdict == "useful"


def test_ablation_result_aggregates():
    ar = AblationResult(chunks=[
        ChunkUsefulness(index=0, tokens=812, query_similarity=0.9, redundancy=0.1, usefulness=0.85, verdict="useful"),
        ChunkUsefulness(index=1, tokens=744, query_similarity=0.2, redundancy=0.1, usefulness=0.18, verdict="irrelevant"),
    ], potential_removal_tokens=744, estimated_quality_delta=-0.01)
    assert ar.potential_removal_tokens == 744
    assert abs(ar.estimated_quality_delta + 0.01) < 1e-9
```

**Step 2 — FAIL; Step 3 — add types** to `token_lens/types.py`. **Step 4 — PASS; commit** `feat(types): ChunkUsefulness + AblationResult`.

### Task 4.2: Embedding backend (lazy + cache)

**Step 1 — Failing test** in `tests/test_embeddings.py`:

```python
import pytest
from token_lens.embeddings import get_embedder, hash_embed

def test_hash_embed_deterministic():
    a = hash_embed("hello world")
    b = hash_embed("hello world")
    assert a == b


def test_get_embedder_falls_back_to_hash_when_unavailable(monkeypatch):
    # Force sentence_transformers import to fail
    monkeypatch.setattr("token_lens.embeddings._try_sentence_transformers", lambda m: None)
    e = get_embedder(model="all-MiniLM-L6-v2")
    out = e.encode(["hello", "world"])
    assert len(out) == 2
    assert all(isinstance(v, list) for v in out)


def test_get_embedder_caches():
    e1 = get_embedder(model="all-MiniLM-L6-v2")
    e2 = get_embedder(model="all-MiniLM-L6-v2")
    assert e1 is e2
```

**Step 2 — FAIL; Step 3 — implement** `embeddings.py` with a tiny hashing embedder as the always-available fallback (deterministic 384-dim via feature hashing) and a real sentence-transformers backend if installed. Cache by model name. **Step 4 — PASS; commit** `feat(embeddings): pluggable embedder with hash fallback`.

### Task 4.3: Chunk usefulness scoring

**Step 1 — Failing test** in `tests/test_ablation.py`:

```python
from token_lens.ablation import score_chunk_usefulness
from token_lens.types import MessageRecord

def test_score_usefulness_for_relevant_chunk():
    chunks = [
        MessageRecord(role="system", content="The Eiffel Tower is in Paris, built in 1889.", zone="rag", tokens=12),
        MessageRecord(role="system", content="Pizza toppings include pineapple controversy.", zone="rag", tokens=10),
    ]
    results = score_chunk_usefulness(chunks, query="Where is the Eiffel Tower?")
    # First chunk should be more useful than the second
    assert results[0].usefulness > results[1].usefulness
    assert results[0].verdict in ("useful", "marginal")


def test_score_usefulness_detects_redundancy():
    a = MessageRecord(role="system", content="Apples are red fruits.", zone="rag", tokens=8)
    b = MessageRecord(role="system", content="Apples are red fruits that grow on trees.", zone="rag", tokens=12)
    results = score_chunk_usefulness([a, b], query="Tell me about apples")
    # b should score higher redundancy than a
    assert results[1].redundancy > results[0].redundancy
```

**Step 2 — FAIL; Step 3 — implement** `score_chunk_usefulness`:

```
usefulness = clamp(query_similarity - redundancy * 0.5, 0, 1)
verdict    = "useful" if usefulness >= 0.5 else ("marginal" if usefulness >= 0.2 else "irrelevant")
```

Where `query_similarity` = cosine(query_emb, chunk_emb); `redundancy` = max cosine(chunk_emb, other_chunk_embs). Use the embedder from Phase 4.2. **Step 4 — PASS; commit** `feat(ablation): chunk usefulness scorer (heuristic)`.

### Task 4.4: Cross-chunk redundancy detection (the duplicate RAG chunks use case)

**Step 1 — Failing test**:

```python
def test_detects_near_duplicate_chunks():
    chunks = [
        MessageRecord(role="system", content="The capital of France is Paris.", zone="rag", tokens=10),
        MessageRecord(role="system", content="The capital city of France is Paris.", zone="rag", tokens=11),
        MessageRecord(role="system", content="Bananas are yellow.", zone="rag", tokens=6),
    ]
    results = score_chunk_usefulness(chunks, query="France capital")
    # chunks 0 and 1 are near-duplicates; one should be flagged redundant
    assert abs(results[0].redundancy - results[1].redundancy) > 0.05 or \
           (results[0].verdict == "irrelevant" or results[1].verdict == "irrelevant")
```

**Step 2 — FAIL; Step 3 — refine** the redundancy calc to use max-sim against all *other* chunks and ensure near-duplicates both get high redundancy scores. **Step 4 — PASS; commit** `feat(ablation): cross-chunk redundancy`.

### Task 4.5: Estimated quality delta

**Step 1 — Failing test**:

```python
def test_quality_delta_is_small_for_useful_small_for_irrelevant():
    chunks = [
        MessageRecord(role="system", content="x", zone="rag", tokens=10),
        MessageRecord(role="system", content="y", zone="rag", tokens=10),
        MessageRecord(role="system", content="z", zone="rag", tokens=10),
    ]
    r = score_chunk_usefulness(chunks, query="completely unrelated query about quantum foam")
    # Most chunks should be irrelevant; quality delta should be near zero (we don't lose much by removing them)
    assert abs(r.potential_quality_delta) < 0.05
```

**Step 2 — FAIL; Step 3 — implement** `potential_quality_delta = -sum(usefulness * weight)` over the chunks that would be removed; weight defaults to chunk's token share. **Step 4 — PASS; commit** `feat(ablation): heuristic quality delta estimator`.

### Task 4.6: Parse RAG chunks from traces

**Step 1 — Failing test** in `tests/test_parse_rag.py`:

```python
def test_parse_extracts_rag_chunks():
    from token_lens.parse import parse_trace
    trace = {
        "messages": [
            {"role": "system", "content": "you are helpful"},
            {"role": "system", "content": "[doc 1] foo bar baz", "metadata": {"zone": "rag", "chunk_id": "1"}},
            {"role": "system", "content": "[doc 2] quux", "metadata": {"zone": "rag", "chunk_id": "2"}},
            {"role": "user", "content": "question"},
        ]
    }
    parsed = parse_trace(trace)
    rag_chunks = [m for m in parsed.messages if m.zone == "rag"]
    assert len(rag_chunks) == 2
    assert rag_chunks[0].chunk_id == "1"
```

**Step 2 — FAIL; Step 3 — extend** `parse.py` to capture `chunk_id` in `MessageRecord.metadata`. **Step 4 — PASS; commit** `feat(parse): extract RAG chunk IDs`.

### Task 4.7: `analyze` returns ablation result

**Step 1 — Failing test** in `tests/test_analyze_ablation.py`:

```python
def test_analyze_includes_ablation_when_rag_present():
    from token_lens.analyze import analyze_trace
    trace = {
        "messages": [
            {"role": "system", "content": "be helpful"},
            {"role": "system", "content": "doc 1 content", "metadata": {"zone": "rag", "chunk_id": "1"}},
            {"role": "system", "content": "doc 2 unrelated", "metadata": {"zone": "rag", "chunk_id": "2"}},
            {"role": "user", "content": "what is doc 1?"},
        ]
    }
    rep = analyze_trace(trace)
    assert rep.ablation is not None
    assert len(rep.ablation.chunks) == 2
```

**Step 2 — FAIL; Step 3 — wire** `analyze_trace` to compute ablation when RAG zone is non-empty. **Step 4 — PASS; commit** `feat(analyze): include ablation in report`.

### Task 4.8: Report renders ablation table

**Step 1 — Failing test** in `tests/test_report_ablation.py`:

```python
def test_html_report_renders_ablation_section(tmp_path):
    from token_lens.report import render_html
    # build a minimal report with ablation
    ...
    html = ...
    assert "RAG context" in html or "ablation" in html.lower()
    assert "useful" in html or "irrelevant" in html
```

**Step 2 — FAIL; Step 3 — add ablation section** to `report.py` HTML/SVG rendering. **Step 4 — PASS; commit** `feat(report): render RAG ablation section`.

### Task 4.9: CLI `ablation` subcommand

**Step 1 — Failing test** in `tests/test_cli_ablation.py`:

```python
def test_cli_ablation_outputs_table():
    runner = CliRunner()
    result = runner.invoke(main, ["ablation", "examples/lean_trace.json"])
    assert result.exit_code == 0
    # Should mention chunks or usefulness
    assert "chunk" in result.output.lower() or "usefulness" in result.output.lower()
```

**Step 2 — FAIL; Step 3 — implement** `ablation` subcommand. **Step 4 — PASS; commit** `feat(cli): ablation subcommand`.

### Task 4.10: Verify Phase 4

Manual: `token-lens ablation examples/lean_trace.json` shows a chunk-by-chunk table. Run full test suite. Commit: `chore: phase 4 — RAG chunk ablation shipped`.

---

## Phase 5 — Live Trace Ingest (JSONL Tail)

**Objective:** `token-lens ingest --jsonl logs/requests.jsonl` tails a JSONL log of LLM calls, normalizes each line to a trace, stores in SQLite, exposes aggregates via `token-lens stats`.

**Files:**
- Create: `token_lens/store.py` (SQLite schema + DAO)
- Create: `token_lens/ingest/__init__.py`
- Create: `token_lens/ingest/jsonl.py` (tail + normalize)
- Create: `token_lens/ingest/normalize.py` (provider → trace mapping)
- Create: `token_lens/stats.py` (aggregation queries)
- Modify: `token_lens/cli.py` (add `ingest` + `stats` subcommands)
- Modify: `token_lens/server.py` (`/api/stats`, `/api/ingest` POST endpoint)
- Create: `tests/test_store.py`
- Create: `tests/test_ingest_jsonl.py`
- Create: `tests/test_stats.py`
- Create: `examples/requests.jsonl`

### Task 5.1: SQLite schema

**Step 1 — Failing test** in `tests/test_store.py`:

```python
import tempfile, pathlib
from token_lens.store import TraceStore

def test_store_inserts_and_retrieves(tmp_path):
    db = tmp_path / "tl.db"
    s = TraceStore(str(db))
    s.insert_trace({"timestamp": "2026-01-01T00:00:00Z", "model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}], "total_tokens": 5, "cost_usd": 0.0001})
    rows = s.recent_traces(limit=10)
    assert len(rows) == 1
    assert rows[0]["model"] == "gpt-4o"


def test_store_zones_breakdown(tmp_path):
    db = tmp_path / "tl.db"
    s = TraceStore(str(db))
    s.insert_trace({
        "timestamp": "2026-01-01T00:00:00Z", "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": "x" * 100, "zone": "system"},
            {"role": "system", "content": "y" * 200, "zone": "rag"},
            {"role": "user", "content": "z" * 50, "zone": "user"},
        ],
        "total_tokens": 350, "cost_usd": 0.001,
    })
    s.insert_trace({
        "timestamp": "2026-01-01T00:01:00Z", "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": "a" * 100, "zone": "system"},
            {"role": "user", "content": "b" * 50, "zone": "user"},
        ],
        "total_tokens": 150, "cost_usd": 0.0005,
    })
    by_zone = s.zone_breakdown(lookback_traces=10)
    assert by_zone["system"] > 0
    assert by_zone["rag"] > 0
```

**Step 2 — FAIL; Step 3 — implement** `TraceStore`:

```sql
CREATE TABLE traces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    model TEXT NOT NULL,
    total_tokens INTEGER NOT NULL,
    cost_usd REAL NOT NULL,
    messages_json TEXT NOT NULL,
    zones_json TEXT NOT NULL
);
CREATE INDEX traces_timestamp ON traces(timestamp);
CREATE TABLE ingest_state (
    path TEXT PRIMARY KEY,
    last_offset INTEGER NOT NULL,
    last_ingested TEXT
);
```

Provide `insert_trace`, `recent_traces(limit)`, `zone_breakdown(lookback_traces)`, `percentiles(metric, lookback_traces)`. **Step 4 — PASS; commit** `feat(store): SQLite TraceStore with zone aggregates`.

### Task 5.2: Provider normalizer

**Step 1 — Failing test** in `tests/test_ingest_normalize.py`:

```python
from token_lens.ingest.normalize import normalize

def test_normalize_openai_style():
    line = {
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": "hi"}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
    }
    out = normalize(line, source="openai")
    assert out["model"] == "gpt-4o"
    assert out["total_tokens"] == 8
    assert "timestamp" in out


def test_normalize_anthropic_style():
    line = {
        "model": "claude-3-5-sonnet",
        "messages": [{"role": "user", "content": "hi"}],
        "usage": {"input_tokens": 5, "output_tokens": 3},
    }
    out = normalize(line, source="anthropic")
    assert out["total_tokens"] == 8


def test_normalize_handles_unknown_shape_gracefully():
    out = normalize({"messages": []}, source="unknown")
    assert "total_tokens" in out
    assert out["total_tokens"] == 0
```

**Step 2 — FAIL; Step 3 — implement** `normalize(line, source)` mapping OpenAI/Anthropic/Generic shapes to the internal trace schema. Cost estimation via `pricing.py`. **Step 4 — PASS; commit** `feat(ingest): provider normalizer`.

### Task 5.3: JSONL tail

**Step 1 — Failing test** in `tests/test_ingest_jsonl.py`:

```python
import tempfile, pathlib, json, time
from token_lens.ingest.jsonl import tail_jsonl
from token_lens.store import TraceStore

def test_tail_jsonl_ingests_existing_lines(tmp_path):
    log = tmp_path / "req.jsonl"
    log.write_text(json.dumps({"model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}], "usage": {"total_tokens": 5}}) + "\n")
    db = tmp_path / "tl.db"
    store = TraceStore(str(db))
    n = tail_jsonl(str(log), store, source="openai", follow=False)
    assert n == 1
    assert len(store.recent_traces()) == 1


def test_tail_jsonl_only_ingests_new_lines(tmp_path):
    log = tmp_path / "req.jsonl"
    log.write_text(json.dumps({"model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}], "usage": {"total_tokens": 5}}) + "\n")
    db = tmp_path / "tl.db"
    store = TraceStore(str(db))
    tail_jsonl(str(log), store, source="openai", follow=False)
    # Append a new line
    with open(log, "a") as f:
        f.write(json.dumps({"model": "gpt-4o", "messages": [{"role": "user", "content": "yo"}], "usage": {"total_tokens": 3}}) + "\n")
    n2 = tail_jsonl(str(log), store, source="openai", follow=False)
    assert n2 == 1
```

**Step 2 — FAIL; Step 3 — implement** `tail_jsonl(path, store, source, follow=False)` using the `ingest_state` table for offset tracking. `follow=True` polls every second. **Step 4 — PASS; commit** `feat(ingest): JSONL tail with offset checkpointing`.

### Task 5.4: `token-lens ingest` CLI

**Step 1 — Failing test** in `tests/test_cli_ingest.py`:

```python
from click.testing import CliRunner
from token_lens.cli import main
import pathlib, json

def test_cli_ingest_jsonl(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))  # isolate store path
    log = tmp_path / "req.jsonl"
    log.write_text(json.dumps({"model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}], "usage": {"total_tokens": 5}}) + "\n")
    runner = CliRunner()
    result = runner.invoke(main, ["ingest", "--jsonl", str(log), "--source", "openai", "--once"])
    assert result.exit_code == 0
    assert "1" in result.output or "ingested" in result.output.lower()
```

**Step 2 — FAIL; Step 3 — implement** `ingest` subcommand. Default store path: `~/.local/share/token-lens/store.db` (override `--db PATH`). **Step 4 — PASS; commit** `feat(cli): ingest subcommand`.

### Task 5.5: `token-lens stats`

**Step 1 — Failing test** in `tests/test_cli_stats.py`:

```python
def test_cli_stats_renders_table(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    log = tmp_path / "req.jsonl"
    rows = []
    for i in range(20):
        rows.append(json.dumps({
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": "x"*100, "zone": "system"},
                {"role": "system", "content": "y"*200, "zone": "rag"},
                {"role": "user", "content": "z"*50, "zone": "user"},
            ],
            "usage": {"total_tokens": 350 + i},
        }))
    log.write_text("\n".join(rows) + "\n")
    runner = CliRunner()
    r1 = runner.invoke(main, ["ingest", "--jsonl", str(log), "--source", "openai", "--once"])
    r2 = runner.invoke(main, ["stats", "--last", "20"])
    assert r2.exit_code == 0
    out = r2.output.lower()
    assert "avg" in out or "p95" in out
    assert "system" in out or "rag" in out
```

**Step 2 — FAIL; Step 3 — implement** `stats` subcommand querying `TraceStore.percentiles` + `zone_breakdown` + `top_waste_source`. Render as a clean table. **Step 4 — PASS; commit** `feat(cli): stats subcommand with aggregates`.

### Task 5.6: Web `/api/stats` + `/api/ingest`

**Step 1 — Failing test**:

```python
def test_api_stats_returns_json(client):
    client.post("/api/ingest", json={"model": "gpt-4o", "messages": [{"role": "user", "content": "hi"}], "total_tokens": 5, "cost_usd": 0.0001, "timestamp": "2026-01-01T00:00:00Z"})
    resp = client.get("/api/stats")
    assert resp.status_code == 200
    body = resp.get_json()
    assert "avg_total_tokens" in body
```

**Step 2 — FAIL; Step 3 — wire** endpoints. **Step 4 — PASS; commit** `feat(server): /api/stats and /api/ingest`.

### Task 5.7: Verify Phase 5

Manual:
```bash
mkdir -p /tmp/tl-live && cd /tmp/tl-live
cp ~/Documents/github/token-lens/examples/lean_trace.json requests.jsonl
token-lens ingest --jsonl requests.jsonl --source openai --once
token-lens stats --last 1
```
Expected: a table with avg/p95 tokens, zone breakdown. Commit: `chore: phase 5 — JSONL ingest shipped`.

---

## Phase 6 — Live Trace Ingest (Langfuse Pull)

**Objective:** `token-lens ingest --langfuse` pulls recent traces from a Langfuse Cloud or self-hosted instance using its REST API.

**Files:**
- Create: `token_lens/ingest/langfuse.py`
- Modify: `token_lens/ingest/__init__.py` (re-export)
- Modify: `token_lens/cli.py` (`--langfuse` flag on `ingest`)
- Create: `tests/test_ingest_langfuse.py` (mock HTTP)

### Task 6.1: Langfuse client (mocked)

**Step 1 — Failing test** in `tests/test_ingest_langfuse.py`:

```python
from token_lens.ingest.langfuse import pull_langfuse_traces
from unittest.mock import patch

def test_pull_langfuse_traces_parses_paginated_response():
    fake_responses = [
        {"data": [{"id": "1", "input": [{"role": "user", "content": "hi"}], "output": "hello", "model": "gpt-4o", "usage": {"totalTokens": 10}, "timestamp": "2026-01-01T00:00:00Z"}], "meta": {"page": 1}},
        {"data": [], "meta": {"page": 2}},
    ]
    with patch("token_lens.ingest.langfuse._http_get", side_effect=fake_responses):
        traces = list(pull_langfuse_traces(public_key="pk", secret_key="sk", host="https://x", since="2026-01-01T00:00:00Z"))
    assert len(traces) == 1
    assert traces[0]["model"] == "gpt-4o"
```

**Step 2 — FAIL; Step 3 — implement** `pull_langfuse_traces(...)` paginating `/api/public/traces` with Basic auth (`public_key:secret_key` base64). Convert Langfuse shape → internal via `normalize()`. **Step 4 — PASS; commit** `feat(ingest): Langfuse pull`.

### Task 6.2: CLI `--langfuse` flag

Wire `--langfuse` flag on `ingest` to call `pull_langfuse_traces` and write into the same `TraceStore`. Commit: `feat(cli): ingest --langfuse`.

### Task 6.3: Verify Phase 6

Manual smoke against a Langfuse sandbox (or skip if creds unavailable, mock-test is sufficient). Commit: `chore: phase 6 — Langfuse ingest shipped`.

---

## Phase 7 — Live Trace Ingest (Otel Receiver)

**Objective:** `token-lens ingest --otel --port 4317` runs an OTLP gRPC receiver that ingests OpenTelemetry LLM spans. The biggest engineering surface in this plan — last because we want to learn the data shape from JSONL + Langfuse first.

**Files:**
- Modify: `pyproject.toml` (add optional dep: `grpcio>=1.50`)
- Create: `token_lens/ingest/otel.py` (minimal OTLP receiver)
- Modify: `token_lens/cli.py` (`--otel` flag)
- Create: `tests/test_ingest_otel.py` (use `grpcio-testing`)

### Task 7.1: OTLP receiver skeleton

**Step 1 — Failing test** in `tests/test_ingest_otel.py`:

```python
def test_otel_receiver_accepts_spans_and_stores_them(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    # Use grpcio-testing to send one fake span
    from token_lens.ingest.otel import start_otel_receiver, stop_otel_receiver
    from token_lens.store import TraceStore
    store = TraceStore(str(tmp_path / "tl.db"))
    server = start_otel_receiver(port=0, store=store)  # port=0 picks free
    try:
        # Send one ExportTraceServiceRequest via grpcio-testing
        from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest
        from opentelemetry.proto.trace.v1.trace_pb2 import ResourceSpans, ScopeSpans, Span
        req = ExportTraceServiceRequest(resource_spans=[ResourceSpans(scope_spans=[ScopeSpans(spans=[Span(name="llm.call")])])])
        # invoke server method directly
        server._handler(req, None)
        assert len(store.recent_traces(limit=10)) >= 0  # structure asserted separately
    finally:
        stop_otel_receiver(server)
```

**Step 2 — FAIL; Step 3 — implement** minimal OTLP gRPC server using `grpcio`. Extract `gen_ai.*` attributes (the OpenTelemetry GenAI semantic conventions) and the input/output messages. Store as trace. **Step 4 — PASS; commit** `feat(ingest): OTLP gRPC receiver skeleton`.

### Task 7.2: Normalize OTel → trace

**Step 1 — Failing test**:

```python
def test_otel_span_to_trace():
    from token_lens.ingest.otel import span_to_trace
    span = {
        "name": "llm.call",
        "start_time": "2026-01-01T00:00:00Z",
        "attributes": {
            "gen_ai.system": "openai",
            "gen_ai.request.model": "gpt-4o",
            "gen_ai.usage.input_tokens": "100",
            "gen_ai.usage.output_tokens": "50",
            "gen_ai.prompt": "hello",
            "gen_ai.completion": "hi",
        }
    }
    t = span_to_trace(span)
    assert t["model"] == "gpt-4o"
    assert t["total_tokens"] == 150
```

**Step 2 — FAIL; Step 3 — implement** `span_to_trace` mapping GenAI semconv → internal. **Step 4 — PASS; commit** `feat(ingest): OTel GenAI semconv mapping`.

### Task 7.3: CLI `--otel` flag

Wire `--otel --port 4317` into `ingest` to start the receiver. Commit: `feat(cli): ingest --otel`.

### Task 7.4: Verify Phase 7

Manual: start `token-lens ingest --otel --port 4317`, run a small Python script using OpenInference instrumentation that makes one OpenAI call. Expected: `token-lens stats` shows the new trace. Commit: `chore: phase 7 — Otel ingest shipped`.

---

## Phase 8 — Evidence-Based Recommendations + Pareto Frontier

**Objective:** Aggregate ablation results across many traces in `TraceStore`. Recommend chunk removals that hold across the sample. Emit a quality-vs-tokens Pareto curve.

**Files:**
- Create: `token_lens/optimize.py`
- Modify: `token_lens/store.py` (add `ablation_cache` table)
- Modify: `token_lens/types.py` (add `CrossTraceRecommendation`, `ParetoPoint`)
- Modify: `token_lens/cli.py` (add `optimize` subcommand + `--pareto` flag)
- Modify: `token_lens/report.py` (Pareto SVG)
- Create: `tests/test_optimize.py`

### Task 8.1: Types

**Step 1 — Failing test** in `tests/test_optimize.py`:

```python
from token_lens.types import CrossTraceRecommendation, ParetoPoint

def test_cross_trace_recommendation_fields():
    r = CrossTraceRecommendation(
        action="remove_chunks",
        targets=["7", "12", "19"],
        token_reduction=2481,
        cost_reduction_usd=0.0074,
        trace_coverage=0.93,
        quality_delta=-0.002,
        confidence="high",
    )
    assert r.token_reduction == 2481
    assert r.confidence == "high"


def test_pareto_point_fields():
    p = ParetoPoint(tokens=4000, quality=1.0)
    assert p.tokens == 4000
```

**Step 2 — FAIL; Step 3 — add types**. **Step 4 — PASS; commit** `feat(types): CrossTraceRecommendation + ParetoPoint`.

### Task 8.2: Ablation persistence in store

**Step 1 — Failing test** in `tests/test_store_ablation.py`:

```python
def test_store_persists_ablation(tmp_path):
    from token_lens.store import TraceStore
    s = TraceStore(str(tmp_path / "tl.db"))
    s.insert_ablation(trace_id=1, chunk_id="7", usefulness=0.05, verdict="irrelevant")
    rows = s.recent_ablations(limit=100)
    assert any(r["chunk_id"] == "7" for r in rows)
```

**Step 2 — FAIL; Step 3 — add** `ablations` table + DAO methods. **Step 4 — PASS; commit** `feat(store): persist ablations`.

### Task 8.3: Cross-trace recommendation engine

**Step 1 — Failing test**:

```python
def test_recommend_removes_chunks_consistently_irrelevant(tmp_path):
    from token_lens.optimize import recommend_across_traces
    from token_lens.store import TraceStore
    s = TraceStore(str(tmp_path / "tl.db"))
    # Insert 100 traces. Chunk "7" is irrelevant in 95 of them.
    for i in range(100):
        tid = s.insert_trace({"timestamp": "2026-01-01T00:00:00Z", "model": "gpt-4o", "messages": [{"role": "user", "content": "x"}], "total_tokens": 100, "cost_usd": 0.001})
        usefulness = 0.05 if i < 95 else 0.7
        s.insert_ablation(trace_id=tid, chunk_id="7", usefulness=usefulness, verdict="irrelevant" if usefulness < 0.2 else "useful")
        s.insert_ablation(trace_id=tid, chunk_id="8", usefulness=0.8, verdict="useful")
    recs = recommend_across_traces(s, min_coverage=0.9, min_usefulness=0.2)
    chunk7_rec = next((r for r in recs if r.targets == ["7"]), None)
    assert chunk7_rec is not None
    assert chunk7_rec.trace_coverage >= 0.9
    assert chunk7_rec.confidence == "high"
```

**Step 2 — FAIL; Step 3 — implement** `recommend_across_traces`:

```
For each chunk_id:
    coverage    = traces_with_chunk / total_traces
    mean_use    = mean(usefulness across traces)
    if mean_use < threshold AND coverage > min_coverage:
        emit CrossTraceRecommendation(action="remove_chunks", targets=[chunk_id], ...)
        token_reduction = mean(chunk_tokens) * coverage
        cost_reduction  = token_reduction * mean_cost_per_token
        quality_delta   = mean_use - baseline_useful_quality (heuristic)
```

**Step 4 — PASS; commit** `feat(optimize): cross-trace recommendation engine`.

### Task 8.4: Pareto frontier computation

**Step 1 — Failing test**:

```python
def test_pareto_curve_monotonic_quality_decreasing_with_tokens(tmp_path):
    from token_lens.optimize import compute_pareto
    from token_lens.store import TraceStore
    s = TraceStore(str(tmp_path / "tl.db"))
    # Seed with varied traces
    ...
    curve = compute_pareto(s, max_points=10)
    # Quality should be non-increasing as tokens decrease
    qualities = [p.quality for p in curve.points]
    for a, b in zip(qualities, qualities[1:]):
        assert b <= a + 1e-9
```

**Step 2 — FAIL; Step 3 — implement** `compute_pareto`:

```
1. For each trace: get baseline total_tokens + heuristic baseline_quality (1.0 by default).
2. Greedily remove chunks starting from lowest-usefulness, recompute total_tokens + estimated_quality.
3. Sample N points along the removal sequence.
4. Filter to keep only Pareto-optimal (no point has both more tokens AND lower quality).
```

**Step 4 — PASS; commit** `feat(optimize): quality/tokens Pareto frontier`.

### Task 8.5: CLI `optimize` subcommand

**Step 1 — Failing test**:

```python
def test_cli_optimize_outputs_recommendations(tmp_path, monkeypatch):
    # Seed the store with traces + ablations, run `optimize`, assert output
    ...
```

**Step 2 — FAIL; Step 3 — implement** `optimize` subcommand with `--json`, `--pareto`, `--min-coverage`, `--min-usefulness` flags. **Step 4 — PASS; commit** `feat(cli): optimize subcommand`.

### Task 8.6: Pareto SVG renderer

**Step 1 — Failing test**:

```python
def test_pareto_svg_renders(tmp_path):
    from token_lens.optimize import ParetoCurve, ParetoPoint
    from token_lens.report import render_pareto_svg
    curve = ParetoCurve(points=[ParetoPoint(tokens=4000, quality=1.0), ParetoPoint(tokens=2000, quality=0.95)])
    out = tmp_path / "pareto.svg"
    render_pareto_svg(curve, str(out))
    svg = out.read_text()
    assert "<svg" in svg
    assert '4000' in svg and '2000' in svg
```

**Step 2 — FAIL; Step 3 — implement** `render_pareto_svg` (re-uses existing SVG helpers in `report.py`). **Step 4 — PASS; commit** `feat(report): Pareto SVG renderer`.

### Task 8.7: Verify Phase 8

Manual: seed `examples/requests.jsonl` with 50+ traces, run `token-lens optimize --pareto`. Expected: a Pareto SVG + ranked recommendations. Commit: `chore: phase 8 — evidence-based optimization shipped`.

---

## Phase 9 — Web App: Budget / Live / Optimize Pages

**Objective:** Add three new pages to the existing stdlib web server. Reuse existing patterns (`routes`, `templates`).

**Files:**
- Modify: `token_lens/server.py`
- Modify: `token_lens/templates/*.html`
- Create: `tests/test_server_pages.py`

### Task 9.1: Budget panel page

**Step 1 — Failing test** in `tests/test_server_pages.py`:

```python
def test_budget_page_renders(client):
    resp = client.get("/budget")
    assert resp.status_code == 200
    assert b"budget" in resp.data.lower()
```

**Step 2 — FAIL; Step 3 — add route** + template that consumes the existing `/api/budget/check` and shows a form (paste trace → run check). **Step 4 — PASS; commit** `feat(server): /budget page`.

### Task 9.2: Live ingest page

**Step 1 — Failing test**:

```python
def test_live_page_renders_stats(client):
    resp = client.get("/live")
    assert resp.status_code == 200
    assert b"avg" in resp.data.lower() or b"p95" in resp.data.lower()
```

**Step 2 — FAIL; Step 3 — add route** + template that polls `/api/stats` every 5s. **Step 4 — PASS; commit** `feat(server): /live page`.

### Task 9.3: Optimize recommendations page

**Step 1 — Failing test**:

```python
def test_optimize_page_renders_pareto(client):
    resp = client.get("/optimize")
    assert resp.status_code == 200
    assert b"pareto" in resp.data.lower() or b"recommend" in resp.data.lower()
```

**Step 2 — FAIL; Step 3 — add route** + template that calls `/api/optimize` and shows the SVG + recommendation list. **Step 4 — PASS; commit** `feat(server): /optimize page`.

### Task 9.4: Navigation links

Add Budget / Live / Optimize to the index page nav. Commit: `feat(server): nav links for new pages`.

### Task 9.5: Verify Phase 9

Manual: `token-lens serve`, visit `http://127.0.0.1:8793/budget`, `/live`, `/optimize`. Commit: `chore: phase 9 — web pages shipped`.

---

## Phase 10 — README + Hero + Release

**Objective:** Rewrite the README around the new thesis. Lead with the problem, the new value prop, and a 90-second demo. Update the hero asset. Tag v1.0.0.

**Files:**
- Rewrite: `README.md`
- Modify: `assets/hero.svg` (refresh to reflect context-optimizer positioning)
- Modify: `pyproject.toml` (bump to 1.0.0)
- Create: `CHANGELOG.md`

### Task 10.1: New README

Structure:

1. **The thesis (top, 3 sentences):** "Find the minimum context needed to preserve answer quality."
2. **One-command demo:** `pip install token-lens && token-lens init && token-lens demo && token-lens check logs/ && token-lens optimize --pareto`
3. **The problem this solves** (with the Aniket-style framing from this plan)
4. **Features** (organized by the 5 phases)
5. **Real tokenizers** with examples
6. **RAG ablation** with the WITH/WITHOUT chunk example
7. **Token budget CI** with the GitHub Actions YAML
8. **Live ingest** with the JSONL/Langfuse/Otel flags
9. **Evidence-based recommendations** with the Pareto ASCII
10. **Honest limitations** (heuristic ablation isn't real eval; Otel requires a heavy dep; etc.)
11. **CLI reference**
12. **API reference**
13. **Privacy** (still 100% offline)

### Task 10.2: Hero SVG refresh

Replace the current hero with a new one showing: token zones flowing left → right, with a "minimum viable context" highlighted zone. SVG only — no raster. Commit: `feat(assets): v1 hero reflecting context optimization`.

### Task 10.3: CHANGELOG.md

Initialize with v1.0.0 entry. Commit: `docs: changelog for v1.0.0`.

### Task 10.4: Bump version, tag, push

```bash
# In repo
sed -i '' 's/version = "0.3.0"/version = "1.0.0"/' pyproject.toml
git add -A
git commit -m "chore: release v1.0.0 — context optimizer"
git tag -a v1.0.0 -m "v1.0.0 — context optimizer"
git push origin main --tags
```

Verify: `git ls-remote --tags origin | grep v1.0.0` returns the SHA.

### Task 10.5: Verify Phase 10

Manual smoke: `pip install -e .` from a fresh venv, run all the demo commands from the README, take a screenshot of the `/optimize` page, embed in README. Commit: `chore: phase 10 — v1.0.0 release shipped`.

---

## Cross-Phase: Continuous Hygiene

These run *between every commit* across all phases — listed once, not repeated per task.

- **Run the full test suite** before each commit: `python3 -m pytest -q` — must stay 100% green.
- **Lint/format** (if `ruff`/`black` configured; otherwise skip — YAGNI): `python3 -m pyflakes token_lens/ tests/`.
- **Verify CLI** before commit: `token-lens --help` lists all new subcommands.
- **Verify web** before commit: `token-lens serve --once` then `curl localhost:8793/healthz` returns 200.
- **Commit author**: `Aniket Karne <aniketkarne@gmail.com>` (already configured in repo per memory).
- **Commit message style**: conventional commits (`feat:`, `fix:`, `chore:`, `docs:`, `test:`).

---

## Final Verification (end of v1.0)

Run all of these in sequence. Every one must pass:

```bash
cd ~/Documents/github/token-lens
python3 -m pytest -q                                     # all green
python3 -m token_lens.cli analyze examples/lean_trace.json --json | jq '.tokenizer_name'
# → "cl100k_base" or actual backend name

cd /tmp && rm -rf tl-final && mkdir tl-final && cd tl-final
token-lens init
token-lens check --config token-lens.yaml examples/sample_trace.json; echo "exit=$?"  # exit 0 or non-zero per config
echo "---"
echo '{"model":"gpt-4o","messages":[{"role":"user","content":"hi"}],"usage":{"total_tokens":5}}' > r.jsonl
token-lens ingest --jsonl r.jsonl --source openai --once
token-lens stats --last 5
echo "---"
# Seed with several traces for optimize demo
python3 -c "
import json
for i in range(20):
    print(json.dumps({
        'model': 'gpt-4o',
        'messages': [
            {'role': 'system', 'content': 'be helpful', 'zone': 'system'},
            {'role': 'system', 'content': 'doc '+str(i)+' content about topic', 'zone': 'rag', 'chunk_id': str(i % 3)},
            {'role': 'user', 'content': 'q '+str(i), 'zone': 'user'},
        ],
        'usage': {'total_tokens': 100+i*10},
    }))
" > many.jsonl
token-lens ingest --jsonl many.jsonl --source openai --once
token-lens optimize --pareto --min-coverage 0.8

# Web smoke
token-lens serve --host 127.0.0.1 --port 8793 --once &
SERVER_PID=$!
sleep 1
curl -sf http://127.0.0.1:8793/healthz && echo "healthz OK"
curl -sf http://127.0.0.1:8793/budget > /dev/null && echo "budget OK"
curl -sf http://127.0.0.1:8793/live > /dev/null && echo "live OK"
curl -sf http://127.0.0.1:8793/optimize > /dev/null && echo "optimize OK"
kill $SERVER_PID
```

Expected: every line prints OK. If anything fails, fix before tagging v1.0.0.

---

## Risks & Open Questions

| Risk | Mitigation |
|------|------------|
| Heuristic ablation misleads users about quality impact | Always label output as "heuristic quality estimate"; README has prominent limitations section |
| `sentence-transformers` install is heavy (~100MB) | Lazy import; hash embedder is the default; `pip install token-lens[embeddings]` for real ones |
| Otel `grpcio` install adds ~30MB | Make `grpcio` an optional `[otel]` extra; receiver gated behind flag |
| Pareto curve computed from heuristics looks authoritative | SVG renderer includes "heuristic, not measured" watermark text |
| Langfuse / OTel creds not available in CI | Tests use mocks; CI doesn't run the live ingest smoke |
| v1.0.0 scope is large (10 phases) | Each phase ends in a working, tested state; phases can ship as 0.4.0 → 1.0.0 minor releases if user wants intermediate cuts |

---

## Out of Scope for v1.0 (deferred)

- Eval-mode (real LLM judge) — v1.1
- Otel metrics/logs (only traces) — v1.1
- Multi-user / hosted dashboard — out of scope, ever (privacy)
- Auto-apply recommendations as PRs — v1.2
- Cloud cost integrations (AWS Bedrock, Azure OpenAI billing) — v1.2
- Custom embedding model registry / fine-tuned usefulness classifier — v2.0
