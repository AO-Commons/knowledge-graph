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
| [sync_tooling.py](sync_tooling.py) | Re-reads awesome-builder-tools, reports what moved and what is worth profiling |
| [mcp_server.py](mcp_server.py) | Shim; the server itself is `ao_commons_kg.mcp_server`, run as `aokg-mcp` |

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
