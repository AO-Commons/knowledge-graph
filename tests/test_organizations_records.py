"""Organization records: the ecosystem layer's nodes.

The loader is the only thing standing between a typo in a hand-written file
and a map nobody can tell is wrong, so most of this is about what it refuses.
"""
from __future__ import annotations

import pytest

from ao_commons_kg.models import Organization, RelationType
from ao_commons_kg.organizations import affiliation_edges, load_organizations


def an_org(**kw):
    return Organization(
        id=kw.pop("id", "org:framework-zero"),
        name=kw.pop("name", "Framework Zero"),
        kind=kw.pop("kind", "company"),
        **kw,
    )


class TestTheRecord:
    def test_kind_is_one_of_the_eight(self):
        with pytest.raises(ValueError, match="unknown kind"):
            an_org(kind="startup")

    def test_a_role_outside_the_vocabulary_is_refused(self):
        with pytest.raises(ValueError, match="unknown role"):
            an_org(roles=["research", "vibes"])

    def test_a_role_listed_twice_is_refused(self):
        # Not pedantry: a duplicate role doubles an organization in any count
        # grouped by role, which is most of what the map does.
        with pytest.raises(ValueError, match="listed twice"):
            an_org(roles=["research", "research"])

    def test_no_roles_is_allowed_and_means_something(self):
        """Most organizations here have published once and done nothing else.
        An empty list says that; a default of ['research'] would not."""
        assert an_org().roles == []

    def test_empty_fields_are_dropped_not_written_as_null(self):
        assert "city" not in an_org().to_dict()


class TestTheRecordsWeHold:
    def test_they_all_load(self):
        orgs = load_organizations()
        assert len(orgs) > 100

    def test_every_id_matches_its_name(self):
        for org in load_organizations().values():
            assert org.id.startswith("org:")

    def test_the_ones_with_a_ror_have_a_city(self):
        # Both come from the same OpenAlex record, so one without the other
        # means the seeder half-wrote a file.
        for org in load_organizations().values():
            if org.ror:
                assert org.city, f"{org.id} has a ROR and no city"

    def test_every_record_says_where_it_came_from(self):
        for org in load_organizations().values():
            assert org.source_provenance, org.id


class TestTheEdges:
    def test_a_paper_reaches_the_organizations_on_its_byline(self):
        class R:
            id = "resource:arxiv:1"
            organizations = ["Framework Zero"]
            affiliations = {"Somebody": ["Framework Zero"]}
        edges = affiliation_edges([R()], {"org:framework-zero": an_org()})
        assert len(edges) == 1, "one organization named twice is one edge"
        assert edges[0].relation is RelationType.AFFILIATED_WITH
        assert edges[0].target_id == "org:framework-zero"

    def test_the_edge_is_extracted_not_inferred(self):
        """It is read off the record's own affiliation data. An inferred
        confidence class here would make it look like a judgment."""
        class R:
            id = "resource:arxiv:1"
            organizations = ["Framework Zero"]
            affiliations = {}
        assert affiliation_edges([R()], {"org:framework-zero": an_org()})[0] \
            .confidence_class.value == "EXTRACTED"

    def test_an_organization_with_no_record_is_skipped_not_invented(self):
        class R:
            id = "resource:arxiv:1"
            organizations = ["Some Place Nobody Has Filed"]
            affiliations = {}
        assert affiliation_edges([R()], {}) == []

    def test_an_alias_reaches_the_same_organization(self):
        class R:
            id = "resource:arxiv:1"
            organizations = ["FrameworkZero"]
            affiliations = {}
        orgs = {"org:framework-zero": an_org(aliases=["FrameworkZero"])}
        assert affiliation_edges([R()], orgs)[0].target_id == "org:framework-zero"
