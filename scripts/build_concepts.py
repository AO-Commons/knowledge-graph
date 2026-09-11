#!/usr/bin/env python3
"""Write the statement vocabulary out as a file anyone can read.

The 523 terms exist only as an object built at load time: 514 parsed out of
indented bullets in the taxonomy markdown, 9 from `concepts-extra.yml`. So
the list that decides which statements can ever be linked to each other was
not readable anywhere — not on the site, not in a release, not from the MCP
server, and not in the repository except as prose inside a document about
something else.

That is a problem for the one instruction the process gives: check whether a
term already exists before adding it. Checking required a local checkout and
an installed package, which is a bar most contributors will not clear, and a
vocabulary nobody can read is one people will duplicate.

Generated, not authored. `data/concepts.json` is a build artifact in the same
sense as `site/graph.json` — committed so it is diffable and legible in a pull
request, rebuilt from the two sources rather than edited. Editing it does
nothing; the taxonomy and the extras file remain the only places a term is
actually defined.

Usage: python3 scripts/build_concepts.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from ao_commons_kg.claims import load_claims  # noqa: E402
from ao_commons_kg.concepts import (  # noqa: E402
    duplicate_pairs, load_vocabulary, usage,
)

OUTPUT = REPO / "data" / "concepts.json"


def build() -> dict:
    vocabulary = load_vocabulary()
    claims = load_claims()
    counts = usage(claims, vocabulary)

    by_concept: dict[str, list[str]] = {}
    for claim in claims:
        for tag in claim.concept_tags:
            by_concept.setdefault(tag, []).append(claim.id)

    concepts = []
    for key in sorted(vocabulary.concepts):
        concept = vocabulary.concepts[key]
        entry = {
            "id": concept.id,
            "label": concept.label,
            "topics": list(concept.topics),
            "origin": concept.origin,
            "statements": counts.get(key, 0),
        }
        if by_concept.get(key):
            entry["claims"] = sorted(by_concept[key])
        if concept.note:
            entry["note"] = concept.note
        concepts.append(entry)

    return {
        # Said in the file, because a generated artifact that does not say so
        # is one somebody will eventually hand-edit.
        "generated_by": "scripts/build_concepts.py — do not edit; "
                        "terms are defined in the taxonomy and concepts-extra.yml",
        "counts": {
            "total": len(concepts),
            "from_taxonomy": sum(1 for c in concepts if c["origin"] == "taxonomy"),
            "from_claims": sum(1 for c in concepts if c["origin"] == "claim"),
            "carrying_a_statement": sum(1 for c in concepts if c["statements"]),
            "on_exactly_one": sum(1 for c in concepts if c["statements"] == 1),
        },
        # Shipped rather than left to be rediscovered. These cannot be fixed
        # here — the taxonomy owns 514 of the terms — but a list that hides
        # its own collisions invites a reader to trust it more than it earns.
        "looks_like_one_idea": [
            {"similarity": round(score, 3), "a": left.id, "b": right.id}
            for score, left, right in duplicate_pairs(vocabulary)
        ],
        "concepts": concepts,
    }


def main() -> int:
    payload = build()
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")
    counts = payload["counts"]
    print(f"wrote {OUTPUT.relative_to(REPO)}  {OUTPUT.stat().st_size:,} bytes")
    print(f"  {counts['total']} concepts — {counts['from_taxonomy']} from the taxonomy, "
          f"{counts['from_claims']} from claims")
    print(f"  {counts['carrying_a_statement']} carry a statement, "
          f"{counts['on_exactly_one']} on exactly one")
    print(f"  {len(payload['looks_like_one_idea'])} pairs look like one idea")
    return 0


if __name__ == "__main__":
    sys.exit(main())
