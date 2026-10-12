---
id: graph
title: Nodes and edges
kicker: how the graph fits together
order: 4
---

Six kinds of node and the edges between them. Everything is a file in git —
there is no database, which is what makes a change reviewable as a diff and a
release reproducible byte for byte.

| Node | Is | Where it lives |
| --- | --- | --- |
| Resource | a paper, a tool, or a deployment | `data/resources/` |
| Statement | one assertion, with the quote it came from | `data/claims/` |
| Question | an open question several statements are asking, {{questions}} of them | `data/questions.yml` |
| Concept | a tag fine enough to propose a pair worth reading together | `taxonomy/concepts-extra.yml` |
| Topic | a category in the taxonomy, {{topics}} of them | `taxonomy/` |
| Person | an author, one spelling per person | derived from bylines |

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

The four statement-to-statement names are CiTO's (Shotton, 2010) and
`ADDRESSES` is MIRA's, so they mean to an outside reader what they mean here.
Every one is marked inferred and carries a reason — no source states that two
claims disagree, or that one paper's open question is an instance of another's
— and one drafted by a model says so, and can never be read as a person's
judgment.
