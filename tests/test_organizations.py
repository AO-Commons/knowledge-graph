"""Organization names: fold the variants, keep the distinctions.

The mirror of `test_people.py`, with the risk reversed. A wrong author
merge is hard to notice; a wrong organization merge is easy to notice and
much worse, because putting every DeepMind paper under Google deletes a
distinction the field cares about.
"""

import pytest

from ao_commons_kg.organizations import (
    Registry, apply_index, build_index, fold, load_registry, near_misses, strip_country,
)


class TestFolding:
    def test_a_country_suffix_comes_off(self):
        assert strip_country("Google (United States)") == "Google"
        assert strip_country("DeepMind (United Kingdom)") == "DeepMind"

    def test_one_company_reported_from_two_countries_is_one_organization(self):
        """OpenAlex emits a row per country. Three of the corpus's 55
        organizations were this."""
        names = ["Google (United States)", "Google (United Kingdom)", "Google (United States)"]
        assert len(set(apply_index(names, build_index(names)))) == 1

    def test_a_subsidiary_is_not_its_parent(self):
        """The merge this module exists to refuse."""
        assert fold("Google") != fold("Google DeepMind")
        names = ["Google (United States)", "Google DeepMind (United Kingdom)"]
        assert len(set(apply_index(names, build_index(names)))) == 2

    def test_two_campuses_stay_two(self):
        names = ["University of California, Berkeley", "University of California, Davis"]
        assert len(set(apply_index(names, build_index(names)))) == 2

    def test_a_parenthetical_that_is_not_a_country_is_kept(self):
        """It is carrying meaning, and dropping it would lose the meaning."""
        assert strip_country("Acme (Research Division)") == "Acme (Research Division)"

    def test_accents_do_not_split_an_organization(self):
        assert fold("Université de Montréal") == fold("Universite de Montreal")


class TestNearMisses:
    def test_related_names_are_reported_not_merged(self):
        """A person decides, once, in the alias file. A rule that guessed
        would eventually guess wrong somewhere nobody was looking."""
        pairs = near_misses(["Google", "Google DeepMind", "MIT"])
        assert ("Google", "Google DeepMind") in pairs

    def test_a_publisher_is_not_its_university(self):
        """Found in the live corpus, and correct to keep apart."""
        pairs = near_misses(["Harvard University", "Harvard University Press"])
        assert pairs == [("Harvard University", "Harvard University Press")]


class TestRegistry:
    def test_an_alias_joins_what_a_rule_cannot(self, tmp_path):
        """`DeepMind` and `Google DeepMind` are the same place and no rule
        should infer it. A person writes it down once."""
        path = tmp_path / "orgs.yml"
        path.write_text(
            "organizations:\n"
            "  - canonical: Google DeepMind\n"
            "    aliases: [DeepMind, 'DeepMind Technologies']\n",
            encoding="utf-8")
        registry = load_registry(path)
        assert registry.resolve("DeepMind (United Kingdom)") == "Google DeepMind"
        assert registry.resolve("DeepMind Technologies") == "Google DeepMind"
        # And still not Google.
        assert registry.resolve("Google (United States)") == "Google"

    def test_no_alias_file_is_not_an_error(self, tmp_path):
        assert len(load_registry(tmp_path / "absent.yml")) == 0


class TestTheRealCorpus:
    def test_affiliations_join_to_the_bylines_they_belong_to(self):
        """Affiliation keys are spelled the way the corpus spells the
        person, so they join the people graph rather than starting a second
        identity scheme."""
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
        from ao_commons_kg.people import same_person
        from ao_commons_kg.resources import load_resources

        for resource in load_resources():
            for who in (resource.affiliations or {}):
                assert any(same_person(who, a) for a in resource.authors or []), (
                    f"{resource.id}: affiliation for {who!r}, who is not on the byline")

    def test_no_organization_carries_a_country_suffix(self):
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
        from ao_commons_kg.resources import load_resources

        for resource in load_resources():
            for org in (resource.organizations or []):
                assert org == strip_country(org), f"{resource.id}: unfolded {org!r}"


class TestIdentityCheck:
    """An identifier can point at the wrong paper, and then every fetched
    field is somebody else's. Found in the live corpus."""

    class _Work:
        def __init__(self, title, authors):
            self.title, self.authors = title, authors

    def test_a_matching_title_is_enough(self):
        from ao_commons_kg.organizations import resolves_to_the_same_paper
        assert resolves_to_the_same_paper(
            "Scalable Evaluation of Multi-Agent Reinforcement Learning",
            [], self._Work("Scalable Evaluation of Multi-Agent Reinforcement Learning", []))

    def test_a_retitled_paper_still_matches_on_its_byline(self):
        """Preprint to version of record often changes the title."""
        from ao_commons_kg.organizations import resolves_to_the_same_paper
        assert resolves_to_the_same_paper(
            "Characterizing AI Agents for Alignment and Governance",
            ["Atoosa Kasirzadeh", "Iason Gabriel"],
            self._Work("Agentic profiles for effective AI governance",
                       ["Atoosa Kasirzadeh", "Iason Gabriel"]))

    def test_a_different_paper_entirely_is_refused(self):
        """The real case: this record's DOI belongs to someone else's
        paper, and a backfill that trusted it wrote their institution."""
        from ao_commons_kg.organizations import resolves_to_the_same_paper
        assert not resolves_to_the_same_paper(
            "Multiparty Dynamics and Failure Modes for Machine Learning and AI",
            [], self._Work("Deep Fictitious Play for Stochastic Differential Games",
                           ["Ruimeng Hu"]))

    def test_nothing_to_compare_is_not_a_match(self):
        from ao_commons_kg.organizations import resolves_to_the_same_paper
        assert not resolves_to_the_same_paper("", [], self._Work("", []))
