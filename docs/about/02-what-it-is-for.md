---
id: for
title: Questions it answers
order: 2
---

The field is young, fast, and spread across venues that do not cite each
other. Finding papers is not the expensive part. The expensive part is finding
out whether anybody has actually tested the thing you are about to assume, and
whether anybody disagrees.

| What you want to know | What you get | Why a search will not do it |
| --- | --- | --- |
| Has anybody measured this, or is it only argued? | the statements that claim it, each marked as a finding or a position, with the sentence it came from | a search returns papers, and an abstract does not tell you which of its claims were tested and which were asserted |
| Does anybody disagree, and about what exactly? | pairs of statements asserted to contradict each other, each with the reason a person gave for saying so | a citation graph tells you what cites what, never whether it agrees |
| Who has studied this, working that way? | a finding's subject joined to a method's technique | no index separates what a paper is about from how it was done |
| What should I know before trusting this result? | the background it rests on, and the limitations the authors stated themselves | limitations live in discussion sections and are the first thing a reader drops |
| What is still open? | questions clustered from what several papers said they could not resolve | nobody indexes what a field has failed to answer |
| What does the field hold right now? | a fixed, checksummed release that will say the same thing next year | a literature review is out of date the week it is published, and cannot be queried |

**For a researcher**, it is a way into a subject that returns the claims and
the disagreements rather than a reading list. **For a practitioner**, it is a
way to check a design decision against what has actually been demonstrated.
**For an agent**, it is a queryable substrate: claims with provenance, which
is what a model needs to answer carefully rather than plausibly.

**What makes it trustworthy is the same thing that makes it slow.** Machines
find, resolve, admit and tag. Every statement has been checked mechanically:
its quote was found verbatim in the source, its tags resolve, and it is about
the field rather than about the paper's own instrument. That is why
{{machineChecked}} of {{statements}} say machine-checked. It is a real signal
and it is not review.

What no machine does is decide whether a statement says what its source says.
A person does that, and the judgment is recorded against their name in a pull
request anyone can read. Today that is {{reviewed}} of {{statements}}, which
is the honest state of the library.
