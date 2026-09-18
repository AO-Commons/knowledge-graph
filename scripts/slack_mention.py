#!/usr/bin/env python3
"""Answer somebody who tagged the agent in Slack.

Two things can happen, and which one is not the model's decision.

**An addition** — the message carries an identifier and asks for it to go in.
That opens a `new-resource` issue, which is the door the site's Add tab already
uses: `new-resource.yml` resolves the metadata, writes the record and rebuilds
the site. Nothing new downstream.

**A question** — anything else. That goes to `slack_agent`, which reads the
graph through the same tools the MCP server exposes and answers in the thread.

The split is deterministic on purpose. "Machines admit, humans judge" is the
rule the corpus grows under, and letting the model decide it had been asked to
add something would quietly move admission from a person's sentence to a
model's reading of it. A person writing a link and the word "add" is the
judgment; this only carries it.

    python3 scripts/slack_mention.py --channel C0BV170L4GJ --ts 1789…
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

SLACK = "https://slack.com/api/"
GITHUB = "https://api.github.com/"

# An identifier somebody could actually be asking us to file. Deliberately
# narrow: a link to a Slack thread or a GitHub issue is not a paper.
IDENTIFIER = re.compile(
    r"(arxiv\.org/(?:abs|pdf|html)/\d{4}\.\d{4,5}"
    r"|\b\d{4}\.\d{4,5}\b"
    r"|\b10\.\d{4,9}/\S+"
    r"|https?://(?!\S*(?:slack\.com|github\.com/[^/]+/[^/]+/(?:issues|pull)))\S+)", re.I)

# What asking looks like. Without one of these a message with a link in it is
# somebody discussing a paper, not filing one.
ADDING = re.compile(
    r"\b(add|ingest|include|file|index|import|catalogue|catalog)\b", re.I)


class SlackError(RuntimeError):
    pass


def call(method: str, payload: dict, *, token: str) -> dict:
    """One Slack API call. GET for reads, POST for writes, as Slack wants."""
    if method in ("conversations.replies", "conversations.history", "auth.test"):
        url = SLACK + method + "?" + urllib.parse.urlencode(payload)
        request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    else:
        request = urllib.request.Request(
            SLACK + method, data=json.dumps(payload).encode(),
            headers={"Authorization": f"Bearer {token}",
                     "Content-Type": "application/json; charset=utf-8"})
    with urllib.request.urlopen(request, timeout=30) as response:
        body = json.loads(response.read().decode("utf-8"))
    if not body.get("ok"):
        raise SlackError(f"{method}: {body.get('error')}")
    return body


def strip_mention(text: str) -> str:
    """The message without the tag that summoned us.

    Leaving it in means the model reads its own name as part of the question,
    and starts answering as though addressed in the third person.
    """
    return re.sub(r"<@[A-Z0-9]+>", " ", text or "").strip()


def is_addition(text: str) -> str | None:
    """The identifier, if this is somebody asking for something to be filed."""
    if not ADDING.search(text):
        return None
    match = IDENTIFIER.search(text)
    return match.group(0).rstrip(".,;)") if match else None


def issue_body(*, identifier: str, why: str, permalink: str, who: str) -> str:
    """The shape `add_resource.read_issue` reads, which is the Add tab's shape.

    Using the same body means one parser, one set of field names, and no second
    format to keep in step.
    """
    return "\n".join([
        "### DOI, arXiv id, or link", "", identifier, "",
        "### Why does it belong", "",
        why or "Proposed in Slack without a reason given.", "",
        "### Notes", "",
        f"Asked for by {who} in Slack: {permalink}",
        "",
        "Opened by the knowledge-graph Slack agent. The reason above is theirs, "
        "quoted from the message.",
    ])


def open_issue(*, repo: str, token: str, title: str, body: str) -> dict:
    request = urllib.request.Request(
        f"{GITHUB}repos/{repo}/issues",
        data=json.dumps({"title": title, "body": body, "labels": ["new-resource"]}).encode(),
        headers={"Authorization": f"Bearer {token}",
                 "Accept": "application/vnd.github+json",
                 "Content-Type": "application/json",
                 "User-Agent": "ao-commons-kg-slack-agent"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def thread_context(messages: list, *, limit: int = 6) -> str:
    """What was said before, so a follow-up question is answerable.

    Only the thread, only the tail of it, and only text. A question asked five
    replies deep usually depends on the three above it and never on the
    ninety-line digest somebody pasted at the top.
    """
    lines = []
    for message in messages[-limit:]:
        text = strip_mention(message.get("text", ""))
        if text:
            who = "agent" if message.get("bot_id") else "person"
            lines.append(f"{who}: {text}")
    return "\n".join(lines[:-1])   # the last one is the question itself


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--channel", required=True)
    parser.add_argument("--ts", required=True, help="the message that tagged us")
    parser.add_argument("--thread-ts", default="", help="its thread, if it is in one")
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    slack_token = os.environ.get("SLACK_BOT_TOKEN")
    if not slack_token:
        print("SLACK_BOT_TOKEN is not set", file=sys.stderr)
        return 1

    root = args.thread_ts or args.ts
    thread = call("conversations.replies",
                  {"channel": args.channel, "ts": root, "limit": 20},
                  token=slack_token)
    messages = thread.get("messages", [])
    here = next((m for m in messages if m.get("ts") == args.ts), messages[-1] if messages else None)
    if not here:
        print(f"no message at {args.ts}", file=sys.stderr)
        return 1

    question = strip_mention(here.get("text", ""))
    if not question:
        print("tagged with no question; saying nothing")
        return 0

    permalink = call("chat.getPermalink", {"channel": args.channel, "message_ts": args.ts},
                     token=slack_token).get("permalink", "")
    who = f"<@{here.get('user')}>" if here.get("user") else "somebody"

    identifier = is_addition(question)
    if identifier:
        github_token = os.environ.get("GITHUB_TOKEN")
        if args.dry_run or not github_token:
            print(f"would open a new-resource issue for {identifier}")
            return 0
        # The reason is the rest of their sentence. It is what a reviewer reads,
        # and it is theirs — never written for them.
        why = IDENTIFIER.sub("", question).strip(" .,—-")
        issue = open_issue(
            repo=args.repo, token=github_token,
            title=f"[Add] {identifier}",
            body=issue_body(identifier=identifier, why=why, permalink=permalink, who=who))
        reply = (f"Opened <{issue['html_url']}|#{issue['number']}> for `{identifier}`. "
                 "A bot resolves the metadata and writes the record — it lands unreviewed, "
                 "like everything else.")
    else:
        from ao_commons_kg.slack_agent import answer

        result = answer(question, history=thread_context(messages))
        reply = result.text
        if not reply:
            reply = "I could not work out an answer to that from the graph."

    if args.dry_run:
        print(reply)
        return 0

    call("chat.postMessage",
         {"channel": args.channel, "thread_ts": root, "text": reply,
          "unfurl_links": False, "unfurl_media": False},
         token=slack_token)
    print(f"replied in {args.channel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
