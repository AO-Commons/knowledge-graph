#!/usr/bin/env python3
"""Add many resources at once, from a list of identifiers.

    python3 scripts/bulk_add.py papers.txt          # what it would do
    python3 scripts/bulk_add.py papers.txt --write  # write the records

Built for an agent working through a reading list: paste the identifiers into
a file, run this, open a pull request. See docs/bulk-add.md, which is written
for that agent to follow.

Every identifier goes through the same resolution and the same duplicate check
as a single addition through the site — this is the one-at-a-time path in a
loop, not a second implementation of it. That matters because a bulk path with
looser rules is how a corpus fills up with near-duplicates that nobody
notices.

Duplicates keep the original, in both directions: an identifier already in the
corpus is skipped, and a repeat inside the file itself keeps its first
appearance. Both are reported rather than passed over in silence, because a
list that turns out to be half duplicates is worth knowing about.
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

from add_resource import (  # noqa: E402
    ProposalError,
    already_held,
    identify,
    paper_record,
    read_topics,
    thing_record,
    write_record,
)
from ao_commons_kg.people import build_index  # noqa: E402
from ao_commons_kg.resources import load_resources  # noqa: E402
from ao_commons_kg.scholarly.keys import canonical_key  # noqa: E402
from ao_commons_kg.scholarly import arxiv, openalex, semanticscholar  # noqa: E402
from ao_commons_kg.taxonomy import load_taxonomy  # noqa: E402

TAXONOMY = REPO / "taxonomy" / "agentic-org-research-library-taxonomy-v3.md"

# A line may be a bare identifier, a markdown bullet, or a citation with the
# link buried in it. Being fussy here would send an agent to reformat a list
# that was perfectly readable.
_COMMENT = re.compile(r"^\s*(#|//)")
_TOPICS = re.compile(r"\[([0-9.,\s]+)\]\s*$")
_DOI = re.compile(r"^10\.\d{4,9}/\S+$")
_ARXIV = re.compile(r"^\d{4}\.\d{4,5}(v\d+)?$")


def read_list(text: str) -> list[tuple[str, str]]:
    """Identifiers, with optional trailing topic codes in square brackets."""
    found: list[tuple[str, str]] = []
    for line in text.split("\n"):
        line = line.strip()
        if not line or _COMMENT.match(line):
            continue
        line = re.sub(r"^[-*+]\s+", "", line)          # markdown bullet
        line = re.sub(r"^\d+[.)]\s+", "", line)        # numbered list

        topics = ""
        if match := _TOPICS.search(line):
            topics = match.group(1)
            line = line[: match.start()].strip()

        # The identifier is the first token that looks like one, in order of
        # how sure we can be. "Any token with a dot in it" was the first rule,
        # and it read "al" out of "Hammond et al., ...".
        parts = [part.strip().rstrip(".,;") for part in line.split()]
        token = (
            next((p for p in parts if p.lower().startswith("http")), None)
            or next((p for p in parts if _DOI.match(p)), None)
            or next((p for p in parts if _ARXIV.match(p)), None)
            or next((p for p in parts if "/" in p), None)
            or line.strip().rstrip(".,;")
        )
        found.append((token, topics))
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("list", help="file of identifiers, one per line")
    parser.add_argument("--write", action="store_true", help="write the records")
    parser.add_argument("--author", default="a contributor")
    parser.add_argument("--offline", action="store_true", help="skip lookups; for testing the parse")
    parser.add_argument("--pause", type=float, default=1.0,
                        help="seconds between lookups; be kind to the free APIs")
    args = parser.parse_args(argv)

    entries = read_list(Path(args.list).read_text(encoding="utf-8"))
    if not entries:
        print("nothing to add — the file has no identifiers in it", file=sys.stderr)
        return 1

    resources = load_resources()
    known_topics = {t.code for t in load_taxonomy(TAXONOMY)}
    known_names = build_index([a for r in resources for a in (r.authors or [])])

    fetchers = {} if args.offline else {
        "fetch_openalex": openalex.http_fetcher(),
        "fetch_s2": semanticscholar.http_fetcher(),
        "fetch_arxiv": arxiv.http_fetcher(),
    }

    added, held, repeated, failed = [], [], [], []
    seen: dict[str, str] = {}          # canonical identity -> the line that claimed it
    written: list = list(resources)    # grows, so a batch cannot duplicate itself

    for position, (raw, topics) in enumerate(entries, start=1):
        try:
            ident = identify(raw)
        except ProposalError as error:
            failed.append((raw, str(error)))
            continue

        # Within the file: first appearance wins, as on the site — and through
        # the same canonical key the corpus check uses, or the two disagree.
        # They did: `10.48550/arXiv.2608.10218` and `2608.10218` are one paper,
        # which `already_held` knew and this did not.
        key = (canonical_key({"doi": ident.get("doi"), "arxiv": ident.get("arxiv")})
               or (ident.get("url") or raw).rstrip("/").lower())
        if key in seen:
            repeated.append((raw, seen[key]))
            continue
        seen[key] = raw

        # Against the corpus, including anything written earlier in this run.
        if existing := already_held(ident, written):
            held.append((raw, existing.id, existing.title))
            continue

        try:
            if ident["kind"] == "paper":
                payload, _ = paper_record(
                    ident, {}, topics=read_topics(topics, known_topics),
                    author=args.author, issue=0, known_names=known_names, **fetchers)
            else:
                payload, _ = thing_record(
                    ident, {"name": raw}, topics=read_topics(topics, known_topics),
                    author=args.author, issue=0)
        except ProposalError as error:
            failed.append((raw, str(error)))
            continue
        except Exception as error:  # noqa: BLE001 — one bad row must not end the run
            failed.append((raw, f"{type(error).__name__}: {error}"))
            continue

        added.append((raw, payload["id"], payload["title"]))
        if args.write:
            write_record(payload)
            written = load_resources()
        else:
            # Keep the in-memory corpus current so a dry run still detects a
            # duplicate that a later line in the same file would create.
            from ao_commons_kg.models import Resource
            written = written + [Resource(**{k: v for k, v in payload.items()
                                             if v not in (None, [], {}, "")})]

        if fetchers and position < len(entries):
            time.sleep(args.pause)

    print(f"read {len(entries)} identifier(s)\n")
    if added:
        print(f"{len(added)} to add:")
        for raw, rid, title in added:
            print(f"  + {title[:66]}\n      {rid}")
    if held:
        print(f"\n{len(held)} already in the library, kept as they are:")
        for raw, rid, title in held:
            print(f"  = {raw}\n      {rid} — {title[:56]}")
    if repeated:
        print(f"\n{len(repeated)} repeated inside the file, first one kept:")
        for raw, first in repeated:
            print(f"  = {raw}  (already listed as {first})")
    if failed:
        print(f"\n{len(failed)} could not be added:")
        for raw, why in failed:
            print(f"  ! {raw}\n      {why}")

    if not args.write:
        print("\nNothing written. Run again with --write to create the records.")
    else:
        print(f"\nWrote {len(added)} record(s) to data/resources/.")

    return 1 if failed and not added else 0


if __name__ == "__main__":
    sys.exit(main())
