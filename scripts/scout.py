#!/usr/bin/env python3
"""Look for work the citation graph cannot see.

`grow` finds papers connected to ones we hold. This finds papers connected to
nothing we hold, which is the larger half of the field and completely
invisible to expansion — a paper that neither cites us nor is cited by us
scores zero against a citation threshold, however plainly it belongs.

It proposes and never admits. Growth admits automatically because two held
papers citing something is the corpus voting for it; a scout has no such
vote, so its output is a candidate file and a person decides.

    python3 scripts/scout.py                    # report
    python3 scripts/scout.py --write            # write the candidate file

See `docs/scouting.md` for the argument.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from ao_commons_kg.claims import load_claims  # noqa: E402
from ao_commons_kg.classify import TopicIndex  # noqa: E402
from ao_commons_kg.concepts import load_vocabulary  # noqa: E402
from ao_commons_kg.resources import load_resources  # noqa: E402
from ao_commons_kg.scholarly.keys import keys_for_corpus  # noqa: E402
from ao_commons_kg.scout import queries_from_corpus, sweep  # noqa: E402
from ao_commons_kg.scout_sources import ArxivSource, OpenAlexSource  # noqa: E402
from ao_commons_kg.taxonomy import load_taxonomy  # noqa: E402

TAXONOMY = REPO / "taxonomy" / "agentic-org-research-library-taxonomy-v3.md"
ALIASES = REPO / "taxonomy" / "aliases.yaml"
OUT = REPO / "data" / "candidates"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deepen", type=int, default=6,
                        help="queries from concepts statements have needed")
    parser.add_argument("--widen", type=int, default=6,
                        help="queries from taxonomy subpoints nothing is filed under")
    parser.add_argument("--seed", type=int, default=0,
                        help="which slice of the unreached subpoints to search")
    parser.add_argument("--threshold", type=float, default=12.0)
    parser.add_argument("--per-query", type=int, default=10)
    parser.add_argument("--budget", type=int, default=40)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)

    resources = load_resources()
    claims = load_claims()
    vocabulary = load_vocabulary()

    in_use = sorted({t for c in claims for t in (c.concept_tags or [])})
    unreached = sorted(set(vocabulary.concepts) - set(in_use))

    queries = queries_from_corpus(in_use, unreached, deepen=args.deepen,
                                  widen=args.widen, seed=args.seed)
    print(f"{len(resources)} held, {len(in_use)} concepts in use, "
          f"{len(unreached)} never reached for")
    for query in queries:
        print(f"  {query.reason:7} {query.text}")

    index = TopicIndex(load_taxonomy(TAXONOMY),
                       yaml.safe_load(ALIASES.read_text(encoding="utf-8")) or {})

    print()
    found = sweep(
        [ArxivSource(), OpenAlexSource()], queries,
        index=index, concepts_in_use=in_use,
        held_keys=keys_for_corpus(resources),
        threshold=args.threshold, per_query=args.per_query, budget=args.budget,
        on_query=lambda q, s, n: print(f"  {s:9} {n:3} for {q.text[:44]!r}"),
    )
    print(f"\n{found.summary()}\n")

    for find in found.kept:
        topics = ", ".join(code for code, _ in find.topics[:3])
        print(f"  {find.score:6.1f}  {find.date or '????-??-??'}  {find.title[:58]}")
        print(f"          {find.key}  [{topics}]")
        if find.concepts:
            print(f"          concepts: {', '.join(find.concepts)}")

    if not args.write:
        print("\nRe-run with --write to record these as candidates.")
        return 0

    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"scout-{date.today().isoformat()}.yml"
    path.write_text(yaml.safe_dump({
        "found_by": "scout",
        "generated_on": date.today().isoformat(),
        "threshold": args.threshold,
        "queries": [{"text": q.text, "reason": q.reason} for q in queries],
        "candidates": [{
            "key": f.key, "title": f.title, "date": f.date, "url": f.url,
            "source": f.source, "score": round(f.score, 2),
            "topics": [{"code": c, "score": s} for c, s in f.topics],
            "concepts": list(f.concepts),
            "found_via": list(f.queries),
        } for f in found.kept],
    }, sort_keys=False, allow_unicode=True, width=88), encoding="utf-8")
    print(f"\nwrote {path.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
