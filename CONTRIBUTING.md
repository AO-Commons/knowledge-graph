# Contributing

The most valuable contributions are corrections and missing evidence, in that order.

## What helps most

**Research we've missed.** A paper, postmortem, standard, or implementation that belongs in the library and isn't there. Say which taxonomy topic it belongs under if you know.

**Misclassifications.** A resource tagged to the wrong topic, or given a facet value the source doesn't support. Classification is partly automated, so this is expected and useful.

**Scope arguments.** If we've included something that fails the scope test, or excluded something that passes it, say so. The [exclusion register](taxonomy/agentic-org-research-library-taxonomy-v3.md) exists so the boundary is contestable rather than invisible — the taxonomy itself flags three exclusions as genuinely arguable.

## The scope test

Everything in the library has to pass it:

> An item belongs if it would change how you design, operate, oversee, or hold accountable an organization where agents act with real authority.

Material about human collective decision-making that is unchanged by the presence of machine agents does not belong, however good it is. If you're proposing something the register excludes, the thing to argue is **what changes because machine agents hold authority**.

## Taxonomy changes

The v3 taxonomy is a seed, not scripture — but it is a set of stable identifiers that other people's tags point at. Changes are deliberate, in this order:

1. Would an **alias** solve it? A synonym on an existing topic makes it findable.
2. Would **multi-tagging** across existing topics cover it?
3. Would a **cross-link** between two existing topics express the relationship?
4. Only then, propose a **new topic**.

A proposal goes in `taxonomy/proposals/` and states the proposed code, its parent, a title, the rationale, example resources that need it, and why the existing nodes are insufficient.

Two rules that don't bend:

- **Codes are never renumbered or reused.** A deprecated topic keeps its code forever so old tags stay resolvable.
- **No new top-level sections in V1** unless the corpus shows a persistent gap that none of the 16 can hold.

## Code

```bash
pip install -e ".[dev]"
pytest
```

Keep it small and boring. A new dependency needs a reason, and "it's more elegant" is not one. The taxonomy tests run against the real v3 file rather than only a fixture, so a change that breaks the actual source fails loudly.

If you add an edge type, it must be able to say where it came from. Anything non-deterministic carries a `confidence_class` and the source it was extracted from — a relationship nobody can trace is worse than a missing one.

## Terms

Contributions are licensed [CC BY 4.0](LICENSE); code is additionally MIT. By contributing you confirm you have the right to license the material that way.

Please don't include personal information about third parties. Participation is governed by our [Code of Conduct](CODE_OF_CONDUCT.md).
