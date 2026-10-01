# Auditing the statements against the papers

**2026-10-01.** Every paper holding statements was re-read against its full
text. Building the Loop was re-read and corrected first (#55). The other six
were audited the same way, and nothing in them has been changed yet. This
records what the audit found, what the checks added afterwards would and
would not have caught, and what needs a person.

## How

One model per paper, which did not draft that paper's statements, with the
cached arXiv HTML, the repository's parser and `verbatim` check, and a fixed
rubric:

- quote
- type
- attribution
- paraphrase
- standalone
- tags
- provenance
- coverage by section
- missing statements, each with a quote confirmed verbatim

Human verdicts in `evals/gold/claims.yml` were treated as outranking the
audit. Where an audit disagreed with one, it says so and recommends raising it
with the reviewer. It never overrides a verdict.

These are machine readings, unconfirmed, like any other draft.

## What it found

| Paper | Statements | Human verdicts | Need a change | Type changes | Paraphrase says more than the quote | Tag changes | Body with no statements |
|---|---|---|---|---|---|---|---|
| Melting Pot | 6 | none | 6 | 0 (1 attribution) | 4 | 4 | Experiments, the evaluation protocol |
| Vending-Bench | 8 | 8, by an author | 6, none to text or quote | 0 | 0 | 4 | Both trace analyses |
| Beyond the High Score | 7 | none | 6 | 1 | 5 | optional | Every results section |
| Inter-Agent Trust Models | 6 | 6, by an author | 6 | 2 (1 attribution) | 2 | 4 | The whole body |
| Dissociative Identity | 9 | 9, six by an author | 8 | 3 (1 attribution) | 1 | 4 | Sections 1–4 |
| Solipsistic Superintelligence | 12 | none | 10 | 4 | 6 | 4 | 12 of 21 sections |
| **Total** | **48** | | **42** | **10** | **18** | **~20** | **every paper** |

**Eight of the seventeen findings are not findings.** They are conclusions of
arguments, in papers that run no experiments. "Our study finds that no single
trust mechanism is sufficient" ends a qualitative comparison. "It is then
plausible that leading submissions exploited the evaluation" is an inference.
The nine that stand are the measured ones: Vending-Bench's five, three of
Beyond the High Score's four, and Melting Pot's one.

**Eighteen paraphrases say more than their quote.** "Seems to require"
became "requires". "May be costly or impossible" became "not at any acceptable
cost". "Plausible" was dropped. "Must" became "should". "Within the Melting Pot
suite" became a general claim about multi-agent evaluation. This is the failure
an author is most entitled to object to, and it was in five of the six
papers.

**No paper's statements reached its body.** Statements came from the
abstract, the introduction and the conclusion. The experiments, trace
analyses, analyses of each mechanism, and whole chains of argument carried
none. A reader asking what a paper showed was given the paper's summary of
itself.

**Tags were wrong in ways that propagated.**
- Some contradicted their statement. `stake-based-trust` was on "where stakes
  are high". `dynamic-evaluation` was on a suite whose background populations
  are fixed at test time. `agent-generated-evaluation-and-scoring` was on
  scenario generation.
- One was a blanket. `endogenous-non-stationarity` was on seven of twelve
  statements.
- Several were filed under topics their statements never mention.

The derived-topic table in `docs/statements-first.md` rests partly on these.
Its "gains are right" examples include a 2.7 for Inter-Agent Trust Models that
comes only from the "stakes" tag, and a 14.3 for Melting Pot that cites a
statement no longer in the corpus. That table needs re-measuring after the
fixes, not before.

**Three statements credited the wrong party.** A sentence the paper cites to
Raskar et al. was filed as the authors' own. A survey's open problem (Reuel et
al.) was filed as the authors' own. Melting Pot's own judgment of the field
was filed as somebody else's.

**Some asserted relations misstate a paper.** All twelve were drafted by a
model and are unconfirmed.
- `2606.03237:6 DISAGREES_WITH 2107.06857:5` has the Solipsistic paper
  rejecting Melting Pot's approach. The paper cites Melting Pot as a step
  forward, and two authors are shared.
- `2509.14485:4 SUPPORTS 2509.14485:3` points the wrong way.
- Several `because` texts repeat a hardened paraphrase.

## What the checks would have caught

Five checks were added to the drafting gates after this audit (see
`docs/reading-a-paper.md`). Run over the same 48 statements:

| Failure | Audit found | Checks flag |
|---|---|---|
| Substantial body section with no statement | every paper | every paper with a cached body |
| Tag on more than half of a paper's statements | 2 papers | both, plus one the audit judged acceptable |
| Paraphrase surer than its quote | 18 | 5 |
| Finding quoted as argued | 8 | 1 |
| Term not typed definition | 2 | 1 |

The checks find structural failures reliably and failures of meaning only
sometimes. A paper that says "our study finds" about an argument, or a
paraphrase that drops "in combination", needs a reader. So the full-text audit
should not be a one-off. It should be a standing step between drafting and
review, done by a model that did not draft the statements, using the rubric
above. Its report goes to the person reviewing.

## Also found

- **The parser misfiles sections.** Headings containing "evaluation" are filed
  as results and headings containing "model" as method. Dropped parent
  headings leave sections labeled `other`. Appendices and figure captions are
  not parsed at all, so `text_coverage: full-text` means the body only, and
  `extracted_from` should be set by hand.
- **Two conceptual papers are faceted `empirical-single-study`** (Dissociative
  Identity, Solipsistic Superintelligence). That facet is first-pass and
  unreviewed.
- **The flagship joined query depends on a definition typed `method`.**
  "Findings about the train-test-deploy gap by people doing dynamic
  evaluation" answers through `2606.03237:5`, a paper that defines dynamic
  evaluation and performs none. Retyping it empties the example.

## What needs a person

- **Inter-Agent Trust Models and Dissociative Identity:** the type changes,
  attribution changes and tag changes go to their author-reviewer
  (helenarong2703). Her verdicts were on whether each paraphrase is accurate,
  and they stand. She was not asked about types, and the `definition` type did
  not exist when she reviewed. Three of Dissociative Identity's statements
  have verdicts by ankeliu.
- **Vending-Bench:** the tag and standalone changes go to its
  author-reviewer (Axelmannen). None touches a verdict.
- **Melting Pot, Beyond the High Score and Solipsistic Superintelligence:**
  these have no verdicts. The fixes are ready to apply as drafts, then review.
- **The flagship query and its test:** a decision about what the example
  should demonstrate.
