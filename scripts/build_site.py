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
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from ao_commons_kg.claims import load_claims  # noqa: E402
from ao_commons_kg.classify import TopicIndex, classify_resource  # noqa: E402
from ao_commons_kg.resources import load_resources  # noqa: E402
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
            "text": claim.text,
            "standalone": claim.standalone or "",
            "quote": claim.quote,
            # Which section it was read from. A claim from a results section
            # is not on the reviewer's screen the way an abstract one is, so
            # they need to be told where to look.
            "where": claim.extracted_from,
            "type": claim.claim_type.value,
            "topics": claim.topic_codes,
            # A verdict already merged is shown rather than asked for again.
            "verdict": claim.verdict or "",
            "by": claim.reviewed_by or "",
        })

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
            "current": resource.taxonomy_topics or [],
            "suggested": [a.code for a in suggestions],
            "claims": by_resource.get(resource.id, []),
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
