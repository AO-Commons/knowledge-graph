---
id: review
title: Review
order: 9
---

One question per statement: **is this what the paper says?** The quote sits underneath, and is not editable: it is what the statement is
checked against, and anybody who could edit both could make anything true.

| Action | Means | What it does |
| --- | --- | --- |
| Add as is | the statement says what the quote says, no more | records accurate |
| Adjust | nearly right — rewrite it in your words | you retype it and press Confirm wording; the tags follow |
| Remove | the paper does not say this | records not-in-source, and the extractor is the thing at fault |

Adjusting is faster than describing what is wrong and waiting for somebody to
fix it, which is why it is there. A draft is not a judgment: until you confirm
the wording, the statement is not counted as done and is not submitted.

**After Submit.** Your filing opens a prefilled GitHub issue. A bot checks
every claim id and every tag against the vocabulary, answers on the issue if
something is wrong, and otherwise opens a pull request. Merging it records the
verdict against your name and, for an adjustment, replaces the statement with
your wording. The pull request list is the audit trail — every human judgment
in the dataset, who made it, and what it changed.

Two things the screen will tell you. A paper read only from its abstract says
so above its statements, because those statements cannot say more than the
abstract does. And a statement that was rewritten after somebody judged it
comes back to the queue rather than keeping the old verdict — a verdict
belongs to the wording it was given.

Nothing is uploaded as you work. Your filing lives in your browser until you
send it.
