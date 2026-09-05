# token-lens compare

**tokens:** `1,496` → `160` (-1,336, -89.3%)
**cost:** `$0.007480` → `$0.000800` (`$-0.006680`)

| zone | before | after | Δ |
|---|---:|---:|---:|
| tool_schema | 444 | 93 | -351 |
| few_shot | 103 | 17 | -86 |
| rag | 835 | 32 | -803 |
| history | 96 | — | -96 |
| user | 18 | 18 | +0 |

## Recommendations to push `after` further

- **Drop 2 low-scoring RAG chunk(s)** — ~32 tok (~$0.000160). 2 of 2 RAG chunks score below 0.20 vs. your last user query (best-of n-gram/LCS/containment).
  - *how:* Re-rank or filter your retriever: drop chunks with score < 0.20; start with index #0.
