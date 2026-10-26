# Audit brief

What a model auditing one paper's drafted claims is asked to do. It was
used for the audit in
[evals/results/2026-10-01-statement-audit.md](../results/2026-10-01-statement-audit.md),
and is the standing step between drafting and review described in
[docs/reading-a-paper.md](../../docs/reading-a-paper.md).

The auditor must not be the model or session that drafted the claims. It
reads; it does not edit. Its report goes to the person reviewing.

---

You are auditing the claims held for **one paper** against the paper's
full text. Read only; change nothing.

**Read first.**
- The paper's claims: `data/claims/<paper>.yml`.
- The record: `data/resources/<paper>.yml`.
- The full text: `data/cache/fulltext/<arxiv id>.html`. Parse it with
  `ao_commons_kg.fulltext.parse` and check quotes with `verbatim`. Read the
  whole body, not only the abstract, introduction and conclusion.
- The rules: the `ClaimType` and `Attribution` docstrings in
  `src/ao_commons_kg/models.py`, and `docs/reading-a-paper.md`.
- The vocabulary: `data/concepts.json`, both `vocabulary` and `suggestions`.
- Human verdicts: `evals/gold/claims.yml`. A verdict outranks you. Report a
  problem on a claim with a verdict as "has human verdict: <verdict> by
  <reviewer>", and recommend raising it with them. Never recommend overriding
  a verdict.
- Relations: `data/claim-relations.yml`. Note any relation a change would
  affect.

**For each claim:**
1. **Quote.** Is it verbatim, and in which section, compared with `extracted_from`?
2. **Type.** Above all: is an evidence claim observed or measured in this work, or argued?
3. **Attribution.** Own, or another's? Is `attributed_to` right?
4. **Paraphrase.** Does `text` say exactly what the quote says, with no widened
   scope, hardened or softened modal, dropped hedge, or added cause?
5. **Standalone.** Is it the claim made checkable cold, or a note about the paper?
6. **Tags.** Does each name what the claim argues about? Flag a blanket tag,
   a contradicting tag or an implausible topic. Name a better existing term
   before proposing a new one.
7. **Provenance.** Is `extraction_method` truthful about what was read?

**For the paper:**
- Coverage: the sections, and how many claims each carries.
- Up to six missing claims, most important first. Each needs a quote
  confirmed verbatim, a type, an attribution, a `text` and tags.
- Claims to cut, which means artifact trivia or duplicates.

**Report:** summary with counts; one block per claim (verdict, reason,
exact proposed replacement); missing; paper-level issues; and where you are
unsure, say so.
