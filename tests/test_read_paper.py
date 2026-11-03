"""Reading a paper because an issue asked for it.

The gates themselves are `test_extract.py`'s subject and are not re-tested
here. What is tested here is everything around them: which requests are
refused, and that a reading which fails leaves nothing behind. A reader that
writes an empty claims file on failure is worse than one that crashes — the
file says somebody looked.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

import read_paper  # noqa: E402
from ao_commons_kg import reader  # noqa: E402
from ao_commons_kg.fulltext import Section  # noqa: E402
from ao_commons_kg.models import Resource  # noqa: E402

PAPER = "resource:arxiv:2604.10290"
BODY = f"### Which record\n\n`{PAPER}`\n"

SECTIONS = [
    Section("abstract", "Abstract", "We study organizations of agents. " * 20),
    Section("results", "4 Results",
            "Organizations of aligned agents scored higher on business goals and "
            "lower on ethics than a single aligned agent. " * 20),
    Section("discussion", "5 Discussion",
            "Our setting is simulated and the result may not carry to deployment. " * 20),
]


def a_paper(**kw):
    return Resource(
        id=kw.pop("id", PAPER),
        resource_type=kw.pop("resource_type", "preprint"),
        title=kw.pop("title", "AI Organizations are More Effective"),
        authors=kw.pop("authors", ["Judy Hanwen Shen"]),
        arxiv_id=kw.pop("arxiv_id", "2604.10290"),
        **kw,
    )


def a_reply(*claims) -> str:
    return json.dumps({"claims": list(claims)})


GOOD = {
    "text": "Organizations of aligned agents scored higher on business goals and lower on ethics.",
    "quote": "Organizations of aligned agents scored higher on business goals and "
             "lower on ethics than a single aligned agent.",
    "standalone": "Across twelve tasks in two settings, organizations beat single agents "
                  "on the business measure and lost on the ethics measure.",
    "claim_type": "evidence",
    "attribution": "own",
    "concept_tags": ["multi-agent-dynamics"],
}


class TestWhatIsRefused:
    def test_an_issue_with_no_record_id(self):
        with pytest.raises(read_paper.Refused, match="No record id"):
            read_paper.read("I would like the Shen paper read please")

    def test_a_record_the_corpus_does_not_hold(self):
        with pytest.raises(read_paper.Refused, match="not a record"):
            read_paper.read("`resource:arxiv:9999.99999`", resources=[], curated=set())

    def test_a_record_that_is_not_curated(self, tmp_path):
        """The gate the whole thing turns on: reading is a model call over a
        whole paper, startable by anyone with an issue form, so the queue is
        the set somebody already chose."""
        with pytest.raises(read_paper.Refused, match="not in the curated set"):
            read_paper.read(BODY, resources=[a_paper()], curated=set(),
                            claims_dir=tmp_path)

    def test_a_paper_already_read(self, tmp_path):
        """A second drafting would replace claims carrying human verdicts."""
        (tmp_path / "arxiv-2604.10290.yml").write_text(
            yaml.safe_dump({"resource_id": PAPER, "claims": [{"id": "claim:x:1"}]}),
            encoding="utf-8")
        with pytest.raises(read_paper.Refused, match="already been read"):
            read_paper.read(BODY, resources=[a_paper()], curated={PAPER},
                            claims_dir=tmp_path)

    def test_a_paper_with_no_arxiv_id(self, tmp_path):
        with pytest.raises(read_paper.Refused, match="no arXiv id"):
            read_paper.read(BODY, resources=[a_paper(arxiv_id=None)],
                            curated={PAPER}, claims_dir=tmp_path)


class TestWhatIsWritten:
    def test_a_reading_writes_the_claims_it_kept(self, tmp_path, monkeypatch):
        monkeypatch.setattr(read_paper, "sections_for", lambda r: SECTIONS)
        result = read_paper.read(
            BODY, resources=[a_paper()], curated={PAPER}, claims_dir=tmp_path,
            make_reader=lambda: (lambda system, paper: a_reply(GOOD)))

        assert result["kept"] == 1
        written = yaml.safe_load((tmp_path / "arxiv-2604.10290.yml").read_text())
        assert written["resource_id"] == PAPER
        assert written["claims"][0]["id"] == "claim:arxiv:2604.10290:1"
        assert written["claims"][0]["quote"] == GOOD["quote"]

    def test_a_claim_whose_quote_is_not_in_the_paper_is_dropped(self, tmp_path, monkeypatch):
        """The one error that survives every later check, because a
        reconstructed quote reads exactly like a real one."""
        monkeypatch.setattr(read_paper, "sections_for", lambda r: SECTIONS)
        invented = dict(GOOD, quote="Agents are reliable and always will be.")
        with pytest.raises(read_paper.Refused, match="refused by a gate"):
            read_paper.read(BODY, resources=[a_paper()], curated={PAPER},
                            claims_dir=tmp_path,
                            make_reader=lambda: (lambda s, p: a_reply(invented)))
        assert not list(tmp_path.iterdir()), "a failed reading left a file behind"

    def test_a_failed_reading_writes_nothing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(read_paper, "sections_for", lambda r: SECTIONS)

        def broken(system, paper):
            return "I'm afraid I can't do that"

        with pytest.raises(reader.ReadingError):
            read_paper.read(BODY, resources=[a_paper()], curated={PAPER},
                            claims_dir=tmp_path, make_reader=lambda: broken)
        assert not list(tmp_path.iterdir())


class TestTheReader:
    def test_no_key_is_a_refusal_not_an_empty_reading(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(reader.ReadingError, match="ANTHROPIC_API_KEY"):
            reader.anthropic_reader()

    def test_an_empty_claims_list_is_a_failed_reading(self):
        with pytest.raises(reader.ReadingError, match="failed, not a paper"):
            reader.parse('{"claims": []}')

    def test_json_in_a_fence_is_still_json(self):
        assert reader.parse('```json\n{"claims": [{"text": "x"}]}\n```') == [{"text": "x"}]

    def test_the_prompt_carries_the_body_not_the_abstract(self):
        _, paper = reader.prompt("A title", ["An author"], SECTIONS)
        assert "4 Results" in paper
        assert "Abstract" not in paper

    def test_the_prompt_lists_the_vocabulary_it_wants_reused(self):
        from ao_commons_kg.concepts import load_vocabulary

        vocabulary = load_vocabulary()
        system, _ = reader.prompt("A title", [], SECTIONS, vocabulary)
        assert len(vocabulary) > 50
        for term in list(vocabulary.concepts)[:5]:
            assert term in system


class TestTheExitCodes:
    """The workflow branches on these rather than parsing stdout."""

    def _run(self, tmp_path, body, monkeypatch, **kw):
        issue = tmp_path / "issue.md"
        issue.write_text(body, encoding="utf-8")
        out = tmp_path / "out.json"
        monkeypatch.setattr(read_paper, "read",
                            kw.pop("read", read_paper.read))
        code = read_paper.main(["--body-file", str(issue), "--out", str(out)])
        return code, json.loads(out.read_text())

    def test_a_refusal_is_two(self, tmp_path, monkeypatch):
        def refuse(body, **kw):
            raise read_paper.Refused("not on the list")

        code, payload = self._run(tmp_path, BODY, monkeypatch, read=refuse)
        assert code == 2 and "not on the list" in payload["summary"]

    def test_a_reader_problem_is_three(self, tmp_path, monkeypatch):
        def broken(body, **kw):
            raise reader.ReadingError("no key")

        code, payload = self._run(tmp_path, BODY, monkeypatch, read=broken)
        assert code == 3
        assert "problem with the reader" in payload["summary"]

    def test_a_reading_is_zero(self, tmp_path, monkeypatch):
        def fine(body, **kw):
            return {"summary": "read it", "kept": 3, "path": "data/claims/x.yml"}

        code, payload = self._run(tmp_path, BODY, monkeypatch, read=fine)
        assert code == 0 and payload["kept"] == 3
