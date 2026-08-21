"""Read-only questions the corpus can answer, as plain data.

Separated from the MCP server on purpose. This layer is pure — it takes the
corpus and returns dicts — so it can be tested without a protocol, and so a
second consumer (a CLI, an HTTP service, a notebook) never has to reimplement
the queries or, worse, reimplement them slightly differently.

One rule runs through all of it: **nothing leaves here without saying how much
it has been checked.** Every record carries `review_status`. Every claim
carries the verbatim sentence it came from and who, if anyone, verified it.
Every computed edge says it was computed and by what method.

That is not decoration. At the time of writing the corpus holds 61 records of
which none have been reviewed, and 45 machine-extracted claims of which none
have been verified. An agent asking this server a question is entitled to know
that, and a response shaped like a settled fact would be a lie the caller has
no way to detect.

The questions deliberately *not* answered here are the synthesising ones —
"what reduces cascading failures". Those need the gold set, and answering them
over an unreviewed tenth of the corpus would be confident retrieval over
nothing.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from .classify import TopicIndex
from .claims import claim_edges, load_claims  # noqa: F401
from .claims import coverage as claim_coverage
from .graph import similarity_edges
from .people import same_person
from .resources import load_resources
from .scholarly.store import ReferenceStore
from .taxonomy import load_taxonomy
from . import tooling as _tooling

REPO = Path(__file__).resolve().parent.parent.parent
TAXONOMY = REPO / "taxonomy" / "agentic-org-research-library-taxonomy-v3.md"
ALIASES = REPO / "taxonomy" / "aliases.yaml"
REFERENCES = REPO / "data" / "scholarly" / "references.jsonl"


class Corpus:
    """Everything loaded once, so a server does not re-read files per call.

    Deliberately not a cache with invalidation: the files change when a build
    runs, and a long-lived server is expected to be restarted with them. A
    stale-cache bug here would be invisible and would make the server quietly
    disagree with the site.
    """

    def __init__(self, *, taxonomy: Path = TAXONOMY, aliases: Path = ALIASES,
                 references: Path = REFERENCES) -> None:
        self.topics = load_taxonomy(taxonomy)
        self.by_code = {t.code: t for t in self.topics}
        self.aliases = yaml.safe_load(aliases.read_text(encoding="utf-8")) if aliases.exists() else {}
        self.resources = load_resources()
        self.by_id = {r.id: r for r in self.resources}
        self.claims = load_claims()

        self.claims_by_resource: dict[str, list] = {}
        for claim in self.claims:
            self.claims_by_resource.setdefault(claim.resource_id, []).append(claim)

        # Built here so a phrase can be turned into branches. `search_topics`
        # matches substrings, which is right for "MARL" and useless for "stop
        # an agent overspending".
        self.index = TopicIndex(self.topics, self.aliases)

        store = ReferenceStore.load(references)
        held = set(self.by_id)
        self.citations = [(a, b) for a, b in store.citation_pairs() if a in held and b in held]
        self.similar = similarity_edges(
            {k: v for k, v in store.references().items() if k in held}, min_shared=2
        )


# ---- shapes ---------------------------------------------------------------
#
# Written out rather than dumping the dataclasses, because what a caller needs
# is not what we store: they need the provenance surfaced next to the content,
# not buried in a field they may not read.

def topic_brief(corpus: Corpus, code: str) -> dict:
    topic = corpus.by_code[code]
    filed = [r for r in corpus.resources if code in (r.taxonomy_topics or [])]
    return {
        "code": topic.code,
        "title": topic.title,
        "section": topic.top_level_section,
        "parent": topic.parent_code,
        "depth": topic.depth,
        "also_known_as": corpus.aliases.get(code, []),
        "notes": topic.subpoints[:4],
        "records_filed_here": len(filed),
    }


def claim_brief(claim) -> dict:
    return {
        "id": claim.id,
        "of_record": claim.resource_id,
        "claim": claim.text,
        "in_context": claim.standalone,
        "type": claim.claim_type.value,
        # The load-bearing field. A claim without its source sentence cannot be
        # checked, and an unchecked claim presented alone invites belief.
        "quoted_from_the_paper": claim.quote,
        "read_from": claim.extracted_from,
        "extracted_by": claim.extraction_method,
        "suggests_topics": claim.topic_codes,
        "review_status": claim.review_status.value,
        "verdict": claim.verdict,
        "verified_by": claim.reviewed_by,
    }


def record_brief(corpus: Corpus, resource, *, with_claims: bool = False) -> dict:
    claims = corpus.claims_by_resource.get(resource.id, [])
    brief = {
        "id": resource.id,
        "title": resource.title,
        "type": resource.resource_type,
        "authors": resource.authors or [],
        "published": str(resource.published_at or ""),
        "url": resource.url or "",
        "doi": resource.doi or "",
        "arxiv_id": resource.arxiv_id or "",
        "filed_under": resource.taxonomy_topics or [],
        "review_status": resource.review_status.value,
        "is_borrowed_background": resource.is_borrowed_background,
        "provenance": resource.source_provenance,
        "claims_extracted": len(claims),
    }
    if with_claims:
        brief["claims"] = [claim_brief(c) for c in claims]
    if resource.abstract:
        brief["abstract"] = resource.abstract
    if resource.tool is not None:
        brief["tool"] = resource.tool.to_dict()
    return brief


# ---- the questions --------------------------------------------------------

def search_topics(corpus: Corpus, term: str, limit: int = 10) -> list[dict]:
    """Topics matching a word, including the aliases people actually use."""
    q = (term or "").strip().lower()
    if len(q) < 2:
        return []

    scored = []
    for topic in corpus.topics:
        aka = corpus.aliases.get(topic.code, [])
        hay = " ".join([topic.title, " ".join(topic.subpoints), " ".join(aka)]).lower()
        score = 0
        if any(name.lower() == q for name in aka):
            score += 6
        if topic.code.startswith(q):
            score += 5
        if topic.title.lower().startswith(q):
            score += 3
        if q in hay:
            score += 2
        if score:
            scored.append((score, topic.code))

    scored.sort(key=lambda pair: (-pair[0], pair[1]))
    return [topic_brief(corpus, code) for _, code in scored[:limit]]


def get_topic(corpus: Corpus, code: str) -> dict:
    """One topic, its place in the tree, and what is filed under it."""
    if code not in corpus.by_code:
        return {"error": f"{code} is not a topic code in this taxonomy"}

    brief = topic_brief(corpus, code)
    brief["children"] = [
        topic_brief(corpus, t.code) for t in corpus.topics if t.parent_code == code
    ]
    brief["records"] = [
        record_brief(corpus, r) for r in corpus.resources
        if code in (r.taxonomy_topics or [])
    ]
    # Filed under a descendant rather than here. Worth separating: a caller
    # asking about 14.5 wants to know 14.5.5 holds things, without being told
    # they were filed at the parent.
    below = [
        record_brief(corpus, r) for r in corpus.resources
        if any(c.startswith(code + ".") for c in (r.taxonomy_topics or []))
    ]
    brief["records_under_children"] = below
    return brief


def search_records(corpus: Corpus, term: str, limit: int = 10) -> list[dict]:
    """Records matching a word in the title, byline or abstract."""
    q = (term or "").strip().lower()
    if len(q) < 2:
        return []

    scored = []
    for resource in corpus.resources:
        score = 0
        if q in (resource.title or "").lower():
            score += 4
        if any(q in name.lower() for name in resource.authors or []):
            score += 3
        if q in (resource.abstract or "").lower() or q in (resource.description or "").lower():
            score += 1
        if score:
            scored.append((score, resource))

    scored.sort(key=lambda pair: (-pair[0], pair[1].id))
    return [record_brief(corpus, r) for _, r in scored[:limit]]


def get_record(corpus: Corpus, resource_id: str) -> dict:
    """One record in full, with its claims and their sources."""
    resource = corpus.by_id.get(resource_id)
    if resource is None:
        return {"error": f"{resource_id} is not a record in this corpus"}
    return record_brief(corpus, resource, with_claims=True)


def get_claims(corpus: Corpus, *, record: str | None = None, claim_type: str | None = None,
               only_unverified: bool = False, limit: int = 50) -> dict:
    """Claims, always with the sentence each was read from."""
    found = corpus.claims
    if record:
        found = [c for c in found if c.resource_id == record]
    if claim_type:
        found = [c for c in found if c.claim_type.value == claim_type]
    if only_unverified:
        found = [c for c in found if c.verdict is None]

    return {
        "claims": [claim_brief(c) for c in found[:limit]],
        "matched": len(found),
        "returned": min(len(found), limit),
        # Repeated on every response on purpose. A caller that filters to one
        # paper should still be told the layer as a whole is unverified.
        "caveat": claims_caveat(corpus),
    }


def get_author(corpus: Corpus, name: str) -> dict:
    """One person and what the library holds by them.

    Matched with the same rule the corpus uses for deduplication, so an initial
    or a missing accent still finds them.
    """
    written = [r for r in corpus.resources
               if any(same_person(a, name) for a in r.authors or [])]
    if not written:
        return {"error": f"nobody matching {name!r} appears in this corpus",
                "note": "names are matched allowing for initials and accents"}

    spellings = sorted({a for r in written for a in r.authors or [] if same_person(a, name)})
    return {
        "name": spellings[0],
        "also_spelled": spellings[1:],
        "records": [record_brief(corpus, r) for r in written],
        "record_count": len(written),
        "co_authors": sorted({
            a for r in written for a in r.authors or [] if not same_person(a, name)
        }),
    }


def related_records(corpus: Corpus, resource_id: str, limit: int = 10) -> dict:
    """What this record connects to, with each connection's basis named.

    A citation is printed in the paper. A shared-references score is something
    this project computed. Returning them in one undifferentiated list would
    let a caller read the second as the first.
    """
    if resource_id not in corpus.by_id:
        return {"error": f"{resource_id} is not a record in this corpus"}

    cites = [b for a, b in corpus.citations if a == resource_id]
    cited_by = [a for a, b in corpus.citations if b == resource_id]

    coupled = []
    for edge in corpus.similar:
        other = (edge.target_id if edge.source_id == resource_id
                 else edge.source_id if edge.target_id == resource_id else None)
        if other:
            coupled.append({"record": other,
                            "title": corpus.by_id[other].title if other in corpus.by_id else "",
                            "score": round(edge.score or 0, 3),
                            "method": edge.method})
    coupled.sort(key=lambda item: -item["score"])

    return {
        "record": resource_id,
        "cites": [{"record": r, "title": corpus.by_id[r].title} for r in cites[:limit]],
        "cited_by": [{"record": r, "title": corpus.by_id[r].title} for r in cited_by[:limit]],
        "shares_references_with": coupled[:limit],
        "how_to_read_this": (
            "`cites` and `cited_by` are read from reference lists. "
            "`shares_references_with` is computed by this project as bibliographic "
            "coupling and is not a claim by either paper about the other."
        ),
    }


def claims_caveat(corpus: Corpus) -> str:
    stats = claim_coverage(corpus.claims)
    return (
        f"{stats['claims']} claims across {stats['resources']} of {len(corpus.resources)} "
        f"records; {stats['reviewed']} have been checked by a person. Every claim is a "
        "machine's reading of the quoted sentence until then — check the quote."
    )


def tools_for(corpus: Corpus, need: str, limit: int = 8) -> dict:
    """What the library holds that bears on a builder's problem.

    The question a builder actually asks is "what should I use to stop an agent
    overspending", which is a question about a branch of the taxonomy, not
    about a product category. So it resolves through the taxonomy: find the
    branches the words point at, then return what is filed there — the tools
    with what oversight they ship, and the research on the same shelf, because
    the paper describing how a control fails is part of the answer to which
    control to adopt.

    Deliberately not a recommendation. Nothing here is reviewed yet, most tools
    are unprofiled, and a ranked "use this one" would be a confident answer
    assembled from unchecked parts.
    """
    matched = corpus.index.classify(need, limit=4, min_score=0.5)
    if not matched:
        return {"need": need, "topics": [],
                "note": "no branch of the taxonomy matched that. Try the words the "
                        "taxonomy would use — budget, approval, permission, audit."}

    codes = [a.code for a in matched]
    topics = [topic_brief(corpus, code) for code in codes]
    tools, papers = [], []
    for resource in corpus.resources:
        filed = set(resource.taxonomy_topics or [])
        if not filed & set(codes):
            continue
        entry = record_brief(corpus, resource)
        if resource.tool is not None or resource.resource_type in TOOL_LIKE:
            entry["profile"] = resource.tool.to_dict() if resource.tool else None
            tools.append(entry)
        else:
            papers.append(entry)

    mirrored = [
        {"name": e.name, "url": e.url, "listed_under": e.subsection or e.section,
         "described_by_upstream": e.description[:240]}
        for e in _tooling.load().entries
        if any(word in (e.description or "").lower() or word in e.name.lower()
               for word in [w for w in need.lower().split() if len(w) > 3])
    ][:limit]

    return {
        "need": need,
        "topics": topics,
        "tools_in_the_library": tools[:limit],
        "research_on_the_same_branches": papers[:limit],
        "unassessed_from_the_mirrored_list": mirrored,
        "how_to_read_this": (
            "Tools are matched through the taxonomy branch, not by product category. "
            "A profile says what oversight the tool ships and cites where that was read; "
            "an entry under `unassessed_from_the_mirrored_list` is somebody else's "
            "one-line description, carried from awesome-builder-tools (Framework Zero, "
            "MIT) and never checked here. Nothing in this answer is a recommendation — "
            "no record in this corpus has been reviewed yet."
        ),
    }


TOOL_LIKE = frozenset({"code-tool", "platform", "framework", "repository"})


def coverage(corpus: Corpus) -> dict:
    """How much of the corpus has been checked, so a caller can weigh the rest."""
    stats = claim_coverage(corpus.claims)
    reviewed = [r for r in corpus.resources if r.review_status.value != "unreviewed"]
    tagged = [r for r in corpus.resources if r.taxonomy_topics]
    return {
        "topics": len(corpus.topics),
        "records": len(corpus.resources),
        "records_with_a_topic": len(tagged),
        "records_reviewed_by_a_person": len(reviewed),
        "records_with_claims_extracted": stats["resources"],
        "claims": stats["claims"],
        "claims_verified_by_a_person": stats["reviewed"],
        "citations_between_held_records": len(corpus.citations),
        "computed_similarity_edges": len(corpus.similar),
        "what_this_means": (
            "Topic tags are a first pass unless a record says otherwise, and claims are "
            "machine-extracted until verified. Treat both as leads to check rather than "
            "as findings, and prefer the quoted sentence over the paraphrase."
        ),
    }
