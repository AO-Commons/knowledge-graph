"""The scholarly layer: OpenAlex resolution, references, and expansion.

Separated from the rest of the package because it is the only part that
talks to the network, and because the discovery paths should be swappable —
Semantic Scholar is a benchmark and a fallback, not a rewrite.
"""

from .openalex import (
    OpenAlexError,
    ReferenceStore,
    expand_neighborhood,
    resolve_work,
    scope_score,
)

__all__ = [
    "OpenAlexError",
    "ReferenceStore",
    "expand_neighborhood",
    "resolve_work",
    "scope_score",
]
