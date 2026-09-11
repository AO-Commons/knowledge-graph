"""The Docs tab: what the project is, said on the project's own page.

Two things are worth testing about a documentation page. That its numbers come
from the corpus rather than from whoever last edited the prose — a page that
states its own figures is the thing people check the figures against, so it
is the last place that should be able to drift. And that it did not break the
four screens it sits beside.
"""

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def page():
    return (ROOT / "site" / "template.html").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def built():
    return (ROOT / "site" / "index.html").read_text(encoding="utf-8")


class TestTheTab:
    def test_it_is_in_the_masthead_and_wired(self, page):
        assert '<button id="mode-docs"' in page
        assert '"mode-docs").addEventListener' in page
        assert "docs: renderDocs" in page

    def test_the_page_is_named_for_the_graph(self, page):
        assert "AO&nbsp;Knowledge&nbsp;Graph" in page
        assert "<title>AO Knowledge Graph</title>" in page

    def test_every_section_the_contents_promises_exists(self, page):
        listed = re.findall(r'\["(\w+)", "[^"]+"\]', page.split("DOCS_SECTIONS = [")[1].split("];")[0])
        assert len(listed) >= 8
        for section in listed:
            assert f'section("{section}"' in page, f"{section} is in the contents and nowhere else"


class TestTheFiguresAreMeasured:
    """Hard-coding them is how a page ends up describing a corpus that no
    longer exists, while being the thing everyone trusts for the numbers."""

    def test_the_payload_carries_them(self, built):
        stats = json.loads(re.search(r'"stats":(\{.*?"built":"[\d-]+"\})', built).group(1))
        for key in ("records", "statements", "papers_with_statements", "primary",
                    "reviewed", "concepts_in_use", "relations", "citation_edges",
                    "with_references", "vocabulary", "suggestion_pool", "releases",
                    "by_type", "topics"):
            assert key in stats, key

    def test_they_match_the_corpus(self, built):
        from ao_commons_kg.claims import load_claims, load_claim_relations
        from ao_commons_kg.resources import load_resources

        stats = json.loads(re.search(r'"stats":(\{.*?"built":"[\d-]+"\})', built).group(1))
        claims = load_claims()
        assert stats["records"] == len(load_resources())
        assert stats["statements"] == len(claims)
        assert stats["relations"] == len(load_claim_relations(claims=claims))
        assert stats["primary"] == sum(1 for c in claims if c.claim_type.is_primary)

    def test_the_page_reads_them_rather_than_stating_them(self, page):
        docs = page.split("function renderDocs()")[1].split("function renderDocsNav")[0]
        assert "DATA.stats" in docs
        # The one number written out in prose is the corpus-wide estimate that
        # is not derivable from the corpus, and it is marked as an estimate.
        assert "roughly 4,900 records" in docs


class TestItDidNotBreakTheOtherScreens:
    """Both bugs found here were the same bug: a class name this page chose
    was already doing a job elsewhere, and CSS does not warn."""

    def test_the_docs_styles_are_scoped(self, page):
        """`#stage` already carried `class="stage"`, so an unscoped `.stage`
        rule turned the main column of every screen into a two-track grid."""
        block = page.split("/* ---- Docs ---")[1].split("</style>")[0]
        for rule in re.findall(r"(?m)^  (\.[\w.\- ]+?) \{", block):
            assert rule.startswith(".docs"), f"{rule} is not scoped to the docs page"

    def test_the_diagram_classes_are_namespaced(self, page):
        """`width` is a CSS property on an SVG rect, and the page already had
        `.node { width: 100% }` for the taxonomy rows — so every box in the
        diagram drew at the full width of the canvas, attribute ignored."""
        diagram = page.split("function nodeBox(")[1].split("function renderDocs")[0]
        assert 'class: "dg-node"' in diagram
        assert 'class: "node ' not in diagram

    def test_hidden_actually_hides(self, page):
        """`[hidden]` is a user-agent rule and loses to any class rule that
        sets `display`. The taxonomy heading was marked hidden weeks before
        this and sat on screen the whole time, reading "70/103 filed" above
        nothing."""
        assert "[hidden] { display: none !important; }" in page
