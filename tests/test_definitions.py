"""A term a paper introduces is a definition, not a method.

Before the type existed, three of the corpus's six method statements defined
a term or listed a typology. They were filed as methods because the paper was
introducing something and method was the type for introductions, and the
method layer is what "who has found this, working that way" joins through.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from ao_commons_kg.claims import load_claims  # noqa: E402
from ao_commons_kg.models import ClaimType  # noqa: E402


class TestTheType:
    def test_a_definition_is_its_own_kind_of_statement(self):
        assert ClaimType("definition") is ClaimType.DEFINITION

    def test_it_is_not_primary(self):
        """Nobody comes to the library for what a word means in place of what
        has been shown about it. They reach the definition through the
        concept it defines."""
        assert not ClaimType.DEFINITION.is_primary

    def test_the_bot_accepts_it(self):
        from merge_filing import CLAIM_TYPES
        assert "definition" in CLAIM_TYPES

    def test_the_site_explains_it(self):
        """A type the review screen has no words for falls through to the raw
        value, which is the least help on the newest type."""
        page = (ROOT / "site" / "template.html").read_text(encoding="utf-8")
        assert "definition: [\"definition\"" in page
        assert 'kindCard("definition"' in page


class TestTheMethodGate:
    def test_it_does_not_look_at_definitions(self):
        """A definition is tagged with what it defines, which is the paper's
        subject by construction. Flagging it would be flagging the rule."""
        from ao_commons_kg.extract import method_tagged_by_subject
        assert not method_tagged_by_subject([
            {"claim_type": "position", "concept_tags": ["building-the-loop"],
             "text": "a position"},
            {"claim_type": "definition", "concept_tags": ["building-the-loop"],
             "text": "Building the loop is ..."},
        ])


class TestACoinedTermSaysWhereItCameFrom:
    """A concept a paper coined is joined to its coinage by a definition
    statement carrying the tag. Without one, "who introduced this term, and
    what did they mean by it" has no answer in the graph."""

    def test_the_terms_building_the_loop_coined_are_defined(self):
        defined = {tag for claim in load_claims()
                   if claim.claim_type is ClaimType.DEFINITION
                   for tag in claim.concept_tags}
        for term in ("artificial-organizational-intelligence", "building-the-loop"):
            assert term in defined, f"{term} has no definition statement"

    def test_a_definition_carries_the_concept_it_defines(self):
        untagged = [c.id for c in load_claims()
                    if c.claim_type is ClaimType.DEFINITION and not c.concept_tags]
        assert not untagged, untagged
