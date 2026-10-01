"""The checks a draft is put through, built from what went wrong.

Every fixture here is a real failure from the audit of the first seven
papers against their full texts. A check that passes on invented examples and
misses the case that motivated it would be decoration.
"""

from ao_commons_kg.extract import (
    argued_findings, blanket_tags, check, hedges_dropped, undeclared_definitions,
    unread_sections,
)


class FakeSection:
    def __init__(self, kind, text, heading=""):
        self.kind, self.text, self.heading = kind, text, heading


class TestAParaphraseSurerThanItsQuote:
    def test_a_dropped_hedge_is_flagged(self):
        """Melting Pot's conclusion, as first drafted."""
        flagged = hedges_dropped([{
            "quote": "solving the problems posed here seems to require agents that "
                     "understand trust, generosity, and forgiveness",
            "text": "Solving novel social situations requires agents that model trust.",
        }])
        assert flagged

    def test_a_kept_hedge_passes(self):
        assert not hedges_dropped([{
            "quote": "solving the problems posed here seems to require agents that "
                     "understand trust",
            "text": "Solving Melting Pot's test scenarios seems to require agents "
                    "that understand trust.",
        }])

    def test_softening_an_author_is_flagged_too(self):
        """Dissociative Identity says governance *must* shift. A paraphrase
        that says *should* has misread it as surely as one that hardened it."""
        assert hedges_dropped([{
            "quote": "Governance must therefore shift from ex post reputation",
            "text": "Governance should shift from ex post reputation to ex ante harnesses.",
        }])

    def test_a_quote_with_no_hedge_has_nothing_to_drop(self):
        assert not hedges_dropped([{"quote": "Agents with larger memory performed worse.",
                                    "text": "More memory made agents perform worse."}])


class TestAFindingQuotedAsArgued:
    def test_plausible_is_not_observed(self):
        """Beyond the High Score's gaming inference, typed finding."""
        assert argued_findings([{
            "claim_type": "finding",
            "quote": "It is then plausible that leading submissions gained much of "
                     "their advantage by excelling in scenarios that did not reward "
                     "prosocial ability",
            "text": "Leading submissions gained much of their advantage by exploiting "
                    "a weakness in the evaluation framework.",
        }])

    def test_the_same_sentence_as_a_position_is_fine(self):
        assert not argued_findings([{
            "claim_type": "position",
            "quote": "It is then plausible that leading submissions gained much",
            "text": "It is plausible that leading submissions gained much.",
        }])


class TestATermNotTypedDefinition:
    def test_an_announced_term_typed_method_is_flagged(self):
        """Building the Loop's first statement, for a month."""
        assert undeclared_definitions([{
            "claim_type": "method",
            "quote": "We introduce Artificial Organisational Intelligence (AOI): the "
                     "capacity for organisations to make their knowledge legible",
            "text": "AOI is an organization's capacity to make its knowledge legible.",
        }])

    def test_the_unannounced_form_is_caught(self):
        """Solipsistic Superintelligence's dynamic evaluation."""
        assert undeclared_definitions([{
            "claim_type": "method",
            "quote": "A dynamic evaluation is the one in which the test distribution "
                     "depends on the policy",
            "text": "A dynamic evaluation is one whose test distribution depends on "
                    "the evaluated policy.",
        }])

    def test_a_definition_is_left_alone(self):
        assert not undeclared_definitions([{
            "claim_type": "definition",
            "quote": "We introduce Artificial Organisational Intelligence (AOI)",
            "text": "AOI is ...",
        }])


class TestABlanketTag:
    def _paper(self, tagged, untagged):
        return ([{"concept_tags": ["one-idea"]}] * tagged
                + [{"concept_tags": ["another"]}] * untagged)

    def test_ten_of_eleven_is_flagged(self):
        assert blanket_tags(self._paper(10, 1)) == ["one-idea (10 of 11)"]

    def test_seven_of_twelve_is_flagged(self):
        """The next worst in the corpus, and the reason the line is half."""
        assert blanket_tags(self._paper(7, 5))

    def test_half_is_not_a_blanket(self):
        assert not blanket_tags(self._paper(3, 3))

    def test_a_short_paper_can_be_about_one_thing(self):
        assert not blanket_tags(self._paper(4, 0))


class TestASectionNobodyRead:
    BODY = "The experiments show a gap between training and testing. " * 40

    def test_a_results_section_with_no_statement_is_named(self):
        sections = [FakeSection("abstract", "We find a gap."),
                    FakeSection("results", self.BODY, heading="7 Experiments")]
        assert unread_sections([{"quote": "We find a gap."}], sections) == ["7 Experiments"]

    def test_a_section_a_statement_was_drawn_from_is_read(self):
        sections = [FakeSection("results", self.BODY, heading="7 Experiments")]
        quote = "The experiments show a gap between training and testing."
        assert not unread_sections([{"quote": quote}], sections)

    def test_front_matter_and_short_sections_are_not_asked_for(self):
        sections = [FakeSection("abstract", self.BODY), FakeSection("introduction", self.BODY),
                    FakeSection("results", "Short.", heading="7.1")]
        assert not unread_sections([], sections)

    def test_no_body_means_nothing_to_report(self):
        assert unread_sections([{"quote": "x"}], None) == []


class TestTheyReportRatherThanRefuse:
    def test_a_flagged_statement_is_still_kept(self):
        result = check([{
            "text": "Leading submissions gained their advantage by gaming.",
            "quote": "It is then plausible that leading submissions gained much of "
                     "their advantage",
            "claim_type": "finding", "attribution": "own", "concept_tags": [],
        }])
        assert len(result.kept) == 1
        assert "typed finding, quoted as argued" in result.warnings
        assert "paraphrase surer than its quote" in result.warnings


class TestBuildingTheLoopNoLongerTripsThem:
    """The paper these checks were first written for. Its re-read must pass
    the two it used to fail outright."""

    def test_no_blanket_tag_and_no_undeclared_definition(self):
        from ao_commons_kg.claims import load_claims
        candidates = [{"text": c.text, "quote": c.quote, "claim_type": c.claim_type.value,
                       "concept_tags": list(c.concept_tags)}
                      for c in load_claims() if c.resource_id == "resource:doi:10-1111-epic-70009"]
        assert len(candidates) >= 20
        assert not blanket_tags(candidates)
        assert not undeclared_definitions(candidates)
