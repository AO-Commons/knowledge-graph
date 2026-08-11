"""The invariants that keep the graph trustworthy.

Mostly one idea: a reader must always be able to tell what an edge is based
on. Deterministic metadata, a computed score, and a model's inference are
three different claims, and the schema refuses to let them look alike.
"""

import pytest

from ao_commons_kg.facets import FacetError
from ao_commons_kg.models import (
    ConfidenceClass,
    Entity,
    RelationType,
    Relationship,
    Resource,
    Topic,
)


def topic(code="2.2.1", **kwargs):
    return Topic(code=code, title="A topic", taxonomy_version="v3", **kwargs)


class TestTopic:
    def test_parent_and_section_derive_from_the_code(self):
        assert topic("2.2.1").parent_code == "2.2"
        assert topic("2.2.1").top_level_section == "2"
        assert topic("7").parent_code is None

    def test_a_parent_contradicting_the_code_is_rejected(self):
        """The code is the hierarchy; letting them disagree would make
        browsing and ancestor rollup diverge."""
        with pytest.raises(ValueError, match="contradicts the code"):
            topic("2.2.1", parent_code="3.1")

    def test_non_numeric_codes_are_rejected(self):
        with pytest.raises(ValueError, match="dotted-numeric"):
            Topic(code="2.2.a", title="x", taxonomy_version="v3")


class TestResource:
    def test_facets_are_normalized_to_lists(self):
        resource = Resource(
            id="resource:1", resource_type="paper", title="T",
            facets={"artifact_type": "preprint", "control_type": ["technical", "legal"]},
        )
        assert resource.facets["artifact_type"] == ["preprint"]
        assert resource.facets["control_type"] == ["technical", "legal"]

    def test_unknown_facet_value_is_rejected(self):
        """A typo that passed silently would produce a resource no filter
        ever matches — invisible rather than merely wrong."""
        with pytest.raises(FacetError, match="no value"):
            Resource(id="r", resource_type="paper", title="T",
                     facets={"evidence_strength": "vibes"})

    def test_unknown_facet_name_is_rejected(self):
        with pytest.raises(FacetError, match="unknown facet"):
            Resource(id="r", resource_type="paper", title="T", facets={"F99": "x"})

    def test_single_valued_facet_rejects_two_values(self):
        with pytest.raises(FacetError, match="single value"):
            Resource(id="r", resource_type="paper", title="T",
                     facets={"artifact_type": ["preprint", "essay"]})

    def test_taxonomy_tags_must_be_topic_codes(self):
        with pytest.raises(ValueError, match="not a topic code"):
            Resource(id="r", resource_type="paper", title="T",
                     taxonomy_topics=["delegation chains"])

    def test_export_drops_empties_but_keeps_false(self):
        """`is_retracted: false` is a claim; an empty list is just absence."""
        payload = Resource(id="r", resource_type="paper", title="T",
                           is_retracted=False).to_dict()
        assert payload["is_retracted"] is False
        assert "authors" not in payload


class TestEntity:
    def test_unknown_entity_type_is_rejected(self):
        with pytest.raises(ValueError, match="unknown entity_type"):
            Entity(id="e", entity_type="thingamajig", name="X")


class TestRelationship:
    def test_citation_needs_no_confidence(self):
        edge = Relationship("resource:a", "resource:b", RelationType.CITES)
        assert edge.confidence_class is None

    def test_labelling_a_citation_with_confidence_is_rejected(self):
        """It implies a judgement that was never made."""
        with pytest.raises(ValueError, match="never made"):
            Relationship("resource:a", "resource:b", RelationType.CITES,
                         confidence_class=ConfidenceClass.INFERRED)

    def test_inferred_edges_must_declare_themselves(self):
        with pytest.raises(ValueError, match="non-deterministic"):
            Relationship("resource:a", "entity:x", RelationType.PROPOSES)

        edge = Relationship("resource:a", "entity:x", RelationType.PROPOSES,
                            confidence_class=ConfidenceClass.EXTRACTED,
                            source_resource_id="resource:a",
                            source_location="§3.2")
        assert edge.confidence_class is ConfidenceClass.EXTRACTED

    def test_similarity_must_show_its_method_and_score(self):
        """A similarity score whose method is hidden cannot be interpreted
        or reproduced."""
        with pytest.raises(ValueError, match="method"):
            Relationship("resource:a", "resource:b", RelationType.SIMILAR_TO, score=0.4)
        with pytest.raises(ValueError, match="score"):
            Relationship("resource:a", "resource:b", RelationType.SIMILAR_TO,
                         method="bibliographic-coupling")

        edge = Relationship("resource:a", "resource:b", RelationType.SIMILAR_TO,
                            method="bibliographic-coupling", score=0.42)
        assert edge.to_dict()["method"] == "bibliographic-coupling"

    def test_confidence_score_is_bounded(self):
        with pytest.raises(ValueError, match="outside 0..1"):
            Relationship("resource:a", "entity:x", RelationType.DISCUSSES,
                         confidence_class=ConfidenceClass.INFERRED, confidence_score=4.2)

    def test_relation_accepts_a_plain_string(self):
        assert Relationship("a", "b", "CITES").relation is RelationType.CITES
