"""Curated resources, including the tools folded in from the registry.

Runs against the real files in data/resources/, so a migration that produces
records the model rejects fails here rather than at release time.
"""

import pytest

from ao_commons_kg.models import Resource, ToolProfile
from ao_commons_kg.resources import (
    ResourceError,
    load_resources,
    tagged_edges,
    unknown_tags,
)
from ao_commons_kg.taxonomy import load_taxonomy
from tests.test_taxonomy import TAXONOMY


@pytest.fixture(scope="module")
def resources():
    return load_resources()


@pytest.fixture(scope="module")
def topic_codes():
    return {topic.code for topic in load_taxonomy(TAXONOMY)}


def test_curated_resources_load(resources):
    assert resources, "data/resources/ should not be empty"


def test_every_tag_resolves_to_a_real_topic(resources, topic_codes):
    """A dangling tag is an edge to nowhere that nobody notices."""
    assert unknown_tags(resources, topic_codes) == {}


def test_tools_kept_their_substance(resources):
    """The fold from the registry must not quietly drop the fields that made
    a tool entry worth having."""
    paperclip = next(r for r in resources if r.id == "resource:tool:paperclip")
    assert paperclip.resource_type == "code-tool"
    assert paperclip.license == "MIT"
    assert paperclip.tool.open_source == "yes"
    assert paperclip.tool.maintainer == "Paperclip Labs, Inc."
    assert "board of directors" in paperclip.tool.agent_model
    assert "budget" in paperclip.tool.human_controls.lower()
    assert len(paperclip.sources) >= 3, "evidence must survive the migration"


def test_tool_profiles_only_on_tool_types():
    with pytest.raises(ValueError, match="tool profile on resource_type"):
        Resource(id="r", resource_type="peer-reviewed-paper", title="T",
                 tool=ToolProfile(maintainer="Someone"))


def test_tristate_fields_reject_booleans_in_disguise():
    """Tri-state exists so an unresearched tool is never recorded as
    proprietary by omission."""
    with pytest.raises(ValueError, match="expected one of"):
        ToolProfile(open_source="true")
    assert ToolProfile(open_source="unknown").open_source == "unknown"


def test_tool_dict_is_coerced_from_yaml():
    resource = Resource(id="r", resource_type="code-tool", title="T",
                        tool={"maintainer": "X", "open_source": "partial"})
    assert isinstance(resource.tool, ToolProfile)
    assert resource.to_dict()["tool"] == {"maintainer": "X", "open_source": "partial"}


def test_tag_edges_are_marked_curated(resources, topic_codes):
    edges = tagged_edges(resources, topic_codes)
    assert edges
    for edge in edges:
        assert edge.confidence_class.value == "EXTRACTED"
        assert edge.extraction_method == "curated"
        assert edge.target_id.startswith("topic:")


def test_filename_must_follow_from_the_id(tmp_path):
    """So a record can be found from a citation without an index."""
    (tmp_path / "wrong-name.yml").write_text(
        "id: resource:tool:buzz\nresource_type: code-tool\ntitle: Buzz\n"
    )
    with pytest.raises(ResourceError, match="implies tool-buzz.yml"):
        load_resources(tmp_path)


def test_bad_facet_fails_the_load_not_the_release(tmp_path):
    (tmp_path / "thing.yml").write_text(
        "id: resource:thing\nresource_type: essay\ntitle: T\n"
        "facets:\n  evidence_strength: vibes\n"
    )
    with pytest.raises(ResourceError, match="no value"):
        load_resources(tmp_path)


def test_missing_directory_is_empty_not_an_error(tmp_path):
    assert load_resources(tmp_path / "absent") == []
