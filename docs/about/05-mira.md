---
id: mira
title: Published as MIRA
order: 5
---

Every release carries `graph.mira.jsonld`: the whole corpus written in
[MIRA](https://github.com/MIRA-science/schema), an open schema for research
graphs — questions, the claims that address them, and the evidence behind
each.

Two of its names were here first. `Question` and `addresses` are MIRA's,
adopted while that layer was still a sketch. Taking somebody else's word for
something not yet built costs nothing, and means an outside reader already
knows what the edge asserts.

```
   this corpus                      MIRA

   Resource (paper) ──────────────▶ SourceDocument
   Statement  position ──────────▶ Claim
              finding  ──────────▶ Evidence ──▶ sourceDocument
              method   ──────────▶ Protocol
   Question ──────────────────────▶ Question
   quote ─────────────────────────▶ Item in the paper's Container

   Topic · Concept · Organization · Person          no class
   CITES · SIMILAR_TO · TAGGED_WITH · ABOUT         no relation
   MAKES_CLAIM · AUTHORED · AFFILIATED_WITH         no relation
```

**It is checked, not claimed.** MIRA generates SHACL shapes from its own
source, and every build validates the projection against a copy of them
pinned by commit. The result is in each release, and a reader can run the
same check without asking us anything:

```sh
python3 -m pip install '.[mira]'
python3 scripts/validate_mira.py data/releases/v0.11.0
```

## What it carries, and what it cannot

A projection, not a replacement. The JSONL files stay exactly as they are,
and `models.py` is still where meaning is argued. MIRA is a second output of
the same build, and deleting it would change nothing else.

It also cannot yet say most of what this corpus knows. Every release ships
`mira-report.json`, which counts and names what did not fit rather than
dropping it quietly:

- **The taxonomy and the concepts.** MIRA has no class for either.
- **Organizations.** No class, and nothing tying one to a document, so an
  ecosystem map cannot be expressed at all.
- **Tools and deployments.** `SourceDocument` means a paper, a book or a
  report. Calling a running deployment one would be false in the data.
- **The edge from a paper to a statement.** MIRA routes a document to a claim
  through a Study and its Evidence, which is right when you ran the work and
  impossible when you read somebody else's. Only a `finding` can state its
  source outright, because Evidence is the one class with a slot for it.
- **Who checked a statement, and whose result it is.** No slot for either.

That list is the point of publishing at all. It is the evidence for what a
shared schema would need to carry a corpus built by reading other people's
papers, and it is written to be read by the people who maintain MIRA. If the
number stops falling, the integration is nominal and this page should say so
rather than claim compatibility.

## Why a shared vocabulary at all

A graph nobody else can read is a private database with extra steps. Borrowed
names cost nothing while a layer is young: MIRA's for questions, CiTO's for
the relations between claims.

Where no shared name exists, this corpus keeps its own and says so, which is
a proposal rather than a fork.
