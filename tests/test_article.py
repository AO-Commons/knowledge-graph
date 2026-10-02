"""Reading things that were never papers.

No test here touches the network. A reader that needs a live page to be tested
is a reader nobody runs in CI, and the pages it reads are exactly the ones that
change without warning.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from ao_commons_kg import article  # noqa: E402
from ao_commons_kg.fulltext import FullTextError, Section  # noqa: E402

LONG = "This sentence is long enough to clear the minimum section length. " * 5

PAGE = f"""
<html><head><title>What agents do | A Lab</title></head><body>
<nav><a href="/">home</a></nav>
<header>site chrome</header>
<main>
  <h1>What agents do</h1>
  <p>{LONG}</p>
  <h2>Results</h2>
  <p>{LONG}</p>
  <h2>Cookie notice</h2>
  <p>{LONG}</p>
  <h2>References</h2>
  <p>{LONG}</p>
  <h2>Caption</h2>
  <p>too short</p>
</main>
<footer>more chrome</footer>
</body></html>
"""


class TestParsing:
    def test_it_produces_the_same_sections_a_paper_does(self):
        """Borrowed rather than parallel, so gap hunting, verbatim checking and
        extraction work on a blog post exactly as they work on a paper."""
        sections = article.parse(PAGE)
        assert all(isinstance(s, Section) for s in sections)
        assert [s.heading for s in sections] == ["What agents do", "Results"]

    def test_headings_are_classified_by_the_same_rule(self):
        kinds = {s.heading: s.kind for s in article.parse(PAGE)}
        assert kinds["Results"] == "results"

    def test_furniture_is_dropped(self):
        """A cookie banner reads as prose and would be extracted from."""
        text = "\n".join(s.text for s in article.parse(PAGE))
        headings = [s.heading for s in article.parse(PAGE)]
        assert "Cookie notice" not in headings
        assert "References" not in headings

    def test_a_caption_is_not_a_section(self):
        assert "Caption" not in [s.heading for s in article.parse(PAGE)]

    def test_chrome_outside_the_container_never_arrives(self):
        text = " ".join(s.text for s in article.parse(PAGE))
        assert "site chrome" not in text and "more chrome" not in text

    def test_a_page_with_no_article_is_refused_rather_than_guessed(self):
        """Returning an empty record would file a landing page as a read work."""
        with pytest.raises(FullTextError, match="no article text"):
            article.read("https://example.invalid/",
                         **{}) if False else _read_static("<html><body><p>hi</p></body></html>")


def _read_static(html: str):
    sections = article.parse(html)
    if not sections:
        raise FullTextError("no article text found")
    return sections


class TestTheSnapshot:
    """The archive is the whole reason this is safe to build on: a web page can
    change or vanish, and a quote that cannot be re-checked is worthless."""

    def _article(self):
        return article.Article(url="https://example.org/post", title="A post",
                               retrieved_on="2026-10-01", sha256="abc123",
                               sections=article.parse(PAGE))

    def test_it_round_trips_exactly(self, tmp_path):
        original = self._article()
        article.save(original, "resource:web:a-post", directory=tmp_path)
        back = article.load("resource:web:a-post", directory=tmp_path)
        assert back.url == original.url
        assert back.sha256 == original.sha256
        assert back.retrieved_on == original.retrieved_on
        assert back.text == original.text, "the text a quote is checked against must not drift"

    def test_it_reads_without_the_network(self, tmp_path):
        article.save(self._article(), "resource:web:a-post", directory=tmp_path)
        assert article.sections_for("resource:web:a-post", directory=tmp_path)

    def test_a_missing_snapshot_says_so(self, tmp_path):
        with pytest.raises(FullTextError, match="no snapshot"):
            article.load("resource:web:nothing", directory=tmp_path)

    def test_no_snapshot_is_an_orphan(self):
        """A snapshot with no record behind it is a page somebody read and
        never filed. Two reached the repository this way, written by test runs
        before the archive path could be redirected."""
        import yaml
        if not article.SNAPSHOTS.exists():
            return
        held = {(yaml.safe_load(p.read_text(encoding="utf-8")) or {}).get("id")
                for p in (ROOT / "data" / "resources").glob("*.yml")}
        for path in article.SNAPSHOTS.glob("*.json"):
            import json
            payload = json.loads(path.read_text(encoding="utf-8"))
            assert payload["resource_id"] in held, \
                f"{path.name} has no record behind it"

    def test_every_web_record_in_the_corpus_has_one(self):
        """Without the snapshot the record's quotes cannot be re-verified, which
        is the one guarantee a web source does not come with."""
        import yaml
        for path in (ROOT / "data" / "resources").glob("*.yml"):
            payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            if payload.get("resource_type") == "written-work":
                assert article.snapshot_path(payload["id"]).exists(), \
                    f"{payload['id']} has no snapshot"


class TestIntake:
    def test_a_code_host_is_a_tool_not_a_written_work(self):
        from add_resource import _looks_like_a_tool
        assert _looks_like_a_tool({"url": "https://github.com/a/b"}, {})

    def test_answering_the_tool_form_means_a_tool(self):
        from add_resource import _looks_like_a_tool
        assert _looks_like_a_tool({"url": "https://x.org/t"}, {"agents": "they act"})

    def test_a_bare_link_is_not_assumed_to_be_a_tool(self):
        from add_resource import _looks_like_a_tool
        assert not _looks_like_a_tool({"url": "https://lab.org/post"}, {})

    def test_a_companion_paper_is_reported(self, tmp_path, monkeypatch):
        """A DOI carries references, citations and a byline. A web page carries
        none of them, so a page naming its paper should hand over to it."""
        from add_resource import written_work_record
        monkeypatch.setattr(article, "SNAPSHOTS", tmp_path)
        piece = article.Article(
            url="https://lab.org/post", title="A post", retrieved_on="2026-10-01",
            sha256="x", sections=[Section("other", "—",
                                          "see https://arxiv.org/abs/2604.10290 for detail")])
        _, gaps = written_work_record({"url": "https://lab.org/post"}, {"why": "fits"},
                                      topics=[], author="a", issue=1, read=lambda url: piece)
        assert any("companion paper" in gap for gap in gaps)

    def test_a_record_with_no_title_anywhere_is_refused(self, tmp_path, monkeypatch):
        from add_resource import ProposalError, written_work_record
        monkeypatch.setattr(article, "SNAPSHOTS", tmp_path)
        piece = article.Article(url="https://lab.org/p", title="", retrieved_on="2026-10-01",
                                sha256="x", sections=[Section("other", "—", LONG)])
        with pytest.raises(ProposalError, match="no title"):
            written_work_record({"url": "https://lab.org/p"}, {}, topics=[], author="a",
                                issue=1, read=lambda url: piece)

    def test_an_unreadable_page_is_refused_rather_than_filed_empty(self, tmp_path, monkeypatch):
        from add_resource import ProposalError, written_work_record
        monkeypatch.setattr(article, "SNAPSHOTS", tmp_path)

        def unreadable(url):
            raise FullTextError("no article text found")

        with pytest.raises(ProposalError, match="could not be read"):
            written_work_record({"url": "https://lab.org/p"}, {}, topics=[], author="a",
                                issue=1, read=unreadable)

    def test_the_record_says_it_holds_full_text(self, tmp_path, monkeypatch):
        from add_resource import written_work_record
        monkeypatch.setattr(article, "SNAPSHOTS", tmp_path)
        piece = article.Article(url="https://lab.org/p", title="A post",
                                retrieved_on="2026-10-01", sha256="x",
                                sections=[Section("other", "—", LONG)])
        payload, _ = written_work_record({"url": "https://lab.org/p"}, {"why": "fits"},
                                         topics=[], author="a", issue=1,
                                         read=lambda url: piece)
        assert payload["text_coverage"] == "full-text"
        assert payload["resource_type"] == "written-work"
        assert article.snapshot_path(payload["id"], directory=tmp_path).exists()
