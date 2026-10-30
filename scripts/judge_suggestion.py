#!/usr/bin/env python3
"""Decide whether a suggested record is in scope, before anything is written.

    python3 scripts/judge_suggestion.py --body-file /tmp/proposal.md \
        --out /tmp/verdict.json

Filing used to be unconditional: an issue carrying an identifier became a
record, resolved and committed, within a minute. That was defensible while the
door was effectively internal. It is not defensible on a public repository,
where the same minute is available to anybody.

So the same judge the citation expansion already answers to runs here. One
scope test, one exclusion register, one set of criteria — `scope_judge._prompt`
builds the prompt for both, which is the point of it being shared. A
suggestion that clears it is filed exactly as before. One that does not gets
the reasoning on the issue and nothing in the corpus.

**A judge that cannot answer refuses.** No key, no network, an unparseable
reply — each is a refusal, never an admission. "The API was down so everything
got in" is the failure this gate exists to prevent, and it is the failure a
gate is most likely to have.

Exit codes, because the workflow branches on them rather than parsing stdout:

    0   admit — file it
    0   admit as borrowed background — file it, flagged
    2   refuse — do not file; the reasoning is in --out
    3   could not judge — do not file; configuration or API problem
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from ao_commons_kg.expansion import Candidate, ScopeVerdict  # noqa: E402
from ao_commons_kg.scope_judge import anthropic_judge  # noqa: E402


def metadata_from_body(body: str, issue_title: str = "") -> dict:
    """What the issue form gives us, as the judge's metadata block.

    Deliberately thin. The form asks for a link, a name and a case for
    inclusion, and the case is the part that matters: the judge is being asked
    whether this belongs, and the person proposing it has just answered that
    question in their own words. Resolution against OpenAlex happens after a
    verdict, not before — there is no reason to spend a lookup on something
    about to be refused.
    """
    fields: dict[str, str] = {}
    current = None
    for line in body.splitlines():
        if line.startswith("### "):
            current = line[4:].strip().lower()
            fields[current] = ""
        elif current:
            fields[current] += line + "\n"

    def get(*names: str) -> str:
        for name in names:
            for key, value in fields.items():
                if name in key:
                    text = value.strip()
                    if text and text != "_No response_":
                        return text
        return ""

    why = get("why does it belong", "why")
    kind = get("what is it")
    return {
        "title": (issue_title or get("title or name", "title")
                  or get("link", "identifier") or "(unknown)"),
        "venue": kind,
        "date": "",
        "abstract": why or "(the proposer gave no reason)",
    }


def judge_body(body: str, *, judge=None, issue_title: str = "") -> ScopeVerdict:
    candidate = Candidate(key="suggestion", cited_by=())
    judge = judge or anthropic_judge()
    return judge(candidate, metadata_from_body(body, issue_title))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--body-file", required=True)
    parser.add_argument("--out", default="")
    parser.add_argument("--title", default="", help="the issue's own title")
    args = parser.parse_args(argv)

    body = pathlib.Path(args.body_file).read_text(encoding="utf-8")

    try:
        verdict = judge_body(body, issue_title=args.title)
    except Exception as error:                      # noqa: BLE001
        payload = {"admit": False, "judged": False,
                   "reasoning": f"could not run the scope scan "
                                f"({type(error).__name__}: {error})"}
        if args.out:
            pathlib.Path(args.out).write_text(json.dumps(payload, indent=1), encoding="utf-8")
        print(payload["reasoning"], file=sys.stderr)
        return 3

    payload = {"admit": verdict.admit, "judged": True,
               "borrowed_background": verdict.borrowed_background,
               "judged_by": verdict.judged_by, "reasoning": verdict.reasoning}
    if args.out:
        pathlib.Path(args.out).write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(verdict.reasoning)
    return 0 if verdict.admit else 2


if __name__ == "__main__":
    sys.exit(main())
