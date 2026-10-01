#!/usr/bin/env python3
"""Run the drafting checks over the statements the library already holds.

The checks in `extract.py` run when a model drafts statements from a paper.
Statements drafted before a check existed were never put through it, so this
puts them through now. It reports and changes nothing: every warning is a
question for a person, and the answer can be "this one is right".

    python3 scripts/check_statements.py               # every paper with statements
    python3 scripts/check_statements.py arxiv:2107.06857

Full text is read from the cache where there is one. A paper without a cached
body gets every check except the one that needs the body.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from ao_commons_kg.claims import load_claims  # noqa: E402
from ao_commons_kg.extract import check  # noqa: E402
from ao_commons_kg.fulltext import CACHE, parse  # noqa: E402


def sections_for(resource_id: str):
    arxiv = resource_id.split("arxiv:", 1)[1] if "arxiv:" in resource_id else None
    path = CACHE / f"{arxiv}.html" if arxiv else None
    if path and path.exists():
        return parse(path.read_text(encoding="utf-8"))
    return None


def main(argv=None) -> int:
    wanted = set(argv if argv is not None else sys.argv[1:])
    by_paper = defaultdict(list)
    for claim in load_claims():
        by_paper[claim.resource_id].append(claim)

    total = 0
    for resource_id in sorted(by_paper):
        if wanted and not any(w in resource_id for w in wanted):
            continue
        candidates = [{
            "text": c.text, "quote": c.quote, "claim_type": c.claim_type.value,
            "concept_tags": list(c.concept_tags),
        } for c in by_paper[resource_id]]
        sections = sections_for(resource_id)
        warnings = check(candidates, sections=sections).warnings
        found = sum(len(v) for v in warnings.values())
        total += found
        body = "" if sections else "  (no cached body: section coverage not checked)"
        print(f"\n{resource_id} — {len(candidates)} statements, {found} to look at{body}")
        for name, items in warnings.items():
            print(f"  {name}:")
            for item in items:
                print(f"    - {item}")
    print(f"\n{total} things for a person to look at.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
