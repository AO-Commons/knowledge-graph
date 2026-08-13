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
from .graph import co_citation_counts, similarity_edges
from .models import ConfidenceClass, Relationship, RelationType
from .people import apply_index, build_index, duplicates
import yaml

from .classify import TopicIndex, classify_resource
from .resources import ResourceError, load_resources, tagged_edges, unknown_tags
from .review import GoldSet, agreement, parse_decision, present, search_topics, select_for_review
from .scholarly import (
    ReferenceStore, SemanticScholarError, expand_neighborhood, key_for_resource,
    resolve_paper, resolve_work, scope_score,
)
from .scholarly import semanticscholar
from .scholarly.openalex import (
    Candidate, OpenAlexError, http_fetcher, short_id,
)
from .taxonomy import TaxonomyError, load_taxonomy

REPO = Path(__file__).resolve().parent.parent.parent
DEFAULT_TAXONOMY = REPO / "taxonomy" / "agentic-org-research-library-taxonomy-v3.md"
OUT_RESOURCES = REPO / "data" / "resources"
DEFAULT_RELEASES = REPO / "data" / "releases"
REFERENCES = REPO / "data" / "scholarly" / "references.jsonl"
CANDIDATES = REPO / "data" / "candidates"
GOLD = REPO / "evals" / "gold" / "tags.yml"
ALIASES = REPO / "taxonomy" / "aliases.yaml"


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


def _scholarly_edges(resources) -> list[Relationship]:
    """CITES from stored references, SIMILAR_TO from bibliographic coupling.

    Both deterministic in the sense that matters: read or computed from
    structured data, never inferred, so neither carries a confidence class.
    """
    store = ReferenceStore.load(REFERENCES)
    held = {r.id for r in resources}

    edges = [
        Relationship(source, target, RelationType.CITES)
        for source, target in store.citation_pairs()
        if source in held and target in held
    ]
    references = {k: v for k, v in store.references().items() if k in held}
    edges += similarity_edges(references, min_shared=2)
    return edges



def cmd_resolve(args) -> int:
    """Fill in metadata our records lack, from the source that carries it.

    OpenAlex is identity and citation counts. Semantic Scholar is abstracts
    and references for preprints, which OpenAlex does not store — the gap
    that held reference coverage at 9 of 59 records.

    Never overwrites a curated value: a hand-written summary outranks a
    machine abstract, and losing one to a refresh would make the command
    untrustworthy.
    """
    store = ReferenceStore.load(REFERENCES)
    resources = load_resources()
    filled = skipped = failed = 0

    # The corpus is the authority on how a person's name is spelled, so a
    # newly fetched author list is folded onto what is already there rather
    # than adding a second spelling of someone we already hold.
    known_names = build_index(
        [a for r in resources for a in (r.authors or [])]
    )

    use_s2 = args.source in ("semanticscholar", "both")
    use_oa = args.source in ("openalex", "both")
    fetch_oa = http_fetcher() if use_oa else None
    fetch_s2 = semanticscholar.http_fetcher() if use_s2 else None

    for resource in resources:
        stored = store.entries.get(resource.id, {})
        if stored.get("referenced_works") and not args.refresh:
            skipped += 1
            continue

        path = OUT_RESOURCES / (resource.id.removeprefix("resource:").replace(":", "-") + ".yml")
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        updates: dict = {}
        references: list[str] = []
        source_used = stored.get("source", "")
        citations = stored.get("cited_by_count", 0)

        if use_oa and (identifier := resource.openalex_id or resource.doi or resource.arxiv_id):
            try:
                work = resolve_work(identifier, fetch_oa)
                citations = max(citations, work.cited_by_count)
                source_used = "openalex"
                updates.update({
                    "openalex_id": work.openalex_id, "abstract": work.abstract,
                    "authors": apply_index(work.authors, known_names),
                    "organizations": work.institutions,
                    "is_open_access": work.is_open_access, "is_retracted": work.is_retracted,
                })
            except OpenAlexError as error:
                print(f"  {resource.id}: openalex: {error}", file=sys.stderr)

        if use_s2 and (identifier := resource.doi or resource.arxiv_id):
            try:
                paper = resolve_paper(identifier, fetch_s2)
                references = paper.referenced_keys
                citations = max(citations, paper.citation_count)
                if references:
                    source_used = "semanticscholar"
                updates.setdefault("abstract", paper.abstract)
                updates["semantic_scholar_id"] = paper.semantic_scholar_id
                if not updates.get("authors"):
                    updates["authors"] = apply_index(paper.authors, known_names)
            except SemanticScholarError as error:
                print(f"  {resource.id}: s2: {error}", file=sys.stderr)

        if not updates and not references:
            failed += 1
            continue

        for key, value in updates.items():
            if value not in (None, [], "") and not payload.get(key):
                payload[key] = value
        path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True, width=88),
                        encoding="utf-8")

        store.put(resource.id, key=key_for_resource(resource), source=source_used or "unknown",
                  referenced_keys=references, cited_by_count=citations)
        filled += 1
        print(f"  {resource.id}: {len(references)} references, {citations} citations")

    store.save()
    with_refs, total = store.coverage()
    print(f"\n{filled} resolved, {skipped} skipped, {failed} with nothing to add.")
    if total:
        print(f"reference coverage: {with_refs}/{total} records ({with_refs / total:.0%})")
        if with_refs < total / 2:
            print(
                "\nStill thin. OpenAlex carries no reference lists for arXiv preprints;\n"
                "run `aokg resolve --source semanticscholar --refresh` to fill them."
            )
    return 0



def cmd_expand(args) -> int:
    """Walk one hop out from the corpus and write a review queue."""
    fetch = http_fetcher()
    resources = load_resources()
    known = {r.openalex_id for r in resources if r.openalex_id}

    if args.seed:
        seeds = args.seed
    else:
        # Which seeds you pick decides what the corpus becomes.
        #
        # Borrowed-background records are excluded by default. They are in the
        # library for transfer, and their citation neighbourhoods are the
        # adjacent field section 15 says to point at rather than ingest —
        # seeding from multi-agent RL benchmarks returns more multi-agent RL.
        #
        # Ranked by citations because only the forward direction works here:
        # OpenAlex holds no reference lists for arXiv preprints, which is most
        # of this corpus, so a seed with no citers yields nothing at all.
        store = ReferenceStore.load(REFERENCES)
        pool = [r for r in resources if r.openalex_id]
        if not args.include_borrowed:
            pool = [r for r in pool if not r.is_borrowed_background]
        seeds = [
            r.openalex_id for r in sorted(
                pool,
                key=lambda r: -(store.entries.get(r.id, {}).get("cited_by_count", 0)),
            )
        ]

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

    # Structural candidates: works the corpus already cites, repeatedly.
    #
    # No keywords involved. A work several of our papers cite is part of this
    # conversation by the field's own behaviour, whatever its title says —
    # which is how "Institutions as cached computation" would be found, and
    # keyword scoring never will.
    if not args.no_structural:
        references = store.references()
        co_cited = co_citation_counts(references)
        structural = [
            (work_id, count) for work_id, count in co_cited.most_common()
            if count >= args.min_co_cited and work_id not in known
        ][: args.structural_limit]

        if structural:
            print(f"\nresolving {len(structural)} work(s) the corpus cites repeatedly")
        for work_id, count in structural:
            if any(c.openalex_id == work_id for c in candidates):
                continue
            try:
                work = resolve_work(work_id, fetch)
            except OpenAlexError:
                continue
            score, reasons = scope_score(work)
            # Structural evidence outranks vocabulary. Cited by several of our
            # own papers is a stronger claim than containing the word "agent".
            candidates.append(Candidate(
                openalex_id=work.openalex_id, title=work.title, doi=work.doi,
                publication_date=work.publication_date,
                cited_by_count=work.cited_by_count,
                score=score + 3 * count,
                reasons=[f"+{3 * count} co-cited by {count} corpus papers"] + reasons,
                found_via=f"co-cited by {count} corpus papers",
                authors=work.authors, institutions=work.institutions,
            ))
            print(f"  co-cited×{count}  {work.title[:58]}")

    store.save()
    candidates.sort(key=lambda c: (-c.score, -c.cited_by_count))
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


def _index() -> TopicIndex:
    aliases = yaml.safe_load(ALIASES.read_text(encoding="utf-8")) if ALIASES.exists() else {}
    return TopicIndex(load_taxonomy(DEFAULT_TAXONOMY), aliases or {})


def cmd_review(args) -> int:
    """Walk records one at a time, picking topics from a shortlist.

    Resumable: anything already in the gold file is skipped, so this can be
    done in several sittings without losing place.
    """
    index = _index()
    gold = GoldSet.load(args.gold)
    if args.reviewer:
        gold.reviewer = args.reviewer

    queue = select_for_review(load_resources(), gold, limit=args.limit)
    if not queue:
        print(f"Nothing left to review. {len(gold.entries)} record(s) in {args.gold}.")
        return 0

    print(f"{len(queue)} record(s) queued, {len(gold.entries)} already reviewed.")
    print("Sampled across taxonomy sections so the set resembles the corpus.")

    reviewed = 0
    for position, resource in enumerate(queue, 1):
        candidates = classify_resource(index, resource, limit=args.suggestions, min_score=0.5)
        while True:
            print(present(resource, candidates, index))
            print(f"  [{position}/{len(queue)}]")
            decision = parse_decision(input("  > "), candidates)

            if decision.action == "search":
                found = search_topics(index, decision.query)
                if not found:
                    print("  nothing matched.")
                    continue
                candidates = found
                continue
            if decision.action == "quit":
                gold.save()
                print(f"\nSaved {len(gold.entries)} record(s) to {args.gold}.")
                return 0
            if decision.action == "skip":
                break
            if decision.action == "keep":
                gold.record(resource.id, resource.taxonomy_topics, reviewer=gold.reviewer)
                reviewed += 1
                break
            gold.record(resource.id, decision.topics, reviewer=gold.reviewer)
            reviewed += 1
            break

        if reviewed and reviewed % 5 == 0:
            gold.save()

    gold.save()
    print(f"\nReviewed {reviewed}. {len(gold.entries)} record(s) in {args.gold}.")
    return 0


def cmd_evaluate(args) -> int:
    """Score the classifier against reviewed tags."""
    gold = GoldSet.load(args.gold)
    if not gold.entries:
        print(f"No gold set at {args.gold}. Build one with `aokg review`.", file=sys.stderr)
        return 1

    index = _index()
    resources = {r.id: r for r in load_resources()}
    predictions = {
        resource_id: [a.code for a in classify_resource(
            index, resources[resource_id], limit=args.limit, min_score=args.min_score)]
        for resource_id in gold.entries if resource_id in resources
    }

    scores = agreement(gold, predictions)
    print(f"against {scores['reviewed_records']} reviewed record(s)")
    print(f"  gold tags recovered   {scores['recovered']}/{scores['gold_tags']} "
          f"= {scores['recall']:.0%}")
    print(f"  exact code matches    {scores['exact']}")
    print(f"  records with a hit    {scores['records_with_a_hit']}/{scores['reviewed_records']} "
          f"= {scores['record_hit_rate']:.0%}")
    if scores["reviewed_records"] < 30:
        print("\nFewer than 30 reviewed records — treat these as indicative, not as a"
              "\nbaseline to tune against.")
    return 0


def cmd_people(args) -> int:
    """Report, and optionally fix, one person appearing under two spellings."""
    resources = load_resources()
    names = [a for r in resources for a in (r.authors or [])]
    found = duplicates(names)

    distinct = len({a for a in names})
    print(f"{len(names)} authorship(s), {distinct} distinct spelling(s), "
          f"{len(found)} person/people split across spellings")
    if not found:
        return 0

    for best, spellings in sorted(found.items()):
        variants = "  |  ".join(
            f"{name!r} ×{count}" for name, count in sorted(spellings.items(), key=lambda x: -x[1])
        )
        print(f"\n  keep {best!r}")
        print(f"       {variants}")

    if not args.fix:
        print("\nRe-run with --fix to rewrite the records.")
        return 0

    index = build_index(names)
    touched = 0
    for resource in resources:
        merged = apply_index(resource.authors or [], index)
        if merged == (resource.authors or []):
            continue
        path = OUT_RESOURCES / (resource.id.removeprefix("resource:").replace(":", "-") + ".yml")
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        payload["authors"] = merged
        path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=True, width=88),
                        encoding="utf-8")
        touched += 1
    print(f"\nrewrote {touched} record(s).")
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
                       + _scholarly_edges(resources)),
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
    resolve.add_argument("--source", choices=("openalex", "semanticscholar", "both"),
                         default="both",
                         help="openalex for identity and citations, semanticscholar "
                              "for the arXiv abstracts and references it does not carry")
    resolve.set_defaults(func=cmd_resolve)

    expand = sub.add_parser("expand", help="propose new records from the citation graph")
    expand.add_argument("--seed", action="append",
                        help="OpenAlex id to expand from; repeatable. Default: the whole corpus")
    expand.add_argument("--max-seeds", type=int, default=10)
    expand.add_argument("--per-seed", type=int, default=25)
    expand.add_argument("--min-score", type=int, default=3)
    expand.add_argument("--limit", type=int, default=60)
    expand.add_argument("--name", default="candidates")
    expand.add_argument("--min-co-cited", type=int, default=2,
                        help="propose works cited by at least this many corpus papers")
    expand.add_argument("--structural-limit", type=int, default=40)
    expand.add_argument("--no-structural", action="store_true",
                        help="keyword expansion only, skipping the co-citation pass")
    expand.add_argument("--include-borrowed", action="store_true",
                        help="also seed from borrowed-background records; their "
                             "neighbourhoods are the adjacent fields section 15 excludes")
    expand.set_defaults(func=cmd_expand)

    review = sub.add_parser("review", help="assign topics by hand, to build a gold set")
    review.add_argument("--gold", default=str(GOLD))
    review.add_argument("--limit", type=int, default=50)
    review.add_argument("--suggestions", type=int, default=12)
    review.add_argument("--reviewer", default="", help="recorded on each decision")
    review.set_defaults(func=cmd_review)

    evaluate = sub.add_parser("evaluate", help="score the classifier against reviewed tags")
    evaluate.add_argument("--gold", default=str(GOLD))
    evaluate.add_argument("--limit", type=int, default=6)
    evaluate.add_argument("--min-score", type=float, default=4.0)
    evaluate.set_defaults(func=cmd_evaluate)

    people = sub.add_parser("people", help="find one person spelled two ways")
    people.add_argument("--fix", action="store_true", help="rewrite the records")
    people.set_defaults(func=cmd_people)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (TaxonomyError, ResourceError, OpenAlexError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
