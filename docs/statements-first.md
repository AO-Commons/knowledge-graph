# Statements first

**Status:** proposal, not yet built. Argued here before any code moves, because
it changes what the project is rather than how it works.

For how the corpus is processed today, stage by stage, see
[pipeline.md](pipeline.md).

## The claim

A paper is a container. The answerable thing is inside it.

Today the library files papers on a taxonomy and, separately, extracts
statements from a few of them. The proposal is to make statements the unit
that carries meaning — tags, relations, retrieval — and let a paper's place in
the taxonomy be **derived from the statements it contains** rather than
asserted about the paper as a whole.

## Why the corpus already says this

Three pieces of evidence, none of them new.

**Two thirds of records need more than one topic.** 67 of 101 carry multiple
codes; the median is two and one carries seven. That is not filing. It is
somebody trying to describe a container by listing its contents, and reaching
for a second code because the first one was not a lie but was not the whole
truth either.

**The taxonomy collapse was evidence for this, read as evidence about
something else.** In August, 568 codes became 103 because 93% of tags landed
at subsection level and 458 leaves held nothing at all. The conclusion drawn
was that the leaf layer was too fine. The better conclusion is that *a paper
is too coarse an object to carry a fine tag* — because the concept vocabulary,
which is exactly as fine-grained, works perfectly well on statements. 523
terms, 17 in use across 40 claims, and they cluster meaningfully enough that
25 candidate pairs produced 3 real relations.

**The two tagging layers on a claim already disagree.** A claim carries
`topic_codes` (where it suggests the record belongs) and `concept_tags` (what
it argues about). On `arxiv:2511.03434` claim 2 those are `[10.1, 4.4]` and
`[agent-reputation-systems]` — which resolves to `5.3`. Two answers to
overlapping questions, reconciled nowhere. Deriving one from the other removes
the contradiction rather than documenting it.

## What we measured

Derived topics for the six papers that have statements — the union of the
taxonomy codes their concept tags sit under — against what a person filed.

| Paper | Hand-filed | Derived | Agreed | Lost | Gained |
|---|---|---|---|---|---|
| Melting Pot | 14.1, 14.5 | 14.1, 14.3, 5.2, 5.3, 8.2 | 14.1 | **14.5** | 14.3, 5.2, 5.3, 8.2 |
| Beyond the High Score | 14.1, 5.2 | 14.1, 14.3, 5.2 | both | — | 14.3 |
| Inter-Agent Trust Models | 4.4, 5.3 | 2.7, 5.3 | 5.3 | **4.4** | 2.7 |
| Dissociative Identity | 5.3, 6.3 | 2.7, 5.3, 6.3 | both | — | 2.7 |
| Solipsistic Superintelligence | 1.2, 15.3, 5.2 | 14.1, 14.3, 5.2 | 5.2 | **1.2, 15.3** | 14.1, 14.3 |
| Building the Loop | 16.1, 16.4 | 16.1, 2.4 | 16.1 | **16.4** | 2.4 |

**The gains are right.** Melting Pot picks up 14.3 (evaluation integrity)
because one of its own statements predicts the suite will be gamed, and 5.2
and 5.3 because another says solving it requires modelling trust and
deception. Nobody filed it there. It belongs there, by its own words.
Dissociative Identity and Inter-Agent Trust Models both pick up 2.7 (machine
participation in governance), which is exactly what their recommendations are
about.

**The losses are a real finding, not noise.** Four papers lose a code, and the
lost codes have a shape: `1.2` agency and organizational theory, `15.3`
borrowed background, `16.4` research methods, `14.5` MARL environments. These
describe **what kind of intellectual move the paper makes** — it reframes a
field, it borrows from an adjacent one, it contributes a method — rather than
what it asserts.

So: *statement concepts capture what a paper says; they do not capture what a
paper is.* A paper whose contribution is a reframing makes that contribution
at the level of the whole, and no individual sentence in it carries the frame.

That is the thing to design around, and it is the argument against a pure
switch.

## Two kinds of statement

Not all five types do the same work, and the corpus says which.

**Findings and positions are what the library is asked for** — what has been
shown, and what has been argued. **Background, method and limitation are
context**: how a researcher judges a finding once they have one, rather than
the thing they were searching for.

```
10 of the first 12 asserted relations run between findings and positions
 8 of 11 proposed pairs involved a context statement — and produced nothing
```

The argument a field is having is carried almost entirely by two of the five
types. Context enters that argument as *grounds* — a background premise
supporting a finding — rather than as a participant in it.

So the two behave differently. Linking proposes between primaries, because
otherwise most of a reviewer's attention goes to pairs the corpus has never
once produced a relation from. And context travels *with* its primary,
from its own paper, rather than being returned beside it in a search:
asking for a finding should hand back the background it rests on, the method
that produced it, and the limitation its authors put on it.

This is a reading of the types rather than a new field. Nothing is tagged
primary; it follows from what kind of statement it is.

## The design

**Statements carry the specific tags.** Fine-grained on purpose: the finer the
tag, the better it proposes relations, which is the whole reason the layer
exists. `sanction-sensitivity` is a better tag than `inter-agent trust`
because two claims sharing it are worth reading together, and two claims
sharing the second are not.

**Every statement tag belongs to a taxonomy category.** Already true —
`Concept.topics` records it, and 514 of the 523 terms inherited their category
by being demoted taxonomy leaves. This is the join that makes the rest work.

**A paper's categories are derived, plus a small asserted remainder.** The
union of its statements' concepts' topics, which is computed and needs no
judgement — and papers land in several categories naturally, because their
statements do. Alongside that, a short hand-filed list for the framing codes
derivation cannot see. Two fields, differently sourced, each honest about
which it is.

**Citations stay paper-level and become a proposal signal.** A citation
supports a statement in the world, but the data available is paper to paper;
getting to statement level needs citation contexts from full text, and yields
an *inferred* edge where we currently have the only *read* one in the graph.
So keep `CITES` as it is, and use it the way concept tags are used — if A
cites B, A's statements are candidates for relations to B's statements.

That is cheap and already meaningful: the one citation edge today whose ends
both have statements is `2509.14485 → 2107.06857`, worth 63 candidate pairs,
and two of the relations we found by hand are exactly that pair. The signal is
real and starved of coverage rather than of ideas.

## Extraction becomes the load-bearing process

If statements are the unit, extraction quality is the whole product, and it is
currently a one-off: 40 claims from 6 papers, three-pass over full text, one
model, one afternoon, unreviewed. That does not scale and it has never been
measured.

What the process needs before it carries the library:

1. **A stated unit.** One assertion, one subject. SciFact's criteria — fluent,
   atomic, decontextualised, faithful — are already cited in the model and
   should become the extraction contract rather than a docstring.
2. **A yield target.** Melting Pot produced 14 claims and Building the Loop
   4; after the editorial pass, 9 and 4. The variance tracked how much methods
   detail a paper had, not how much it contributed. Five of the 45 were cut as
   artifact trivia — *"contains more than 80 scenarios"* — and a process that
   produces 11% waste needs a rule about what is not a claim.
3. **Attribution at extraction time.** Five of 40 were the paper reporting
   prior work, and were found by a person rereading them afterwards. The
   extractor should be asked the OWN/OTHER question directly.
4. **Tagging as part of extraction, checked against the vocabulary.** A
   concept that does not resolve should fail loudly, as it does now, rather
   than quietly producing a statement nothing can link to.
5. **Measurement.** The gold set has one entry. Until extraction has an
   accuracy number, "statements are first class" is an aspiration with 40
   examples.

## Sequencing, and the thing that makes this hard

Statement extraction is roughly seven judgements per paper against one for
filing. The Tuesday bot admits about eight papers a week. **Extraction cannot
keep pace with intake unless it is automated, and automated extraction is
unreviewed by definition** — which is the same bind the scope scan is in, and
should be answered the same way: let the machine produce, mark clearly what is
unconfirmed, and let human review of the output be both the quality signal and
the evidence for loosening the rules.

The order that avoids a cliff:

1. Derive paper categories from statement concepts **as an additional view**,
   next to the hand-filed ones. Costs nothing, reveals disagreement
   immediately, changes no existing data.
2. Add citations as a second relation-proposal signal. One edge today, free
   later.
3. Fix extraction as a measured process, and run it over the next twenty
   papers rather than six.
4. Only when statement coverage is broad enough that derived categories cover
   most of the corpus, let hand-filing wither — for the codes derivation can
   see. Keep the framing codes.

Switching today would take the navigable corpus from 101 records to 6. The
destination is right; the cliff is avoidable.

## What this changes about the project

Not a better-organised library. A map of what the field asserts, and where it
disagrees with itself.

That is the thing both researchers asked for in different words — *find who
has already said this*, and *show me the camps and the gaps* — and neither is
answerable by a well-filed pile of papers, however well filed.
