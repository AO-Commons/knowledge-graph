# Lexical classification baseline — 2026-08-13

The measurement the brief asks for before adding embeddings: *"optional
pgvector only if measured retrieval quality improves."* This is the number
that has to be beaten.

## Method

BM25 over the 567 taxonomy topics. Each topic's document is its title, its
ancestors' titles, its aliases, and its unnumbered subpoints. Queries are a
resource's title, description, and abstract. No embeddings, no vector store.

Scored against the 59 hand-tagged records, hierarchy-aware: predicting `2.2.2`
where the tag says `2.2` counts as correct, since it is the same branch and
more specific.

## Results

| | gold tags recovered | records with ≥1 correct |
|---|---|---|
| classify, `min_score=4, limit=6` | 32% | 59% |
| retrieval top-10 | 40% | 71% |
| retrieval top-15 | 44% | 78% |
| retrieval top-25 | 54% | 83% |
| retrieval top-40 | 62% | 88% |

Abstracts roughly double it: 39% with, 18% on titles alone. Only 42 of 59
records have an abstract, which is the same arXiv gap that limits references.

## What this says

**Lexical alone will not scale the tagging.** A two-stage design — cheap
retrieval narrows 567 topics to a shortlist, then a model picks from it —
needs recall around 80% at k≈25 before the second stage can be trusted. 54%
means the model cannot recover what retrieval missed, and the missing half
would be invisible.

So there is now an evidence-based case for embeddings, which is what the brief
wanted before spending that complexity. The cheapest experiment that would
settle it: embed topic documents and resource abstracts, measure the same
recall@25, and keep whichever wins.

## The caveat that matters most

**The gold set is not gold.** All 59 records are `review_status: unreviewed`
and their tags are my own first pass. A 32% agreement could mean the
classifier is wrong, or that the hand tags are wrong, or both — this measures
similarity-to-me, not accuracy.

Nothing here should be quoted as classifier accuracy until a reviewed subset
exists. Building one is cheap and worth doing before tuning anything: fifty
records, tagged carefully by someone who knows the taxonomy, would turn every
number above into something that can be trusted.
