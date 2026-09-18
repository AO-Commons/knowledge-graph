#!/usr/bin/env python3
"""Recompute which verdicts came from the paper's own author.

The mark is derived from the link table, so confirming a link has to be able
to reach verdicts already merged — otherwise the first author review in the
corpus would stay invisible for ever because it arrived before anybody
recorded who filed it.

Idempotent, and safe to run after every confirmation:

    python3 scripts/mark_authors.py            # report
    python3 scripts/mark_authors.py --write    # record it
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from ao_commons_kg.claims import DEFAULT_VERDICTS  # noqa: E402
from ao_commons_kg.people import load_identities, wrote  # noqa: E402
from ao_commons_kg.resources import load_resources  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)

    path = DEFAULT_VERDICTS
    if not path.exists():
        print("no verdicts yet")
        return 0

    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    gold = payload.get("claims") or {}
    identities = load_identities()
    authors_of = {r.id: (r.authors or []) for r in load_resources()}

    # A claim id carries its resource, so the byline is reachable without
    # loading the corpus through the gold file it is about to rewrite.
    changed = []
    for claim_id, entry in gold.items():
        resource_id = "resource:" + ":".join(claim_id.split(":")[1:-1])
        is_author = wrote(entry.get("reviewer") or "", authors_of.get(resource_id, []),
                          identities)
        if bool(entry.get("by_author")) == is_author:
            continue
        changed.append((claim_id, entry.get("reviewer"), is_author))
        if is_author:
            entry["by_author"] = True
        else:
            entry.pop("by_author", None)

    if not changed:
        print(f"{len(gold)} verdict(s), nothing to change")
        return 0

    for claim_id, who, is_author in changed:
        print(f"  {'+' if is_author else '-'} {claim_id}  {who}")
    if not args.write:
        print(f"\n{len(changed)} would change. Re-run with --write.")
        return 0

    path.write_text(yaml.safe_dump({"claims": gold}, sort_keys=False,
                                   allow_unicode=True, width=88), encoding="utf-8")
    print(f"\nmarked {len(changed)} verdict(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
