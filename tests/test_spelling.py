"""One spelling across everything this project writes.

The reason is not style. A statement's tags are slugs, so
`organisational-knowledge-legibility` and `organizational-knowledge-legibility`
are two concepts that connect to nothing and to each other least of all — and
a corpus written by a model over many sittings will produce both unless
something says which.
"""

from pathlib import Path

import pytest
import yaml

from ao_commons_kg.claims import load_claims
from ao_commons_kg.concepts import load_vocabulary
from ao_commons_kg.spelling import findings, to_american

ROOT = Path(__file__).resolve().parent.parent


class TestTheConverter:
    def test_it_moves_the_ones_that_matter(self):
        assert to_american("organisational behaviour") == "organizational behavior"
        assert to_american("a judgement, characterised") == "a judgment, characterized"

    def test_it_leaves_the_words_that_only_look_british(self):
        """`analysis` and `parameter` are spelled the same on both sides, and a
        converter that mangles them is worse than none."""
        assert to_american("the analysis of one parameter") == "the analysis of one parameter"
        assert to_american("metres of diameter") == "metres of diameter"


class TestTheStatements:
    """What a reviewer reads, and what the tags are built from."""

    def test_every_statement_is_american(self):
        offenders = [(c.id, findings(c.text)) for c in load_claims() if findings(c.text)]
        assert not offenders, f"British spelling in statement text: {offenders}"

    def test_every_tag_is_american(self):
        offenders = [(c.id, t) for c in load_claims()
                     for t in (c.concept_tags or []) if findings(t)]
        assert not offenders, (
            "British spelling in a concept tag. A tag is a slug, so this is not a "
            f"style question — it is a second concept nothing joins to: {offenders}")

    def test_the_vocabulary_is_american(self):
        vocab = load_vocabulary()
        offenders = [c.id for c in vocab.concepts.values()
                     if findings(c.id) or findings(c.label)]
        assert not offenders, f"British spelling in the vocabulary: {offenders}"

    def test_the_quotes_are_left_exactly_as_published(self):
        """The other half of the rule, and the one that is easy to lose. A quote
        is checked verbatim against the paper; spelling it our way would make
        the corpus disagree with its own source."""
        claims = {c.id: c for c in load_claims()}
        quoted = claims["claim:doi:10-1111-epic-70009:1"]
        assert "Organisational" in quoted.quote, "the paper's spelling, untouched"
        assert "Organizational" in quoted.text, "our sentence, our spelling"


class TestTheAssertedRelations:
    def test_the_reasoning_is_american(self):
        raw = (ROOT / "data" / "claim-relations.yml").read_text(encoding="utf-8")
        payload = yaml.safe_load(raw) or {}
        offenders = [r.get("because") for r in (payload.get("relations") or [])
                     if findings(r.get("because") or "")]
        assert not offenders, offenders


class TestExtractionSettlesItEarly:
    """Normalizing after the fact is a sweep somebody has to remember. The
    place it actually matters is before a proposed tag is looked up."""

    def test_a_proposed_tag_resolves_to_the_concept_that_exists(self):
        from ao_commons_kg.extract import check

        vocab = load_vocabulary()
        assert "organizational-knowledge-legibility" in vocab.concepts

        result = check(
            [{
                "text": "Organisational knowledge legibility is what the work is after.",
                "quote": "x", "claim_type": "finding", "attribution": "own",
                "concept_tags": ["organisational-knowledge-legibility"],
            }],
            vocabulary=vocab,
        )
        assert not result.new_concepts, (
            "a British spelling of an existing tag entered as a new concept")
        assert result.kept[0]["concept_tags"] == ["organizational-knowledge-legibility"]
        assert result.kept[0]["text"].startswith("Organizational")

    def test_the_quote_keeps_the_paper_s_spelling(self):
        from ao_commons_kg.extract import check

        candidate = {
            "text": "Organisations make their knowledge legible.",
            "quote": "the capacity for organisations to make their knowledge legible",
            "claim_type": "finding", "attribution": "own", "concept_tags": [],
        }
        result = check([candidate])
        assert result.kept[0]["quote"] == (
            "the capacity for organisations to make their knowledge legible")
