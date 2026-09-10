"""Automatic citation expansion: the threshold, the budget, and the scan.

These rules decide what enters the corpus without anybody reading a queue,
so the tests are about what the rules refuse as much as what they admit.
"""

import pytest

from ao_commons_kg.expansion import (
    BASE_THRESHOLD, Candidate, ScopeVerdict, find_candidates, provenance,
    select, threshold_for,
)


def admit_all(candidate, metadata):
    return ScopeVerdict(True, "in scope for the test", "test-judge")


def refuse_all(candidate, metadata):
    return ScopeVerdict(False, "out of scope for the test", "test-judge")


class TestThreshold:
    def test_it_rises_one_per_generation(self):
        assert [threshold_for(g) for g in (1, 2, 3, 4)] == [2, 3, 4, 5]

    def test_generation_zero_is_not_admitted(self):
        """Generation 0 is what a person chose. Asking what threshold it had
        to clear is a category error, and silently returning one would let a
        bug admit records as if a human had picked them."""
        with pytest.raises(ValueError, match="what a person chose"):
            threshold_for(0)

    def test_the_same_support_stops_qualifying_further_out(self):
        """The brake. Two citations admit at generation 1 and do not at
        generation 2 — which is what stops an admitted paper's own references
        from entering on the same terms it did."""
        near = Candidate("k", ("a", "b"), generation=1)
        far = Candidate("k", ("a", "b"), generation=2)
        assert near.clears() and not far.clears()


class TestFindingCandidates:
    def test_held_works_are_edges_not_candidates(self):
        """A cited work already in the corpus is a CITES edge. Proposing it
        again would re-admit records the corpus already has."""
        candidates = find_candidates(
            references={"resource:a": ["arxiv:held", "arxiv:new"]},
            held_keys={"arxiv:held": "resource:b"},
            generations={"resource:a": 0},
        )
        assert [c.key for c in candidates] == ["arxiv:new"]

    def test_support_is_the_set_of_citing_records(self):
        candidates = find_candidates(
            references={"resource:a": ["arxiv:x"], "resource:b": ["arxiv:x"]},
            held_keys={},
            generations={"resource:a": 0, "resource:b": 0},
        )
        assert candidates[0].support == 2
        assert candidates[0].cited_by == ("resource:a", "resource:b")

    def test_generation_follows_the_closest_citing_paper(self):
        """Closest, not furthest. Being cited by an original seed is a
        stronger claim than being cited by something three hops out, and the
        candidate is judged at its best case."""
        candidates = find_candidates(
            references={"resource:seed": ["arxiv:x"], "resource:far": ["arxiv:x"]},
            held_keys={},
            generations={"resource:seed": 0, "resource:far": 3},
        )
        assert candidates[0].generation == 1

    def test_a_reference_list_for_a_dropped_record_is_ignored(self):
        """Reference lists outlive the records they describe — a duplicate
        removed from the corpus leaves its entry in the store."""
        candidates = find_candidates(
            references={"resource:gone": ["arxiv:x"]},
            held_keys={},
            generations={},
        )
        assert candidates == []

    def test_output_does_not_depend_on_dict_order(self):
        refs = {"resource:a": ["arxiv:y", "arxiv:x"], "resource:b": ["arxiv:x"]}
        forward = find_candidates(refs, {}, {"resource:a": 0, "resource:b": 0})
        backward = find_candidates(dict(reversed(list(refs.items()))), {},
                                   {"resource:b": 0, "resource:a": 0})
        assert [c.key for c in forward] == [c.key for c in backward]


class TestSelection:
    def test_nothing_is_admitted_without_a_judge(self):
        """The fallback for a missing scope test is a queue, not a keyword
        score. A run with no judge configured must look like it did nothing,
        not like it approved everything."""
        candidates = [Candidate("k", ("a", "b"), 1)]
        selection = select(candidates)
        assert selection.admitted == []
        assert selection.over_budget == candidates

    def test_below_threshold_never_reaches_the_judge(self):
        """93% of candidates are cited once. Paying for a model call on each
        of them is the difference between a run that costs cents and one
        that costs real money."""
        seen = []

        def judge(candidate, metadata):
            seen.append(candidate.key)
            return ScopeVerdict(True, "y", "test")

        select([Candidate("lonely", ("a",), 1)], judge=judge)
        assert seen == []

    def test_the_scan_can_refuse_a_candidate_that_cleared(self):
        """Structure proposes, scope disposes. A work several of our papers
        cite can still be optimization background."""
        selection = select([Candidate("k", ("a", "b"), 1)], judge=refuse_all)
        assert selection.admitted == []
        assert len(selection.rejected) == 1
        assert selection.rejected[0][1].reasoning

    def test_the_budget_defers_rather_than_drops(self):
        """Over-budget candidates come back next run. Dropping them would
        make the corpus depend on the order runs happened to fire."""
        candidates = [Candidate(f"k{i}", ("a", "b"), 1) for i in range(5)]
        selection = select(candidates, judge=admit_all, budget=2)
        assert len(selection.admitted) == 2
        assert len(selection.over_budget) == 3

    def test_a_verdict_must_say_why(self):
        with pytest.raises(ValueError, match="cannot be audited"):
            ScopeVerdict(True, "   ", "test")


class TestProvenance:
    def test_it_records_the_generation_the_citers_and_the_reasoning(self):
        """The field somebody reads when they are surprised to find a record
        in the corpus. "expansion gen 2" answers nothing."""
        candidate = Candidate("arxiv:x", ("resource:a", "resource:b"), 1)
        verdict = ScopeVerdict(True, "Agents hold budget authority.", "claude-opus-5")
        text = provenance(candidate, verdict, {"resource:a": "Melting Pot"})
        assert "generation 1" in text
        assert "threshold of 2" in text
        assert "Melting Pot" in text
        assert "claude-opus-5" in text
        assert "Agents hold budget authority." in text
        assert "Unreviewed" in text


class TestAgainstTheRealCorpus:
    def test_the_measured_shape_still_holds(self):
        """The numbers the design was argued from. If the corpus stops
        looking like this, the thresholds were chosen for a different
        library and should be revisited."""
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
        from ao_commons_kg.resources import load_resources
        from ao_commons_kg.scholarly.keys import keys_for_corpus
        from ao_commons_kg.scholarly.store import ReferenceStore

        repo = Path(__file__).resolve().parent.parent
        resources = load_resources()
        store = ReferenceStore.load(repo / "data" / "scholarly" / "references.jsonl")
        candidates = find_candidates(
            store.references(),
            keys_for_corpus(resources),
            {r.id: r.expansion_generation for r in resources},
        )
        assert candidates, "no candidates at all means references stopped resolving"
        singletons = [c for c in candidates if c.support == 1]
        # The 93% finding. Loose bound: this is a property of citation
        # behaviour, not of our code, and it should not fail on a good week.
        assert len(singletons) / len(candidates) > 0.8
        assert all(c.generation >= 1 for c in candidates)
