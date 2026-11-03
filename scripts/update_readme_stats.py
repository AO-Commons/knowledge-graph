#!/usr/bin/env python3
"""Rewrite the figures table in README.md from the corpus.

    python3 scripts/update_readme_stats.py           # rewrite if stale
    python3 scripts/update_readme_stats.py --check   # exit 1 if stale

The table sits between two HTML comments, and only that span is touched. The
counts come from `build_site.payload()`, so the README and the preview site
cannot disagree about how many records there are.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "src"))

import build_site  # noqa: E402
from ao_commons_kg.taxonomy import load_taxonomy  # noqa: E402

README = REPO / "README.md"
START, END = "<!-- stats:start -->", "<!-- stats:end -->"
SPAN = re.compile(re.escape(START) + r".*?" + re.escape(END), re.S)


def table(counts: dict, sections: int) -> str:
    c = counts
    return "\n".join([
        START,
        "| | |",
        "|---|---|",
        f"| Records | {c['records']} papers, tools, deployments, benchmarks, and reports |",
        f"| Papers with claims | {c['read']} |",
        f"| Claims | {c['claims']}, of which {c['reviewed']} have been checked by a person against the paper |",
        f"| Open questions | {c['questions']}, grouped from questions the papers say are unanswered |",
        f"| Topics | {c['topics']}, in {sections} sections |",
        END,
    ])


def rewrite(text: str, counts: dict, sections: int) -> str:
    if not SPAN.search(text):
        raise SystemExit(f"README.md has no {START} … {END} span to rewrite")
    return SPAN.sub(lambda _: table(counts, sections), text, count=1)


def main() -> int:
    counts = build_site.payload()["counts"]
    sections = len({t.top_level_section for t in load_taxonomy(build_site.TAXONOMY)})
    old = README.read_text(encoding="utf-8")
    new = rewrite(old, counts, sections)
    if new == old:
        print("README figures are current")
        return 0
    if "--check" in sys.argv:
        print("README figures are stale; run scripts/update_readme_stats.py")
        return 1
    README.write_text(new, encoding="utf-8")
    print("README figures updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
