#!/usr/bin/env python3
"""Build the public Airtable base from this repository and the AO registry.

    python3 scripts/mirror_public.py --dry-run   # say what would change
    python3 scripts/mirror_public.py             # converge the base

Env: AIRTABLE_TOKEN, AIRTABLE_PUBLIC_BASE_ID

**The repository is the source of truth. This base is a way to view it.**

Everything here is extracted from `data/resources/` and from the registry's
published JSON. Nothing is ever read back. An edit typed into the base survives
until the next run and no longer, which is why every table says so in its
description and why this script has no `sync` counterpart.

Five tables:

    Papers         what the library holds
    People         who wrote it
    Organizations  where those people work, and who builds the tooling
    Tooling        software a builder would reach for, and its oversight
    Registry       autonomous organizations — the actual experiments

People join to Organizations through per-paper affiliations rather than a
flattened list, so "who works on inter-agent trust, and where" stays answerable.
Tooling joins to Organizations through its maintainer, and to Registry through
the organizations known to run it.

The taxonomy is a field here, not a table. It is a tree of 103 codes whose whole
value is the hierarchy, and a flat Airtable tab would keep the codes while
losing the thing that makes them worth having. The claim and statement layer is
left out for a stronger reason: a claim without the sentence it was read from is
exactly the confident, unfalsifiable data this project exists not to produce.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
from collections import defaultdict
from pathlib import Path

import requests

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from ao_commons_kg import organizations as orgs_mod  # noqa: E402
from ao_commons_kg import people as people_mod  # noqa: E402
from ao_commons_kg.facets import BY_NAME as FACETS  # noqa: E402
from ao_commons_kg.models import TRISTATE, ReviewStatus  # noqa: E402
from ao_commons_kg.resources import load_resources  # noqa: E402
from ao_commons_kg.taxonomy import load_taxonomy  # noqa: E402

API = "https://api.airtable.com/v0"
META = f"{API}/meta/bases"
RESOURCES = REPO / "data" / "resources"
TAXONOMY = REPO / "taxonomy" / "agentic-org-research-library-taxonomy-v3.md"
REGISTRY_LOCAL = REPO.parent / "registry" / "data" / "registry.json"
REGISTRY_URL = (
    "https://raw.githubusercontent.com/AO-Commons/registry/main/data/registry.json"
)
REGISTRY_API = (
    "https://api.github.com/repos/AO-Commons/registry/contents/data/registry.json"
)

# A view that empties itself because an upstream read failed is worse than a
# stale one. Past this fraction the run stops instead of retiring rows. There is
# deliberately no floor on table size: a table of four hand-made rows is exactly
# the one nobody would notice losing.
DELETION_GUARD_FRACTION = 0.25

RETRYABLE = {429, 500, 502, 503, 504}
MAX_RETRIES = 5

TOOL_TYPES = {
    "code-tool", "platform", "evaluation-suite", "deployment", "research-programme",
}

VIEW_NOTE = (
    "Rebuilt daily from AO-Commons/knowledge-graph. The repository is the source "
    "of truth; this base is a way to view it. Edits made here are overwritten by "
    "the next run."
)

# Facets worth browsing by. All twelve live in the repository; these are the ones
# that answer a question somebody actually asks of a spreadsheet.
MIRRORED_FACETS = (
    "evidence_strength", "source_independence", "temporal_relevance", "applicability",
    "organizational_function", "autonomy_level_addressed", "agent_count_regime",
    "control_type", "stakeholder_perspective", "failure_relevance",
    "maturity_of_subject",
)


# ---------------------------------------------------------------------------
# Field helpers


def text(name, desc="", multi=False):
    return {
        "name": name,
        "type": "multilineText" if multi else "singleLineText",
        "description": desc,
    }


def url_field(name, desc=""):
    return {"name": name, "type": "url", "description": desc}


def number(name, desc=""):
    return {
        "name": name,
        "type": "number",
        "options": {"precision": 0},
        "description": desc,
    }


def checkbox(name, desc=""):
    return {
        "name": name,
        "type": "checkbox",
        "options": {"icon": "check", "color": "greenBright"},
        "description": desc,
    }


def select(name, values, desc="", multi=False):
    return {
        "name": name,
        "type": "multipleSelects" if multi else "singleSelect",
        "options": {"choices": [{"name": v} for v in values]},
        "description": desc,
    }


def link(name, table, desc=""):
    """A link field. `table` is resolved to a table id once the target exists."""
    return {
        "name": name,
        "type": "multipleRecordLinks",
        "_link": table,
        "description": desc,
    }


def facet_field(key):
    """One F1-F12 facet, with its vocabulary and cardinality taken from the model."""
    facet = FACETS[key]
    return select(
        key.replace("_", " ").title(), facet.values, facet.question, multi=facet.multi
    )


REVIEW = [e.value for e in ReviewStatus]
TRI = sorted(TRISTATE)


def topic_labels():
    """Taxonomy codes as select options, ordered by the tree rather than by string.

    "2.10" sorts after "2.9" here and before it everywhere a string comparison
    is used, which is the whole reason this is a key function and not `sorted`.
    """
    topics = load_taxonomy(TAXONOMY)

    def order(topic):
        return tuple(int(p) if p.isdigit() else 0 for p in topic.code.split("."))

    return {t.code: f"{t.code} {t.title}" for t in sorted(topics, key=order)}


# ---------------------------------------------------------------------------
# The five tables.
#
# Order matters twice over: a link field can only be created once its target
# table exists, and rows must exist before they can be linked to. Airtable adds
# the inverse of every link automatically, naming it after the source table —
# which is why no count field here is called "Papers", "People" or "Tooling".


def build_tables(topics):
    choices = list(topics.values())
    return [
        ("Organizations",
         "Where the people in this library work, and who builds the tooling. "
         + VIEW_NOTE, [
             text("Name",
                  "Canonical spelling. A trailing country is folded away; distinct "
                  "sub-entities such as Google and Google DeepMind stay apart, "
                  "because merging them would delete a distinction the field cares "
                  "about."),
             number("Paper Count",
                    "Records in the library credited to this organization."),
         ]),
        ("Registry",
         "Autonomous organizations: the actual experiments, where agents hold real "
         "operational or governance authority. Mirrored from AO-Commons/registry. "
         + VIEW_NOTE, [
             text("ID", "Stable registry slug. Safe to cite — it never changes, even "
                        "when an organization renames itself."),
             text("Name"),
             text("Summary", multi=True),
             select("Status",
                    ["active", "dormant", "wound-down", "announced", "unverified"]),
             url_field("Website"),
             text("Launched"),
             text("Categories"),
             text("Agent Roles"),
             select("Autonomy Level",
                    ["human-decision-machine-support",
                     "machine-proposal-human-approval",
                     "machine-decision-human-veto-window",
                     "fully-autonomous-execution", "mixed-unspecified"],
                    "What the evidence supports, not what the organization claims "
                    "about itself."),
             text("Human Oversight", "What keeps humans in control.", multi=True),
             text("Governance Model"),
             text("Legal Wrapper"),
             text("Jurisdiction"),
             text("Agent Stack"),
             text("Tags"),
         ]),
        ("People",
         "Authors in the library, one spelling each. " + VIEW_NOTE, [
             text("Name", "Canonical byline. Variant spellings fold onto it."),
             number("Paper Count", "Records in the library carrying this byline."),
             link("Organizations", "Organizations",
                  "Where this person is credited, taken from per-paper affiliations "
                  "rather than a flattened list."),
         ]),
        ("Papers",
         "What the library holds: papers, preprints and reports. " + VIEW_NOTE, [
             text("ID", "Stable record id. It is also the citation key."),
             text("Title"),
             select("Type", FACETS["artifact_type"].values),
             text("Abstract", multi=True),
             text("Published On",
                  "YYYY, YYYY-MM or YYYY-MM-DD. Text rather than a date, so partial "
                  "dates survive."),
             url_field("URL"),
             text("DOI"),
             text("arXiv ID"),
             text("OpenAlex ID"),
             checkbox("Open Access"),
             checkbox("Retracted"),
             select("Review Status", REVIEW,
                    "Whether a named human has checked the tags. An unreviewed tag is "
                    "a navigational aid, not a claim AO Commons is making."),
             checkbox("Borrowed Background",
                      "Section 15 material: relevant by transfer rather than about "
                      "agentic organizations directly. Exclude it from any count that "
                      "claims to measure the field's own literature."),
             select("Topics", choices,
                    "Taxonomy codes. The hierarchy itself lives in the repository — "
                    "a code's parent is derived from the code, never stored.",
                    multi=True),
             link("Authors", "People"),
             link("Organizations", "Organizations"),
         ] + [facet_field(k) for k in MIRRORED_FACETS]),
        ("Tooling",
         "Software a builder would reach for, profiled for what it lets agents do "
         "and what stops them. " + VIEW_NOTE, [
             text("ID"),
             text("Name"),
             select("Type", sorted(TOOL_TYPES)),
             text("Description", multi=True),
             url_field("URL"),
             url_field("Repository"),
             text("Agent Model",
                  "What shape of organization this tool makes possible.", multi=True),
             text("Human Controls", "The oversight it actually ships.", multi=True),
             select("Open Source", TRI,
                    "Tri-state, so an unresearched tool is never silently recorded as "
                    "proprietary."),
             select("Self Hostable", TRI),
             select("Model Agnostic", TRI),
             text("Status"),
             text("Languages"),
             text("Protocols"),
             select("Review Status", REVIEW),
             select("Topics", choices, "Taxonomy codes.", multi=True),
             link("Built By", "Organizations", "The organization that builds it."),
             link("Used By", "Registry",
                  "Autonomous organizations known to run on this tool."),
         ]),
    ]


PRIMARY = {
    "Organizations": "Name", "Registry": "ID", "People": "Name",
    "Papers": "ID", "Tooling": "ID",
}


# ---------------------------------------------------------------------------
# Airtable plumbing


def credentials():
    token = os.environ.get("AIRTABLE_TOKEN")
    base = os.environ.get("AIRTABLE_PUBLIC_BASE_ID")
    if not token or not base:
        sys.exit("AIRTABLE_TOKEN and AIRTABLE_PUBLIC_BASE_ID must be set.")
    return token, base


def api(method, url, token, **kwargs):
    """One Airtable call, with backoff on the failures that are worth retrying.

    Airtable allows five requests a second per base, and a full build is a few
    hundred. Without this a single 429 aborts the run midway, which for a
    convergent script means a half-built base until somebody notices and re-runs
    it. Retries cover 429 and 5xx only: a 401 or a 422 is a fact, not a phase.
    """
    delay = 1.0
    for attempt in range(MAX_RETRIES):
        response = requests.request(
            method, url, timeout=60,
            headers={"Authorization": f"Bearer {token}",
                     "Content-Type": "application/json"},
            **kwargs,
        )
        if response.ok:
            return response.json()
        if response.status_code not in RETRYABLE or attempt == MAX_RETRIES - 1:
            raise requests.HTTPError(
                f"{method} {url} -> {response.status_code}: {response.text}"
            )
        wait = float(response.headers.get("Retry-After") or delay)
        print(f"  … {response.status_code} from Airtable, retrying in {wait:.0f}s",
              file=sys.stderr)
        time.sleep(wait)
        delay *= 2
    raise AssertionError("unreachable")


def fetch_all(base, table, token):
    records, offset = [], None
    while True:
        params = {"pageSize": 100}
        if offset:
            params["offset"] = offset
        page = api("GET", f"{API}/{base}/{table}", token, params=params)
        records.extend(page.get("records", []))
        if not (offset := page.get("offset")):
            return records


def batched(seq, size=10):
    """Airtable writes ten records per request."""
    for start in range(0, len(seq), size):
        yield seq[start:start + size]


def keyed(records, key_field):
    return {
        r["fields"].get(key_field): r["id"]
        for r in records if r["fields"].get(key_field)
    }


# ---------------------------------------------------------------------------
# Schema convergence


def live_schema(base, token):
    return {t["name"]: t for t in api("GET", f"{META}/{base}/tables", token)["tables"]}


def converge_schema(base, token, tables, dry):
    """Create missing tables and fields.

    Never deletes a table, a field or a select option, and never retypes one.
    A view that can drop a column is a view that can lose the only copy of
    something a person added by hand before anyone told them not to.
    """
    live = live_schema(base, token)
    ids = {name: table["id"] for name, table in live.items()}
    changes = []

    for name, description, fields in tables:
        plain = [f for f in fields if "_link" not in f]
        if name not in live:
            if dry:
                changes.append(f"create table {name} ({len(fields)} fields)")
                ids[name] = f"<new:{name}>"
                continue
            created = api("POST", f"{META}/{base}/tables", token, json={
                "name": name,
                "description": description[:20000],
                "fields": [{k: v for k, v in f.items() if k != "_link"} for f in plain],
            })
            ids[name] = created["id"]
            live[name] = created
            changes.append(f"created table {name}")
            continue

        have = {f["name"] for f in live[name]["fields"]}
        for field in plain:
            if field["name"] in have:
                continue
            if dry:
                changes.append(f"add {name}.{field['name']} ({field['type']})")
                continue
            api("POST", f"{META}/{base}/tables/{ids[name]}/fields", token, json=field)
            changes.append(f"added {name}.{field['name']}")

    # Link fields last, when every target table is guaranteed to exist.
    if not dry:
        live = live_schema(base, token)
        ids = {name: table["id"] for name, table in live.items()}
    for name, _, fields in tables:
        have = {f["name"] for f in live.get(name, {}).get("fields", [])}
        for field in fields:
            target = field.get("_link")
            if not target or field["name"] in have:
                continue
            if dry:
                changes.append(f"add {name}.{field['name']} -> {target}")
                continue
            api("POST", f"{META}/{base}/tables/{ids[name]}/fields", token, json={
                "name": field["name"],
                "type": "multipleRecordLinks",
                "description": field.get("description", ""),
                "options": {"linkedTableId": ids[target]},
            })
            changes.append(f"added {name}.{field['name']} -> {target}")

    return ids, changes


# ---------------------------------------------------------------------------
# Repository to rows


class RegistryUnavailable(Exception):
    """The registry could not be read. Distinct from the registry being empty."""


def load_registry():
    """The AO registry, from a sibling checkout if there is one, else from GitHub.

    The registry repository is private, so the anonymous raw URL 404s and CI has
    no sibling checkout. Rather than crash the whole build over one of five
    tables — or, worse, report zero rows and let the guard think the registry was
    emptied — an unreadable registry raises, and the caller leaves that table
    exactly as it found it.
    """
    if REGISTRY_LOCAL.exists():
        try:
            payload = json.loads(REGISTRY_LOCAL.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise RegistryUnavailable(f"{REGISTRY_LOCAL}: {exc}") from exc
        return payload.get("registry", [])

    request = urllib.request.Request(REGISTRY_URL)
    if token := os.environ.get("REGISTRY_TOKEN"):
        # A PAT that can read the private registry. The workflow's own
        # GITHUB_TOKEN is scoped to this repository and will not do.
        request = urllib.request.Request(
            REGISTRY_API,
            headers={"Authorization": f"Bearer {token}",
                     "Accept": "application/vnd.github.raw"},
        )
    try:
        with urllib.request.urlopen(request, timeout=60) as handle:
            payload = json.loads(handle.read().decode())
    except Exception as exc:  # noqa: BLE001 — every failure means the same thing
        raise RegistryUnavailable(str(exc)) from exc
    return payload.get("registry", [])


def join(values):
    return ", ".join(str(v) for v in values if v) or None


def build_rows(topics):
    """Everything the base will hold, keyed by each table's primary value.

    A table mapped to ``None`` means its source could not be read, and the run
    must leave that table exactly as it found it. That is a different fact from
    an empty dict, which means the source was read and holds nothing — and the
    difference decides whether rows get retired.
    """
    resources = load_resources(RESOURCES)
    try:
        aos = load_registry()
    except RegistryUnavailable as exc:
        print(f"  ! registry unreadable ({exc}) — leaving that table untouched",
              file=sys.stderr)
        aos = None

    tools = [r for r in resources if r.tool or r.resource_type in TOOL_TYPES]
    tool_ids = {r.id for r in tools}
    papers = [r for r in resources if r.id not in tool_ids]

    # One spelling per person and per organization, across the whole corpus.
    person_index = people_mod.build_index([a for r in resources for a in r.authors])
    org_index = orgs_mod.build_index(
        [o for r in resources for o in r.organizations]
        + [r.tool.maintainer for r in tools if r.tool and r.tool.maintainer],
        orgs_mod.load_registry(),
    )

    def person(name):
        return person_index.get(people_mod.fold(name), name)

    def org(name):
        return org_index.get(orgs_mod.fold(name), name)

    person_counts, org_counts = defaultdict(int), defaultdict(int)
    affiliations = defaultdict(set)
    for resource in resources:
        for author in resource.authors:
            person_counts[person(author)] += 1
        for name in resource.organizations:
            org_counts[org(name)] += 1
        for author, places in (resource.affiliations or {}).items():
            for place in places:
                affiliations[person(author)].add(org(place))

    # An organization that only ever built a tool still needs a row, or the
    # Built By link has nothing to point at. Its paper count is honestly zero.
    for resource in tools:
        if resource.tool and resource.tool.maintainer:
            org_counts.setdefault(org(resource.tool.maintainer), 0)

    def topic_options(resource):
        return [topics[c] for c in resource.taxonomy_topics if c in topics]

    rows = {
        "Organizations": {
            name: {"Name": name, "Paper Count": count}
            for name, count in sorted(org_counts.items())
        },
        "People": {
            name: {"Name": name, "Paper Count": count}
            for name, count in sorted(person_counts.items())
        },
        "Registry": None if aos is None else {
            ao["id"]: {
                "ID": ao["id"],
                "Name": ao.get("name", ""),
                "Summary": ao.get("summary", ""),
                "Status": ao.get("status"),
                "Website": ao.get("website"),
                "Launched": ao.get("launched"),
                "Categories": join(ao.get("categories", [])),
                "Agent Roles": join(ao.get("agent_roles", [])),
                "Autonomy Level": ao.get("autonomy_level"),
                "Human Oversight": ao.get("human_oversight"),
                "Governance Model": ao.get("governance_model"),
                "Legal Wrapper": ao.get("legal_wrapper"),
                "Jurisdiction": ao.get("jurisdiction"),
                "Agent Stack": join(ao.get("agent_stack", [])),
                "Tags": join(ao.get("tags", [])),
            }
            for ao in aos
        },
        "Papers": {},
        "Tooling": {},
    }

    for resource in papers:
        slug = resource.id.removeprefix("resource:")
        row = {
            "ID": slug,
            "Title": resource.title,
            "Type": resource.resource_type,
            "Abstract": resource.abstract or resource.description or "",
            "Published On": str(resource.published_at or ""),
            "URL": resource.url,
            "DOI": resource.doi,
            "arXiv ID": resource.arxiv_id,
            "OpenAlex ID": resource.openalex_id,
            "Open Access": bool(resource.is_open_access),
            "Retracted": bool(resource.is_retracted),
            "Review Status": getattr(
                resource.review_status, "value", resource.review_status
            ),
            "Borrowed Background": bool(resource.is_borrowed_background),
            "Topics": topic_options(resource),
        }
        for key in MIRRORED_FACETS:
            value = resource.facets.get(key)
            if not value:
                continue
            label = key.replace("_", " ").title()
            if FACETS[key].multi:
                row[label] = value if isinstance(value, list) else [value]
            else:
                row[label] = value[0] if isinstance(value, list) else value
        row["_links"] = {
            "Authors": sorted({person(a) for a in resource.authors}),
            "Organizations": sorted({org(o) for o in resource.organizations}),
        }
        rows["Papers"][slug] = row

    for resource in tools:
        slug = resource.id.removeprefix("resource:")
        profile = resource.tool
        row = {
            "ID": slug,
            "Name": resource.title,
            "Type": (
                resource.resource_type
                if resource.resource_type in TOOL_TYPES else "code-tool"
            ),
            "Description": resource.description or resource.abstract or "",
            "URL": resource.url,
            "Repository": resource.repository_url,
            "Review Status": getattr(
                resource.review_status, "value", resource.review_status
            ),
            "Topics": topic_options(resource),
        }
        if profile:
            row.update({
                "Agent Model": profile.agent_model,
                "Human Controls": profile.human_controls,
                "Open Source": profile.open_source,
                "Self Hostable": profile.self_hostable,
                "Model Agnostic": profile.model_agnostic,
                "Status": profile.status,
                "Languages": join(profile.languages),
                "Protocols": join(profile.protocols),
            })
        row["_links"] = {
            "Built By": (
                [org(profile.maintainer)] if profile and profile.maintainer else []
            ),
            "Used By": list(profile.used_by) if profile else [],
        }
        rows["Tooling"][slug] = row

    for name, places in affiliations.items():
        if name in rows["People"]:
            rows["People"][name]["_links"] = {"Organizations": sorted(places)}

    return rows


# ---------------------------------------------------------------------------
# Record convergence


def push_table(base, table_id, name, wanted, key_field, token, dry):
    """Create, update and retire rows so the table equals `wanted`.

    `wanted` of None means the source could not be read; the table is skipped.
    """
    if wanted is None:
        print(f"  {name}: skipped, source unreadable")
        return {}

    live = [] if dry else fetch_all(base, table_id, token)
    by_key = keyed(live, key_field)

    creates, updates = [], []
    for key, row in wanted.items():
        payload = {
            k: v for k, v in row.items()
            if k != "_links" and v not in (None, "", [])
        }
        if key in by_key:
            updates.append({"id": by_key[key], "fields": payload})
        else:
            creates.append({"fields": payload})

    stale = [rid for key, rid in by_key.items() if key not in wanted]
    if stale and not wanted:
        print(f"  ! {name}: the repository says this table is empty while the base "
              f"holds {len(by_key)} row(s) — refusing to clear it.", file=sys.stderr)
        stale = []
    elif len(stale) > max(1, int(len(by_key) * DELETION_GUARD_FRACTION)):
        print(f"  ! {name}: {len(stale)} of {len(by_key)} rows would be retired — "
              f"refusing. Check the upstream read, then re-run.", file=sys.stderr)
        stale = []

    if dry:
        print(f"  {name}: +{len(creates)} new, ~{len(updates)} updated, "
              f"-{len(stale)} retired")
        return {}

    for batch in batched(creates):
        api("POST", f"{API}/{base}/{table_id}", token,
            json={"records": batch, "typecast": True})
    for batch in batched(updates):
        api("PATCH", f"{API}/{base}/{table_id}", token,
            json={"records": batch, "typecast": True})
    for batch in batched(stale):
        api("DELETE", f"{API}/{base}/{table_id}", token,
            params=[("records[]", rid) for rid in batch])

    print(f"  {name}: +{len(creates)} new, ~{len(updates)} updated, "
          f"-{len(stale)} retired")
    return keyed(fetch_all(base, table_id, token), key_field)


def link_target(tables, table_name, field_name):
    for name, _, fields in tables:
        if name != table_name:
            continue
        for field in fields:
            if field.get("name") == field_name:
                return field.get("_link")
    return None


def push_links(base, table_id, name, wanted, key_field, ids, tables, token):
    """Second pass: every row exists, so links resolve to real record ids."""
    by_key = keyed(fetch_all(base, table_id, token), key_field)
    updates, dropped = [], 0
    for key, row in wanted.items():
        links = row.get("_links")
        if not links or key not in by_key:
            continue
        fields = {}
        for field_name, targets in links.items():
            known = ids.get(link_target(tables, name, field_name), {})
            fields[field_name] = [known[t] for t in targets if t in known]
            dropped += sum(1 for t in targets if t not in known)
        if fields:
            updates.append({"id": by_key[key], "fields": fields})

    for batch in batched(updates):
        api("PATCH", f"{API}/{base}/{table_id}", token, json={"records": batch})
    note = f", {dropped} target(s) not in the base" if dropped else ""
    print(f"  {name}: linked {len(updates)} row(s){note}")


# ---------------------------------------------------------------------------


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="report what would change and write nothing")
    args = parser.parse_args(argv)

    topics = topic_labels()
    tables = build_tables(topics)
    rows = build_rows(topics)

    print("From the repository:")
    for name, _, _ in tables:
        count = "unreadable" if rows[name] is None else f"{len(rows[name])} row(s)"
        print(f"  {name}: {count}")

    if args.dry_run and not os.environ.get("AIRTABLE_TOKEN"):
        print("\nNo AIRTABLE_TOKEN set — row counts only, the base was not read.")
        return 0

    token, base = credentials()

    print(f"\nSchema ({'dry run' if args.dry_run else 'converging'}):")
    ids, changes = converge_schema(base, token, tables, args.dry_run)
    for change in changes:
        print(f"  {change}")
    if not changes:
        print("  already matches")

    print("\nRecords:")
    resolved = {
        name: push_table(base, ids[name], name, rows[name], PRIMARY[name], token,
                         args.dry_run)
        for name, _, _ in tables
    }
    if args.dry_run:
        return 0

    print("\nLinks:")
    for name, _, fields in tables:
        if any("_link" in f for f in fields):
            push_links(base, ids[name], name, rows[name], PRIMARY[name], resolved,
                       tables, token)

    print("\nDone. The base now reflects the repository.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
