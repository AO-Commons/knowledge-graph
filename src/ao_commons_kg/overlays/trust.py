"""The community trust overlay — separate, optional, and measurable.

Who in the AO Commons community wrote, cited, or vouched for a work is real
signal. It is also the kind of signal that quietly becomes unfalsifiable if
you bake it into the core ranking: results get better-looking, nobody can say
by how much, and the graph starts encoding "people we know" as if it were
"work that matters".

So it is an overlay. The core graph is computed without it and is complete
without it. The overlay is applied afterward, can be switched off, and the
two rankings can be compared on the same evaluation set. If it does not
improve retrieval, that is a finding worth having rather than a suspicion.

**It also holds personal data, and this repository is public.** Keeping it
separable is what lets the overlay file live in the private repo — or on one
laptop — while the public graph stays complete and useful without it. A
design that needed the overlay to function would have forced the community
roster into a public artifact.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..models import ConfidenceClass, Relationship, RelationType


@dataclass
class TrustOverlay:
    """Affinity between community members and works in the corpus.

    Deliberately holds no names beyond what the overlay file supplies, and
    the loader treats it as opaque: the core package never reasons about who
    a person is, only that some identifier has a relationship to a work.
    """

    authors: dict[str, list[str]] = field(default_factory=dict)
    """Member identifier -> resource ids they authored."""
    endorsements: dict[str, list[str]] = field(default_factory=dict)
    """Member identifier -> resource ids they vouched for."""
    weight: float = 1.0

    @property
    def is_empty(self) -> bool:
        return not (self.authors or self.endorsements)

    @classmethod
    def load(cls, path: str | Path | None) -> TrustOverlay:
        """Absent overlay is the normal case, not an error.

        The public graph builds without one, and every caller has to keep
        working when it is missing — which is what makes the comparison
        honest rather than aspirational.
        """
        if path is None:
            return cls()
        path = Path(path)
        if not path.exists():
            return cls()

        import yaml

        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return cls(
            authors=payload.get("authors") or {},
            endorsements=payload.get("endorsements") or {},
            weight=float(payload.get("weight", 1.0)),
        )

    def affinity(self) -> dict[str, float]:
        """Resource id -> a score from community attachment.

        Authorship counts double an endorsement: writing a thing is a
        stronger signal than pointing at it. Both saturate — a work with ten
        endorsements is not ten times more relevant, and letting it be would
        make the overlay a popularity contest among a small group.
        """
        scores: dict[str, float] = {}
        for resources in self.authors.values():
            for resource_id in resources:
                scores[resource_id] = scores.get(resource_id, 0.0) + 2.0
        for resources in self.endorsements.values():
            for resource_id in resources:
                scores[resource_id] = scores.get(resource_id, 0.0) + 1.0

        # Diminishing returns, then the configured weight.
        return {
            resource_id: self.weight * (1 + score) ** 0.5
            for resource_id, score in scores.items()
        }

    def edges(self) -> list[Relationship]:
        """Overlay edges, kept out of the core relationship set.

        Emitted only when the overlay is explicitly included in a build, and
        marked INFERRED because community attachment is evidence about
        attention rather than about content.
        """
        edges = []
        for member, resources in sorted(self.authors.items()):
            for resource_id in sorted(resources):
                edges.append(Relationship(
                    f"member:{member}", resource_id, RelationType.RELATED_TO,
                    confidence_class=ConfidenceClass.EXTRACTED,
                    extraction_method="trust-overlay:authorship",
                ))
        for member, resources in sorted(self.endorsements.items()):
            for resource_id in sorted(resources):
                edges.append(Relationship(
                    f"member:{member}", resource_id, RelationType.RELATED_TO,
                    confidence_class=ConfidenceClass.INFERRED,
                    extraction_method="trust-overlay:endorsement",
                ))
        return edges


def apply(
    ranked: list[tuple[str, float]], overlay: TrustOverlay
) -> list[tuple[str, float]]:
    """Re-rank a scored list with the overlay.

    Takes and returns the same shape, so a caller can run with and without and
    diff the two. An empty overlay returns the input untouched — not a copy
    that happens to be equal, the same ordering — so "overlay off" and "no
    overlay file" are provably the same path.
    """
    if overlay.is_empty:
        return ranked
    affinity = overlay.affinity()
    return sorted(
        ((key, score + affinity.get(key, 0.0)) for key, score in ranked),
        key=lambda pair: -pair[1],
    )
