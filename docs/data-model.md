# Data model

Three node families, a dozen edge types, and a rule that every edge can say where it came from. That is the whole model, and keeping it that small is a design goal rather than a stage we intend to grow out of.

## Nodes

### Topic

One node of the taxonomy. `code` is the identifier and the hierarchy at once: `2.2.1`'s parent is `2.2`, derived rather than stored, so the tree cannot disagree with the codes. Passing a `parent_code` that contradicts the code is an error.

`usage_mode` is `navigation` for most topics and `coding_scheme` for Section 11, where multi-tagging is the norm rather than the exception.

`subpoints` holds unnumbered bullets that sit under a numbered topic in the source file. They carry no codes — inventing some would break the promise that codes are stable identifiers — but they are often the most specific phrasing available, so they travel with their parent.

### Resource

Anything a researcher might read or use: paper, preprint, report, standard, repository, tool, dataset, postmortem, incident, regulation. Identity comes from external identifiers wherever possible (`doi`, `openalex_id`, `arxiv_id`) so records can be reconciled against upstream sources.

`taxonomy_topics` holds topic codes; `facets` holds F1–F12 values, validated against their controlled vocabularies on construction. An unknown facet value is an error rather than a warning: a typo that passes silently produces a resource no filter will ever match, which is worse than one that fails to load.

`is_borrowed_background` marks Section 15 material — relevant by transfer rather than about agentic organizations directly — so it can be excluded from counts that claim to measure the field's own literature.

### Entity

Approaches, methods, implementations, benchmarks, systems. **One** generic type with an `entity_type` field, not a node family per concept. The distinctions matter for display and filtering, not for storage, and a schema per concept is a cost paid on every future change.

## Edges

| Relation | Kind | Requires |
|---|---|---|
| `CITES`, `PARENT_OF` | Deterministic | Nothing — read from structured metadata |
| `SIMILAR_TO` | Computed | `method` and `score` |
| `TAGGED_WITH`, `DISCUSSES`, `PROPOSES`, `EVALUATES`, `IMPLEMENTS`, `DESCRIBES_FAILURE_OF`, `BELONGS_TO_TOPIC`, `RELATED_TO`, `EXTENDS` | Extracted or inferred | `confidence_class`, plus provenance |

`confidence_class` is one of `EXTRACTED`, `INFERRED`, `AMBIGUOUS` — the distinction Graphify makes, and the reason a reader can trust the graph at all. Attaching one to a `CITES` edge is an error: it implies a judgement that was never made.

`SIMILAR_TO` must name its method (`bibliographic-coupling`, `co-citation`, …). A similarity score whose method is hidden cannot be interpreted or reproduced, and hiding it would make the discovery layer unfalsifiable.

## Releases

```
data/releases/<version>/
├── nodes.jsonl           {"kind": "topic"|"resource"|"entity", ...}
├── relationships.jsonl
├── taxonomy.json         the tree alone, for consumers who only want to browse
├── metadata.json         counts, relation and confidence breakdowns, license
└── checksums.txt
```

Reproducible by construction: nodes sort by `(kind, id)`, edges by `(relation, source, target)`, empty values are omitted, and no clock is read unless `built_at` is passed in. Rebuilding from unchanged inputs produces identical bytes — otherwise the checksums would be decoration and release diffs unreadable.

The export exists so the data is usable without our infrastructure. That is the part of Learning Commons' model worth copying: the JSONL is a product, not a dump.

## What is deliberately absent

No claim or argument nodes, no author or venue nodes, no reputation scores, no vector index. Each would be defensible; none is needed to answer the questions in the evaluation set, and every node family is a permanent cost. Add one when a real query cannot be answered without it.
