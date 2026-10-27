"""The corpus as a MIRA graph.

MIRA (https://github.com/MIRA-science/schema) is an open schema for research
graphs: questions, the claims that address them, and the evidence behind each.
We already took two of its names — `Question` and `addresses` — when that layer
was still a sketch. This writes the whole corpus in its vocabulary.

A second output of the same build, never a replacement. `write_release` keeps
writing `nodes.jsonl` byte for byte as before, models.py stays the place where
meaning is argued, and this module is a projection. Deleting this file removes
the integration and changes nothing else.

**What it refuses to do is guess.** MIRA cannot express large parts of this
corpus — 103 taxonomy topics, 62 concepts, and four of our six edge kinds have
no home in it at all. Every one of those is counted and named in the report
rather than dropped quietly or forced into a slot that means something else.
The report is the point of this module as much as the graph is: it is the
evidence for what MIRA would need to carry a corpus like ours, and it is meant
to be read by their maintainers.

Three conventions here are MIRA's rather than ours, taken from its sample data
and from MIRA-science/MIRA-extraction, so that two tools emitting MIRA emit the
same MIRA:

* **Node subtypes are a pair.** A node is typed `[local NodeSchema, MIRA
  class]`, with the local definition declaring `subClassOf`. That is how our
  seven claim kinds survive inside MIRA's four classes without inventing
  anything.
* **Relations are reified.** Every edge is a `RelationInstance` with
  `dgb:source` and `dgb:destination` rather than a property on the node. Not
  stylistic: MIRA's `Argument` mixin is attached to no class, so `supports` on
  a Claim fails the closed SHACL shape, while a reified claim touches no
  shape at all. It also gives us somewhere legal to put the provenance an edge
  of ours carries, which a bare property could not hold.
* **Quotes are anchors.** A verbatim quote becomes a `sioc:Item` inside the
  paper's text `Container`, and the node it grounds points at it through
  `description`. One construction carries what `quote` and `extracted_from`
  carry here, and gives every quote a URI.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from ..concepts import Concept
from ..models import (
    Claim,
    ClaimType,
    Entity,
    Question,
    Relationship,
    RelationType,
    Resource,
    Topic,
)

#: Their published context. Pinned by the vendored schema, not fetched here.
CONTEXT = "https://purl.org/mira-science/mira.jsonld"

#: Where our own identifiers live. Everything we mint is under this, so a
#: reader can tell at a glance which half of the graph is MIRA's.
BASE = "https://graph.aocommons.com"
AOC = f"{BASE}/ns#"

#: Which MIRA class each of our seven claim kinds becomes.
#:
#: Two of the seven are not Claims in MIRA's sense, and they are named for
#: what they are: `evidence` is an observation from applying a method, and
#: Evidence is the only class with a direct `sourceDocument` slot, so it is
#: the one kind whose link to its paper MIRA can state. A `gap`
#: stays a Claim here: it is something a paper said, and it reaches the
#: question it raises through `addresses`. MIRA's extractor reads the same
#: sentences as `Request` instead; that disagreement is live and is recorded in
#: docs/open-problems.md rather than resolved by this file.
CLASS_OF: dict[ClaimType, str] = {
    # Identity mappings since the kinds took MIRA's names on 2026-10-26.
    ClaimType.EVIDENCE: "Evidence",
    ClaimType.PROTOCOL: "Protocol",
    ClaimType.POSITION: "Claim",
    ClaimType.DEFINITION: "Claim",
    ClaimType.LIMITATION: "Claim",
    ClaimType.GAP: "Claim",
    ClaimType.BACKGROUND: "Claim",
}

#: Our relations that MIRA names, and what it calls them.
RELATION_OF: dict[RelationType, str] = {
    RelationType.ADDRESSES: "addresses",
    RelationType.SUPPORTS: "supports",
    RelationType.DISAGREES_WITH: "opposes",
}

#: Relations MIRA has no term for, with the reason, so the report can say more
#: than a number. `qualifies` and `extends` are CiTO's and are the two we would
#: most like upstream: in a young field papers rarely flatly oppose each other,
#: they qualify and extend.
NO_MIRA_RELATION: dict[RelationType, str] = {
    RelationType.MAKES_CLAIM:
        "MIRA routes a document to a claim through Study and Evidence. We have "
        "no Study nodes, so this is carried by the anchor convention instead: "
        "a claim's quote is an Item in the paper's Container.",
    RelationType.CITES:
        "Citation between documents is outside MIRA's scope; dcterms:references "
        "would serve but is not in its context.",
    RelationType.SIMILAR_TO: "Computed bibliographic coupling. Ours alone.",
    RelationType.TAGGED_WITH:
        "Concept tags. RRGI has proposed the same thing upstream as "
        "contextEntities (schema issue #35).",
    RelationType.ABOUT:
        "Taxonomy placement. RRGI has proposed the same thing upstream as "
        "tradition/stemsFrom (schema issue #35).",
    RelationType.PARENT_OF: "Taxonomy hierarchy. Ours alone.",
    RelationType.AUTHORED:
        "A person to a record they wrote. MIRA carries bylines as dct:creator "
        "on a SourceDocument, which is attribution without identity: the same "
        "person on two papers is two strings.",
    RelationType.AFFILIATED_WITH:
        "A person to the organization they were at. MIRA has foaf:Agent "
        "through dg_base but no class for an organization and nothing tying one "
        "to a document, so an ecosystem map cannot be expressed. One of ours to "
        "propose.",
    RelationType.QUALIFIES:
        "CiTO's cito:qualifies. No MIRA term; one of ours to propose.",
    RelationType.EXTENDS_CLAIM:
        "CiTO's cito:extends. No MIRA term; one of ours to propose.",
}

#: Claim fields with no MIRA slot, and why we want one. Reported per
#: release so the list shrinks visibly as proposals land.
UNHOMED_CLAIM_FIELDS: dict[str, str] = {
    "standalone":
        "The claim restated with enough context to judge it cold. `title` is "
        "the short form and `description` is taken by the quote anchor.",
    "attribution":
        "Whether the paper is reporting its own result or somebody else's. "
        "Without this axis, 'who first showed X' returns the most recent "
        "repeater. Nobody has proposed it upstream; it is the strongest of ours.",
    "confidence_class":
        "Whether a record was read off the source, inferred, or ambiguous. "
        "MIRA already imports PROV, so this may need a convention rather than "
        "a slot.",
    "extraction_method":
        "Which model drafted a record, under which brief, on what date. "
        "`creator` carries an account standing for the drafter, which is where "
        "MIRA's own extractor puts it, but the brief and the date of the "
        "reading have nowhere to go.",
    "review_status / reviewed_by / verdict / reviewed_by_author":
        "Who checked this against the paper and what they concluded. RRGI has "
        "proposed endorsements upstream (schema PR #32); an author's verdict "
        "counting differently from a reader's is the part still missing.",
    "concept_tags":
        "Proposed upstream by RRGI as contextEntities (schema issue #35).",
    "entity_ids":
        "The named things a claim is about — a system, an organization, a "
        "particular deployment. Designed here and not yet built; see "
        "docs/concepts-and-entities.md for why these are not concepts.",
}


@dataclass
class Report:
    """What the projection did, and what it could not do.

    Modelled on MIRA-extraction's own discipline: report, never drop. A number
    here that nobody can account for means this module lost something.
    """

    nodes: Counter = field(default_factory=Counter)
    edges: Counter = field(default_factory=Counter)
    omitted_nodes: Counter = field(default_factory=Counter)
    omitted_edges: Counter = field(default_factory=Counter)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "emitted": {
                "nodes": dict(sorted(self.nodes.items())),
                "edges": dict(sorted(self.edges.items())),
                "node_total": sum(self.nodes.values()),
                "edge_total": sum(self.edges.values()),
            },
            "omitted": {
                "nodes": dict(sorted(self.omitted_nodes.items())),
                "edges": dict(sorted(self.omitted_edges.items())),
                "node_total": sum(self.omitted_nodes.values()),
                "edge_total": sum(self.omitted_edges.values()),
            },
            "unhomed_claim_fields": UNHOMED_CLAIM_FIELDS,
            "notes": self.notes,
        }


def _doc_iri(resource: Resource) -> str:
    """A document's identifier, preferring one the world already resolves.

    A DOI beats our own URL because somebody else's graph can join on it, which
    is most of the reason to publish MIRA at all.
    """
    if resource.doi:
        return f"https://doi.org/{resource.doi}"
    if resource.arxiv_id:
        return f"https://arxiv.org/abs/{resource.arxiv_id}"
    if resource.url:
        return resource.url
    return f"{BASE}/papers/{resource.id}"


def _is_document(resource: Resource) -> bool:
    """Whether MIRA's `SourceDocument` is a true description of this record.

    `SourceDocument` is `is_a: CreativeWork` and means a paper, book or report.
    A tool, a deployment or an evaluation suite is none of those, and typing
    one as a document to get it into the file would put a false claim in
    the data. They are counted out instead.
    """
    return str(getattr(resource.resource_type, "value", resource.resource_type)) in {
        "preprint", "peer-reviewed-paper", "technical-report", "article",
        "book", "thesis", "dataset-paper",
    }


def _slug(name: str) -> str:
    """A byline as something that can be an IRI.

    Names carry spaces, accents and punctuation, and an IRI carrying a space is
    not an IRI — a validator resolves it against the file it was parsed from
    and reports a type error three steps away from the cause. This cost an
    afternoon, so: slug, always.
    """
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower().strip()).strip("-")
    return slug or "unnamed"


def _account(name: str, *, kind: str = "people") -> dict[str, Any]:
    return {"@id": f"{BASE}/{kind}/{_slug(name)}", "@type": "UserAccount",
            "accountName": name}


#: The account that stands for a machine draft. MIRA's `creator` takes a
#: UserAccount and an account is the only place in-schema to say who produced a
#: record, so a model gets one — the same convention MIRA's own extractor uses.
#: It does not assert that anybody holds it.
DRAFTED_BY = "ao-commons extraction"


def build_graph(
    *,
    resources: Iterable[Resource] = (),
    claims: Iterable[Claim] = (),
    questions: Iterable[Question] = (),
    relationships: Iterable[Relationship] = (),
    topics: Iterable[Topic] = (),
    concepts: Iterable[Concept] = (),
    entities: Iterable[Entity] = (),
    organizations: Iterable[Any] = (),
    built_at: str | None = None,
) -> tuple[dict[str, Any], Report]:
    """Project the corpus into MIRA, and say what did not fit."""
    report = Report()
    graph: list[dict[str, Any]] = []
    drafter = _account(DRAFTED_BY, kind="agents")

    resources = list(resources)
    claims = list(claims)
    questions = list(questions)
    relationships = list(relationships)

    # ---- what MIRA has no class for ----------------------------------------
    for group, name, why in (
        (list(topics), "topic",
         "Taxonomy sections. RRGI has proposed tradition/stemsFrom upstream."),
        (list(concepts), "concept",
         "Concept tags. RRGI has proposed contextEntities upstream."),
        (list(organizations), "organization",
         "Universities, labs, companies and agencies, with a city and a kind. "
         "MIRA has no class for one; foaf:Agent exists in dg_base and nothing "
         "connects it to a SourceDocument."),
        (list(entities), "entity",
         "People and organizations. foaf:Agent exists in dg_base but no MIRA "
         "class ties one to a document."),
    ):
        if group:
            report.omitted_nodes[name] = len(group)
            report.notes.append(f"{len(group)} {name} nodes: {why}")

    # ---- documents ----------------------------------------------------------
    iri_of_resource: dict[str, str] = {}
    accounts: dict[str, dict[str, Any]] = {}
    merged_bylines: set[tuple[str, str]] = set()

    for resource in sorted(resources, key=lambda r: r.id):
        if not _is_document(resource):
            kind = str(getattr(resource.resource_type, "value", resource.resource_type))
            report.omitted_nodes[f"resource:{kind}"] += 1
            continue

        iri = _doc_iri(resource)
        iri_of_resource[resource.id] = iri

        node: dict[str, Any] = {
            "@id": iri,
            "@type": "SourceDocument",
            "title": resource.title,
        }
        if resource.published_at:
            node["created"] = resource.published_at
        # The paper's authors as its creators. MIRA's `creator` takes a
        # UserAccount, so a byline becomes an account with no claim that
        # anybody holds it — which is what a byline is.
        bylines = [a for a in (resource.authors or []) if isinstance(a, str)]
        if bylines:
            # Keyed by slug, not by byline. Two spellings of one name — "Joon
            # Sung Park" and "Joon-Sung Park" — are one account, and keying by
            # the string would give that account two names and fail the
            # cardinality constraint. The merge is counted, because it is also
            # a small fact about our own data worth seeing.
            for name in bylines:
                key = _slug(name)
                if key in accounts:
                    if accounts[key]["accountName"] != name:
                        merged_bylines.add((accounts[key]["accountName"], name))
                else:
                    accounts[key] = _account(name)
            node["creator"] = sorted({accounts[_slug(n)]["@id"] for n in bylines})
        graph.append(node)
        report.nodes["SourceDocument"] += 1

    if report.omitted_nodes:
        missing = sum(v for k, v in report.omitted_nodes.items()
                      if k.startswith("resource:"))
        if missing:
            report.notes.append(
                f"{missing} records are not documents — tools, deployments and "
                "evaluation suites, held as records so a claim can point at "
                "one. MIRA's SourceDocument is_a CreativeWork and would be a "
                "false description of them. A class for a studied artefact is "
                "one of ours to propose."
            )

    # ---- claims, and the anchors that ground them -----------------------
    containers: dict[str, str] = {}
    items: list[dict[str, Any]] = []
    claim_iris: dict[str, str] = {}
    used_classes: set[str] = set()
    used_kinds: set[str] = set()

    for claim in sorted(claims, key=lambda c: c.id):
        kind = ClaimType(claim.claim_type) if not isinstance(claim.claim_type, ClaimType) \
            else claim.claim_type
        mira_class = CLASS_OF[kind]
        iri = f"{BASE}/claims/{claim.id}"
        claim_iris[claim.id] = iri
        used_classes.add(mira_class)
        used_kinds.add(kind.value)

        node: dict[str, Any] = {
            "@id": iri,
            "@type": [f"{AOC}kind/{kind.value}", mira_class],
            "title": claim.text,
        }
        node["creator"] = drafter["@id"]
        if claim.standalone:
            # `content` is the fuller text of the item. The quote lives on the
            # anchor, so this is where the self-contained restatement goes —
            # the closest MIRA has to `standalone`, and not quite it.
            node["content"] = claim.standalone

        doc_iri = iri_of_resource.get(claim.resource_id)

        # The anchor: the paper's own sentence, as an Item in the paper's text
        # container. This is MIRA's grounding convention and it is the only
        # thing tying a Claim to the document it was read out of.
        if claim.quote and doc_iri:
            container = containers.setdefault(doc_iri, f"{doc_iri}#text")
            anchor = f"{iri}#quote"
            items.append({
                "@id": anchor,
                "@type": "Item",
                "format": "text/plain",
                "content": claim.quote,
                "has_container": container,
            })
            node["description"] = anchor
            report.nodes["Item"] += 1

        # Evidence is the one class with a slot naming the document it came
        # from, which is why a finding is the only kind of claim whose
        # provenance MIRA can state outright.
        if mira_class == "Evidence" and doc_iri:
            node["sourceDocument"] = doc_iri

        graph.append(node)
        report.nodes[mira_class] += 1

    if claims and not any(k.startswith("Claim") for k in report.nodes):
        pass  # nothing to say; the counter speaks

    report.notes.append(
        "A claim that is not a finding reaches its paper only through the "
        "anchor Item's container, by URI convention. MIRA has no slot from a "
        "Claim to the document that asserts it, which is the single largest "
        "thing this projection cannot say."
    )

    # ---- questions ----------------------------------------------------------
    question_iris: dict[str, str] = {}
    for question in sorted(questions, key=lambda q: q.id):
        iri = f"{BASE}/problems/{question.id}"
        question_iris[question.id] = iri
        node: dict[str, Any] = {
            "@id": iri,
            "@type": "Question",
            "title": question.text,
        }
        if question.note:
            # Why these claims are one question. On our own surface this is
            # never shown without the cluster, because a cluster asserted
            # without its reasoning is a judgement hiding as a fact. MIRA's
            # Question has no slot for it and no slot for who asserted it.
            node["content"] = question.note
        graph.append(node)
        report.nodes["Question"] += 1

    if questions:
        report.notes.append(
            "MIRA's Question carries no slots of its own. The reasoning for a "
            "cluster is emitted as `content`; who asserted it and when, and the "
            "question's status, have nowhere to go."
        )

    # ---- edges, reified ------------------------------------------------------
    iri_of_node: dict[str, str] = {**claim_iris, **question_iris, **iri_of_resource}
    used_relations: set[str] = set()
    reified: list[dict[str, Any]] = []

    for i, edge in enumerate(sorted(
        relationships, key=lambda e: (str(e.relation), e.source_id, e.target_id)
    )):
        relation = RelationType(edge.relation) if not isinstance(edge.relation, RelationType) \
            else edge.relation
        name = RELATION_OF.get(relation)
        if name is None:
            report.omitted_edges[relation.value] += 1
            continue

        source = iri_of_node.get(edge.source_id)
        target = iri_of_node.get(edge.target_id)
        if source is None or target is None:
            # An edge whose ends did not both survive the projection. Counted
            # separately, because this is our bug rather than MIRA's limit.
            report.omitted_edges[f"{relation.value}:dangling"] += 1
            continue

        used_relations.add(name)
        claim: dict[str, Any] = {
            "@id": f"{AOC}edge/{i}",
            "@type": ["RelationInstance", name],
            "source": source,
            "destination": target,
            # A reified relation is a Node, so it can say who asserted it where
            # a bare property could not. `description` is not available for
            # this: its range is an Item, not a string, so the method that
            # drafted the edge is reported rather than emitted.
            "creator": drafter["@id"],
        }
        reified.append(claim)
        report.edges[name] += 1

    for relation, why in NO_MIRA_RELATION.items():
        if report.omitted_edges.get(relation.value):
            report.notes.append(
                f"{report.omitted_edges[relation.value]} {relation.value} edges: {why}"
            )

    # ---- the declarations that make our subtypes legal MIRA -----------------
    schema_defs = [
        {
            "@id": f"{AOC}kind/{kind}",
            "@type": "NodeSchema",
            "subClassOf": [CLASS_OF[ClaimType(kind)]],
            "label": kind,
            **({"created": built_at} if built_at else {}),
        }
        for kind in sorted(used_kinds)
    ]
    relation_defs = [
        {
            "@id": f"{AOC}rel/{name}",
            "@type": "AbstractRelationDef",
            "subClassOf": [name],
            "label": name,
            **({"created": built_at} if built_at else {}),
        }
        for name in sorted(used_relations)
    ]
    # A bare Container, as MIRA's own tooling emits it: its shape permits no
    # properties at all, so it carries none.
    container_nodes = [
        {"@id": iri, "@type": "Container"} for iri in sorted(set(containers.values()))
    ]
    report.nodes["Container"] = len(container_nodes)

    if merged_bylines:
        report.notes.append(
            f"{len(merged_bylines)} byline pairs differ only in punctuation and "
            "were emitted as one account: "
            + "; ".join(f"{a!r}/{b!r}" for a, b in sorted(merged_bylines))
            + ". Worth fixing in the corpus rather than only here."
        )
    accounts.setdefault(_slug(DRAFTED_BY), drafter)
    document = {
        "@context": CONTEXT,
        "@graph": (
            sorted(accounts.values(), key=lambda a: a["@id"])
            + schema_defs
            + relation_defs
            + container_nodes
            + sorted(items, key=lambda i: i["@id"])
            + graph
            + reified
        ),
    }
    report.nodes["UserAccount"] = len(accounts)
    return document, report


def write_mira(
    out_dir: str | Path,
    *,
    built_at: str | None = None,
    **parts: Any,
) -> tuple[Path, Report]:
    """Write `graph.mira.jsonld` and `mira-report.json` into a release.

    Deterministic, like the release writer beside it: the same corpus produces
    byte-identical files, which is what lets CI validate the output against a
    pinned copy of MIRA's shapes and mean something by the result.
    """
    document, report = build_graph(built_at=built_at, **parts)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    graph_path = out / "graph.mira.jsonld"
    graph_path.write_text(
        json.dumps(document, indent=2, ensure_ascii=False, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    (out / "mira-report.json").write_text(
        json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return graph_path, report
