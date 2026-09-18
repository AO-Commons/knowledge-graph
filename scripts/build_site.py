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

import hashlib
import json
import sys
from datetime import date
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
REFERENCES = REPO / "data" / "scholarly" / "references.jsonl"
sys.path.insert(0, str(REPO / "src"))

from ao_commons_kg.claims import (  # noqa: E402
    load_claim_relations, load_claims,
)
from ao_commons_kg.concepts import (  # noqa: E402
    derived_topics, load_vocabulary,
)
from ao_commons_kg.classify import (  # noqa: E402
    _SUFFIXES,
    STOP,
    TopicIndex,
    classify_resource,
)
from ao_commons_kg.resources import load_resources  # noqa: E402
from ao_commons_kg.scholarly.keys import keys_for_corpus  # noqa: E402
from ao_commons_kg.scholarly.store import ReferenceStore  # noqa: E402
from ao_commons_kg.taxonomy import load_taxonomy  # noqa: E402

TEMPLATE = REPO / "site" / "template.html"
GOLD = REPO / "evals" / "gold" / "tags.yml"
GOLD_OUT = REPO / "site" / "gold.json"
INDEX_OUT = REPO / "site" / "classifier.json"
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

    # Claims travel with the record that makes them. A reviewer already has
    # the paper in their head by the time they reach these, which is the whole
    # argument for asking both questions in one sitting — the expensive part is
    # the reading, and it should be paid once.
    by_resource: dict[str, list] = {}
    for claim in load_claims():
        by_resource.setdefault(claim.resource_id, []).append({
            "id": claim.id,
            "status": claim.review_status.value,
            # What this statement said when the page was built. The filing
            # echoes it back, so a verdict can be tied to the wording it was
            # given rather than to an id that outlives it.
            "saw": claim.fingerprint,
            "text": claim.text,
            "standalone": claim.standalone or "",
            "quote": claim.quote,
            # Which section it was read from. A claim from a results section
            # is not on the reviewer's screen the way an abstract one is, so
            # they need to be told where to look.
            "where": claim.extracted_from,
            "type": claim.claim_type.value,
            # From the model, not re-derived in the page. Which types are
            # primary is a judgment about what the library is for, and it
            # should have one home.
            "primary": claim.claim_type.is_primary,
            "topics": claim.topic_codes,
            # A verdict already merged is shown rather than asked for again.
            "verdict": claim.verdict or "",
            "by": claim.reviewed_by or "",
            # What the claim argues about, as opposed to what it is filed
            # under. The reviewer's route to the other papers saying
            # something about the same thing.
            "concepts": claim.concept_tags,
            # Whose claim it is. For a borrowed one the reviewer is being
            # asked a different question — is this correctly attributed —
            # and cannot tell without being shown.
            "own": claim.attribution.value == "own",
            "from_whom": claim.attributed_to or "",
        })

    # Relations, and the concept labels the page needs to render a tag as
    # something a person recognizes rather than as a slug.
    claim_list = load_claims()
    vocabulary = load_vocabulary()
    relations = [
        {
            "source": r.source_id,
            "target": r.target_id,
            "relation": r.relation.value,
            "because": r.source_location or "",
            "by": r.extraction_method or "",
            # A relation a model drafted and nobody has confirmed is not the
            # same object as one a person asserted, and the review surface is
            # exactly where that difference has to be visible.
            "unconfirmed": "unconfirmed" in (r.extraction_method or ""),
        }
        for r in load_claim_relations(claims=claim_list)
    ]
    concepts = {
        concept_id: {
            "label": (vocabulary.get(concept_id).label
                      if vocabulary.get(concept_id) else concept_id),
            "claims": sorted(c.id for c in claim_list if concept_id in c.concept_tags),
        }
        for concept_id in sorted({t for c in claim_list for t in c.concept_tags})
    }

    # Where a paper's own statements put it, next to where a person filed it.
    # Shown side by side rather than merged: the two disagree usefully, and
    # collapsing them would hide which judgment came from where.
    by_claims: dict[str, list] = {}
    for claim in claim_list:
        by_claims.setdefault(claim.resource_id, []).append(claim)
    derived_by_record = {
        rid: derived_topics(claims, vocabulary) for rid, claims in by_claims.items()
    }

    records = []
    for resource in sorted(resources, key=lambda r: (not r.abstract, r.id)):
        abstract = resource.abstract or resource.description or ""
        if len(abstract) > ABSTRACT_LIMIT:
            abstract = abstract[:ABSTRACT_LIMIT].rsplit(" ", 1)[0] + "…"
        ranked = classify_resource(index, resource, limit=SUGGESTIONS, min_score=0.5)
        # Five suggestions were shown whether five were competitive or two
        # were. The cut keeps the ones scoring within 70% of the best, bounded
        # so a decisive match still offers an alternative and a flat one does
        # not offer fourteen. Measured: 3.8 shown instead of 5, precision@shown
        # 16% -> 21%, recall 35% -> 30% — and the rest is one click away.
        suggestions, tail = ranked[:2], ranked[2:]
        if ranked:
            floor = ranked[0].score * 0.70
            suggestions = [a for a in ranked[:6] if a.score >= floor] or ranked[:2]
            if len(suggestions) < 2:
                suggestions = ranked[:2]
            tail = [a for a in ranked if a not in suggestions]
        records.append({
            "id": resource.id,
            "title": resource.title,
            "abstract": abstract,
            # All of them, not the first five. Truncating here made an author
            # page under-report its own author: Joel Z. Leibo showed 10 records
            # against the 13 he is on, because three list him sixth or later.
            # The display truncates instead, which is where truncation belongs.
            "authors": resource.authors or [],
            "date": str(resource.published_at or ""),
            "url": resource.url or "",
            "type": resource.resource_type,
            # Carried so the Add form can tell a genuinely new paper from one
            # the library already holds, without a network call.
            "doi": (resource.doi or "").lower(),
            "arxiv": (resource.arxiv_id or "").lower(),
            "repo": resource.repository_url or "",
            # What a tool lets agents do and what stops them — the fields that
            # make a record worth more than a line in a list. Only tools carry
            # them, so this costs the other records nothing.
            **({"tool": resource.tool.to_dict()} if resource.tool else {}),
            **({"sources": resource.sources} if resource.sources else {}),
            "current": resource.taxonomy_topics or [],
            "suggested": [a.code for a in suggestions],
            "suggested_more": [a.code for a in tail],
            "claims": by_resource.get(resource.id, []),
            "derived_topics": derived_by_record.get(resource.id, {}),
        })

    # The classifier's index, shipped compactly so the browser can suggest
    # topics for a paper that is not in the corpus yet. Terms are interned to
    # integers: as raw strings this roughly trebles the page.
    #
    # The scoring formula ends up written twice, here in Python and again in
    # the page. That is a real cost and worth naming — it is accepted because
    # the browser's copy only ever produces suggestions a person confirms,
    # never a stored classification, and shipping the same index data keeps
    # the two from drifting on the part that actually matters.
    terms: dict[str, int] = {}
    topic_tokens = []
    for topic in topics:
        ids = []
        for token in index.documents[topic.code]:
            ids.append(terms.setdefault(token, len(terms)))
        topic_tokens.append(ids)
    idf = [round(index.idf.get(term, 0.0), 3) for term in terms]

    # Written beside the page rather than into it. It is 17% of the payload and
    # only the Add tab ever reads it, so everyone who came to file papers was
    # parsing a search index they would never touch.
    INDEX_OUT.write_text(json.dumps({
        "terms": list(terms),
        "idf": idf,
        "topics": topic_tokens,
        "lengths": [len(index.documents[t.code]) for t in topics],
        "averageLength": round(index.average_length, 2),
    }, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")

    # Every number the docs page states, measured here at build time.
    #
    # A documentation page that hard-codes its own figures is wrong within a
    # week and nobody notices, because the page is the thing people check the
    # figures against. These are counted from the same objects the rest of the
    # payload is built from, so the page cannot disagree with the corpus it
    # describes.
    all_claims = [c for group in by_resource.values() for c in group]
    reference_store = ReferenceStore.load(REFERENCES)
    releases = sorted(p.name for p in (REPO / "data" / "releases").iterdir()
                      if p.is_dir()) if (REPO / "data" / "releases").exists() else []
    stats = {
        "records": len(records),
        "with_abstract": sum(1 for r in records if r["abstract"]),
        "with_references": len(reference_store.entries),
        "citation_edges": len(reference_store.citation_pairs(
            keys_for_corpus(resources))),
        "statements": len(all_claims),
        "papers_with_statements": sum(1 for r in records if r["claims"]),
        "primary": sum(1 for c in all_claims if c["primary"]),
        "reviewed": sum(1 for c in all_claims if c.get("verdict")),
        "machine_checked": sum(1 for c in all_claims
                               if c.get("status") == "machine-checked"),
        "by_type": {
            kind: sum(1 for c in all_claims if c["type"] == kind)
            for kind in ("finding", "position", "method", "background", "limitation",
                         "gap")
        },
        "concepts_in_use": len({t for c in all_claims for t in (c["concepts"] or [])}),
        "vocabulary": len(vocabulary.concepts),
        "suggestion_pool": sum(len(t.subpoints or []) for t in topics),
        "relations": len(relations),
        "topics": len(topics),
        "releases": releases,
        "built": date.today().isoformat(),
    }

    return {
        "generated_for": "AO Commons knowledge graph",
        "stats": stats,
        # Injected rather than copied. The page scores queries against the
        # index built here, so every one of these existing twice was a way for
        # the two to drift apart in silence.
        "scoring": {
            "stop": sorted(STOP),
            "suffixes": list(_SUFFIXES),
            "k1": TopicIndex.K1,
            "b": TopicIndex.B,
            "word": "[a-z0-9]+",
        },
        "taxonomy_version": "v3",
        "relations": relations,
        "concepts": concepts,
        "topics": [
            {
                "code": t.code,
                "title": t.title,
                "parent": t.parent_code,
                "section": t.top_level_section,
                "depth": t.depth,
                "coding": t.usage_mode.value == "coding_scheme",
                "points": t.subpoints[:4],
                # Aliases fed the classifier but never the search box, so a
                # topic could be the top machine suggestion for a paper and
                # still be unfindable by the word a person would type for it.
                "aka": (aliases or {}).get(t.code, []),
            }
            for t in topics
        ],
        "records": records,
    }


def check_script(path: Path) -> None:
    """Parse the page's script before calling the build a success.

    One unbalanced template literal takes the entire page down, and the only
    symptom is a console message on a site nobody has opened yet. Skipped
    silently where node is unavailable rather than failing a build for it.
    """
    import shutil
    import subprocess
    import tempfile

    node = shutil.which("node")
    if not node:
        print("  (node not found — script not syntax-checked)")
        return

    html = path.read_text(encoding="utf-8")
    script = html.rsplit("<script>", 1)[-1].rsplit("</script>", 1)[0]
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as handle:
        handle.write(script)
        temporary = handle.name

    result = subprocess.run([node, "--check", temporary], capture_output=True, text=True)
    Path(temporary).unlink(missing_ok=True)
    if result.returncode != 0:
        raise SystemExit(f"the page's script does not parse:\n{result.stderr}")
    print("  script parses")


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
    page = template.replace("__GRAPH_DATA__", blob)

    # GitHub Pages serves HTML with `cache-control: max-age=600`, so for ten
    # minutes after a deploy a returning visitor gets the previous graph page
    # and concludes nothing shipped. Stamping the link with a hash of the page
    # makes a changed page a changed URL, which no cache can answer from.
    graph_page = REPO / "site" / "graph.html"
    if graph_page.exists():
        stamp = hashlib.sha256(graph_page.read_bytes()).hexdigest()[:8]
        page = page.replace('href="graph.html"', f'href="graph.html?v={stamp}"')

    OUTPUT.write_text(page, encoding="utf-8")

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
    print(f"wrote {INDEX_OUT.relative_to(REPO)}  {INDEX_OUT.stat().st_size:,} bytes "
          "(fetched only by the Add tab)")

    check_script(OUTPUT)

    size = OUTPUT.stat().st_size
    print(f"wrote {OUTPUT.relative_to(REPO)}  {size:,} bytes")
    print(f"  {len(payload['topics'])} topics, {len(payload['records'])} records")
    with_abstract = sum(1 for r in payload["records"] if r["abstract"])
    print(f"  {with_abstract} records have text to judge from")
    return 0


if __name__ == "__main__":
    sys.exit(main())
