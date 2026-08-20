# AO Commons — Knowledge Graph

A maintained map of research on **agentic organizations**: organizations in which machine agents hold operational or decision authority.

Browse the field through a purpose-built taxonomy, discover related work through the scholarly graph, find implementations and evaluations where they exist, and query the whole library directly from an AI agent.

The point is to help a researcher — human or machine — reach the right **small set of primary sources** faster and more cheaply than starting from a search engine. The graph decides *what to read*. It does not replace reading.

## Status

Early. Milestone 1 is done: the v3 taxonomy loads deterministically and exports as a portable release.

| Milestone | State |
|---|---|
| 1 — Taxonomy and data model | **Done** — 103 topics, 16 sections, JSONL export |
| 2 — Scholarly corpus (OpenAlex) | **Pipeline built; awaiting a live run** |
| 3 — Taxonomy classification | **Started** — BM25 baseline, review tooling, measured |
| 4 — Connected-Papers-style similarity | **Started** — bibliographic coupling and co-citation |
| 5 — Query surfaces (CLI, REST, MCP) | Not started |
| 6 — Optional enrichment | Deliberately deferred |

## The taxonomy

[`taxonomy/agentic-org-research-library-taxonomy-v3.md`](taxonomy/agentic-org-research-library-taxonomy-v3.md) is the source of truth. Everything else is derived from it.

```
103 topics · 16 sections · 86 subsections · 510 notes carried beneath them
```

Its scope test is enforced rather than decorative:

> An item belongs if it would change how you design, operate, oversee, or hold accountable an organization where agents act with real authority. Material about collective human decision-making that is unchanged by the presence of agents does not belong, however good it is.

Three structures live in that one file, and they are implemented differently on purpose:

- **The numbered hierarchy** is navigation. Codes are stable identifiers — never renumbered, never reused. `2.2.2` is a child of `2.2` because of its code, not because of how the file is indented.
- **Section 11 (Failure modes)** is a coding scheme, not a set of shelves. An incident normally carries several codes at once, and its 119 topics are marked `usage_mode: coding_scheme` so the query layer treats multi-tagging as the default.
- **F1–F12** are facets — flat controlled vocabularies on a resource, never a second tree. The taxonomy says what a resource is *about*; the facets say what kind of evidence it is and when it applies.

## Asking it questions from Claude

A read-only MCP server ships with the repository, so Claude can search the
taxonomy, look up people and records, and read extracted claims with the
sentence each came from.

```bash
python3 -m pip install -e '.[mcp]'
claude mcp add ao-commons -- aokg-mcp
```

[docs/mcp.md](docs/mcp.md) covers Claude Desktop, what it answers well, and
what it deliberately will not tell you while the corpus is unreviewed.

## Using the data

```bash
python3 -m pip install -e ".[scholarly]"
aokg taxonomy --stats            # what loaded, per section
aokg resolve                     # fetch OpenAlex metadata + reference lists
aokg expand --limit 40           # propose new records from the citation graph
aokg build --version v0.4.0      # write a portable release
```

Building the gold set that every classification figure is measured against:

```bash
aokg review --reviewer your-name   # assign topics from a shortlist
aokg evaluate                      # score the classifier against them
```

`expand` walks one hop out from the corpus in **both** directions — references
and citers — because they answer different questions. A corpus grown only
forward drifts toward the recent; only backward, toward the foundational. It
writes a scored review queue to `data/candidates/`, and nothing enters the
corpus without a human promoting it.

Candidates come from two instruments, and the structural one is the better of them:

- **Structure** — works the corpus already cites, repeatedly. No keywords involved. A work several of our papers cite is part of this conversation by the field's own behaviour, whatever its title says.
- **Vocabulary** — a keyword score, used to rank rather than to admit.

The keyword score has a known ceiling and the code says so. *Institutions as cached computation for resource-rational negotiation* is squarely in scope, contains no agent-ish words, and scores 1; it would be found by co-citation and never by vocabulary. Domain applications ("agentic AI in smart manufacturing") are **flagged rather than penalized**, because no keyword can separate "agents run this business" from "agents schedule maintenance here" — the reviewer decides.

The score is a **keyword pre-filter, not the scope test**. Calibrated against
a hand pass over ~90 works it agrees on 11 of 12 title-only cases, and its one
known blind spot is recorded in the tests: it cannot find papers that are
relevant by argument rather than by vocabulary. Author expansion finds those;
the two instruments are complementary.

Releases follow the layout below and are usable without running any of our code:

```
data/releases/<version>/
├── nodes.jsonl           topics, resources, entities — one JSON object per line
├── relationships.jsonl   edges, each carrying its provenance
├── taxonomy.json         the tree on its own, for browsing
├── metadata.json         counts, license, attribution
└── checksums.txt
```

Builds are reproducible: nodes sort by id, edges by their triple, and no timestamp is written unless you pass one. The same inputs produce the same bytes, which is what makes the checksums worth publishing and a diff between releases worth reading.

## How to read an edge

Every relationship says where it came from, because "this paper cites that one" and "a model thinks these are related" are different claims and should never look alike.

| Kind | Example | Carries |
|---|---|---|
| Deterministic | `CITES`, `PARENT_OF` | Nothing extra — read from structured metadata |
| Computed | `SIMILAR_TO` | `method` and `score`, always. A similarity whose method is hidden can't be interpreted |
| Extracted or inferred | `DISCUSSES`, `PROPOSES`, … | `confidence_class` of `EXTRACTED`, `INFERRED`, or `AMBIGUOUS`, plus the source text it came from |

The schema refuses to let these blur: labelling a citation with a confidence class is an error, because it implies a judgement nobody made.

## Design commitments

**Small schema.** Three node families — Resource, Topic, and one generic Entity. Adding a fourth should require showing a real query that can't be answered without it.

**Boring storage.** The logical product is a graph; the physical database can be SQLite or Postgres. No graph database and no vector store until measurement shows one earns its place.

**Graph first, source second.** For an ordinary question: query the taxonomy and graph, return compact metadata, identify 5–15 likely sources, and only then fetch full text. Sending a corpus to a model is the thing this project exists to avoid.

**Scope discipline over completeness.** The exclusion register in the taxonomy is honoured. Material that is excellent but unchanged by machine authority stays out, and Section 15 points at adjacent literatures rather than ingesting them.

## Repository layout

| Path | Contents |
|---|---|
| [taxonomy/](taxonomy/) | The v3 source file, aliases, cross-links, and change proposals |
| [src/ao_commons_kg/](src/ao_commons_kg/) | Models, taxonomy parser, export |
| [data/releases/](data/releases/) | Published graph releases |
| [tests/](tests/) | Run with `pytest` |
| [evals/](evals/) | Research questions and results for benchmarking against baselines |
| [docs/](docs/) | Data model and architecture notes |

## Contributing

Corrections to the taxonomy, missing research, and evidence that a classification is wrong are all welcome — see [CONTRIBUTING.md](CONTRIBUTING.md). Taxonomy changes are deliberate: try aliases, then multi-tagging, then a cross-link, and only then propose a new topic.

## License

Content and data are [CC BY 4.0](LICENSE). Code in `src/` is additionally available under MIT.
