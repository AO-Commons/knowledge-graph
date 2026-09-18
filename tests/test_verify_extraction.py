"""An independent pass over the extraction.

The five gates in `extract.py` are mechanical and run inside the extraction.
The thing none of them measures is the one the extractor is least able to
judge about itself — whether the paraphrase says what the quote says. This is
the second pass, and the rule it enforces is about *who*: the verifier never
sees the extractor's reasoning.
"""

import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from verify_extraction import packet, record  # noqa: E402

PAPER = "resource:doi:10-1111-epic-70009"


class TestThePacket:
    def test_it_carries_the_question_and_nothing_else(self):
        """The statement, the sentence it came from, and the section. A
        verifier given the extractor's gloss is grading the reasoning rather
        than the reading."""
        text = packet(PAPER, seed=0)
        assert "statement:" in text and "quote:" in text and "section:" in text
        assert "standalone" not in text, "the gloss written to justify the reading"
        assert "concept_tags" not in text and "attribution" not in text
        assert "extraction_method" not in text

    def test_it_says_what_the_answers_may_be(self):
        text = packet(PAPER, seed=0)
        for verdict in ("supported", "overstated", "not-in-source", "unclear"):
            assert verdict in text

    def test_the_order_is_not_the_order_they_were_written_in(self):
        """Read in production order, the statements tell a story the extractor
        composed. The paper is what is being checked, not the narrative."""
        from ao_commons_kg.claims import load_claims
        produced = [c.id for c in load_claims() if c.resource_id == PAPER]
        shown = [line.removeprefix("## ") for line in packet(PAPER, seed=0).splitlines()
                 if line.startswith("## ")]
        assert sorted(shown) == sorted(produced)
        assert shown != produced

    def test_it_refuses_a_paper_it_holds_nothing_for(self):
        with pytest.raises(SystemExit):
            packet("resource:arxiv:0000.00000", seed=0)

    def test_every_statement_carries_the_fingerprint_it_was_judged_at(self):
        assert "saw:" in packet(PAPER, seed=0)


class TestRecording:
    def _claim(self):
        from ao_commons_kg.claims import load_claims
        return [c for c in load_claims() if c.resource_id == PAPER][0]

    def test_a_verdict_needs_a_reason(self, tmp_path, monkeypatch):
        import verify_extraction
        monkeypatch.setattr(verify_extraction, "MACHINE", tmp_path / "extraction.yml")
        with pytest.raises(SystemExit, match="no reason given"):
            record({self._claim().id: {"verdict": "overstated"}}, "a-verifier")

    def test_an_unknown_verdict_is_refused(self, tmp_path, monkeypatch):
        import verify_extraction
        monkeypatch.setattr(verify_extraction, "MACHINE", tmp_path / "extraction.yml")
        with pytest.raises(SystemExit, match="unknown verdict"):
            record({self._claim().id: {"verdict": "looks fine", "because": "it does"}},
                   "a-verifier")

    def test_it_binds_to_what_was_judged(self, tmp_path, monkeypatch):
        import verify_extraction
        path = tmp_path / "extraction.yml"
        monkeypatch.setattr(verify_extraction, "MACHINE", path)
        claim = self._claim()
        record({claim.id: {"verdict": "supported", "because": "the quote says it"}},
               "a-verifier")
        stored = yaml.safe_load(path.read_text())["statements"][claim.id]
        assert stored["saw"] == claim.fingerprint
        assert stored["by"] == "a-verifier"


class TestWhatItChanges:
    """It triages. It never reviews."""

    def _corpus(self, tmp_path, verdict, because="the quote does not carry it"):
        from ao_commons_kg.claims import load_claims
        claim = [c for c in load_claims() if c.resource_id == PAPER][0]
        path = tmp_path / "extraction.yml"
        path.write_text(yaml.safe_dump({"statements": {claim.id: {
            "verdict": verdict, "because": because, "saw": claim.fingerprint,
            "by": "a-verifier", "on": "2026-09-18"}}}), encoding="utf-8")
        return claim.id, {c.id: c for c in load_claims(machine=path)}

    def test_a_disagreement_moves_the_statement_up_the_queue(self, tmp_path):
        claim_id, corpus = self._corpus(tmp_path, "overstated")
        flagged = corpus[claim_id]
        assert flagged.review_status.value == "needs-review"
        assert "overstated" in flagged.machine_check

    def test_agreement_changes_nothing(self, tmp_path):
        claim_id, corpus = self._corpus(tmp_path, "supported", "it says exactly this")
        assert corpus[claim_id].review_status.value == "machine-checked"
        assert corpus[claim_id].machine_check is None

    def test_it_never_reaches_reviewed(self, tmp_path):
        """A machine cannot review a statement. Only a named human's verdict
        gets there, and that is the whole point of keeping two files."""
        claim_id, corpus = self._corpus(tmp_path, "supported", "it says exactly this")
        assert corpus[claim_id].verdict is None
        assert corpus[claim_id].review_status.value != "reviewed"

    def test_a_human_verdict_outranks_it(self, tmp_path):
        """Once somebody has actually read the thing, a machine's opinion of
        it is no longer the interesting fact."""
        from ao_commons_kg.claims import load_claims
        claim = [c for c in load_claims() if c.resource_id == PAPER][0]
        machine = tmp_path / "extraction.yml"
        machine.write_text(yaml.safe_dump({"statements": {claim.id: {
            "verdict": "overstated", "because": "too strong", "saw": claim.fingerprint,
            "by": "a-verifier", "on": "2026-09-18"}}}), encoding="utf-8")
        gold = tmp_path / "claims.yml"
        gold.write_text(yaml.safe_dump({"claims": {claim.id: {
            "verdict": "accurate", "reviewer": "anke", "reviewed_on": "2026-09-18",
            "saw": claim.fingerprint}}}), encoding="utf-8")
        judged = {c.id: c for c in load_claims(verdicts=gold, machine=machine)}[claim.id]
        assert judged.review_status.value == "reviewed"
        assert judged.machine_check is None

    def test_a_pass_over_wording_that_changed_is_ignored(self, tmp_path):
        from ao_commons_kg.claims import load_claims
        claim = [c for c in load_claims() if c.resource_id == PAPER][0]
        path = tmp_path / "extraction.yml"
        path.write_text(yaml.safe_dump({"statements": {claim.id: {
            "verdict": "not-in-source", "because": "stale", "saw": "deadbeef1234",
            "by": "a-verifier", "on": "2026-09-18"}}}), encoding="utf-8")
        stale = {c.id: c for c in load_claims(machine=path)}[claim.id]
        assert stale.machine_check is None
        assert stale.review_status.value == "machine-checked"
