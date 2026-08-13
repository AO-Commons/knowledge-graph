"""One person, one spelling.

The cases here are the real ones from the corpus: two metadata sources
punctuating a middle initial differently, and — the one nobody spots by eye —
two different Unicode hyphens.
"""

from ao_commons_kg.people import (
    apply_index,
    build_index,
    canonical,
    duplicates,
    fold,
)


class TestFold:
    def test_a_missing_period_folds(self):
        assert fold("Joel Z. Leibo") == fold("Joel Z Leibo")

    def test_two_unicode_hyphens_fold(self):
        """U+002D and U+2010 render almost identically. This is the duplicate
        a person will never find by reading."""
        assert fold("Edgar A. Duéñez-Guzmán") == fold("Edgar A. Duéñez‐Guzmán")

    def test_accents_fold(self):
        assert fold("Duéñez-Guzmán") == fold("Duenez-Guzman")

    def test_initials_are_not_expanded(self):
        """Merging these needs evidence this module does not have, and a
        wrong merge is much harder to notice than a missed one."""
        assert fold("J. Leibo") != fold("Joel Z. Leibo")

    def test_different_people_stay_different(self):
        assert fold("Alan Chan") != fold("Alan Chen")


class TestCanonical:
    def test_the_more_complete_spelling_wins_a_tie(self):
        """Trivedi appears once each way in the corpus, so frequency cannot
        decide it — which is exactly when a rule is needed."""
        assert canonical({"Rakshit S. Trivedi": 1, "Rakshit S Trivedi": 1}) == "Rakshit S. Trivedi"

    def test_completeness_outranks_frequency(self):
        """A stripped spelling is a lossy rendering of the same name, not a
        competing opinion about it."""
        assert canonical({"Joel Z Leibo": 12, "Joel Z. Leibo": 1}) == "Joel Z. Leibo"

    def test_accents_are_preferred(self):
        assert canonical({"Duenez-Guzman": 5, "Duéñez-Guzmán": 1}) == "Duéñez-Guzmán"

    def test_the_choice_is_deterministic(self):
        spellings = {"A B": 1, "A. B": 1, "A.B.": 1}
        assert canonical(spellings) == canonical(dict(reversed(list(spellings.items()))))


class TestIndex:
    def test_only_genuine_variants_are_indexed(self):
        """Applying the index has to be a no-op for almost every name."""
        index = build_index(["Joel Z. Leibo", "Joel Z Leibo", "Alan Chan"])
        assert index == {"Joel Z Leibo": "Joel Z. Leibo"}

    def test_a_lone_spelling_is_left_alone(self):
        assert build_index(["Alan Chan", "Alan Chan"]) == {}

    def test_authorship_order_is_preserved(self):
        """Order carries meaning in a byline; sorting would destroy it."""
        index = {"Joel Z Leibo": "Joel Z. Leibo"}
        assert apply_index(["Alan Chan", "Joel Z Leibo", "Iyad Rahwan"], index) == [
            "Alan Chan", "Joel Z. Leibo", "Iyad Rahwan",
        ]

    def test_a_record_holding_both_spellings_collapses_to_one(self):
        index = {"Joel Z Leibo": "Joel Z. Leibo"}
        assert apply_index(["Joel Z. Leibo", "Alan Chan", "Joel Z Leibo"], index) == [
            "Joel Z. Leibo", "Alan Chan",
        ]

    def test_empty_authors_are_fine(self):
        assert apply_index([], {}) == [] and apply_index(None, {}) == []


class TestReport:
    def test_duplicates_are_reported_under_the_canonical_name(self):
        found = duplicates(["Joel Z. Leibo", "Joel Z Leibo", "Alan Chan"])
        assert list(found) == ["Joel Z. Leibo"]
        assert found["Joel Z. Leibo"] == {"Joel Z. Leibo": 1, "Joel Z Leibo": 1}


def test_the_corpus_holds_no_split_people():
    """A regression guard on the real data. Ingesting a new source is exactly
    when this comes back."""
    from ao_commons_kg.resources import load_resources

    names = [a for r in load_resources() for a in (r.authors or [])]
    assert duplicates(names) == {}
