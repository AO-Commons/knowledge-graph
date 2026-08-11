"""The Airtable Resources table: its definition and its mapping to Resource.

Airtable is the curation surface. Humans add memos, tools, and papers there;
the discovery paths (OpenAlex, Semantic Scholar) add candidates alongside
them; `data/resources/` is the generated mirror. `source_provenance`
distinguishes the two so a hand-checked record is never confused with one a
crawler proposed.

Two things are derived rather than written down, so they cannot drift:

- **Facet options come from `ao_commons_kg.facets`.** Twelve controlled
  vocabularies maintained in one place, not two.
- **Resource type options come from the model.**

This is the same trick the registry uses with its JSON Schema, for the same
reason: a base whose options say "Preprint" while the model says "preprint"
turns the sync into a translation layer nobody maintains.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from ao_commons_kg.facets import FACETS  # noqa: E402
from ao_commons_kg.models import TRISTATE, Resource, ReviewStatus  # noqa: E402

RESOURCES_TABLE = "Resources"
SOURCES_TABLE = "Sources"

PUBLISHED_FIELD = "Published"
SOURCES_LINK_FIELD = "Sources *"
SUPPORTS_FIELD = "Supports"

RESOURCE_TYPES = [
    "peer-reviewed-paper", "preprint", "technical-report", "standard-specification",
    "regulation", "framework-guideline", "dataset", "code-tool", "repository",
    "essay", "governance-proposal", "postmortem", "incident-report", "audit-report",
    "legal-opinion", "talk-interview", "memo",
]

# Airtable field name -> Resource attribute, for values copied unchanged.
SIMPLE_FIELDS = {
    "ID *": "id",
    "Title *": "title",
    "Resource Type *": "resource_type",
    "Description": "description",
    "Abstract": "abstract",
    "Published On": "published_at",
    "Updated On": "updated_at",
    "URL": "url",
    "DOI": "doi",
    "arXiv ID": "arxiv_id",
    "OpenAlex ID": "openalex_id",
    "Semantic Scholar ID": "semantic_scholar_id",
    "Repository URL": "repository_url",
    "License": "license",
    "Review Status *": "review_status",
    "Reviewed By": "reviewed_by",
    "Source Provenance": "source_provenance",
    "Ingested At": "ingested_at",
}

# Comma-separated text -> list. Airtable has no plain list type, and a
# multi-select would impose a closed vocabulary on open-ended values.
COMMA_LIST_FIELDS = {
    "Authors": "authors",
    "Organizations": "organizations",
    "Taxonomy Topics *": "taxonomy_topics",
}

CHECKBOX_FIELDS = {
    "Open Access": "is_open_access",
    "Retracted": "is_retracted",
    "Borrowed Background": "is_borrowed_background",
}

# Airtable field name -> key on the nested tool profile.
TOOL_FIELDS = {
    "Tool: Agent Model": "agent_model",
    "Tool: Human Controls": "human_controls",
    "Tool: Maintainer": "maintainer",
    "Tool: Open Source": "open_source",
    "Tool: Self Hostable": "self_hostable",
    "Tool: Model Agnostic": "model_agnostic",
    "Tool: Status": "status",
}
TOOL_LIST_FIELDS = {
    "Tool: Languages": "languages",
    "Tool: Protocols": "protocols",
    "Tool: Used By": "used_by",
}

# Facet name -> Airtable field name. `F1 Artifact Type` keeps the axis code
# visible in the grid, which is how the taxonomy document refers to them.
FACET_FIELDS = {
    facet.name: f"{facet.code} {facet.name.replace('_', ' ').title()}"
    for facet in FACETS
}

INTERNAL_ONLY = {
    PUBLISHED_FIELD, "Curation State", "Publish Blockers", "Suggested ID", "Notes",
}


def _text(name, description="", multiline=False):
    field = {"name": name, "type": "multilineText" if multiline else "singleLineText"}
    if description:
        field["description"] = description
    return field


def _url(name, description=""):
    field = {"name": name, "type": "url"}
    if description:
        field["description"] = description
    return field


def _checkbox(name, description=""):
    field = {"name": name, "type": "checkbox",
             "options": {"icon": "check", "color": "greenBright"}}
    if description:
        field["description"] = description
    return field


def _select(name, values, multi=False, description=""):
    field = {"name": name, "type": "multipleSelects" if multi else "singleSelect",
             "options": {"choices": [{"name": v} for v in values]}}
    if description:
        field["description"] = description
    return field


REQUIRED = "Required — a record missing this cannot be published."

FACET_DEFINITIONS = [
    _select(
        FACET_FIELDS[facet.name],
        facet.values,
        multi=facet.multi,
        description=f"{facet.question} Options come from the model, not from this base.",
    )
    for facet in FACETS
]

RESOURCE_FIELDS = [
    _text("ID *", f"{REQUIRED} Stable slug — becomes the published filename and the "
                  "citation key. Never change it once published."),
    _text("Title *", REQUIRED),
    _checkbox(PUBLISHED_FIELD, "The sync gate. Unchecked records stay out of the public repo."),
    _select("Resource Type *", RESOURCE_TYPES, description=REQUIRED),
    _text("Description", "One or two neutral sentences. Not the abstract.", multiline=True),
    _text("Abstract", multiline=True),
    _text("Authors", "Comma-separated, in order. Bibliographic authorship only — "
                     "this is not a place for community members or contacts."),
    _text("Organizations", "Comma-separated."),
    _text("Published On", "YYYY, YYYY-MM, or YYYY-MM-DD. Text, not a date, so partial "
                          "precision survives."),
    _text("Updated On"),
    _url("URL"),
    _text("DOI"), _text("arXiv ID"), _text("OpenAlex ID"), _text("Semantic Scholar ID"),
    _url("Repository URL"),
    _text("License"),
    _checkbox("Open Access"), _checkbox("Retracted"),
    _text("Taxonomy Topics *",
          f"{REQUIRED} Comma-separated codes from the v3 taxonomy (e.g. 2.2, 11.3.4). "
          "Validated against the taxonomy file at sync; an unknown code is a curation "
          "error and the record will not publish."),
    _checkbox("Borrowed Background",
              "Section 15 material: relevant by transfer, not about agentic "
              "organizations directly. Excluded from counts of the field's own literature."),
    *FACET_DEFINITIONS,
    # Tools only. Empty on papers, which are the majority.
    _text("Tool: Agent Model",
          "Tools only. How agents participate: managed workers, identity-holding peers, "
          "orchestrated teams. What shape of organization the tool makes possible.",
          multiline=True),
    _text("Tool: Human Controls",
          "Tools only. The oversight primitives it ships — budget caps, approval gates, "
          "pause and terminate, audit trails. If it ships none, say so: that is a finding.",
          multiline=True),
    _text("Tool: Maintainer", "Tools only. The organization behind it, never an individual."),
    _select("Tool: Open Source", sorted(TRISTATE),
            description="Tri-state, so an unresearched tool is never silently recorded "
                        "as proprietary."),
    _select("Tool: Self Hostable", sorted(TRISTATE)),
    _select("Tool: Model Agnostic", sorted(TRISTATE)),
    _text("Tool: Status"),
    _text("Tool: Languages", "Comma-separated."),
    _text("Tool: Protocols", "Comma-separated (nostr, mcp, a2a)."),
    _text("Tool: Used By", "Comma-separated registry slugs of AOs known to run on this."),
    _text("Source Provenance",
          "How this record arrived: hand-curated, or proposed by an OpenAlex or Semantic "
          "Scholar sweep. A crawler's suggestion and a checked record must not look alike."),
    _text("Ingested At"),
    _select("Review Status *", [s.value for s in ReviewStatus],
            description=f"{REQUIRED} PUBLISHED. Whether the taxonomy tags and facets have "
                        "been checked. 'reviewed' means a named human checked them — an "
                        "automated pass does not promote a record. Options come from the "
                        "model."),
    _text("Reviewed By", "Role or handle of the human who checked the tags. Never "
                         "personal contact details."),
    _select("Curation State",
            ["Candidate", "Scope check", "Needs tagging", "Needs sources", "Ready to publish"],
            description="INTERNAL, never published. Where the record sits in the curation "
                        "workflow — deliberately distinct from Review Status, which says "
                        "whether its tags were checked."),
    _text("Notes", "Internal. Never published.", multiline=True),
]

SOURCES_FIELDS = [
    _url("URL *", REQUIRED),
    _text("Title"),
    {"name": "Accessed *", "type": "date",
     "options": {"dateFormat": {"name": "iso", "format": "YYYY-MM-DD"}},
     "description": REQUIRED},
    _text(SUPPORTS_FIELD,
          "Which fields this source is evidence for, comma-separated. What makes a "
          "claim auditable by a reader who doubts it."),
]

TABLES = [
    (RESOURCES_TABLE,
     "The curation surface for the knowledge graph. Rows with Published checked sync to "
     "data/resources/ in AO-Commons/knowledge-graph. Papers, memos, tools, and "
     "deployments all live here — a tool is a resource you consult to decide how to build.",
     RESOURCE_FIELDS),
    (SOURCES_TABLE,
     "Evidence for claims. Shared across records, so one report cited by several "
     "resources is one row.",
     SOURCES_FIELDS),
]

# Fields the Publish Blockers formula checks, as (field, kind, label).
BLOCKERS = [
    ("ID *", "single", "ID"),
    ("Title *", "single", "Title"),
    ("Resource Type *", "single", "ResourceType"),
    ("Taxonomy Topics *", "single", "TaxonomyTopics"),
    ("Review Status *", "single", "ReviewStatus"),
]


def resource_from_row(row: dict, sources_by_id: dict) -> dict:
    """Map one Airtable row onto a Resource-shaped dict."""
    fields = row.get("fields", {})
    out: dict = {}

    for airtable_name, key in SIMPLE_FIELDS.items():
        value = fields.get(airtable_name)
        if value not in (None, ""):
            out[key] = value

    for airtable_name, key in COMMA_LIST_FIELDS.items():
        raw = fields.get(airtable_name)
        if raw:
            out[key] = [part.strip() for part in str(raw).split(",") if part.strip()]

    for airtable_name, key in CHECKBOX_FIELDS.items():
        if airtable_name in fields:
            out[key] = bool(fields[airtable_name])

    facets = {}
    for name, airtable_name in FACET_FIELDS.items():
        value = fields.get(airtable_name)
        if value:
            facets[name] = value if isinstance(value, list) else [value]
    if facets:
        out["facets"] = facets

    tool = {}
    for airtable_name, key in TOOL_FIELDS.items():
        if value := fields.get(airtable_name):
            tool[key] = value
    for airtable_name, key in TOOL_LIST_FIELDS.items():
        if raw := fields.get(airtable_name):
            tool[key] = [p.strip() for p in str(raw).split(",") if p.strip()]
    if tool:
        out["tool"] = tool

    sources = []
    for source_id in fields.get(SOURCES_LINK_FIELD, []):
        source_fields = (sources_by_id.get(source_id) or {}).get("fields", {})
        if not source_fields.get("URL *"):
            continue
        source = {"url": source_fields["URL *"], "accessed": source_fields.get("Accessed *")}
        if title := source_fields.get("Title"):
            source["title"] = title
        if raw := source_fields.get(SUPPORTS_FIELD):
            source["supports"] = [p.strip() for p in str(raw).split(",") if p.strip()]
        sources.append({k: v for k, v in source.items() if v})
    if sources:
        out["sources"] = sorted(sources, key=lambda s: s["url"])

    # The id in Airtable is a bare slug; the graph's ids are namespaced.
    if slug := out.get("id"):
        out["id"] = slug if slug.startswith("resource:") else f"resource:{slug}"

    return out


def validate_definition() -> list[str]:
    """Check the table definition against the model it feeds."""
    problems = []
    names = [field["name"] for field in RESOURCE_FIELDS]
    if len(names) != len(set(names)):
        problems.append("duplicate field names in the Resources table")

    attributes = set(Resource.__dataclass_fields__)
    for airtable_name, key in {**SIMPLE_FIELDS, **COMMA_LIST_FIELDS, **CHECKBOX_FIELDS}.items():
        if key not in attributes:
            problems.append(f"{airtable_name} maps to {key!r}, which Resource does not have")
        if airtable_name not in names:
            problems.append(f"{airtable_name} is mapped but not defined in the table")

    for facet_name, airtable_name in FACET_FIELDS.items():
        if airtable_name not in names:
            problems.append(f"facet {facet_name} has no field {airtable_name!r}")

    for name, _, _ in BLOCKERS:
        if name not in names:
            problems.append(f"Publish Blockers checks {name!r}, which is not a field")
        if not name.endswith(" *"):
            problems.append(f"{name!r} is checked as required but is not marked with *")

    starred = {n for n in names if n.endswith(" *")} | {SOURCES_LINK_FIELD}
    checked = {n for n, _, _ in BLOCKERS} | {SOURCES_LINK_FIELD}
    if starred != checked:
        problems.append(
            f"starred fields and Publish Blockers disagree: "
            f"starred-only {sorted(starred - checked)}, checked-only {sorted(checked - starred)}"
        )
    return problems


def row_from_resource(resource, source_ids: dict[str, str]) -> dict:
    """The inverse of resource_from_row: a Resource as Airtable fields.

    Used only to seed the base from records curated in the repo. Once a
    record is in Airtable, Airtable is where it is edited — this direction
    is for filling an empty table, not for keeping two copies in step.
    """
    payload = resource.to_dict()
    fields: dict = {}

    for airtable_name, key in SIMPLE_FIELDS.items():
        if (value := payload.get(key)) not in (None, ""):
            # Airtable holds the bare slug; the graph namespaces it.
            fields[airtable_name] = (
                value.removeprefix("resource:") if key == "id" else value
            )

    for airtable_name, key in COMMA_LIST_FIELDS.items():
        if values := payload.get(key):
            fields[airtable_name] = ", ".join(values)

    for airtable_name, key in CHECKBOX_FIELDS.items():
        if key in payload:
            fields[airtable_name] = bool(payload[key])

    for name, airtable_name in FACET_FIELDS.items():
        if values := (payload.get("facets") or {}).get(name):
            facet = next(f for f in FACETS if f.name == name)
            fields[airtable_name] = list(values) if facet.multi else values[0]

    tool = payload.get("tool") or {}
    for airtable_name, key in TOOL_FIELDS.items():
        if value := tool.get(key):
            fields[airtable_name] = value
    for airtable_name, key in TOOL_LIST_FIELDS.items():
        if values := tool.get(key):
            fields[airtable_name] = ", ".join(values)

    if links := [source_ids[s["url"]] for s in payload.get("sources", [])
                 if s.get("url") in source_ids]:
        fields[SOURCES_LINK_FIELD] = links

    # These records are already published in the repo; the base should say so
    # rather than presenting a live corpus as a pile of drafts.
    fields[PUBLISHED_FIELD] = True
    return fields
