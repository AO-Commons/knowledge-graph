#!/usr/bin/env python3
"""An MCP server over the knowledge graph. Read-only.

    aokg-mcp            # after `pip install -e '.[mcp]'`

Thin on purpose. Every question lives in `ao_commons_kg.queries` as a pure
function returning plain data; this file is the protocol binding and nothing
else. If a tool here ever needs logic of its own, that is the signal the query
does not belong yet.

Read-only is a design decision, not a limitation to fix later. Filings and
claim verdicts enter through the review site and a pull request, where they
are attributable to a person and visible before they land. A tool that let an
agent write into the gold set would put unattributable judgements into the one
dataset every measurement is taken against.

What this will not answer: research questions. "What reduces cascading
failures" needs claims across the corpus, verified. Today there are 45,
covering 6 of 61 records, none verified. Every response carries the review
status so a caller can see that for itself rather than being told a number it
cannot check.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from ao_commons_kg import queries  # noqa: E402

try:
    # `MCPServer` in the 2.x SDK; this was `FastMCP` in 1.x, and importing the
    # old name gets you the "not installed" message below rather than an error
    # naming the real problem.
    from mcp.server import MCPServer
except ImportError:  # pragma: no cover - a missing optional dependency
    print(
        "The MCP SDK is not installed. It is an optional extra, because the rest\n"
        "of this package deliberately depends on almost nothing:\n\n"
        "    pip install -e '.[mcp]'\n",
        file=sys.stderr,
    )
    raise SystemExit(1)


# Loaded once at start-up. The corpus changes when a build runs, and a server
# holding a stale copy would quietly disagree with the site — so this is a
# restart, not a cache to invalidate.
# Built on first use rather than at import, so `--help`, the console-script
# shim and a stray import do not read the whole corpus off disk.
_CORPUS: queries.Corpus | None = None


def corpus() -> queries.Corpus:
    global _CORPUS
    if _CORPUS is None:
        _CORPUS = queries.Corpus()
    return _CORPUS


server = MCPServer(
    "ao-commons-knowledge-graph",
    instructions=(
        "The AO Commons research library: a taxonomy of agentic-organization "
        "research, the records filed under it, the people who wrote them, and "
        "machine-extracted claims with the sentence each came from.\n\n"
        "Two things to hold onto when using it. Topic tags are a first pass "
        "unless a record says it was reviewed, and claims are a model's reading "
        "of a quoted sentence until a person has verified them — so prefer the "
        "quote to the paraphrase, and say which you are relying on. Call "
        "`coverage` first if you need to know how much of this is checked."
    ),
)


def as_text(payload) -> str:
    """MCP carries text. JSON keeps the structure a caller needs to filter on."""
    return json.dumps(payload, ensure_ascii=False, indent=2)


@server.tool()
def coverage() -> str:
    """How much of the library has been checked by a person, and how much has not.

    Worth calling before relying on anything else: it says how many records
    have been reviewed and how many claims verified, which is what decides how
    much weight the other answers can carry.
    """
    return as_text(queries.coverage(corpus()))


@server.tool()
def search_topics(term: str, limit: int = 10) -> str:
    """Find topics in the 103-code taxonomy by word, including known aliases.

    Aliases matter here: "MARL" finds the multi-agent reinforcement learning
    topic even though those words are not in its title.
    """
    return as_text(queries.search_topics(corpus(), term, limit))


@server.tool()
def get_topic(code: str) -> str:
    """One topic: its place in the tree, its children, and what is filed under it.

    Records filed directly under the code are separated from those filed under
    its children, because "nothing here" and "nothing below here" are different
    facts about a branch.
    """
    return as_text(queries.get_topic(corpus(), code))


@server.tool()
def get_statement(claim_id: str, with_context: bool = True) -> str:
    """One statement, its source sentence, and the context needed to judge it.

    Findings and positions are what the library is asked for — what has been
    shown, and what has been argued. Background, method and limitation are
    how you decide what a finding is worth once you have it, so they travel
    with it rather than being returned as peers in a search.

    Also returns the relations this statement is an end of, with the
    reasoning behind each. Every one is inferred and most are currently a
    machine's draft; the response says which.
    """
    from .claims import context_for, load_claim_relations, load_claims

    claims = load_claims()
    by_id = {c.id: c for c in claims}
    claim = by_id.get(claim_id)
    if not claim:
        return as_text({"error": f"no statement {claim_id!r}"})

    def brief(c) -> dict:
        return {
            "id": c.id, "text": c.text, "type": c.claim_type.value,
            "primary": c.claim_type.is_primary,
            "attribution": c.attribution.value,
            "attributed_to": c.attributed_to or "",
            "concepts": c.concept_tags,
            "quote": c.quote,
            "from": c.extracted_from,
            "verified": c.review_status.value != "unreviewed",
        }

    payload = {"statement": brief(claim), "of_paper": claim.resource_id}
    if with_context:
        payload["context"] = [brief(c) for c in context_for(claim, claims)]
    payload["relations"] = [
        {"relation": r.relation.value,
         "direction": "from this" if r.source_id == claim_id else "to this",
         "other": (by_id[r.target_id if r.source_id == claim_id else r.source_id].text),
         "because": r.source_location,
         "asserted_by": r.extraction_method}
        for r in load_claim_relations(claims=claims)
        if claim_id in (r.source_id, r.target_id)
    ]
    return as_text(payload)


@server.tool()
def search_concepts(term: str = "", unused: bool = False, limit: int = 20) -> str:
    """Search the statement vocabulary — what a claim can be tagged with.

    Different from `search_topics`. A topic is a shelf a record is filed on,
    103 of them. A concept is what a statement argues about, 523 of them, and
    it is the thing that decides which statements can ever be proposed as
    related to each other: two claims sharing a concept become a candidate
    pair, and two claims with no concept in common never meet.

    Which makes this the tool to reach for before adding a term. The one
    failure mode a vocabulary has is silent — two labels for one idea break
    nothing and quietly halve the relations either would have proposed — so
    the question worth asking first is always whether the idea is already
    here under another name.

    `unused` lists concepts no statement carries. Most of the 523 are unused:
    514 were inherited from the taxonomy's own subpoints and only a handful
    have met a claim yet.
    """
    from .concepts import load_vocabulary, similar_terms, usage

    vocabulary = load_vocabulary()
    counts = usage(corpus().claims, vocabulary)

    if unused:
        found = [c for c in vocabulary.concepts.values() if not counts.get(c.id)]
    elif term:
        found = [c for c in vocabulary.search(term)]
        # A near-miss is the answer to "is this already here", so surface it
        # even when the words do not overlap.
        found += [c for _, c in similar_terms(term, vocabulary) if c not in found]
    else:
        found = [c for c in vocabulary.concepts.values() if counts.get(c.id)]

    return as_text({
        "vocabulary_size": len(vocabulary),
        "carrying_a_statement": sum(1 for n in counts.values() if n),
        "matches": [
            {"id": c.id, "label": c.label, "topics": list(c.topics),
             "origin": c.origin, "statements": counts.get(c.id, 0)}
            for c in found[:limit]
        ],
    })


@server.tool()
def search_records(term: str, limit: int = 10) -> str:
    """Find papers, tools and deployments by title, author or abstract."""
    return as_text(queries.search_records(corpus(), term, limit))


@server.tool()
def get_record(record_id: str) -> str:
    """One record in full, with every claim extracted from it and its source sentence."""
    return as_text(queries.get_record(corpus(), record_id))


@server.tool()
def get_claims(record: str = "", claim_type: str = "", only_unverified: bool = False,
               limit: int = 50) -> str:
    """Claims extracted from the corpus, each with the sentence it was read from.

    `claim_type` is one of finding, method, limitation, position, background.
    A finding is something the work reports observing; a position is an
    argument offered without evidence in that work, and conflating the two is
    how a graph comes to report that something has been shown when it was only
    argued.
    """
    return as_text(queries.get_claims(
        corpus(), record=record or None, claim_type=claim_type or None,
        only_unverified=only_unverified, limit=limit,
    ))


@server.tool()
def tools_for(need: str, limit: int = 8) -> str:
    """What the library holds that bears on a builder's problem.

    Ask it in the builder's words — "stop an agent overspending", "approve an
    action before it runs", "audit what an agent did". It resolves through the
    taxonomy rather than by product category, and returns the tools filed on
    those branches with what oversight each ships, the research on the same
    branches, and anything from the mirrored builder-tooling list that nobody
    here has assessed.

    It does not recommend. Nothing in this corpus has been reviewed yet, and
    most tools are unprofiled; a ranked answer would be confident about
    unchecked parts.
    """
    return as_text(queries.tools_for(corpus(), need, limit))


@server.tool()
def get_author(name: str) -> str:
    """A person, what the library holds by them, and who they wrote it with.

    Matched allowing for initials and accents, so "joel z leibo" finds
    "Joel Z. Leibo".
    """
    return as_text(queries.get_author(corpus(), name))


@server.tool()
def related_records(record_id: str, limit: int = 10) -> str:
    """What a record connects to, with the basis of each connection named.

    Citations are read from reference lists. Shared-reference scores are
    computed by this project as bibliographic coupling and are not a claim by
    either paper about the other; the response says so.
    """
    return as_text(queries.related_records(corpus(), record_id, limit))


def main() -> None:
    """Entry point for `aokg-mcp`, and for running the module directly."""
    server.run()


if __name__ == "__main__":
    main()
