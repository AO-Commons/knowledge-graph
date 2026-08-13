#!/usr/bin/env python3
"""Check bylines against arXiv, which is the paper's own account of who wrote it.

OpenAlex is an inference over the literature, not a transcript of it. Its author
records are disambiguated by machine, and when that disambiguation is wrong it
is wrong in the worst possible way: it substitutes a real, plausible, different
person. Two examples found in this corpus —

    resource:arxiv:2511.03434   "Bin Hu"      should be  "Botao 'Amber' Hu"
    resource:arxiv:2501.16138   "G. Flucke"   should be  "Michael Luck"

— neither of which looks wrong unless you happen to know the field. Attributing
someone else's work to a person is a worse failure than any tagging error this
project measures, and it is invisible to every check we had.

For an arXiv preprint the authoritative byline is arXiv's own. But our stored
names are sometimes *better* than arXiv's, because a resolver supplied
diacritics arXiv's plain-text submission dropped: we hold "Nenad Tomašev" where
arXiv has "Nenad Tomasev". So this reconciles rather than overwrites — where
both name the same person, the fuller spelling wins; where they name different
people, arXiv wins.

Usage:
    python3 scripts/check_authors.py            # report
    python3 scripts/check_authors.py --fix      # reconcile and write
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from ao_commons_kg.people import canonical, fold, same_person  # noqa: E402
from ao_commons_kg.resources import load_resources  # noqa: E402
from ao_commons_kg.scholarly import arxiv  # noqa: E402

RESOURCES = REPO / "data" / "resources"


def arxiv_bylines(arxiv_ids: list[str]) -> dict[str, list[str]]:
    """The author list arXiv itself publishes, per id."""
    return {aid: p.authors for aid, p in arxiv.resolve_many(arxiv_ids).items()}


def reconcile(ours: list[str], theirs: list[str]) -> tuple[list[str], list[str]]:
    """Take arXiv's byline, keeping our diacritics, and name anyone it drops.

    Matched against the whole list rather than position by position. A long
    author list often reaches us in a different order, and comparing by index
    made every subsequent name look like a substitution — it reported that
    "Joel Z. Leibo" had become "Jakob Foerster" on a paper both of them wrote.

    arXiv's rendering wins wherever the two differ by more than accents. It is
    the byline the authors submitted, and second-guessing it needs better
    evidence than a resolver's guess.
    """
    merged: list[str] = []
    for theirs_name in theirs:
        match = next((o for o in ours if same_person(o, theirs_name)), None)
        # A pure accent or punctuation difference is a rendering, not a
        # disagreement: keep whichever is richer, which is usually ours,
        # because arXiv submissions are frequently plain ASCII.
        merged.append(canonical({match: 1, theirs_name: 1})
                      if match and fold(match) == fold(theirs_name) else theirs_name)

    # The finding that matters: a person we credit who is on no byline of this
    # paper. Everything else is spelling.
    dropped = [o for o in ours if not any(same_person(o, t) for t in theirs)]
    return merged, dropped


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fix", action="store_true", help="write the reconciled bylines")
    args = parser.parse_args(argv)

    resources = [r for r in load_resources() if r.arxiv_id]
    bylines = arxiv_bylines([r.arxiv_id for r in resources])

    changed = wrong_people = 0
    for resource in resources:
        theirs = bylines.get(resource.arxiv_id)
        if not theirs:
            print(f"  {resource.arxiv_id}: no arXiv entry — left alone", file=sys.stderr)
            continue

        merged, dropped = reconcile(resource.authors or [], theirs)
        if merged == (resource.authors or []):
            continue
        changed += 1

        print(f"\n{resource.id}")
        if dropped:
            wrong_people += 1
            for name in dropped:
                print(f"  NOT AN AUTHOR  {name!r} is on no byline of this paper")
        for before, after in zip(resource.authors or [], merged):
            if before != after and same_person(before, after):
                print(f"  spelling       {before!r} -> {after!r}")

        if args.fix:
            path = RESOURCES / (resource.id.removeprefix("resource:").replace(":", "-") + ".yml")
            payload = yaml.safe_load(path.read_text(encoding="utf-8"))
            payload["authors"] = merged
            path.write_text(
                yaml.safe_dump(payload, sort_keys=False, allow_unicode=True, width=88),
                encoding="utf-8",
            )

    print(f"\n{changed}/{len(resources)} bylines differ from arXiv; "
          f"{wrong_people} name at least one different person.")
    if changed and not args.fix:
        print("Run with --fix to reconcile them.")
    # A wrong person is a failure worth a red build, not a warning in a log.
    return 1 if wrong_people and not args.fix else 0


if __name__ == "__main__":
    sys.exit(main())
