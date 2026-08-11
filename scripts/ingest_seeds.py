#!/usr/bin/env python3
"""Expand a seed manifest into Resource records.

The manifest is the curated input — hand-picked, hand-tagged, and reviewable
as one file. This turns it into one Resource per entry in data/resources/,
which is what the graph builds from.

Idempotent and safe to re-run: a record already present is left alone, so a
correction made to a resource file survives.

Usage:  python3 scripts/ingest_seeds.py [--manifest data/seeds/seed-corpus-v1.yml]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from ao_commons_kg.models import Resource  # noqa: E402
from ao_commons_kg.resources import load_resources  # noqa: E402
from ao_commons_kg.taxonomy import load_taxonomy  # noqa: E402

DEFAULT_MANIFEST = REPO / "data" / "seeds" / "seed-corpus-v1.yml"
OUT = REPO / "data" / "resources"

PROVENANCE = (
    "seed corpus v1, curated by hand and resolved against OpenAlex. "
    "Taxonomy tags are a first pass from title, abstract, and venue — not "
    "classification-pipeline output, and not reviewed."
)

# Papers get the same facet baseline: a preprint reporting a single study is
# the modal case here, and anything more specific is a judgement the record
# should not make on its own.
PAPER_FACETS = {
    "artifact_type": "preprint",
    "evidence_strength": "empirical-single-study",
    "source_independence": "independent-academic",
    "temporal_relevance": "current",
    "applicability": "background",
}
PLATFORM_FACETS = {
    "artifact_type": "code-tool",
    "evidence_strength": "structured-case-study",
    "source_independence": "independent-practitioner",
    "maturity_of_subject": "limited-deployment",
    "temporal_relevance": "current",
    "applicability": "directly-actionable",
}


def paper_record(entry: dict) -> dict:
    arxiv = str(entry["arxiv"])
    record = {
        "id": f"resource:arxiv:{arxiv}",
        "resource_type": "preprint",
        "title": entry["title"],
        "authors": entry.get("authors", []),
        "published_at": str(entry["date"]),
        "url": f"https://arxiv.org/abs/{arxiv}",
        "arxiv_id": arxiv,
        "doi": f"10.48550/arXiv.{arxiv}",
        "taxonomy_topics": entry.get("topics", []),
        "facets": dict(PAPER_FACETS),
        "is_borrowed_background": bool(entry.get("borrowed")),
        "source_provenance": PROVENANCE,
        "ingested_at": "2026-08-11",
    }
    if openalex := entry.get("openalex"):
        record["openalex_id"] = openalex
    if note := entry.get("note"):
        record["description"] = note.strip()
    return record


def platform_record(entry: dict) -> dict:
    return {
        "id": f"resource:platform:{entry['id']}",
        "resource_type": entry.get("type", "code-tool"),
        "title": entry["title"],
        "description": (entry.get("note") or "").strip() or None,
        "url": entry["url"],
        "taxonomy_topics": entry.get("topics", []),
        "facets": dict(PLATFORM_FACETS),
        "source_provenance": PROVENANCE,
        "ingested_at": "2026-08-11",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    manifest = yaml.safe_load(Path(args.manifest).read_text(encoding="utf-8"))
    topic_codes = {t.code for t in load_taxonomy(REPO / "taxonomy" /
                                                 "agentic-org-research-library-taxonomy-v3.md")}
    existing = {r.id for r in load_resources(OUT)}

    OUT.mkdir(parents=True, exist_ok=True)
    written = skipped = 0
    bad_tags: dict[str, list[str]] = {}

    entries = [paper_record(e) for e in manifest.get("papers", [])]
    entries += [platform_record(e) for e in manifest.get("platforms", [])]

    for payload in entries:
        payload = {k: v for k, v in payload.items() if v not in (None, [], {}, "", False)}

        if unknown := [c for c in payload.get("taxonomy_topics", []) if c not in topic_codes]:
            bad_tags[payload["id"]] = unknown

        # Construct it before writing: a record the model rejects should fail
        # here, not at release time.
        Resource(**payload)

        path = OUT / (payload["id"].removeprefix("resource:").replace(":", "-") + ".yml")
        if payload["id"] in existing:
            skipped += 1
            continue
        if not args.dry_run:
            path.write_text(
                yaml.safe_dump(payload, sort_keys=False, allow_unicode=True, width=88),
                encoding="utf-8",
            )
        written += 1

    if bad_tags:
        print("tags not in the taxonomy:", file=sys.stderr)
        for resource_id, codes in sorted(bad_tags.items()):
            print(f"  {resource_id}: {codes}", file=sys.stderr)
        return 1

    if unresolved := manifest.get("unresolved", []):
        print(f"{len(unresolved)} item(s) named but not resolved to a record:")
        for item in unresolved:
            print(f"  - {item['title']}")

    print(f"\n{written} written, {skipped} already present.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
