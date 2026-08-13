#!/usr/bin/env python3
"""Bake the review site into a single self-contained HTML file.

Data is inlined rather than fetched. The site then works from a file:// URL,
from GitHub Pages, and from anywhere else it is dropped — no server, no CORS,
no build step for a contributor who just wants to help tag papers.

Topic suggestions are precomputed here rather than scored in the browser.
The classifier is already written and tested in Python; reimplementing BM25
in JavaScript would be a second thing to keep correct, and the two would
drift.

Usage:  python3 scripts/build_site.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from ao_commons_kg.classify import TopicIndex, classify_resource  # noqa: E402
from ao_commons_kg.resources import load_resources  # noqa: E402
from ao_commons_kg.taxonomy import load_taxonomy  # noqa: E402

TEMPLATE = REPO / "site" / "template.html"
GOLD = REPO / "evals" / "gold" / "tags.yml"
GOLD_OUT = REPO / "site" / "gold.json"
OUTPUT = REPO / "site" / "index.html"
TAXONOMY = REPO / "taxonomy" / "agentic-org-research-library-taxonomy-v3.md"
ALIASES = REPO / "taxonomy" / "aliases.yaml"

ABSTRACT_LIMIT = 1100
SUGGESTIONS = 14


def build_payload() -> dict:
    topics = load_taxonomy(TAXONOMY)
    aliases = yaml.safe_load(ALIASES.read_text(encoding="utf-8")) if ALIASES.exists() else {}
    index = TopicIndex(topics, aliases or {})
    resources = load_resources()

    records = []
    for resource in sorted(resources, key=lambda r: (not r.abstract, r.id)):
        abstract = resource.abstract or resource.description or ""
        if len(abstract) > ABSTRACT_LIMIT:
            abstract = abstract[:ABSTRACT_LIMIT].rsplit(" ", 1)[0] + "…"
        suggestions = classify_resource(
            index, resource, limit=SUGGESTIONS, min_score=0.5
        )
        records.append({
            "id": resource.id,
            "title": resource.title,
            "abstract": abstract,
            "authors": (resource.authors or [])[:5],
            "date": str(resource.published_at or ""),
            "url": resource.url or "",
            "type": resource.resource_type,
            # Carried so the Add form can tell a genuinely new paper from one
            # the library already holds, without a network call.
            "doi": (resource.doi or "").lower(),
            "arxiv": (resource.arxiv_id or "").lower(),
            "repo": resource.repository_url or "",
            "current": resource.taxonomy_topics or [],
            "suggested": [a.code for a in suggestions],
        })

    return {
        "generated_for": "AO Commons knowledge graph",
        "taxonomy_version": "v3",
        "topics": [
            {
                "code": t.code,
                "title": t.title,
                "parent": t.parent_code,
                "section": t.top_level_section,
                "depth": t.depth,
                "coding": t.usage_mode.value == "coding_scheme",
                "points": t.subpoints[:4],
            }
            for t in topics
        ],
        "records": records,
    }


def main() -> int:
    payload = build_payload()
    template = TEMPLATE.read_text(encoding="utf-8")
    if "__GRAPH_DATA__" not in template:
        print("template is missing the __GRAPH_DATA__ placeholder", file=sys.stderr)
        return 1

    # `</script>` inside the JSON would close the tag early and break the page.
    blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace(
        "</", "<\\/"
    )
    OUTPUT.write_text(template.replace("__GRAPH_DATA__", blob), encoding="utf-8")

    # The merged ledger, published beside the page. The site fetches it
    # same-origin so every contributor sees what has already been accepted,
    # which is the closest a page with no backend gets to shared state.
    merged = {}
    if GOLD.exists():
        merged = (yaml.safe_load(GOLD.read_text(encoding="utf-8")) or {}).get("records") or {}
    GOLD_OUT.write_text(
        json.dumps({"records": merged}, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {GOLD_OUT.relative_to(REPO)}  {len(merged)} merged filing(s)")

    size = OUTPUT.stat().st_size
    print(f"wrote {OUTPUT.relative_to(REPO)}  {size:,} bytes")
    print(f"  {len(payload['topics'])} topics, {len(payload['records'])} records")
    with_abstract = sum(1 for r in payload["records"] if r["abstract"])
    print(f"  {with_abstract} records have text to judge from")
    return 0


if __name__ == "__main__":
    sys.exit(main())
