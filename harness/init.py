#!/usr/bin/env python3
"""Usage: init.py [--root DIR] NAME

One-time rename of the `example_app` placeholder to NAME (snake_case) across every
tracked file (`git ls-files`) — pyproject, src/, tests/, docs. Refuses to run twice.
Skips itself, `uv.lock`, and gitignored scratch trees.
"""

import argparse
import keyword
import re
import subprocess
import sys
from pathlib import Path

PLACEHOLDER = "example_app"
# Never rewrite: this script (it *defines* the placeholder), the lock (relocked by
# `just init`), or scratch trees that are not template deliverables.
SKIP_FILES = {"harness/init.py", "uv.lock"}
SKIP_PREFIXES = ("docs/superpowers/", ".superpowers/")
# A package named for a keyword can never be imported; one named for a top-level
# directory collides with it (`src/src/`). Both pass a bare snake_case regex.
RESERVED = {"src", "tests", "harness", "docs", PLACEHOLDER}


def tracked(root: Path) -> list[str]:
    r = subprocess.run(
        ["git", "-C", str(root), "ls-files"], capture_output=True, text=True, check=False
    )
    if r.returncode != 0:
        print(f"init: not a git repository: {root}", file=sys.stderr)
        raise SystemExit(1)
    return [line for line in r.stdout.splitlines() if line]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=Path("."))
    ap.add_argument("name")
    a = ap.parse_args()
    if not re.fullmatch(r"[a-z][a-z0-9_]*", a.name):
        print("init: NAME must be snake_case ([a-z][a-z0-9_]*)", file=sys.stderr)
        return 1
    if keyword.iskeyword(a.name):
        print(f"init: NAME must not be a Python keyword: {a.name}", file=sys.stderr)
        return 1
    if a.name in RESERVED:
        print(f"init: NAME must not be a reserved directory name: {a.name}", file=sys.stderr)
        return 1
    src = a.root / "src" / PLACEHOLDER
    if not src.is_dir():
        print(f"init: {src} not found — already renamed?", file=sys.stderr)
        return 1
    dest = a.root / "src" / a.name
    if dest.exists():
        print(f"init: {dest} already exists — pick another NAME", file=sys.stderr)
        return 1
    for rel in tracked(a.root):
        if rel in SKIP_FILES or rel.startswith(SKIP_PREFIXES):
            continue
        f = a.root / rel
        try:
            text = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if PLACEHOLDER in text:
            f.write_text(text.replace(PLACEHOLDER, a.name), encoding="utf-8")
    src.rename(dest)
    print(f"init: renamed {PLACEHOLDER} -> {a.name}. Next: uv lock && just sync && just check")
    return 0


if __name__ == "__main__":
    sys.exit(main())
