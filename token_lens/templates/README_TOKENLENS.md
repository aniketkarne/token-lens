# token-lens

This project now has token-lens configured. Here's what you got:

- `token-lens.yaml` — budgets and tokenizer config.
- `examples/sample_trace.json` — a small trace you can analyze immediately:

      token-lens analyze examples/sample_trace.json

- `.github/workflows/token-lens.yml` — a CI workflow that fails the build when
  any trace in `logs/` exceeds a budget.

## Next steps

1. Pipe your real traces into a JSONL log under `logs/requests.jsonl`.
2. Tighten budgets in `token-lens.yaml`.
3. Run `token-lens check` locally before pushing.
4. Ingest real traffic with `token-lens ingest --jsonl logs/requests.jsonl`.

Docs: https://github.com/aniketkarne/token-lens