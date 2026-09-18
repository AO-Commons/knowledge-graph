"""Tagging the agent: what it treats as a question, and what as an addition.

The split is the part worth testing. It decides whether a sentence becomes a
record in the corpus, and it is deliberately not the model's to make — "machines
admit, humans judge" stops meaning anything if a model can decide it was asked.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import slack_mention  # noqa: E402

is_addition = slack_mention.is_addition


class TestWhatCountsAsAnAddition:
    @pytest.mark.parametrize("text,expected", [
        ("add https://arxiv.org/abs/2502.14143", "https://arxiv.org/abs/2502.14143"),
        ("can you add 2502.14143 — agents approving each other's spend", "2502.14143"),
        ("please include 10.48550/arXiv.2502.14143 under 9.2", "10.48550/arXiv.2502.14143"),
        ("file https://example.org/paper.pdf", "https://example.org/paper.pdf"),
    ])
    def test_an_identifier_and_a_request(self, text, expected):
        assert is_addition(text) == expected

    # Somebody discussing a paper is not somebody filing one, and the
    # difference is the whole of the human judgment this carries.
    @pytest.mark.parametrize("text", [
        "what do we hold on 2502.14143?",
        "https://arxiv.org/abs/2502.14143 is the one Rakshit mentioned",
        "is arxiv 2502.14143 in the graph already",
    ])
    def test_a_link_alone_is_a_question(self, text):
        assert is_addition(text) is None

    def test_asking_without_an_identifier_is_a_question(self):
        assert is_addition("can you add something about agent budgets") is None

    # A Slack permalink or an issue link is what somebody pastes while talking
    # about the thing, never the thing.
    @pytest.mark.parametrize("text", [
        "add this to the list https://aoyeah.slack.com/archives/C0BV170L4GJ/p178968",
        "add it, see https://github.com/AO-Commons/knowledge-graph/issues/14",
    ])
    def test_our_own_links_are_not_papers(self, text):
        assert is_addition(text) is None

    def test_trailing_punctuation_is_not_part_of_the_identifier(self):
        assert is_addition("add https://arxiv.org/abs/2502.14143.") \
            == "https://arxiv.org/abs/2502.14143"


class TestTheMessage:
    def test_the_tag_is_stripped_so_it_is_not_read_as_the_question(self):
        assert slack_mention.strip_mention("<@U0C9ABC> what do we hold on approvals?") \
            == "what do we hold on approvals?"

    def test_a_message_that_is_only_a_tag_has_no_question(self):
        assert slack_mention.strip_mention("<@U0C9ABC>") == ""


class TestTheIssueItOpens:
    def test_it_is_the_shape_add_resource_already_reads(self):
        from add_resource import read_issue

        body = slack_mention.issue_body(
            identifier="2502.14143",
            why="agents approving each other's spend, relevant to 9.2",
            permalink="https://aoyeah.slack.com/archives/C/p1",
            who="<@U0BACG8RS4D>")
        fields = read_issue(body)
        assert fields["identifier"] == "2502.14143"
        assert "approving each other" in fields["why"]

    # The reason a reviewer reads has to be the person's, not one written for
    # them — an invented rationale is the thing the scope test cannot catch.
    def test_a_missing_reason_says_so_rather_than_inventing_one(self):
        from add_resource import read_issue

        body = slack_mention.issue_body(identifier="2502.14143", why="",
                                        permalink="https://x/1", who="somebody")
        assert "without a reason given" in read_issue(body)["why"]

    def test_it_says_where_it_came_from(self):
        body = slack_mention.issue_body(
            identifier="2502.14143", why="because", permalink="https://x/p1", who="<@U1>")
        assert "https://x/p1" in body
        assert "<@U1>" in body


class TestThreadContext:
    def test_the_question_itself_is_not_repeated_as_context(self):
        messages = [{"text": "what about approvals?"}, {"text": "and budgets?"}]
        assert slack_mention.thread_context(messages) == "person: what about approvals?"

    def test_the_agent_is_labelled_so_a_follow_up_reads_correctly(self):
        messages = [{"text": "what about approvals?"},
                    {"text": "Three records, all unreviewed.", "bot_id": "B1"},
                    {"text": "which one is newest?"}]
        context = slack_mention.thread_context(messages)
        assert "person: what about approvals?" in context
        assert "agent: Three records, all unreviewed." in context

    def test_only_the_tail_of_a_long_thread(self):
        messages = [{"text": f"message {i}"} for i in range(30)]
        assert len(slack_mention.thread_context(messages, limit=4).splitlines()) == 3
