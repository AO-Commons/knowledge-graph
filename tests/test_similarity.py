"""Structure-based relatedness.

Both measures work on reference lists alone and read no titles. That is the
point: the keyword pre-filter has a ceiling, and structure is what gets past
it.
"""

from ao_commons_kg.graph import (
    bibliographic_coupling,
    co_citation_counts,
    co_cited_pairs,
    connectivity,
    similarity_edges,
)

# A cites X, Y, Z. B cites X, Y, W. C cites nothing in common.
REFERENCES = {
    "W_A": ["W_X", "W_Y", "W_Z"],
    "W_B": ["W_X", "W_Y", "W_W"],
    "W_C": ["W_Q", "W_R"],
}


class TestBibliographicCoupling:
    def test_shared_references_make_a_pair(self):
        """Neither cites the other and neither shares vocabulary; they are
        related because they build on the same work."""
        couplings = bibliographic_coupling(REFERENCES, min_shared=2)
        assert [(c.source, c.target) for c in couplings] == [("W_A", "W_B")]
        assert couplings[0].shared == 2

    def test_scoring_is_normalized_not_raw_overlap(self):
        """Raw overlap rewards long bibliographies, which is a property of
        the paper rather than of the relationship."""
        narrow = {"a": ["1", "2", "3"], "b": ["1", "2", "4"]}
        broad = {"a": ["1", "2"] + [str(i) for i in range(10, 60)],
                 "b": ["1", "2"] + [str(i) for i in range(60, 110)]}
        assert (bibliographic_coupling(narrow)[0].score
                > bibliographic_coupling(broad)[0].score)

    def test_a_single_shared_reference_is_not_evidence(self):
        """Usually a canonical work everyone cites."""
        assert bibliographic_coupling({"a": ["1", "2"], "b": ["1", "9"]},
                                      min_shared=2) == []

    def test_works_without_references_are_skipped(self):
        assert bibliographic_coupling({"a": [], "b": []}) == []

    def test_output_is_ordered_deterministically(self):
        assert (bibliographic_coupling(REFERENCES)
                == bibliographic_coupling(dict(reversed(list(REFERENCES.items())))))


class TestCoCitation:
    def test_counts_how_many_of_ours_cite_each_work(self):
        counts = co_citation_counts(REFERENCES)
        assert counts["W_X"] == 2 and counts["W_Z"] == 1

    def test_a_work_cited_twice_by_one_paper_counts_once(self):
        assert co_citation_counts({"a": ["W_X", "W_X"]})["W_X"] == 1

    def test_co_cited_pairs_are_related_by_our_own_citing(self):
        pairs = co_cited_pairs(REFERENCES, min_shared=2)
        assert ("W_X", "W_Y") in [(p.source, p.target) for p in pairs]


class TestConnectivity:
    def test_candidates_are_scored_by_attachment_not_text(self):
        candidates = {"W_NEW": ["W_X", "W_Y"], "W_FAR": ["W_ZZZ"]}
        scores = connectivity(candidates, REFERENCES)
        assert scores["W_NEW"][0] == 2, "shares two references with the corpus"
        assert scores["W_FAR"][0] == 0

    def test_being_cited_by_the_corpus_counts(self):
        scores = connectivity({"W_X": []}, REFERENCES)
        assert scores["W_X"][1] == 2


class TestEdges:
    def test_edges_carry_their_method_and_score(self):
        """A similarity whose method is hidden cannot be interpreted."""
        edges = similarity_edges(REFERENCES, {"W_A": "resource:a", "W_B": "resource:b"})
        assert len(edges) == 1
        edge = edges[0].to_dict()
        assert edge["method"] == "bibliographic-coupling"
        assert 0 < edge["score"] <= 1
        assert edge["relation"] == "SIMILAR_TO"

    def test_unresolvable_pairs_are_dropped_not_dangled(self):
        assert similarity_edges(REFERENCES, {"W_A": "resource:a"}) == []

    def test_similar_to_never_carries_a_confidence_class(self):
        """It is computed, not judged — a different kind of claim from an
        inferred edge, and the schema keeps them apart."""
        edge = similarity_edges(REFERENCES, {"W_A": "a", "W_B": "b"})[0]
        assert edge.confidence_class is None
