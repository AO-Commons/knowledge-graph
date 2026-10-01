# Concepts, definitions and entities

**Status:** the `definition` statement type is built. Entities are a proposal,
not yet built. Argued here because one paper showed all three problems at once.

## What one paper showed

Building the Loop (Rennie et al., EPIC 2025) introduces two terms, Artificial
Organizational Intelligence and "building the loop", and builds on a system,
BlockScience's Knowledge Organization Infrastructure (KOI). Its statements had
handled all three with the two tools available, a concept tag and a statement
type, and got each one wrong in a different way:

- **The definition of AOI was typed `method`.** It is a technique only in the
  sense that every new term is a new thing.
- **KOI was typed `method` and tagged `shared-schemas-for-agentic-organization-data`.**
  It is not the paper's method, because the paper credits it to BlockScience.
  The tag says the opposite of the statement, since KOI's point is joining
  systems without a shared schema.
- **One concept carried ten of eleven statements**, so it told them apart from
  nothing and connected them to nothing. It was also filed under 2.4, graduated
  autonomy, which the paper does not discuss.

Each failure has the same cause: three different kinds of thing were forced
through one slot.

| Kind | What it is | Example | Where it lives |
|---|---|---|---|
| Concept | An idea another paper could hold under another name | AOI, building the loop | `concept_tags`, the vocabulary |
| Definition | The statement where a paper fixes what a term means | "We introduce AOI: the capacity for ..." | a statement typed `definition` |
| Entity | A named thing that exists, which you could link to | KOI, Telescope, BlockScience, a particular DAO | `entity_ids`, once built |

## Definitions (built)

**The evidence is corpus-wide, not one paper's.** Of the six statements typed
`method`, three defined a term or listed a typology:

- Building the Loop's definition of AOI
- "A dynamic evaluation is one whose test distribution depends on the
  evaluated policy" (`arxiv:2606.03237:5`)
- the six trust models of `arxiv:2511.03434:3`

Both concepts that a paper coined for itself had their defining statement
typed `method`. A fourth definition, Building the Loop's sharpest one, was
typed `position`.

**Where the lines are.**
- **Against `method`:** a method is how something is done, and a definition
  is what a word means.
- **Against `position`:** a definition stipulates. "AOI is not about replacing
  organizations with AI" sounds like an argument and is scoping a term.

**Tag a definition with the concept it defines.** That is the whole join, and
it needs no new field. "Who coined this term, and what did they mean by it?" is
answered by the definition statements carrying the tag. A later paper that
redefines the term carries the same tag, and the two definitions become a
`QUALIFIES` or `DISAGREES_WITH` pair.

**Not primary.** Nobody comes to the library for what a word means in place of
what has been shown about it. Definitions are not proposed for linking yet.
The first time two papers define one concept, proposing that pair is the
obvious next step, and it is not worth building before then.

### What was retyped, and what was left for a person

- **Building the Loop:** three definitions retyped. Its KOI statement became
  `background`, attributed to BlockScience.
- **`arxiv:2606.03237:5` (dynamic evaluation): left as a method on purpose.**
  It is a definition. The paper argues that no existing evaluation meets the
  requirements for dynamic evaluation, and it never performs one. But it is
  the method statement behind this library's flagship joined query: what has
  been found about the train-test-deploy gap by people doing dynamic
  evaluation. That query answers only because a definition is filed as a
  method. Retyping it would correctly make the example return nothing, and
  the example, its test and the MCP docstring would have to change with it.
  That is a judgment about what the flagship query should demonstrate, so it
  is a person's call.
- **`arxiv:2511.03434:3` (six trust models): borderline.** A comparative
  typology can be the framework a paper works through, which is method-shaped.
  It is left as a method until reviewed.

## Entities (proposal)

**Why not make them concepts.** It would be tempting to let the concept layer
cover technologies and real organizations too. It should not, for two reasons:

- **The safeguard doesn't fit.** The one check a concept has is the collision
  check: is this already here under another name? That is the right question
  for an idea and a meaningless one for a proper noun.
- **The fields don't fit.** A named thing needs aliases (KOI, KOI-net,
  Knowledge Organization Infrastructure) and identifiers (a repository, a
  specification, a website). A concept has neither field, and adding them
  would make every concept carry fields that only proper nouns use.

**The slot already exists.** The data model has had one generic `Entity`
since the start, with an `entity_type` drawn from approach, method,
implementation, framework, model, benchmark, dataset, organization, standard
and system. `Claim.entity_ids` exists too. Nothing has used either.

**What building it takes.** A small amount, and all of it follows existing
patterns:

1. `data/entities/<slug>.yml`, one file per entity, with `entity_type`,
   `name`, `aliases`, `external_ids` and `source_provenance`.
2. A loader that fails loudly when a statement's `entity_ids` do not resolve,
   as concept tags do. An id pointing at nothing is an edge with no end.
3. Entities emitted in the release as `kind: entity`, which the data model
   already lists.
4. The drafting model asked to name the systems and organizations a statement is
   about, checked against the entity list the way tags are checked against the
   vocabulary.

**The first entities, from this paper.**

| Entity | Type |
|---|---|
| KOI | `standard` (a protocol) |
| Telescope | `system` |
| BlockScience | `organization` |
| Metagov | `organization` |
| ADM+S, the Australian research center the five academic authors belong to | `organization` |

A particular autonomous organization studied by a paper would be an
`organization` in the same way.

**Layering needs no new edge.** "This concept is realized by that technology,
which this organization runs" is carried by statements, not by edges between
concepts and entities. Concepts are a vocabulary, not nodes.
`claim:doi:10-1111-epic-70009:19` argues that KOI is one architecture that
makes AOI possible. Once it carries `entity_ids: [koi]` beside its AOI tag,
the joins answer the questions directly:

- "What implements AOI?" means statements tagged AOI that carry a system or
  standard entity.
- "Who runs KOI?" means statements carrying KOI and an organization entity.

If a query ever needs a direct edge, `IMPLEMENTS` between two entities is
already in the edge list.

**Deliberately absent.** No node family per entity type, no reputation or
scoring of entities, and no entity created because a paper mentioned a name in
passing. An entity enters when a statement is about it, the same rule that
admits a concept.
