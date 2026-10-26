# Open problems

How a question gets onto the open problems surface, what it is made of, and
what the numbers beside it count.

**Status:** live as of 2026-10-09; the reader-asked layer added 2026-10-21. Argued on the roadmap for months before it
was built, under its MIRA names, which is why the vocabulary below was not
invented here.

For the extraction pass that produces the raw material, see
[pipeline.md](pipeline.md), stage 4.

## The distinction the layer exists for

A `gap` claim is one paper saying something is unresolved — in that
paper's words, bounded by that paper's scope, and carrying the quote it was
read out of. Seven of those are held today.

A **question** is the thing several of those turn out to be asking. It is not
a summary of them and not a ninth kind of claim. It is a node, and each
gap reaches it by an **`addresses`** edge that keeps its own quote, its own
paper and its own wording.

Both names are [MIRA](https://github.com/MIRA-science/schema)'s, a shared
schema for research graphs, as the four claim-to-claim relations are CiTO's.
In MIRA's vocabulary the edge runs from a `Claim` to a `Question`, which is
the direction `ADDRESSES` runs here. Adopting somebody else's word for a
layer we had not built cost nothing and means an outside reader already knows
what the edge asserts.

The distinction matters because the two sentences

> How well the same measurement layout transfers to other social-AI suites
> remains an open question

and

> METR's investigation focused on very complex tasks, but it is not clear if
> this trend holds for more simple tasks

are asking the same thing — is this number a property of the agent, or of the
conditions it was measured under — in papers that share no citation, no author
and no vocabulary. No search puts them together. The corpus can, because it
holds the sentences rather than the papers.

## What a question is made of

Questions live in [`data/questions.yml`](../data/questions.yml), one file
rather than inside each paper's claims, for the reason
`claim-relations.yml` gives: the edge belongs to neither end, and filing it
under one paper would make the corpus read differently depending on which
paper you opened.

| Field | Is | Required |
|---|---|---|
| `id` | `question:` and a slug | yes |
| `text` | the question, in the corpus's voice, ending in `?` | yes |
| `note` | why these claims are one question | yes |
| `concept_tags` | the concepts it sits under | no |
| `status` | `open`, `answered`, or `retired` | defaults to `open` |
| `asserted_by` / `asserted_on` | who made the judgment, and when | no, but say it |
| `addressed_by` | the claims asking it, each with a `because` | yes, at least one |

Two of those are load-bearing and the loader refuses a file without them.

**`note` is the judgment.** Everything else in a question is bookkeeping; the
note is the claim that these particular sentences are one question, and it is
the thing a reader most needs to be able to disagree with. A question whose
note does not survive reading its claims is wrong, and that is the whole
review.

**`because`, per occurrence.** No paper says "my open question is an instance
of yours." Somebody read several and decided, so every `addresses` edge is
`INFERRED` and carries its reasoning, exactly as a claim relation does. An
edge here that looked deterministic would assert a judgment nobody made.

As of 2026-10-09 that somebody is a machine for all four, drafted and
unconfirmed — the same state the claim relations were in, and for the same
reason: a question attributed to a person reads as settled, and none of these
has been read by one yet.

## What a question does not assert

That it is unanswered. A question asserts only that the corpus holds
claims asking it. Whether anyone has answered it is what the claims
bearing on it are for, and the corpus is far too thin to say so — 7 papers of
257 have been read down to their claims at all.

This is why `status` exists and why it is not computed. "Answered" is a
judgment somebody makes after reading, not a count of findings.

## The two numbers, and why they are two

```
papers        distinct papers holding a claim that addresses it
occurrences   claims that address it
```

A question asked twice by one paper is that paper's framing. A question asked
by two papers is a claim about a field. That difference is the only reason
this layer is worth building, so it is counted rather than implied, and
showing a single number over both would let the first pass for the second.

`questions.reach()` returns them separately, and the test that pins them is
`test_papers_and_occurrences_are_counted_apart`.

## What the corpus holds today

Seven gap claims from four papers, clustering into four questions.

| Question | Papers | Occurrences |
|---|---|---|
| Does a measured agent capability survive a change of testbed? | 2 | 3 |
| Who is accountable when an agent's identity does not hold still? | 1 | 2 |
| How do ex ante constraints on autonomous action interact in practice? | 1 | 1 |
| Can an evaluation stay valid while the system it measures keeps changing? | 1 | 1 |

One crosses papers and three do not, and that ratio is the honest state of the
layer: it works, and it is thin. A question with one occurrence is a thin
question and is counted as one; it is kept so the second paper to ask it lands
somewhere rather than starting again.

## What the loader refuses

Failing the build is cheap; shipping a question that cannot be checked is not.

- a `text` that is not phrased as a question — a claim there would be a
  claim nobody made
- a question no claim addresses — one the corpus cannot show anybody
  asking is an opinion, not a finding
- an occurrence with no `because` — an unexplained judgment cannot be told
  from a guess
- an occurrence naming a claim we do not hold — it was cut, renamed, or
  never extracted, and an edge to nothing would make the layer's claim false
  while still rendering
- a duplicate `id`
- a missing `note`

`test_every_gap_statement_is_accounted_for` adds one more, from the other
direction: a gap that reaches no question fails the suite. A gap the layer
silently drops is worse than one it clusters wrongly, because a wrong cluster
is visible and an absence is not. That test is what caught two gap claims
missing from the first draft of `questions.yml`.

## Adding or correcting one

1. Read the gap claims that look related, with their quotes.
2. If they are one question, add it to `data/questions.yml` with a `note`
   that says why, and an occurrence per claim with its own `because`.
3. If a cluster is wrong, the fix is usually the note: either it describes a
   question the claims are not asking, or it is vague enough to cover
   anything.
4. `pytest tests/test_questions.py` and `aokg build` — the release refuses a
   dangling edge, so a build that passes is a question layer that resolves.

Every change is a diff against one file, reviewable the way everything else
here is.

## Proposing one

```
aokg questions            the questions, with how far each reaches
aokg questions --propose  concepts that look like a question nobody has clustered
```

`--propose` proposes and never admits, exactly as the scout does for papers.
A concept is proposed when at least two distinct papers argue about it — in
`position`, `gap` or `limitation` claims — and **nothing has been shown on
it**: one `finding` carrying the concept and it is not proposed at all.

That last bound is the one worth arguing about. It separates "nobody has shown
this" from "somebody has, and you have not read it", and loosening it would
produce a longer list of weaker proposals, which is the failure this
repository exists to avoid. Concepts already covered by a question are left
out, because noise in a proposal list is what stops anybody reading it.

A proposal is not a question. A question is the sentence somebody writes after
reading the claims, and no amount of counting produces that sentence. The
command prints the claim ids so the reading can start.

Two concepts qualify today: `sources-of-legitimate-machine-authority` and
`legitimacy-erosion-through-automation`.

## Questions readers ask

Everything above describes a question derived from what papers wrote. A reader
asking the library something is a second source for the same object, and a
weaker one: a gap claim is a published author saying in print that
something is unresolved, while a question typed into a search box is somebody
wondering. The two must not be mixed without saying which is which.

They are worth having anyway, for a reason the derived ones cannot supply.
`--propose` can only find a question the corpus already contains the material
for. A reader asking about something no held paper mentions is the only signal
this repository gets about what is missing from it entirely.

So a reader-asked question is **not** a question node. It lives in the
application, it never enters `questions.yml` by itself, and the only way it
becomes a question here is the way everything else does: somebody reads it,
writes the sentence, and opens a pull request. What follows is the test for
which reader-asked questions are worth that reading.

### The eligibility test

A list of everything anyone typed is a log. These five gates decide what goes
on the list a maintainer is asked to read, in this order. A question that
fails one is not recorded at all.

That last part was decided twice. Keeping a rejected question with the gate
that rejected it makes the test inspectable, which is worth something: a test
nobody can audit is a test nobody should trust. It also puts a greeting on a
shelf of a public list and turns the filter into a tour of other people's
rejected typing, which is worth less. So nothing ineligible is stored, and the
cost is admitted here rather than hidden: a gate that rejects too much leaves
no evidence that it did, and the only way to find out is to ask the library
something it should have kept and see what happens.

One exception, and it is not an exception to the test. A question the library
answered well fails gate three, and is kept: it is a real question, and "this
has an answer here" is worth showing. Only the junk goes unrecorded.

1. **Is it about autonomous organizations?** The scope judge already answers
   this on every ask. A question it calls out of scope is never eligible,
   however often it is asked. This is the only gate that rejects the asker
   rather than the library.

2. **Is it a question rather than a lookup?** "Do you have this paper?" and a
   bare URL have their answer in the index, not in the literature. A lookup is
   not an open question even when the index says no.

3. **Is it still unsettled here?** An answer that cited claims and came
   back at strong confidence has settled the question for this corpus. Only a
   question that came back `unread` or `nothing-held`, or was answered weakly,
   is eligible.

4. **Is it a research question this field could settle?** Two things at once,
   because the gate is useless without both. It has to be a question about
   machine agents holding authority, or an adjacent subject — multi-agent
   coordination, agent evaluation, identity, reputation, machine
   accountability. And a paper has to be able to close it: a prediction, a
   preference and a request for a definition cannot be, so none of them is an
   open problem however reasonable it is. The usable form is, can you name
   what a paper would have to report for the question to be closed?

   Every question goes to a judge for this; counting content words was tried
   first and is the wrong instrument, because it rejects a greeting for the
   wrong reason and rejects a terse real question for the same one.

   This gate is deliberately stricter than gate one, and the two pull in
   opposite directions on purpose. The scope judge that decides how to word a
   refusal leans towards "in scope", because telling somebody their real
   question is off-topic is the worse error when answering. The eligibility
   gate leans the other way, because the list is read by people deciding what
   to research and one that admits greetings is worth less than a short one.
   Both biases are correct for their own job; neither is correct for the
   other's. This was written after a greeting reached the list.

5. **Has somebody already asked it?** A near duplicate seconds the question
   that exists rather than starting a second one beside it. Without this gate
   the most-asked question is spread across nine rows and the list ranks
   phrasings instead of questions.

A maintainer can also mark a question ineligible, with a reason, recorded.
Five automatic gates will admit things that do not belong and reject things
that do, and a judgment that cannot be overridden by a person is a judgment
nobody can be held to.

### What the gates do not decide

Nothing here says a backed question is true, well posed, or worth answering.
It says a person asked it, the library could not answer it, and a paper could
in principle. The sentence that makes it a question in this corpus is still
written by hand, and `asserted_by` still records whose hand.

### Promotion

Not built. When it is, it should carry the reader-asked origin in the node
rather than losing it: a question that arrived this way has a different
warrant from one clustered out of seven gap claims, and a reader of
`questions.yml` should be able to tell them apart without consulting the
application.

## What is not built

- **Answering.** Nothing marks a question answered, and nothing proposes that
  a finding closes one. `status` is hand-set.
- **Review.** No question has been confirmed by a person, so every one of them
  says so in `asserted_by`.
- **Proposals as files.** `--propose` prints; the scout writes a candidate
  file with `--write`. When proposals are acted on by somebody other than
  whoever ran the command, they should be written down the same way.
