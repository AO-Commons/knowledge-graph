# Attribution

Work this library builds on, and the terms it carries.

## awesome-builder-tools

[framework-zero/awesome-builder-tools](https://github.com/framework-zero/awesome-builder-tools)
— © 2026 Framework Zero, MIT licence.

`data/tooling/awesome-builder-tools.yml` mirrors that list. Entry names,
descriptions and section headings are Framework Zero's own words, carried under
the MIT licence with the copyright notice preserved. The mirror records the
upstream commit it was taken from and is re-read weekly by
[`scripts/sync_tooling.py`](scripts/sync_tooling.py).

**The two are not the same thing, and the split is deliberate.** Their list
answers *what should I build with*, organised by the builder's job — orchestration,
CRM, go-to-market, payments. This library answers *what does a tool let agents
do, and what stops them*, organised by the taxonomy. Of their 60 entries, 7
describe agents holding authority or being constrained; the rest are tools a
company buys rather than tools that give an agent authority, and pouring all of
them into `data/resources/` would drown a corpus scoped to agentic
organizations.

So an entry crosses into the library one at a time, when somebody has read the
tool's own documentation and can say what oversight it actually ships, with
sources. A mirrored entry is upstream's claim. A record in `data/resources/` is
ours. `promoted_to` on an entry marks the ones that have made that crossing.

If you are looking for breadth, read their list — it is better at that than this
will be, and it is maintained by people closer to the building.

## Metadata sources

- **arXiv** — bylines, titles and abstracts for preprints, via its public API,
  and full text via the LaTeXML rendering at `arxiv.org/html/`. Authoritative
  for a preprint over any index, which is why it wins on disagreement.
- **OpenAlex** — identity, citation counts and institutional affiliations.
  CC0. Its author disambiguation is machine-inferred and has been wrong here,
  which is why [`scripts/check_authors.py`](scripts/check_authors.py) exists.
- **Semantic Scholar** — abstracts and reference lists, particularly for
  preprints OpenAlex has not indexed.
- **DataCite** and **Crossref** — DOI metadata, reachable from a browser where
  the others are not.

## The library itself

Released under CC-BY-4.0, as recorded in every release's `metadata.json`.
Attribution: AO Commons — https://github.com/AO-Commons/knowledge-graph
