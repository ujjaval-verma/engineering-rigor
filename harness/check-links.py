#!/usr/bin/env python3
"""Usage: check-links.py [repo-root]

Every relative markdown link in tracked *.md files must resolve to a tracked
path, matched case-sensitively so a link that only works on a case-insensitive
filesystem still fails here. Fenced code blocks, anchors, absolute paths and
external schemes are skipped. Outside a git repo, the filesystem is used.
"""

import posixpath
import re
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import unquote

INLINE = re.compile(r"\[[^\]]*\]\(\s*([^)\s]+)(?:\s+[\"'][^\"']*[\"'])?\s*\)")
# Reference definition. `[^1]: …` is a GFM footnote, not a link; and a target
# without a `/` or `.` is prose, not a path.
REFDEF = re.compile(r"^ {0,3}\[[^\]^][^\]]*\]:\s*(\S*[/.]\S*)\s*(?:[\"'(].*)?$")
FENCE = re.compile(r"^\s*(```|~~~)")
SKIP = ("/", "#", "<", "http", "mailto:", "tel:", "data:", "?")


def targets(text: str) -> Iterator[str]:
    """Link targets outside fenced code blocks, inline and reference-style."""
    fenced = False
    for line in text.splitlines():
        if FENCE.match(line):
            fenced = not fenced
        elif not fenced:
            ref = REFDEF.match(line)
            if ref:
                yield ref.group(1)
            yield from INLINE.findall(line)


def ls_files(root: Path) -> list[str] | None:
    r = subprocess.run(
        ["git", "-C", str(root), "ls-files"], capture_output=True, text=True, check=False
    )
    return None if r.returncode != 0 else [line for line in r.stdout.splitlines() if line]


def main(argv: list[str]) -> int:
    if argv[1:2] in (["-h"], ["--help"]):
        print(__doc__)
        return 0
    root = Path(argv[1] if len(argv) > 1 else ".").resolve()
    known = ls_files(root)
    mds = (
        sorted(p.relative_to(root).as_posix() for p in root.rglob("*.md"))
        if known is None
        else [p for p in known if p.endswith(".md")]
    )
    tracked = set(known or ())
    dirs: set[str] = set()
    for path in tracked:  # a link may point at a directory, at any depth
        while "/" in path:
            path = posixpath.dirname(path)
            dirs.add(path)
    broken: list[str] = []
    for md in mds:
        try:
            text = (root / md).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for raw in targets(text):
            bare = unquote(raw.split("#", 1)[0]).strip()
            if not bare or bare.startswith(SKIP) or "://" in bare:
                continue
            rel = posixpath.normpath(posixpath.join(posixpath.dirname(md), bare))
            found = (root / rel).exists() if known is None else rel in tracked or rel in dirs
            if not found:
                broken.append(f"{md}: {raw}")
    if not broken:
        return 0
    print("links: broken relative links:\n  " + "\n  ".join(broken))
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
