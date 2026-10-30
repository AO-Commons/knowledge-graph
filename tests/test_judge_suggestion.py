"""The gate between a public issue and the corpus.

Filing from an issue used to be unconditional, which was defensible while the
door was effectively internal and is not on a public repository.
"""
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "src"))

import judge_suggestion  # noqa: E402
from ao_commons_kg.expansion import ScopeVerdict  # noqa: E402

BODY = """### What is it?

Paper or preprint

### Link, DOI or arXiv id

2502.14143

### Title or name

Multi-Agent Risks from Advanced AI

### Why does it belong?

It catalogues failure modes that only exist once several agents interact.
"""


class TestReadingTheForm:
    def test_the_case_for_inclusion_is_what_the_judge_is_given(self):
        """The proposer has just answered the question the judge is asked."""
        meta = judge_suggestion.metadata_from_body(BODY)
        assert "only exist once several agents interact" in meta["abstract"]
        assert meta["title"] == "Multi-Agent Risks from Advanced AI"

    def test_an_unanswered_field_does_not_become_the_string_github_writes(self):
        body = BODY.replace("It catalogues failure modes that only exist once several "
                            "agents interact.", "_No response_")
        meta = judge_suggestion.metadata_from_body(body)
        assert "_No response_" not in meta["abstract"]
        assert meta["abstract"] == "(the proposer gave no reason)"

    def test_without_a_title_the_identifier_stands_in(self):
        body = BODY.replace("### Title or name\n\nMulti-Agent Risks from Advanced AI\n", "")
        assert judge_suggestion.metadata_from_body(body)["title"] == "2502.14143"


class TestWhatTheExitCodeSays:
    """The workflow branches on these rather than parsing stdout."""

    def _run(self, tmp_path, verdict_or_error):
        body = tmp_path / "proposal.md"
        body.write_text(BODY, encoding="utf-8")
        out = tmp_path / "verdict.json"

        def judge(candidate, metadata):
            if isinstance(verdict_or_error, Exception):
                raise verdict_or_error
            return verdict_or_error

        real = judge_suggestion.anthropic_judge
        judge_suggestion.anthropic_judge = lambda *a, **k: judge
        try:
            code = judge_suggestion.main(["--body-file", str(body), "--out", str(out)])
        finally:
            judge_suggestion.anthropic_judge = real
        return code, json.loads(out.read_text(encoding="utf-8"))

    def test_in_scope_is_filed(self, tmp_path):
        code, payload = self._run(tmp_path, ScopeVerdict(
            admit=True, reasoning="agents hold authority over the budget",
            judged_by="claude-opus-5"))
        assert code == 0 and payload["admit"] is True

    def test_borrowed_background_is_filed_and_flagged(self, tmp_path):
        code, payload = self._run(tmp_path, ScopeVerdict(
            admit=True, reasoning="load-bearing, not about agent authority",
            judged_by="claude-opus-5", borrowed_background=True))
        assert code == 0 and payload["borrowed_background"] is True

    def test_out_of_scope_is_refused_with_its_reasoning(self, tmp_path):
        code, payload = self._run(tmp_path, ScopeVerdict(
            admit=False, reasoning="human deliberation, unchanged by machines",
            judged_by="claude-opus-5"))
        assert code == 2
        assert payload["admit"] is False
        assert "unchanged by machines" in payload["reasoning"]

    def test_a_judge_that_cannot_answer_refuses(self, tmp_path):
        """The failure a gate is most likely to have is letting everything
        through when it breaks."""
        code, payload = self._run(tmp_path, RuntimeError("ANTHROPIC_API_KEY is not set"))
        assert code == 3
        assert payload["admit"] is False
        assert payload["judged"] is False
        assert "ANTHROPIC_API_KEY" in payload["reasoning"]

    def test_no_exit_code_means_file_it_except_zero(self, tmp_path):
        """2 and 3 are different reasons and must not collapse into one."""
        refused, _ = self._run(tmp_path, ScopeVerdict(
            admit=False, reasoning="out", judged_by="m"))
        broke, _ = self._run(tmp_path, RuntimeError("no key"))
        assert refused != broke


class TestItAnswersToTheSameCriteriaAsExpansion:
    def test_it_uses_the_shared_prompt_rather_than_its_own(self):
        """Two scope tests drift. The second copy is the one nobody updates."""
        source = (REPO / "scripts" / "judge_suggestion.py").read_text(encoding="utf-8")
        assert "from ao_commons_kg.scope_judge import anthropic_judge" in source
        assert "SCOPE_TEST" not in source, "it must not restate the test"
