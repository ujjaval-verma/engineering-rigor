#!/bin/sh
# Usage: check-no-todo.sh [repo-root]
# Fails if any tracked file contains a deferred-work marker outside docs/FOLLOWUPS.md,
# the one legal home for follow-ups. Markers match case-insensitively, as whole words.
set -eu
case "${1:-}" in --help|-h) sed -n '2,4p' "$0"; exit 0;; esac
root=${1:-.}
cd "$root"
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || {
  echo "no-todo: not a git work tree: $root" >&2
  exit 2
}
# Explicit boundaries, not grep -w: -w counts '-' and '.' as boundaries, so this
# script's own hyphenated filename would match wherever the repo mentions it.
bound='[^A-Za-z0-9_.-]'
pat="(^|$bound)(TO""DO|FIX""ME|XXX|HA""CK)($bound|$)"
hits=$(git ls-files -z | grep -zv -e '^docs/FOLLOWUPS.md$' -e '^harness/check-no-todo.sh$' \
  | xargs -0 grep -HniIE -- "$pat" 2>/dev/null || true)
[ -z "$hits" ] && exit 0
echo "no-todo: deferred-work markers found; move them to docs/FOLLOWUPS.md:"
echo "$hits"
exit 1
