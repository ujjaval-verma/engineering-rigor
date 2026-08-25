#!/usr/bin/env python3
"""Usage: check-commit-msg.py <msgfile>

Enforce `type(scope)?!?: subject` (Conventional Commits). Merges, reverts and
the autosquash prefixes are exempt. Subject ≤ 72 chars.
"""

import re
import sys

TYPES = "feat|fix|refactor|docs|chore|test|perf|build"
PATTERN = re.compile(rf"^({TYPES})(\([A-Za-z0-9._/-]+\))?!?: \S.{{0,71}}$")
EXEMPT = re.compile(r"^(Merge |Revert |fixup! |squash! |amend! )")


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0 if argv[1:2] in (["-h"], ["--help"]) else 1
    with open(argv[1], encoding="utf-8") as fh:
        subject = fh.readline().rstrip("\n")
    if EXEMPT.match(subject) or PATTERN.match(subject):
        return 0
    print(
        f"commit-msg: {subject!r} is not `type(scope)?: subject` "
        f"(types: {TYPES}; subject ≤ 72 chars)",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
