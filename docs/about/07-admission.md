---
id: admission
title: How anything gets in
kicker: the evaluation framework
order: 7
---

Every route ends at the same gate, and none of them is a keyword score. What
differs is the evidence a candidate arrives with and therefore what it has to
clear first.

| | Growth | Scouting |
| --- | --- | --- |
| Finds | papers the corpus already cites, or that cite it | papers connected to nothing we hold |
| First bound | a rising citation threshold — two held papers at one hop, three at two, each step from a human judgment strictly harder | topical support: BM25 against our own published taxonomy, plus overlap with concepts statements have needed |
| Then | the scope scan | the scope scan |
| Budget | 40 admitted a run | 25 scanned a run |
| On passing | admitted to the corpus automatically | written to a candidate file for a person to promote |

**The scope scan is the gate, and it is one gate.** A model reads the abstract
against the scope test — what changes because machine agents hold authority —
and against a register of things deliberately excluded before. Both routes
send it the same policy and the same standard of proof; only the evidence
block differs, because a scouted paper has no citations and saying "cited by 0
papers" would read as weak evidence when the truth is different evidence.

It must answer in one sentence what about designing, operating or overseeing
an agent-authority organization is different because of the work. If it
cannot, the answer is no. A scan that errors refuses: "the API was down so
everything got in" is the drift this layer exists to prevent.

**Three answers, not two.** Admit, refuse, or borrowed background — adjacent
work the library points at rather than ingests, such as an evaluation suite or
a foundational method the field builds on. Melting Pot is held that way.

**What the numbers say so far.** A growth run in September considered 3,659
works and admitted 40 against a budget of 40, refusing 119 as out of scope.
The scout's first scan put 12 candidates to the gate and admitted 5 — two
outright and three as borrowed background. Refusals are the more useful half
of both: if most of what clears a bound is refused by the scan, the bound is
too loose to be worth its budget.

Every admission carries the scan's reasoning in its record, so a bad rule
shows up as a readable pattern rather than a mystery pile. A refusal is
remembered too, and a verdict that flips between runs is reported rather than
quietly applied.
