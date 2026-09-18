"""Finding the questions a paper says are open.

Every other statement type has to be recognized. An open question is
announced, because an author stating one wants it found — which makes this
the one place a pattern can do real work, and the one place it is allowed to
be generous: a false positive costs a passage an extractor glances at and
discards, a false negative costs a problem nobody knows is open.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from ao_commons_kg.extract import GAP_MARKERS, Passage, gap_passages  # noqa: E402
from ao_commons_kg.models import ClaimType  # noqa: E402


class FakeSection:
    def __init__(self, kind, text, heading=""):
        self.kind, self.text, self.heading = kind, text, heading


class TestTheType:
    def test_a_gap_is_its_own_kind_of_statement(self):
        assert ClaimType("gap") is ClaimType.GAP

    def test_it_is_not_primary(self):
        """It is not an answer the library holds. It is a question the library
        can say nobody has answered — a different product on the same
        statements."""
        assert not ClaimType.GAP.is_primary

    def test_the_bot_accepts_it(self):
        from merge_filing import CLAIM_TYPES
        assert "gap" in CLAIM_TYPES


class TestTheMarkers:
    @pytest.mark.parametrize("text", [
        "their ability to reproduce these patterns remains an open question",
        "Whether summarization bias survives Stage 3 is genuinely open.",
        "We leave a multilingual evaluation to future work.",
        "It is not yet known whether this holds at scale.",
        "No accepted benchmark exists for this task.",
        "How to price delegated authority is an open problem.",
        "Future work should test the mechanism under load.",
        "This remains unclear at present.",
    ])
    def test_it_finds_an_announced_question(self, text):
        assert GAP_MARKERS.search(text), text

    @pytest.mark.parametrize("text", [
        "A2A is an open specification for inter-agent interoperability",
        "The results are open to interpretation by practitioners.",
        "The model is open source and the weights are open access.",
        "The environment is open-ended by construction.",
        "We evaluate in an open world setting.",
        "Our evaluation covers only English.",
    ])
    def test_it_leaves_the_other_senses_of_open_alone(self, text):
        """`open` is a busy word here — open source, open weights, an open
        specification. A blacklist of the nouns that can follow it would never
        finish, so the rule is grammatical: the sense meaning unresolved is
        predicative. Real full text produced this test — `A2A is an open
        specification` was the first thing the pattern got wrong."""
        assert not GAP_MARKERS.search(text), text


class TestThePassages:
    def test_it_reports_where_and_why(self):
        found = gap_passages([FakeSection(
            "conclusion", "Whether this survives at scale is genuinely open.")])
        assert len(found) == 1
        assert isinstance(found[0], Passage)
        assert found[0].section == "conclusion"
        assert "genuinely open" in found[0].marker

    def test_abstracts_are_skipped(self):
        """An abstract that mentions an open question is selling the paper's
        contribution; the question itself is stated properly further down."""
        assert gap_passages([FakeSection(
            "abstract", "Whether this survives at scale remains an open question.")]) == []

    def test_it_carries_enough_around_the_marker_to_read(self):
        text = ("Before. " * 40) + "This remains unclear. " + ("After. " * 40)
        found = gap_passages([FakeSection("discussion", text)])
        assert found and len(found[0].text) > 200
        assert "Before." in found[0].text and "After." in found[0].text

    def test_it_finds_nothing_in_a_paper_that_announces_nothing(self):
        assert gap_passages([FakeSection(
            "results", "We measure a 12% improvement over the baseline.")]) == []
