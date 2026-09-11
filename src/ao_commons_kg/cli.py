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

from .claims import claim_edges, load_claims
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
    keys_for_corpus,
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
        for source, target in store.citation_pairs(keys_for_corpus(resources))
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

    # Claims are nodes of their own. Folding them into the resource that makes
    # them would put them back inside the container they exist to be
    # addressable outside of.
    claims = load_claims()

    out = write_release(
        args.out,
        version=args.version,
        topics=topics,
        resources=resources,
        claims=claims,
        relationships=(_parent_edges(topics) + tagged_edges(resources, codes)
                       + _scholarly_edges(resources)
                       + claim_edges(claims, topic_codes=codes)),
        built_at=args.built_at,
    )
    print(f"wrote {out}  ({len(topics)} topics, {len(resources)} resources, "
          f"{len(claims)} claims)")
    for path in sorted(out.iterdir()):
        print(f"  {path.name:<22} {path.stat().st_size:>9,} bytes")
    return 0



def cmd_grow(args) -> int:
    """Admit works the corpus already cites, automatically and within bounds.

    The path that replaces "a maintainer reads a queue". Three gates in cost
    order — a rising threshold, then the scope scan, then a per-run budget —
    and with no scope judge configured it admits nothing and says so, rather
    than falling back to a keyword score.
    """
    import sys as _sys
    from datetime import date as _date

    _sys.path.insert(0, str(REPO / "scripts"))
    from add_resource import (
        identify, likely_same_work, paper_record, write_record, write_references,
    )

    from .expansion import (
        DUPLICATES, REFUSALS, admissions_that_were_previously_refused,
        find_candidates, load_excluded, merge_refusals, provenance,
        record_duplicate, refusal_record, select,
    )
    from .scholarly import arxiv
    from .scholarly.keys import keys_for_corpus
    from .scholarly.store import ReferenceStore

    resources = load_resources()
    titles = {r.id: r.title for r in resources}
    store = ReferenceStore.load(REFERENCES)

    # The forward direction. Without it the corpus can only ever find work
    # old enough to have been cited, which makes it structurally unable to
    # admit anything published recently however plainly it belongs. Costs a
    # query per held record, so it is on by default and can be skipped.
    citers: dict[str, list[str]] = {}
    if not args.no_citers:
        from .scholarly.keys import canonical_key
        from .scholarly.openalex import works_citing

        fetch_citers = http_fetcher()
        holders = [r for r in resources if r.openalex_id]
        print(f"asking who cites {len(holders)} held record(s)"
              + (f", published since {args.since}" if args.since else ""))
        for resource in holders:
            found = works_citing(resource.openalex_id, fetch_citers,
                                 limit=args.citer_limit, since=args.since)
            keys = [k for k in (canonical_key({"doi": w.doi, "arxiv": w.arxiv_id})
                                for w in found) if k]
            if keys:
                citers[resource.id] = keys

    candidates = find_candidates(
        store.references(), keys_for_corpus(resources),
        {r.id: r.expansion_generation for r in resources},
        citers=citers)
    # Drop what a previous run already established is a record we hold.
    # Left in, each one costs a scope scan and a metadata fetch every week
    # to rediscover the same thing.
    excluded = load_excluded(REPO / DUPLICATES)
    if excluded:
        before = len(candidates)
        candidates = [c for c in candidates if c.key not in excluded]
        print(f"{len(candidates)} cited works not held "
              f"({before - len(candidates)} known duplicates excluded)")
    else:
        print(f"{len(candidates)} cited works not held")

    fetch_oa = http_fetcher()

    def metadata(candidate) -> dict:
        """Only ever called for candidates that cleared the threshold, which
        is what keeps a run from costing one lookup per cited work."""
        try:
            work = resolve_work(candidate.key.split(":", 1)[1], fetch_oa)
        except OpenAlexError:
            return {}
        return {"title": work.title, "abstract": work.abstract,
                "date": work.publication_date}

    judge = None
    if not args.propose_only:
        from .scope_judge import anthropic_judge
        judge = anthropic_judge(args.model, titles=titles)

    selection = select(candidates, judge=judge, metadata=metadata,
                       base=args.threshold, budget=args.budget)
    print(selection.summary())
    for candidate, verdict in selection.rejected:
        print(f"  refused {candidate.key}: {verdict.reasoning[:110]}")
    for candidate in selection.unresolvable:
        print(f"  unresolvable {candidate.key}: no title from OpenAlex, so there "
              "was nothing to judge — a data problem, not a scope decision")

    # A scan that errors refuses, which is the safe direction and also an
    # excellent way to hide a broken key or a bad deploy: every candidate
    # comes back refused and the run reports a normal-looking week in which
    # nothing happened to qualify. Distinguish the two out loud.
    broke = [v for _, v in selection.rejected if "could not complete" in v.reasoning]
    if broke and len(broke) == len(selection.rejected) and not selection.admitted:
        print(f"\nEvery scan failed ({len(broke)} of {len(broke)}). This is not a week "
              f"with nothing to add — the scan itself is broken.")
        print(f"  first failure: {broke[0].reasoning[:200]}")
        return 1
    if broke:
        print(f"\n{len(broke)} scan(s) failed and were refused rather than admitted. "
              "Refusing is the safe direction, but these are not scope judgements "
              "and the candidates remain queued.")
    if judge is None:
        for candidate in selection.over_budget[:20]:
            print(f"  would consider {candidate.support}x [{candidate.direction}] "
                  f"{candidate.key}")
        return 0

    # What the scan refused last time. Read before writing anything, so a
    # candidate it is now admitting can be flagged as a verdict it has
    # already made the other way.
    refusals_path = REPO / REFUSALS
    history = []
    if refusals_path.exists():
        history = (yaml.safe_load(refusals_path.read_text(encoding="utf-8")) or {}).get(
            "refused", [])
    flipped = admissions_that_were_previously_refused(
        [c.key for c, _ in selection.admitted], history)
    for entry in flipped:
        print(f"  NOTE {entry['key']} was refused {entry.get('times_refused', 1)}x "
              f"before and is admitted now — the scan has changed its mind")

    written = skipped = 0
    for candidate, verdict in selection.admitted:
        try:
            ident = identify(candidate.key.split(":", 1)[1])
            payload, _ = paper_record(
                ident, {}, topics=[], author="citation-expansion", issue=0,
                fetch_openalex=fetch_oa, fetch_s2=semanticscholar.http_fetcher(),
                # arXiv last and decisive, exactly as the human paths do it.
                # Passing None here was a mistake that reintroduced the
                # comma-byline bug this pipeline already fixed once: OpenAlex
                # writes "Yao, Shunyu" and only the submission itself gives
                # "Shunyu Yao". Three of the first eight auto-admitted
                # records came in wrong, and the Airtable round-trip test —
                # which splits authors on commas — is what caught it.
                fetch_arxiv=arxiv.http_fetcher())
        except Exception as error:  # noqa: BLE001 — one bad candidate must not end the run
            print(f"  could not resolve {candidate.key}: {error}")
            continue
        # The duplicate check the two human paths run. It is *stricter*
        # here, and has to be: on those paths the warning goes to a person
        # who decides, and on this one there is nobody to warn. So a likely
        # duplicate is skipped rather than written with a note nobody reads.
        #
        # The first live run needed this. It admitted the ACM version of
        # Generative Agents while the corpus already held the arXiv
        # preprint — different DOIs, so `already_held` could not see it,
        # and this path was not calling the check that could.
        if twins := likely_same_work(payload, resources):
            twin, why = twins[0]
            print(f"  skipped {payload['title'][:52]}: looks like {twin.id} ({why})")
            if not args.dry_run:
                record_duplicate(REPO / DUPLICATES, candidate.key, twin.id, why,
                                 _date.today().isoformat())
            skipped += 1
            continue
        payload["expansion_generation"] = candidate.generation
        if verdict.borrowed_background:
            payload["is_borrowed_background"] = True
        payload["source_provenance"] = provenance(candidate, verdict, titles)
        payload["ingested_at"] = _date.today().isoformat()
        if not args.dry_run:
            write_references(payload)
            write_record(payload)
        written += 1
        print(f"  + gen{candidate.generation} {payload['title'][:64]}")

    if not args.dry_run and selection.rejected:
        fresh = [refusal_record(c, v, _date.today().isoformat())
                 for c, v in selection.rejected
                 if "could not complete" not in v.reasoning]
        merged, _ = merge_refusals(history, fresh)
        refusals_path.parent.mkdir(parents=True, exist_ok=True)
        refusals_path.write_text(
            yaml.safe_dump({"refused": merged}, sort_keys=False, allow_unicode=True,
                           width=94), encoding="utf-8")
        print(f"  {len(fresh)} refusal(s) recorded; {len(merged)} in the history")

    print(f"\n{written} record(s) {'would be ' if args.dry_run else ''}added"
          + (f", {skipped} skipped as likely duplicates." if skipped else "."))
    return 0



def cmd_relate(args) -> int:
    """Propose claim pairs worth reading, from shared concepts.

    Proposes only. Writing a relation is a judgement with provenance
    attached, and this command deliberately cannot make one — it hands a
    person, or a model whose name goes on the result, a short queue where
    there was an unreadable 780.
    """
    from .claims import candidate_pairs, load_claim_relations, load_claims

    claims = list(load_claims())
    relations = load_claim_relations(claims=claims)
    pairs = candidate_pairs(claims, relations,
                            across_papers_only=not args.within_papers)

    by_id = {c.id: c for c in claims}
    print(f"{len(claims)} claims, {len(relations)} relations already asserted")
    print(f"{len(pairs)} pair(s) share a concept and have not been judged\n")

    for left, right, shared in pairs:
        print(f"── {', '.join(shared)}")
        for claim in (left, right):
            paper = claim.resource_id.removeprefix("resource:")
            print(f"   [{claim.claim_type.value:10}] {paper}  {claim.id.rsplit(':', 1)[-1]}")
            print(f"      {claim.text}")
        if args.draft:
            print(f"""
  - source: {left.id}
    target: {right.id}
    relation: SUPPORTS | DISAGREES_WITH | QUALIFIES | EXTENDS_CLAIM
    confidence_class: INFERRED
    because: >-
      # why, or delete this block — sharing a concept is not a relation
    asserted_by: {args.by}
    asserted_on: {__import__("datetime").date.today().isoformat()}""")
        print()

    print("Most of these should be nothing. A high yield means the concept "
          "vocabulary is too loose, not that the corpus is unusually connected.")
    return 0



def cmd_concepts(args) -> int:
    """Report the statement vocabulary: what is used, what collides, what is inert.

    A concept list rots quietly. Nothing errors when two terms mean one
    thing; the relations that would have been proposed between claims
    carrying them simply are not, and an absence is not something anybody
    notices. This is the check that makes the state visible.
    """
    from .claims import load_claims
    from .concepts import duplicate_pairs, load_vocabulary, similar_terms, usage

    vocabulary = load_vocabulary()
    claims = load_claims()

    if args.propose:
        close = similar_terms(args.propose, vocabulary)
        if close:
            print(f"{args.propose!r} looks like something already here:\n")
            for score, concept in close[:5]:
                print(f"  {score:.0%}  {concept.id}")
                print(f"        {concept.label}   [{', '.join(concept.topics) or 'no topic'}]")
            print("\nUse one of those, or add it with `distinct_from_near_matches:` "
                  "saying why it is a different idea.")
            return 1
        print(f"{args.propose!r} is clear of everything in the vocabulary.\n"
              "Add it to taxonomy/concepts-extra.yml with the topics it sits under "
              "and a note saying what it is for.")
        return 0

    counts = usage(claims, vocabulary)
    used = {k: n for k, n in counts.items() if n}
    grown = sum(1 for k in used if vocabulary.get(k).origin == "claim")
    print(f"vocabulary: {len(used)} terms in use — {grown} grown from statements, "
          f"{len(used) - grown} taken from the suggestion pool")
    print(f"{len(counts) - len(used)} suggestions available, never reached for\n")

    alone = sorted(k for k, n in counts.items() if n == 1)
    if alone:
        print(f"on exactly one statement — connects nothing yet ({len(alone)}):")
        for key in alone:
            print(f"  {key}")
        print()

    pairs = duplicate_pairs(vocabulary)
    if pairs:
        print(f"pairs that look like one idea ({len(pairs)}):")
        for score, left, right in pairs[:args.limit]:
            flag = "  <- both in use" if counts.get(left.id) and counts.get(right.id) else ""
            print(f"  {score:.0%}  {left.label}")
            print(f"       {right.label}{flag}")
        print("\nMost of these are inherited from the taxonomy's subpoints, which were "
              "written as prose rather than as a vocabulary. They can only be fixed "
              "where the taxonomy is; what the loader prevents is a new one.\n")

    # A concept layer drifting far from the taxonomy is evidence about the
    # taxonomy, and the right response is eventually a topic proposal.
    from_claims = [c for c in vocabulary.concepts.values() if c.origin == "claim"]
    if from_claims:
        untopiced = [c.id for c in from_claims if not c.topics]
        print(f"added from claims: {len(from_claims)}"
              + (f", {len(untopiced)} with no taxonomy home: {untopiced}" if untopiced else ""))
        if len(from_claims) > 30:
            print("  That is a lot. A vocabulary drifting this far from the taxonomy "
                  "is evidence about the taxonomy — consider a topic proposal.")
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

    grow = sub.add_parser(
        "grow", help="admit works the corpus already cites, within bounds")
    grow.add_argument("--threshold", type=int, default=2,
                      help="citations from held papers needed at generation 1; "
                           "each generation out adds one")
    grow.add_argument("--budget", type=int, default=40,
                      help="most records to admit in one run")
    grow.add_argument("--model", default="claude-opus-5")
    grow.add_argument("--propose-only", action="store_true",
                      help="list what clears the threshold and stop, with no "
                           "model calls and nothing written")
    grow.add_argument("--dry-run", action="store_true",
                      help="run the scope scan but write nothing")
    grow.add_argument("--no-citers", action="store_true",
                      help="skip the forward direction. Cheaper, and makes the "
                           "run unable to find anything published recently")
    grow.add_argument("--since", default="",
                      help="only consider citing works published on or after this "
                           "date (YYYY-MM-DD), so a weekly run asks about what is "
                           "new rather than re-reading the same citers")
    grow.add_argument("--citer-limit", type=int, default=100,
                      help="most citing works to read per held record")
    grow.set_defaults(func=cmd_grow)

    relate = sub.add_parser(
        "relate", help="propose claim pairs worth reading, from shared concepts")
    relate.add_argument("--draft", action="store_true",
                        help="print a YAML skeleton for each pair")
    relate.add_argument("--within-papers", action="store_true",
                        help="include pairs from the same paper, which are mostly "
                             "premise-to-conclusion and a different reading task")
    relate.add_argument("--by", default="unattributed",
                        help="who the drafted relations would be attributed to")
    relate.set_defaults(func=cmd_relate)

    concepts = sub.add_parser(
        "concepts", help="report the statement vocabulary, or check a proposed term")
    concepts.add_argument("--propose", default="",
                          help="a label you are thinking of adding; says what it "
                               "collides with, or that it is clear")
    concepts.add_argument("--limit", type=int, default=12,
                          help="how many near-duplicate pairs to list")
    concepts.set_defaults(func=cmd_concepts)

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
