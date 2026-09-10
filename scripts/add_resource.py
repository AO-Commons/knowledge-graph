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
from ao_commons_kg.scholarly.store import ReferenceStore  # noqa: E402
from ao_commons_kg.taxonomy import load_taxonomy  # noqa: E402

RESOURCES = REPO / "data" / "resources"
TAXONOMY = REPO / "taxonomy" / "agentic-org-research-library-taxonomy-v3.md"


class ProposalError(ValueError):
    """The proposal cannot be added, with a reason the contributor can act on."""


class RateLimited(ProposalError):
    """Every source refused to answer, at least one of them because we asked
    too fast.

    Distinct from "no source has this paper", which is what the contributor
    used to be told. The two look identical at the point of failure and call
    for opposite responses: a rate limit means wait and re-run, a genuine
    miss means add it by hand with a title. Telling someone to hand-type a
    title for a paper the resolver could have filled in perfectly is how a
    guess gets into the corpus dressed as a fact.

    Nine of twenty-nine identifiers in the first bulk run hit this, including
    Generative Agents and Open Problems in Cooperative AI — both plainly in
    all three indexes.
    """


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


def likely_same_work(payload: dict, resources: list) -> list[tuple[object, str]]:
    """Records that look like the same paper under a different identifier.

    `already_held` compares canonical keys, and a preprint and its published
    version have different DOIs by construction — so it cannot see the case
    that actually happens. Both duplicates found in the first outside
    contribution were this shape:

        EPIC 10.1111/epic.70009   vs  SSRN 10.2139/ssrn.5516298
        Nature 10.1038/s41586-…   vs  arXiv 2504.21848

    The second defeats a title check too: "Characterizing AI Agents for
    Alignment and Governance" was published as "Agentic profiles for
    effective AI governance". What survives retitling is the byline.

    So: the same author set, or a title that barely changed. Reported for a
    person to confirm rather than refused — two papers by the same pair in
    the same year is normal, and blocking on it would make the common case
    pay for the rare one. A sweep over the whole corpus on this signal found
    exactly the one real pair and no false admissions.
    """
    import difflib

    from ao_commons_kg.people import fold

    incoming = {fold(a) for a in payload.get("authors") or []}
    title = re.sub(r"[^a-z0-9 ]", "", (payload.get("title") or "").lower()).strip()
    hits: list[tuple[object, str]] = []

    for resource in resources:
        if resource.id == payload.get("id"):
            continue
        held_authors = {fold(a) for a in (resource.authors or [])}
        held_title = re.sub(r"[^a-z0-9 ]", "", (resource.title or "").lower()).strip()

        if title and held_title:
            ratio = difflib.SequenceMatcher(None, title, held_title).ratio()
            if ratio > 0.9:
                hits.append((resource, f"near-identical title ({ratio:.0%})"))
                continue

        if incoming and held_authors:
            shared = incoming & held_authors
            overlap = len(shared) / len(incoming | held_authors)
            # Two or more shared names and near-identical author sets. One
            # shared name is a co-author, not a duplicate.
            #
            # And the pair must straddle preprint and published. That is what
            # the preprint/version-of-record shape *is*, and it is what
            # separates it from the far more common case of one research
            # group publishing several papers together — which flagged five
            # of eighty-seven records before this condition, every one of
            # them a false positive. Companion preprints posted the same day
            # share a byline and a type; a preprint and its published
            # version share a byline and differ in type.
            straddles = _is_preprint(payload.get("resource_type")) != _is_preprint(
                resource.resource_type)
            if overlap >= 0.8 and len(shared) >= 2 and straddles:
                hits.append((resource, f"same byline across preprint and published "
                                       f"({len(shared)} authors, {overlap:.0%} overlap)"))
    return hits


def _is_preprint(resource_type) -> bool:
    value = getattr(resource_type, "value", resource_type)
    return str(value or "") == "preprint"


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
    """Resolve a paper and build its record. Also returns what could not be filled.

    The payload carries a `_references` key that is not part of the record:
    the caller writes it to the reference store and pops it before the YAML
    is saved. Reference lists are large and machine-generated, and inlining
    a hundred identifiers into a file a person is expected to correct by
    hand would be a poor trade — the store exists for exactly that reason.
    """
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
    #
    # Asked even when we already have an abstract, which is a change: it is
    # also the only source of reference lists for preprints, and OpenAlex
    # carries none for them. Skipping it when the abstract happened to
    # arrive was how every preprint entered the corpus with no citations.
    references: list[str] = list(work.referenced_works) if work else []
    citation_count = work.cited_by_count if work else 0
    if fetch_s2 is not None:
        try:
            paper = semanticscholar.resolve_paper(identifier, fetch_s2)
            abstract = abstract or paper.abstract
            authors = authors or list(paper.authors)
            references = references or list(paper.referenced_keys)
            citation_count = max(citation_count, paper.citation_count)
        except semanticscholar.SemanticScholarError as error:
            if not abstract:
                gaps.append(f"no abstract from Semantic Scholar either ({error})")
            else:
                gaps.append(f"no reference list from Semantic Scholar ({error})")

    if not abstract:
        gaps.append("no abstract, so the topic matcher has only the title to work from")

    # arXiv last, and decisive. It has recent preprints the indexes have not
    # caught up with, and for a preprint its byline is the submission itself
    # rather than a machine's guess at who the authors are.
    preprint = None
    if ident.get("arxiv") and fetch_arxiv is not None:
        try:
            preprint = arxiv.resolve(ident["arxiv"], fetch_arxiv)
        except arxiv.ArxivTransportError as error:
            # A third source must never *block* an add. It is still allowed
            # to say it was never reached — this is the decisive source for
            # a preprint byline, and a record whose provenance claims
            # otherwise is lying about how it was made.
            preprint = None
            gaps.append(
                f"arXiv was unreachable ({error}), so the byline is whichever "
                "index answered rather than the submission itself")
        except Exception as error:  # noqa: BLE001
            preprint = None
            gaps.append(f"arXiv had nothing usable for this id ({error})")

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
        # The diagnosis already exists — openalex raises a distinct message
        # for 429 and it is sitting in `gaps`. It used to be discarded one
        # line before it would have been printed.
        throttled = [g for g in gaps if "rate-limit" in g.lower() or "429" in g]
        if throttled:
            raise RateLimited(
                "Rate-limited, not missing. " + " ".join(throttled)
                + " Re-run with a longer --pause; the record is almost certainly "
                "resolvable. Do not add it by hand with a typed title."
            )
        raise ProposalError(
            "No title. None of OpenAlex, Semantic Scholar or arXiv has this "
            "identifier, and the issue does not give a title, so there is nothing "
            "to file it under. Add a Title and this runs again."
            + (f" What the sources said: {' '.join(gaps)}" if gaps else "")
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
        "_references": {"keys": sorted(set(references)),
                        "cited_by_count": citation_count,
                        "source": "openalex" if (work and work.referenced_works)
                                  else ("semanticscholar" if references else "none")},
    }
    if not references:
        gaps.append(
            "no reference list, so this record joins the citation graph with no "
            "outgoing edges and cannot contribute to expansion until resolved")
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
    """Say where the record came from and how far to trust each part of it.

    `issue=0` means the bulk path, which has no issue behind it. It used to
    render as "from issue #0", and there is no issue #0 — every record added
    by a reading list said so. `source_provenance` is the field that
    separates a claim somebody checked from one a crawler proposed; it must
    not contain a fiction.
    """
    where = (f"added from a reading list by @{author}, in a batch"
             if not issue
             else f"added automatically from issue #{issue} by @{author}")
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


REFERENCES = REPO / "data" / "scholarly" / "references.jsonl"


def write_references(payload: dict) -> int:
    """Persist a new record's reference list, if it came with one.

    Split out from `write_record` because the two write to different places
    and either can be useful alone. Called by every path that adds a paper —
    the site's Add tab and the bulk reading-list path both — so that a record
    never enters the corpus as a citation isolate. It used to: `paper_record`
    fetched the reference list from OpenAlex and discarded it, and every
    paper added since August joined the graph with no citation edges at all.
    """
    details = payload.get("_references") or {}
    keys = details.get("keys") or []
    if not keys:
        return 0
    store = ReferenceStore.load(REFERENCES)
    store.put(payload["id"],
              key=canonical_key({"doi": payload.get("doi"),
                                 "arxiv": payload.get("arxiv_id")}),
              source=details.get("source", "unknown"),
              referenced_keys=keys,
              cited_by_count=details.get("cited_by_count", 0))
    store.save()
    return len(keys)


def write_record(payload: dict) -> Path:
    """Write the record, having first made the model accept it."""
    # Not part of the record. It goes to the reference store, and leaving it
    # in the payload would both break the model and inline a hundred
    # identifiers into a file a person is meant to hand-correct.
    payload = {k: v for k, v in payload.items() if k != "_references"}
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
        # Onto the summary, which is what gets posted back on the issue.
        # `gaps` belongs to paper_record and is long gone by here.
        if twins := likely_same_work(payload, resources):
            lines = "\n".join(
                f"- **{twin.id}** — {why}\n  _{(twin.title or '')[:70]}_"
                for twin, why in twins)
            summary += (
                "\n\n**This may already be in the library.**\n\n" + lines +
                "\n\nA preprint and its published version have different DOIs, so "
                "the duplicate check cannot see it. The record was still added — "
                "if it is the same work, revert this commit and keep the one "
                "already held.")
        stored = write_references(payload)
        print(f"wrote {write_record(payload).relative_to(REPO)}")
        if stored:
            print(f"  {stored} references stored — it joins the citation graph")
    if args.summary_file:
        Path(args.summary_file).write_text(summary, encoding="utf-8")
    print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
