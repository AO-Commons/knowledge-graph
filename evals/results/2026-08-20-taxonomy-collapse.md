# Collapsing the leaf layer

**2026-08-20.** The taxonomy went from 568 codes to 103: the leaf layer was
demoted to notes on its subsection, leaving 16 sections and 87 subsections. Every word survives; 465 codes do not.

## Why

A reviewer reported overlap, with a screenshot showing eight suggestions of
which five were siblings under 5.1. Measuring rather than eyeballing:

| | |
|---|---|
| Tags landing at subsection level | 138 of 149 — **93%** |
| Tags landing at leaf level | 11 — **7%**, across 8 of 466 leaves |
| Leaves holding nothing | **458 / 466** |
| Subsections whose own leaves competed for the same paper | **31 / 86** |

The leaf layer asked a reviewer for a hard choice on every record and took 7%
of the filings. It also produced 61 events where two or more children of one
subsection were offered for the same paper — five for 5.1 alone.

Textual duplication existed too, but it was the smaller problem: nine
cross-section pairs at 0.45 Jaccard or above on stemmed titles, such as
`3.4.3 Emergent structure in large agent populations` against
`5.1.1 Emergence in agent populations`. Section 11 looked worse than it is —
it is a coding scheme for incidents and re-covers other sections deliberately,
so its overlaps were set aside rather than counted.

## What changed

Every leaf title became an unnumbered note on its subsection, which the parser
already supported and the classifier index already reads. So the vocabulary is
intact for retrieval and for the hover text on the site; what is gone is the
obligation to choose between five phrasings of one idea.

`14.5.5` was kept at first, which left one numbered leaf in an otherwise
two-level tree. It has since moved to `15.6 From reinforcement learning`, a
subsection of Borrowed foundations — where the siblings are all "From
\<field\>" and the brief is compressed pointers rather than shelves. MARL now
sits under the field it is a branch of, the tree is uniformly two levels, and
`15.6` still ranks first for both Melting Pot and SocialJax.

43 references were repointed to surviving codes — 23 record tags, 17 claim
suggestions and 3 alias keys.

## Effect

Same measurement, same 58 records, before and after:

| | 568 codes | 103 codes |
|---|---|---|
| Top suggestion is a tag the record carries | 3% | **21%** |
| A carried tag appears in the top five | 5% | **62%** |
| Sibling self-competition events | 61 | **0** |

The before figures are depressed by a granularity mismatch — the classifier
was proposing leaves while people filed at subsections, so agreement was
close to impossible by construction. That mismatch *was* the problem, and
removing it is most of the gain. The honest claim is not that classification
got twelve times better; it is that suggestions and filings now describe the
same thing, and can therefore agree.

## What this does not settle

Whether 86 subsections is itself too many. Nothing measured here says so, and
the corpus is too small to tell: 61 records over 103 codes still leaves most
of the tree empty. That is a question for after the review, when there are
human filings to measure against rather than the corpus's own first-pass tags.

Reversing this is a revert. The leaf titles are in the file, one indent level
deeper.
