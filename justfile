set dotenv-load := true
set shell := ["sh", "-eu", "-c"]

# `just` with no args is the menu.
default:
    @just --list --unsorted

# Install deps from the lock and wire git hooks. The only setup step.
sync *ARGS:
    uv sync --locked {{ARGS}}
    git config core.hooksPath .githooks

# Format and autofix.
fmt:
    uv run --locked ruff format .
    uv run --locked ruff check --fix .

# Format check + lint (no writes).
lint:
    uv run --locked ruff format --check .
    uv run --locked ruff check .

# Type check (strict on core/, basic elsewhere).
types:
    uv run --locked pyright

# `-m` here replaces the default expression in pyproject, so it repeats it in full.
# `just --list` shows only the last comment line, so the description goes last.
# Fast unit + harness tests.
test-fast:
    uv run --locked pytest tests/unit tests/harness -m "not needs_llm and not needs_net and not slow"

# Everything, including capability-marked tests.
test-all:
    uv run --locked pytest -m ""

# The gate must be deterministic.
env-guard:
    test -z "${PYTEST_ADDOPTS:-}" || { echo "PYTEST_ADDOPTS is set; unset it — the gate must be deterministic"; exit 1; }

# Fast gate: pre-commit and Claude Stop hook. Target < 30 s.
check: env-guard lint types test-fast

# Advisory coverage — never gates.
cov:
    uv run --locked pytest --cov=src --cov-report=term-missing -m ""

# Delete tool caches and the scratch trees (`out/`, `work/`).
clean:
    rm -rf .pytest_cache .ruff_cache .pyright_cache .coverage out work

# --- full gate -------------------------------------------------------------

# Fail if generated files or `uv.lock` differ from what is committed.
drift:
    sh harness/check-drift.sh

# Fail on credential-shaped strings in tracked files.
secrets:
    python3 harness/check-secrets.py

# Fail on relative links in markdown that point at nothing.
links:
    python3 harness/check-links.py

# Named `markers`, not the marker word it hunts for — the recipe would fail its own check.
markers:
    sh harness/check-no-todo.sh

# Fail on root markdown outside README/CLAUDE/AGENTS/CHANGELOG/CONTRIBUTING.
stray-md:
    sh harness/check-stray-md.sh

# Fail on model ids in `src/` that the AGENTS.md allow-list does not carry.
models:
    python3 harness/check-models.py --src src --agents AGENTS.md

# Fail if a CLAUDE.md invariant names an enforcement site that does not exist.
invariants:
    python3 harness/check-invariants.py --claude CLAUDE.md --root .

# Full gate: pre-push and CI.
verify: check drift secrets links markers stray-md models invariants test-all

# --- session ---------------------------------------------------------------

# Where am I: branch, dirty files, hook wiring. Also the session-start banner.
status:
    @sh harness/status.sh

# Is this machine set up: uv, just, python version, git hooks, exec bits.
doctor:
    sh harness/doctor.sh

# One-time rename of the placeholder package (relocks so --locked keeps working).
init NAME:
    python3 harness/init.py {{NAME}}
    uv lock
