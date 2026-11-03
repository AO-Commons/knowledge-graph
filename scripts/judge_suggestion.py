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

**It looks first, then judges.** The form tells people a paper needs only its
link, so the judge must see the paper rather than the link: a suggestion that
is already held is answered as such without a verdict, and a paper is judged on
its title and abstract (from arXiv or OpenAlex) with the proposer's case beside
them. Judging the bare link refused papers the form had invited, and called a
paper the library already holds out of scope.

Exit codes, because the workflow branches on them rather than parsing stdout:

    0   admit — file it
    0   admit as borrowed background — file it, flagged
    2   refuse — do not file; the reasoning is in --out
    3   could not judge — do not file; configuration or API problem
    4   already held — nothing to judge or file; the record is in --out
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

from ao_commons_kg.expansion import Candidate, ScopeVerdict  # noqa: E402
from ao_commons_kg.scope_judge import anthropic_judge  # noqa: E402


def look_up(body: str, *, resources=None, fetch_openalex=None, fetch_arxiv=None) -> dict:
    """Before judging: whether the library holds it already, and what it is.

    Returns {"held": True, "id", "title"} for a duplicate; otherwise what the
    lookups found for a paper ({"title", "abstract", "date"}, any of them), or
    {} for a link with no paper behind it. A lookup that fails is not a reason
    to refuse: the judge then has what the form gave, as before.
    """
    from add_resource import ProposalError, already_held, identify, read_issue
    try:
        ident = identify(read_issue(body).get("identifier", ""))
    except ProposalError:
        return {}
    if resources is None:
        from ao_commons_kg.resources import load_resources
        resources = load_resources()
    if (held := already_held(ident, resources)) is not None:
        return {"held": True, "id": held.id, "title": held.title or ident.get("label", "")}
    if ident.get("kind") != "paper":
        return {}
    from ao_commons_kg.scholarly import arxiv, openalex
    found: dict = {}
    if ident.get("arxiv") and fetch_arxiv is not None:
        try:
            preprint = arxiv.resolve(ident["arxiv"], fetch_arxiv)
            found = {"title": preprint.title, "abstract": preprint.abstract}
        except Exception:                           # noqa: BLE001
            pass
    if not found.get("abstract") and fetch_openalex is not None:
        try:
            work = openalex.resolve_work(ident.get("doi") or ident.get("arxiv"), fetch_openalex)
            found = {"title": found.get("title") or work.title, "abstract": work.abstract,
                     "date": work.publication_date or ""}
        except Exception:                           # noqa: BLE001
            pass
    return {k: v for k, v in found.items() if v}


def metadata_from_body(body: str, issue_title: str = "", found: dict | None = None) -> dict:
    """What the issue form gives us, and what the lookup found, as the judge's metadata.

    The proposer's case for inclusion always goes in: the judge is asked whether
    this belongs, and the person proposing it has answered that in their own
    words. For a paper, its own title and abstract go in ahead of it, so a link
    with one word of reason is judged as the paper it is.
    """
    found = found or {}
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
    case = why or "(the proposer gave no reason)"
    return {
        "title": (found.get("title") or issue_title or get("title or name", "title")
                  or get("link", "identifier") or "(unknown)"),
        "venue": kind,
        "date": found.get("date", ""),
        "abstract": (f"{found['abstract']}\n\nThe proposer's case for including it: {case}"
                     if found.get("abstract") else case),
    }


def judge_body(body: str, *, judge=None, issue_title: str = "", found: dict | None = None) -> ScopeVerdict:
    candidate = Candidate(key="suggestion", cited_by=())
    judge = judge or anthropic_judge()
    return judge(candidate, metadata_from_body(body, issue_title, found))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--body-file", required=True)
    parser.add_argument("--out", default="")
    parser.add_argument("--title", default="", help="the issue's own title")
    parser.add_argument("--offline", action="store_true", help="skip the corpus check and the lookups")
    args = parser.parse_args(argv)

    body = pathlib.Path(args.body_file).read_text(encoding="utf-8")
    write = lambda payload: args.out and pathlib.Path(args.out).write_text(json.dumps(payload, indent=1), encoding="utf-8")

    found: dict = {}
    if not args.offline:
        from ao_commons_kg.scholarly import arxiv, openalex
        try:
            found = look_up(body, fetch_openalex=openalex.http_fetcher(), fetch_arxiv=arxiv.http_fetcher())
        except Exception as error:                  # noqa: BLE001
            print(f"lookup skipped ({type(error).__name__}: {error})", file=sys.stderr)
    if found.get("held"):
        write({"admit": False, "judged": False, "held": True, "id": found["id"], "title": found["title"],
               "reasoning": f"already in the library as {found['id']}"})
        print(f"already held: {found['id']}")
        return 4

    try:
        verdict = judge_body(body, issue_title=args.title, found=found)
    except Exception as error:                      # noqa: BLE001
        payload = {"admit": False, "judged": False,
                   "reasoning": f"could not run the scope scan "
                                f"({type(error).__name__}: {error})"}
        write(payload)
        print(payload["reasoning"], file=sys.stderr)
        return 3

    payload = {"admit": verdict.admit, "judged": True,
               "borrowed_background": verdict.borrowed_background,
               "judged_by": verdict.judged_by, "reasoning": verdict.reasoning,
               "title": found.get("title", "")}   # what it is, so a refused issue can be named after it
    write(payload)
    print(verdict.reasoning)
    return 0 if verdict.admit else 2


if __name__ == "__main__":
    sys.exit(main())
