# Reading a paper

The brief given to a model that drafts claims from a paper, and the
standard a person checks the drafts against. It comes from an audit of the
first seven papers against their full texts
([evals/results/2026-10-01-statement-audit.md](../evals/results/2026-10-01-statement-audit.md)),
which found the same failures in nearly every one.

A claim represents somebody's work to strangers. A reader who meets it
may never open the paper, so it has to say what the paper says: no more, no
less, and in a form its authors would recognize.

## Before drafting

**Read the whole paper.** Every section of the body, not the abstract and
conclusion with the rest skimmed. The commonest failure was claims drawn
from the paper's summary of itself, while the methods, the results, the
traces and the arguments carried none. An abstract states conclusions and omits
what they rest on, and it is often surer than the body.

**Know what kind of paper it is.** An empirical paper has evidence claims. A
conceptual or position paper has positions, definitions and perhaps
limitations. It may have no evidence claims at all, which is not a defect. Calling
its conclusions evidence claims is.

## The seven kinds of claim

| Type | What it is | The test |
|---|---|---|
| evidence | Something this work observed or measured | Could the paper's own data have come out otherwise? |
| position | An argument, implication or recommendation | Is it argued, not measured — including "our analysis finds" in a paper with no experiments? |
| definition | A term the paper introduces or fixes the meaning of | Does it say what a word means, not how something is done? |
| protocol | How the work was done: a technique, design or procedure it used | Could someone repeat it? |
| limitation | A boundary the authors put on their own result | Is it about this result, not the field? |
| gap | A question the paper leaves open, or says the field has not answered | Does the paper leave it for somebody else? |
| background | The state of the field or prior work, as the paper reports it | Is it somebody else's result, or the premise the paper argues from? |

Three lines are crossed most often:

- **An implication is a position.** "It is then plausible that leading
  submissions exploited the evaluation" is an inference from a result. It is
  not the result.
- **A new term is a definition.** "We introduce X: the capacity for ..." is
  not a protocol.
- **A system the paper builds on is background.** Credit it to whoever built
  it, even when they are co-authors. The paper's method is what the authors
  did with it.

## Writing the claim

- **`quote`** is the paper's exact sentence, copied, never reconstructed. It
  is checked character for character against the source.
- **`text`** is one assertion in plain words. It must not say more than the
  quote:
  - **Keep every hedge.** "May", "seems to", "plausible", "can be", "in
    principle" stay. Dropping them was the second commonest failure.
  - **Keep the scope.** "Within the Melting Pot suite" does not become "in
    multi-agent evaluation".
  - **Keep the modality.** "Must" does not become "should", any more than
    "may" becomes "does".
  - **Add no cause** the paper does not give, and no "rather than" it does not
    draw.
- **`standalone`** is the same claim with enough context to check it cold:
  the setting, the population, the conditions, the size of the effect. It is
  not a note about the paper, and it does not call itself "the claim the paper
  is named for" — only one claim can be.
- **`attribution`** is `own`, or `other` with `attributed_to` naming whose
  result it is. A sentence the paper cites is usually `other`.
- **`extracted_from`** is the section the quote is actually in. Check it, not
  the parser: headings with "evaluation" or "model" in them are misfiled, and
  headings the parser drops leave sections labeled `other`.

## Tagging

A tag says what the claim argues about, specifically enough that two
claims sharing it are worth reading together.

- **Search before inventing.** The vocabulary and its unused pool are in
  `data/concepts.json`.
- **A tag must not contradict its claim.** "Shared schemas" on a protocol
  whose point is joining systems without one, "stake-based trust" on "where
  stakes are high", "dynamic evaluation" on a suite whose counterparties are
  fixed: each was in the corpus.
- **No tag on more than half a paper's claims.** A blanket tag tells
  claims apart from nothing.
- **A definition carries the concept it defines.** A term the paper coins is a
  new concept, and its definition claim is where it comes from.
- **A protocol carries its technique,** not the paper's subject.

## What not to draft

- Facts about the paper's own instrument: its scenario count, its run
  count, its metric names.
- The same assertion twice.
- A promise the body does not keep. If the abstract promises an evaluation and
  the body has none, there is no evidence to draft.

## After drafting

The gates in `src/ao_commons_kg/extract.py` run on every draft. They refuse a
quote that is not in the paper, artifact trivia, an unstated attribution, and
an unresolved tag. Six more checks report rather than refuse:

- a protocol tagged with its paper's subject
- a paraphrase surer than its quote
- an evidence claim quoted as argued
- a term not typed as a definition
- a blanket tag
- a body section with no claim

`scripts/check_claims.py` runs the same checks over claims already
held.

**Then an independent audit.** The checks find structural failures reliably
and failures of meaning only sometimes. On the first seven papers they caught
5 of 18 paraphrases that said more than their quote, and 1 of 8 arguments
typed as evidence claims. So every paper's drafts are audited against its full text
by a model that did not draft them, with the brief in
[evals/machine/audit-brief.md](../evals/machine/audit-brief.md). The audit
reports to the person reviewing and changes nothing itself.

Every draft arrives `machine-checked`, which means the gates passed and
nothing more. Whether a claim says what its paper says is decided by a
person. When that person is an author of the paper, their verdict is recorded
as an author's.
