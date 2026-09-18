"""What the profiling run says in Slack.

Mostly about what it does when something is missing. A notification that fails
loudly is annoying; one that fails silently means the run stops being visible
without anybody deciding that it should.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import notify_slack  # noqa: E402

SUMMARY = {
    "profiled": [
        {"name": "LangGraph", "url": "https://github.com/langchain-ai/langgraph",
         "undocumented": "No spend caps, budgets, or transaction limits. No kill switch."},
    ],
    "refused": [
        {"name": "Mastra", "why": "Mastra: the documentation does not say what agents "
                                  "may do or what constrains them; refused rather than guessed"},
    ],
    "waiting": 50,
    "relinked": [],
    "dry_run": False,
}


def test_it_says_what_was_profiled_and_what_the_docs_leave_out():
    text = notify_slack.summarize(SUMMARY, url="https://example.com/pr/1")
    assert "1 tool profiled" in text
    assert "LangGraph" in text
    assert "No spend caps, budgets, or transaction limits" in text
    assert "https://example.com/pr/1" in text


# A tool whose README never says what stops an agent is a finding about that
# tool, not noise to trim out of the message.
def test_refusals_are_reported_with_their_reason():
    text = notify_slack.summarize(SUMMARY)
    assert "1 refused" in text
    assert "Mastra" in text
    assert "does not say what agents may do" in text


def test_a_refusal_does_not_repeat_the_tool_name():
    assert notify_slack._short("Mastra: the README is a feature list") \
        == "the README is a feature list"


def test_a_long_refusal_is_cut_rather_than_wrapped():
    assert notify_slack._short("x" * 300).endswith("…")
    assert len(notify_slack._short("x" * 300)) <= 110


def test_an_empty_run_still_says_so():
    text = notify_slack.summarize({"profiled": [], "refused": [], "waiting": 52})
    assert "Nothing profiled" in text
    assert "52 still unprofiled" in text


def test_a_dry_run_says_nothing_was_written():
    text = notify_slack.summarize({**SUMMARY, "dry_run": True})
    assert "Dry run" in text


def test_links_do_not_unfurl(monkeypatch):
    """A profile links a repository and its docs. Unfurling each of those turns
    four lines into a screen."""
    sent = {}

    class Response:
        def read(self):
            return b'{"ok": true}'

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def urlopen(request, timeout=0):
        sent.update(json.loads(request.data))
        return Response()

    monkeypatch.setattr(notify_slack.urllib.request, "urlopen", urlopen)
    notify_slack.post("hello", token="xoxb-test", channel="knowledge-graph")
    assert sent["unfurl_links"] is False
    assert sent["unfurl_media"] is False


# ---- a missing credential is a quiet run, never a failed one ---------------

def test_without_a_token_it_prints_what_it_would_have_said(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
    path = tmp_path / "summary.json"
    path.write_text(json.dumps(SUMMARY), encoding="utf-8")

    assert notify_slack.main(["--summary", str(path)]) == 0
    out = capsys.readouterr().out
    assert "SLACK_BOT_TOKEN is not set" in out
    assert "LangGraph" in out, "and says it loudly enough to notice"


def test_no_summary_file_is_not_an_error(tmp_path, capsys):
    assert notify_slack.main(["--summary", str(tmp_path / "absent.json")]) == 0
    assert "nothing to say" in capsys.readouterr().out


def test_a_failed_post_does_not_fail_the_run(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test")
    path = tmp_path / "summary.json"
    path.write_text(json.dumps(SUMMARY), encoding="utf-8")

    def boom(*args, **kwargs):
        raise OSError("connection reset")

    monkeypatch.setattr(notify_slack, "post", boom)
    assert notify_slack.main(["--summary", str(path)]) == 0
    assert "could not post to Slack" in capsys.readouterr().err


# The error that actually happens, whose fix is a human action in Slack.
def test_not_in_channel_says_what_to_do_about_it(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test")
    path = tmp_path / "summary.json"
    path.write_text(json.dumps(SUMMARY), encoding="utf-8")

    monkeypatch.setattr(notify_slack, "post",
                        lambda *a, **k: {"ok": False, "error": "not_in_channel"})
    assert notify_slack.main(["--summary", str(path), "--channel", "knowledge-graph"]) == 0
    assert "invite the app to #knowledge-graph" in capsys.readouterr().err


@pytest.mark.parametrize("error,expected", [
    ("invalid_auth", "revoked"),
    ("channel_not_found", "does not exist"),
])
def test_other_refusals_are_explained_too(tmp_path, capsys, monkeypatch, error, expected):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test")
    path = tmp_path / "summary.json"
    path.write_text(json.dumps(SUMMARY), encoding="utf-8")
    monkeypatch.setattr(notify_slack, "post", lambda *a, **k: {"ok": False, "error": error})
    notify_slack.main(["--summary", str(path)])
    assert expected in capsys.readouterr().err
