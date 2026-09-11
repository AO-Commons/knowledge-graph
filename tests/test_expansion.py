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
    def test_an_admission_keeps_the_verdict_that_allowed_it(self):
        """The reasoning becomes the record's provenance. Re-fetching it
        later would pay for the model call twice and could return a
        different answer than the one the record was admitted on."""
        selection = select([Candidate("k", ("a", "b"), 1)], judge=admit_all)
        candidate, verdict = selection.admitted[0]
        assert candidate.key == "k" and verdict.reasoning

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
        assert all(v.admit for _, v in selection.admitted)
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
        # behavior, not of our code, and it should not fail on a good week.
        assert len(singletons) / len(candidates) > 0.8
        assert all(c.generation >= 1 for c in candidates)


class TestVerdictParsing:
    """The half that broke in production.

    Twelve of thirty-two candidates in the first live run were refused with
    `AttributeError: 'NoneType' object has no attribute 'group'` — a regex
    that returned None, three frames from where it surfaced, saying nothing
    about what came back. Every shape below is one the model actually
    produced.
    """

    def test_a_bare_object(self):
        from ao_commons_kg.scope_judge import parse_verdict
        assert parse_verdict('{"admit": true}')["admit"] is True

    def test_inside_a_code_fence(self):
        from ao_commons_kg.scope_judge import parse_verdict
        body = '```json\n{"admit": false, "reasoning": "no"}\n```'
        assert parse_verdict(body)["admit"] is False

    def test_with_prose_either_side(self):
        from ao_commons_kg.scope_judge import parse_verdict
        body = 'Here is my assessment.\n{"admit": true}\nLet me know if you need more.'
        assert parse_verdict(body)["admit"] is True

    def test_a_brace_inside_a_string_does_not_end_the_object(self):
        """Why this matches braces instead of using a regex."""
        from ao_commons_kg.scope_judge import parse_verdict
        body = '{"admit": true, "reasoning": "the set {a, b} is cited"}'
        assert "{a, b}" in parse_verdict(body)["reasoning"]

    def test_a_truncated_reply_says_it_was_truncated(self):
        """The actual production failure: max_tokens cut the object off.
        The message has to name that, or the next person re-derives it."""
        from ao_commons_kg.scope_judge import ScanUnreadable, parse_verdict
        with pytest.raises(ScanUnreadable, match="max_tokens"):
            parse_verdict('{"admit": true, "reasoning": "cut off here')

    def test_an_empty_reply_is_not_an_admission(self):
        from ao_commons_kg.scope_judge import ScanUnreadable, parse_verdict
        with pytest.raises(ScanUnreadable, match="no text at all"):
            parse_verdict("")

    def test_prose_with_no_object_reports_what_came_back(self):
        from ao_commons_kg.scope_judge import ScanUnreadable, parse_verdict
        with pytest.raises(ScanUnreadable, match="I cannot"):
            parse_verdict("I cannot assess this paper.")


class TestBorrowedBackground:
    def test_a_verdict_can_admit_as_adjacent_material(self):
        """The corpus holds Melting Pot and SocialJax as borrowed
        background. A binary scan had to refuse that class, and did — it
        turned away a MARL benchmark in the first live run while the corpus
        held two others."""
        verdict = ScopeVerdict(True, "adjacent but load-bearing", "test",
                               borrowed_background=True)
        assert verdict.admit and verdict.borrowed_background

    def test_it_defaults_off(self):
        assert ScopeVerdict(True, "core scope", "test").borrowed_background is False


class TestRememberingRefusals:
    """A refusal used to leave no trace, so the same candidate was
    re-scanned and re-paid for every run, and a verdict that flipped
    between runs was invisible. ReAct was refused twice and admitted once
    before anyone noticed, by reading three logs."""

    def test_a_repeat_refusal_counts_up_and_keeps_the_first_date(self):
        from ao_commons_kg.expansion import merge_refusals
        first = [{"key": "arxiv:1", "refused_on": "2026-09-01", "times_refused": 1,
                  "first_refused_on": "2026-09-01"}]
        merged, _ = merge_refusals(first, [{"key": "arxiv:1", "refused_on": "2026-09-08"}])
        assert merged[0]["times_refused"] == 2
        assert merged[0]["first_refused_on"] == "2026-09-01"
        assert merged[0]["refused_on"] == "2026-09-08"

    def test_a_new_refusal_starts_at_one(self):
        from ao_commons_kg.expansion import merge_refusals
        merged, _ = merge_refusals([], [{"key": "arxiv:2", "refused_on": "2026-09-08"}])
        assert merged[0]["times_refused"] == 1

    def test_admitting_something_previously_refused_is_surfaced(self):
        """A record entering on a judgment the same scan already made the
        other way. A reader is entitled to know that."""
        from ao_commons_kg.expansion import admissions_that_were_previously_refused
        history = [{"key": "arxiv:2210.03629", "times_refused": 2,
                    "reasoning": "upstream capability work"}]
        flipped = admissions_that_were_previously_refused(
            ["arxiv:2210.03629", "arxiv:9999"], history)
        assert [f["key"] for f in flipped] == ["arxiv:2210.03629"]

    def test_history_is_ordered_so_a_diff_is_readable(self):
        from ao_commons_kg.expansion import merge_refusals
        merged, _ = merge_refusals(
            [], [{"key": "arxiv:9", "refused_on": "d"}, {"key": "arxiv:1", "refused_on": "d"}])
        assert [e["key"] for e in merged] == ["arxiv:1", "arxiv:9"]

    def test_a_failed_scan_is_not_recorded_as_a_refusal(self):
        """`could not complete` is a broken scan, not a scope judgment.
        Recording it would poison the flip rate with outages."""
        from ao_commons_kg.expansion import ScopeVerdict
        verdict = ScopeVerdict(False, "scope scan could not complete (timeout)", "m")
        assert "could not complete" in verdict.reasoning


class TestKnownDuplicates:
    def test_a_confirmed_duplicate_is_never_proposed_again(self, tmp_path):
        """It is cited by the same papers next week and clears the same
        threshold, so without this the run pays for a scan and a fetch every
        time to rediscover it. The ACM Generative Agents record was top of
        the candidate list the run after being skipped."""
        from ao_commons_kg.expansion import load_excluded, record_duplicate
        path = tmp_path / "known.yml"
        assert load_excluded(path) == set()
        record_duplicate(path, "doi:10.1145/3586183.3606763",
                         "resource:arxiv:2304.03442", "near-identical title", "2026-09-10")
        assert load_excluded(path) == {"doi:10.1145/3586183.3606763"}

    def test_recording_twice_does_not_duplicate_the_entry(self, tmp_path):
        from ao_commons_kg.expansion import load_excluded, record_duplicate
        path = tmp_path / "known.yml"
        for _ in range(3):
            record_duplicate(path, "arxiv:1", "resource:x", "same title", "2026-09-10")
        assert len(load_excluded(path)) == 1


class TestBothDirections:
    """The recency fix.

    A threshold counting only citations *into* a work cannot admit anything
    published recently, however plainly it belongs — a paper from last month
    has been cited by nobody. It can, however, cite three of ours on the day
    it appears. Counting both directions makes new research reachable, and
    `expand_neighborhood` had said so in its docstring since August while
    this path quietly did the opposite.
    """

    def test_a_paper_nobody_has_cited_yet_can_still_clear(self):
        new = Candidate("arxiv:2609.99999", cited_by=(), cites=("a", "b", "c"),
                        generation=1)
        assert new.support == 3
        assert new.clears()
        assert new.direction == "cites us"

    def test_both_directions_count_the_same(self):
        """"Three of ours cite it" and "it cites three of ours" are equally
        strong evidence of being part of this conversation."""
        backward = Candidate("k", cited_by=("a", "b"), cites=(), generation=1)
        forward = Candidate("k", cited_by=(), cites=("a", "b"), generation=1)
        assert backward.support == forward.support == 2

    def test_one_held_paper_on_both_sides_is_counted_once(self):
        """A mutual citation is one connection, not two."""
        mutual = Candidate("k", cited_by=("a",), cites=("a",), generation=1)
        assert mutual.support == 1
        assert mutual.direction == "both"

    def test_citers_are_found_alongside_references(self):
        candidates = find_candidates(
            references={"resource:a": ["arxiv:old"]},
            held_keys={},
            generations={"resource:a": 0, "resource:b": 0},
            citers={"resource:b": ["arxiv:new"]},
        )
        found = {c.key: c for c in candidates}
        assert found["arxiv:old"].direction == "we cite"
        assert found["arxiv:new"].direction == "cites us"

    def test_a_citer_of_a_record_we_dropped_is_ignored(self):
        assert find_candidates({}, {}, {}, citers={"resource:gone": ["arxiv:x"]}) == []

    def test_a_citer_already_held_is_an_edge_not_a_candidate(self):
        assert find_candidates(
            {}, {"arxiv:held": "resource:b"}, {"resource:a": 0},
            citers={"resource:a": ["arxiv:held"]}) == []


class TestUnresolvable:
    """Observed on a live run: three of 44 candidates had corrupt upstream
    metadata — a wrong title, a wrong abstract, and a 404. The scan caught
    all three, which is the right outcome, but one of them cost a model call
    to assess a blank."""

    def test_a_candidate_with_no_title_never_reaches_the_judge(self):
        seen = []

        def judge(candidate, metadata):
            seen.append(candidate.key)
            return ScopeVerdict(True, "should not be asked", "test")

        selection = select([Candidate("k", ("a", "b"), 1)], judge=judge,
                           metadata=lambda c: {})
        assert seen == []
        assert [c.key for c in selection.unresolvable] == ["k"]
        assert selection.admitted == []

    def test_it_is_not_counted_as_out_of_scope(self):
        """Different facts. One says the work does not belong; the other
        says the index could not say what the work is."""
        selection = select([Candidate("k", ("a", "b"), 1)], judge=admit_all,
                           metadata=lambda c: {"title": "   "})
        assert selection.rejected == []
        assert len(selection.unresolvable) == 1
        assert "unresolvable" in selection.summary()

    def test_a_resolvable_candidate_is_unaffected(self):
        selection = select([Candidate("k", ("a", "b"), 1)], judge=admit_all,
                           metadata=lambda c: {"title": "A real paper"})
        assert len(selection.admitted) == 1
        assert selection.unresolvable == []
