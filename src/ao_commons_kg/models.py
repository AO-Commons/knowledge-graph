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


class ReviewStatus(str, Enum):
    """Whether a record's taxonomy tags and facets have been checked.

    Published deliberately, because it changes what a reader should do with a
    result. A first-pass tag assigned from a title is a navigational aid; a
    reviewed one is a claim AO Commons is making. Presenting them identically
    would overstate the corpus.

    `unreviewed` is the default and the honest state of most of the corpus.
    A record moves to `reviewed` only when a named human has checked it —
    an AI pass, however careful, does not promote a record.
    """

    UNREVIEWED = "unreviewed"
    NEEDS_REVIEW = "needs-review"
    """Actively suspected wrong — a stronger claim than 'not yet looked at',
    and the queue a reviewer should work from first."""
    REVIEWED = "reviewed"
    DISPUTED = "disputed"
    """Someone contested the classification and it has not been settled."""


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
    MAKES_CLAIM = "MAKES_CLAIM"
    """A resource to something it says. Added with the extraction that
    populates it — the relation types below have sat here unpopulated since the
    first release, and a vocabulary that promises edges the graph does not have
    is worse than a smaller one."""
    ABOUT = "ABOUT"
    """A claim to the entity or topic it concerns."""
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


TRISTATE = frozenset({"yes", "no", "partial", "unknown"})


@dataclass
class ToolProfile:
    """The extra facts a tool carries that a paper does not.

    A nested object rather than ten more optional fields on Resource: papers
    outnumber tools and should not each carry an empty `self_hostable`.

    `agent_model` and `human_controls` are the fields worth the trouble. They
    record what shape of organization a tool makes possible and what oversight
    it actually ships — which is the question the research library exists to
    answer, asked of software instead of of literature.

    The yes/no/partial/unknown fields are tri-state rather than boolean so an
    unresearched tool is never silently recorded as proprietary.
    """

    agent_model: str | None = None
    human_controls: str | None = None
    maintainer: str | None = None
    open_source: str | None = None
    self_hostable: str | None = None
    model_agnostic: str | None = None
    status: str | None = None
    languages: list[str] = field(default_factory=list)
    protocols: list[str] = field(default_factory=list)
    used_by: list[str] = field(default_factory=list)
    """Slugs of autonomous organizations known to run on this tool — the
    cross-reference into the AO registry."""

    def __post_init__(self) -> None:
        for name in ("open_source", "self_hostable", "model_agnostic"):
            value = getattr(self, name)
            if value is not None and value not in TRISTATE:
                raise ValueError(
                    f"tool.{name} is {value!r}; expected one of {sorted(TRISTATE)}"
                )

    def to_dict(self) -> dict[str, Any]:
        return _drop_empty(asdict(self))


@dataclass
class Resource:
    """Something a researcher may want to read or use.

    Papers, preprints, reports, standards — and tools. A tool is a resource in
    exactly the sense that matters here: something you consult to decide how to
    build. It carries a `tool` profile with the facts software has and
    literature does not.
    """

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
    tool: ToolProfile | None = None
    review_status: ReviewStatus = ReviewStatus.UNREVIEWED
    reviewed_by: str | None = None
    """Role or handle of the human who checked the tags. Never personal
    contact details, and never set for an automated pass."""
    sources: list[dict[str, Any]] = field(default_factory=list)
    """Evidence for the record's claims, each with a url and access date.

    Carried through from curation rather than recomputed: a tool entry
    asserting that agents cannot exceed a budget needs the document that
    shows it, and that citation should survive the trip into the graph."""
    source_provenance: str | None = None
    ingested_at: str | None = None

    TOOL_TYPES = frozenset({"code-tool", "repository", "framework", "platform"})

    def __post_init__(self) -> None:
        self.facets = validate_facets(self.facets)
        for code in self.taxonomy_topics:
            if not TOPIC_CODE.match(code):
                raise ValueError(
                    f"resource {self.id}: taxonomy topic {code!r} is not a topic code"
                )
        if isinstance(self.tool, dict):
            self.tool = ToolProfile(**self.tool)
        if isinstance(self.review_status, str):
            self.review_status = ReviewStatus(self.review_status)
        if self.reviewed_by and self.review_status is ReviewStatus.UNREVIEWED:
            raise ValueError(
                f"resource {self.id}: reviewed_by is set but review_status is "
                "unreviewed — a reviewer without a review is a contradiction"
            )
        if self.tool is not None and self.resource_type not in self.TOOL_TYPES:
            raise ValueError(
                f"resource {self.id}: a tool profile on resource_type "
                f"{self.resource_type!r}; expected one of {sorted(self.TOOL_TYPES)}"
            )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for key in ("published_at", "updated_at"):
            value = payload.get(key)
            if isinstance(value, date):
                payload[key] = value.isoformat()
        if self.tool is not None:
            payload["tool"] = self.tool.to_dict()
        # Always emitted, even at its default: a consumer must never have to
        # infer that an absent field means unreviewed.
        payload["review_status"] = self.review_status.value
        return _drop_empty(payload)


class ClaimType(str, Enum):
    """What kind of statement this is.

    The distinction that earns its keep is FINDING versus POSITION. "Agents
    with budget caps overspent less in our trials" and "agents should have
    budget caps" look alike in an abstract and answer different questions —
    one is evidence, the other is advocacy. A graph that flattens them will
    confidently report that something has been shown when it has only been
    argued.
    """

    FINDING = "finding"
    """Something the work reports as observed or measured."""
    METHOD = "method"
    """A technique, architecture, or mechanism the work introduces."""
    LIMITATION = "limitation"
    """A boundary the authors themselves put on their result. Rare in
    abstracts and disproportionately useful, because it is the part a
    downstream reader is most likely to drop."""
    POSITION = "position"
    """An argument or recommendation, offered without evidence in this work."""


@dataclass
class Claim:
    """Something a resource says, addressable on its own.

    The unit the graph is missing while a paper is its smallest node. Papers
    are containers; the answerable things are inside them, and a question like
    "what reduces cascading failures" is a question about claims, not about
    documents.

    Two fields carry the weight. `quote` is verbatim source text and is what
    makes a claim checkable in seconds rather than by re-reading the paper —
    without it, review costs as much as extraction and nobody does it. `text`
    is our paraphrase, which is where distortion enters, so the pair is always
    stored together and shown together.

    A claim is never promoted by the extraction that produced it. It arrives
    `unreviewed` exactly like a first-pass tag, for the same reason: a machine
    reading of a sentence is a navigational aid until a person has checked it.
    """

    id: str
    resource_id: str
    text: str
    quote: str
    claim_type: ClaimType = ClaimType.FINDING
    entity_ids: list[str] = field(default_factory=list)
    topic_codes: list[str] = field(default_factory=list)
    """Where this claim suggests the record belongs. A suggestion and nothing
    more — the record's own `taxonomy_topics` are only ever written by a human
    filing it, so a claim can inform that judgement without becoming it."""
    confidence_class: ConfidenceClass = ConfidenceClass.EXTRACTED
    extracted_from: str = "abstract"
    """Which text this was read out of. An abstract states conclusions and
    omits the evidence for them, so a claim drawn from one supports a weaker
    reading than the same claim drawn from a results section — and a consumer
    cannot tell the difference unless it is recorded."""
    extraction_method: str | None = None
    review_status: ReviewStatus = ReviewStatus.UNREVIEWED
    reviewed_by: str | None = None
    verdict: str | None = None
    """How review landed. `overstated` is the one worth having: the claim is
    in the paper but the paraphrase says more than the source does, which is
    the characteristic failure of extraction and is invisible in a yes/no."""
    note: str | None = None

    VERDICTS = frozenset({"accurate", "overstated", "not-in-source", "ambiguous"})

    def __post_init__(self) -> None:
        if isinstance(self.claim_type, str):
            self.claim_type = ClaimType(self.claim_type)
        if isinstance(self.confidence_class, str):
            self.confidence_class = ConfidenceClass(self.confidence_class)
        if isinstance(self.review_status, str):
            self.review_status = ReviewStatus(self.review_status)

        if not self.quote or not self.quote.strip():
            raise ValueError(
                f"claim {self.id}: no quote. A claim with no source text cannot be "
                "checked without re-reading the paper, which is the cost this "
                "layer exists to avoid"
            )
        if self.verdict is not None and self.verdict not in self.VERDICTS:
            raise ValueError(
                f"claim {self.id}: unknown verdict {self.verdict!r}; "
                f"expected one of {sorted(self.VERDICTS)}"
            )
        if self.reviewed_by and self.review_status is ReviewStatus.UNREVIEWED:
            raise ValueError(
                f"claim {self.id}: reviewed_by is set but review_status is "
                "unreviewed — a reviewer without a review is a contradiction"
            )
        for code in self.topic_codes:
            if not TOPIC_CODE.match(code):
                raise ValueError(
                    f"claim {self.id}: topic code {code!r} is not a topic code"
                )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["claim_type"] = self.claim_type.value
        payload["confidence_class"] = self.confidence_class.value
        # Always emitted, as on Resource: an absent field must never have to be
        # read as "unreviewed".
        payload["review_status"] = self.review_status.value
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
