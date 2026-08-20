"""The read layer the MCP server exposes.

Tested here rather than through the protocol, because the protocol is a
binding and this is the part that can be wrong in a way that matters.

Most of these are about provenance rather than retrieval. An agent asking this
corpus a question cannot tell a verified claim from a machine's guess unless
every answer says which it is, and it has no way to detect the difference
afterwards — so the tests that would catch a regression are the ones that
assert the caveats are still attached.
"""

import pytest

from ao_commons_kg.queries import (
    Corpus,
    coverage,
    get_author,
    get_claims,
    get_record,
    get_topic,
    related_records,
    search_records,
    search_topics,
)


@pytest.fixture(scope="module")
def corpus():
    return Corpus()


class TestTopics:
    def test_an_alias_finds_a_topic_whose_title_lacks_the_word(self, corpus):
        """"MARL" is nowhere in 15.6's title. A researcher types it anyway."""
        assert [t["code"] for t in search_topics(corpus, "MARL")][:1] == ["15.6"]

    def test_a_code_finds_its_own_topic(self, corpus):
        assert search_topics(corpus, "15.6")[0]["code"] == "15.6"

    def test_a_topic_carries_its_aliases_so_a_caller_can_see_why_it_matched(self, corpus):
        assert "MARL" in get_topic(corpus, "15.6")["also_known_as"]

    def test_filed_here_and_filed_below_are_separated(self, corpus):
        """"Nothing here" and "nothing under here" are different facts about a
        branch, and a caller deciding whether a topic is empty needs both."""
        topic = get_topic(corpus, "14.5")
        assert "records" in topic and "records_under_children" in topic

    def test_an_unknown_code_says_so_rather_than_returning_nothing(self, corpus):
        """An empty list reads as "nothing is filed there", which is a
        different answer from "that is not a topic"."""
        assert "error" in get_topic(corpus, "99.9")

    def test_a_one_letter_search_is_not_a_search(self, corpus):
        assert search_topics(corpus, "a") == []


class TestRecords:
    def test_a_record_says_whether_anyone_has_checked_it(self, corpus):
        found = search_records(corpus, "melting pot")
        assert found and all("review_status" in r for r in found)

    def test_records_are_findable_by_author(self, corpus):
        assert any("Rong" in " ".join(r["authors"])
                   for r in search_records(corpus, "Rong"))

    def test_a_record_carries_its_provenance(self, corpus):
        """Where a record came from decides how much of it to trust — a
        hand-curated entry and one a bot resolved are not the same evidence."""
        record = get_record(corpus, "resource:arxiv:2107.06857")
        assert record["provenance"]

    def test_an_unknown_record_says_so(self, corpus):
        assert "error" in get_record(corpus, "resource:arxiv:0000.00000")


class TestClaims:
    def test_every_claim_carries_the_sentence_it_came_from(self, corpus):
        """The load-bearing assertion of this whole layer. A claim without its
        quote cannot be checked, and an unchecked claim that arrives looking
        like a fact is the failure this project is built to avoid."""
        claims = get_claims(corpus, limit=100)["claims"]
        assert claims
        assert all(c["quoted_from_the_paper"].strip() for c in claims)

    def test_every_claim_says_whether_a_person_verified_it(self, corpus):
        claims = get_claims(corpus, limit=100)["claims"]
        assert all("review_status" in c and "verdict" in c for c in claims)

    def test_the_caveat_rides_along_even_on_a_narrow_query(self, corpus):
        """Filtering to one paper should not lose the fact that the layer as a
        whole is unverified — that is exactly when a caller stops noticing."""
        answer = get_claims(corpus, record="resource:arxiv:2107.06857")
        assert "checked by a person" in answer["caveat"]

    def test_claims_can_be_narrowed_to_a_record(self, corpus):
        answer = get_claims(corpus, record="resource:arxiv:2107.06857")
        assert answer["matched"] > 0
        assert all(c["of_record"] == "resource:arxiv:2107.06857" for c in answer["claims"])

    def test_findings_and_positions_can_be_told_apart(self, corpus):
        """Conflating them is how a graph comes to report that something was
        shown when it was only argued."""
        findings = get_claims(corpus, claim_type="finding")["matched"]
        positions = get_claims(corpus, claim_type="position")["matched"]
        assert findings and positions

    def test_the_unverified_filter_is_honest_while_nothing_is_verified(self, corpus):
        every = get_claims(corpus, limit=100)["matched"]
        assert get_claims(corpus, only_unverified=True, limit=100)["matched"] == every


class TestPeople:
    def test_a_person_is_found_without_punctuation_or_capitals(self, corpus):
        assert get_author(corpus, "joel z leibo")["name"] == "Joel Z. Leibo"

    def test_a_person_is_found_through_an_initial(self, corpus):
        assert get_author(corpus, "Botao Amber Hu")["record_count"] >= 1

    def test_somebody_absent_says_so_and_explains_the_matching(self, corpus):
        answer = get_author(corpus, "Ada Lovelace")
        assert "error" in answer and "initials" in answer["note"]

    def test_co_authors_exclude_the_person_asked_about(self, corpus):
        answer = get_author(corpus, "Joel Z. Leibo")
        assert "Joel Z. Leibo" not in answer["co_authors"]


class TestRelated:
    def test_read_and_computed_connections_are_kept_apart(self, corpus):
        """A citation is printed in the paper; a coupling score is something
        this project calculated. One list would let a caller read the second
        as the first."""
        answer = related_records(corpus, "resource:arxiv:2606.16613")
        assert set(answer) >= {"cites", "cited_by", "shares_references_with"}
        assert "not a claim by either paper" in answer["how_to_read_this"]

    def test_a_computed_edge_carries_its_method_and_score(self, corpus):
        coupled = related_records(corpus, "resource:arxiv:2606.16613")["shares_references_with"]
        assert coupled and all(c["method"] and "score" in c for c in coupled)


class TestCoverage:
    def test_it_reports_what_has_not_been_checked(self, corpus):
        stats = coverage(corpus)
        assert stats["records"] > 0
        assert "records_reviewed_by_a_person" in stats
        assert "claims_verified_by_a_person" in stats

    def test_it_tells_a_caller_how_to_weigh_the_rest(self, corpus):
        assert "first pass" in coverage(corpus)["what_this_means"]
