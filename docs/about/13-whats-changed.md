---
id: changes
title: Changelog
order: 13
---

**29 October 2026. Fifteen papers read.**

- {{claims}} claims, up from 112. The fifteen are the ones a foundational
  bibliography names and the library already held without having read: the
  collusion papers, the multi-agent security work, the workplace and market
  benchmarks, the economics of agent firms.
- {{questions}} open questions, up from four. One is now asked by six papers
  that share no author, all arriving at the same missing instrument: how to
  evaluate a system of agents rather than the agents in it.
- **A record says what it does here**, not only what it is about — where a
  term comes from, what claims are measured against, what somebody ran. A
  judgment about this library rather than a property of the work.
- The economics and law the field borrows its vocabulary from are held at
  last, as pointed-at background. Coase, Williamson, Aghion and Tirole and
  twelve others: cited, not ingested, and not read.
- Two things the reading broke and fixed. The helper that says how much a
  claim is worth was being used to choose what to read, which skipped the
  sections modern papers name after what they found. And the review queue
  sorted by how many tags a pair shared before sorting by the tag, which
  split each concept across the queue.

**Late October 2026. The ecosystem, and a shared vocabulary.**

- Every release now carries the whole corpus as a **MIRA** graph, validated
  against MIRA's own generated shapes on every build. Two of its names were
  already in use here; the rest of the projection followed.
- **Organizations are nodes**, with a city, a kind and the roles they play
  here. They were strings on a record until now, pointing at nothing.
- **People are nodes too**, derived from bylines rather than filed, with
  `data/people/` as the overlay that carries the judgments.
- Two edges that are read rather than inferred: a person authored a record,
  and a person was at an organization.
- A fold that deleted hyphens instead of treating them as spaces had been
  carrying two researchers as four.

**Late October 2026. The ask log goes public.**

- A question put to the library appears on a public list under the name of
  whoever asked it, and anyone can second it. Nothing asked before this was
  published, and nothing retroactively can be.
- Five gates decide what goes on that list, written up in the contributor
  documentation. Four of them cost nothing, because answering already works
  them out; the fourth is a judge of its own.
- An answer can be judged, in six specific ways rather than with a rating, and
  each judgment becomes an issue against the claim it disputes.
- One of those six files a paper the library was missing. When that paper is
  read, the question offers to ask itself again; the original answer is never
  rewritten.
- Contributions are posted under the contributor's own GitHub account rather
  than the app's, so they land in their own history.
- Credit can now be earned back as well as spent, capped at what was spent, so
  a good question with good feedback costs its author nothing.

**October 2026. Questions, and a guide that covers both surfaces.**

- Gap claims cluster into **questions**, the layer the roadmap had carried
  for months under MIRA's names. Seven gaps from four papers make four
  questions, and exactly one is asked by more than one paper.
- Papers and occurrences are counted apart, because a question two papers ask
  is a claim about a field and a question one paper asks twice is that
  paper's framing.
- `aokg questions --propose` proposes candidate questions from concepts, and
  never admits — the rule the scout already follows for papers.
- This documentation moved out of the site's JavaScript and into markdown
  here, so one set of words serves the repository and the app.

**September 2026. Claims become the main character.**

- Papers stopped being the unit. Tags moved onto claims, and a paper's
  categories are now computed from them.
- Extraction became a process with five gates, and the first six papers were
  re-read under it.
- The vocabulary was rebuilt bottom-up: a term is in it because a claim
  needed it. The taxonomy's subpoints became a suggestion pool.
- Citation expansion walks both directions, with a rising threshold, a model
  scope scan, and a hard budget — no human in the loop.
- The review screen became one question per claim, with add, adjust and
  remove, and adjustments that carry the reviewer's wording into the corpus.
- A verdict binds to the wording it was given. An id outlives the sentence
  under it, so a verdict from August could otherwise land on a sentence
  written in November.
- Machine-checked sits between unreviewed and reviewed: the quote has been
  verified verbatim against its source, which is real and is not review.

**August 2026. The corpus and the surfaces.**

- The filing site, with filings becoming pull requests so the audit trail is
  the pull request list.
- The graph in three dimensions, people included.
- A read-only MCP server, so an assistant can query the corpus.
- The scholarly pipeline: resolve, expand, and citation edges.
- The taxonomy's leaf layer demoted to notes — 568 codes became {{topics}}.

**Earlier. Foundations.**

- The taxonomy, the data model, and portable releases.
- Tooling folded in as resources with their own profile.
