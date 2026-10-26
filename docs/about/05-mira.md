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
   Claim  position ───────────────▶ Claim
          evidence ───────────────▶ Evidence ──▶ sourceDocument
          protocol ───────────────▶ Protocol
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

## Vocabulary

Where MIRA has a word for something, it is the word used here — in the data,
in the code and in this documentation. Until 2026-10-26 three of them were
ours: a claim was a *claim*, an `evidence` claim was a *finding*, a
`protocol` claim was a *method*. Three names for things a shared schema had
already named meant every reader arriving from MIRA had to learn a second
vocabulary to read a corpus published in their first.

| Here | In MIRA | |
| --- | --- | --- |
| Claim | `Claim`, `Evidence` or `Protocol` | the kind picks one: an `evidence` claim projects to Evidence, a `protocol` claim to Protocol, the rest to Claim |
| Resource | `SourceDocument` | ours also holds tools and deployments, which are not documents |
| `DISAGREES_WITH` | `opposes` | ours is CiTO's name for it; both are shared vocabularies and we took the other one |
| Question, `ADDRESSES` | `Question`, `addresses` | already the same, because these came from MIRA |

Two differences are left and both are deliberate. A Resource is wider than a
SourceDocument, because a benchmark suite is not a document. `DISAGREES_WITH`
is CiTO's name, kept because the three relations beside it are CiTO's too and
a set drawn from one vocabulary beats a set drawn from two.

`protocol` reads oddly on a claim pulled from a Methods section — it is
bench-science vocabulary, and the corpus is not bench science. That is the
price of speaking one language instead of two, and it is worth paying.

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
- **The edge from a paper to a claim.** MIRA routes a document to a claim
  through a Study and its Evidence, which is right when you ran the work and
  impossible when you read somebody else's. Only an `evidence` claim can state its
  source outright, because Evidence is the one class with a slot for it.
- **Who checked a claim, and whose result it is.** No slot for either.

That list is the point of publishing at all. It is the evidence for what a
shared schema would need to carry a corpus built by reading other people's
papers, and it is written to be read by the people who maintain MIRA. If the
number stops falling, the integration is nominal and this page should say so
rather than claim compatibility.

## Why a shared vocabulary at all

Borrowed names cost nothing while a layer is young: MIRA's for questions,
CiTO's for the relations between claims. A reader arriving from another
project already knows what the edge asserts.

Where no shared name exists, this corpus keeps its own and says so, which is
a proposal rather than a fork.
