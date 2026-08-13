"""Proposals entering the corpus.

This one lands without review, so the tests are mostly about what it refuses:
a duplicate, a typo'd topic code, a link with nothing behind it. The parsing
tests use the three body shapes that actually arrive — the issue form, the
site's paper body, the site's tool body — because a parser that only handles
the one you wrote it against is the failure this file exists to catch.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from add_resource import (  # noqa: E402
    ProposalError,
    already_held,
    identify,
    paper_record,
    process,
    read_issue,
    read_topics,
    thing_record,
    write_record,
)
from ao_commons_kg.models import Resource  # noqa: E402

KNOWN_TOPICS = {"2.2", "4.1", "5.3.1", "11.6", "11.10"}

FORM = """### DOI, arXiv id, or link

2502.14143

### Title

_No response_

### Why does it belong?

Agents hold budget authority in every deployment it studies.

### Topics, if you already know them

2.2, 11.6
"""

FROM_SITE = """**Identifier:** 2502.14143
**Title:** Governable Agent Organizations

**Topics the contributor confirmed:** 5.3.1, 4.1

**Notes**

Worth reading next to the Melting Pot line of work.
"""

TOOL = """**Name:** Buzz
**Link:** https://github.com/block/buzz

**What it does**

An open-source workspace for running teams of agents against business goals.

**How agents participate**

Agents are peers with their own permissions and can call each other.

**Oversight it ships**

Spending caps, approval gates, and a full audit trail.

**Maintainer:** Block, Inc.
**License and source:** Apache-2.0 · github.com/block/buzz
"""


class TestReadIssue:
    def test_the_issue_form_shape(self):
        fields = read_issue(FORM)
        assert fields["identifier"] == "2502.14143"
        assert fields["topics"] == "2.2, 11.6"
        assert "budget authority" in fields["why"]

    def test_github_no_response_is_not_a_title(self):
        """`_No response_` is what an untouched optional field looks like, and
        filing a paper under it would be worse than filing it untitled."""
        assert "title" not in read_issue(FORM)

    def test_the_sites_paper_shape(self):
        fields = read_issue(FROM_SITE)
        assert fields["title"] == "Governable Agent Organizations"
        assert fields["topics"] == "5.3.1, 4.1"
        assert fields["why"].startswith("Worth reading")

    def test_the_sites_tool_shape(self):
        fields = read_issue(TOOL)
        assert fields["name"] == "Buzz"
        assert fields["agents"].startswith("Agents are peers")
        assert fields["controls"].startswith("Spending caps")
        assert fields["maintainer"] == "Block, Inc."

    def test_an_em_dash_means_empty(self):
        """The site writes — for a field nobody filled in."""
        assert "maintainer" not in read_issue("**Maintainer:** —")

    def test_an_unknown_section_does_not_join_the_previous_answer(self):
        body = "**What it does**\n\nRuns agents.\n\n### Some heading we do not know\n\nnoise\n"
        assert read_issue(body)["summary"] == "Runs agents."

    def test_prose_with_no_fields_reads_as_empty(self):
        assert read_issue("I think you should add this paper, it is good.") == {}


class TestIdentify:
    def test_a_bare_arxiv_id(self):
        assert identify("2502.14143") == {"kind": "paper", "arxiv": "2502.14143", "label": "2502.14143"}

    def test_an_arxiv_url(self):
        assert identify("https://arxiv.org/abs/2502.14143")["arxiv"] == "2502.14143"

    def test_a_version_suffix_is_dropped(self):
        """v1 and v2 are the same paper, and filing them apart would split its
        citations in half."""
        assert identify("2502.14143v2")["arxiv"] == "2502.14143"

    def test_a_doi_url_is_a_doi(self):
        assert identify("https://doi.org/10.1145/3770291.3770333")["doi"] == "10.1145/3770291.3770333"

    def test_a_plain_link_is_a_thing_to_describe(self):
        assert identify("https://paperclip.ing")["kind"] == "thing"

    def test_a_bare_domain_is_still_a_link(self):
        assert identify("paperclip.ing")["url"] == "https://paperclip.ing"

    def test_nonsense_is_refused_with_the_shapes_it_accepts(self):
        with pytest.raises(ProposalError, match="DOI, an arXiv id, or a link"):
            identify("the melting pot paper")


class TestAlreadyHeld:
    def test_the_same_arxiv_id(self):
        held = [Resource(id="resource:arxiv:2502.14143", resource_type="preprint",
                         title="Held", arxiv_id="2502.14143")]
        assert already_held(identify("2502.14143"), held) is held[0]

    def test_an_arxiv_doi_finds_the_arxiv_record(self):
        """arXiv DOIs are minted mechanically, so `10.48550/arXiv.2502.14143`
        and `2502.14143` are one paper. Comparing raw strings would miss it and
        the corpus would hold it twice."""
        held = [Resource(id="resource:arxiv:2502.14143", resource_type="preprint",
                         title="Held", arxiv_id="2502.14143")]
        assert already_held(identify("10.48550/arXiv.2502.14143"), held) is held[0]

    def test_a_trailing_slash_is_not_a_different_tool(self):
        held = [Resource(id="resource:tool:paperclip", resource_type="code-tool",
                         title="Paperclip", url="https://paperclip.ing")]
        assert already_held(identify("https://paperclip.ing/"), held) is held[0]

    def test_something_genuinely_new_is_not_a_duplicate(self):
        held = [Resource(id="resource:arxiv:2502.14143", resource_type="preprint",
                         title="Held", arxiv_id="2502.14143")]
        assert already_held(identify("2107.06857"), held) is None


class TestTopics:
    def test_codes_are_sorted_numerically(self):
        assert read_topics("11.6, 2.2, 4.1", KNOWN_TOPICS) == ["2.2", "4.1", "11.6"]

    def test_a_code_that_does_not_exist_stops_the_add(self):
        """Almost always a typo for a code that does. Dropping it silently
        would lose a judgement the contributor thinks they recorded."""
        with pytest.raises(ProposalError, match="99.9"):
            read_topics("2.2, 99.9", KNOWN_TOPICS)

    def test_no_topics_is_fine(self):
        assert read_topics("", KNOWN_TOPICS) == []

    def test_neighbouring_codes_are_kept_apart(self):
        """11.1 and 11.10 are different topics; text keeps them that way."""
        assert read_topics("11.10", KNOWN_TOPICS | {"11.1"}) == ["11.10"]


class FakeWork:
    openalex_id = "https://openalex.org/W4406789"
    title = "Governable Agent Organizations"
    abstract = "We study organizations in which agents hold budget authority."
    authors = ["Joel Z Leibo", "Helena Rong"]
    institutions = ["DeepMind"]
    publication_date = "2026-02-20"
    is_open_access = True
    is_retracted = False
    type = "preprint"


class TestPaperRecord:
    def _build(self, body=FROM_SITE, **kwargs):
        fields = read_issue(body)
        return paper_record(
            identify(fields["identifier"]), fields,
            topics=read_topics(fields.get("topics", ""), KNOWN_TOPICS),
            author="ankeliu", issue=7,
            fetch_openalex=lambda url: {}, **kwargs,
        )

    def test_it_builds_a_record_the_model_accepts(self, monkeypatch):
        import add_resource

        monkeypatch.setattr(add_resource.openalex, "resolve_work", lambda i, f: FakeWork())
        payload, _ = self._build()
        payload = {k: v for k, v in payload.items() if v not in (None, [], {}, "")}
        assert Resource(**payload).id == "resource:arxiv:2502.14143"

    def test_the_bylines_spelling_follows_the_corpus(self, monkeypatch):
        """OpenAlex writes "Joel Z Leibo"; the corpus writes "Joel Z. Leibo".
        Taking the fetched spelling would put one researcher in the graph
        twice."""
        import add_resource

        monkeypatch.setattr(add_resource.openalex, "resolve_work", lambda i, f: FakeWork())
        payload, _ = self._build(known_names={"Joel Z Leibo": "Joel Z. Leibo"})
        assert payload["authors"][0] == "Joel Z. Leibo"

    def test_an_arxiv_paper_gets_its_minted_doi(self, monkeypatch):
        import add_resource

        monkeypatch.setattr(add_resource.openalex, "resolve_work", lambda i, f: FakeWork())
        payload, _ = self._build()
        assert payload["doi"] == "10.48550/arXiv.2502.14143"
        assert payload["resource_type"] == "preprint"

    def test_an_unresolvable_paper_still_lands_if_it_has_a_title(self, monkeypatch):
        """The lookup is a convenience. Losing a contribution because OpenAlex
        was down would teach people not to bother."""
        import add_resource

        def fail(identifier, fetch):
            raise add_resource.openalex.OpenAlexError("404")

        monkeypatch.setattr(add_resource.openalex, "resolve_work", fail)
        payload, gaps = self._build()
        assert payload["title"] == "Governable Agent Organizations"
        assert any("OpenAlex" in gap for gap in gaps)

    def test_no_title_and_no_lookup_is_refused(self, monkeypatch):
        import add_resource

        def fail(identifier, fetch):
            raise add_resource.openalex.OpenAlexError("404")

        monkeypatch.setattr(add_resource.openalex, "resolve_work", fail)
        with pytest.raises(ProposalError, match="No title"):
            self._build(body=FORM)

    def test_provenance_says_the_tags_are_unreviewed(self, monkeypatch):
        import add_resource

        monkeypatch.setattr(add_resource.openalex, "resolve_work", lambda i, f: FakeWork())
        payload, _ = self._build()
        assert "unreviewed" in payload["source_provenance"]
        assert payload["review_status"] == "unreviewed"


class TestThingRecord:
    def _build(self, body=TOOL):
        fields = read_issue(body)
        return thing_record(identify(fields["identifier"]), fields,
                            topics=[], author="ankeliu", issue=8)

    def test_it_builds_a_tool_record_the_model_accepts(self):
        payload, _ = self._build()
        payload = {k: v for k, v in payload.items() if v not in (None, [], {}, "")}
        resource = Resource(**payload)
        assert resource.id == "resource:tool:buzz"
        assert resource.tool.human_controls.startswith("Spending caps")

    def test_a_github_link_is_recorded_as_the_repository(self):
        assert self._build()[0]["repository_url"] == "https://github.com/block/buzz"

    def test_an_unresearched_tool_is_never_recorded_as_proprietary(self):
        """`unknown` and `no` are different claims. Defaulting to the second
        would put a false fact in the graph."""
        body = TOOL.replace("**License and source:** Apache-2.0 · github.com/block/buzz", "")
        assert self._build(body)[0]["tool"]["open_source"] == "unknown"

    def test_a_tool_with_no_description_is_refused(self):
        body = "**Name:** Buzz\n**Link:** https://buzz.xyz\n"
        with pytest.raises(ProposalError, match="what Buzz does"):
            self._build(body)

    def test_missing_answers_are_reported_rather_than_invented(self):
        body = "**Name:** Buzz\n**Link:** https://buzz.xyz\n\n**What it does**\n\nRuns agent teams for you.\n"
        _, gaps = self._build(body)
        assert any("how agents participate" in gap for gap in gaps)


class TestProcess:
    def _run(self, body, resources=(), **kwargs):
        return process(body, author="ankeliu", issue=9, resources=list(resources),
                       known_topics=KNOWN_TOPICS, **kwargs)

    def test_a_duplicate_is_an_ordinary_answer_not_an_error(self, tmp_path):
        """Two people proposing the same paper is normal. Failing the run on it
        would train contributors to ignore the bot."""
        held = [Resource(id="resource:arxiv:2502.14143", resource_type="preprint",
                         title="Held", arxiv_id="2502.14143")]
        summary, payload = self._run(FROM_SITE, held)
        assert payload is None and "Already in the library" in summary

    def test_an_empty_issue_says_what_is_missing(self):
        with pytest.raises(ProposalError, match="DOI, an arXiv id, or a link"):
            self._run("I would like to add a paper please.")

    def test_a_tool_goes_all_the_way_through(self):
        summary, payload = self._run(TOOL)
        assert payload["id"] == "resource:tool:buzz"
        assert "Buzz" in summary

    def test_the_summary_carries_the_contributors_reasoning(self, monkeypatch):
        import add_resource

        monkeypatch.setattr(add_resource.openalex, "resolve_work", lambda i, f: FakeWork())
        summary, _ = self._run(FORM, fetch_openalex=lambda url: {})
        assert "budget authority" in summary


def test_the_record_lands_where_the_loader_will_find_it(tmp_path, monkeypatch):
    """The file name is derived from the id, and the loader reads the directory
    by glob — so a wrong name is a record that exists and is never loaded."""
    import add_resource

    monkeypatch.setattr(add_resource, "RESOURCES", tmp_path)
    fields = read_issue(TOOL)
    payload, _ = thing_record(identify(fields["identifier"]), fields,
                              topics=["2.2"], author="ankeliu", issue=8)
    path = write_record(payload)

    from ao_commons_kg.resources import load_resources

    assert path.name == "tool-buzz.yml"
    assert [r.id for r in load_resources(tmp_path)] == ["resource:tool:buzz"]


class TestBylines:
    """OpenAlex disambiguates authors by machine, and when it is wrong it names
    a real, plausible, different person. It credited this corpus's Botao
    'Amber' Hu paper to "Bin Hu" — invisible to anyone who does not know the
    field, and the worst error the project can make."""

    def _build(self, byline, **kwargs):
        import add_resource

        fields = read_issue(FROM_SITE)
        return paper_record(
            identify(fields["identifier"]), fields, topics=[], author="ankeliu", issue=7,
            fetch_openalex=lambda url: {},
            fetch_byline=lambda arxiv_id: byline, **kwargs,
        )

    def test_arxiv_outranks_openalex(self, monkeypatch):
        import add_resource

        monkeypatch.setattr(add_resource.openalex, "resolve_work", lambda i, f: FakeWork())
        payload, _ = self._build(["Botao 'Amber' Hu", "Helena Rong"])
        assert payload["authors"] == ["Botao 'Amber' Hu", "Helena Rong"]

    def test_the_substitution_is_reported_not_silently_corrected(self, monkeypatch):
        """A maintainer should see that the resolver got a person wrong, not
        just a quietly different byline."""
        import add_resource

        monkeypatch.setattr(add_resource.openalex, "resolve_work", lambda i, f: FakeWork())
        _, gaps = self._build(["Botao 'Amber' Hu", "Helena Rong"])
        assert any("Joel Z Leibo" in gap and "arXiv does not list" in gap for gap in gaps)

    def test_a_spelling_difference_is_not_reported_as_a_substitution(self, monkeypatch):
        import add_resource

        monkeypatch.setattr(add_resource.openalex, "resolve_work", lambda i, f: FakeWork())
        _, gaps = self._build(["Joel Z. Leibo", "Helena Rong"])
        assert not any("does not list" in gap for gap in gaps)

    def test_an_unreachable_arxiv_never_blocks_the_add(self, monkeypatch):
        """A byline check is a nicety. Losing a contribution to it would be a
        poor trade."""
        import add_resource

        monkeypatch.setattr(add_resource.openalex, "resolve_work", lambda i, f: FakeWork())
        fields = read_issue(FROM_SITE)

        def boom(arxiv_id):
            raise RuntimeError("arXiv is down")

        payload, _ = paper_record(
            identify(fields["identifier"]), fields, topics=[], author="a", issue=1,
            fetch_openalex=lambda url: {}, fetch_byline=boom,
        )
        assert payload["authors"]
