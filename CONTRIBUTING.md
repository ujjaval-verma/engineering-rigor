# Contributing

Thanks for looking. This repo is small on purpose, and the bar for a change is the same for
humans and agents: the gate decides, not the reviewer's mood.

## Setup

```sh
uv tool install rust-just   # once per machine
just sync                   # deps from the lock + git hooks (core.hooksPath)
just doctor                 # confirms uv, just, python, hooks, exec bits
```

`just` with no args is the menu. `just check` is the fast gate (pre-commit); `just verify` is the
full one (pre-push, CI). If either is red, the change isn't ready — there is no `--no-verify` here.

## Making a change

- **One concern per commit.** Subject is `type(scope)?: subject`, ≤ 72 chars, type one of
  `feat fix refactor docs chore test perf build` — `commit-msg` checks it.
- **Deferred work goes in [`docs/FOLLOWUPS.md`](docs/FOLLOWUPS.md)**, never as a marker in code
  (`just markers` fails on those). Format: `- [ ] <what> — why deferred: <reason> (added YYYY-MM-DD)`.
- **New root markdown** needs a reason; `just stray-md` only allows
  README/CLAUDE/AGENTS/CHANGELOG/CONTRIBUTING.
- **Changing the gate itself** (`justfile`, `harness/`, `.githooks/`, `.claude/`): edit by hand in
  an editor — agents are refused on purpose. Harness scripts stay ≤ 80 lines (≤ 100 for the
  secret and link scanners), one job each, `--help` on every one, and are the most strictly
  tested code in the repo: write the failing test in `tests/harness/` first.
- **Adding an invariant**: add the row to the table in [`CLAUDE.md`](CLAUDE.md) *and* name a real
  enforcement site — `just invariants` fails if the site doesn't exist. `prose` is allowed, but
  say so.
- **Model ids** in `src/` must be on the [`AGENTS.md`](AGENTS.md) allow-list (`just models`).

## Pull requests

Keep them slice-sized: one PR-sized change that crosses every layer, tracer bullet first. CI runs
`just verify` on the pushed tree, which is the only reviewer that cannot be argued with. Docs-only
PRs skip CI (`paths-ignore: docs/**`); run `just links` locally.

Bugs in the gate — a bypass it should have caught, a false refusal — are the most useful reports.
Open an issue with the exact command and the message you got.
