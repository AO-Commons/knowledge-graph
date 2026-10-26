#!/usr/bin/env python3
"""Write an organization file for every organization the corpus cites.

    python3 scripts/seed_organizations.py            say what it would write
    python3 scripts/seed_organizations.py --write    write them
    python3 scripts/seed_organizations.py --write --only "Google DeepMind"

Names come from the affiliations already on records. `city`, `country`, `ror`
and `website` come from OpenAlex, because they go stale and ROR is the
identifier the rest of the world joins on. `kind` is guessed from OpenAlex's
own type and left for a person to correct; `roles` is always left empty,
because what an organization *does in this ecosystem* is a judgment no
registry holds.

A file that already exists is never overwritten. The whole point of the file
is to hold the judgments, and a seeder that clobbers them is a seeder nobody
can run twice.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from ao_commons_kg.models import Organization  # noqa: E402
from ao_commons_kg.organizations import build_index  # noqa: E402
from ao_commons_kg.resources import load_resources  # noqa: E402

OUT = REPO / "data" / "organizations"
API = "https://api.openalex.org/institutions"

#: OpenAlex's institution types, mapped onto ours. Theirs describes what an
#: organization is in general; `frontier-lab` and `collective` are
#: distinctions this field makes that theirs does not, so neither can be
#: guessed and both are left for a person.
FROM_OPENALEX = {
    "education": "university",
    "facility": "research-institute",
    "government": "government",
    "nonprofit": "foundation",
    "company": "company",
    "healthcare": "research-institute",
    "archive": "research-institute",
    "other": "company",
}


#: When OpenAlex cannot be reached or knows nothing, the name itself says a
#: good deal. Conservative on purpose: anything these do not recognise is left
#: as `company`, which is the kind a person is most likely to notice is wrong.
BY_NAME = (
    ("university", ("university", "universit", "college", "école", "universidad",
                    "universität", "université", "universiteit")),
    ("research-institute", ("institute", "institut", "laboratory", "laboratoire",
                            "academy", "academia", "research center",
                            "research centre", "cnrs", "max planck", "inria")),
    ("government", ("ministry", "department of", "national agency", "bureau of",
                    "centers for disease", "center for disease")),
    ("foundation", ("foundation", "trust", "fund", "society", "association")),
    ("standards-body", ("consortium", "standards", "w3c", "ietf")),
)


def kind_from_name(name: str) -> str:
    low = name.lower()
    for kind, words in BY_NAME:
        if any(w in low for w in words):
            return kind
    return "company"


def slug(name: str) -> str:
    keep = [c.lower() if c.isalnum() else "-" for c in name]
    out = "".join(keep)
    while "--" in out:
        out = out.replace("--", "-")
    return out.strip("-")


def ask_openalex(name: str) -> dict | None:
    """One institution, or nothing. Never guesses past the first result."""
    url = f"{API}?search={urllib.parse.quote(name)}&per_page=1"
    req = urllib.request.Request(url, headers={
        "User-Agent": "ao-commons-kg (https://github.com/AO-Commons/knowledge-graph)"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            results = json.load(r).get("results") or []
    except Exception as err:                        # noqa: BLE001
        print(f"    openalex: {type(err).__name__}", file=sys.stderr)
        return None
    return results[0] if results else None


def organization_names() -> Counter:
    """Every organization the corpus names, canonicalised, with a count."""
    raw: Counter = Counter()
    for resource in load_resources():
        for name in (resource.organizations or []):
            raw[name] += 1
        for names in (resource.affiliations or {}).values():
            for name in names:
                raw[name] += 1
    index = build_index(sorted(raw))
    canon: Counter = Counter()
    for name, n in raw.items():
        canon[index.get(name, name)] += n
    return canon


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--only", default="", help="one organization, by name")
    ap.add_argument("--min", type=int, default=1,
                    help="skip organizations named fewer than this many times")
    args = ap.parse_args(argv)

    names = organization_names()
    wanted = [(n, c) for n, c in names.most_common()
              if c >= args.min and (not args.only or n == args.only)]
    print(f"{len(names)} organizations named; {len(wanted)} to consider\n")

    OUT.mkdir(parents=True, exist_ok=True)
    written = skipped = unmatched = 0

    for name, count in wanted:
        path = OUT / f"{slug(name)}.yml"
        if path.exists():
            skipped += 1
            continue

        found = ask_openalex(name)
        time.sleep(0.12)                      # OpenAlex asks for politeness
        geo = (found or {}).get("geo") or {}
        kind = (FROM_OPENALEX.get(found.get("type") or "", "company")
                if found else kind_from_name(name))

        org = Organization(
            id=f"org:{slug(name)}",
            name=name,
            organization_type=kind,
            roles=[],
            city=geo.get("city"),
            country=geo.get("country"),
            ror=(found or {}).get("ror"),
            website=(found or {}).get("homepage_url"),
            source_provenance=(
                f"openalex {found['id'].rsplit('/', 1)[-1]}, {time.strftime('%Y-%m-%d')}"
                if found else "named by the corpus; no OpenAlex match"),
        )
        if not found:
            unmatched += 1

        where = f"{org.city}, {org.country}" if org.city else "—"
        print(f"  {count:>4}  {name[:44]:<44} {kind:<18} {where}")

        if args.write:
            lines = [f"id: {org.id}", f"name: {org.name}", f"organization_type: {org.organization_type}",
                     "roles: []                 # what it does here; see models.py ROLES"]
            for key in ("city", "country", "ror", "website"):
                value = getattr(org, key)
                if value:
                    lines.append(f"{key}: {value}")
            lines.append(f"source_provenance: {org.source_provenance}")
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            written += 1

    print(f"\n{written} written, {skipped} already there, {unmatched} with no OpenAlex match")
    if not args.write:
        print("Nothing written. Re-run with --write.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
