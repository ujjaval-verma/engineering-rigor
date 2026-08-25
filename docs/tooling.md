# Tooling decisions

Format: pick · why · upgrade trigger. If a trigger fires, revisit; otherwise don't.

| area | pick | why | upgrade trigger |
|---|---|---|---|
| deps | `uv`, `uv run --locked` for project code; bare `python3`/`sh` for `harness/` | stale lock fails instead of silently re-locking; the harness is stdlib-only so it runs before `just sync` ever has, and ports to non-Python projects | — |
| tasks | `just` | one discovery surface; hooks, CI and humans call the same recipe | — |
| lint/format | `ruff` (ANN, T20, FBT, FIX on) | single tool; every ignore carries a reason | — |
| types | `pyright`, strict on `core/` | stable; rigor where contracts live | `ty` 1.0 → one line in `just types` |
| models | `pydantic` v2, `pydantic-settings` | shape enforced at boundaries; no tests for shape | — |
| tests | `pytest --strict-markers`, `needs_*` markers, golden fixture | `just test-fast` is offline and deterministic; `slow` (real git hooks) needs `uv` and a warm cache or network, and `needs_llm`/`needs_net` are opt-in always | — |
| hooks | `.githooks/` via `core.hooksPath`, installed by `just sync` | versioned, zero install, tamper-checked on push | — |
| agent gate | Claude `Stop`/`SubagentStop` → `just check`, exit 2 | "done" means green, mechanically | suite > 30 s → move tests to `verify` |
| CI | GitHub Actions, `just verify` only | same recipe as pre-push; no duplicated pins | — |
| agent permissions | `.claude/settings.json` deny list + `harness/guard-gate.sh` | the deny list is a coarse **prefix** filter (Claude Code `Bash(...)` rules are exact or trailing-`*` only); guard-gate is the one that actually parses the command | — |
| coverage | none (advisory `just cov`) | guardrails are typed contracts + golden tests, not a number | — |

## Sharp edges worth knowing

- **`paths-ignore: docs/**` keeps docs-only PRs off CI.** If you make `verify` a *required*
  status check, remove `paths-ignore` or add a no-op `verify` job on the ignored paths —
  otherwise a docs-only PR never produces the check and can never merge.
- **`set dotenv-load := true` means `just` loads `.env` into every recipe.** Never put
  `PYTEST_ADDOPTS` in `.env`: `just env-guard` will fail `just check` and `just verify`
  (the two recipes that depend on it), and its message
  ("unset it") points at your shell while the value is coming from a file.
- **The first `just types` downloads a Node runtime** (the `pyright` wheel fetches it). That
  cost lands in `check`, not `sync`, which is why CI times both.
- **Measured cold local run** (2026-08-24, Apple silicon macOS, `uv cache clean` first):
  `just sync` 2.2 s, `just check` 7.7 s, 9.9 s combined. First GitHub Actions run
  (2026-08-25): `just sync` 2.8 s, `just check` 12.0 s — the README's "~15 s" badge. Both
  machines had `node`, so `pyright` skipped the runtime download; CI's `time` lines stay the
  authority.

## Deliberately not added

pre-commit framework · tox/nox · black/isort/flake8 · mypy · Copier · coverage thresholds ·
Docker/DB (add a `db-up` recipe when you need one) · LangChain-class frameworks · GitLab CI.
