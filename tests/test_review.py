"""The review loop that produces a gold set.

The interactive shell is thin on purpose; selection, parsing, persistence and
scoring are separated out so the parts that decide what gets measured are
testable without a terminal.
"""

from dataclasses import dataclass, field

import pytest

from ao_commons_kg.review import (
    GoldSet,
    agreement,
    parse_decision,
    select_for_review,
)


@dataclass
class FakeResource:
    id: str
    taxonomy_topics: list[str] = field(default_factory=list)
    abstract: str | None = None
    title: str = "T"


@dataclass
class FakeAssignment:
    code: str


CANDIDATES = [FakeAssignment("2.2"), FakeAssignment("3.1"), FakeAssignment("11.6")]


class TestGoldSet:
    def test_round_trips(self, tmp_path):
        gold = GoldSet.load(tmp_path / "tags.yml")
        gold.reviewer = "anke"
        gold.record("resource:a", ["3.1", "2.2"], note="borderline")
        gold.save()

        reloaded = GoldSet.load(tmp_path / "tags.yml")
        assert reloaded.reviewer == "anke"
        assert reloaded.entries["resource:a"]["topics"] == ["2.2", "3.1"], "sorted numerically"
        assert reloaded.entries["resource:a"]["note"] == "borderline"
        assert reloaded.entries["resource:a"]["reviewed_on"]

    def test_topics_sort_numerically_not_lexically(self):
        """`11.6` after `2.2`, not before it."""
        gold = GoldSet(path=None)
        gold.record("r", ["11.6", "2.2", "3.10", "3.2"])
        assert gold.entries["r"]["topics"] == ["2.2", "3.2", "3.10", "11.6"]

    def test_recording_no_topics_is_a_real_answer(self):
        """"None of these apply" is a judgement worth keeping — it says the
        record is out of scope or the taxonomy has a gap."""
        gold = GoldSet(path=None)
        gold.record("r", [])
        assert "r" in gold and gold.entries["r"]["topics"] == []

    def test_missing_file_starts_empty(self, tmp_path):
        assert GoldSet.load(tmp_path / "absent.yml").entries == {}


class TestSelection:
    def test_already_reviewed_records_are_not_offered_again(self):
        gold = GoldSet(path=None)
        gold.record("resource:a", ["2.2"])
        pool = [FakeResource("resource:a", ["2.2"]), FakeResource("resource:b", ["2.2"])]
        assert [r.id for r in select_for_review(pool, gold, limit=10)] == ["resource:b"]

    def test_the_sample_is_stratified_across_sections(self):
        """Reviewing whatever comes first would measure one corner of the
        corpus and report it as the whole."""
        pool = [FakeResource(f"resource:a{i}", ["2.2"]) for i in range(10)]
        pool += [FakeResource("resource:b", ["11.6"]), FakeResource("resource:c", ["16.1"])]

        chosen = select_for_review(pool, GoldSet(path=None), limit=4)
        sections = {r.taxonomy_topics[0].split(".")[0] for r in chosen}
        assert sections == {"2", "11", "16"}, "a big section cannot crowd out small ones"

    def test_records_with_abstracts_come_first(self):
        """A reviewer cannot fairly judge a record from its title alone."""
        pool = [
            FakeResource("resource:bare", ["2.2"]),
            FakeResource("resource:full", ["2.2"], abstract="An abstract."),
        ]
        assert select_for_review(pool, GoldSet(path=None), limit=1)[0].id == "resource:full"

    def test_selection_respects_the_limit(self):
        pool = [FakeResource(f"r{i}", ["2.2"]) for i in range(20)]
        assert len(select_for_review(pool, GoldSet(path=None), limit=5)) == 5


class TestDecisions:
    @pytest.mark.parametrize("raw,expected", [
        ("1 3", ["2.2", "11.6"]),
        ("1,3", ["2.2", "11.6"]),
        ("  2 ", ["3.1"]),
    ])
    def test_numbers_select_candidates_however_they_are_separated(self, raw, expected):
        """Being pedantic about separators would slow the only part of this
        that costs human time."""
        assert parse_decision(raw, CANDIDATES).topics == expected

    def test_codes_can_be_entered_directly(self):
        decision = parse_decision("c 7.2, 9.1", CANDIDATES)
        assert decision.action == "accept" and decision.topics == ["7.2", "9.1"]

    def test_search_is_recognised(self):
        decision = parse_decision("/delegation revocation", CANDIDATES)
        assert decision.action == "search" and decision.query == "delegation revocation"

    def test_none_records_an_empty_decision_rather_than_skipping(self):
        assert parse_decision("n", CANDIDATES) == parse_decision("none", CANDIDATES)
        assert parse_decision("n", CANDIDATES).action == "accept"

    def test_skip_and_quit_are_distinct(self):
        assert parse_decision("s", CANDIDATES).action == "skip"
        assert parse_decision("q", CANDIDATES).action == "quit"

    def test_empty_input_skips_rather_than_recording_nothing(self):
        """Pressing return by accident must not assert that no topic applies."""
        assert parse_decision("", CANDIDATES).action == "skip"

    def test_out_of_range_numbers_are_ignored(self):
        assert parse_decision("99", CANDIDATES).action == "skip"


class TestAgreement:
    def test_scoring_is_hierarchy_aware(self):
        """Predicting `2.2.2` where the reviewer said `2.2` is the same
        branch, more specific — not a miss."""
        gold = GoldSet(path=None)
        gold.record("r", ["2.2"])
        assert agreement(gold, {"r": ["2.2.2"]})["recall"] == 1.0

    def test_a_parent_prediction_also_counts(self):
        gold = GoldSet(path=None)
        gold.record("r", ["2.2.2"])
        assert agreement(gold, {"r": ["2.2"]})["recall"] == 1.0

    def test_a_different_branch_is_a_miss(self):
        gold = GoldSet(path=None)
        gold.record("r", ["2.2"])
        assert agreement(gold, {"r": ["11.6"]})["recall"] == 0.0

    def test_exact_matches_are_counted_separately(self):
        gold = GoldSet(path=None)
        gold.record("r", ["2.2"])
        scores = agreement(gold, {"r": ["2.2.2"]})
        assert scores["recovered"] == 1 and scores["exact"] == 0

    def test_records_reviewed_as_out_of_scope_do_not_skew_recall(self):
        """A record the reviewer tagged with nothing has no gold tags to
        recover, and counting it would make recall depend on how many
        out-of-scope records happened to be sampled."""
        gold = GoldSet(path=None)
        gold.record("in", ["2.2"])
        gold.record("out", [])
        assert agreement(gold, {"in": ["2.2"]})["gold_tags"] == 1
