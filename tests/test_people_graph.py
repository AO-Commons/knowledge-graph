"""People as nodes: derived from bylines, corrected by the overlay."""
from __future__ import annotations

from ao_commons_kg.models import RelationType
from ao_commons_kg.people import (authorship_edges, fold, person_nodes,
                                  slug_for_person)


class R:
    def __init__(self, rid, authors, affiliations=None):
        self.id, self.authors = rid, authors
        self.affiliations = affiliations or {}
        self.organizations = []


class TestFolding:
    def test_a_hyphen_is_a_space(self):
        """Folding it away made "Joon-Sung Park" into "joonsung park", which
        never meets "Joon Sung Park". Two people in the corpus were two
        people twice."""
        assert fold("Joon-Sung Park") == fold("Joon Sung Park")
        assert fold("Sheer El-Showk") == fold("Sheer El Showk")

    def test_an_apostrophe_still_vanishes(self):
        # "O'Brien" is not "O Brien" in any source that matters.
        assert fold("O'Brien") == "obrien"

    def test_accents_still_fold_and_initials_still_do_not(self):
        assert fold("Duéñez-Guzmán") == fold("Duenez-Guzman")
        assert fold("J. Leibo") != fold("Joel Z. Leibo")

    def test_two_spellings_reach_one_id(self):
        assert slug_for_person("Joon-Sung Park") == slug_for_person("Joon Sung Park")


class TestTheNodes:
    def test_a_byline_becomes_a_person(self):
        people = person_nodes([R("r:1", ["Ada Lovelace"])])
        assert [p.name for p in people.values()] == ["Ada Lovelace"]

    def test_two_spellings_become_one_person_with_an_alias(self):
        people = person_nodes([R("r:1", ["Joon-Sung Park"]), R("r:2", ["Joon Sung Park"])])
        assert len(people) == 1
        person = next(iter(people.values()))
        assert person.aliases, "the spelling that lost should be kept as an alias"

    def test_the_overlay_supplies_the_account(self):
        class Identity:
            name, github, orcid, attestation = "Ada Lovelace", "ada", None, "vouched"
        people = person_nodes([R("r:1", ["Ada Lovelace"])], {"ada": Identity()})
        person = next(iter(people.values()))
        assert person.github == "ada" and person.attestation == "vouched"

    def test_someone_with_no_overlay_is_still_a_person(self):
        person = next(iter(person_nodes([R("r:1", ["Ada Lovelace"])]).values()))
        assert person.github is None and "github" not in person.to_dict()


class TestTheEdges:
    def test_a_byline_authors_its_paper(self):
        people = person_nodes([R("r:1", ["Ada Lovelace"])])
        edges = authorship_edges([R("r:1", ["Ada Lovelace"])], people)
        assert [e.relation for e in edges] == [RelationType.AUTHORED]

    def test_affiliation_runs_from_the_person_not_the_paper(self):
        """A paper reaches an organization through its authors. Storing the
        paper edge too would store something derivable, and it cannot hold the
        case this one can: the same person at two organizations."""
        class Org:
            id, name, aliases = "org:x", "X Lab", []
        rs = [R("r:1", ["Ada Lovelace"], {"Ada Lovelace": ["X Lab"]})]
        edges = authorship_edges(rs, person_nodes(rs), {"org:x": Org()})
        aff = [e for e in edges if e.relation is RelationType.AFFILIATED_WITH]
        assert len(aff) == 1
        assert aff[0].source_id.startswith("person:")
        assert aff[0].target_id == "org:x"

    def test_one_person_at_two_organizations_is_two_edges(self):
        class Org:
            def __init__(s, i, n): s.id, s.name, s.aliases = i, n, []
        rs = [R("r:1", ["Ada"], {"Ada": ["A Lab"]}), R("r:2", ["Ada"], {"Ada": ["B Lab"]})]
        orgs = {"org:a": Org("org:a", "A Lab"), "org:b": Org("org:b", "B Lab")}
        edges = authorship_edges(rs, person_nodes(rs), orgs)
        assert len([e for e in edges if e.relation is RelationType.AFFILIATED_WITH]) == 2

    def test_an_unfiled_organization_is_skipped_not_invented(self):
        rs = [R("r:1", ["Ada"], {"Ada": ["Nowhere"]})]
        edges = authorship_edges(rs, person_nodes(rs), {})
        assert not [e for e in edges if e.relation is RelationType.AFFILIATED_WITH]
