"""The concept layer: vocabulary, attribution, and claim-to-claim relations.

Tested against the real taxonomy and the real claims rather than fixtures,
on the same reasoning the taxonomy tests give: a vocabulary that works on a
tidied sample and not on the source would be worse than none.
"""

from pathlib import Path

import pytest
import yaml

from ao_commons_kg.claims import ClaimError, load_claim_relations, load_claims
from ao_commons_kg.concepts import load_vocabulary, slug
from ao_commons_kg.models import CLAIM_RELATIONS, Attribution, Claim, ConfidenceClass

REPO = Path(__file__).resolve().parent.parent


class TestVocabulary:
    def test_it_is_built_from_the_taxonomy_not_copied_from_it(self):
        """The 514 demoted leaf titles are read from the taxonomy file. A
        second copy would be a second source of truth, and the two would
        disagree within a month."""
        vocab = load_vocabulary()
        from_taxonomy = [c for c in vocab.concepts.values() if c.origin == "taxonomy"]
        assert len(from_taxonomy) > 500
        assert "agent-reputation-systems" in vocab
        assert vocab.get("agent-reputation-systems").topics == ("5.3",)

    def test_claim_terms_are_kept_separately_and_marked(self):
        """A concept the corpus needed and the taxonomy did not have. Marked
        so that drift between the two layers stays visible — a long list here
        is evidence about the taxonomy."""
        vocab = load_vocabulary()
        concept = vocab.get("dissociative-agent-identity")
        assert concept is not None
        assert concept.origin == "claim"
        assert "5.3" in concept.topics

    def test_a_term_in_both_places_is_an_error_rather_than_a_silent_winner(self, tmp_path):
        """If the taxonomy grows a subpoint for a term the extras file already
        has, the extras entry is stale. Failing beats picking one."""
        extra = tmp_path / "extra.yml"
        extra.write_text(yaml.safe_dump({"concepts": [
            {"label": "Agent reputation systems", "topics": ["5.3"]},
        ]}), encoding="utf-8")
        with pytest.raises(ValueError, match="source of truth"):
            load_vocabulary(extra_path=extra)

    def test_one_subpoint_under_two_subsections_is_one_concept(self, tmp_path):
        """Same rule as bylines: one thing, one identifier. Two concepts with
        the same label would split every relation that used them."""
        vocab = load_vocabulary()
        for concept in vocab.concepts.values():
            assert concept.id == slug(concept.label)
        labels = [c.label.lower() for c in vocab.concepts.values()]
        assert len(labels) == len(set(labels))

    def test_unknown_tags_are_reported_not_dropped(self):
        """A tag that does not resolve is usually a near-miss for one that
        does. Discarding it silently loses a judgement somebody made."""
        vocab = load_vocabulary()
        assert vocab.unknown(["stake-based-trust"]) == []
        assert vocab.unknown(["stake-based-trusts"]) == ["stake-based-trusts"]

    def test_search_finds_a_concept_from_a_phrase(self):
        """Arrive with a question, land on the concepts that mention it —
        the navigation the taxonomy's two levels cannot give on their own."""
        vocab = load_vocabulary()
        assert any(c.id == "evaluation-gaming-and-answer-key-attacks"
                   for c in vocab.search("gaming"))


class TestAttribution:
    def test_a_claim_defaults_to_the_paper_s_own(self):
        claim = Claim(id="claim:x:1", resource_id="resource:x", text="t", quote="q")
        assert claim.attribution is Attribution.OWN

    def test_a_reported_claim_can_name_whose_it_is(self):
        """Argumentative Zoning's OWN/OTHER axis. Without it, "who has already
        said X" returns whoever most recently repeated X."""
        claim = Claim(id="claim:x:1", resource_id="resource:x", text="t", quote="q",
                      attribution="other", attributed_to="prior work")
        assert claim.attribution is Attribution.OTHER
        assert claim.to_dict()["attribution"] == "other"

    def test_a_claim_cannot_be_its_own_and_someone_else_s(self):
        with pytest.raises(ValueError, match="cannot be the paper's own"):
            Claim(id="claim:x:1", resource_id="resource:x", text="t", quote="q",
                  attributed_to="somebody")

    def test_the_corpus_actually_marks_reported_claims(self):
        """The pass over the first six papers found five. If this drops to
        zero, extraction has stopped making the distinction."""
        borrowed = [c for c in load_claims() if c.attribution is Attribution.OTHER]
        assert borrowed
        assert all(c.attributed_to for c in borrowed)


class TestClaimRelations:
    def test_the_corpus_relations_load_and_are_all_inferred(self):
        """No source states that two claims conflict. A person decided, so
        every one of these carries a confidence class and its reasoning."""
        claims = load_claims()
        relations = load_claim_relations(claims=claims)
        assert relations
        for relation in relations:
            assert relation.relation in CLAIM_RELATIONS
            assert relation.confidence_class is ConfidenceClass.INFERRED
            assert relation.source_location, "a relation with no reasoning is a guess"

    def test_a_relation_to_a_cut_claim_is_refused(self, tmp_path):
        """The editorial pass cuts claims. A cut claim leaving a live edge
        behind would have the graph assert a disagreement with nothing."""
        path = tmp_path / "relations.yml"
        path.write_text(yaml.safe_dump({"relations": [{
            "source": "claim:arxiv:2107.06857:7",   # cut in the first pass
            "target": "claim:arxiv:2107.06857:8",
            "relation": "SUPPORTS", "because": "points at a cut claim",
        }]}), encoding="utf-8")
        with pytest.raises(ClaimError, match="not a claim we hold"):
            load_claim_relations(path, claims=load_claims())

    def test_only_claim_relations_are_allowed_between_claims(self, tmp_path):
        """CITES between two claims would dress an inference as a fact read
        from an index."""
        path = tmp_path / "relations.yml"
        path.write_text(yaml.safe_dump({"relations": [{
            "source": "claim:a", "target": "claim:b",
            "relation": "CITES", "because": "wrong kind of edge",
        }]}), encoding="utf-8")
        with pytest.raises(ClaimError, match="not a claim-to-claim relation"):
            load_claim_relations(path)

    def test_reasoning_is_required(self, tmp_path):
        path = tmp_path / "relations.yml"
        path.write_text(yaml.safe_dump({"relations": [{
            "source": "claim:a", "target": "claim:b", "relation": "SUPPORTS",
        }]}), encoding="utf-8")
        with pytest.raises(ClaimError, match="missing `because`"):
            load_claim_relations(path)

    def test_a_claim_cannot_relate_to_itself(self, tmp_path):
        path = tmp_path / "relations.yml"
        path.write_text(yaml.safe_dump({"relations": [{
            "source": "claim:a", "target": "claim:a",
            "relation": "SUPPORTS", "because": "circular",
        }]}), encoding="utf-8")
        with pytest.raises(ClaimError, match="cannot relate to itself"):
            load_claim_relations(path)


class TestTaggedCorpus:
    def test_every_concept_tag_in_the_corpus_resolves(self):
        """The check that keeps the two layers honest. A tag pointing at
        nothing is a relation that will never be proposed."""
        vocab = load_vocabulary()
        unknown = {
            tag for claim in load_claims()
            for tag in vocab.unknown(claim.concept_tags)
        }
        assert not unknown, f"unresolvable concept tags: {sorted(unknown)}"

    def test_the_pilot_papers_are_tagged(self):
        """Six papers were passed over by hand. If tagging coverage falls,
        something reverted them."""
        claims = load_claims()
        tagged = [c for c in claims if c.concept_tags]
        assert len(tagged) == len(claims), "every claim in the pilot carries a concept"


class TestCandidateQueue:
    """The arithmetic that makes the statement layer tractable: 780 pairs
    are unreadable, 25 are an afternoon."""

    def test_a_shared_concept_is_required(self):
        from ao_commons_kg.claims import candidate_pairs, load_claims
        claims = load_claims()
        for left, right, shared in candidate_pairs(claims, []):
            assert shared, "a pair with no shared concept has nothing to judge"
            assert set(shared) <= set(left.concept_tags) & set(right.concept_tags)

    def test_pairs_already_settled_do_not_come_back(self):
        """Re-reading a pair somebody already judged wastes the scarce half
        of this process."""
        from ao_commons_kg.claims import candidate_pairs, load_claim_relations, load_claims
        claims = load_claims()
        relations = load_claim_relations(claims=claims)
        settled = {(r.source_id, r.target_id) for r in relations}
        pairs = {(a.id, b.id) for a, b, _ in candidate_pairs(claims, relations)}
        assert not (pairs & settled)
        assert not (pairs & {(b, a) for a, b in settled}), "direction must not smuggle one back"

    def test_same_paper_pairs_are_a_separate_pass(self):
        from ao_commons_kg.claims import candidate_pairs, load_claims
        claims = load_claims()
        assert all(a.resource_id != b.resource_id
                   for a, b, _ in candidate_pairs(claims, []))
        within = candidate_pairs(claims, [], across_papers_only=False)
        assert any(a.resource_id == b.resource_id for a, b, _ in within)

    def test_the_queue_is_ordered_so_one_concept_is_read_at_a_time(self):
        from ao_commons_kg.claims import candidate_pairs, load_claims
        pairs = candidate_pairs(load_claims(), [])
        concepts = [shared[0] for _, _, shared in pairs]
        assert concepts == sorted(concepts, key=concepts.index), "grouped, not interleaved"

    def test_drafted_relations_say_they_are_unconfirmed(self):
        """A model proposing an inference and writing its own justification
        is the case the INFERRED class exists to mark. It must not be
        readable as a person's judgement."""
        from ao_commons_kg.claims import load_claim_relations, load_claims
        drafted = [r for r in load_claim_relations(claims=load_claims())
                   if "claude" in (r.extraction_method or "")]
        assert drafted
        assert all("unconfirmed" in r.extraction_method for r in drafted)


class TestDerivedTopics:
    """A paper's categories, computed from what its statements argue about."""

    def test_a_paper_lands_where_its_statements_do(self):
        from ao_commons_kg.concepts import derived_topics, load_vocabulary
        claims = [c for c in load_claims() if c.resource_id == "resource:arxiv:2605.30169"]
        derived = derived_topics(claims, load_vocabulary())
        assert "5.3" in derived, "a paper arguing about reputation belongs under 5.3"
        assert derived["5.3"] > 1, "weight is information, not just membership"

    def test_it_finds_categories_the_filer_missed(self):
        """Melting Pot was filed 14.1 and 14.5. One of its own statements
        predicts the suite will be gamed, which is 14.3 — evaluation
        integrity — and nobody filed it there."""
        from ao_commons_kg.concepts import derived_topics, load_vocabulary
        claims = [c for c in load_claims() if c.resource_id == "resource:arxiv:2107.06857"]
        assert "14.3" in derived_topics(claims, load_vocabulary())

    def test_it_cannot_see_a_paper_s_framing(self):
        """The finding that keeps this additive rather than replacing. A
        paper whose contribution is a reframing makes it at the level of the
        whole, and no sentence in it carries the frame — so Solipsistic
        Superintelligence derives its evaluation codes and loses 1.2."""
        from ao_commons_kg.concepts import derived_topics, load_vocabulary
        claims = [c for c in load_claims() if c.resource_id == "resource:arxiv:2606.03237"]
        derived = derived_topics(claims, load_vocabulary())
        assert "1.2" not in derived
        assert "14.3" in derived

    def test_no_statements_derives_nothing_rather_than_guessing(self):
        from ao_commons_kg.concepts import derived_topics, load_vocabulary
        assert derived_topics([], load_vocabulary()) == {}


class TestVocabularyHygiene:
    """A concept list has one failure mode and it is silent: two terms for
    one idea. Nothing errors; the relations that would have been proposed
    between claims carrying them are simply never proposed."""

    def test_a_colliding_term_is_refused_with_the_alternative(self, tmp_path):
        from ao_commons_kg.concepts import load_vocabulary
        extra = tmp_path / "extra.yml"
        extra.write_text(yaml.safe_dump({"concepts": [
            {"label": "Agent reputation", "topics": ["5.3"]},
        ]}), encoding="utf-8")
        with pytest.raises(ValueError, match="agent-reputation-systems"):
            load_vocabulary(extra_path=extra)

    def test_a_genuinely_different_idea_can_say_so(self, tmp_path):
        """The escape hatch has to exist, and has to be a sentence somebody
        wrote rather than a boolean nobody reads."""
        from ao_commons_kg.concepts import load_vocabulary
        extra = tmp_path / "extra.yml"
        extra.write_text(yaml.safe_dump({"concepts": [
            {"label": "Agent reputation", "topics": ["5.3"],
             "distinct_from_near_matches": "the signal, not the system carrying it"},
        ]}), encoding="utf-8")
        assert "agent-reputation" in load_vocabulary(extra_path=extra)

    def test_containment_is_caught_where_ratio_alone_misses_it(self):
        """"Agent reputation" against "Agent reputation systems" scores 0.80
        on ratio and slips under any threshold loose enough not to flag real
        siblings. One label being a whole-word prefix of another is the
        clearest synonym signal there is."""
        from ao_commons_kg.concepts import load_vocabulary, similar_terms
        hits = similar_terms("Agent reputation", load_vocabulary())
        assert any(c.id == "agent-reputation-systems" for _, c in hits)

    def test_a_word_prefix_is_not_a_substring_match(self):
        """"agent" must not match "agentic"."""
        from ao_commons_kg.concepts import Concept, Vocabulary, similar_terms
        vocab = Vocabulary(concepts={"agentic-drift": Concept("agentic-drift", "Agentic drift")})
        assert not similar_terms("Agent", vocab)

    def test_the_inherited_duplicates_are_reported_not_hidden(self):
        """Eight pairs came in with the taxonomy's subpoints, which were
        written as prose rather than as a vocabulary. They cannot be fixed
        here, and pretending they are not there would be worse."""
        from ao_commons_kg.concepts import duplicate_pairs, load_vocabulary
        assert len(duplicate_pairs(load_vocabulary())) >= 8

    def test_usage_counts_the_zeros(self):
        """A concept on no statements is inert and a concept on one connects
        nothing. Both are invisible if only the used terms are counted."""
        from ao_commons_kg.concepts import load_vocabulary, usage
        vocab = load_vocabulary()
        counts = usage(load_claims(), vocab)
        assert len(counts) == len(vocab)
        assert sum(1 for n in counts.values() if n == 0) > 400


class TestGeneratedList:
    """`data/concepts.json` is the only place the vocabulary is readable
    without a checkout and an installed package. A stale one is worse than
    none, because people will check it and believe the answer."""

    def _built(self):
        import sys
        from pathlib import Path
        repo = Path(__file__).resolve().parent.parent
        sys.path.insert(0, str(repo / "scripts"))
        from build_concepts import build
        return build()

    def _committed(self):
        import json
        from pathlib import Path
        path = Path(__file__).resolve().parent.parent / "data" / "concepts.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def test_the_committed_list_matches_the_sources(self):
        """The check that makes the file trustworthy. If the taxonomy grows a
        subpoint or the extras file gains a term, this fails until the list
        is rebuilt."""
        assert self._committed() == self._built()

    def test_it_holds_every_term_not_only_the_used_ones(self):
        """The site payload carries 17. A contributor asking "does this term
        already exist" needs all 523, and the unused ones are most of what
        they would be duplicating."""
        payload = self._committed()
        assert payload["counts"]["total"] == len(payload["concepts"]) >= 520

    def test_it_says_it_is_generated(self):
        """A build artifact that does not say so is one somebody hand-edits."""
        assert "do not edit" in self._committed()["generated_by"]

    def test_it_ships_its_own_collisions(self):
        """A list that hides its duplicates invites more trust than it has
        earned."""
        assert len(self._committed()["looks_like_one_idea"]) >= 8

    def test_every_concept_records_whether_anything_uses_it(self):
        payload = self._committed()
        assert all("statements" in c for c in payload["concepts"])
        assert payload["counts"]["carrying_a_statement"] == sum(
            1 for c in payload["concepts"] if c["statements"])
