# CLAUDE.md — AO Commons Knowledge Graph

A map of research on **agentic organizations**: organizations in which machine agents hold operational or decision authority. This repository is public.

## What this is for

A researcher — human or agent — should reach the right small set of primary sources faster and more cheaply than by searching the web. The graph helps decide *what to read*. It never replaces the source.

Judge every proposed change against that. A feature that makes the graph more elegant without making a real research question cheaper to answer is not an improvement.

## The taxonomy is the source of truth

[`taxonomy/agentic-org-research-library-taxonomy-v3.md`](taxonomy/agentic-org-research-library-taxonomy-v3.md) is authoritative. Do not invent a parallel taxonomy, do not collapse it into generic AI categories, and do not renumber existing codes — a code is a stable identifier and old tags must stay resolvable.

Three structures, implemented differently:

1. **Numbered hierarchy** — navigation topics. The code *is* the hierarchy; `2.2.1`'s parent is `2.2` regardless of indentation.
2. **Section 11** — a failure coding scheme, `usage_mode: coding_scheme`. Multi-tagging is normal; an incident carries several codes.
3. **F1–F12** — flat facets on a resource. Never turn them into a second tree.

When the corpus reveals a gap: try aliases, then multi-tagging across existing topics, then a cross-link, and only then propose a new topic. **Never expand the taxonomy because a model invented a concept.**

## Enforce the scope test

> An item belongs if it would change how you design, operate, oversee, or hold accountable an organization where agents act with real authority.

Material about human collective governance that is unchanged by the presence of machine agents does not belong, however good it is. The taxonomy's exclusion register is binding: when ingestion proposes an excluded resource, it must state what changes *because machine agents hold authority*.

Section 15 is intentionally shallow. It points into adjacent mature fields — organizational theory, zero-trust security, aviation safety, corporate law — rather than ingesting them. Mark those resources as borrowed background.

## Provenance is the product

Every non-deterministic edge records how it was made. `CITES` from scholarly metadata and `RELATED_TO` from a model are different claims and must never look alike:

- deterministic (`CITES`, `PARENT_OF`) — no confidence class; adding one implies a judgement nobody made
- computed (`SIMILAR_TO`) — always a named `method` and a `score`; a hidden method makes a score uninterpretable
- extracted or inferred — `confidence_class` plus the source text

If you cannot say where an edge came from, do not add the edge.

## Keep it small

Three node families: Resource, Topic, Entity. One generic Entity with an `entity_type`, not a node family per concept. A dozen relationship types, not fifty. SQLite or Postgres, not a graph database. No vector store unless measurement shows it improves retrieval.

Do not build in V1: a universal ontology, claim/warrant graphs, reputation systems, a custom graph or vector database, a general research agent, or full-text ingestion of whole corpora.

Prefer deleting complexity over preserving an elegant architecture.

## Cost discipline

Graph first, source second. For an ordinary query: search the taxonomy and graph, return compact metadata, identify 5–15 candidate sources, and only then fetch text for those. Never send the corpus to a model. Cache metadata, classifications, similarity, and extractions.

MCP tools return compact structured records — enough for an agent to decide what deserves deeper reading, not the papers themselves.

## Conventions

- Python ≥3.11, standard library by default. A new dependency needs a reason.
- Releases are reproducible: no clock reads, no random ordering. `built_at` is injected, never read from the system.
- Tests live in `tests/` and run with `pytest`. The taxonomy tests run against the **real** v3 file, not only the fixture — a parser that works on a tidied sample and not on the source would be worse than none.
- Dates in ISO format. Prose in the docs is direct and unhyped; this is a research artifact.

## Public repository

git history is public. No internal strategy, no CRM references, no unannounced work. The taxonomy and the graph are the public artifacts; deliberation about them belongs in the private `internal` repo.
