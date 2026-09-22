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
