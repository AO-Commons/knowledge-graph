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
  4  FILING          a place in the taxonomy     73 filed
  5  EXTRACTION      statements out of text       6 records · proposed as process
  6  TAGGING         concepts on statements      40 of 40 statements
  7  LINKING         relations between them      12 relations
  8  DERIVATION      categories from statements   6 records
  9  REVIEW          a person decides             0 reviewed
 10  RELEASE         a fixed, citable version     3 releases
```

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

**Add tab** → issue labelled `new-resource` → `new-resource.yml` runs
`add_resource.py` → commits to main → asks Pages to rebuild. No maintainer in
the loop, on a blast-radius argument: a new record changes no existing
judgement and no measured number, and `git revert` undoes it completely.

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
flattened into two lists. Organisation names fold only on the country suffix:
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

**A rising threshold.** Generation 1 needs 2 held papers to cite it,
generation 2 needs 3, each hop from a human judgement strictly harder. This is
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

## 4 · Filing — a place in the taxonomy

A classifier proposes from title and abstract; a person confirms. The record's
own `taxonomy_topics` are only ever written by a human filing it.

Filing happens on the site, becomes a prefilled issue, and
`filing-to-pr.yml` turns it into a pull request. **The PR list is the audit
trail**: every human judgement in the dataset, who made it, what it changed.

*Proposed change:* most of this becomes derived (stage 8), leaving a short
hand-filed remainder for the framing codes derivation cannot see.

**Coverage: 73 of 101 filed.**

---

## 5 · Extraction — proposed as a process

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

**The bind:** ~7 judgements per paper against 1 for filing, and admission runs
at ~8 papers a week. Extraction cannot keep pace unless it is machine-led —
and machine-led extraction is unreviewed by definition. Same shape as the
scope scan, and it should be answered the same way: let the machine produce,
mark clearly what is unconfirmed, and let review of the output be both the
quality signal and the evidence for loosening the rules.

**Coverage: 6 of 101 records.**

---

## 6 · Tagging — concepts on statements

Fine-grained on purpose. The finer the tag, the better it proposes relations,
which is the entire reason the layer exists: `sanction-sensitivity` is a
better tag than `inter-agent trust`, because two claims sharing the first are
worth reading together and two sharing the second are not.

The vocabulary is 523 terms. **514 of them are the taxonomy's own demoted leaf
titles**, read from the taxonomy file rather than copied — one source of
truth. The other 9 are terms the corpus needed and the taxonomy had no shelf
for, in `concepts-extra.yml`, each carrying the categories it sits under.

Concepts grow bottom-up from what the corpus argues about; the taxonomy stays
top-down and stable. That asymmetry is what makes a new concept cheap and a
new topic code expensive.

A tag that does not resolve fails loudly. A concept whose id disagrees with
its label fails too — two of the first nine drifted.

**Coverage: 40 of 40 statements tagged, 17 concepts in use.**

---

## 7 · Linking — relations between statements

Two mechanisms, and the split is the design.

**Concepts propose.** Pairs sharing a tag become candidates. 40 claims is 780
pairs; a shared concept cuts it to 73, different papers to 27, minus settled
leaves 25. The tags do the filtering so judgement is spent where there is
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
judgement.

*Proposed:* citations as a second proposal signal. If A cites B, A's
statements are candidates for relations to B's. One usable edge today — worth
63 pairs — and free as coverage grows.

**Coverage: 12 relations across 16 of 40 statements.**

---

## 8 · Derivation — categories from what a paper says

The union of the taxonomy codes its statements' concepts sit under. Computed,
no judgement, and papers land in several categories naturally because their
statements do.

Measured against hand-filing on the six: derivation **gains** codes the filer
missed — Melting Pot picks up evaluation integrity because one of its own
statements predicts the suite will be gamed — and **loses** codes describing
what kind of move the paper makes: agency theory, borrowed background,
research method.

So it adds and never removes, and the review screen offers derived codes as
dashed chips beside the classifier's suggestions rather than applying them.

**Coverage: 6 of 101.**

---

## 9 · Review — the stage nothing has passed through

The scarce good, and the one thing on this page no machine does.

A reviewer opening a record is asked two questions in one sitting, because the
expensive part is the reading and it should be paid once: **where does this
belong**, and **is each statement what its quote says**. They also now see
whose claim it is, what it argues about, and any relation it is an end of —
including machine drafts asking for exactly this judgement.

Verdicts: `accurate`, `overstated`, `not-in-source`, `ambiguous`.
`overstated` is the one worth having — the claim is in the paper but the
paraphrase says more than the source does, which is the characteristic failure
of extraction and invisible in a yes/no.

Filings become pull requests. The gold set they build is what every
classification number is measured against.

**Coverage: 0 of 101 records, 0 of 40 statements.** This is the honest state
of the library and the reason every accuracy figure is still unquotable.

---

## 10 · Release — a fixed, citable version

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
machine, unattended      intake · resolution · admission · derivation · release
machine, then confirmed  extraction · tagging · linking          ← proposed
human, irreducible       filing · review
```

The bottom line grows only when somebody reads something. Everything above it
now grows on its own — which is why the binding constraint has moved from
"how do we find papers" to "who decides whether any of this is right", and why
the incentive question is about review rather than about adding.
