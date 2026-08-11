"""The seam between the Airtable table, the mapping, and the Resource model.

These are the failures that raise nothing when they happen: a facet renamed
in the model but not the base, a field mapped to an attribute that no longer
exists, a select option capitalized differently. They produce records that
quietly fail to load, or worse, load with a field silently empty.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import airtable_schema as schema  # noqa: E402

from ao_commons_kg.facets import BY_NAME, FACETS  # noqa: E402
from ao_commons_kg.models import Resource  # noqa: E402

FIELDS = {f["name"]: f for f in schema.RESOURCE_FIELDS}


def test_definition_agrees_with_the_model():
    """Every mapped field exists, and maps to something Resource has."""
    assert schema.validate_definition() == []


def test_facet_options_equal_the_model_vocabulary():
    """Not 'compatible with' — equal. Anything else makes the sync a
    translation layer, and translation layers rot."""
    for facet in FACETS:
        field = FIELDS[schema.FACET_FIELDS[facet.name]]
        assert [c["name"] for c in field["options"]["choices"]] == list(facet.values), (
            f"{facet.code} options drifted"
        )


def test_single_valued_facets_are_single_select():
    """A multi-select on a single-valued axis would let the base record a
    combination the model rejects."""
    for facet in FACETS:
        field = FIELDS[schema.FACET_FIELDS[facet.name]]
        expected = "multipleSelects" if facet.multi else "singleSelect"
        assert field["type"] == expected, f"{facet.code} is the wrong select type"


def test_every_facet_has_a_field():
    assert set(schema.FACET_FIELDS) == set(BY_NAME)


def test_internal_fields_are_not_mapped():
    """Nothing a maintainer writes for themselves should reach the graph."""
    mapped = set(schema.SIMPLE_FIELDS) | set(schema.COMMA_LIST_FIELDS) | set(schema.CHECKBOX_FIELDS)
    assert not (mapped & schema.INTERNAL_ONLY)


def test_row_maps_to_a_valid_resource():
    row = {
        "id": "recAAAAAAAAAAAAAA",
        "fields": {
            "ID *": "arxiv:2502.14143",
            "Title *": "Multi-Agent Risks from Advanced AI",
            "Resource Type *": "preprint",
            "Authors": "Lewis Hammond, Alan Chan, Joel Z. Leibo",
            "Published On": "2025-02-19",
            "arXiv ID": "2502.14143",
            "Taxonomy Topics *": "11.1, 11.6, 11.13",
            "F1 Artifact Type": "preprint",
            "F7 Control Type": ["technical", "procedural"],
            "Open Access": True,
            "Retracted": False,
            "Published": True,
            "Notes": "INTERNAL — must not be published",
            schema.SOURCES_LINK_FIELD: ["recS1"],
        },
    }
    sources = {"recS1": {"id": "recS1", "fields": {
        "URL *": "https://arxiv.org/abs/2502.14143", "Accessed *": "2026-08-11",
        "Supports": "taxonomy_topics"}}}

    payload = schema.resource_from_row(row, sources)
    resource = Resource(**payload)

    assert resource.id == "resource:arxiv:2502.14143", "ids are namespaced on the way in"
    assert resource.authors == ["Lewis Hammond", "Alan Chan", "Joel Z. Leibo"]
    assert resource.taxonomy_topics == ["11.1", "11.6", "11.13"]
    assert resource.facets["control_type"] == ["technical", "procedural"]
    assert resource.facets["artifact_type"] == ["preprint"]
    assert resource.is_open_access is True
    assert resource.is_retracted is False, "false is a claim, not an absence"
    assert len(resource.sources) == 1
    assert "INTERNAL" not in str(resource.to_dict())


def test_tool_fields_become_a_tool_profile():
    row = {"id": "recB", "fields": {
        "ID *": "tool:paperclip", "Title *": "Paperclip", "Resource Type *": "code-tool",
        "Taxonomy Topics *": "2.2",
        "Tool: Maintainer": "Paperclip Labs, Inc.",
        "Tool: Open Source": "yes",
        "Tool: Languages": "TypeScript, JavaScript",
        "Tool: Human Controls": "Budget caps that pause execution.",
    }}
    resource = Resource(**schema.resource_from_row(row, {}))
    assert resource.tool.maintainer == "Paperclip Labs, Inc."
    assert resource.tool.open_source == "yes"
    assert resource.tool.languages == ["TypeScript", "JavaScript"]


def test_a_row_with_no_tool_fields_gets_no_profile():
    row = {"id": "recC", "fields": {
        "ID *": "arxiv:1", "Title *": "A paper", "Resource Type *": "preprint"}}
    assert Resource(**schema.resource_from_row(row, {})).tool is None


def test_bad_facet_value_fails_the_row():
    row = {"id": "recD", "fields": {
        "ID *": "x", "Title *": "T", "Resource Type *": "essay",
        "F2 Evidence Strength": "vibes"}}
    with pytest.raises(ValueError, match="no value"):
        Resource(**schema.resource_from_row(row, {}))


def test_resource_types_cover_what_the_corpus_holds():
    """A type the model uses but the base cannot express would be a record
    nobody can curate."""
    for used in ("preprint", "code-tool", "peer-reviewed-paper", "memo"):
        assert used in schema.RESOURCE_TYPES


def test_review_status_options_come_from_the_model():
    from ao_commons_kg.models import ReviewStatus
    field = FIELDS["Review Status *"]
    assert [c["name"] for c in field["options"]["choices"]] == [s.value for s in ReviewStatus]


def test_review_status_is_published_and_curation_state_is_not():
    """Two fields with 'review' in the name is a trap, so they are named
    apart and only one of them reaches the graph."""
    assert "Review Status *" in schema.SIMPLE_FIELDS
    assert "Curation State" in schema.INTERNAL_ONLY
    assert "Curation State" not in schema.SIMPLE_FIELDS
    assert not (set(schema.SIMPLE_FIELDS) & schema.INTERNAL_ONLY)


def test_review_status_gates_publication():
    """A record cannot publish without saying whether its tags were checked."""
    assert any(name == "Review Status *" for name, _, _ in schema.BLOCKERS)


# --- Seeding the base from the repo -----------------------------------------

def test_a_resource_round_trips_through_airtable():
    """push then sync must not change a record. If the two mappings disagree,
    seeding the base silently rewrites the corpus."""
    from ao_commons_kg.resources import load_resources

    for original in load_resources():
        row = schema.row_from_resource(original, {})
        # Airtable hands back exactly what it was given, plus the record id.
        returned = Resource(**schema.resource_from_row({"id": "rec", "fields": row}, {}))

        assert returned.id == original.id
        assert returned.title == original.title
        assert returned.resource_type == original.resource_type
        assert returned.taxonomy_topics == original.taxonomy_topics
        assert returned.facets == original.facets
        assert returned.authors == original.authors
        assert returned.review_status is original.review_status
        if original.tool:
            assert returned.tool.maintainer == original.tool.maintainer
            assert returned.tool.used_by == original.tool.used_by


def test_push_marks_records_published():
    """They are already live in the repo; the base should say so rather than
    presenting a published corpus as a pile of drafts."""
    from ao_commons_kg.resources import load_resources
    row = schema.row_from_resource(load_resources()[0], {})
    assert row[schema.PUBLISHED_FIELD] is True


def test_push_strips_the_id_namespace():
    from ao_commons_kg.models import Resource as R
    row = schema.row_from_resource(R(id="resource:arxiv:1", resource_type="preprint",
                                     title="T"), {})
    assert row["ID *"] == "arxiv:1", "Airtable holds the bare slug"


def test_push_links_sources_it_has_ids_for():
    from ao_commons_kg.models import Resource as R
    resource = R(id="resource:x", resource_type="preprint", title="T",
                 sources=[{"url": "https://example.org/a", "accessed": "2026-08-11"}])
    row = schema.row_from_resource(resource, {"https://example.org/a": "recS1"})
    assert row[schema.SOURCES_LINK_FIELD] == ["recS1"]
