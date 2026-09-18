#!/usr/bin/env python3
"""Say in Slack what a profiling run did.

Its own Slack app, deliberately separate from the internal task agent. Two
reasons, and the second is the one that matters.

The small one: this repository is public and that agent reads private channels
and writes to a CRM base. A token that can do both of those should not be a
secret on a public repository, however carefully the workflow is written.

The real one: a bot's name is what a reader uses to decide how much to trust a
message. "Task Digest says three tools were profiled" invites you to read it
like a task update — something to action. This is a different claim, made by a
different process, about a public artifact, and it should arrive under a name
that says so.

No inbound events, so no request URL, no signing secret and no relay. This
posts and stops. A reply in the thread is a conversation between people.

    python3 scripts/notify_slack.py --summary /tmp/profile.json --url <pr url>

Without SLACK_BOT_TOKEN it prints what it would have said and exits cleanly,
the same way the profiler writes nothing without an API key: a missing
credential is a quiet run, never a failed one and never a silent one.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

API = "https://slack.com/api/chat.postMessage"
DEFAULT_CHANNEL = "knowledge-graph"


def summarize(summary: dict, *, url: str = "") -> str:
    """The message, in as few lines as it can be said in.

    What was profiled, what each tool's documentation does not say, what was
    refused and why. The refusals are not noise to be trimmed: a tool whose
    README never says what stops an agent is a finding about that tool.
    """
    profiled = summary.get("profiled") or []
    refused = summary.get("refused") or []
    lines: list[str] = []

    if profiled:
        lines.append(f"*{len(profiled)} tool{'' if len(profiled) == 1 else 's'} profiled*")
        for tool in profiled:
            lines.append(f"• <{tool['url']}|{tool['name']}>")
            gap = (tool.get("undocumented") or "").strip()
            if gap:
                # One sentence. The record carries the whole thing; this is the
                # hook that gets somebody to open it.
                first = gap.split(". ")[0].rstrip(".")
                lines.append(f"    not documented: {first}")
    else:
        lines.append("*Nothing profiled this run.*")

    if refused:
        lines.append("")
        lines.append(f"*{len(refused)} refused*")
        for tool in refused:
            lines.append(f"• {tool['name']} — {_short(tool.get('why', ''))}")

    waiting = summary.get("waiting")
    if waiting:
        lines.append("")
        lines.append(f"{waiting} still unprofiled.")

    if url:
        lines.append(f"Review: {url}")
    if summary.get("dry_run"):
        lines.append("_Dry run — nothing was written._")

    return "\n".join(lines)


def _short(why: str, limit: int = 110) -> str:
    """A refusal, said once.

    The profiler prefixes its reasons with the tool name because the console
    output is a flat list; here the name is already on the line.
    """
    why = why.split(": ", 1)[-1].strip()
    return why if len(why) <= limit else why[:limit - 1].rstrip() + "…"


def post(text: str, *, token: str, channel: str) -> dict:
    payload = json.dumps({
        "channel": channel,
        "text": text,
        # A profile links to a tool's repository and its documentation. Slack
        # unfurling every one of those turns a four-line message into a screen.
        "unfurl_links": False,
        "unfurl_media": False,
    }).encode()
    request = urllib.request.Request(
        API, data=payload,
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json; charset=utf-8"})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", required=True, help="the JSON written by `aokg profile`")
    parser.add_argument("--url", default="", help="pull request or compare link")
    parser.add_argument("--channel", default=os.environ.get("SLACK_CHANNEL", DEFAULT_CHANNEL))
    args = parser.parse_args(argv)

    path = Path(args.summary)
    if not path.exists():
        print(f"no summary at {path}; nothing to say")
        return 0

    text = summarize(json.loads(path.read_text(encoding="utf-8")), url=args.url)

    token = os.environ.get("SLACK_BOT_TOKEN")
    if not token:
        # Loud, because a run that silently stops telling anybody is
        # indistinguishable from a run that stopped happening.
        print("SLACK_BOT_TOKEN is not set — would have posted:\n")
        print(text)
        return 0

    try:
        result = post(text, token=token, channel=args.channel)
    except Exception as error:  # noqa: BLE001 — a failed notification is not a failed run
        print(f"could not post to Slack ({type(error).__name__}: {error})", file=sys.stderr)
        return 0

    if not result.get("ok"):
        # `not_in_channel` is the one that actually happens, and the fix is a
        # human action in Slack, so name it rather than printing a code.
        hint = {"not_in_channel": f"invite the app to #{args.channel}",
                "channel_not_found": f"#{args.channel} does not exist, or the app cannot see it",
                "invalid_auth": "the bot token is wrong or has been revoked"}.get(
                    result.get("error", ""), "")
        print(f"Slack refused the message: {result.get('error')}"
              + (f" — {hint}" if hint else ""), file=sys.stderr)
        return 0

    print(f"posted to #{args.channel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
