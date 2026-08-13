"""The scholarly layer: resolution, references, and expansion.

Separated from the rest of the package because it is the only part that talks
to the network, and because the discovery paths are meant to be swappable —
OpenAlex is the identity and citation backbone, Semantic Scholar fills the
arXiv references and abstracts it does not carry.
"""

from .keys import canonical_key, key_for_resource
from .openalex import OpenAlexError, expand_neighborhood, resolve_work, scope_score
from .semanticscholar import SemanticScholarError, resolve_paper
from .store import ReferenceStore

__all__ = [
    "OpenAlexError",
    "ReferenceStore",
    "SemanticScholarError",
    "canonical_key",
    "expand_neighborhood",
    "key_for_resource",
    "resolve_paper",
    "resolve_work",
    "scope_score",
]
