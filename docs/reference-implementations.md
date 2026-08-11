# What we take from the reference implementations

The build brief names four references. This records what each one actually settled, and — more usefully — where we deliberately diverge.

## Learning Commons

[docs.learningcommons.org](https://docs.learningcommons.org/) · [knowledge-graph repo](https://github.com/learning-commons-org/knowledge-graph)

**The closest reference for shape and simplicity**, and the one worth reading before making a structural decision.

Worth knowing before you copy the repo: **their public repository is not the implementation.** Its entire tree is a README, a LICENSE, and `tutorials/`. The engine, REST API, GraphQL API, and MCP server are closed and in private beta; only the JSONL exports are public. What is mimicable is the *org layout* — one repo per product — and the *distribution model*.

Adopted:

- **`nodes.jsonl` + `relationships.jsonl` as the portable release.** The export is a product, not a dump. Someone should be able to load it into a graph database, or into Postgres, or just grep it, without running any of our code.
- **Complementary access surfaces.** Local download, REST, and MCP answer different needs; local files are the one that works with no account and no network.
- **Stable IDs independent of the database.** `topic:2.2.2` means the same thing in every release and in anyone's copy.
- **Attribution and licensing on graph objects, not only on the release.** Their relationships carry `author`, `provider`, `attributionStatement`, and `license`. A consumer who lifts a dozen edges into their own graph never sees our `metadata.json`, so imported edges carry an `attribution` of their own.
- **A documented relationship reference and controlled-vocabulary page.** Their "all relationships" and "value and format standards" pages are the model for [data-model.md](data-model.md) and [`facets.py`](../src/ao_commons_kg/facets.py).

Not adopted:

- **Their education ontology**, obviously — standards, learning components, progressions. The brief is explicit about this and it is worth restating, because the temptation is to reach for their entity names when ours feel unfinished.
- **Their relationship metadata as sufficient.** LC edges record authorship and licensing but carry **no confidence class and no method**. That works when every edge is curated by domain experts. Ours are not: a citation read from OpenAlex, a similarity computed from bibliographic coupling, and a relationship a model inferred from a paragraph are three different kinds of claim, and flattening them would make the graph impossible to audit. See Graphify below.

## Connected Papers

[connectedpapers.com/about](https://www.connectedpapers.com/about)

The discovery idea, not the service — we depend on none of their infrastructure.

The useful insight is that **direct citation is a poor similarity measure**. Two papers that never cite each other can be closely related, and bibliographic coupling (shared references) plus co-citation (shared citers) find those where a citation graph walk will not. Both are computable from the scholarly metadata we already import.

The other borrowed idea is scope: expand a seed paper into a *manageable neighborhood*, not a search result. We compute similarity inside the curated corpus plus a candidate ring around it, never over the global scholarly graph.

## Graphify

[Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify)

A design reference and a candidate component to benchmark — **not** the canonical schema, and not a dependency until a spike shows it beats the simple in-house path.

Adopted wholesale: the **`EXTRACTED` / `INFERRED` / `AMBIGUOUS` distinction**. It is the single most important thing in the edge model. Every non-deterministic edge declares which it is and where it came from, and the schema refuses to construct one that cannot. This is the gap in the LC model, and closing it is what makes the graph checkable by someone who doubts a specific claim.

Also adopted: a small extraction contract (`{nodes, edges}`), scoped queries over repeated corpus reads, incremental processing keyed on content hashes, and the advice to avoid a vector database until it demonstrably improves the workload.

## OpenAlex

[developers.openalex.org](https://developers.openalex.org/)

The default scholarly backbone: paper identity, DOI resolution, references, citations, open-access status, retraction metadata.

The rule is to **store the AO Commons subset, not rebuild a global index**. OpenAlex answers "what is this paper and what does it cite"; the taxonomy and scope test answer "does it belong here", and the second question is the one that keeps the graph small enough to be worth querying.

Citations imported from OpenAlex are deterministic — they carry no confidence class, and an `attribution` naming the source.

## Ai2 Asta / Semantic Scholar

[allenai.org/asta/resources](https://allenai.org/asta/resources)

An optional connector and, more valuably, a **benchmark**: baseline B in [the evaluation set](../evals/README.md) is a frontier model querying a strong general scientific retrieval system directly. If AO Commons cannot beat that on AO research questions, the curation is not earning its keep.
