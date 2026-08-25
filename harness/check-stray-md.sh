#!/bin/sh
# Usage: check-stray-md.sh [repo-root]
# Root-level *.md must be one of README CLAUDE AGENTS CHANGELOG CONTRIBUTING.
# Everything else is a doc (docs/) or scratch (gitignored).
set -eu
case "${1:-}" in --help|-h) sed -n '2,4p' "$0"; exit 0;; esac
cd "${1:-.}"
allow=' README.md CLAUDE.md AGENTS.md CHANGELOG.md CONTRIBUTING.md '
bad=""
for f in $(git ls-files -- '*.md' | grep -v '/'); do
  case "$allow" in *" $f "*) ;; *) bad="$bad $f";; esac
done
[ -z "$bad" ] && exit 0
echo "stray-md: root markdown not allowed:$bad (move under docs/ or gitignore)"
exit 1
