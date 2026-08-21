"""Turning a paper's text into candidate topics.

The numbers here were measured, not assumed. Against the tags the corpus
already carries — themselves a first pass, so this is agreement with an earlier
judgement rather than truth — stemming bought +3 points of recall@1 and phrases
another +2 of recall@3, together taking MRR from 0.42 to 0.49.
"""

import yaml
import pytest

from pathlib import Path

from ao_commons_kg.classify import TopicIndex, stem, tokenize, with_phrases
from ao_commons_kg.taxonomy import load_taxonomy

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def index():
    topics = load_taxonomy(ROOT / "taxonomy" / "agentic-org-research-library-taxonomy-v3.md")
    aliases = yaml.safe_load((ROOT / "taxonomy" / "aliases.yaml").read_text(encoding="utf-8"))
    return TopicIndex(topics, aliases)


class TestStemming:
    def test_a_plural_meets_its_singular(self):
        assert stem("permissions") == stem("permission")

    def test_a_gerund_loses_its_ending(self):
        assert stem("overspending") == "overspend"

    def test_evaluating_and_evaluation_deliberately_do_not_meet(self):
        """They land on `evaluat` and `evalu`, and closing that gap was tried:
        stripping the verb stem's trailing `at` as well made everything worse
        — recall@1 14% to 13%, MRR 0.49 to 0.47 — because it collides terms
        that mean different things. The miss is cheaper than the collision."""
        assert stem("evaluating") != stem("evaluation")

    def test_short_words_keep_their_endings(self):
        """Chopping a four-letter word leaves a stub that collides with
        everything."""
        assert stem("bias") == "bias"
        assert stem("data") == "data"

    def test_tokenizing_stems_and_drops_the_noise_words(self):
        assert "agent" not in tokenize("agents and permissions")
        assert "permission" in tokenize("agents and permissions")


class TestPhrases:
    def test_adjacent_pairs_become_terms_of_their_own(self):
        assert with_phrases(["spend", "cap"]) == ["spend", "cap", "spend_cap"]

    def test_a_single_term_has_no_pair(self):
        assert with_phrases(["budget"]) == ["budget"]

    def test_the_index_holds_phrases_so_a_phrase_query_can_match(self, index):
        assert any("_" in term for term in index.documents["8.1"])


class TestClassify:
    def test_a_budget_question_lands_on_the_treasury_branch(self, index):
        codes = [a.code for a in index.classify("spend caps and cumulative budgets",
                                                limit=3, min_score=0.5)]
        assert "8.1" in codes

    def test_an_alias_reaches_a_topic_that_does_not_use_the_word(self, index):
        codes = [a.code for a in index.classify("MARL", limit=3, min_score=0.5)]
        assert "15.6" in codes

    def test_a_match_says_which_terms_carried_it(self, index):
        """A suggestion a reviewer cannot account for is one they have to take
        on trust, and the whole point is that they should not have to."""
        found = index.classify("audit trail and logging", limit=1, min_score=0.5)
        assert found and found[0].matched

    def test_nonsense_matches_nothing(self, index):
        assert index.classify("zzzz qqqq wwww", limit=5, min_score=0.5) == []

    def test_the_browser_copy_of_the_stemmer_still_agrees(self):
        """The page scores queries in JavaScript against the index built here,
        so the suffix list exists twice. If they drift, the query is built from
        terms the index no longer holds and suggestions quietly get worse with
        nothing failing."""
        import re

        from ao_commons_kg.classify import _SUFFIXES

        template = (ROOT / "site" / "template.html").read_text(encoding="utf-8")
        block = re.search(r"const SUFFIXES = \[(.*?)\];", template, re.S)
        assert block, "the page should carry a matching stemmer"
        assert tuple(re.findall(r'"([a-z]+)"', block.group(1))) == _SUFFIXES
