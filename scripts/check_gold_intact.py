#!/usr/bin/env python3
"""Nothing leaves the gold set by accident.

A verdict is the most expensive thing in this library: somebody read a paper
and decided. Eight of them were deleted by a rebase that replaced the file
wholesale from a branch predating another reviewer's merge, and nothing
noticed — the tests passed, the fingerprints matched, the site built. A gold
set missing eight entries is a perfectly valid gold set.

So this compares the file against a base commit and fails if any claim id
that was there is gone. Removing one deliberately is still possible; it just
has to be deliberate, which is the whole point.

    python3 scripts/check_gold_intact.py --base origin/main
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
GOLD = ("evals/gold/claims.yml", "evals/gold/tags.yml")


def entries(text: str) -> dict:
    payload = yaml.safe_load(text) or {}
    return payload.get("claims") or payload.get("records") or {}


def at(ref: str, path: str) -> dict:
    shown = subprocess.run(["git", "show", f"{ref}:{path}"],
                           capture_output=True, text=True, cwd=REPO)
    if shown.returncode != 0:
        return {}
    return entries(shown.stdout)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="origin/main",
                        help="the ref to compare against")
    args = parser.parse_args(argv)

    gone = []
    for path in GOLD:
        before = at(args.base, path)
        here = entries((REPO / path).read_text(encoding="utf-8")) if (REPO / path).exists() else {}
        for key, entry in before.items():
            if key not in here:
                who = (entry or {}).get("reviewer", "somebody")
                gone.append(f"{path}: {key} — judged by {who}")

    if gone:
        print("Judgements that were in the gold set and are not here any more:\n", file=sys.stderr)
        for line in gone:
            print(f"  {line}", file=sys.stderr)
        print("\nSomebody read a paper to produce each of these. If the removal is "
              "deliberate, say so in the commit message and re-run with the base it "
              "should be measured against.", file=sys.stderr)
        return 1

    print(f"gold set intact against {args.base}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
