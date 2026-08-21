# Sharpening the topic suggestions

**2026-08-21.** Reviewers were being offered five topics for every paper
whether five were plausible or two were. Two changes, both measured before
shipping.

## What was wrong

Diagnosed before touching the scorer, because the fix differs:

| | |
|---|---|
| Correct tags never retrieved at all | **0%** |
| Correct tags in the top 5 | 36% |
| Median rank of a correct tag | **11** |

Nothing was missing — everything was findable somewhere in the 103. It was a
ranking problem, so reweighting was worth trying and better retrieval was not.

## What worked

Measured over 61 records and 143 tags:

| variant | recall@1 | recall@3 | recall@5 | MRR |
|---|---|---|---|---|
| as shipped | 10% | 24% | 36% | 0.42 |
| + stemming | 13% | 27% | 36% | 0.46 |
| + stemming and phrases | **14%** | **29%** | 35% | **0.49** |

Stemming collapses the endings that were costing matches — `permissions`
against `permission`, `overspending` against `overspend`. Phrases add adjacent
pairs as terms of their own, because "spend cap" is not "spend" plus "cap".

## What did not work

**Weighting the title above the notes.** The obvious suspect: after the leaf
collapse a subsection's document is mostly former leaf titles, median 25 terms
and up to 85, so a title term is diluted. Tripling the title changed recall@1
from 10% to 9%. Quintupling it did no better. The hypothesis was wrong.

**Dropping the ancestor titles.** Every subsection carries its section's title,
so `evaluation` appears across all of section 14 and discriminates poorly.
Removing them cost 2 points at rank 3 — IDF was already handling it, and the
ancestor context helps more than the dilution hurts.

**Tuning length normalisation.** b=0.9 and b=0.3 were both worse than 0.6.

**Closing the `evaluating`/`evaluation` gap.** They stem to `evaluat` and
`evalu` and never meet. Stripping the verb stem's trailing `at` to fix that
took recall@1 from 14% to 13% and MRR from 0.49 to 0.47: it collides terms that
mean different things. The miss is cheaper than the collision, so the gap
stays, with a test recording why.

## Less choice

Accuracy alone does not answer the complaint. A fixed five shows five weak
options when only two are competitive, so the count now follows the scores —
suggestions within 70% of the best, bounded to between two and six:

| rule | shown on average | recall | precision |
|---|---|---|---|
| fixed five | 5.0 | 35% | 16% |
| within 70% of the best | **3.8** | 30% | **21%** |
| within 75% | 3.4 | 28% | 22% |

24 records now offer two suggestions, 18 offer six. The rest of the ranking is
behind "show more", so a missed tag costs a click rather than a search.

## The honest limit

These are all agreements with tags the corpus assigned itself, unreviewed. They
measure similarity to an earlier machine-assisted pass, not correctness, and a
variant that agrees more is only *likelier* to be better.

The ceiling for lexical matching also looks close. Retrieval is already perfect
and the median correct tag sits at rank 11 — that gap is semantic, not
lexical, which is what an embedding model fixes and what BM25 over 103 short
documents cannot. That was the recommendation of the first classification
baseline and this measurement strengthens it. Worth doing after the review,
when there is a gold set to measure against rather than the corpus's own guess.
