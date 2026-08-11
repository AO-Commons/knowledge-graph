#!/usr/bin/env python3
"""Build the Airtable Resources table, and sync it into data/resources/.

    python3 scripts/airtable.py setup    # create or converge the tables
    python3 scripts/airtable.py push     # seed an empty base from data/resources/
    python3 scripts/airtable.py check    # compare the live base to the definition
    python3 scripts/airtable.py sync     # regenerate data/resources/ from Airtable

Env: AIRTABLE_TOKEN, AIRTABLE_BASE_ID

`setup` needs schema.bases:write. `sync` and `check` need only read access,
and the runtime token should not be able to alter the base structure.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import requests
import yaml

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "scripts"))

from airtable_schema import (  # noqa: E402
    BLOCKERS, PUBLISHED_FIELD, RESOURCES_TABLE, SOURCES_FIELDS, SOURCES_LINK_FIELD,
    SUPPORTS_FIELD,
    SOURCES_TABLE, TABLES, resource_from_row, row_from_resource,
    validate_definition,
)

from ao_commons_kg.models import Resource  # noqa: E402
from ao_commons_kg.resources import load_resources  # noqa: E402
from ao_commons_kg.taxonomy import load_taxonomy  # noqa: E402

API = "https://api.airtable.com/v0"
META = f"{API}/meta/bases"
OUT = REPO / "data" / "resources"
TAXONOMY = REPO / "taxonomy" / "agentic-org-research-library-taxonomy-v3.md"

# The same guard the registry sync uses: an Airtable filter typo should not
# be able to empty the corpus.
DELETION_GUARD_MIN = 5
DELETION_GUARD_FRACTION = 0.25


def credentials() -> tuple[str, str]:
    token = os.environ.get("AIRTABLE_TOKEN")
    base = os.environ.get("AIRTABLE_BASE_ID")
    if not token or not base:
        sys.exit("AIRTABLE_TOKEN and AIRTABLE_BASE_ID must be set.")
    return token, base


def api(method: str, url: str, token: str, **kwargs) -> dict:
    response = requests.request(
        method, url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        timeout=30, **kwargs,
    )
    if not response.ok:
        raise requests.HTTPError(f"{response.status_code}: {response.text}", response=response)
    return response.json()


def fetch_all(base: str, table: str, token: str) -> list[dict]:
    records, offset = [], None
    while True:
        params = {"pageSize": 100}
        if offset:
            params["offset"] = offset
        payload = api("GET", f"{API}/{base}/{table}", token, params=params)
        records.extend(payload.get("records", []))
        if not (offset := payload.get("offset")):
            return records


def live_tables(base: str, token: str) -> dict:
    return {t["name"]: t for t in api("GET", f"{META}/{base}/tables", token)["tables"]}


def cmd_setup(args) -> int:
    if problems := validate_definition():
        print("the table definition disagrees with the model:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    token, base = credentials()
    live = live_tables(base, token)
    changed = 0

    for name, description, fields in TABLES:
        if name in live:
            present = {f["name"] for f in live[name]["fields"]}
            for field in fields:
                if field["name"] not in present:
                    api("POST", f"{META}/{base}/tables/{live[name]['id']}/fields", token,
                        json=field)
                    print(f"added {name}.{field['name']}")
                    changed += 1
            continue
        api("POST", f"{META}/{base}/tables", token,
            json={"name": name, "description": description, "fields": fields})
        print(f"created table {name} ({len(fields)} fields)")
        changed += 1

    live = live_tables(base, token)
    resources = live[RESOURCES_TABLE]
    if SOURCES_LINK_FIELD not in {f["name"] for f in resources["fields"]}:
        api("POST", f"{META}/{base}/tables/{resources['id']}/fields", token, json={
            "name": SOURCES_LINK_FIELD, "type": "multipleRecordLinks",
            "description": "Evidence for this record.",
            "options": {"linkedTableId": live[SOURCES_TABLE]["id"]},
        })
        print(f"added {RESOURCES_TABLE}.{SOURCES_LINK_FIELD}")
        changed += 1
        live = live_tables(base, token)
        resources = live[RESOURCES_TABLE]

    # Formula fields last, written against field IDs so a name like `ID *`
    # raises no escaping question.
    ids = {f["name"]: f["id"] for f in resources["fields"]}
    if "Publish Blockers" not in ids and all(n in ids for n, _, _ in BLOCKERS):
        clauses = [f'IF({{{ids[n]}}}, "", "{label} ")' for n, _, label in BLOCKERS]
        clauses.append(f'IF(LEN(ARRAYJOIN({{{ids[SOURCES_LINK_FIELD]}}}))>0, "", "Sources ")')
        try:
            api("POST", f"{META}/{base}/tables/{resources['id']}/fields", token, json={
                "name": "Publish Blockers", "type": "formula",
                "description": "Required fields still empty. Blank when publishable.",
                "options": {"formula": "TRIM(" + " & ".join(clauses) + ")"},
            })
            print(f"added {RESOURCES_TABLE}.Publish Blockers")
            changed += 1
        except requests.HTTPError as error:
            print(f"\ncould not create Publish Blockers: {error}", file=sys.stderr)

    print(f"\n{changed} change(s)." if changed else "\nBase already matches the definition.")
    return 0


def cmd_check(args) -> int:
    problems = validate_definition()
    token, base = credentials()
    live = live_tables(base, token)

    for name, _, fields in TABLES:
        if name not in live:
            problems.append(f"table {name!r} missing")
            continue
        actual = {f["name"]: f for f in live[name]["fields"]}
        for field in fields:
            found = actual.get(field["name"])
            if found is None:
                problems.append(f"{name}.{field['name']} missing")
            elif found["type"] != field["type"]:
                problems.append(
                    f"{name}.{field['name']}: base has {found['type']}, "
                    f"definition says {field['type']}"
                )
            elif "choices" in (field.get("options") or {}):
                want = {c["name"] for c in field["options"]["choices"]}
                got = {c["name"] for c in (found.get("options") or {}).get("choices", [])}
                if extra := got - want:
                    problems.append(f"{name}.{field['name']}: options not in the model {sorted(extra)}")
                if missing := want - got:
                    problems.append(f"{name}.{field['name']}: missing options {sorted(missing)}")

    if problems:
        print(f"{len(problems)} problem(s):", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    print("Base matches the definition.")
    return 0


def _create(base: str, table: str, token: str, records: list[dict]) -> list[str]:
    """Create records ten at a time — Airtable's per-request limit."""
    ids = []
    for start in range(0, len(records), 10):
        batch = records[start:start + 10]
        result = api("POST", f"{API}/{base}/{table}", token,
                     json={"records": [{"fields": f} for f in batch]})
        ids.extend(r["id"] for r in result["records"])
    return ids


def cmd_push(args) -> int:
    """Seed an empty base from records curated in the repo.

    One-way and one-time. `setup` builds the table; this fills it; after that
    Airtable is the source of truth and `sync` runs the other way. Records
    already in the base are left alone — this never overwrites an edit made
    there.
    """
    token, base = credentials()
    resources = load_resources(OUT)
    if not resources:
        print("nothing in data/resources/ to push.")
        return 0

    existing_sources = {
        r["fields"].get("URL *"): r["id"]
        for r in fetch_all(base, SOURCES_TABLE, token)
        if r.get("fields", {}).get("URL *")
    }
    existing_ids = {
        r["fields"].get("ID *")
        for r in fetch_all(base, RESOURCES_TABLE, token)
        if r.get("fields", {}).get("ID *")
    }

    # Sources first: a resource cannot link to a row that does not exist.
    wanted: dict[str, dict] = {}
    for resource in resources:
        for source in resource.sources:
            url = source.get("url")
            if url and url not in existing_sources and url not in wanted:
                wanted[url] = {
                    "URL *": url,
                    "Title": source.get("title", ""),
                    "Accessed *": source.get("accessed"),
                    SUPPORTS_FIELD: ", ".join(source.get("supports", [])),
                }
    if wanted:
        rows = [{k: v for k, v in f.items() if v} for f in wanted.values()]
        created = _create(base, SOURCES_TABLE, token, rows)
        existing_sources.update(dict(zip(wanted, created)))
        print(f"created {len(created)} source row(s)")

    to_create, skipped = [], 0
    for resource in resources:
        slug = resource.id.removeprefix("resource:")
        if slug in existing_ids:
            skipped += 1
            continue
        to_create.append(row_from_resource(resource, existing_sources))

    if to_create and not args.dry_run:
        created = _create(base, RESOURCES_TABLE, token, to_create)
        print(f"created {len(created)} resource row(s)")
    elif to_create:
        print(f"would create {len(to_create)} resource row(s)")

    print(f"\n{len(to_create)} to push, {skipped} already in the base.")
    return 0


def cmd_sync(args) -> int:
    token, base = credentials()
    codes = {t.code for t in load_taxonomy(TAXONOMY)}

    sources = {r["id"]: r for r in fetch_all(base, SOURCES_TABLE, token)}
    rows = fetch_all(base, RESOURCES_TABLE, token)
    published = [r for r in rows if r.get("fields", {}).get(PUBLISHED_FIELD)]
    print(f"{len(rows)} row(s), {len(published)} published, {len(sources)} source(s).")

    valid: dict[str, dict] = {}
    skipped: list[str] = []

    for row in published:
        payload = resource_from_row(row, sources)
        if not payload.get("id"):
            skipped.append(f"{row['id']} — no ID")
            continue
        if bad := [c for c in payload.get("taxonomy_topics", []) if c not in codes]:
            skipped.append(f"{payload['id']} — tags not in the taxonomy: {bad}")
            continue
        try:
            Resource(**payload)
        except (TypeError, ValueError) as error:
            skipped.append(f"{payload['id']} — {error}")
            continue
        valid[payload["id"]] = payload

    for line in skipped:
        print(f"  skipped {line}", file=sys.stderr)

    OUT.mkdir(parents=True, exist_ok=True)
    # Only Airtable-sourced files are managed here. Records curated in the
    # repo — the seed corpus — are left alone rather than deleted for being
    # absent from a table they were never in.
    managed = {
        r.id for r in load_resources(OUT)
        if (r.source_provenance or "").startswith("airtable")
    }
    removed = managed - set(valid)
    if (removed and len(managed) >= DELETION_GUARD_MIN
            and len(removed) / len(managed) > DELETION_GUARD_FRACTION
            and os.environ.get("SYNC_ALLOW_DELETIONS") != "1"):
        print(f"\nRefusing: would remove {len(removed)} of {len(managed)} Airtable-sourced "
              f"records. Re-run with SYNC_ALLOW_DELETIONS=1 if intended.", file=sys.stderr)
        return 1

    for resource_id, payload in sorted(valid.items()):
        payload.setdefault("source_provenance", "airtable")
        name = resource_id.removeprefix("resource:").replace(":", "-") + ".yml"
        (OUT / name).write_text(
            yaml.safe_dump(payload, sort_keys=False, allow_unicode=True, width=88),
            encoding="utf-8")
    for resource_id in sorted(removed):
        (OUT / (resource_id.removeprefix("resource:").replace(":", "-") + ".yml")).unlink()
        print(f"  removed {resource_id}")

    print(f"\nwrote {len(valid)} record(s) to data/resources/.")
    return 0 if not skipped else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="airtable", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name, func in (("setup", cmd_setup), ("check", cmd_check), ("sync", cmd_sync)):
        sub.add_parser(name).set_defaults(func=func)
    push = sub.add_parser("push", help="seed an empty base from data/resources/")
    push.add_argument("--dry-run", action="store_true")
    push.set_defaults(func=cmd_push)
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except requests.HTTPError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
