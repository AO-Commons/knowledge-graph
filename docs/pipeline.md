# The pipeline, stage by stage

What happens to a paper between arriving and being citable, who or what does
each part, and what it costs.

Stages marked **live** run today. Stages marked **proposed** are argued in
[statements-first.md](statements-first.md) and not built. Coverage figures are
measured, not estimated, and are the honest answer to "how far does this
actually go" — the scaffolding is complete and thins sharply toward the top.

```
                                            coverage today
  1  INTAKE          three doors                101 records
  2  RESOLUTION      metadata, references        45 with references
  3  ADMISSION       scope, duplicates          automatic since 10 Sep
  4  EXTRACTION      statements out of text       6 records · proposed as process
  5  TAGGING         concepts on statements      40 of 40 statements
  6  LINKING         relations between them      12 relations
  7  FILING          categories, derived          6 derived · 73 legacy hand-filed
  8  REVIEW          a person decides             0 reviewed
  9  RELEASE         a fixed, citable version     3 releases
```

**Filing moved.** It used to sit at stage 4, before extraction, and it is now
stage 7 and mostly computed. Asking somebody to name what a paper is "about"
before anything has said what it contains is the wrong question in the wrong
order — which is why two thirds of the filed records carry more than one code
and 28 carry none at all. See [statements-first.md](statements-first.md).

---

## 1 · Intake — three doors, one destination

Every path ends in one YAML file per record under `data/resources/`, and each
records which door it came through in `source_provenance`. That field is the
difference between a claim somebody checked and one a crawler proposed, and
it is never inferred or defaulted.

| Door | For | Run by | Gate |
|---|---|---|---|
| **Add tab** | one paper | a person, via a prefilled issue | none — lands `unreviewed` |
| **`bulk_add.py`** | a reading list | a contributor, opens a PR | PR review |
| **`aokg grow`** | the citation graph | Tuesday cron | threshold + scope scan |

**Add tab** → issue labeled `new-resource` → `new-resource.yml` runs
`add_resource.py` → commits to main → asks Pages to rebuild. No maintainer in
the loop, on a blast-radius argument: a new record changes no existing
judgment and no measured number, and `git revert` undoes it completely.

**Bulk** is the one-at-a-time path in a loop, deliberately — same resolution,
same duplicate check, same refusal to file a paper nothing can resolve. A bulk
path with looser rules is how a corpus fills with near-duplicates.

**Growth** is covered in stage 3.

*Proposed:* a browser extension, so adding from an arXiv or DOI page is one
click. Cheap — it is the Add tab's POST with a button in front of it — and the
right place to reduce friction, because adding is self-interested and needs no
other incentive.

---

## 2 · Resolution — what the record knows

Three sources, asked in order, each covering the others' blind spot.

| Source | Gives | Why it is in the order it is |
|---|---|---|
| **OpenAlex** | identity, citation counts, institutions, references | the backbone |
| **Semantic Scholar** | abstracts and references for preprints | OpenAlex has no references for preprints — the whole reason this connector exists |
| **arXiv** | the byline | **last and decisive** for a preprint: the submission itself, not an index's guess |

Reference lists go to `data/scholarly/references.jsonl`, keyed by our resource
id under a canonical key so the sources meet. They are not inlined into the
record — a hundred identifiers in a file a person is meant to hand-correct is
a poor trade.

Per-author affiliations are kept paired (`Resource.affiliations`), not
flattened into two lists. Organization names fold only on the country suffix:
`Google (United States)` and `Google (United Kingdom)` are one company,
`Google DeepMind` is not Google, and anything ambiguous is reported rather
than merged.

A fetched work is checked against the record before its metadata is written.
An identifier can be wrong — one record in this corpus was filed under a DOI
belonging to a different paper, and a backfill that trusted it wrote a
stranger's institution onto it.

```bash
aokg resolve --source semanticscholar --refresh
```

**Coverage: 45 of 101.** The rest are records the indexes do not carry
references for, mostly tools and recent DOIs.

---

## 3 · Admission — the only automatic gate

Runs Tuesdays. Three filters in cost order, because the cheap one removes 93%
before the expensive one sees anything.

**Both directions.** Backward: works our papers cite, free from the reference
store. Forward: works that cite ours, a query per held record. The forward
half is not an optimization — it is the only route by which recent research
can be reached at all. A paper published last month has been cited by nobody
and can never clear a backward threshold however plainly it belongs; it can
cite three of ours on the day it appears. Both count the same toward support.

Measured on the corpus with a window back to January 2025: 687 forward
candidates, 38 clearing the threshold, the newest published three weeks ago
and reachable no other way.

**A rising threshold.** Generation 1 needs 2 held papers connected to it,
generation 2 needs 3, each hop from a human judgment strictly harder. This is
a brake, not a termination proof — a famous enough work clears any bar.

**A scope scan.** A model reads the abstract against the scope test and the
exclusion register, and must state what changes *because machine agents hold
authority*. Not the keyword score, which the README already records as having
a ceiling. A scan that errors refuses; "the API was down so everything got in"
is the drift this prevents.

**A budget.** 40 per run, deferring the rest — the hard bound.

Then the same duplicate check the human paths run, but stricter: they warn a
person who decides, this one has nobody to warn, so a likely duplicate is
skipped and remembered.

Refusals are written down with their reasoning, so a verdict that flips
between runs is visible rather than invisible.

> Admitting everything cited measures out at ~4,900 records, 93% cited by
> exactly one of ours. Narrow scope is why 101 curated records beat 8,500.

---

## 4 · Extraction — proposed as a process

**This is the stage that decides whether statements can carry the library, and
it is currently not a process.** 40 claims, six papers, one model, one
afternoon, three passes over full text, never measured.

What it produces per statement: `text` (the paraphrase), `quote` (verbatim
source), `standalone` (enough context to judge it cold), a type, the section it
came from, and the extraction method.

What it has to become:

1. **A stated unit.** One assertion, one subject — SciFact's criteria, which
   the model already cites in a docstring and should enforce as a contract.
2. **A waste rule.** Five of the first 45 were artifact trivia — *"contains
   more than 80 scenarios"* — useful for reproduction, useless for "who has
   already said X". 11% waste, found only because a person reread them.
3. **Attribution asked at extraction, not found later.** Five of 40 were the
   paper reporting prior work. Without that axis, "who has already said X"
   returns the most recent repeater.
4. **Yield calibration.** 14 claims from Melting Pot and 4 from Building the
   Loop tracked how much methods detail each had, not how much each
   contributed.
5. **A measurement.** Until extraction has an accuracy number against the gold
   set, "statements are first class" is an aspiration with 40 examples.

**The bind:** ~7 judgments per paper against 1 for filing, and admission runs
at ~8 papers a week. Extraction cannot keep pace unless it is machine-led —
and machine-led extraction is unreviewed by definition. Same shape as the
scope scan, and it should be answered the same way: let the machine produce,
mark clearly what is unconfirmed, and let review of the output be both the
quality signal and the evidence for loosening the rules.

**Coverage: 6 of 101 records.**

---

## 5 · Tagging — concepts on statements

Fine-grained on purpose. The finer the tag, the better it proposes relations,
which is the entire reason the layer exists: `sanction-sensitivity` is a
better tag than `inter-agent trust`, because two claims sharing the first are
worth reading together and two sharing the second are not.

**The vocabulary is what statements have needed, and it grows from the bottom
up.** A term is in it because a claim argued about something, not because
somebody predicted the field would. The corpus is the argument for doing it
this way:

```
17 terms in use — 9 grown from statements, 8 taken from the pool
506 taxonomy subpoints never reached for
```

More of the working vocabulary arrived from claims than from the taxonomy,
and the predefined majority has gone untouched. So the taxonomy's 514
subpoints are a **suggestion pool** — searched before a near-duplicate is
invented, joining the vocabulary the moment a statement uses one — rather
than the vocabulary itself.

The asymmetry with the taxonomy is the point: a concept is cheap and
reversible, a topic code is a stable identifier other people's filings point
at.

A tag that does not resolve fails loudly. A concept whose id disagrees with
its label fails too — two of the first nine drifted.

**Growing the list.** The only failure mode a vocabulary has is silent: two
terms for one idea break nothing, and every relation that would have been
proposed between claims carrying them simply is not. Half a link layer
disappears into a synonym and nothing is ever raised.

```bash
aokg concepts --propose "Delegation revocation latency"   # is this already here?
aokg concepts                                             # the whole list's state
```

The list itself is readable without any of that: **[`data/concepts.json`](../data/concepts.json)**
holds all 523 terms with their topics, origin, and how many statements carry
each — generated from the taxonomy and the extras file, rebuilt on every
Pages run, and committed so a pull request shows what moved. Agents ask the
MCP server's `search_concepts` instead.

That file exists because the vocabulary previously lived only as an object
built at load time — 514 terms parsed out of indented bullets in a markdown
document about something else — so the one instruction the process gives,
*check before you add*, required a local checkout and an installed package.

The loader refuses a colliding term, with no way to assert past it. Two
resolutions and "they are different, trust me" is not one: either the terms
name one idea and you use the existing one, or the *name* is failing to say
what differs and the fix is a better name.

Prefer the more specific. `agent reputation` is a worse term than `agent
reputation systems` because it could mean either, and a vocabulary holding
both makes every tagger guess. A genuinely distinct idea says so in its
label — `reputation portability between agent ecosystems` collides with
nothing because it is actually specific.

It separates the vocabulary from the pool rather than reporting 523 as one
list, and ships the **8 pairs that look like one idea** — all inherited from
the taxonomy's subpoints, which were written as prose rather than as a
controlled vocabulary. Those can only be fixed where the taxonomy is. What
the loader prevents is a ninth.

**Coverage: 40 of 40 statements tagged, 17 concepts in use.**

---

## 6 · Linking — relations between statements

Two mechanisms, and the split is the design.

**Concepts propose.** Pairs sharing a tag become candidates. 40 claims is 780
pairs; a shared concept cuts it to 73, different papers to 27, minus settled
leaves 25. The tags do the filtering so judgment is spent where there is
something to judge.

```bash
aokg relate            # the queue
aokg relate --draft    # with a YAML skeleton per pair
```

**People assert.** Four types, named after CiTO so they mean what an outside
reader expects: `SUPPORTS`, `DISAGREES_WITH`, `QUALIFIES`, `EXTENDS_CLAIM`.
Every one is `INFERRED` and carries its reasoning — no source states that two
claims disagree — and the loader refuses one without.

**Most candidates should be nothing.** 25 read, 3 survived. A high yield would
mean the vocabulary is too loose.

A relation drafted by a model says so, and is never readable as a person's
judgment.

*Proposed:* citations as a second proposal signal. If A cites B, A's
statements are candidates for relations to B's. One usable edge today — worth
63 pairs — and free as coverage grows.

**Coverage: 12 relations across 16 of 40 statements.**

---

## 7 · Filing — categories, derived from what a paper says

The union of the taxonomy codes its statements' concepts sit under. Computed,
no judgment, and papers land in several categories naturally because their
statements do.

Measured against hand-filing on the six: derivation **gains** codes the filer
missed — Melting Pot picks up evaluation integrity because one of its own
statements predicts the suite will be gamed — and **loses** codes describing
what kind of move the paper makes: agency theory, borrowed background,
research method.

So it adds and never removes. What stays hand-filed is the remainder:
the framing codes, saying what kind of move a paper makes.

Filing a record still becomes a prefilled issue and `filing-to-pr.yml` turns
it into a pull request — **the PR list is the audit trail**, every human
judgment in the dataset, who made it and what it changed. What changed is
when it happens and how much of it there is to do.

**Coverage: 6 derived, 73 hand-filed from before the reordering.** Those 73
keep their codes; nothing is rewritten. They will look increasingly like what
they are — a judgment made before anyone had read the paper's statements.

---

## 8 · Review — the stage nothing has passed through

The scarce good, and the one thing on this page no machine does.

A reviewer opening a record is asked two questions in one sitting, because the
expensive part is the reading and it should be paid once: **where does this
belong**, and **is each statement what its quote says**. They also now see
whose claim it is, what it argues about, and any relation it is an end of —
including machine drafts asking for exactly this judgment.

Verdicts: `accurate`, `overstated`, `not-in-source`, `ambiguous`.
`overstated` is the one worth having — the claim is in the paper but the
paraphrase says more than the source does, which is the characteristic failure
of extraction and invisible in a yes/no.

Filings become pull requests. The gold set they build is what every
classification number is measured against.

**Coverage: 0 of 101 records, 0 of 40 statements.** This is the honest state
of the library and the reason every accuracy figure is still unquotable.

---

## 9 · Release — a fixed, citable version

```bash
aokg build --version v1.0.0
```

Nodes sorted by id, edges by their triple, no timestamp unless passed — the
same inputs produce the same bytes, which is what makes the checksums worth
publishing and a diff between releases worth reading.

A release describes the corpus on the day it was cut. When a record is later
found to be wrong, the release keeps it: rewriting one to hide a mistake would
make every other release less trustworthy.

**3 releases cut.**

---

## Where the effort actually goes

```
machine, unattended      intake · resolution · admission · filing · release
machine, then confirmed  extraction · tagging · linking          ← proposed
human, irreducible       review · the framing codes filing cannot derive
```

The bottom line grows only when somebody reads something. Everything above it
now grows on its own — which is why the binding constraint has moved from
"how do we find papers" to "who decides whether any of this is right", and why
the incentive question is about review rather than about adding.
