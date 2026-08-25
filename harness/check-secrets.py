#!/usr/bin/env python3
"""Usage: check-secrets.py [repo-root]

Scan tracked text files for credential-shaped strings. Vendor prefixes match
outright; a named key/token assignment (quoted or bare) must also look like a
real value: mixed classes, no placeholder wording, no URL. Lock files are
skipped. Escape a match with `# rigor: ignore-secret` on the same line, or a path
with an fnmatch glob in a root `.secret-scan-ignore` (`#` comments allowed).
"""

import fnmatch
import re
import subprocess
import sys
from pathlib import Path

VENDOR = re.compile(
    r"sk-ant-[A-Za-z0-9_-]{20,}|sk-proj-[A-Za-z0-9_-]{20,}|(?<![A-Za-z0-9-])sk-[A-Za-z0-9]{20,}"
    r"|github_pat_[A-Za-z0-9_]{20,}|gh[oprsu]_[A-Za-z0-9]{20,}"
    r"|xox[abp]-[A-Za-z0-9-]{10,}|AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{35}"
    r"|[sr]k_live_[A-Za-z0-9]{10,}|eyJ[A-Za-z0-9_-]{10,}\.eyJ|-----BEGIN [A-Z ]*PRIVATE KEY-----"
)
# Quoted assignment, incl. JSON/YAML (the name's quote precedes the colon).
GENERIC = re.compile(
    r"(?i)(api[_-]?key|secret|token|password|passwd)(?P<tail>[A-Za-z0-9_-]*)['\"]?\s*[:=]\s*"
    r"['\"](?P<val>[A-Za-z0-9_\-/+.=]{20,})['\"]"
)
UNQUOTED = re.compile(
    r"^\s*[A-Za-z_]*(KEY|SECRET|TOKEN|PASSWORD|PASSWD)(?P<tail>[A-Za-z0-9_]*)"
    r"\s*[=:]\s*(?P<val>\S{20,})\s*$"
)
# `API_KEY_PROD` holds a credential; `API_KEY_HEADER` (and friends) does not.
DENY_TAIL = re.compile(
    r"(?i)^[_-](URL|URI|ENDPOINT|HEADER|NAME|FILE|PATH|ID|TTL|EXPIRY|LENGTH|FIELD|PREFIX)"
    r"([^A-Za-z0-9]|$)"
)
PLACEHOLDER = re.compile(
    r"(?i)(^|[^a-z])(replace|change_?me|example|your|dummy|placeholder"
    r"|xxxx|sample|test|insecure)(s|ing|d)?([^a-z]|$)"
)
ESCAPE = "rigor: ignore-secret"
IGNORE_FILE = ".secret-scan-ignore"


def credential_shaped(value: str) -> bool:
    """Reject prose and placeholders: real keys mix digits, letters and symbols."""
    if PLACEHOLDER.search(value) or "://" in value:
        return False
    mixed = sum(c.isdigit() for c in value) >= 2 and sum(c.isalpha() for c in value) >= 2
    return mixed and (any(not c.isalnum() for c in value) or len(value) >= 32)


def ignored(root: Path) -> list[str]:
    """Globs from the optional root .secret-scan-ignore, for comment-less formats."""
    path = root / IGNORE_FILE
    lines = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
    return [s for ln in lines if (s := ln.strip()) and not s.startswith("#")]


def tracked(root: Path) -> list[str]:
    cmd = ["git", "-C", str(root), "ls-files"]
    r = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if r.returncode != 0:
        raise SystemExit(f"secrets: not a git repository: {root}")
    return [line for line in r.stdout.splitlines() if line]


def offending(line: str) -> bool:
    if ESCAPE in line:
        return False
    named = [m for pattern in (GENERIC, UNQUOTED) for m in pattern.finditer(line)]
    return bool(VENDOR.search(line)) or any(
        not DENY_TAIL.match(m.group("tail")) and credential_shaped(m.group("val").strip("'\""))
        for m in named
    )


def main(argv: list[str]) -> int:
    if argv[1:2] in (["-h"], ["--help"]):
        print(__doc__)
        return 0
    root = Path(argv[1] if len(argv) > 1 else ".").resolve()
    skip = ignored(root)
    hits: list[str] = []
    for rel in tracked(root):
        if rel.endswith(".lock") or any(fnmatch.fnmatch(rel, g) for g in skip):
            continue
        try:
            text = (root / rel).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        hits += [f"{rel}:{n}" for n, line in enumerate(text.splitlines(), 1) if offending(line)]
    if hits:
        print(f"secrets: credential-shaped strings found (escape: `# {ESCAPE}` or {IGNORE_FILE}):")
        print("  " + "\n  ".join(hits))
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
