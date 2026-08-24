#!/usr/bin/env python3
"""Write the graph the visualisation reads.

Every edge the release carries, flattened into the shape 3d-force-graph wants:
`{nodes: [{id, ...}], links: [{source, target, ...}]}`. Written beside the page
rather than inlined, because it is fetched once by a page nobody opens on a
phone, and inlining a second copy of the corpus into index.html would slow the
filing site down for everyone who never looks at the graph.

Kept honest about what each edge *is*. A citation and a bibliographic-coupling
score and a machine-extracted claim are three different kinds of assertion, and
a picture that draws them identically invites the viewer to read a resemblance
as a fact. They are separately coloured and separately switchable.

Usage:  python3 scripts/build_graph.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from ao_commons_kg.claims import claim_edges, load_claims  # noqa: E402
from ao_commons_kg.graph import similarity_edges  # noqa: E402
from ao_commons_kg.models import RelationType  # noqa: E402
from ao_commons_kg.resources import load_resources, tagged_edges  # noqa: E402
from ao_commons_kg.scholarly.keys import keys_for_corpus  # noqa: E402
from ao_commons_kg.scholarly.store import ReferenceStore  # noqa: E402
from ao_commons_kg.taxonomy import load_taxonomy  # noqa: E402

TAXONOMY = REPO / "taxonomy" / "agentic-org-research-library-taxonomy-v3.md"
REFERENCES = REPO / "data" / "scholarly" / "references.jsonl"
OUTPUT = REPO / "site" / "graph.json"


def build() -> dict:
    topics = load_taxonomy(TAXONOMY)
    codes = {t.code for t in topics}
    resources = load_resources()
    claims = load_claims()

    claims_by_resource: dict[str, int] = {}
    for claim in claims:
        claims_by_resource[claim.resource_id] = claims_by_resource.get(claim.resource_id, 0) + 1

    # Which topics actually hold something. The default view hides the rest:
    # most subsections hold nothing yet, and drawn together they bury the
    # records the graph exists to show.
    filed: dict[str, int] = {}
    for resource in resources:
        for code in resource.taxonomy_topics or []:
            if code in codes:
                filed[code] = filed.get(code, 0) + 1

    nodes = [
        {
            "id": f"topic:{t.code}",
            "kind": "section" if t.depth == 0 else "topic",
            "label": f"{t.code} {t.title}",
            "code": t.code,
            "section": t.top_level_section,
            "depth": t.depth,
            "held": filed.get(t.code, 0),
        }
        for t in topics
    ]
    nodes += [
        {
            "id": r.id,
            "kind": "resource",
            "label": r.title,
            "section": (r.taxonomy_topics or [""])[0].split(".")[0],
            "type": r.resource_type,
            "url": r.url or "",
            "authors": (r.authors or [])[:3],
            "date": str(r.published_at or ""),
            "claims": claims_by_resource.get(r.id, 0),
            "reviewed": r.review_status.value,
        }
        for r in resources
    ]
    # People. 251 of them across 297 bylines, but only 25 appear on more than
    # one paper — the rest hang off a single record and add no structure. Both
    # are shipped and the page decides; `wrote` says how many, so it can.
    by_author: dict[str, list] = {}
    for resource in resources:
        for name in resource.authors or []:
            by_author.setdefault(name, []).append(resource)

    def dominant_section(written: list) -> str:
        """Which part of the field this person mostly works in.

        Their colour, so a co-authorship cluster shows the areas it spans. Ties
        break on the lowest section number rather than on dict order, because a
        person's colour changing between builds would be a diff nobody could
        explain.
        """
        tally: dict[str, int] = {}
        for resource in written:
            for code in resource.taxonomy_topics or []:
                section = code.split(".")[0]
                tally[section] = tally.get(section, 0) + 1
        if not tally:
            return ""
        return min(sorted(tally), key=lambda section: (-tally[section], int(section)))

    nodes += [
        {
            "id": f"person:{name}",
            "kind": "author",
            "label": name,
            "section": dominant_section(written),
            "wrote": len(written),
        }
        for name, written in sorted(by_author.items())
    ]
    nodes += [
        {
            "id": c.id,
            "kind": "claim",
            "label": c.text,
            "type": c.claim_type.value,
            "of": c.resource_id,
            "reviewed": c.review_status.value,
        }
        for c in claims
    ]

    edges = [
        {"source": f"topic:{t.parent_code}", "target": f"topic:{t.code}", "kind": "parent"}
        for t in topics
        if t.parent_code
    ]
    edges += [
        {"source": e.source_id, "target": e.target_id, "kind": "tagged"}
        for e in tagged_edges(resources, codes)
    ]

    edges += [
        {"source": f"person:{name}", "target": resource.id, "kind": "wrote"}
        for name, written in sorted(by_author.items())
        for resource in written
    ]

    store = ReferenceStore.load(REFERENCES)
    held = {r.id for r in resources}
    edges += [
        {"source": source, "target": target, "kind": "cites"}
        for source, target in store.citation_pairs(keys_for_corpus(resources))
    ]
    references = {k: v for k, v in store.references().items() if k in held}
    edges += [
        {"source": e.source_id, "target": e.target_id, "kind": "similar",
         "score": round(e.score or 0, 3)}
        for e in similarity_edges(references, min_shared=2)
    ]
    edges += [
        {"source": e.source_id, "target": e.target_id,
         "kind": "claim" if e.relation is RelationType.MAKES_CLAIM else "about"}
        for e in claim_edges(claims, topic_codes=codes)
    ]

    # An edge to a node that is not in the graph makes the layout throw rather
    # than draw. Cheaper to notice here than in a console nobody has open.
    known = {n["id"] for n in nodes}
    dangling = [e for e in edges if e["source"] not in known or e["target"] not in known]
    if dangling:
        raise SystemExit(f"{len(dangling)} edge(s) point at nodes not in the graph: "
                         f"{dangling[:3]}")

    return {
        "nodes": sorted(nodes, key=lambda n: n["id"]),
        "links": sorted(edges, key=lambda e: (e["kind"], e["source"], e["target"])),
    }


def main() -> int:
    graph = build()
    OUTPUT.write_text(json.dumps(graph, ensure_ascii=False, separators=(",", ":")) + "\n",
                      encoding="utf-8")

    kinds: dict[str, int] = {}
    for node in graph["nodes"]:
        kinds[node["kind"]] = kinds.get(node["kind"], 0) + 1
    links: dict[str, int] = {}
    for link in graph["links"]:
        links[link["kind"]] = links.get(link["kind"], 0) + 1

    print(f"wrote {OUTPUT.relative_to(REPO)}  {OUTPUT.stat().st_size:,} bytes")
    print(f"  nodes: {kinds}")
    print(f"  links: {links}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
