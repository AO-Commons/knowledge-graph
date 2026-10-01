"""Who made the library, read from what the records already say.

The principles these tests hold the ledger to are Rennie and Potts' (2025),
for contribution systems: credit follows dependencies upstream, use is
recomputed rather than frozen, recognition is legible to the people
recognized, and machine contributions are recorded but kept apart.
"""

import json
from pathlib import Path

from ao_commons_kg.contributions import KINDS, collect, load_ledger, summarize
from ao_commons_kg.models import Claim, Resource
from ao_commons_kg.people import Identity

ROOT = Path(__file__).resolve().parent.parent


def _paper(rid="resource:arxiv:1", authors=("Ada Lovelace",), provenance=None):
    return Resource(id=rid, resource_type="preprint", title="A paper",
                    authors=list(authors), source_provenance=provenance)


def _claim(cid="claim:arxiv:1:1", rid="resource:arxiv:1"):
    return Claim(id=cid, resource_id=rid, text="t", quote="q",
                 extraction_method="claude-opus-5, drafted from the abstract, 2026-09-12")


HELENA = {"helenarong2703": Identity(name="Ada Lovelace", github="helenarong2703",
                                     link_status="verified", verified_by="ankeliu",
                                     verified_how="confirmed 2026-09-10")}


class TestCreditFollowsDependencies:
    def test_the_authors_of_a_paper_are_credited(self):
        ledger = collect(resources=[_paper()], claims=[])
        assert [(c.contributor, c.kind) for c in ledger.contributions] == [
            ("Ada Lovelace", "wrote")]

    def test_a_verdict_builds_on_the_statement_it_judged(self):
        ledger = collect(resources=[_paper()], claims=[_claim()],
                         gold_claims={"claim:arxiv:1:1": {"reviewer": "someone",
                                                          "reviewed_on": "2026-09-18"}})
        verdict = next(c for c in ledger.contributions if c.kind == "reviewed-statement")
        assert verdict.builds_on == ("claim:arxiv:1:1",)

    def test_a_draft_builds_on_the_paper(self):
        ledger = collect(resources=[_paper()], claims=[_claim()])
        draft = next(c for c in ledger.contributions if c.kind == "drafted")
        assert draft.builds_on == ("resource:arxiv:1",) and draft.machine


class TestUseIsRecomputed:
    def test_a_paper_is_used_by_what_cites_it_and_what_is_drawn_from_it(self):
        ledger = collect(resources=[_paper(), _paper("resource:arxiv:2", ("B",))],
                         claims=[_claim()], citations=[("resource:arxiv:2", "resource:arxiv:1")])
        assert ledger.used_by["resource:arxiv:1"] == {
            "cited by records": 1, "statements drawn from it": 1}


class TestOnePersonAcrossRoles:
    def test_a_verified_reviewer_meets_their_own_byline(self):
        """Without the link, an author's reviews and papers would belong to two
        contributors who never meet."""
        ledger = collect(resources=[_paper()], claims=[_claim()], identities=HELENA,
                         gold_claims={"claim:arxiv:1:1": {"reviewer": "helenarong2703"}})
        kinds = {c.kind for c in ledger.contributions if c.contributor == "Ada Lovelace"}
        assert {"wrote", "reviewed-statement"} <= kinds
        verdict = next(c for c in ledger.contributions if c.kind == "reviewed-statement")
        assert verdict.by_author

    def test_an_unverified_login_is_not_joined_on_a_guess(self):
        ledger = collect(resources=[_paper()], claims=[_claim()],
                         gold_claims={"claim:arxiv:1:1": {"reviewer": "adalovelace"}})
        verdict = next(c for c in ledger.contributions if c.kind == "reviewed-statement")
        assert verdict.contributor == "@adalovelace" and not verdict.by_author

    def test_a_proposer_is_read_from_the_record_s_provenance(self):
        paper = _paper(provenance="added automatically from issue #54 by @someone; resolved")
        ledger = collect(resources=[paper], claims=[])
        assert ("@someone", "proposed") in {(c.contributor, c.kind) for c in ledger.contributions}


class TestMachinesAreKeptApart:
    def test_a_machine_relation_is_a_machine_s(self):
        ledger = collect(resources=[], claims=[], relations=[{
            "source": "a", "target": "b", "relation": "SUPPORTS",
            "asserted_by": "claude-opus-5 (drafted, unconfirmed)"}])
        (relation,) = ledger.contributions
        assert relation.machine and relation.contributor == "claude-opus-5"

    def test_no_machine_is_listed_as_a_person(self):
        summary = summarize(load_ledger())
        people = {p["contributor"] for p in summary["people"]}
        assert not any(name.startswith("claude") or name == "citation expansion"
                       for name in people)
        assert {m["contributor"] for m in summary["machines"]} >= {"citation expansion"}


class TestRecognitionIsLegible:
    def test_nothing_is_scored_weighted_or_ranked(self):
        text = json.dumps(summarize(load_ledger())).lower()
        for word in ('"score"', '"weight"', '"rank"', '"value"'):
            assert word not in text

    def test_people_are_listed_by_name_not_by_count(self):
        names = [p["contributor"] for p in summarize(load_ledger())["people"]]
        assert names == sorted(names)

    def test_every_contribution_names_a_file_that_exists(self):
        for c in load_ledger().contributions:
            assert c.source.endswith("/") or (ROOT / c.source).exists(), c

    def test_every_kind_is_explained(self):
        assert {c.kind for c in load_ledger().contributions} <= set(KINDS)


class TestTheRealLedger:
    def test_the_authors_who_reviewed_their_own_papers_are_recorded_as_authors(self):
        verdicts = [c for c in load_ledger().contributions if c.kind == "reviewed-statement"]
        by_author = {c.contributor for c in verdicts if c.by_author}
        assert {"Helena Rong", "Axel Backlund"} <= by_author
