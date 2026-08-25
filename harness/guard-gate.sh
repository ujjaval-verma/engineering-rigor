#!/bin/sh
# guard-gate: Claude Code PreToolUse hook for Bash. A speed bump, not security —
# .githooks/pre-push is the backstop. It matches verbs it names, so known holes are:
# variable splitting (f=just; rm ${f}file), payloads read from files, shell
# aliases, chained read-verb prefix (grep x justfile && rm justfile), and editors
# not on the list below (ed, ex, awk -i inplace, patch, git apply, rsync).
# Usage: echo '{"tool_input":{"command":"..."}}' | guard-gate.sh   (exit 0 allow, 2 block)
set -eu
case "${1:-}" in --help|-h) sed -n '2,7p' "$0"; exit 0;; esac

PROTECTED="justfile harness/ .githooks/ .claude/ .env"
# Spellings of one verb are separate entries on purpose: `sed -i` and `sed --in-place`
# are the same edit, and a list that names only the first is a list that lies.
WRITE_VERBS="sed -i|sed --in-place|perl -pi|perl -i|rm |mv |cp |ln |tee |chmod |chown |truncate |touch | of=|git restore |git checkout --|python -c|python3 -c|python - |python3 - |eval |install "

cmd=$(python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("tool_input",{}).get("command",""))
except Exception: print("")' 2>/dev/null || true)
[ -n "$cmd" ] || exit 0

# Trailing space so a verb that ends the command (`… | python3 -`) still matches.
n=$(printf '%s ' "$cmd" | tr '[:upper:]' '[:lower:]' | sed 's/\\//g; s/\$'"'"'//g')
qa=$(printf '%s' "$n" | tr -d "\"'")
qb=$(printf '%s' "$n" | sed "s/\"[^\"]*\"//g; s/'[^']*'//g")
prot_re=$(printf '%s' "$PROTECTED" | sed 's/\./\\./g' | tr ' ' '|')

block() { printf 'guard-gate: blocked (%s). Fix the code; never bypass the gate.\n' "$1" >&2; exit 2; }

# Bypass checks. Run on qb (quoted content removed) so a commit message may mention
# --no-verify; re-run on qa when the command hides a payload behind sh -c/eval.
bypass() {
  case "$1" in
    *--no-verify*) block "--no-verify";;
    *"git commit -n"*|*"git commit "*" -n"*|*"git commit "*" -n "*) block "commit -n";;
    *hookspath*) block "hooksPath";;
    *git_config_*|*"git_dir="*) block "git env override";;
    *skip-worktree*|*assume-unchanged*) block "index tricks";;
    *"push --force"*|*"push -f"*|*"push "*" --force"*|*"push "*" -f"*) block "force push";;
    *"push +"*|*"push "*" +"*) block "force push (+refspec)";;
    *"| sh"*|*"|sh"*|*"| bash"*|*"|bash"*|*"| zsh"*|*"|zsh"*) block "pipe to shell";;
  esac
  if printf '%s' "$1" | grep -Eq '(^|[^a-z0-9])pip[0-9.]* install'; then block "pip — use uv"; fi
}
bypass "$qb"
case "$qa" in *"sh -c"*|*"eval "*) bypass "$qa";; esac

# A redirect is a write only when it aims at a protected path; bare `>` is fine
# (grep foo justfile 2>/dev/null, git log -- harness/ > /tmp/out.txt).
if printf '%s' "$qa" | grep -Eq ">[>|]?[[:space:]]*[^[:space:]]*($prot_re)"; then block "redirect into protected path"; fi

# Read-only lookups (cat/grep/git diff …) carry no write verb, so they fall through to exit 0.
writes=0
old_ifs=$IFS; IFS='|'
for v in $WRITE_VERBS; do case "$qb" in *"$v"*) writes=1;; esac; done
IFS=$old_ifs
[ "$writes" -eq 1 ] || exit 0

for p in $PROTECTED; do
  case "$qa" in *"$p"*) block "write to protected path $p";; esac
done
exit 0
