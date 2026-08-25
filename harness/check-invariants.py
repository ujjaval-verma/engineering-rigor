#!/usr/bin/env python3
"""Usage: check-invariants.py --claude CLAUDE.md --root DIR

Every row of the invariants table (header contains "enforced by") must name an
enforcement site: `prose`, or backticked paths that exist under DIR.
"""

import argparse
import re
import sys
from pathlib import Path

PATH = re.compile(r"`([^`]+)`")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--claude", required=True, type=Path)
    ap.add_argument("--root", required=True, type=Path)
    a = ap.parse_args()
    errors: list[str] = []
    in_table = False
    for line in a.claude.read_text(encoding="utf-8").splitlines():
        if line.startswith("|") and "enforced by" in line.lower():
            in_table = True
            continue
        if not line.startswith("|"):
            in_table = False
            continue
        if not in_table or set(line.replace("|", "").strip()) <= {"-", " "}:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        site = cells[-1]
        if site == "prose":
            continue
        paths = PATH.findall(site)
        if not paths:
            errors.append(f"row {cells[0]}: enforcement site must be `prose` or backticked path(s)")
        errors.extend(
            f"row {cells[0]}: {p} does not exist" for p in paths if not (a.root / p).exists()
        )
    if not errors:
        return 0
    print("invariants:\n  " + "\n  ".join(errors))
    return 1


if __name__ == "__main__":
    sys.exit(main())
