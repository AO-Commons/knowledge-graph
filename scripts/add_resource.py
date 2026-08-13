#!/usr/bin/env python3
"""Turn a new-resource issue into a record in the corpus.

    site  →  prefilled issue  →  this script  →  the corpus

Run by `.github/workflows/new-resource.yml` on a labelled issue.

This lands without a human in the loop, where a filing and a taxonomy change
do not, and the difference is blast radius rather than trust. A new record is
one file that changes no existing judgement and no measured number; it arrives
`unreviewed`, which every consumer already filters on, and reverting it is one
commit. A taxonomy change moves the branches everything else is filed under,
so that path stays manual on purpose.

What is automated here is the clerical work — resolving an identifier to
metadata, spelling the authors the way the corpus already spells them, giving
the record an id and a home. The judgement is not automated: whether the paper
belongs is decided later, by the same review the rest of the corpus goes
through. The script refuses malformed input; it does not pretend to referee.

Usage:
    python3 scripts/add_resource.py --body-file issue.md --author name --issue 12
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from ao_commons_kg.models import Resource  # noqa: E402
from ao_commons_kg.people import apply_index, build_index, same_person  # noqa: E402
from ao_commons_kg.resources import load_resources  # noqa: E402
from ao_commons_kg.scholarly import arxiv, openalex, semanticscholar  # noqa: E402
from ao_commons_kg.scholarly.keys import canonical_key, key_for_resource  # noqa: E402
from ao_commons_kg.taxonomy import load_taxonomy  # noqa: E402

RESOURCES = REPO / "data" / "resources"
TAXONOMY = REPO / "taxonomy" / "agentic-org-research-library-taxonomy-v3.md"


class ProposalError(ValueError):
    """The proposal cannot be added, with a reason the contributor can act on."""


# ---- reading the issue -----------------------------------------------------
#
# The same question reaches this script under three different names: the issue
# form's label, the site's paper body, and the site's tool body. They are the
# same question, so they collapse to one key here rather than becoming three
# branches everywhere downstream.

HEADING = re.compile(r"^\s{0,3}#{2,4}\s+(.+?)\s*$")
LABELLED = re.compile(r"^\s*\*\*(.+?):\*\*\s*(.*)$")
SECTION = re.compile(r"^\s*\*\*(.+?)\*\*\s*$")

FIELDS = {
    "doi arxiv id or link": "identifier",
    "identifier": "identifier",
    "link": "identifier",
    "title": "title",
    "name": "name",
    "topics": "topics",
    "topics if you already know them": "topics",
    "topics the contributor confirmed": "topics",
    "why does it belong": "why",
    "notes": "why",
    "anything a reviewer should know": "why",
    "what does it do": "summary",
    "what it does": "summary",
    "how do agents participate": "agents",
    "how agents participate": "agents",
    "what oversight does it ship with": "controls",
    "oversight it ships": "controls",
    "who maintains it": "maintainer",
    "maintainer": "maintainer",
    "license and source": "license",
    "license": "license",
}

# What people and forms write when they mean "nothing here". GitHub's own
# `_No response_` is the common one and would otherwise become a title.
BLANK = {"", "—", "-", "–", "_no response_", "no response", "none", "n/a", "na", "tbd"}


def _key(label: str) -> str | None:
    plain = re.sub(r"[^a-z0-9 ]", " ", label.lower())
    return FIELDS.get(" ".join(plain.split()))


def read_issue(body: str) -> dict[str, str]:
    """Read the fields out of an issue body, whatever shape it arrived in.

    A labelled line carries its own value and closes. A bare heading opens a
    block that runs to the next label. An unrecognized label closes the block
    rather than swallowing the text under it, so a section this script does
    not know about cannot end up appended to the previous answer.
    """
    collected: dict[str, list[str]] = {}
    current: str | None = None

    for line in (body or "").splitlines():
        if match := LABELLED.match(line):
            current = None
            if key := _key(match.group(1)):
                collected.setdefault(key, []).append(match.group(2).strip())
            continue
        if match := SECTION.match(line) or HEADING.match(line):
            current = _key(match.group(1))
            continue
        if current:
            collected.setdefault(current, []).append(line)

    fields = {}
    for key, lines in collected.items():
        value = "\n".join(lines).strip()
        if value.lower() not in BLANK:
            fields[key] = value
    return fields


# ---- what was pasted -------------------------------------------------------

DOI = re.compile(r"^10\.\d{4,9}/\S+$")
ARXIV = re.compile(r"^\d{4}\.\d{4,5}(v\d+)?$")


def identify(raw: str) -> dict:
    """Work out what the identifier is: a paper to resolve, or a thing to describe.

    Mirrors the site's reader so a contributor sees the same verdict twice —
    the page tells them it is new, and this agrees.
    """
    value = re.sub(r"^https?://(dx\.)?doi\.org/", "", (raw or "").strip(), flags=re.I)
    if not value:
        raise ProposalError("No identifier. Give a DOI, an arXiv id, or a link.")

    if found := re.search(r"arxiv\.org/(?:abs|pdf|html)/(\d{4}\.\d{4,5})", value, re.I):
        return {"kind": "paper", "arxiv": found.group(1).lower(), "label": found.group(1)}
    if ARXIV.match(value):
        return {"kind": "paper", "arxiv": value.split("v")[0].lower(), "label": value}
    if DOI.match(value):
        return {"kind": "paper", "doi": value.lower(), "label": value}
    if found := re.search(r"(10\.\d{4,9}/\S+)", value):
        return {"kind": "paper", "doi": found.group(1).lower(), "label": found.group(1)}
    if re.match(r"^(https?://|www\.)", value, re.I) or re.match(r"^[\w-]+\.[\w.-]+", value):
        url = value if value.lower().startswith("http") else f"https://{value}"
        return {"kind": "thing", "url": url, "label": value}

    raise ProposalError(
        f"{value!r} is not a DOI, an arXiv id, or a link. Paste one of those — "
        "or the address of the tool's site if it has no paper."
    )


def already_held(ident: dict, resources: list) -> object | None:
    """The record this proposal duplicates, if the corpus already has it.

    Identity goes through the same canonical key the graph uses, so pasting a
    preprint's `10.48550/arXiv.…` DOI finds the record filed under its arXiv
    id. Comparing the raw strings would miss it and add the paper twice.
    """
    if key := canonical_key({"doi": ident.get("doi"), "arxiv": ident.get("arxiv")}):
        for resource in resources:
            if key_for_resource(resource) == key:
                return resource

    url = (ident.get("url") or "").rstrip("/").lower()
    if url:
        for resource in resources:
            known = {(resource.url or "").rstrip("/").lower(),
                     (resource.repository_url or "").rstrip("/").lower()}
            if url in known - {""}:
                return resource
    return None


def read_topics(raw: str, known: set[str]) -> list[str]:
    """The contributor's own codes, checked against the taxonomy.

    Refused rather than dropped when one is wrong. A code that does not exist
    is usually a typo for one that does, and silently discarding it would lose
    a judgement the contributor thought they had recorded.
    """
    codes = [c.strip() for c in re.split(r"[,;\s]+", raw or "") if c.strip()]
    if unknown := [c for c in codes if c not in known]:
        raise ProposalError(
            f"not taxonomy codes: {', '.join(unknown)}. Fix them in the issue "
            "body and this runs again on its own."
        )
    return sorted(set(codes), key=lambda code: [int(part) for part in code.split(".")])


# ---- building the record ---------------------------------------------------

TYPES = {
    "preprint": "preprint",
    "article": "peer-reviewed-paper",
    "review": "peer-reviewed-paper",
    "book-chapter": "peer-reviewed-paper",
    "report": "technical-report",
    "dataset": "dataset",
    "standard": "standard-specification",
}


def _slug(text: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", text.lower())).strip("-")


def path_for(resource_id: str) -> Path:
    return RESOURCES / (resource_id.removeprefix("resource:").replace(":", "-") + ".yml")


def paper_record(ident: dict, fields: dict, *, topics: list[str], author: str, issue: int,
                 fetch_openalex=None, fetch_s2=None, fetch_arxiv=None,
                 known_names=None) -> tuple[dict, list[str]]:
    """Resolve a paper and build its record. Also returns what could not be filled."""
    work = None
    gaps: list[str] = []
    identifier = ident.get("doi") or ident.get("arxiv")

    if fetch_openalex is not None:
        try:
            work = openalex.resolve_work(identifier, fetch_openalex)
        except openalex.OpenAlexError as error:
            gaps.append(f"OpenAlex could not resolve it ({error})")

    title = (work.title if work else "") or fields.get("title") or ""
    abstract = work.abstract if work else None
    authors = list(work.authors) if work else []
    # Semantic Scholar carries abstracts for preprints that OpenAlex does not,
    # which is the gap that kept most arXiv records text-free.
    if fetch_s2 is not None and not abstract:
        try:
            paper = semanticscholar.resolve_paper(identifier, fetch_s2)
            abstract = paper.abstract
            authors = authors or list(paper.authors)
        except semanticscholar.SemanticScholarError as error:
            gaps.append(f"no abstract from Semantic Scholar either ({error})")

    if not abstract:
        gaps.append("no abstract, so the topic matcher has only the title to work from")

    # arXiv last, and decisive. It has recent preprints the indexes have not
    # caught up with, and for a preprint its byline is the submission itself
    # rather than a machine's guess at who the authors are.
    preprint = None
    if ident.get("arxiv") and fetch_arxiv is not None:
        try:
            preprint = arxiv.resolve(ident["arxiv"], fetch_arxiv)
        except Exception:  # noqa: BLE001 — a third source must never block an add
            preprint = None

    if preprint:
        if preprint.authors:
            wrong = [a for a in authors if not any(same_person(a, o) for o in preprint.authors)]
            if wrong:
                gaps.append(
                    "OpenAlex credited "
                    + ", ".join(repr(name) for name in wrong)
                    + ", who arXiv does not list as an author — arXiv's byline was used"
                )
            authors = preprint.authors
        if not title:
            title = preprint.title
        if not abstract:
            abstract = preprint.abstract
            gaps = [g for g in gaps if "no abstract" not in g]

    # Checked only once every source has been asked. Moving this earlier let a
    # paper through with an empty title whenever OpenAlex missed it and arXiv
    # was unreachable — a record filed under nothing at all.
    if not title:
        raise ProposalError(
            "No title. None of OpenAlex, Semantic Scholar or arXiv has this "
            "identifier, and the issue does not give a title, so there is nothing "
            "to file it under. Add a Title and this runs again."
        )

    kind = "preprint" if ident.get("arxiv") else TYPES.get(work.type if work else "", "peer-reviewed-paper")
    if ident.get("arxiv"):
        resource_id = f"resource:arxiv:{ident['arxiv']}"
        url = f"https://arxiv.org/abs/{ident['arxiv']}"
        doi = f"10.48550/arXiv.{ident['arxiv']}"
    else:
        resource_id = f"resource:doi:{_slug(ident['doi'])}"
        url = f"https://doi.org/{ident['doi']}"
        doi = ident["doi"]

    payload = {
        "id": resource_id,
        "resource_type": kind,
        "title": title,
        "abstract": abstract,
        # The corpus is the authority on how a person's name is spelled, so a
        # freshly fetched byline is folded onto the spellings already held
        # rather than introducing a second one.
        "authors": apply_index(authors, known_names or {}),
        "organizations": list(work.institutions) if work else [],
        "published_at": (work.publication_date if work else None) or None,
        "url": url,
        "doi": doi,
        "arxiv_id": ident.get("arxiv"),
        "openalex_id": openalex.short_id(work.openalex_id) if work else None,
        "is_open_access": work.is_open_access if work else None,
        "is_retracted": work.is_retracted if work else None,
        "taxonomy_topics": topics,
        "facets": {"artifact_type": kind},
        "review_status": "unreviewed",
        "source_provenance": provenance(author, issue, resolved=work is not None, topics=topics),
        "ingested_at": date.today().isoformat(),
    }
    return payload, gaps


def thing_record(ident: dict, fields: dict, *, topics: list[str], author: str,
                 issue: int) -> tuple[dict, list[str]]:
    """Build the record for something with no scholarly identity: a tool, a platform."""
    name = fields.get("name") or fields.get("title") or ""
    if not name:
        raise ProposalError(
            "No name. A link with no paper behind it has to be described by hand — "
            "the site's Add tab asks for the name, what it does, how agents "
            "participate, and what oversight it ships."
        )
    if not fields.get("summary"):
        raise ProposalError(
            f"No description of what {name} does. A one-line entry is not worth "
            "the row; say what it does in a sentence or two."
        )

    gaps = [
        label for key, label in (
            ("agents", "how agents participate is blank — the field this collection exists to answer"),
            ("controls", "what oversight it ships is blank"),
            ("maintainer", "no maintainer named"),
        ) if not fields.get(key)
    ]

    url = ident["url"]
    repository = url if "github.com" in url or "gitlab.com" in url else None
    license_field = fields.get("license") or ""
    # Tri-state on purpose: an unresearched tool must never be recorded as
    # proprietary just because nobody filled the box in.
    open_source = "yes" if license_field else "unknown"

    profile = {
        "agent_model": fields.get("agents"),
        "human_controls": fields.get("controls"),
        "maintainer": fields.get("maintainer"),
        "open_source": open_source,
    }

    payload = {
        "id": f"resource:tool:{_slug(name)}",
        "resource_type": "code-tool",
        "title": name,
        "description": fields.get("summary"),
        "url": url,
        "repository_url": repository,
        "license": license_field.split("·")[0].strip() or None,
        "taxonomy_topics": topics,
        "facets": {"artifact_type": "code-tool"},
        "tool": {k: v for k, v in profile.items() if v},
        "review_status": "unreviewed",
        "source_provenance": provenance(author, issue, resolved=False, topics=topics, described=True),
        "ingested_at": date.today().isoformat(),
    }
    return payload, gaps


def provenance(author: str, issue: int, *, resolved: bool, topics: list[str],
               described: bool = False) -> str:
    """Say where the record came from and how far to trust each part of it."""
    where = f"added automatically from issue #{issue} by @{author}"
    how = (
        "described by the contributor and not verified against vendor documentation"
        if described
        else "identity and byline resolved against OpenAlex"
        if resolved
        else "not resolvable against OpenAlex, so title and date are as given"
    )
    tags = (
        "topic tags are the contributor's own, confirmed but unreviewed"
        if topics
        else "no topic tags yet — it enters the review queue untagged"
    )
    return f"{where}; {how}. {tags}."


def write_record(payload: dict) -> Path:
    """Write the record, having first made the model accept it."""
    payload = {k: v for k, v in payload.items() if v not in (None, [], {}, "")}
    # Constructed before writing so a record the model rejects fails here,
    # loudly, rather than at release time in someone else's build.
    Resource(**payload)

    path = path_for(payload["id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True, width=88),
        encoding="utf-8",
    )
    return path


# ---- the whole job ---------------------------------------------------------

def process(body: str, *, author: str, issue: int, resources: list, known_topics: set[str],
            fetch_openalex=None, fetch_s2=None, fetch_arxiv=None) -> tuple[str, dict | None]:
    """Read an issue and produce the record it asks for.

    Returns the summary to post and the record written, if any. A duplicate is
    an ordinary outcome rather than an error: the same paper reaches this from
    two people often enough that failing on it would train them to ignore the
    bot.
    """
    fields = read_issue(body)
    if not fields.get("identifier") and not fields.get("name"):
        raise ProposalError(
            "Nothing to add. The issue needs a DOI, an arXiv id, or a link — the "
            "site's Add tab fills that in for you."
        )

    ident = identify(fields.get("identifier", ""))
    if held := already_held(ident, resources):
        return (
            f"**Already in the library.** `{ident['label']}` is "
            f"[{held.title}](https://ao-commons.github.io/knowledge-graph/) — "
            f"record `{held.id}`.\n\nNothing was added. If you meant to file topics "
            "against it, the Review tab on the site has it waiting.",
            None,
        )

    topics = read_topics(fields.get("topics", ""), known_topics)
    known_names = build_index([a for r in resources for a in (r.authors or [])])

    if ident["kind"] == "paper":
        payload, gaps = paper_record(
            ident, fields, topics=topics, author=author, issue=issue,
            fetch_openalex=fetch_openalex, fetch_s2=fetch_s2, fetch_arxiv=fetch_arxiv,
            known_names=known_names,
        )
    else:
        payload, gaps = thing_record(ident, fields, topics=topics, author=author, issue=issue)

    if any(r.id == payload["id"] for r in resources):
        return (
            f"**Already in the library.** `{payload['id']}` exists. Nothing was added.",
            None,
        )

    return summarize(payload, gaps, fields, author), payload


def summarize(payload: dict, gaps: list[str], fields: dict, author: str) -> str:
    """What the bot did, in terms the contributor can check."""
    lines = [
        f"Added **{payload['title']}** — thank you, @{author}.",
        "",
        f"- `{payload['id']}`",
        f"- filed as {payload['resource_type']}",
        f"- topics: {', '.join(payload['taxonomy_topics']) or 'none yet — it joins the review queue untagged'}",
    ]
    if payload.get("authors"):
        shown = ", ".join(payload["authors"][:4])
        more = len(payload["authors"]) - 4
        lines.append(f"- authors: {shown}{f' and {more} more' if more > 0 else ''}")
    if payload.get("published_at"):
        lines.append(f"- published {payload['published_at']}")

    if gaps:
        lines += ["", "Worth knowing:", ""] + [f"- {gap}" for gap in gaps]

    if why := fields.get("why"):
        lines += ["", "### Why the contributor says it belongs", "", why]

    lines += [
        "",
        "It is `unreviewed`, like everything else that has not been through the "
        "review queue, and it appears on the site at the next build. Nothing about "
        "it is settled — the tags above are a starting point for whoever files it.",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--body-file", required=True)
    parser.add_argument("--author", default="a contributor")
    parser.add_argument("--issue", type=int, default=0)
    parser.add_argument("--summary-file", default="")
    parser.add_argument("--offline", action="store_true",
                        help="skip the metadata lookups; for testing the parse")
    args = parser.parse_args(argv)

    resources = load_resources()
    known_topics = {t.code for t in load_taxonomy(TAXONOMY)}

    try:
        summary, payload = process(
            Path(args.body_file).read_text(encoding="utf-8"),
            author=args.author, issue=args.issue,
            resources=resources, known_topics=known_topics,
            fetch_openalex=None if args.offline else openalex.http_fetcher(),
            fetch_s2=None if args.offline else semanticscholar.http_fetcher(),
            fetch_arxiv=None if args.offline else arxiv.http_fetcher(),
        )
    except ProposalError as error:
        message = f"This could not be added.\n\n{error}"
        if args.summary_file:
            Path(args.summary_file).write_text(message, encoding="utf-8")
        print(message, file=sys.stderr)
        return 1

    if payload is not None:
        print(f"wrote {write_record(payload).relative_to(REPO)}")
    if args.summary_file:
        Path(args.summary_file).write_text(summary, encoding="utf-8")
    print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
