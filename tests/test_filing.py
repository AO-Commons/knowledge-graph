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
