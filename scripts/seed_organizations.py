#!/usr/bin/env python3
"""Write an organization file for every organization the corpus cites.

    python3 scripts/seed_organizations.py            say what it would write
    python3 scripts/seed_organizations.py --write    write them
    python3 scripts/seed_organizations.py --write --only "Google DeepMind"
    python3 scripts/seed_organizations.py --fill --write   fill missing places in existing files

Names come from the affiliations already on records. `city`, `country`, `ror`
and `website` come from OpenAlex, because they go stale and ROR is the
identifier the rest of the world joins on. `kind` is guessed from OpenAlex's
own type and left for a person to correct; `roles` is always left empty,
because what an organization *does in this ecosystem* is a judgment no
registry holds.

A file that already exists is never overwritten. The whole point of the file
is to hold the judgments, and a seeder that clobbers them is a seeder nobody
can run twice. `--fill` is the one exception, and it is narrow: for a file
with no `city`, the state OpenAlex's rate limit left most of the first run in,
it asks ROR and adds only the derived fields that are missing.
`organization_type`, `roles` and `aliases` are never touched.

ROR rather than OpenAlex for the fill, for two reasons. OpenAlex now wants an
API key for more than a handful of calls, and ROR's affiliation matcher says
when it is sure: a match it has not `chosen` is skipped rather than guessed,
so a common name never lands in the wrong city.
"""
from __future__ import annotations

import argparse
import json
import os
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
ROR = "https://api.ror.org/v2/organizations"

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
    """One institution, or nothing. Never guesses past the first result.

    Without a key the request counts against a daily budget shared by
    everyone on this IP, which is how 138 of the first 191 came back empty.
    `OPENALEX_API_KEY` in the environment gives this run its own budget;
    keys are free, and the key is read from the environment rather than
    stored here so it never reaches the repository.
    """
    url = f"{API}?search={urllib.parse.quote(name)}&per_page=1"
    headers = {"User-Agent": "ao-commons-kg (https://github.com/AO-Commons/knowledge-graph)"}
    if key := os.environ.get("OPENALEX_API_KEY"):
        headers["Authorization"] = f"Bearer {key}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            results = json.load(r).get("results") or []
    except Exception as err:                        # noqa: BLE001
        print(f"    openalex: {type(err).__name__}", file=sys.stderr)
        return None
    return results[0] if results else None


DERIVED = ("city", "country", "ror", "website")


def ask_ror(name: str) -> dict | None:
    """The organization ROR's affiliation matcher is sure of, or nothing."""
    url = f"{ROR}?affiliation={urllib.parse.quote(name)}"
    req = urllib.request.Request(url, headers={
        "User-Agent": "ao-commons-kg (https://github.com/AO-Commons/knowledge-graph)"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            items = json.load(r).get("items") or []
    except Exception as err:                        # noqa: BLE001
        print(f"    ror: {type(err).__name__}", file=sys.stderr)
        return None
    chosen = [i["organization"] for i in items if i.get("chosen")]
    if not chosen:
        return None
    org = chosen[0]
    place = ((org.get("locations") or [{}])[0].get("geonames_details") or {})
    website = next((link["value"] for link in org.get("links") or [] if link.get("type") == "website"), None)
    return {"id": org["id"], "city": place.get("name"), "country": place.get("country_name"),
            "ror": org["id"], "website": website}


def fill(path: Path, write: bool) -> str:
    """Add the derived fields a file lacks, and nothing else. Returns what happened."""
    text = path.read_text(encoding="utf-8")
    have = {line.split(":", 1)[0] for line in text.splitlines() if ":" in line and not line.startswith(" ")}
    if "city" in have:
        return "has a city"
    name = next(line.split(":", 1)[1].strip() for line in text.splitlines() if line.startswith("name:"))
    found = ask_ror(name)
    time.sleep(0.2)
    if not found:
        return "no confident ROR match"
    values = {key: found.get(key) for key in DERIVED}
    new = [f"{key}: {values[key]}" for key in DERIVED if values[key] and key not in have]
    if not new:
        return "ROR has no place either"
    stamp = f"ror {found['id'].rsplit('/', 1)[-1]}, {time.strftime('%Y-%m-%d')}"
    lines = text.rstrip("\n").splitlines()
    at = next((i for i, line in enumerate(lines) if line.startswith("source_provenance:")), len(lines))
    lines[at:at] = new
    if at < len(lines) - len(new) and lines[at + len(new)].startswith("source_provenance:"):
        old = lines[at + len(new)].split(":", 1)[1].strip()
        lines[at + len(new)] = f"source_provenance: {old}; {', '.join(k for k in DERIVED if values[k] and k not in have)} from {stamp}"
    else:
        lines.append(f"source_provenance: derived fields from {stamp}")
    if write:
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return f"{name} -> {values['city']}, {values['country']}"


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
    ap.add_argument("--fill", action="store_true",
                    help="fill missing city, country, ror and website in existing files, from ROR")
    args = ap.parse_args(argv)

    if args.fill:
        filled = 0
        for path in sorted(OUT.glob("*.yml")):
            result = fill(path, args.write)
            if "->" in result:
                filled += 1
                print(f"  {result}")
        print(f"\n{filled} {'filled' if args.write else 'would be filled'}")
        if not args.write:
            print("Nothing written. Re-run with --write.")
        return 0

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
        # OpenAlex asks for politeness. A key raises the budget, not the rate.
        time.sleep(0.12)
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
