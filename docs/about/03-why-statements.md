---
id: why
title: Design principles
order: 3
---

Six decisions explain nearly everything else here, including the things that
look like limitations. Each one has a cost, and the cost is the point.

**The statement is the unit, not the paper.** A paper is a container. The
thing worth linking is what it asserts, and two papers are almost never about
the same thing while two sentences often are. Everything downstream follows:
tags go on statements, so they can name one mechanism instead of a whole
subfield; relations run between statements, so "who disagrees with this" has
an answer more precise than "that paper, somewhere"; and a paper's categories
are computed from its statements rather than assigned by hand, which is why a
paper lands in several at once. The cost is that a paper is not in the library
in any useful sense until somebody reads it down to its claims, which is why
{{read}} of {{records}} records have statements and the rest are held with
metadata only.

**Provenance is the product.** Every statement carries the sentence it came
from. Every edge that is an inference says so and carries the reasoning for
it, because no source states that two claims disagree or that one paper's open
question is an instance of another's. Anything a model drafted says it was
drafted and is never readable as a person's judgment. The cost is volume:
nothing can be added faster than it can be sourced.

**Machines admit, people judge.** Finding, resolving, admitting and tagging
run unattended. Deciding whether a statement says what its source says does
not, and never will. A verdict binds to the wording it was given, so
re-extracting a sentence sends it back to the queue rather than carrying
somebody's name onto words they never read. The cost is that the library grows
only as fast as people read.

**Open problems are found, not written.** This is the one thing here that a
search engine cannot do, so it is worth saying how it works. When a paper says
something is unresolved, that sentence is captured as a **gap** statement, in
that paper's words. Gaps that turn out to be asking the same thing are
clustered into a **question**, and each gap reaches it by an edge that keeps
its own quote and its own paper. {{questions}} questions so far.

Two numbers are kept apart deliberately: how many papers ask a question, and
how many statements do. A question two papers ask is a statement about a
field. A question one paper asks twice is that paper's framing. One number
over both would let the second pass for the first. The cost is that this layer
is only as good as the reading underneath it, and today exactly one question
crosses papers.

**Counts, not scores.** How many people saved a thing, how many papers reach a
question, how many statements have been reviewed. No ranking anybody has to
take on faith, and no number that cannot be traced to the rows it came from.
The cost is that nothing is sorted for you by importance.

**Small on purpose.** Files in git rather than a database, so a change is
reviewable as a diff and a release is reproducible byte for byte. A narrow
corpus rather than a broad one: admitting everything cited by everything held
measures out at roughly 4,900 records, 93% of them cited exactly once, and
{{records}} curated records are worth more than 8,500 indiscriminate ones. The
cost is that things you might expect to find are deliberately absent, and the
scope test that kept them out is recorded on the refusal.
