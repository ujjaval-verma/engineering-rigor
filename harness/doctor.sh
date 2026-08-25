#!/bin/sh
# Usage: doctor.sh — verify toolchain: uv, just, python version, hooksPath, hook bits.
set -u
case "${1:-}" in --help|-h) sed -n '2p' "$0"; exit 0;; esac
fail=0
need() { command -v "$1" >/dev/null 2>&1 && echo "ok   $1 $($1 --version 2>/dev/null | head -1)" || { echo "MISSING $1 — $2"; fail=1; }; }
need uv "https://docs.astral.sh/uv/"
uvv=$(uv --version 2>/dev/null | awk '{print $2}')
case "$uvv" in
  ""|0.[0-7].*) echo "FAIL uv '$uvv' < 0.8 (see [tool.uv] required-version) — run: uv self update"; fail=1;;
  *) echo "ok   uv $uvv >= 0.8";;
esac
need just "uv tool install rust-just"
want=$(cat .python-version 2>/dev/null || echo "")
# The project interpreter is the one uv resolves; bare `python3` is only the fallback.
# Never `xargs -I{} {} --version`: BSD xargs does not substitute into the utility name.
py=$(uv python find 2>/dev/null || echo "")
have=$( { [ -n "$py" ] && "$py" --version || python3 --version; } 2>/dev/null | awk '{print $2}')
mm() { printf '%s' "$1" | cut -d. -f1,2; }
if [ -n "$have" ] && [ "$(mm "$have")" = "$(mm "$want")" ]; then echo "ok   python $have"
else echo "FAIL python '$have' != .python-version $want — run: uv python install $want"; fail=1; fi
hp=$(git config core.hooksPath 2>/dev/null || echo "")
[ "$hp" = ".githooks" ] && echo "ok   core.hooksPath" || { echo "WARN core.hooksPath='$hp' — run: just sync"; }
for h in .githooks/* harness/*.sh harness/*.py; do
  [ -f "$h" ] && [ ! -x "$h" ] && { echo "FAIL $h not executable"; fail=1; }
done
exit $fail
