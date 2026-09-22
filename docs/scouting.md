# Scouting: finding work the citation graph cannot see

`aokg grow` walks citations in both directions and is good at it. Tuesday's
run considered 2,915 works, admitted 40 and deferred 123 — it is bounded by
its budget, not by a shortage of candidates.

What it cannot do is find a paper that neither cites us nor is cited by us.
`Candidate` is citation-shaped: support is the number of held records
connected to it, and the threshold asks for two at generation 1. A paper with
no connection has support 0 and can never clear any threshold, however plainly
it belongs.

That is not hypothetical. One query to arXiv's free API — `cat:cs.MA AND
abs:"delegation"`, newest first — returned this, published on 6 September:

> **CAPMAS: Capability-Based Delegation of Privileges in Multi-Agent Systems**

Capability-based delegation of privileges is the center of this library's
scope. We do not hold it, and expansion would never have found it.

---

## The problem the design has to solve

Remove citation support and the rising threshold does nothing. The only gate
left is the scope scan, and a scout bounded by nothing but a model's opinion
is precisely the unbounded admission this project was built to avoid —
admitting everything cited measures out at ~4,900 records, 93% of them cited
exactly once.

So a scout needs a bound of its own, and it has to be one the corpus can
compute about itself rather than one a model asserts.

## Where the queries come from

Not from a hand-written list, which rots. From the corpus, in two halves that
do opposite jobs.

**Concepts in use — 31 of them — deepen.** A term is in the working
vocabulary because a statement needed it. Searching for those finds more work
on the things the library has actually turned out to be about.

**Taxonomy subpoints never reached for — 493 of them — widen.** These are the
things somebody thought mattered enough to name and about which the corpus
holds nothing. They are a map of our blind spots, written down in advance.

The asymmetry is the point. A scout that only searches what the corpus already
contains deepens a rut: it finds neighbours of what we have, which is what
citation expansion already does better. Half the queries must come from where
we have nothing, or scouting becomes a slower version of `grow`.

## The bound that replaces citation support

**Topical support**, computed locally and free:

- `classify.py` already scores any abstract against the 103-topic taxonomy
  with BM25. A candidate that scores well is on-topic by the library's own
  published definition rather than by a model's judgment.
- Concept overlap against the working vocabulary, as a second signal.
- Attention — Hacker News points, GitHub stars, both keyless — only for work
  too new to have been cited at all. Never as a quality signal: it is the
  answer to "is this reachable at all yet", not to "is this good".

A candidate must clear a topical threshold to reach the scan, exactly as a
cited candidate must clear a citation threshold. The numbers will need
calibrating against the first few runs, which is a thing to measure rather
than guess.

## Sources

Pluggable, and the free ones come first so the tool never depends on a
subscription.

| Source | Cost | Gives |
|---|---|---|
| arXiv API | free, no key | category + keyword, newest first — the freshest signal |
| OpenAlex | free, no key | search across venues, filters by date and concept |
| Hacker News, GitHub | free, no key | attention on work too new to cite |
| Emergent Mind | $0–12/month | semantic search and attention ranking |

**Emergent Mind is asked for trending, once a run, and the free tier is why.**
50 requests a month buys six runs if it is asked per query, and almost a year
of weekly runs if it is asked once for what is trending — which returns up to
50 papers for that one request. It is also the only thing here the free
sources cannot do: arXiv and OpenAlex can be asked what is new, not what is
being read. The source stops on its own when the month's remaining count
approaches zero, because an allowance spent by a loop nobody noticed is a
month with no attention signal at all.

On Emergent Mind specifically: their terms forbid copying content out of the
service, so a scout may keep **pointers** — an arXiv id — and must resolve and
extract everything itself from arXiv, OpenAlex and Semantic Scholar, as every
other path already does. Their free tier is 50 requests a month, which covers
a weekly run of ten queries; Pro is 2,500 for $10–12. Optional by design: if
their terms or pricing change, the tool loses a source rather than stopping.

## What a scout may do with what it finds

Propose, not admit. Output goes to `data/candidates/` in the shape that
directory already uses, with the reasons that produced each score, and a
person promotes.

That is a deliberate step down from `grow`, which admits automatically. The
argument for automatic admission there is connectedness: two held papers cite
it, so the corpus has already voted. A scout has no such vote, so it gets the
weaker permission.

Everything else is reused rather than rebuilt: `likely_same_work` for
duplicates, the scope scan for the gate, `refused.yml` so a refusal is
remembered and not re-proposed next week, and a hard budget per run.

## What could go wrong, and what would show it

**Homogeneity.** Queries drawn from what we hold return more of what we hold.
The 493 unreached subpoints are the counterweight, and the measure is the
share of admissions that arrive under a concept the corpus had no paper for.
If that share is near zero, the scout is deepening a rut.

**Popularity as a proxy.** Attention measures what is being talked about.
Weighted at all heavily it would fill the corpus with whatever trended, which
is the opposite of a curated library. It earns a place only for work with no
citations yet, and only to reach the scan — never to clear it.

**A model writing its own queries.** Generating search terms from the
vocabulary is reasonable; letting a model invent topics is how scope drifts
without anybody deciding to change it. Queries derive from the taxonomy and
the working vocabulary, both of which are in git and reviewable.

**Cost per run.** Free sources have no per-call cost; the scope scan does. The
budget bounds it, as it already does for growth.

## What the first run taught

Stage 1 is built, and running it corrected the design in one place.

BM25 against the taxonomy measures **"is this about organizations"**, not
"is this about organizations where machine agents hold authority". Our
taxonomy is about organizations, so the first live sweep ranked *Organized
Violence and Crime in Urban Nigeria* (116) and *The ecology of insolvency*
(108) above everything else. Both are legitimately about organizational
governance. Neither has a machine anywhere near it.

So a find must now show the agent half too, by a generous local pattern —
`agent`, `LLM`, `autonomous`, `automated`, and their neighbours. It is not
deciding whether agents hold *authority*; that needs a model and is the
scan's job. It refuses only the case no amount of organizational relevance
can rescue. On the first sweep it removed 47 of 63 finds.

Precision after that is still modest: healthcare information sharing and
the Indian economy survive the bound. That is the intended division of
labor — the bound is free and the scan is not, so the bound's job is to
keep the scan's bill down rather than to be right on its own — but it is
the number to watch. If most of what clears the bound is refused by the
scan, the bound is too loose to be worth its own budget.

## Stages

1. **arXiv and OpenAlex, queries from the corpus, scored locally.** No key, no
   subscription. This alone answers how many CAPMAS-shaped papers we are
   missing, which is the number that justifies anything further.
2. **The scan and the candidate file**, reusing growth's machinery.
3. **Attention and Emergent Mind** as optional sources, once the free path has
   a measured yield to compare against.

Stage 1 is the one worth building first because it is the one that produces
evidence rather than assuming it.
