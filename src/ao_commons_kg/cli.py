"""Command line entry points.

    aokg taxonomy --stats          parse the taxonomy and report what loaded
    aokg resolve                   fetch OpenAlex metadata for existing records
    aokg expand --limit 40         propose new records from the citation graph
    aokg build --version v0.1.0    write a release into data/releases/
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from .export import write_release
from .models import ConfidenceClass, Relationship, RelationType
import yaml

from .resources import ResourceError, load_resources, tagged_edges, unknown_tags
from .scholarly import ReferenceStore, expand_neighborhood, resolve_work, scope_score
from .scholarly.openalex import OpenAlexError, http_fetcher, short_id
from .taxonomy import TaxonomyError, load_taxonomy

REPO = Path(__file__).resolve().parent.parent.parent
DEFAULT_TAXONOMY = REPO / "taxonomy" / "agentic-org-research-library-taxonomy-v3.md"
OUT_RESOURCES = REPO / "data" / "resources"
DEFAULT_RELEASES = REPO / "data" / "releases"
REFERENCES = REPO / "data" / "scholarly" / "references.jsonl"
CANDIDATES = REPO / "data" / "candidates"


def _parent_edges(topics) -> list[Relationship]:
    """PARENT_OF edges are structural, so they're derived rather than stored."""
    codes = {topic.code for topic in topics}
    return [
        Relationship(f"topic:{t.parent_code}", t.id, RelationType.PARENT_OF)
        for t in topics
        if t.parent_code and t.parent_code in codes
    ]


def cmd_taxonomy(args) -> int:
    topics = load_taxonomy(args.path, strict=not args.lenient)
    by_depth = Counter(topic.depth for topic in topics)
    coding = sum(1 for t in topics if t.usage_mode.value == "coding_scheme")

    print(f"{len(topics)} topics from {Path(args.path).name}")
    print(f"  sections {by_depth[0]} · subsections {by_depth[1]} · leaves {by_depth[2]}")
    print(f"  coding-scheme topics (section 11): {coding}")
    print(f"  unnumbered subpoints carried: {sum(len(t.subpoints) for t in topics)}")

    if args.stats:
        print("\n  per section:")
        counts = Counter(topic.top_level_section for topic in topics)
        titles = {t.code: t.title for t in topics if t.depth == 0}
        for section in sorted(counts, key=int):
            print(f"    {section:>2}  {counts[section]:>3}  {titles.get(section, '?')}")
        # Deliberately no "research gap" marker here. A thin *literature* is
        # not a small branch of the tree — section 6 is among the largest and
        # has almost nothing written about it. Coverage is a property of
        # resources per topic, so that signal belongs with the corpus.
    return 0


def _citation_edges(resources) -> list[Relationship]:
    """CITES edges for pairs where both ends are in the corpus.

    Deterministic — read from scholarly metadata, so no confidence class.
    Restricted to the corpus because a reference to a paper we do not hold is
    a dangling edge that inflates the export without answering a question.
    """
    store = ReferenceStore.load(REFERENCES)
    by_openalex = {
        r.openalex_id: r.id for r in resources if r.openalex_id
    }
    return [
        Relationship(by_openalex[source], by_openalex[target], RelationType.CITES)
        for source, target in store.citation_pairs(set(by_openalex))
    ]


def cmd_resolve(args) -> int:
    """Fill in metadata OpenAlex has and our records lack.

    Idempotent, and it never overwrites a curated value — a hand-written
    summary is worth more than a machine abstract, and losing one to a
    refresh would make the whole command untrustworthy.
    """
    fetch = http_fetcher()
    store = ReferenceStore.load(REFERENCES)
    resources = load_resources()
    filled = skipped = failed = 0

    for resource in resources:
        identifier = resource.openalex_id or resource.doi or resource.arxiv_id
        if not identifier:
            skipped += 1
            continue
        if resource.openalex_id and resource.openalex_id in store.entries and not args.refresh:
            skipped += 1
            continue
        try:
            work = resolve_work(identifier, fetch)
        except OpenAlexError as error:
            print(f"  {resource.id}: {error}", file=sys.stderr)
            failed += 1
            continue

        store.put(work, resource_id=resource.id)
        path = OUT_RESOURCES / (resource.id.removeprefix("resource:").replace(":", "-") + ".yml")
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        for key, value in (
            ("openalex_id", work.openalex_id),
            ("abstract", work.abstract),
            ("authors", work.authors),
            ("organizations", work.institutions),
            ("is_open_access", work.is_open_access),
            ("is_retracted", work.is_retracted),
        ):
            if value not in (None, [], "") and not payload.get(key):
                payload[key] = value
        path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True, width=88),
                        encoding="utf-8")
        filled += 1
        print(f"  {resource.id}: {len(work.referenced_works)} references, "
              f"{work.cited_by_count} citations")

    store.save()
    print(f"\n{filled} resolved, {skipped} skipped, {failed} failed. "
          f"{len(store.entries)} reference list(s) stored.")
    return 0


def cmd_expand(args) -> int:
    """Walk one hop out from the corpus and write a review queue."""
    fetch = http_fetcher()
    resources = load_resources()
    known = {r.openalex_id for r in resources if r.openalex_id}

    seeds = args.seed or [r.openalex_id for r in resources if r.openalex_id]
    if not seeds:
        print("no seeds with an OpenAlex id — run `aokg resolve` first.", file=sys.stderr)
        return 1
    seeds = seeds[: args.max_seeds]
    print(f"expanding from {len(seeds)} seed(s), {len(known)} already known")

    candidates, resolved = expand_neighborhood(
        seeds, fetch, known=known, min_score=args.min_score,
        per_seed=args.per_seed, on_progress=print,
    )

    store = ReferenceStore.load(REFERENCES)
    for work in resolved.values():
        store.put(work)
    store.save()

    candidates = candidates[: args.limit]
    CANDIDATES.mkdir(parents=True, exist_ok=True)
    out = CANDIDATES / f"{args.name}.yml"
    out.write_text(
        yaml.safe_dump(
            {"generated_from": len(seeds), "min_score": args.min_score,
             "candidates": [c.to_dict() for c in candidates]},
            sort_keys=False, allow_unicode=True, width=100),
        encoding="utf-8")

    print(f"\n{len(candidates)} candidate(s) -> {out.relative_to(REPO)}")
    print("These are PROPOSALS. The score is a keyword pre-filter, not the "
          "scope test — review before promoting any of them.")
    return 0


def cmd_build(args) -> int:
    topics = load_taxonomy(args.taxonomy)
    codes = {topic.code for topic in topics}
    resources = load_resources()

    # A tag pointing at a code the taxonomy doesn't define is a curation
    # error. Reported rather than written into the graph, where it would be
    # a dangling edge nobody notices.
    if orphaned := unknown_tags(resources, codes):
        for resource_id, bad in sorted(orphaned.items()):
            print(f"warning: {resource_id} tagged to unknown topics {bad}", file=sys.stderr)

    out = write_release(
        args.out,
        version=args.version,
        topics=topics,
        resources=resources,
        relationships=(_parent_edges(topics) + tagged_edges(resources, codes)
                       + _citation_edges(resources)),
        built_at=args.built_at,
    )
    print(f"wrote {out}  ({len(topics)} topics, {len(resources)} resources)")
    for path in sorted(out.iterdir()):
        print(f"  {path.name:<22} {path.stat().st_size:>9,} bytes")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aokg", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    tax = sub.add_parser("taxonomy", help="parse and report on the taxonomy")
    tax.add_argument("--path", default=str(DEFAULT_TAXONOMY))
    tax.add_argument("--stats", action="store_true", help="per-section counts")
    tax.add_argument("--lenient", action="store_true",
                     help="report problems instead of refusing to load")
    tax.set_defaults(func=cmd_taxonomy)

    build = sub.add_parser("build", help="write a graph release")
    build.add_argument("--version", required=True)
    build.add_argument("--taxonomy", default=str(DEFAULT_TAXONOMY))
    build.add_argument("--out", default=str(DEFAULT_RELEASES))
    build.add_argument("--built-at", default=None,
                       help="ISO date recorded in metadata; omit for a reproducible build")
    build.set_defaults(func=cmd_build)

    resolve = sub.add_parser("resolve", help="fetch OpenAlex metadata for existing records")
    resolve.add_argument("--refresh", action="store_true",
                         help="re-fetch records already stored")
    resolve.set_defaults(func=cmd_resolve)

    expand = sub.add_parser("expand", help="propose new records from the citation graph")
    expand.add_argument("--seed", action="append",
                        help="OpenAlex id to expand from; repeatable. Default: the whole corpus")
    expand.add_argument("--max-seeds", type=int, default=10)
    expand.add_argument("--per-seed", type=int, default=25)
    expand.add_argument("--min-score", type=int, default=3)
    expand.add_argument("--limit", type=int, default=60)
    expand.add_argument("--name", default="candidates")
    expand.set_defaults(func=cmd_expand)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (TaxonomyError, ResourceError, OpenAlexError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
