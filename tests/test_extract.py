"""The gates on extraction.

Measured against the first batch's actual failures rather than invented
ones: five claims cut by hand as facts about the instrument, five found on
rereading to be the paper reporting somebody else's result. 11% waste and
12% misattribution, both caught by a person in a batch small enough to
reread — which is what stops working at ninety-five papers.
"""

import pytest

from ao_commons_kg.concepts import load_vocabulary
from ao_commons_kg.extract import check, looks_like_artifact_trivia

# Verbatim, from the first pass.
CUT_BY_HAND = [
    "Melting Pot contains more than 80 unique test scenarios.",
    "Focal-population per-capita return is Melting Pot's primary evaluation metric.",
    "Background-population per-capita return is measured as a secondary metric to "
    "detect harm to the wider population.",
    "Each agent architecture was trained with 21 runs, one per substrate.",
    "Exploiter agents and a random agent bound the performance range on each test scenario.",
]

RIGHTLY_KEPT = [
    "Melting Pot revealed weaknesses in standard MARL algorithms that training "
    "performance alone did not show.",
    "Reputation signals for dissociative agents become actively harmful rather than "
    "merely uninformative.",
    "The paper compares six trust models: Brief, Claim, Proof, Stake, Reputation "
    "and Constraint.",
    "Higher prosocial capability does not reliably accompany higher contest score.",
    "Melting Pot is expected to get harder over time as improved agents are folded "
    "into its background populations.",
]


class TestArtifactGate:
    def test_it_catches_the_countable_and_metric_shapes(self):
        caught = [t for t in CUT_BY_HAND if looks_like_artifact_trivia(t)]
        assert len(caught) == 4

    def test_it_rejects_nothing_that_was_rightly_kept(self):
        """This gate deletes work, so a false positive costs a real claim and
        nobody ever learns it existed. Narrow beats greedy."""
        assert not [t for t in RIGHTLY_KEPT if looks_like_artifact_trivia(t)]

    def test_the_one_it_cannot_catch_is_documented_not_hidden(self):
        """"Exploiter agents bound the performance range" is trivia by
        meaning, not by form. Widening the pattern to reach it would start
        rejecting findings, so it is the extractor's job — and the test says
        so rather than leaving a silent 4-of-5."""
        assert not looks_like_artifact_trivia(CUT_BY_HAND[4])


class TestAttributionGate:
    def test_a_reported_claim_must_say_whose(self):
        result = check([{"text": "Prior work found agents are fragile.", "quote": "q",
                         "attribution": "other"}])
        assert not result.kept
        assert result.rejected[0].gate == "attribution"

    def test_attribution_is_required_at_all(self):
        """Asked at extraction rather than found by rereading, because
        rereading is the part that does not scale."""
        result = check([{"text": "A finding.", "quote": "q"}])
        assert result.rejected[0].gate == "attribution"

    def test_a_properly_attributed_claim_passes(self):
        result = check([{"text": "Prior work found agents are fragile.", "quote": "q",
                         "attribution": "other", "attributed_to": "LLM safety literature"}])
        assert len(result.kept) == 1


class TestVerbatimGate:
    def test_an_invented_quote_is_refused_against_real_full_text(self):
        """The load-bearing check. A quote that is not in the paper was
        reconstructed from memory, and invites a reviewer to confirm
        something the paper never said."""
        from ao_commons_kg.fulltext import sections_for

        sections = sections_for("2107.06857")
        assert sections, "no full text fetched; this test needs the network"
        result = check([{
            "text": "Our method beats all prior approaches.",
            "quote": "Melting Pot demonstrates conclusively that agents trained with "
                     "our method outperform all prior approaches on every benchmark",
            "attribution": "own",
        }], sections=sections)
        assert result.rejected[0].gate == "not-in-source"

    def test_a_real_quote_passes_and_records_its_section(self):
        from ao_commons_kg.fulltext import sections_for

        sections = sections_for("2107.06857")
        assert sections
        result = check([{
            "text": "Existing MARL suites do not target generalization.",
            "quote": "Existing evaluation suites for multi-agent reinforcement learning "
                     "(MARL) do not assess generalization to novel situations as their "
                     "primary objective",
            "attribution": "own",
        }], sections=sections)
        assert len(result.kept) == 1
        assert result.kept[0]["extracted_from"] == "abstract"

    def test_without_full_text_the_gate_is_skipped_not_faked(self):
        """Nineteen records have only a description. Pretending the check ran
        would be worse than recording that it could not."""
        result = check([{"text": "A finding.", "quote": "q", "attribution": "own"}])
        assert len(result.kept) == 1
        assert "extracted_from" not in result.kept[0]


class TestConceptGate:
    def test_a_new_tag_colliding_with_an_existing_one_is_refused(self):
        """Growing a vocabulary at extraction speed is exactly when two names
        for one idea appear."""
        result = check([{"text": "A finding.", "quote": "q", "attribution": "own",
                         "concept_tags": ["agent-reputation"]}],
                       vocabulary=load_vocabulary())
        assert result.rejected[0].gate == "concept"
        assert "agent-reputation-systems" in result.rejected[0].detail

    def test_a_genuinely_new_tag_is_proposed_not_rejected(self):
        result = check([{"text": "A finding.", "quote": "q", "attribution": "own",
                         "concept_tags": ["delegation-revocation-latency"]}],
                       vocabulary=load_vocabulary())
        assert len(result.kept) == 1
        assert result.new_concepts == ["delegation-revocation-latency"]

    def test_new_tags_can_be_forbidden_outright(self):
        result = check([{"text": "A finding.", "quote": "q", "attribution": "own",
                         "concept_tags": ["delegation-revocation-latency"]}],
                       vocabulary=load_vocabulary(), allow_new_concepts=False)
        assert result.rejected[0].gate == "concept"


class TestDuplicates:
    def test_the_same_assertion_twice_is_one_claim(self):
        one = {"text": "Agents are fragile.", "quote": "q", "attribution": "own"}
        result = check([dict(one), dict(one)])
        assert len(result.kept) == 1
        assert result.rejected[0].gate == "duplicate"

    def test_waste_is_reported_as_a_rate(self):
        result = check([
            {"text": "A real finding.", "quote": "q", "attribution": "own"},
            {"text": "It contains more than 80 scenarios.", "quote": "q", "attribution": "own"},
        ])
        assert result.waste == pytest.approx(0.5)
