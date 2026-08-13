"""Semantic Scholar: abstracts and references for preprints.

Added because OpenAlex stores no reference lists for arXiv, and this corpus
is mostly arXiv. That single gap limited reference coverage to 9 of 59
records, which starved bibliographic coupling, and left 17 records without an
abstract, which halves classification quality. One connector, two
bottlenecks.

Not a replacement for OpenAlex. OpenAlex remains the identity and citation-
count backbone; this fills what it does not carry. Both write into the same
store under canonical keys so their references meet.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .keys import canonical_key

API = "https://api.semanticscholar.org/graph/v1"

FIELDS = ",".join((
    "title", "abstract", "year", "publicationDate", "citationCount",
    "externalIds", "authors.name",
    "references.externalIds", "references.title",
))


class SemanticScholarError(RuntimeError):
    pass


@dataclass
class Paper:
    """What Semantic Scholar contributes, in this project's terms."""

    key: str | None
    title: str
    abstract: str | None = None
    publication_date: str | None = None
    citation_count: int = 0
    authors: list[str] = field(default_factory=list)
    semantic_scholar_id: str | None = None
    referenced_keys: list[str] = field(default_factory=list)


def paper_url(identifier: str) -> str:
    """Semantic Scholar accepts several identifier forms directly."""
    identifier = identifier.strip()
    if identifier.lower().startswith("10."):
        return f"{API}/paper/DOI:{identifier}?fields={FIELDS}"
    if identifier.startswith("W"):
        raise SemanticScholarError(
            f"{identifier} is an OpenAlex id; Semantic Scholar needs a DOI or arXiv id"
        )
    if identifier[:4].isdigit() and "." in identifier:
        return f"{API}/paper/arXiv:{identifier.split('v')[0]}?fields={FIELDS}"
    return f"{API}/paper/{identifier}?fields={FIELDS}"


def parse_paper(payload: dict) -> Paper:
    external = payload.get("externalIds") or {}
    references = []
    for reference in payload.get("references") or []:
        if key := canonical_key(reference.get("externalIds")):
            references.append(key)

    return Paper(
        key=canonical_key(external),
        title=payload.get("title") or "",
        abstract=payload.get("abstract"),
        publication_date=payload.get("publicationDate"),
        citation_count=payload.get("citationCount") or 0,
        authors=[a.get("name") for a in payload.get("authors") or [] if a.get("name")],
        semantic_scholar_id=payload.get("paperId"),
        # Sorted and deduplicated so a re-fetch produces an identical record
        # and the store stays diff-friendly.
        referenced_keys=sorted(set(references)),
    )


def http_fetcher():
    """The real fetcher.

    Semantic Scholar rate-limits unauthenticated traffic hard and answers 429
    without a Retry-After, so the error says what to do rather than leaving a
    caller to guess.
    """
    import requests

    def fetch(url: str) -> dict:
        response = requests.get(url, timeout=30)
        if response.status_code == 429:
            raise SemanticScholarError(
                "Semantic Scholar rate limit. Unauthenticated traffic is capped at "
                "roughly 1 request/second; slow down, or request a free API key at "
                "https://www.semanticscholar.org/product/api and set S2_API_KEY."
            )
        if response.status_code == 404:
            raise SemanticScholarError(f"not indexed: {url.split('/paper/')[-1].split('?')[0]}")
        if not response.ok:
            raise SemanticScholarError(f"{response.status_code} for {url}")
        return response.json()

    return fetch


def resolve_paper(identifier: str, fetch) -> Paper:
    return parse_paper(fetch(paper_url(identifier)))
