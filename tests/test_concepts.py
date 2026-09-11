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

    def test_asserting_distinctness_does_not_get_you_past_the_check(self, tmp_path):
        """There is no escape hatch, deliberately. If two labels are this
        close, either they name one idea — use the existing term — or the
        name is doing a bad job of saying what differs, and the fix is a
        better name. A note explaining the collision away leaves the
        ambiguity exactly where it does damage: on the screen at tagging
        time, where somebody has to pick one."""
        from ao_commons_kg.concepts import load_vocabulary
        extra = tmp_path / "extra.yml"
        extra.write_text(yaml.safe_dump({"concepts": [
            {"label": "Agent reputation", "topics": ["5.3"],
             "distinct_from_near_matches": "asserting it is different"},
        ]}), encoding="utf-8")
        with pytest.raises(ValueError, match="rename yours"):
            load_vocabulary(extra_path=extra)

    def test_a_distinct_idea_gets_in_by_being_named_distinctly(self, tmp_path):
        """The intended resolution: not a flag, a clearer label."""
        from ao_commons_kg.concepts import load_vocabulary
        extra = tmp_path / "extra.yml"
        extra.write_text(yaml.safe_dump({"concepts": [
            {"label": "Reputation portability between agent ecosystems",
             "topics": ["5.3"]},
        ]}), encoding="utf-8")
        assert "reputation-portability-between-agent-ecosystems" in load_vocabulary(
            extra_path=extra)

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

    def test_the_vocabulary_is_what_statements_use(self):
        """Not a predefined 523. The list grows bottom-up: a term enters when
        a claim needs it, and the taxonomy's subpoints are a pool to search
        before inventing a near-duplicate."""
        payload = self._committed()
        assert payload["counts"]["vocabulary"] == len(payload["vocabulary"])
        assert all(c["statements"] for c in payload["vocabulary"])
        assert payload["counts"]["vocabulary_from_claims"] > 0

    def test_suggestions_are_kept_apart_from_the_vocabulary(self):
        """Reporting the pool as the vocabulary would describe a predefined
        scheme this deliberately is not — and 506 of the 523 have never been
        reached for."""
        payload = self._committed()
        assert all(not c["statements"] for c in payload["suggestions"])
        assert payload["counts"]["suggestions_available"] == len(payload["suggestions"])
        assert payload["counts"]["suggestions_available"] > payload["counts"]["vocabulary"]

    def test_it_says_how_it_grows(self):
        assert "bottom-up" in self._committed()["how_this_grows"]

    def test_it_says_it_is_generated(self):
        """A build artifact that does not say so is one somebody hand-edits."""
        assert "do not edit" in self._committed()["generated_by"]

    def test_it_ships_its_own_collisions(self):
        """A list that hides its duplicates invites more trust than it has
        earned."""
        assert len(self._committed()["looks_like_one_idea"]) >= 8

    def test_every_term_records_whether_anything_uses_it(self):
        payload = self._committed()
        everything = payload["vocabulary"] + payload["suggestions"]
        assert all("statements" in c for c in everything)


class TestClaimTopicsAreDerived:
    """A statement's place in the taxonomy follows from what it argues about.

    The two layers used to be asserted separately and disagreed: on
    `arxiv:2511.03434` claim 2 the topic codes said 10.1 and 4.4 while the
    concept resolved to 5.3. Deriving one from the other removes the
    contradiction rather than documenting it.
    """

    def test_topics_come_from_the_claim_s_concepts(self):
        from ao_commons_kg.claims import claim_edges
        from ao_commons_kg.concepts import load_vocabulary

        vocab = load_vocabulary()
        claims = [c for c in load_claims() if c.resource_id == "resource:arxiv:2605.30169"]
        edges = claim_edges(claims, vocabulary=vocab)
        about = {e.target_id for e in edges if e.relation.value == "ABOUT"}
        assert "topic:5.3" in about, "reputation claims belong under inter-agent trust"

    def test_a_claim_with_no_concepts_falls_back_to_its_own_codes(self):
        """The fallback matters during the changeover. Without it, 62
        claim-to-topic edges vanished in one commit and nothing failed except
        a test that happened to assert the edge kind still existed."""
        from ao_commons_kg.claims import claim_edges
        from ao_commons_kg.models import Claim

        legacy = Claim(id="claim:x:1", resource_id="resource:x", text="t", quote="q",
                       topic_codes=["5.3"])
        about = [e for e in claim_edges([legacy]) if e.relation.value == "ABOUT"]
        assert [e.target_id for e in about] == ["topic:5.3"]

    def test_a_derived_topic_is_still_marked_inferred(self):
        """Deriving it does not make it read. A claim's topic is an inference
        either way."""
        from ao_commons_kg.claims import claim_edges
        from ao_commons_kg.concepts import load_vocabulary

        edges = claim_edges(load_claims(), vocabulary=load_vocabulary())
        about = [e for e in edges if e.relation.value == "ABOUT"]
        assert about and all(e.confidence_class.value == "INFERRED" for e in about)


class TestRelationAttribution:
    """Who made a judgement is the one thing this file cannot get wrong.

    Nine relations carried a person's name for two days and were drafted by
    a model — the exact failure the confidence class exists to prevent,
    committed in the file that exists to prevent it. A relation attributed
    to a human reads as settled, and none of these is.
    """

    def test_nothing_claims_a_human_asserted_it_until_one_has(self):
        from ao_commons_kg.claims import load_claim_relations
        for relation in load_claim_relations(claims=load_claims()):
            assert "unconfirmed" in (relation.extraction_method or ""), (
                f"{relation.source_id} -> {relation.target_id} is attributed to a "
                "person; if that is now true, this test should be the thing that "
                "changes, deliberately")

    def test_every_relation_still_carries_its_reasoning(self):
        """Re-attributing must not have cost the `because`."""
        from ao_commons_kg.claims import load_claim_relations
        assert all(r.source_location for r in load_claim_relations(claims=load_claims()))


class TestPrimaryAndContext:
    """Findings and positions are what the library is asked for. Background,
    method and limitation are how you judge one once you have it."""

    def test_the_split_follows_the_type(self):
        from ao_commons_kg.models import ClaimType
        assert ClaimType.FINDING.is_primary and ClaimType.POSITION.is_primary
        assert not any(t.is_primary for t in
                       (ClaimType.BACKGROUND, ClaimType.METHOD, ClaimType.LIMITATION))

    def test_context_travels_with_a_primary_from_its_own_paper(self):
        from ao_commons_kg.claims import context_for
        claims = load_claims()
        finding = next(c for c in claims if c.id == "claim:arxiv:2605.30169:4")
        context = context_for(finding, claims)
        assert context
        assert all(c.resource_id == finding.resource_id for c in context)
        assert all(not c.claim_type.is_primary for c in context)

    def test_context_does_not_have_context(self):
        """Not a refusal so much as a category answer: background does not
        have background."""
        from ao_commons_kg.claims import context_for
        claims = load_claims()
        background = next(c for c in claims if not c.claim_type.is_primary)
        assert context_for(background, claims) == []

    def test_proposals_run_between_primaries_by_default(self):
        """Eight of eleven proposed pairs involved a context statement, and
        the corpus has never produced a relation from that shape except as
        grounds. Without this the queue spends most of a reviewer's attention
        where nothing has ever been found."""
        from ao_commons_kg.claims import candidate_pairs, load_claim_relations
        claims = load_claims()
        relations = load_claim_relations(claims=claims)
        narrow = candidate_pairs(claims, relations)
        wide = candidate_pairs(claims, relations, primary_only=False)
        assert len(narrow) < len(wide)
        assert all(a.claim_type.is_primary and b.claim_type.is_primary
                   for a, b, _ in narrow)

    def test_context_pairs_are_still_reachable_when_asked_for(self):
        """Context does relate to a primary, as grounds — two of the twelve
        asserted relations are exactly that. Narrowing the default must not
        make them unfindable."""
        from ao_commons_kg.claims import candidate_pairs, load_claim_relations
        claims = load_claims()
        wide = candidate_pairs(claims, load_claim_relations(claims=claims),
                               primary_only=False)
        assert any(not a.claim_type.is_primary or not b.claim_type.is_primary
                   for a, b, _ in wide)
