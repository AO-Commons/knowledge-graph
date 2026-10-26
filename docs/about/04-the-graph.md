---
id: graph
title: Nodes and edges
order: 4
---

Eight kinds of node and the edges between them. Everything is a file in git —
there is no database, which is what makes a change reviewable as a diff and a
release reproducible byte for byte.

```
                  ┌── TAGGED_WITH ──▶ Concept ──┐
                  │                             │
   Resource ──── MAKES_CLAIM ──▶ Statement      │
      │  ▲                          │           │
      │  │                          ADDRESSES   │
   AUTHORED                         ▼           │
      │  │                       Question       │
   Person ── AFFILIATED_WITH ──▶ Organization   │
                                                ▼
   Resource ──────────── ABOUT ──────────────▶ Topic
```

| Node | Is | Where it lives |
| --- | --- | --- |
| Resource | a paper, a tool, or a deployment | `data/resources/` |
| Statement | one assertion, with the quote it came from | `data/claims/` |
| Question | an open question several statements are asking, {{questions}} of them | `data/questions.yml` |
| Concept | a tag fine enough to propose a pair worth reading together | `taxonomy/concepts-extra.yml` |
| Topic | a category in the taxonomy, {{topics}} of them | `taxonomy/` |
| Person | an author, one spelling per person | derived from bylines |
| Organization | a university, lab, company or agency, with a city | `data/organizations/` |

| Edge | Runs between | Made by |
| --- | --- | --- |
| `MAKES_CLAIM` | a resource and its statements | extraction |
| `TAGGED_WITH` | a statement and a concept | extraction, checked at review |
| `ABOUT` | a resource and a topic | computed from its statements' concepts |
| `ADDRESSES` | a statement and an open question | a person, with reasoning |
| `CITES` | two resources we both hold | OpenAlex and Semantic Scholar |
| `SUPPORTS` | two statements | a person, with reasoning |
| `DISAGREES_WITH` | two statements | a person, with reasoning |
| `QUALIFIES` | two statements | a person, with reasoning |
| `EXTENDS_CLAIM` | two statements | a person, with reasoning |
| `SIMILAR_TO` | two resources | bibliographic coupling |
| `AUTHORED` | a person and a record they wrote | the byline |
| `AFFILIATED_WITH` | a person and an organization | the record's affiliation data |

The four statement-to-statement names are CiTO's (Shotton, 2010) and
`ADDRESSES` is [MIRA](https://github.com/MIRA-science/schema)'s, so they mean
to an outside reader what they mean here. Each is marked inferred and carries a reason. No source states that two claims
disagree, and one drafted by a model says so, so it can never be read as a
person's judgment.

`AUTHORED` and `AFFILIATED_WITH` are the opposite kind of edge: both are read
off what a record already says, so neither is an inference and neither carries
reasoning. An affiliation runs from the person rather than from the paper,
because that is whose it is — and because the same researcher at two
institutions on two papers is a fact a paper-level edge cannot hold.

People are derived rather than filed. There are over two thousand of them and
nearly all are a name on one paper, so a file each would hold nothing a reader
could not get from the byline. What is filed is the overlay in `data/people/`:
which account belongs to whom, and what stands behind the claim. Organizations
are the other way round — one file each, because `kind` and `roles` are
judgments a registry cannot make.
