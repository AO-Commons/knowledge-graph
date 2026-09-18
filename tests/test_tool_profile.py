"""The profiler's refusals, mostly.

What it writes when everything is present matters less than what it does when
something is missing, because the missing case is the common one: a README
that is a feature list, a docs page that will not load, an API that returns a
500. Every one of those has to end in no record rather than a thin one.
"""

from __future__ import annotations

import pytest

from ao_commons_kg.tool_profile import (
    Document, ProfileUnavailable, doc_links, draft_from, existing_links,
    page_title, parse_draft, readme_urls, record_for, to_text,
)
from ao_commons_kg.tooling import Entry

ENTRY = Entry(name="Example Tool", url="https://github.com/acme/example",
              section="Managing the Company",
              description="Upstream's one-line blurb about agents.")
DOCS = [Document(url="https://github.com/acme/example",
                 title="Example Tool — repository README", text="# Example")]

GOOD = {
    "agent_model": "Agents draft and send messages on their own.",
    "human_controls": "An operator approves each send; approval is the product, not a setting.",
    "undocumented": "Rate limits and audit log retention are not documented.",
    "description": "Email infrastructure for agents.",
    "fields": {"maintainer": "Acme", "open_source": "yes", "languages": ["Go"]},
    "facets": {"maturity_of_subject": "prototype"},
    "supports": {"https://github.com/acme/example": ["agent_model", "human_controls"]},
    "confident": True,
}


def test_a_complete_reply_becomes_a_draft():
    draft = draft_from(ENTRY, DOCS, GOOD)
    assert draft.agent_model.startswith("Agents draft")
    assert draft.fields["open_source"] == "yes"


# A README that is a feature list is the normal case, not an error. The first
# live run refused LangGraph on its README alone and was right to.
def test_an_unconfident_reply_is_refused():
    with pytest.raises(ProfileUnavailable, match="refused rather than guessed"):
        draft_from(ENTRY, DOCS, {**GOOD, "confident": False})


@pytest.mark.parametrize("missing", ["agent_model", "human_controls"])
def test_a_profile_that_answers_neither_question_is_not_a_profile(missing):
    with pytest.raises(ProfileUnavailable):
        draft_from(ENTRY, DOCS, {**GOOD, missing: ""})


# The most useful sentence in the hand-written AgentTeam profile is the one
# saying what its documentation leaves out.
def test_a_profile_claiming_to_be_complete_is_refused():
    with pytest.raises(ProfileUnavailable, match="claims to be complete"):
        draft_from(ENTRY, DOCS, {**GOOD, "undocumented": ""})


def test_a_claim_traced_to_no_document_is_refused():
    with pytest.raises(ProfileUnavailable, match="untraceable"):
        draft_from(ENTRY, DOCS, {**GOOD, "supports": {}})


def test_a_document_nobody_fetched_cannot_support_anything():
    payload = {**GOOD, "supports": {"https://invented.example/docs": ["agent_model"]}}
    with pytest.raises(ProfileUnavailable, match="untraceable"):
        draft_from(ENTRY, DOCS, payload)


# The tri-state fields exist so an unresearched tool is never silently
# recorded as proprietary. Writing `unknown` out explicitly would read as
# though somebody had looked.
def test_unknown_is_left_off_rather_than_written():
    draft = draft_from(ENTRY, DOCS, {**GOOD, "fields": {"open_source": "unknown"}})
    assert "open_source" not in draft.fields


def test_a_value_outside_the_tri_state_is_dropped():
    draft = draft_from(ENTRY, DOCS, {**GOOD, "fields": {"self_hostable": "probably"}})
    assert "self_hostable" not in draft.fields


def test_a_field_the_schema_does_not_have_is_dropped():
    draft = draft_from(ENTRY, DOCS, {**GOOD, "fields": {"vibes": "excellent"}})
    assert "vibes" not in draft.fields


def test_a_facet_value_outside_the_vocabulary_is_dropped():
    draft = draft_from(ENTRY, DOCS, {**GOOD, "facets": {"maturity_of_subject": "vapourware"}})
    assert "maturity_of_subject" not in draft.facets


def test_every_profile_is_a_code_tool_from_a_vendor():
    draft = draft_from(ENTRY, DOCS, {**GOOD, "facets": {}})
    assert draft.facets["artifact_type"] == "code-tool"
    assert draft.facets["source_independence"] == "tooling-vendor"


# ---- the record ------------------------------------------------------------

def test_the_record_carries_its_sources_and_what_each_supports():
    record = record_for(ENTRY, draft_from(ENTRY, DOCS, GOOD), DOCS, today="2026-09-18")
    assert record["id"] == "resource:tool:example-tool"
    assert record["review_status"] == "unreviewed"
    assert record["sources"][0]["supports"] == ["agent_model", "human_controls"]
    assert record["sources"][0]["accessed"] == "2026-09-18"


def test_what_is_undocumented_survives_into_the_record():
    record = record_for(ENTRY, draft_from(ENTRY, DOCS, GOOD), DOCS, today="2026-09-18")
    assert "Rate limits and audit log retention are not documented" in record["source_provenance"]
    assert "claude-opus-5" in record["source_provenance"]


# Filing moved to stage 7 and derives from what a record's statements say. A
# profiler guessing at codes would add to the 28 records already carrying none
# and the two thirds carrying more than one.
def test_a_profile_files_itself_under_nothing():
    record = record_for(ENTRY, draft_from(ENTRY, DOCS, GOOD), DOCS, today="2026-09-18")
    assert "taxonomy_topics" not in record


# ---- reading the documents -------------------------------------------------

def test_readme_is_looked_for_at_the_raw_host():
    urls = readme_urls("https://github.com/acme/example")
    assert urls[0] == "https://raw.githubusercontent.com/acme/example/HEAD/README.md"


def test_a_url_that_is_not_a_github_repo_is_tried_as_given():
    assert readme_urls("https://example.com/tool") == ["https://example.com/tool"]


# LangGraph's human-in-the-loop page is 200,000 characters and the first
# 60,000 — the slice that would reach the model — are script tags and
# navigation. The tool was refused twice on a page that answers the question.
def test_html_is_reduced_to_its_words():
    html = ("<!doctype html><html><head><style>.a{color:red}</style>"
            "<script>var x = 'interrupt';</script></head>"
            "<body><nav>Home</nav><p>Graph waits indefinitely&nbsp;until you resume.</p>"
            "</body></html>")
    text = to_text(html)
    assert "Graph waits indefinitely until you resume." in text
    assert "color:red" not in text and "var x" not in text


def test_markdown_passes_through_untouched():
    markdown = "# Title\n\nA <b>bold</b> word in prose."
    assert to_text(markdown) == markdown


def test_only_links_about_authority_are_followed():
    readme = (
        "[Human in the loop](https://docs.example.com/human-in-the-loop)\n"
        "[Pricing](https://example.com/pricing)\n"
        "[Build badge](https://shields.io/badge/approval.svg)\n"
        "[Permissions](https://docs.example.com/permissions)\n"
    )
    assert doc_links(readme) == ["https://docs.example.com/human-in-the-loop",
                                 "https://docs.example.com/permissions"]


def test_following_documentation_is_bounded():
    readme = "\n".join(
        f"[doc](https://docs.example.com/approval-{i})" for i in range(20))
    assert len(doc_links(readme, limit=3)) == 3


def test_a_page_is_cited_by_a_name_somebody_can_read():
    assert page_title("https://docs.langchain.com/oss/python/langgraph/interrupts") \
        == "Docs: interrupts"


# ---- the mirror ------------------------------------------------------------

# Nine tools were profiled and one mirror entry said so, which made the
# shortlist offer up finished work and the mirror understate the library.
def test_a_profile_that_already_exists_relinks_its_mirror_entry(tmp_path):
    (tmp_path / "tool-example.yml").write_text(
        "id: resource:tool:example\nrepository_url: https://github.com/acme/example/\n",
        encoding="utf-8")
    assert existing_links([ENTRY], tmp_path) == {"Example Tool": "resource:tool:example"}


def test_an_entry_already_linked_is_left_alone(tmp_path):
    (tmp_path / "tool-example.yml").write_text(
        "id: resource:tool:example\nrepository_url: https://github.com/acme/example\n",
        encoding="utf-8")
    linked = Entry(name="Example Tool", url="https://github.com/acme/example",
                   section="s", promoted_to="resource:tool:example")
    assert existing_links([linked], tmp_path) == {}


def test_an_unreadable_record_is_not_a_link(tmp_path):
    (tmp_path / "tool-broken.yml").write_text("id: [unclosed\n", encoding="utf-8")
    assert existing_links([ENTRY], tmp_path) == {}


# ---- parsing ---------------------------------------------------------------

def test_a_reply_wrapped_in_prose_still_parses():
    assert parse_draft('Here you go:\n```json\n{"agent_model": "x"}\n```') == {"agent_model": "x"}


def test_a_reply_cut_off_mid_object_says_so():
    with pytest.raises(ProfileUnavailable, match="max_tokens"):
        parse_draft('{"agent_model": "a long answer that never')
