# Agents

Read `CLAUDE.md` first — the gate rules live there. This file is orchestration policy.

## Model policy

`just models` fails the build if `src/` references a model not `allowed` here.
Rows carry a verification date and a confidence — model claims are dated, never assumed.

**`verified` is the date a human last confirmed these id strings against the vendor's published
model list** — not the date the row was written and not the date an agent asserted it. Bump it
only after re-reading the vendor list; if you cannot, lower `confidence` instead of moving the
date. Ids are exact strings, copied verbatim, never reconstructed from a marketing name.

| model | policy | use | verified | confidence |
|---|---|---|---|---|
| `claude-fable-5` | allowed | main-session orchestration; never called from repo code | 2026-08-24 | high |
| `claude-opus-5` | allowed | dev subagents; every in-repo LLM call by default | 2026-08-24 | high |
| `claude-sonnet-5` | allowed | paths designed to be cheap or swappable for an open-weight model | 2026-08-24 | high |
| `claude-haiku-4-5-20251001` | banned | never — quality floor | 2026-08-24 | high |

## Slice delivery

- A slice is one PR-sized change that crosses every layer. Tracer bullet first, then thicken.
  Never "all the types this week, all the adapters next week".
- One concern per commit. Refactor-then-feature is two commits; the refactor body says "no behavior change".
- Commit subjects are `type(scope): subject`; `git log --grep='(P3)'` is the tracker. No tracker file.
- Parallel work only for genuinely independent slices, ≤ 3 worktrees, integrate on `main` only.
- Review is batched by slice family; each slice declares `review: family | standalone | none`.
- "Shipped" means `origin/main`. `git log @{u}..HEAD` is debt, not progress.

## Test scope (graded rigor)

| surface | discipline |
|---|---|
| `core/` contracts, money, gate logic | TDD, strict |
| lookup tables, pricing curves | fixture tables |
| pydantic model shape | none — pydantic enforces it; smoke tests are ceremony |
| glue / CLI | verified end-to-end, no unit ceremony |
| `harness/` | strictest TDD in the repo — it is the product |

After every green test: scan for duplication, long functions, boolean traps, leaked
abstractions. Fix now, in this slice, as a separate commit.
