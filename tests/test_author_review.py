"""A verdict filed by somebody on the paper's own byline.

The first twelve verdicts in this library were filed by an author on her own
two papers, and nothing in the data said so. That is the strongest provenance
the corpus has and it was invisible.

It is recorded as a fact about the reviewer and not as a higher score. An
author is the highest authority on whether a statement says what their paper
says, and the least disinterested party on whether it overstates — which the
project's own docs call the verdict worth having.
"""

import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from ao_commons_kg.people import Identity, load_identities, wrote  # noqa: E402

BYLINE = ["Botao 'Amber' Hu", "Helena Rong", "Max Van Kleek"]


class TestTheLink:
    def test_a_name_that_matches_is_not_a_verification(self):
        """A coincidence of spelling is exactly what an impersonation looks
        like. The link has to be confirmed by a named person."""
        claimed = {"x": Identity(name="Helena Rong", github="x", link_status="claimed")}
        assert not wrote("x", BYLINE, claimed)

    def test_a_confirmed_link_counts(self):
        ok = {"x": Identity(name="Helena Rong", github="x", link_status="verified",
                            verified_by="ankeliu", verified_how="checked")}
        assert wrote("x", BYLINE, ok)

    def test_verified_without_a_name_behind_it_does_not_count(self):
        """`verified_by` is who to ask if the link turns out to be wrong."""
        hollow = {"x": Identity(name="Helena Rong", github="x", link_status="verified")}
        assert not wrote("x", BYLINE, hollow)

    def test_an_author_of_another_paper_is_not_an_author_of_this_one(self):
        ok = {"x": Identity(name="Joel Z. Leibo", github="x", link_status="verified",
                            verified_by="ankeliu", verified_how="checked")}
        assert not wrote("x", BYLINE, ok)

    def test_an_unknown_account_is_simply_not_an_author(self):
        assert not wrote("nobody", BYLINE, {})

    def test_the_committed_links_load(self):
        for login, identity in load_identities().items():
            assert identity.name and login == login.lower()
            assert identity.link_status in ("claimed", "verified")


class TestItIsDerivedNotClaimed:
    def test_the_bot_asks_the_link_table(self):
        """A filing that says it comes from an author is worth nothing on its
        own, so the filing is never asked."""
        from merge_filing import mark_author_verdicts
        source = (ROOT / "scripts" / "merge_filing.py").read_text(encoding="utf-8")
        block = source.split("def mark_author_verdicts")[1].split("\ndef ")[0]
        assert "wrote(" in block
        assert "load_identities" in block
        assert "entry.get(\"as_author\")" not in block, "never take the filing's word"

    def test_an_unlinked_reviewer_marks_nothing(self):
        from merge_filing import mark_author_verdicts
        cleaned = {"claim:arxiv:2511.03434:1": {"verdict": "accurate"}}
        assert mark_author_verdicts(cleaned, "somebody-with-no-link") == []
        assert "by_author" not in cleaned["claim:arxiv:2511.03434:1"]


class TestWhatItChanges:
    CID = "claim:arxiv:2511.03434:1"

    def _corpus(self, tmp_path, verdict, by_author, **extra):
        from ao_commons_kg.claims import load_claims
        claim = {c.id: c for c in load_claims()}[self.CID]
        gold = tmp_path / "claims.yml"
        entry = {"verdict": verdict, "reviewer": "helenarong2703",
                 "reviewed_on": "2026-09-18", "saw": claim.fingerprint,
                 "by_author": by_author, **extra}
        gold.write_text(yaml.safe_dump({"claims": {self.CID: entry}}), encoding="utf-8")
        return {c.id: c for c in load_claims(verdicts=gold)}[self.CID]

    def test_it_is_published_on_the_statement(self):
        judged = None
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            judged = self._corpus(Path(d), "accurate", True)
        assert judged.reviewed_by_author is True
        assert judged.review_status.value == "reviewed"

    def test_an_author_accepting_a_statement_still_settles_it(self, tmp_path):
        """Nothing here treats an author's verdict as suspect by default."""
        assert self._corpus(tmp_path, "accurate", True).review_status.value == "reviewed"

    def test_an_author_rewriting_one_waits_for_a_second_reader(self, tmp_path):
        """The author's wording is the best available and the one nobody
        disinterested has checked against the quote."""
        judged = self._corpus(tmp_path, "adjusted", True,
                              text="A rewording long enough to be a claim.")
        assert judged.review_status.value == "needs-review"

    def test_a_rewrite_from_anybody_else_settles_normally(self, tmp_path):
        judged = self._corpus(tmp_path, "adjusted", False,
                              text="A rewording long enough to be a claim.")
        assert judged.review_status.value == "reviewed"


class TestTheScreenSaysIt:
    def test_the_payload_carries_it(self):
        built = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
        assert '"byAuthor":' in built

    def test_and_says_what_it_means(self):
        page = (ROOT / "site" / "template.html").read_text(encoding="utf-8")
        assert "Filed by an author of this paper" in page
        assert "least disinterested" in page


class TestConfirmingALinkReachesVerdictsAlreadyMerged:
    """The first author review in the corpus arrived before anything recorded
    who filed it. If confirming a link only affected future filings it would
    stay invisible for ever."""

    def test_the_corpus_knows_axel_wrote_vending_bench(self):
        from ao_commons_kg.claims import load_claims
        marked = [c for c in load_claims() if c.reviewed_by_author]
        assert marked, "no verdict is marked as an author's"
        assert all(c.resource_id == "resource:arxiv:2502.15840" for c in marked)

    def test_the_backfill_is_idempotent(self):
        """It is run after every confirmation, so running it twice must be a
        no-op rather than a second round of edits."""
        import subprocess, sys
        from pathlib import Path
        root = Path(__file__).resolve().parent.parent
        out = subprocess.run([sys.executable, "scripts/mark_authors.py"],
                             cwd=root, capture_output=True, text=True)
        assert "nothing to change" in out.stdout, out.stdout


class TestNoJudgementDisappears:
    """Eight verdicts were deleted by a rebase that replaced the gold file
    wholesale from a branch predating another reviewer's merge. Tests passed,
    fingerprints matched, the site built — a gold set missing eight entries is
    a perfectly valid gold set."""

    def test_the_guard_exists_and_runs(self):
        import subprocess, sys
        from pathlib import Path
        root = Path(__file__).resolve().parent.parent
        assert (root / "scripts" / "check_gold_intact.py").exists()
        out = subprocess.run([sys.executable, "scripts/check_gold_intact.py",
                              "--base", "HEAD"], cwd=root, capture_output=True, text=True)
        assert out.returncode == 0, out.stderr

    def test_ci_runs_it_against_main(self):
        from pathlib import Path
        workflow = (Path(__file__).resolve().parent.parent
                    / ".github" / "workflows" / "test.yml").read_text(encoding="utf-8")
        assert "check_gold_intact.py" in workflow
        assert "origin/main" in workflow

    def test_every_verdict_still_names_a_reviewer(self):
        from ao_commons_kg.claims import load_verdicts
        gold = load_verdicts()
        assert len(gold) >= 23
        assert all(e.get("reviewer") for e in gold.values())
