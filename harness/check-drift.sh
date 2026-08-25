#!/bin/sh
# Usage: check-drift.sh [--no-lock] [repo-root]
# Committed artifacts must not be stale: generated trees (**/_generated/**) have no
# diff and no untracked files; uv.lock matches pyproject (skip with --no-lock).
set -eu
case "${1:-}" in --help|-h) sed -n '2,4p' "$0"; exit 0;; esac
lock=1
[ "${1:-}" = "--no-lock" ] && { lock=0; shift; }
dir=${1:-.}
cd "$dir" 2>/dev/null || { echo "drift: no such directory: $dir" >&2; exit 2; }
# A check that reports "clean" because it could not look is worse than one that errors.
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || {
  echo "drift: not a git work tree: $(pwd)" >&2
  exit 2
}
# `git diff` with no ref compares worktree<->index, so a staged stale artifact would pass.
# Compare against HEAD. A repo with no commits has no HEAD to compare against.
if git rev-parse --verify -q HEAD >/dev/null &&
   ! git diff --exit-code --stat HEAD -- ':(glob)**/_generated/**' >/dev/null 2>&1; then
  echo "drift: generated files differ from HEAD — regenerate and commit"
  git diff --stat HEAD -- ':(glob)**/_generated/**'; exit 1
fi
untracked=$(git ls-files --others --exclude-standard | grep -E '(^|/)_generated/' || true)
if [ -n "$untracked" ]; then echo "drift: untracked generated files:"; echo "$untracked"; exit 1; fi
if [ "$lock" -eq 1 ] && [ -f uv.lock ]; then
  uv lock --check || { echo "drift: uv.lock is stale — run uv lock and commit"; exit 1; }
fi
exit 0
