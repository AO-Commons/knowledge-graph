"""Filings entering the gold set.

A filing is a human judgment joining the only dataset that measures
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


class TestJudgments:
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


class TestBothJudgments:
    """One reviewer, one sitting, two judgments. The expensive part is reading
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
        a person's judgment, and the review surface is where it matters
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
    judgment the statements make better.
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

    def test_an_edit_suggests_tags(self):
        """A statement edited from reputation to sanctions is about something
        else now, and nothing in the tags saying so would connect it to the
        wrong statements — quietly, since a wrong link looks like a right
        one."""
        page = self._page()
        assert "function retag(" in page
        assert "entry.suggested = picked.filter(id => !kept.includes(id));" in page

    def test_a_suggestion_never_replaces_an_extracted_tag(self):
        """Word overlap is much weaker evidence than a model that read the
        paper, and weaker evidence does not get to overrule stronger. The
        version that swapped them dropped a good tag on the ordinary case of
        rewording a sentence without changing its subject."""
        page = self._page()
        assert "entry.concepts = [...kept, ...entry.suggested].slice(0, 3);" in page
        assert "picked.length ? picked : (claim.concepts || [])" not in page

    def test_the_two_kinds_of_tag_are_told_apart(self):
        page = self._page()
        assert '"concept still added" : "concept still"' in page
        assert "suggested by your wording" in page

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

    def test_the_review_text_color_passes_contrast(self):
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
        types are primary is a judgment about what the library is for, and
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


class TestAdjustments:
    """The verdict that carries a rewrite.

    "Adjusted" is the only verdict that changes what the corpus says rather
    than recording an opinion about it, so the rewrite has to survive the
    trip: out of the browser, through the filing, into the gold file, and
    onto the pull request where somebody applies it.
    """

    KNOWN = {"claim:arxiv:2502.14143:1"}

    def _filing(self, body: str) -> dict:
        return extract("```yaml\nclaims:\n  claim:arxiv:2502.14143:1:\n" + body + "```\n")

    def test_an_adjustment_is_a_verdict(self):
        cleaned = validate_claims(
            self._filing("    verdict: adjusted\n"
                         "    text: Reputation carries across organizational boundaries.\n"),
            known_claims=self.KNOWN)
        assert cleaned["claim:arxiv:2502.14143:1"]["verdict"] == "adjusted"

    def test_the_rewrite_comes_with_it(self):
        """A verdict saying the statement was rewritten, with nothing saying
        how, is worse than no verdict: it marks the claim reviewed and leaves
        the wrong sentence in place."""
        with pytest.raises(FilingError, match="carries no text"):
            validate_claims(self._filing("    verdict: adjusted\n"),
                            known_claims=self.KNOWN)

    def test_a_fragment_is_not_a_statement(self):
        with pytest.raises(FilingError, match="too short"):
            validate_claims(
                self._filing("    verdict: adjusted\n    text: reputation\n"),
                known_claims=self.KNOWN)

    def test_tags_are_checked_against_the_vocabulary(self):
        """The browser checks them too. A filing is text somebody can hand-edit,
        and a tag that resolves to nothing is a statement nothing links to."""
        with pytest.raises(FilingError, match="do not resolve"):
            validate_claims(
                self._filing("    verdict: adjusted\n"
                             "    text: Reputation carries across organizational boundaries.\n"
                             '    concepts: ["not-a-real-tag"]\n'),
                known_claims=self.KNOWN)

    def test_the_rewrite_reaches_the_pull_request(self, tmp_path):
        """It sits in a gold file otherwise, and the statement it was meant to
        replace stays as extracted."""
        cleaned = validate_claims(
            self._filing("    verdict: adjusted\n"
                         "    text: Reputation carries across organizational boundaries.\n"),
            known_claims=self.KNOWN)
        result = merge_claims(cleaned, "anke", tmp_path / "claims.yml")
        text = "\n".join(summarize_claims(result))
        assert "Reputation carries across organizational boundaries." in text
        assert "data/claims/" in text, "points at the quote it has to answer to"
        assert "Merging this applies" in text, "says what merging it does"

    def test_the_rewrite_is_kept(self, tmp_path):
        gold = tmp_path / "claims.yml"
        cleaned = validate_claims(
            self._filing("    verdict: adjusted\n"
                         "    text: Reputation carries across organizational boundaries.\n"),
            known_claims=self.KNOWN)
        merge_claims(cleaned, "anke", gold)
        stored = yaml.safe_load(gold.read_text())["claims"]["claim:arxiv:2502.14143:1"]
        assert stored["text"] == "Reputation carries across organizational boundaries."
        assert stored["reviewer"] == "anke"


class TestConfirmingAnAdjustment:
    """Typing is not deciding.

    Every keystroke used to be the edit — an accidental character rewrote a
    statement, the tags moved with it, and there was no moment where the
    reviewer said "yes, this is my version". A draft now waits for a confirm.
    """

    def _page(self):
        from pathlib import Path
        return (Path(__file__).resolve().parent.parent
                / "site" / "template.html").read_text(encoding="utf-8")

    def test_typing_writes_a_draft_not_the_statement(self):
        page = self._page()
        assert "entry.draft = area.value;" in page
        assert "state.claims[claim.id].draft = area.value;" not in page

    def test_there_is_a_confirm_and_a_way_back(self):
        page = self._page()
        assert '"Confirm wording"' in page
        assert '"Back to original"' in page

    def test_confirming_makes_the_draft_the_statement(self):
        page = self._page()
        assert "delete entry.draft;" in page

    def test_an_unconfirmed_draft_is_not_judged(self):
        """The count at the top should not tell somebody they have finished a
        sentence they are halfway through rewriting."""
        page = self._page()
        assert "function settledVerdict(" in page
        assert 'if (entry.verdict !== "adjusted") return true;' in page
        assert "return entry.text !== undefined && entry.draft === undefined;" in page

    def test_one_definition_of_judged(self):
        """Five places asked this question and they have to agree, or the
        progress bar, the paper list and the submit button each count a
        different thing."""
        page = self._page()
        assert "state.claims[claim.id] || claim.verdict" not in page
        assert page.count("isJudged") >= 5

    def test_an_unconfirmed_draft_is_not_submitted(self):
        """It would file a verdict of "adjusted" with no adjustment, which the
        bot refuses — taking the rest of an otherwise good filing with it."""
        page = self._page()
        assert "const settled = claimed.filter(([, c]) => settledVerdict(c));" in page
        assert "const unconfirmed = claimed.length - settled.length;" in page
        assert "still being" in page, "and says so, rather than dropping it silently"

    def test_confirming_the_original_unchanged_is_not_an_adjustment(self):
        """That is "Add as is" reached the long way round, and filing it as an
        adjustment puts a reviewer's name on a rewording nobody did."""
        page = self._page()
        assert "const unchanged = committed === null" in page
        assert "Unchanged" in page


class TestTheGoldenSetIsReachable:
    """What a reviewer meets between doing the work and the work counting.

    None of this is the review itself, and all of it decides whether a
    reviewer finishes: whether their progress shows, whether the exercise can
    read as done, and whether what they wrote arrives whole.
    """

    def _page(self):
        from pathlib import Path
        return (Path(__file__).resolve().parent.parent
                / "site" / "template.html").read_text(encoding="utf-8")

    def test_the_filing_is_never_truncated_into_the_link(self):
        """A prefilled issue carries the filing in the URL and a URL has a
        ceiling. Slicing it to fit cut a reviewer who rewrote most of the set
        off mid-line — the bot then refused the remainder as malformed, and
        nothing said why. The whole golden set adjusted is about 8,900
        characters against a 5,200 slice."""
        page = self._page()
        assert "yaml.slice(0, 5200)" not in page
        assert "const fits = prefilled.length <= 6000;" in page

    def test_over_the_limit_it_goes_by_clipboard(self):
        page = self._page()
        assert '"Copy and open an issue"' in page
        assert "too long to carry in a link" in page

    def test_the_title_does_not_lead_with_a_count_of_nothing(self):
        """Golden-set reviewers file no topics, and "[Filing] 0 record(s)" as
        the first thing on their own submission reads like a failure."""
        page = self._page()
        assert "const parts = [];" in page
        assert "`[Filing] ${entries.length} record(s)`" not in page

    def test_done_means_every_statement_judged(self):
        """It also required a topic filing — reachable when the reviewer was
        asked for both, unreachable once filing left this screen. A finished
        paper dropped out of the queue and stayed at "6 of 6 open" in the
        heading beside it."""
        page = self._page()
        assert "const done = p => p.total > 0 && p.checked === p.total;" in page
        assert "p.tagged && p.checked === p.total" not in page

    def test_a_verdict_redraws_the_paper_list(self):
        """Three handlers redrew the card and not the list next to it, so a
        reviewer who had just finished a paper watched it sit at 0/7."""
        page = self._page()
        assert "function verdictChanged()" in page
        body = page.split("function verdictChanged()")[1][:200]
        assert "renderReview();" in body and "renderTree();" in body
        assert page.count("verdictChanged();") == 3

    def test_the_end_of_the_set_counts_what_was_done(self):
        """"You have filed 0 records" after judging thirty-two statements
        reads as though none of it counted."""
        page = self._page()
        assert "That is the whole set." in page
        assert "`You judged ${did.join(\" and \")}. Open Submit to send it in.`" in page


class TestTheIssueForm:
    """The form is the other half of the submission, and it was written when
    filing tags was the only thing that came through it."""

    def _form(self):
        from pathlib import Path
        import yaml as y
        return y.safe_load((Path(__file__).resolve().parent.parent
                            / ".github" / "ISSUE_TEMPLATE" / "filing.yml").read_text())

    def test_it_takes_statement_verdicts_too(self):
        form = self._form()
        blob = str(form)
        assert "claims:" in blob, "a golden-set filing starts with this line"
        assert "Golden-set review" in blob

    def test_the_field_the_site_prefills_still_exists(self):
        """The Submit link fills `&filing=`, which only works while a textarea
        with that id is in the form."""
        form = self._form()
        ids = [item.get("id") for item in form["body"]]
        assert "filing" in ids
        field = next(i for i in form["body"] if i.get("id") == "filing")
        assert field["attributes"]["render"] == "yaml", "the bot reads a yaml fence"

    def test_the_placeholder_shows_the_shape_reviewers_will_have(self):
        form = self._form()
        field = next(i for i in form["body"] if i.get("id") == "filing")
        assert field["attributes"]["placeholder"].startswith("claims:")


class TestTheFilingSaysWhatWasJudged:
    """The other half of the binding. The site ships each statement's
    fingerprint and the filing echoes it back, so a statement rewritten
    between the reviewer opening the page and sending the filing is caught
    where the reviewer can still do something about it."""

    def _known(self):
        from ao_commons_kg.claims import load_claims
        claims = load_claims()
        return {c.id for c in claims}, {c.id: c.fingerprint for c in claims}

    def _filing(self, claim_id, saw):
        body = (f"```yaml\nclaims:\n  {claim_id}:\n    verdict: accurate\n"
                f"    saw: {saw}\n    reviewed_on: 2026-09-18\n```\n")
        return extract(body)

    def test_a_matching_fingerprint_is_accepted_and_kept(self):
        known, prints = self._known()
        claim_id = next(iter(sorted(known)))
        cleaned = validate_claims(self._filing(claim_id, prints[claim_id]),
                                  known_claims=known, fingerprints=prints)
        assert cleaned[claim_id]["saw"] == prints[claim_id]

    def test_a_statement_that_changed_is_refused_by_name(self):
        """And the message tells the reviewer what to do, because this is not
        their mistake — the corpus moved under them."""
        known, prints = self._known()
        claim_id = next(iter(sorted(known)))
        with pytest.raises(FilingError, match="changed after you reviewed it"):
            validate_claims(self._filing(claim_id, "deadbeef1234"),
                            known_claims=known, fingerprints=prints)

    def test_a_filing_with_no_fingerprint_is_refused(self):
        known, prints = self._known()
        claim_id = next(iter(sorted(known)))
        payload = extract(f"```yaml\nclaims:\n  {claim_id}:\n    verdict: accurate\n```\n")
        with pytest.raises(FilingError, match="no `saw:` line"):
            validate_claims(payload, known_claims=known, fingerprints=prints)

    def test_the_check_is_skipped_when_there_is_nothing_to_check_against(self):
        """`fingerprints=None` is the older call, kept so a caller without the
        corpus in hand is not forced to fake one."""
        known, _ = self._known()
        claim_id = next(iter(sorted(known)))
        payload = extract(f"```yaml\nclaims:\n  {claim_id}:\n    verdict: accurate\n```\n")
        assert validate_claims(payload, known_claims=known)[claim_id]["verdict"] == "accurate"


class TestTheBrowserHoldsBackWhatMoved:
    def _page(self):
        from pathlib import Path
        return (Path(__file__).resolve().parent.parent
                / "site" / "template.html").read_text(encoding="utf-8")

    def test_the_payload_ships_the_fingerprint(self):
        from pathlib import Path
        import json, re
        built = (Path(__file__).resolve().parent.parent
                 / "site" / "index.html").read_text(encoding="utf-8")
        assert '"saw":' in built

    def test_a_verdict_records_what_was_on_screen(self):
        page = self._page()
        assert "saw: claim.saw" in page

    def test_the_submission_carries_it(self):
        page = self._page()
        assert "if (c.saw) lines.push(`    saw: ${c.saw}`);" in page

    def test_a_statement_rewritten_since_judging_is_not_sent(self):
        page = self._page()
        assert "const moved = settled.filter(([id, c]) => c.saw && c.saw !== current[id]);" in page
        assert "rewritten since you judged" in page


class TestAMergedVerdictIsTheFinalWord:
    """The first reviewer finished two papers, and one of them then showed as
    5/6 when she reopened the page — because an Adjust she had started and
    never confirmed was still sitting in her browser, and the local entry was
    consulted instead of the verdict that had already merged. The work was in
    the corpus and the screen said it was not."""

    def _page(self):
        from pathlib import Path
        return (Path(__file__).resolve().parent.parent
                / "site" / "template.html").read_text(encoding="utf-8")

    def test_the_corpus_outranks_whatever_is_left_in_the_browser(self):
        page = self._page()
        block = page.split("function settledVerdict(")[1].split("}")[0]
        assert "if (claim && claim.verdict) return true;" in block

    def test_it_is_checked_before_the_local_entry(self):
        """Order is the whole fix — the old version returned on the local
        entry first and never reached the merged verdict."""
        page = self._page()
        block = page.split("function settledVerdict(")[1].split("\n  }")[0]
        assert block.index("claim.verdict") < block.index("if (!entry)")

    def test_the_submit_path_still_works_with_one_argument(self):
        """`settledVerdict(c)` is called with only the entry when deciding
        what to send, so a reviewer revising something already filed can still
        file the revision."""
        page = self._page()
        assert "settledVerdict(c)" in page


class TestAPaperSaysHowMuchOfItWasRead:
    """Building the Loop carried three statements for a month, which reads as
    a paper with little to say. It is a thirteen-page argument whose publisher
    answers 403 to an automated fetch, and the abstract is 879 characters.
    A reviewer judging statements drawn from an abstract is judging the
    paper's summary of itself and should be told so."""

    def _page(self):
        from pathlib import Path
        return (Path(__file__).resolve().parent.parent
                / "site" / "template.html").read_text(encoding="utf-8")

    def test_the_record_carries_it(self):
        from ao_commons_kg.resources import load_resources
        read = [r for r in load_resources() if r.text_coverage != "unknown"]
        assert read, "nothing records what anyone was able to read"
        assert all(r.text_coverage in ("full-text", "abstract-only", "none") for r in read)

    def test_every_paper_with_statements_says_what_was_read(self):
        """The flag matters exactly where statements exist — it is what tells
        a reviewer how much those statements could possibly cover."""
        from ao_commons_kg.claims import load_claims
        from ao_commons_kg.resources import load_resources
        with_claims = {c.resource_id for c in load_claims()}
        unknown = [r.id for r in load_resources()
                   if r.id in with_claims and r.text_coverage == "unknown"]
        assert not unknown, unknown

    def test_the_payload_ships_it(self):
        from pathlib import Path
        built = (Path(__file__).resolve().parent.parent
                 / "site" / "index.html").read_text(encoding="utf-8")
        assert '"coverage":' in built

    def test_the_reviewer_is_told_before_they_judge(self):
        page = self._page()
        assert "Read from the abstract only" in page
        assert "if (coverageNote) stage.append(coverageNote);" in page

    def test_a_fully_read_paper_says_nothing(self):
        """A notice on every paper is a notice nobody reads."""
        page = self._page()
        assert 'record.coverage !== "full-text"' in page
