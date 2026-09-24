# Attribution

Work this library builds on, and the terms it carries.

## awesome-builder-tools

[framework-zero/awesome-builder-tools](https://github.com/framework-zero/awesome-builder-tools)
— © 2026 Framework Zero, MIT license.

`data/tooling/awesome-builder-tools.yml` mirrors that list. Entry names,
descriptions and section headings are Framework Zero's own words, carried under
the MIT license with the copyright notice preserved. The mirror records the
upstream commit it was taken from and is re-read weekly by
[`scripts/sync_tooling.py`](scripts/sync_tooling.py).

**The two are not the same thing, and the split is deliberate.** Their list
answers *what should I build with*, organized by the builder's job — orchestration,
CRM, go-to-market, payments. This library answers *what does a tool let agents
do, and what stops them*, organized by the taxonomy. Of their 60 entries, 7
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

## MIRA

[mira-science/schema](https://github.com/mira-science/schema) — Apache License 2.0.
Namespace `http://purl.org/mira-science/mira#`.

MIRA is an open schema for research graphs: questions, the claims that answer
them, and the evidence behind each. Nothing of theirs is copied into this
repository. What we took is **two names**: their `Question` node, and the
`addresses` edge from a claim to it.

Both are for a layer this library had not built yet, which is the only reason
it was free to take them. We had designed the same node under the name
`Problem` and an edge called `ADDRESSES`; renaming it once the corpus held
data would have been the expensive version. Adopting the vocabulary of a
shared schema while a layer is still a sketch costs nothing and means the
graph is already speaking a common one if MIRA becomes the standard it is
trying to be.

Their schema goes deeper than ours where they work and we do not — `Study`,
`Protocol`, and `Evidence` tied to the activity that produced it, which is the
shape of a lab recording its own experiments. Ours goes deeper on reading
somebody else's published work: a verbatim quote for every claim, a verdict
bound to the wording it was given, and a reviewer linked to a byline. The two
are the same graph approached from opposite ends, which is the interesting
part and the reason to keep watching it.

We take the names and no obligations: Apache-2.0 asks for attribution when
its work is redistributed, and this is credit rather than redistribution.
