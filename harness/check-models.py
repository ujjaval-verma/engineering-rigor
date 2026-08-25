#!/usr/bin/env python3
"""Usage: check-models.py --src DIR --agents AGENTS.md

Every model-id literal under DIR must be an `allowed` row in the AGENTS.md model
table. Rows need a `YYYY-MM-DD` verified date and a confidence of low|medium|high.
Any literal matching a `banned` row fails. Scans .py .yaml .yml .toml .json.

The match is deliberately broad — any digit-bearing `claude-...` token is worth a
look. A line carrying `# rigor: ignore-model` is skipped, for the tokens that
are not model ids (`claude-2024-report`, a bucket name, a URL slug with a year).
"""

import argparse
import re
import sys
from pathlib import Path

ROW = re.compile(
    r"^\|\s*`(claude-[a-z0-9.-]+)`\s*\|\s*(allowed|banned)\s*"
    r"\|[^|]*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|"
)
# A model id is `claude-` plus dash-joined segments, at least one carrying a digit:
# `claude-opus-5`, `claude-3-5-sonnet-20241022`, `claude-2.1`. The lookahead is what
# demands that digit, so a product name like `claude-code` in a docs URL is not read
# as an unknown model; the trailing `[0-9a-z]` drops sentence punctuation, so prose
# saying "we default to claude-opus-5." matches the allowed id and not `claude-opus-5.`.
# The lookbehind stops `xclaude-opus-5` from matching the allowed id as a substring.
LITERAL = re.compile(r"(?<![a-z0-9-])claude-(?=[0-9a-z.-]*[0-9])[0-9a-z.-]*[0-9a-z]")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ESCAPE = "# rigor: ignore-model"
GLOBS = ("*.py", "*.yaml", "*.yml", "*.toml", "*.json")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src", required=True, type=Path)
    ap.add_argument("--agents", required=True, type=Path)
    a = ap.parse_args()
    if not a.agents.is_file():
        print(f"models: no model table at {a.agents}", file=sys.stderr)
        return 2
    policy: dict[str, str] = {}
    errors: list[str] = []
    for line in a.agents.read_text(encoding="utf-8").splitlines():
        m = ROW.match(line)
        if not m:
            continue
        model, pol, date, conf = m.groups()
        if not DATE.match(date) or conf not in ("low", "medium", "high"):
            errors.append(
                f"AGENTS.md row for {model}: needs verified YYYY-MM-DD "
                f"and confidence low|medium|high"
            )
        policy[model] = pol
    for f in sorted({p for g in GLOBS for p in a.src.rglob(g)}):
        for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if ESCAPE in line:  # an opt-out the author had to type, on the line it excuses
                continue
            for lit in LITERAL.findall(line):
                if policy.get(lit) != "allowed":
                    status = policy.get(lit, "not in AGENTS.md model table")
                    errors.append(f"{f}:{n}: {lit} is {status}")
    if not errors:
        return 0
    print("models:\n  " + "\n  ".join(errors))
    print(f"  not a model id? end the line with `{ESCAPE}`")
    return 1


if __name__ == "__main__":
    sys.exit(main())
