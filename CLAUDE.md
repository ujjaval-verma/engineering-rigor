# CLAUDE.md

## The gate

- `just check` (fast) runs on pre-commit and as a **blocking** Stop/SubagentStop hook —
  work isn't done until it's green. `just verify` (full) runs on pre-push and CI.
- `--no-verify`, `hooksPath` tricks, force-push (`-f`, `--force`, `+refspec`), `pip`, and
  shell/file-tool edits to `justfile`, `harness/`, `.githooks/`, `.claude/`, `.env` are
  blocked by `harness/guard-gate.sh` — it matches the write verbs it names (`sed -i` and
  `--in-place`, `perl -i`, `rm`/`mv`/`cp`/`tee`, `dd`, `git restore`/`checkout --`,
  redirects, `python -c` and stdin scripts); its header lists what it still cannot see.
  Never work around the gate; fix the code.
- The gate's own files — `justfile`, `harness/`, `.githooks/`, `.claude/` — are **human-edited**.
  The deny list's Edit rules (which also govern Write) refuse them, and guard-gate refuses
  rewriting them from a shell. That friction is deliberate: a gate an agent can edit is not a
  gate. To change one, open it in an editor yourself. The `.claude/settings.json` deny list is
  defence-in-depth only — it matches command *text*, so `guard-gate.sh`, which parses the
  command, is the real enforcement.
- Every harness script stays ≤80 lines (≤100 for the secret and link scanners): one job each,
  readable in a sitting, `--help` on every one.
- `uv` everywhere, never `pip`. `just` (no args) is the menu.

## Invariants

Each row names where it is enforced. `just invariants` fails if the site doesn't exist.

| # | invariant | enforced by |
|---|---|---|
| 1 | Money is integer cents, never float | prose |
| 2 | Contracts in `core/` are pyright-strict | `pyproject.toml` |
| 3 | No deferred-work markers in code; `docs/FOLLOWUPS.md` is the only home | `harness/check-no-todo.sh` |
| 4 | Root markdown is README/CLAUDE/AGENTS/CHANGELOG/CONTRIBUTING only | `harness/check-stray-md.sh` |
| 5 | Relative doc links resolve | `harness/check-links.py` |
| 6 | No credentials in tracked files | `harness/check-secrets.py` |
| 7 | Model ids in `src/` are on the AGENTS.md allow-list | `harness/check-models.py` |
| 8 | Generated trees and `uv.lock` never drift | `harness/check-drift.sh` |
| 9 | Commit subjects are `type(scope)?: subject` | `.githooks/commit-msg`, `harness/check-commit-msg.py` |
| 10 | Agent sessions can't bypass the gate; pushes carry no uncommitted harness edits | `harness/guard-gate.sh`, `.githooks/pre-push` |
| 11 | Network and LLM tests are opt-in markers; the gate refuses `PYTEST_ADDOPTS` | `pyproject.toml`, `justfile` |
| 12 | Tests pin non-determinism via dependency injection, not `_override` fields | prose |

A row says `prose` when nothing mechanises it — row 1 is a review rule, not a check, and
saying so is the point: `just invariants` proves the named site exists, never that it works.
Rows 9 and 11 name the hook and the config that actually run, not the script they wrap.
Row 10 is deliberately narrow: `.githooks/pre-push` compares your **working tree's** harness
files against your local HEAD and runs `just verify` on each pushed commit. It cannot judge a
gate that was gutted *in a commit* — that commit's own `justfile` is what verify runs. Committed
tampering is caught by code review and by CI, which runs `just verify` on the pushed tree.

The deferred-work check (`just markers`) is the one recipe whose name deliberately avoids the
marker words it looks for.

## Docs: durable vs transient

Durable (committed): `README.md`, `CLAUDE.md`, `AGENTS.md`, `docs/**`. Transient (gitignored):
`docs/superpowers/**`, `out/`, `work/`. When unsure, it's scratch.

## Gotchas

- First run of a new golden test fails on purpose ("created it — review and re-run").
- `just models` reads any digit-bearing `claude-...` token as a model id, on purpose. For the
  ones that aren't (a bucket name, a dated report), end the line with `# rigor: ignore-model`.
- `just init NAME` renames the placeholder package; run it once, before anything else. It walks
  `git ls-files`, so anything untracked or gitignored is left alone.
