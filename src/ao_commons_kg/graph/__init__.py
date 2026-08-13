"""Graph computations over the corpus.

Structure-based relatedness, kept separate from the scholarly layer because
it reads stored data and touches no network.
"""

from .similarity import (
    bibliographic_coupling,
    co_citation_counts,
    co_cited_pairs,
    connectivity,
    similarity_edges,
)

__all__ = [
    "bibliographic_coupling",
    "co_citation_counts",
    "co_cited_pairs",
    "connectivity",
    "similarity_edges",
]
