"""Filings entering the gold set.

A filing is a human judgement joining the only dataset that measures
everything else, so this is strict where it matters and forgiving where it
does not: fussy about topic codes and record ids, relaxed about whether
someone remembered the code fence.
"""

import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from merge_filing import (  # noqa: E402
    FilingError,
    extract,
    merge,
    merge_claims,
    summarize,
    summarize_claims,
    validate,
    validate_claims,
    validate_new_statements,
)

KNOWN_RECORDS = {"resource:arxiv:2502.14143", "resource:tool:paperclip"}
KNOWN_TOPICS = {"11.1", "11.6", "2.2", "2.2.2", "4.1"}

FILING = """Here is what I did.

```yaml
records:
  resource:arxiv:2502.14143:
    topics: ["11.1", "11.6"]
    reviewed_on: 2026-08-13
```

Thanks!
"""


class TestExtract:
    def test_reads_a_fenced_block(self):
        assert "resource:arxiv:2502.14143" in extract(FILING)["records"]

    def test_reads_a_bare_paste_too(self):
        """Rejecting good work over a missing code fence would be a poor
        trade for the strictness it buys."""
        bare = 'records:\n  resource:tool:paperclip:\n    topics: ["2.2"]\n'
        assert "resource:tool:paperclip" in extract(bare)["records"]

    def test_prose_with_no_filing_is_a_clear_error(self):
        with pytest.raises(FilingError, match="No filing found"):
            extract("I reviewed some papers but forgot to paste anything.")

    def test_a_broken_block_does_not_crash_the_parse(self):
        with pytest.raises(FilingError):
            extract("```yaml\nrecords: [unclosed\n```")


class TestValidate:
    def test_a_good_filing_is_normalized(self):
        cleaned = validate(extract(FILING), known_records=KNOWN_RECORDS, known_topics=KNOWN_TOPICS)
        assert cleaned["resource:arxiv:2502.14143"]["topics"] == ["11.1", "11.6"]

    def test_topics_sort_numerically(self):
        payload = {"records": {"resource:tool:paperclip": {"topics": ["11.6", "2.2", "4.1"]}}}
        cleaned = validate(payload, known_records=KNOWN_RECORDS, known_topics=KNOWN_TOPICS)
        assert cleaned["resource:tool:paperclip"]["topics"] == ["2.2", "4.1", "11.6"]

    def test_an_unknown_topic_code_stops_the_merge(self):
        """A typo here would rot the baseline everything else is measured
        against, quietly."""
        payload = {"records": {"resource:tool:paperclip": {"topics": ["2.2", "99.9"]}}}
        with pytest.raises(FilingError, match="99.9"):
            validate(payload, known_records=KNOWN_RECORDS, known_topics=KNOWN_TOPICS)

    def test_an_unknown_record_stops_the_merge(self):
        payload = {"records": {"resource:arxiv:0000.00000": {"topics": ["2.2"]}}}
        with pytest.raises(FilingError, match="not a record"):
            validate(payload, known_records=KNOWN_RECORDS, known_topics=KNOWN_TOPICS)

    def test_every_problem_is_reported_at_once(self):
        """Fixing one error at a time across a round trip each is a good way
        to lose a contributor."""
        payload = {"records": {
            "resource:arxiv:0000.00000": {"topics": ["2.2"]},
            "resource:tool:paperclip": {"topics": ["99.9"]},
        }}
        with pytest.raises(FilingError) as caught:
            validate(payload, known_records=KNOWN_RECORDS, known_topics=KNOWN_TOPICS)
        assert "0000.00000" in str(caught.value) and "99.9" in str(caught.value)

    def test_unquoted_codes_are_refused_rather_than_coerced(self):
        """`topics: [11.10]` parses as the float 11.1, which is a different
        topic in this taxonomy. str() cannot recover which was meant, so the
        only safe answer is to refuse and say why."""
        payload = yaml.safe_load("records:\n  resource:tool:paperclip:\n    topics: [11.10]\n")
        with pytest.raises(FilingError, match="must be quoted"):
            validate(payload, known_records=KNOWN_RECORDS, known_topics=KNOWN_TOPICS | {"11.10"})

    def test_quoted_codes_survive_intact(self):
        payload = yaml.safe_load('records:\n  resource:tool:paperclip:\n    topics: ["11.10"]\n')
        cleaned = validate(payload, known_records=KNOWN_RECORDS, known_topics={"11.10"})
        assert cleaned["resource:tool:paperclip"]["topics"] == ["11.10"]

    def test_none_apply_is_a_valid_filing(self):
        payload = {"records": {"resource:tool:paperclip": {"topics": []}}}
        cleaned = validate(payload, known_records=KNOWN_RECORDS, known_topics=KNOWN_TOPICS)
        assert cleaned["resource:tool:paperclip"]["topics"] == []

    def test_an_empty_filing_is_refused(self):
        with pytest.raises(FilingError, match="empty"):
            validate({"records": {}}, known_records=KNOWN_RECORDS, known_topics=KNOWN_TOPICS)


class TestMerge:
    def test_a_new_decision_is_added(self, tmp_path):
        gold = tmp_path / "tags.yml"
        result = merge({"resource:tool:paperclip": {"topics": ["2.2"], "reviewed_on": "2026-08-13"}},
                       "anke", gold)
        assert result["added"] == ["resource:tool:paperclip"]
        stored = yaml.safe_load(gold.read_text())["records"]["resource:tool:paperclip"]
        assert stored["reviewer"] == "anke"

    def test_disagreement_is_surfaced_not_buried(self, tmp_path):
        """Two reviewers reading the same paper differently is the signal a
        gold set exists to capture. Merging both answers into a union would
        destroy it."""
        gold = tmp_path / "tags.yml"
        merge({"resource:tool:paperclip": {"topics": ["2.2"], "reviewed_on": "2026-08-13"}}, "anke", gold)
        result = merge({"resource:tool:paperclip": {"topics": ["4.1"], "reviewed_on": "2026-08-14"}}, "sam", gold)

        assert result["changed"] and not result["added"]
        record, before, after, who = result["changed"][0]
        assert before == ["2.2"] and after == ["4.1"] and who == "anke"
        assert yaml.safe_load(gold.read_text())["records"][record]["topics"] == ["4.1"]

    def test_an_identical_refiling_is_not_a_change(self, tmp_path):
        gold = tmp_path / "tags.yml"
        entry = {"resource:tool:paperclip": {"topics": ["2.2"], "reviewed_on": "2026-08-13"}}
        merge(entry, "anke", gold)
        result = merge(entry, "sam", gold)
        assert result["unchanged"] and not result["changed"]

    def test_other_records_are_left_alone(self, tmp_path):
        gold = tmp_path / "tags.yml"
        merge({"resource:arxiv:2502.14143": {"topics": ["11.1"], "reviewed_on": "d"}}, "anke", gold)
        merge({"resource:tool:paperclip": {"topics": ["2.2"], "reviewed_on": "d"}}, "sam", gold)
        assert len(yaml.safe_load(gold.read_text())["records"]) == 2

    def test_the_summary_names_the_disagreement(self, tmp_path):
        gold = tmp_path / "tags.yml"
        merge({"resource:tool:paperclip": {"topics": ["2.2"], "reviewed_on": "d"}}, "anke", gold)
        result = merge({"resource:tool:paperclip": {"topics": ["4.1"], "reviewed_on": "d"}}, "sam", gold)
        text = summarize(result, "sam")
        assert "Disagreements" in text and "anke" in text and "4.1" in text


class TestJudgements:
    """A reviewer's read of the record is worth as much as their codes."""

    def test_out_of_scope_and_no_fit_are_kept_apart(self):
        """They were one button and one meaning before. Out of scope is an
        ingestion error; nothing fits is a taxonomy gap and a proposal waiting
        to happen."""
        payload = {"records": {
            "resource:tool:paperclip": {"topics": [], "verdict": "out-of-scope"},
            "resource:arxiv:2502.14143": {"topics": [], "verdict": "no-topic-fits"},
        }}
        cleaned = validate(payload, known_records=KNOWN_RECORDS, known_topics=KNOWN_TOPICS)
        assert cleaned["resource:tool:paperclip"]["verdict"] == "out-of-scope"
        assert cleaned["resource:arxiv:2502.14143"]["verdict"] == "no-topic-fits"

    def test_an_unknown_verdict_is_refused(self):
        payload = {"records": {"resource:tool:paperclip": {"topics": [], "verdict": "maybe"}}}
        with pytest.raises(FilingError, match="unknown verdict"):
            validate(payload, known_records=KNOWN_RECORDS, known_topics=KNOWN_TOPICS)

    def test_filed_is_the_default_and_is_not_stored(self):
        """Storing the common case would put a redundant field on every row."""
        payload = {"records": {"resource:tool:paperclip": {"topics": ["2.2"], "verdict": "filed"}}}
        cleaned = validate(payload, known_records=KNOWN_RECORDS, known_topics=KNOWN_TOPICS)
        assert "verdict" not in cleaned["resource:tool:paperclip"]

    def test_uncertainty_survives(self):
        payload = {"records": {"resource:tool:paperclip": {"topics": ["2.2"], "unsure": True}}}
        cleaned = validate(payload, known_records=KNOWN_RECORDS, known_topics=KNOWN_TOPICS)
        assert cleaned["resource:tool:paperclip"]["unsure"] is True

    def test_a_note_survives(self):
        payload = {"records": {"resource:tool:paperclip": {
            "topics": ["2.2"], "note": "  torn between 2.2 and 3.1  "}}}
        cleaned = validate(payload, known_records=KNOWN_RECORDS, known_topics=KNOWN_TOPICS)
        assert cleaned["resource:tool:paperclip"]["note"] == "torn between 2.2 and 3.1"

    def test_the_summary_surfaces_gaps_and_notes(self, tmp_path):
        gold = tmp_path / "tags.yml"
        result = merge({
            "resource:tool:paperclip": {
                "topics": [], "reviewed_on": "d", "verdict": "no-topic-fits",
                "note": "execution control, not permissions",
            },
            "resource:arxiv:2502.14143": {
                "topics": [], "reviewed_on": "d", "verdict": "out-of-scope"},
        }, "anke", gold)
        text = summarize(result, "anke")
        assert "Nothing in the taxonomy fitted" in text
        assert "out of scope" in text.lower()
        assert "execution control" in text


KNOWN_CLAIMS = {"claim:arxiv:2502.14143:1", "claim:arxiv:2502.14143:2"}

BOTH = """```yaml
records:
  resource:arxiv:2502.14143:
    topics: ["11.1"]
claims:
  claim:arxiv:2502.14143:1:
    verdict: accurate
  claim:arxiv:2502.14143:2:
    verdict: overstated
    note: the source says "in some runs", the paraphrase says "reliably"
```
"""


class TestBothJudgements:
    """One reviewer, one sitting, two judgements. The expensive part is reading
    the paper, and it should be paid once — but the two land in different files
    because they measure different things."""

    def test_a_filing_can_carry_both(self):
        payload = extract(BOTH)
        assert "resource:arxiv:2502.14143" in payload["records"]
        assert "claim:arxiv:2502.14143:1" in payload["claims"]

    def test_claim_verdicts_are_validated_against_the_corpus(self):
        cleaned = validate_claims(extract(BOTH), known_claims=KNOWN_CLAIMS)
        assert cleaned["claim:arxiv:2502.14143:2"]["verdict"] == "overstated"
        assert "reliably" in cleaned["claim:arxiv:2502.14143:2"]["note"]

    def test_a_verdict_on_a_claim_that_does_not_exist_is_refused(self):
        """Otherwise the review is silently discarded, and the reviewer only
        finds out much later that their time bought nothing."""
        payload = {"claims": {"claim:nope:1": {"verdict": "accurate"}}}
        with pytest.raises(FilingError, match="not a claim"):
            validate_claims(payload, known_claims=KNOWN_CLAIMS)

    def test_an_unknown_verdict_is_refused(self):
        payload = {"claims": {"claim:arxiv:2502.14143:1": {"verdict": "seems right"}}}
        with pytest.raises(FilingError, match="unknown verdict"):
            validate_claims(payload, known_claims=KNOWN_CLAIMS)

    def test_a_bare_string_verdict_is_accepted(self):
        payload = {"claims": {"claim:arxiv:2502.14143:1": "accurate"}}
        cleaned = validate_claims(payload, known_claims=KNOWN_CLAIMS)
        assert cleaned["claim:arxiv:2502.14143:1"]["verdict"] == "accurate"

    def test_claims_only_filings_are_allowed(self):
        """A reviewer who checked claims and no tags has done real work, and it
        is the work this layer needs most."""
        payload = extract("claims:\n  claim:arxiv:2502.14143:1:\n    verdict: accurate\n")
        assert validate(payload, known_records=KNOWN_RECORDS, known_topics=KNOWN_TOPICS,
                        require=False) == {}

    def test_verdicts_go_to_their_own_file(self, tmp_path):
        gold = tmp_path / "claims.yml"
        cleaned = validate_claims(extract(BOTH), known_claims=KNOWN_CLAIMS)
        result = merge_claims(cleaned, "anke", gold)
        assert result["total"] == 2
        stored = yaml.safe_load(gold.read_text())["claims"]
        assert stored["claim:arxiv:2502.14143:1"]["reviewer"] == "anke"

    def test_extraction_failures_are_surfaced_not_buried(self, tmp_path):
        """`overstated` and `not-in-source` are feedback on the extractor, and
        a summary that only counted verdicts would waste them."""
        gold = tmp_path / "claims.yml"
        cleaned = validate_claims(extract(BOTH), known_claims=KNOWN_CLAIMS)
        text = "\n".join(summarize_claims(merge_claims(cleaned, "anke", gold)))
        assert "Extraction got these wrong" in text
        assert "claim:arxiv:2502.14143:2" in text
        assert "claim:arxiv:2502.14143:1" not in text

    def test_disagreement_on_a_claim_is_surfaced(self, tmp_path):
        gold = tmp_path / "claims.yml"
        merge_claims({"claim:arxiv:2502.14143:1": {"verdict": "accurate"}}, "anke", gold)
        result = merge_claims({"claim:arxiv:2502.14143:1": {"verdict": "overstated"}}, "sam", gold)
        assert result["changed"] == [("claim:arxiv:2502.14143:1", "accurate", "overstated", "anke")]


class TestNewStatements:
    """A reviewer who has just read the paper is the only one positioned to
    notice what the extractor missed — held to the machine's standard, because
    a standard that depends on who wrote the statement is not one."""

    def test_a_statement_needs_a_quote(self):
        payload = {"new_statements": {"resource:tool:paperclip": [
            {"type": "finding", "text": "This tool caps agent spending."}]}}
        with pytest.raises(FilingError, match="no quote"):
            validate_new_statements(payload, known_records=KNOWN_RECORDS)

    def test_a_statement_needs_text(self):
        payload = {"new_statements": {"resource:tool:paperclip": [
            {"type": "finding", "quote": "Budgets auto-pause execution when limits are hit."}]}}
        with pytest.raises(FilingError, match="no statement text"):
            validate_new_statements(payload, known_records=KNOWN_RECORDS)

    def test_an_unknown_type_is_refused(self):
        payload = {"new_statements": {"resource:tool:paperclip": [
            {"type": "vibe", "text": "This tool caps agent spending.",
             "quote": "Budgets auto-pause execution when limits are hit."}]}}
        with pytest.raises(FilingError, match="unknown type"):
            validate_new_statements(payload, known_records=KNOWN_RECORDS)

    def test_background_is_a_type_a_reviewer_can_use(self):
        payload = {"new_statements": {"resource:tool:paperclip": [
            {"type": "background", "text": "No accepted benchmark existed at the time.",
             "quote": "There is no widely accepted benchmark for this class of system."}]}}
        cleaned = validate_new_statements(payload, known_records=KNOWN_RECORDS)
        assert cleaned["resource:tool:paperclip"][0]["type"] == "background"

    def test_a_statement_against_an_unknown_record_is_refused(self):
        payload = {"new_statements": {"resource:arxiv:0000.00000": [
            {"type": "finding", "text": "Something about a paper we do not hold.",
             "quote": "A sentence from a paper that is not in this corpus."}]}}
        with pytest.raises(FilingError, match="not a record"):
            validate_new_statements(payload, known_records=KNOWN_RECORDS)

    def test_no_new_statements_is_the_normal_case(self):
        assert validate_new_statements({}, known_records=KNOWN_RECORDS) == {}

    def test_a_filing_of_only_new_statements_is_allowed(self):
        body = ('new_statements:\n  resource:tool:paperclip:\n    - type: finding\n'
                '      text: "This tool caps agent spending."\n'
                '      quote: "Budgets auto-pause execution when limits are hit."\n')
        assert "resource:tool:paperclip" in extract(body)["new_statements"]


class TestReviewPayload:
    """What the review surface is given.

    The layer this guards was built and then invisible for a week: claims
    carried attribution, concepts and relations, `build_site` passed nine
    fields and none of them were these, and the page could not show what
    the corpus knew. Nothing failed — the data was simply not there.
    """

    def _payload(self):
        import sys
        from pathlib import Path
        repo = Path(__file__).resolve().parent.parent
        sys.path.insert(0, str(repo / "scripts"))
        sys.path.insert(0, str(repo / "src"))
        from build_site import build_payload
        return build_payload()

    def test_claims_carry_their_concepts(self):
        payload = self._payload()
        claims = [c for r in payload["records"] for c in r.get("claims", [])]
        assert claims
        assert any(c["concepts"] for c in claims), (
            "no claim reached the page with a concept — the tag layer is "
            "invisible to every reviewer")

    def test_borrowed_claims_are_marked_for_the_reviewer(self):
        """A reviewer asked "is this paraphrase accurate" about somebody
        else's claim will answer yes and endorse an attribution nobody
        checked."""
        payload = self._payload()
        claims = [c for r in payload["records"] for c in r.get("claims", [])]
        borrowed = [c for c in claims if not c["own"]]
        assert borrowed
        assert all(c["from_whom"] for c in borrowed)

    def test_relations_reach_the_page_and_both_ends_resolve(self):
        """An unresolvable end renders as a raw claim id, which tells a
        reviewer nothing."""
        payload = self._payload()
        known = {c["id"] for r in payload["records"] for c in r.get("claims", [])}
        assert payload["relations"]
        for relation in payload["relations"]:
            assert relation["source"] in known
            assert relation["target"] in known
            assert relation["because"], "a relation with no reasoning cannot be judged"

    def test_a_drafted_relation_is_marked_unconfirmed_on_the_page(self):
        """The reviewer has to be able to tell a machine's suggestion from
        a person's judgement, and the review surface is where it matters
        most — it is the screen where the confirming happens."""
        payload = self._payload()
        drafted = [r for r in payload["relations"] if r["unconfirmed"]]
        assert drafted, "three relations are awaiting confirmation and none is flagged"

    def test_every_concept_a_claim_cites_has_an_entry(self):
        """Otherwise the page renders a slug where a label should be, and
        the click goes nowhere."""
        payload = self._payload()
        cited = {t for r in payload["records"]
                 for c in r.get("claims", []) for t in c["concepts"]}
        assert cited <= set(payload["concepts"])

    def test_a_concept_entry_lists_the_claims_under_it(self):
        payload = self._payload()
        entry = payload["concepts"]["agent-reputation-systems"]
        assert entry["label"] == "Agent reputation systems"
        assert len(entry["claims"]) > 1, "a concept on one claim connects nothing"


class TestReviewSurface:
    """The reviewer is asked one thing: is this statement what the paper says.

    Filing was removed from this screen entirely. Naming what a paper is
    "about" derives from the concepts on its statements, and asking a
    reviewer for it as well was asking them to redo, from an abstract, a
    judgement the statements make better.
    """

    def _page(self):
        from pathlib import Path
        return (Path(__file__).resolve().parent.parent
                / "site" / "template.html").read_text(encoding="utf-8")

    def test_the_filing_question_is_gone(self):
        page = self._page()
        assert "And where does it belong?" not in page
        assert "Which topics does this belong under?" not in page

    def test_three_actions_not_four_verdicts(self):
        """A reviewer is deciding what the library should hold, not filling
        in a diagnostic form."""
        page = self._page()
        for label in ('"Add as is"', '"Adjust"', '"Remove"'):
            assert label in page
        assert '"Overstated"' not in page, "the diagnostic verdict set is gone"

    def test_adjusting_edits_the_statement_not_the_quote(self):
        """The quote is what the statement is checked against. A reviewer who
        can edit both can make anything true."""
        page = self._page()
        assert "The statement, in your words" in page
        assert "the quote is not editable" in page.lower() or \
               "not editable" in page.lower()

    def test_tags_follow_an_edit(self):
        """A statement edited from reputation to sanctions is about something
        else now, and the old tag would connect it to the wrong statements —
        quietly, since a wrong link looks exactly like a right one."""
        page = self._page()
        assert "function retag(" in page
        assert "tags follow the wording" in page

    def test_an_edit_that_matches_nothing_keeps_the_extracted_tags(self):
        """Never strand a statement with no tag at all."""
        page = self._page()
        assert "picked.length ? picked : (claim.concepts || [])" in page

    def test_an_adjustment_reaches_the_submission(self):
        """Otherwise the verdict says "adjusted" and carries no adjustment,
        and the edit is lost between the browser and the repository."""
        page = self._page()
        assert 'lines.push(`    text: ${JSON.stringify(c.text)}`)' in page
        assert "concepts: [" in page

    def test_a_paper_is_finished_when_its_statements_are_judged(self):
        """Filing is gone, so there is no button to press. This signal is
        true rather than declared."""
        page = self._page()
        assert "function outstanding(record)" in page
        assert "outstanding(r) > 0" in page

    def test_a_record_with_nothing_extracted_says_it_is_not_your_turn(self):
        page = self._page()
        assert "waiting on extraction, not on you" in page

    def test_every_statement_type_is_explained(self):
        """`background` was missing from the page's list for as long as the
        list existed, so those statements rendered a bare label while the
        others carried an explanation — and background is the type where the
        hardest question lives, since it is usually somebody else's result."""
        page = self._page()
        for kind in ("finding", "position", "method", "background", "limitation"):
            assert f"{kind}: [" in page, f"{kind} has no explanation on the review card"

    def test_the_review_text_colour_passes_contrast(self):
        """`--faint` carries the quote, the context line and every hint on
        this screen — most of what a reviewer reads — and was 2.87:1 against
        the sunk surface, below AA on every surface in both themes."""
        import re

        page = self._page()

        def lum(value):
            value = value.lstrip("#")
            channels = [int(value[i:i + 2], 16) / 255 for i in (0, 2, 4)]
            channels = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
                        for c in channels]
            return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]

        def ratio(a, b):
            high, low = sorted([lum(a), lum(b)], reverse=True)
            return (high + 0.05) / (low + 0.05)

        for theme, pattern in (("light", r":root \{(.*?)\}"),
                               ("dark", r':root\[data-theme="dark"\] \{(.*?)\}')):
            block = re.search(pattern, page, re.S).group(1)
            def token(name):
                return re.search(rf"--{name}:\s*(#[0-9a-f]{{6}})", block).group(1)
            for surface in ("card", "sunk"):
                assert ratio(token("faint"), token(surface)) >= 4.5, (
                    f"--faint fails AA on --{surface} in the {theme} theme")

    def test_the_statement_blurb_is_gone(self):
        """Three paragraphs of rationale stood between a reviewer and the
        work. The rationale is still behind the info marker."""
        page = self._page()
        assert "read out of the paper automatically" not in page
        assert "where the full text was available" not in page

    def test_it_reads_as_a_task_with_an_end(self):
        page = self._page()
        assert 'className: "progress"' in page
        assert "All statements checked" in page
        assert "Check ${left} statement" in page

    def test_a_judged_statement_steps_back(self):
        """What is left should be findable by scrolling rather than by
        reading every card."""
        page = self._page()
        assert ".claim.judged" in page
        assert '(settled ? " judged" : "")' in page

    def test_statements_are_grouped_by_what_they_are_for(self):
        """Findings and positions are what the library is asked for; the
        rest is how you judge one. Interleaved, a reviewer reads eleven
        supporting statements at the same weight as the twenty-one carrying
        the argument."""
        page = self._page()
        assert "What this paper shows and argues" in page
        assert "Context for judging those" in page
        assert 'record.claims.filter(c => c.primary !== false)' in page

    def test_the_type_is_a_badge_not_a_word_in_a_row_of_grey_words(self):
        page = self._page()
        assert ".type-badge" in page
        assert ".type-badge.primary" in page and ".type-badge.supporting" in page

    def test_each_group_says_how_much_is_left_in_it(self):
        page = self._page()
        assert 'className: "g-count"' in page
        assert "${openLeft} to check" in page


class TestPrimaryReachesThePage:
    def _payload(self):
        import sys
        from pathlib import Path
        repo = Path(__file__).resolve().parent.parent
        sys.path.insert(0, str(repo / "scripts"))
        sys.path.insert(0, str(repo / "src"))
        from build_site import build_payload
        return build_payload()

    def test_every_claim_says_whether_it_is_primary(self):
        """Shipped from the model rather than re-derived in the page. Which
        types are primary is a judgement about what the library is for, and
        it should have one home."""
        claims = [c for r in self._payload()["records"] for c in r.get("claims", [])]
        assert claims
        assert all("primary" in c for c in claims)

    def test_the_split_matches_the_model(self):
        from ao_commons_kg.models import ClaimType
        claims = [c for r in self._payload()["records"] for c in r.get("claims", [])]
        for claim in claims:
            assert claim["primary"] is ClaimType(claim["type"]).is_primary


class TestTemporarilyHidden:
    """Two things are out of the reviewer's way while extraction and tagging
    are being settled. Both are hidden rather than deleted, and both have a
    comment in the source saying when they come back."""

    def _page(self):
        from pathlib import Path
        return (Path(__file__).resolve().parent.parent
                / "site" / "template.html").read_text(encoding="utf-8")

    def test_relations_are_not_shown_on_a_statement_card(self):
        """Twelve relations across thirty-two statements is not yet a layer
        worth meeting mid-task — it is three paragraphs of reasoning between
        one statement and the next."""
        page = self._page()
        assert 'className: "rel-kind"' not in page.split("function showConcept")[0]

    def test_relations_are_still_in_the_data(self):
        """Hidden from one screen, not removed from the corpus."""
        from ao_commons_kg.claims import load_claim_relations, load_claims
        assert len(load_claim_relations(claims=load_claims())) == 12

    def test_the_taxonomy_tree_is_hidden_not_deleted(self):
        page = self._page()
        assert '<div id="tree" hidden></div>' in page
        # Matched on one line: the comment wraps, and asserting across the
        # break is a test that can never pass however right the code is.
        assert "Unhide both when the vocabulary has" in page


class TestSubmitPath:
    """Somebody reviewing one paper and stopping is the normal case. The
    step between doing the work and the work counting for anything should
    not be finding the tab that sends it."""

    def _page(self):
        from pathlib import Path
        return (Path(__file__).resolve().parent.parent
                / "site" / "template.html").read_text(encoding="utf-8")

    def test_submit_is_the_primary_action(self):
        page = self._page()
        assert 'el("button", { className: "btn primary" }, "Submit")' in page
        assert '"btn primary" }, "Next paper")' not in page

    def test_submit_goes_to_submit(self):
        page = self._page()
        block = page.split('el("button", { className: "btn primary" }, "Submit")')[1][:600]
        assert 'setMode("export")' in block
        assert "loadSubmissions(false)" in block

    def test_it_is_disabled_until_there_is_something_to_send(self):
        """An enabled button that submits nothing teaches people the button
        does nothing."""
        page = self._page()
        assert "submit.disabled = !judgedTotal();" in page
