# scripts/

| Script | Purpose |
|---|---|
| [ingest_seeds.py](ingest_seeds.py) | Expands a seed manifest into `data/resources/`. Idempotent |
| [airtable.py](airtable.py) | `setup` · `push` · `check` · `sync` — the Airtable curation surface |
| [airtable_schema.py](airtable_schema.py) | The Resources table definition and its mapping to `Resource` |
| [add_resource.py](add_resource.py) | Turns a new-resource issue into a record; run by the intake bot |
| [merge_filing.py](merge_filing.py) | Merges a filing issue into the gold set |
| [check_authors.py](check_authors.py) | Reconciles bylines against arXiv |
| [build_site.py](build_site.py) · [build_graph.py](build_graph.py) | The review site and the 3D graph |
| [bulk_add.py](bulk_add.py) | Adds a list of identifiers at once; see [docs/bulk-add.md](../docs/bulk-add.md) |
| [sync_tooling.py](sync_tooling.py) | Re-reads awesome-builder-tools, reports what moved and what is worth profiling |
| [mirror_public.py](mirror_public.py) | Builds the public Airtable base from this repo and the registry. One-way, daily |
| [mcp_server.py](mcp_server.py) | Shim; the server itself is `ao_commons_kg.mcp_server`, run as `aokg-mcp` |

## The public base

**The repository is the source of truth. The public base is a way to view it.**

Five tables, rebuilt every morning from `data/resources/` and the registry's
published JSON. Nothing is read back, and there is no `sync` counterpart — an
edit typed into the base survives until the next run and no longer.

| Table | What it holds | Joined to |
|---|---|---|
| **Papers** | What the library holds | Authors, Organizations |
| **People** | Who wrote it, one spelling each | The organizations they belong to |
| **Organizations** | Where those people work, and who builds the tooling | People, Papers, Tooling |
| **Tooling** | Software and the oversight it ships | The organization that built it, the AOs running it |
| **Registry** | Autonomous organizations — the actual experiments | Tooling |

People join to Organizations through per-paper affiliations rather than a
flattened list, so *who works on inter-agent trust, and where* stays answerable.

```sh
export AIRTABLE_TOKEN=pat...              # schema.bases:write + data.records:*
export AIRTABLE_PUBLIC_BASE_ID=app...
python3 scripts/mirror_public.py --dry-run
python3 scripts/mirror_public.py
```

Convergent and safe to re-run: missing tables and fields are created, rows are
matched on their primary field, and rows whose source record is gone are
retired. It never deletes a table, a field or a select option.

Three things keep a bad run from doing damage:

- **The deletion guard.** It refuses to retire more than a quarter of a table at
  once, and refuses outright to clear a table the repository says is empty.
  There is no floor on table size — a table of four hand-made rows is exactly
  the one nobody would notice losing.
- **An unreadable source is not an empty one.** If the registry cannot be read,
  its table is left *untouched* and the run says so, rather than reporting zero
  rows and retiring what is there. The distinction between "no AOs yet" and "I
  could not tell" is the whole reason a table's rows can be `None` rather than
  `{}`, and it is what stops one failed fetch from clearing the tab.
- **Backoff.** Airtable allows five requests a second and a full build is a few
  hundred, so 429s and 5xx are retried with exponential backoff. A 401 or 422 is
  not retried: that is a fact, not a phase.

Two things are deliberately left in the repository. The **taxonomy** is a tree
whose whole value is the hierarchy, and a flat tab would keep the codes while
losing what makes them worth having; it travels as a field instead. The **claim
and statement layer** stays because a claim without the sentence it was read
from is exactly the confident, unfalsifiable data this project exists not to
produce.

[`.github/workflows/mirror-public.yml`](../.github/workflows/mirror-public.yml)
runs it daily at 06:20 UTC, on every push that changes a record, and on demand
with a dry-run switch. It needs the `AIRTABLE_PUBLIC_TOKEN` secret and the
`AIRTABLE_PUBLIC_BASE_ID` variable. The registry is public, so its JSON is
fetched directly and needs no credential of its own.

[../tests/test_mirror_public.py](../tests/test_mirror_public.py) holds the seam:
every link resolves, every value is a type Airtable accepts, every facet and
topic is in its vocabulary, and no field name collides with the inverse link
Airtable adds by itself.

## Where records come from

Three paths, one destination:

```
hand-curated in Airtable ─┐
seed manifest ────────────┼──→ data/resources/*.yml ──→ release
OpenAlex / Semantic Scholar sweeps ─┘
```

`source_provenance` records which path a record took. That field is the
difference between a claim someone checked and one a crawler proposed, and
it should never be inferred or defaulted away.

The sync only manages records whose provenance starts with `airtable`. The
seed corpus lives in the repo and is not deleted for being absent from a
table it was never in.

## Setting up the curation surface

```sh
export AIRTABLE_TOKEN=...        # temporary, with schema.bases:write
export AIRTABLE_BASE_ID=app...
python3 scripts/airtable.py setup
python3 scripts/airtable.py check
```

Delete the write-scoped token afterwards. Sync needs only read access, and
the runtime token should not be able to restructure the base.

Then seed the empty table from the corpus already in the repo:

```sh
python3 scripts/airtable.py push --dry-run   # see what it would create
python3 scripts/airtable.py push
```

`push` is one-way and one-time. `setup` builds the table, `push` fills it, and
after that Airtable is the source of truth and `sync` runs the other way.
Records already in the base are never overwritten, so an edit made there
survives a re-run.

```sh
python3 scripts/airtable.py sync && aokg build --version v0.4.0
```

## Why the definition is code

`airtable_schema.py` derives every facet's options from
[`facets.py`](../src/ao_commons_kg/facets.py) and every tri-state from the
model. Twelve controlled vocabularies maintained in one place rather than
two, so a base whose options read "Preprint" while the model says "preprint"
cannot happen. `check` reports drift if someone edits the base by hand —
which does not make the sync fail, it makes the sync silently stop
populating a field, and that is worse.

[../tests/test_airtable.py](../tests/test_airtable.py) asserts the seam holds
in CI: options equal the model's vocabulary, single-valued facets are
single-selects, every mapped field exists and maps to a real attribute, and
internal fields are never mapped.

## `mcp_server.py` — the read-only query server

An MCP server over the corpus, for pointing an agent at the library during
review. Read-only by design: filings and claim verdicts enter through the site
and a pull request, where they are attributable to a person.

```bash
python3 -m pip install -e '.[mcp]'
claude mcp add ao-commons -- aokg-mcp
```

See [docs/mcp.md](../docs/mcp.md) for Claude Desktop and for what it will not
answer while the corpus is unreviewed.

Eight tools: `coverage`, `search_topics`, `get_topic`, `search_records`,
`get_record`, `get_claims`, `get_author`, `related_records`.

Every response says how much has been checked. Records carry `review_status`,
claims carry the verbatim sentence they were read from and whether anyone has
verified them, and computed edges say they were computed. That is deliberate:
at the time of writing none of the 61 records has been reviewed and none of
the 45 claims verified, and an agent has no way to detect that unless the
answers say so.

The corpus is read once at start-up. Rebuild the data and restart the server —
a cache with invalidation here would let it disagree with the site silently.

The questions it will not answer are the synthesising ones. "What reduces
cascading failures" needs claims across the corpus, verified; that is what the
review is for.
