"""Source-neutral identity for cited works.

OpenAlex reports references as `W…` ids; Semantic Scholar reports them as
DOIs, arXiv ids, and its own paper hashes. Storing whichever the source
happened to use gives two namespaces that never join — and because
bibliographic coupling is an intersection, the failure is silent: the graph
comes back empty and looks like a corpus with nothing in common rather than
like a bug.

So references are stored under a canonical key, preferring the identifier
most likely to be shared across sources.
"""

from __future__ import annotations

PREFERENCE = ("doi", "arxiv", "openalex", "semanticscholar")


def canonical_key(identifiers: dict[str, str | None] | None) -> str | None:
    """Pick one identifier and namespace it.

    DOI first because both sources report it and it is the identifier the
    literature itself uses. A Semantic Scholar hash is the last resort: it
    joins only against other Semantic Scholar data, which is better than
    nothing but cannot be reconciled later.
    """
    if not identifiers:
        return None

    normalized = {
        key.lower(): str(value).strip()
        for key, value in identifiers.items()
        if value
    }

    if doi := normalized.get("doi"):
        doi = doi.removeprefix("https://doi.org/").removeprefix("doi:").lower()
        # arXiv DOIs are minted mechanically; prefer the arXiv id itself so a
        # record indexed under one form still meets a record indexed under the
        # other.
        if doi.startswith("10.48550/arxiv."):
            return f"arxiv:{doi.split('.', 2)[-1].lower()}"
        return f"doi:{doi}"

    for key in ("arxiv", "arxivid"):
        if value := normalized.get(key):
            return f"arxiv:{value.lower().removeprefix('arxiv:')}"

    if value := normalized.get("openalex"):
        return f"openalex:{value.rstrip('/').rsplit('/', 1)[-1]}"

    for key in ("semanticscholar", "paperid", "corpusid"):
        if value := normalized.get(key):
            return f"semanticscholar:{value}"

    return None


def key_for_resource(resource) -> str | None:
    """The canonical key for a record we hold, from its own identifiers."""
    return canonical_key({
        "doi": resource.doi,
        "arxiv": resource.arxiv_id,
        "openalex": resource.openalex_id,
        "semanticscholar": resource.semantic_scholar_id,
    })


def keys_for_corpus(resources) -> dict[str, str]:
    """Canonical key -> the id of the record holding it, across the corpus.

    The lookup a citation needs to find its target. Built from the records
    themselves rather than from whatever the reference store happens to have
    resolved, because a paper we hold is citeable whether or not anyone has
    fetched its own bibliography yet.

    First id wins on a collision, in sorted order, so the map does not depend
    on the order the corpus loaded. A collision should not happen — two
    records sharing a canonical key are the same paper filed twice — but
    silently picking a different winner between builds would turn that
    duplicate into an unexplainable diff rather than a visible one.
    """
    index: dict[str, str] = {}
    for resource in sorted(resources, key=lambda r: r.id):
        if key := key_for_resource(resource):
            index.setdefault(key, resource.id)
    return index
