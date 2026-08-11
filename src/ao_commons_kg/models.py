"""The three node families and the edges between them.

Deliberately small. V1 has Resource, Topic, and one generic Entity — not a
node type per concept. Adding a fourth node family should require showing
that a real query cannot be answered without it.

IDs are strings with a type prefix (`topic:2.2.2`, `resource:openalex:W123`)
and are stable across releases, independent of whatever database happens to
be storing them. That independence is what makes the JSONL export a usable
product rather than a dump.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import date
from enum import Enum
from typing import Any

from .facets import validate as validate_facets

TOPIC_CODE = re.compile(r"^\d+(\.\d+)*$")


class UsageMode(str, Enum):
    """How a topic is meant to be applied.

    Most topics are navigation shelves. Section 11's failure topics are a
    coding scheme: an incident normally carries several of them at once, and
    forcing a single choice would lose the thing that makes the section
    useful.
    """

    NAVIGATION = "navigation"
    CODING_SCHEME = "coding_scheme"


class TopicStatus(str, Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    """Codes are never reused or renumbered — a deprecated topic keeps its
    code forever so old tags stay resolvable."""


class ConfidenceClass(str, Enum):
    """Where an edge came from.

    The distinction is the point: a reader must be able to tell a citation
    read out of scholarly metadata from a relationship a model inferred. Any
    edge that isn't deterministic carries this, plus enough provenance to go
    back to the source text.
    """

    EXTRACTED = "EXTRACTED"
    INFERRED = "INFERRED"
    AMBIGUOUS = "AMBIGUOUS"


class RelationType(str, Enum):
    # Deterministic — from scholarly metadata, not extraction.
    CITES = "CITES"
    TAGGED_WITH = "TAGGED_WITH"
    PARENT_OF = "PARENT_OF"
    # Computed, with a named method and a score.
    SIMILAR_TO = "SIMILAR_TO"
    # Extracted or inferred; always carries provenance.
    DISCUSSES = "DISCUSSES"
    PROPOSES = "PROPOSES"
    EVALUATES = "EVALUATES"
    IMPLEMENTS = "IMPLEMENTS"
    DESCRIBES_FAILURE_OF = "DESCRIBES_FAILURE_OF"
    BELONGS_TO_TOPIC = "BELONGS_TO_TOPIC"
    RELATED_TO = "RELATED_TO"
    EXTENDS = "EXTENDS"


DETERMINISTIC_RELATIONS = frozenset(
    {RelationType.CITES, RelationType.PARENT_OF}
)
"""Edges read directly from structured metadata. Everything else must say
how confident it is and where it came from."""


def _drop_empty(payload: dict[str, Any]) -> dict[str, Any]:
    """Omit empty values so exported records stay readable.

    False and 0 are kept — `is_retracted: false` is a claim, whereas an empty
    list is just an absence.
    """
    return {
        key: value
        for key, value in payload.items()
        if value not in (None, "", [], {})
    }


@dataclass
class Topic:
    """One node of the taxonomy."""

    code: str
    title: str
    taxonomy_version: str
    parent_code: str | None = None
    top_level_section: str = ""
    description: str | None = None
    aliases: list[str] = field(default_factory=list)
    subpoints: list[str] = field(default_factory=list)
    """Unnumbered bullets sitting under a numbered topic in the source file.

    They are real content — often the most specific phrasing in the taxonomy,
    and exactly what a candidate-topic search should match on — but they carry
    no codes. Inventing codes for them would violate the rule that codes are
    stable identifiers, so they ride along on their parent instead."""
    usage_mode: UsageMode = UsageMode.NAVIGATION
    status: TopicStatus = TopicStatus.ACTIVE
    notes: str | None = None

    def __post_init__(self) -> None:
        if not TOPIC_CODE.match(self.code):
            raise ValueError(f"topic code {self.code!r} is not dotted-numeric")
        derived = self.code.rsplit(".", 1)[0] if "." in self.code else None
        if self.parent_code is None:
            self.parent_code = derived
        elif self.parent_code != derived:
            # The code *is* the hierarchy. A parent that disagrees with it
            # would make browsing and ancestor-rollup diverge.
            raise ValueError(
                f"topic {self.code}: parent_code {self.parent_code!r} "
                f"contradicts the code, which implies {derived!r}"
            )
        if not self.top_level_section:
            self.top_level_section = self.code.split(".", 1)[0]

    @property
    def id(self) -> str:
        return f"topic:{self.code}"

    @property
    def depth(self) -> int:
        return self.code.count(".")

    def ancestor_codes(self) -> list[str]:
        """Codes from the top-level section down to the immediate parent.

        Tagging a leaf implies relevance to everything above it, which is what
        makes browsing work without tagging every level by hand.
        """
        parts = self.code.split(".")
        return [".".join(parts[: i + 1]) for i in range(len(parts) - 1)]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["id"] = self.id
        payload["usage_mode"] = self.usage_mode.value
        payload["status"] = self.status.value
        return _drop_empty(payload)


@dataclass
class Resource:
    """Something a researcher may want to read or use."""

    id: str
    resource_type: str
    title: str
    description: str | None = None
    abstract: str | None = None
    authors: list[str] = field(default_factory=list)
    organizations: list[str] = field(default_factory=list)
    published_at: date | str | None = None
    updated_at: date | str | None = None
    url: str | None = None
    doi: str | None = None
    arxiv_id: str | None = None
    openalex_id: str | None = None
    semantic_scholar_id: str | None = None
    repository_url: str | None = None
    license: str | None = None
    is_open_access: bool | None = None
    is_retracted: bool | None = None
    taxonomy_topics: list[str] = field(default_factory=list)
    facets: dict[str, list[str]] = field(default_factory=dict)
    is_borrowed_background: bool = False
    """Section 15 material: relevant by transfer, not about agentic
    organizations directly. Flagged so it can be excluded from counts that
    claim to measure the field's own literature."""
    source_provenance: str | None = None
    ingested_at: str | None = None

    def __post_init__(self) -> None:
        self.facets = validate_facets(self.facets)
        for code in self.taxonomy_topics:
            if not TOPIC_CODE.match(code):
                raise ValueError(
                    f"resource {self.id}: taxonomy topic {code!r} is not a topic code"
                )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for key in ("published_at", "updated_at"):
            value = payload.get(key)
            if isinstance(value, date):
                payload[key] = value.isoformat()
        return _drop_empty(payload)


@dataclass
class Entity:
    """An approach, method, implementation, benchmark, or system.

    One generic type with an `entity_type` field, rather than a node family
    per concept. The distinctions matter for display and filtering, not for
    storage.
    """

    id: str
    entity_type: str
    name: str
    description: str | None = None
    aliases: list[str] = field(default_factory=list)
    external_ids: dict[str, str] = field(default_factory=dict)
    source_provenance: str | None = None

    ENTITY_TYPES = frozenset({
        "approach", "method", "implementation", "framework", "model",
        "benchmark", "dataset", "organization", "standard", "system",
    })

    def __post_init__(self) -> None:
        if self.entity_type not in self.ENTITY_TYPES:
            raise ValueError(
                f"entity {self.id}: unknown entity_type {self.entity_type!r}; "
                f"expected one of {sorted(self.ENTITY_TYPES)}"
            )

    def to_dict(self) -> dict[str, Any]:
        return _drop_empty(asdict(self))


@dataclass
class Relationship:
    """An edge, with enough provenance to be checked."""

    source_id: str
    target_id: str
    relation: RelationType
    confidence_class: ConfidenceClass | None = None
    confidence_score: float | None = None
    score: float | None = None
    method: str | None = None
    source_resource_id: str | None = None
    source_location: str | None = None
    extraction_method: str | None = None
    computed_at: str | None = None
    created_at: str | None = None
    attribution: str | None = None
    """Where a third party's data ends up on this edge.

    Release-level licensing covers what we produce, but an edge imported from
    OpenAlex or Semantic Scholar carries someone else's terms, and a consumer
    who lifts a handful of edges into their own graph never sees our
    metadata.json. Set it on imported edges; leave it unset on ones we derive
    ourselves, where the release license applies."""

    def __post_init__(self) -> None:
        if isinstance(self.relation, str):
            self.relation = RelationType(self.relation)

        if self.relation in DETERMINISTIC_RELATIONS:
            if self.confidence_class is not None:
                raise ValueError(
                    f"{self.relation.value} is read from structured metadata; "
                    "labelling it with a confidence class implies a judgement "
                    "that was never made"
                )
        elif self.relation is RelationType.SIMILAR_TO:
            # Computed, not judged. Hiding the method would make a score
            # impossible to interpret or reproduce.
            if not self.method:
                raise ValueError("SIMILAR_TO requires the method that produced it")
            if self.score is None:
                raise ValueError("SIMILAR_TO requires a score")
        elif self.confidence_class is None:
            raise ValueError(
                f"{self.relation.value} is non-deterministic and must carry a "
                "confidence_class of EXTRACTED, INFERRED, or AMBIGUOUS"
            )

        if self.confidence_score is not None and not 0.0 <= self.confidence_score <= 1.0:
            raise ValueError(f"confidence_score {self.confidence_score} is outside 0..1")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["relation"] = self.relation.value
        if self.confidence_class is not None:
            payload["confidence_class"] = self.confidence_class.value
        return _drop_empty(payload)
