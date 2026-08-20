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
