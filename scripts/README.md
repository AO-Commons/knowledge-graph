# scripts/

| Script | Purpose |
|---|---|
| [ingest_seeds.py](ingest_seeds.py) | Expands a seed manifest into `data/resources/`. Idempotent |
| [airtable.py](airtable.py) | `setup` · `check` · `sync` — the Airtable curation surface |
| [airtable_schema.py](airtable_schema.py) | The Resources table definition and its mapping to `Resource` |

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

```sh
python3 scripts/airtable.py sync && aokg build --version v0.3.0
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
