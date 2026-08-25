#!/bin/sh
# Usage: gate.sh [recipe] — Claude Stop/SubagentStop hook. Runs `just <recipe>` (default: check);
# on failure tails 40 lines to stderr and exits 2 so the agent must fix before finishing.
set -u
case "${1:-}" in --help|-h) sed -n '2,3p' "$0"; exit 0;; esac
recipe=${1:-check}
cd "${CLAUDE_PROJECT_DIR:-.}"
out=$(mktemp)
if just "$recipe" >"$out" 2>&1; then rm -f "$out"; exit 0; fi
{ echo "just $recipe FAILED — fix before finishing:"; tail -40 "$out"; } >&2
rm -f "$out"
exit 2
