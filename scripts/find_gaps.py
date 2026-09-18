#!/usr/bin/env python3
"""Where in a paper somebody said a question is open.

Open questions are the one kind of statement authors mark for you. A finding
has to be recognized; an open question is announced — "remains an open
question", "we leave to future work", "it is not yet known whether" — because
an author stating one wants it found and worked on.

So this is the opposite of the gates in `extract.py`, which reject. This
finds, and hands the passages to an extractor to read. It does not decide what
the statement is and it does not write the quote: those are the extractor's
job, and keeping them apart is what stops a regex from becoming the author of
a claim.

    python3 scripts/find_gaps.py --paper 2511.03434
    python3 scripts/find_gaps.py --corpus --limit 30
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from ao_commons_kg import fulltext  # noqa: E402
from ao_commons_kg.extract import gap_passages  # noqa: E402
from ao_commons_kg.resources import load_resources  # noqa: E402


def for_paper(arxiv_id: str) -> list:
    return gap_passages(fulltext.sections_for(arxiv_id))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--paper", help="an arXiv id")
    parser.add_argument("--corpus", action="store_true",
                        help="every arXiv record we hold full text for")
    parser.add_argument("--limit", type=int, default=25)
    args = parser.parse_args(argv)

    if not args.paper and not args.corpus:
        parser.error("give --paper or --corpus")

    if args.paper:
        papers = [args.paper]
    else:
        papers = [r.arxiv_id for r in load_resources()
                  if getattr(r, "arxiv_id", None)][: args.limit]

    total = reached = 0
    for arxiv_id in papers:
        try:
            found = for_paper(arxiv_id)
        except Exception as error:  # noqa: BLE001 — no full text is the normal case
            if args.paper:
                print(f"{arxiv_id}: no full text — {type(error).__name__}: {error}")
            continue
        reached += 1
        total += len(found)
        if not found:
            continue
        print(f"\n=== {arxiv_id} — {len(found)} passage(s)")
        for passage in found:
            print(f"\n  [{passage.section}]  marker: {passage.marker!r}")
            print(f"  …{passage.text}…")

    if args.corpus:
        rate = f"{total / reached:.1f}" if reached else "—"
        print(f"\n{reached} paper(s) with full text, {total} passage(s), {rate} per paper")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
