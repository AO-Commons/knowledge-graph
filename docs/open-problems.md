# Open problems

How a question gets onto the open problems surface, what it is made of, and
what the numbers beside it count.

**Status:** live as of 2026-10-09. Argued on the roadmap for months before it
was built, under its MIRA names, which is why the vocabulary below was not
invented here.

For the extraction pass that produces the raw material, see
[pipeline.md](pipeline.md), stage 4.

## The distinction the layer exists for

A `gap` statement is one paper saying something is unresolved — in that
paper's words, bounded by that paper's scope, and carrying the quote it was
read out of. Seven of those are held today.

A **question** is the thing several of those turn out to be asking. It is not
a summary of them and not a ninth kind of statement. It is a node, and each
gap reaches it by an **`addresses`** edge that keeps its own quote, its own
paper and its own wording.

Both names are [MIRA](https://github.com/mira-rg)'s, a shared schema for
research graphs, as the four claim-to-claim relations are CiTO's. Adopting
somebody else's word for a layer we had not built cost nothing and means an
outside reader already knows what the edge asserts.

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
| `note` | why these statements are one question | yes |
| `concept_tags` | the concepts it sits under | no |
| `status` | `open`, `answered`, or `retired` | defaults to `open` |
| `asserted_by` / `asserted_on` | who made the judgment, and when | no, but say it |
| `addressed_by` | the statements asking it, each with a `because` | yes, at least one |

Two of those are load-bearing and the loader refuses a file without them.

**`note` is the judgment.** Everything else in a question is bookkeeping; the
note is the claim that these particular sentences are one question, and it is
the thing a reader most needs to be able to disagree with. A question whose
note does not survive reading its statements is wrong, and that is the whole
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
statements asking it. Whether anyone has answered it is what the statements
bearing on it are for, and the corpus is far too thin to say so — 7 papers of
257 have been read down to their statements at all.

This is why `status` exists and why it is not computed. "Answered" is a
judgment somebody makes after reading, not a count of findings.

## The two numbers, and why they are two

```
papers        distinct papers holding a statement that addresses it
occurrences   statements that address it
```

A question asked twice by one paper is that paper's framing. A question asked
by two papers is a statement about a field. That difference is the only reason
this layer is worth building, so it is counted rather than implied, and
showing a single number over both would let the first pass for the second.

`questions.reach()` returns them separately, and the test that pins them is
`test_papers_and_occurrences_are_counted_apart`.

## What the corpus holds today

Seven gap statements from four papers, clustering into four questions.

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

- a `text` that is not phrased as a question — a statement there would be a
  claim nobody made
- a question no statement addresses — one the corpus cannot show anybody
  asking is an opinion, not a finding
- an occurrence with no `because` — an unexplained judgment cannot be told
  from a guess
- an occurrence naming a statement we do not hold — it was cut, renamed, or
  never extracted, and an edge to nothing would make the layer's claim false
  while still rendering
- a duplicate `id`
- a missing `note`

`test_every_gap_statement_is_accounted_for` adds one more, from the other
direction: a gap that reaches no question fails the suite. A gap the layer
silently drops is worse than one it clusters wrongly, because a wrong cluster
is visible and an absence is not. That test is what caught two gap statements
missing from the first draft of `questions.yml`.

## Adding or correcting one

1. Read the gap statements that look related, with their quotes.
2. If they are one question, add it to `data/questions.yml` with a `note`
   that says why, and an occurrence per statement with its own `because`.
3. If a cluster is wrong, the fix is usually the note: either it describes a
   question the statements are not asking, or it is vague enough to cover
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
`position`, `gap` or `limitation` statements — and **nothing has been shown on
it**: one `finding` carrying the concept and it is not proposed at all.

That last bound is the one worth arguing about. It separates "nobody has shown
this" from "somebody has, and you have not read it", and loosening it would
produce a longer list of weaker proposals, which is the failure this
repository exists to avoid. Concepts already covered by a question are left
out, because noise in a proposal list is what stops anybody reading it.

A proposal is not a question. A question is the sentence somebody writes after
reading the statements, and no amount of counting produces that sentence. The
command prints the statement ids so the reading can start.

Two concepts qualify today: `sources-of-legitimate-machine-authority` and
`legitimacy-erosion-through-automation`.

## What is not built

- **Answering.** Nothing marks a question answered, and nothing proposes that
  a finding closes one. `status` is hand-set.
- **Review.** No question has been confirmed by a person, so every one of them
  says so in `asserted_by`.
- **Proposals as files.** `--propose` prints; the scout writes a candidate
  file with `--write`. When proposals are acted on by somebody other than
  whoever ran the command, they should be written down the same way.
