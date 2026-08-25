#!/bin/sh
# Usage: status.sh — SessionStart orientation: branch, dirty, unpushed, recent commits.
set -u
case "${1:-}" in --help|-h) sed -n '2p' "$0"; exit 0;; esac
echo "branch: $(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo '?')"
echo "dirty:  $(git status --porcelain 2>/dev/null | wc -l | tr -d ' ') files"
if git rev-parse --abbrev-ref '@{u}' >/dev/null 2>&1; then
  echo "unpushed: $(git log '@{u}..HEAD' --oneline | wc -l | tr -d ' ') commits (debt, not progress)"
else
  echo "unpushed: no upstream"
fi
echo "recent:"; git log -5 --format='  %h %s' 2>/dev/null
exit 0
