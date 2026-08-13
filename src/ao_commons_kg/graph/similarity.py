"""Relatedness from graph structure rather than from vocabulary.

The Connected Papers insight: two papers that never cite each other can be
closely related, and a citation walk will not find them. Two measures do,
both computable from reference lists alone:

**Bibliographic coupling** — two papers are related if they cite the same
works. Symmetric, available the moment both are published, and it does not
care what words either uses.

**Co-citation** — two works are related if the same later papers cite both.
Accrues over time, so it finds the foundations a field has converged on.

Neither reads a title. That matters here: the keyword pre-filter scores
"Institutions as cached computation for resource-rational negotiation" at 1
and it is squarely in scope. Structure finds what vocabulary misses.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass

from ..models import Relationship, RelationType


@dataclass(frozen=True)
class Coupling:
    """One SIMILAR_TO relationship, with the arithmetic behind it."""

    source: str
    target: str
    shared: int
    score: float
    method: str

    def to_edge(self, resolve: dict[str, str] | None = None) -> Relationship:
        resolve = resolve or {}
        return Relationship(
            resolve.get(self.source, self.source),
            resolve.get(self.target, self.target),
            RelationType.SIMILAR_TO,
            method=self.method,
            score=round(self.score, 4),
        )


def bibliographic_coupling(
    references: dict[str, list[str]], *, min_shared: int = 2
) -> list[Coupling]:
    """Pairs of works that cite the same things.

    Scored with Jaccard over reference sets, so a pair sharing 5 of 20
    references outranks a pair sharing 5 of 300. Raw overlap alone rewards
    papers with long bibliographies, which is a property of the paper rather
    than of the relationship.

    `min_shared` defaults to 2 because a single shared reference is usually
    a canonical work everyone cites, not evidence of a relationship.
    """
    sets = {key: set(values) for key, values in references.items() if values}
    couplings: list[Coupling] = []

    keys = sorted(sets)
    for i, left in enumerate(keys):
        for right in keys[i + 1:]:
            shared = sets[left] & sets[right]
            if len(shared) < min_shared:
                continue
            union = sets[left] | sets[right]
            couplings.append(
                Coupling(left, right, len(shared), len(shared) / len(union),
                         "bibliographic-coupling")
            )

    return sorted(couplings, key=lambda c: (-c.score, -c.shared, c.source, c.target))


def co_citation_counts(references: dict[str, list[str]]) -> Counter:
    """How many of our works cite each external work.

    The keyword-free relevance signal. A work cited by several papers already
    in the library is connected to this field by the field's own behaviour,
    whatever its title says.
    """
    counts: Counter = Counter()
    for cited in references.values():
        counts.update(set(cited))
    return counts


def co_cited_pairs(
    references: dict[str, list[str]], *, min_shared: int = 2
) -> list[Coupling]:
    """External works that our papers cite together.

    Two works co-cited by several of our papers are related in the eyes of
    this field, which is what the registry is trying to map. Used to rank
    expansion candidates: a candidate co-cited with something we already hold
    is a better proposal than one that merely shares vocabulary.
    """
    together: dict[tuple[str, str], int] = defaultdict(int)
    for cited in references.values():
        unique = sorted(set(cited))
        for i, left in enumerate(unique):
            for right in unique[i + 1:]:
                together[(left, right)] += 1

    appearances = co_citation_counts(references)
    return sorted(
        (
            Coupling(left, right, count,
                     count / min(appearances[left], appearances[right]),
                     "co-citation")
            for (left, right), count in together.items()
            if count >= min_shared
        ),
        key=lambda c: (-c.shared, -c.score, c.source, c.target),
    )


def connectivity(
    candidate_references: dict[str, list[str]],
    corpus_references: dict[str, list[str]],
) -> dict[str, tuple[int, int]]:
    """How attached each candidate is to the corpus, ignoring its text.

    Returns (shared references with the corpus, times cited by the corpus).
    Either one is evidence the field already treats the candidate as part of
    this conversation — evidence a keyword score cannot see and cannot fake.
    """
    corpus_refs = {ref for refs in corpus_references.values() for ref in refs}
    cited_by_corpus = co_citation_counts(corpus_references)

    return {
        candidate: (
            len(set(refs) & corpus_refs),
            cited_by_corpus.get(candidate, 0),
        )
        for candidate, refs in candidate_references.items()
    }


def similarity_edges(
    references: dict[str, list[str]],
    resolve: dict[str, str] | None = None,
    *,
    min_shared: int = 2,
    limit: int | None = None,
) -> list[Relationship]:
    """SIMILAR_TO edges from bibliographic coupling.

    `references` is keyed by resource id, so no translation is needed. The
    optional `resolve` is kept for callers holding a different keying; pairs
    it cannot resolve are skipped rather than emitted as dangling edges.
    """
    couplings = bibliographic_coupling(references, min_shared=min_shared)
    if resolve:
        couplings = [c for c in couplings if c.source in resolve and c.target in resolve]
    if limit:
        couplings = couplings[:limit]
    return [c.to_edge(resolve) for c in couplings]
