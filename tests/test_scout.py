"""Looking for work the citation graph cannot see.

Every test here is offline. A suite that reaches arXiv is a suite that fails
when arXiv is slow, and the thing worth testing is the judgement — which
queries get asked, what clears the bound, what is refused — not whether a
third party answered today.
"""

import pytest

from ao_commons_kg.scout import (
    Find, Query, Sweep, mentions_agents, queries_from_corpus, sweep,
    topical_support,
)
from ao_commons_kg.scout_sources import ArxivSource, OpenAlexSource


class FakeIndex:
    """Scores on how many of the words it was told to like appear."""

    def __init__(self, liked=("governance", "delegation")):
        self.liked = liked

    def classify(self, text, *, limit=6, min_score=4.0):
        from ao_commons_kg.classify import Assignment
        return [Assignment(code=f"x.{i}", score=10.0)
                for i, word in enumerate(self.liked) if word in (text or "").lower()]


class TestWhatItSearchesFor:
    def test_it_asks_both_halves(self):
        """Concepts statements needed, and subpoints nothing is filed under.
        Without the second it is a slower `grow`: it returns neighbours of
        what we already hold, which expansion does better."""
        queries = queries_from_corpus(
            ["agent-reputation-systems", "sanction-sensitivity"],
            ["Capability tokens and scoped credentials", "Kill-switch design and failure"],
            deepen=2, widen=2)
        assert {q.reason for q in queries} == {"deepen", "widen"}
        assert len([q for q in queries if q.reason == "widen"]) == 2

    def test_a_concept_id_becomes_something_searchable(self):
        queries = queries_from_corpus(["agent-reputation-systems"], [], deepen=1, widen=0)
        assert queries[0].text == "agent reputation systems"

    def test_a_subpoint_that_is_a_sentence_is_cut_to_its_subject(self):
        """Taxonomy subpoints are prose. `Reward design, and what optimizing a
        proxy does to a population` is an explanation, not a search term."""
        queries = queries_from_corpus(
            [], ["Reward design, and what optimizing a proxy does to a population"],
            deepen=0, widen=1)
        assert queries[0].text == "Reward design"

    def test_the_same_seed_asks_the_same_thing(self):
        blind = [f"Concept number {i} of many" for i in range(40)]
        first = queries_from_corpus([], blind, deepen=0, widen=5, seed=7)
        again = queries_from_corpus([], blind, deepen=0, widen=5, seed=7)
        assert [q.text for q in first] == [q.text for q in again]

    def test_a_different_seed_reaches_different_blind_spots(self):
        """493 subpoints cannot all be searched every run, and always taking
        the first few means the rest are never looked for at all."""
        blind = [f"Concept number {i} of many" for i in range(40)]
        first = {q.text for q in queries_from_corpus([], blind, deepen=0, widen=5, seed=1)}
        other = {q.text for q in queries_from_corpus([], blind, deepen=0, widen=5, seed=2)}
        assert first != other


class TestTheAgentHalf:
    """The scope test is what changes *because machine agents hold authority*,
    and BM25 against our taxonomy only measures the organization half. The
    first live run ranked "Organized Violence and Crime in Urban Nigeria" and
    "The ecology of insolvency" at the top, on topic scores of 116 and 108."""

    @pytest.mark.parametrize("text", [
        "LLM agents negotiating on behalf of a firm",
        "an autonomous system with budget authority",
        "multi-agent reinforcement learning in organizations",
        "AI adoption and the shape of the firm",
    ])
    def test_a_machine_is_present(self, text):
        assert mentions_agents(text)

    @pytest.mark.parametrize("text", [
        "Organized violence and crime in urban Nigeria",
        "The ecology of insolvency across legal frameworks",
        "Pathways to a merit-based recruitment system",
    ])
    def test_and_here_it_is_not(self, text):
        assert not mentions_agents(text)

    def test_it_is_refused_before_it_is_scored(self):
        found = sweep([], [], index=FakeIndex(), concepts_in_use=[], held_keys={})
        assert isinstance(found, Sweep)


class TestTheBound:
    def test_topic_evidence_and_concept_hits_both_count(self):
        find = Find(key="k", title="Delegation and governance of agent reputation systems")
        score, topics, concepts = topical_support(
            find, FakeIndex(), ["agent-reputation-systems"])
        assert topics and concepts == ("agent-reputation-systems",)
        assert score > 20

    def test_something_unrelated_scores_nothing(self):
        score, topics, _ = topical_support(Find(key="k", title="Baking bread"),
                                           FakeIndex(), [])
        assert (score, topics) == (0.0, ())


class TestTheSweep:
    def _source(self, finds, name="fake"):
        class S:
            def __init__(self):
                self.name = name

            def search(self, query, *, limit):
                return [Find(**{**f.__dict__}) for f in finds]
        return S()

    def test_it_never_proposes_something_already_held(self):
        held = {"arxiv:1234.5678": "resource:arxiv:1234.5678"}
        found = sweep([self._source([Find(key="arxiv:1234.5678", title="agent governance")])],
                      [Query("governance", "deepen")],
                      index=FakeIndex(), concepts_in_use=[], held_keys=held)
        assert [f.key for f in found.already_held] == ["arxiv:1234.5678"]
        assert not found.kept

    def test_a_find_it_cannot_key_is_dropped_not_guessed_at(self):
        """One we cannot key is one we cannot tell we already hold."""
        found = sweep([self._source([Find(key=None, title="agent governance")])],
                      [Query("governance", "deepen")],
                      index=FakeIndex(), concepts_in_use=[], held_keys={})
        assert len(found.unusable) == 1

    def test_one_source_failing_is_not_the_run_failing(self):
        class Broken:
            name = "broken"

            def search(self, query, *, limit):
                raise RuntimeError("down")

        found = sweep(
            [Broken(), self._source([Find(key="k1", title="agent governance delegation")])],
            [Query("governance", "deepen")],
            index=FakeIndex(), concepts_in_use=[], held_keys={})
        assert [f.key for f in found.kept] == ["k1"]

    def test_the_budget_holds(self):
        many = [Find(key=f"k{i}", title="agent governance delegation") for i in range(9)]
        found = sweep([self._source(many)], [Query("governance", "deepen")],
                      index=FakeIndex(), concepts_in_use=[], held_keys={}, budget=4)
        assert len(found.kept) == 4

    def test_a_work_several_queries_return_is_recorded_once(self):
        source = self._source([Find(key="k1", title="agent governance delegation")])
        found = sweep([source], [Query("governance", "deepen"), Query("delegation", "widen")],
                      index=FakeIndex(), concepts_in_use=[], held_keys={})
        assert len(found.kept) == 1
        assert set(found.kept[0].queries) == {"governance", "delegation"}


class TestTheSourcesParseWhatTheyAreGiven:
    def test_arxiv(self):
        payload = """<feed><entry>
          <id>http://arxiv.org/abs/2609.10105v1</id>
          <title>A Feasibility Taxonomy</title>
          <summary>Agents that hold budget authority.</summary>
          <published>2026-09-09T00:00:00Z</published>
        </entry></feed>"""
        finds = ArxivSource.parse(payload)
        assert len(finds) == 1
        assert finds[0].key == "arxiv:2609.10105"
        assert finds[0].date == "2026-09-09"

    def test_openalex_rebuilds_the_inverted_abstract(self):
        payload = ('{"results": [{"id": "https://openalex.org/W1", "title": "T",'
                   ' "publication_date": "2026-09-01",'
                   ' "abstract_inverted_index": {"agents": [0], "decide": [1]}}]}')
        finds = OpenAlexSource.parse(payload)
        assert finds[0].abstract == "agents decide"
        assert finds[0].key == "openalex:W1"

    def test_a_source_that_answers_with_rubbish_yields_nothing(self):
        assert OpenAlexSource.parse("not json") == []
        assert ArxivSource.parse("<feed></feed>") == []


class TestTheScanSeesDifferentEvidence:
    """A scout find has no citations, and the citation prompt would report
    that as "cited by 0 papers" — which reads as weak evidence when the truth
    is different evidence. The policy above it must not fork, though: one
    scope test, one exclusion register, one standard of proof."""

    def _both(self):
        from ao_commons_kg.expansion import Candidate
        from ao_commons_kg.scope_judge import build_prompt, build_scout_prompt
        cited = build_prompt(Candidate(key="k", cited_by=("r1", "r2")),
                             {"title": "T", "abstract": "A"}, ["Paper one"])
        scouted = build_scout_prompt({"title": "T", "abstract": "A"},
                                     queries=["agent reputation systems"],
                                     topics=[("5.3", 12.0)], concepts=["agent-reputation"])
        return cited, scouted

    def test_the_policy_is_one_copy(self):
        cited, scouted = self._both()
        for section in ("THE SCOPE TEST", "EXCLUSION REGISTER", "borrowed\nbackground"):
            assert section in cited and section in scouted, section

    def test_they_ask_for_the_same_answer(self):
        cited, scouted = self._both()
        assert cited[-300:] == scouted[-300:]

    def test_only_the_evidence_differs(self):
        cited, scouted = self._both()
        assert "cited by 2 papers" in cited
        assert "cited by 2 papers" not in scouted
        assert "Nothing in the library cites this paper" in scouted
        assert "Nothing in the library cites this paper" not in cited

    def test_the_scan_is_told_a_high_topic_score_is_not_the_thing(self):
        """It scores words against a taxonomy about organizations. The first
        sweep ranked a paper on violence in Nigeria at the top on that basis,
        so the model has to be told what the number does and does not mean."""
        _, scouted = self._both()
        flat = " ".join(scouted.split())
        assert "not evidence that machine agents hold authority" in flat

    def test_a_scout_without_a_key_refuses_to_pretend(self):
        from ao_commons_kg.scope_judge import anthropic_scout_judge
        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
            anthropic_scout_judge(api_key="")


class TestAMissingKeySaysSo:
    """Both judges imported the Anthropic SDK before checking the key, so on
    an install without the optional extra — which is what CI runs — a missing
    key was reported as ModuleNotFoundError. The common case, with the useful
    answer, hidden behind an install problem."""

    def test_the_scout_judge(self):
        from ao_commons_kg.scope_judge import anthropic_scout_judge
        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
            anthropic_scout_judge(api_key="")

    def test_and_the_growth_judge(self):
        from ao_commons_kg.scope_judge import anthropic_judge
        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
            anthropic_judge(api_key="")
