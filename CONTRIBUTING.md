# Contributing

Two forms and a pull request. Corrections are worth more than additions.

## Correct something

**[Open the correction form →](https://github.com/AO-Commons/knowledge-graph/issues/new?template=request-adjustment.yml)**

Nothing here has been checked by more than one person and most of it has not
been checked by one. The most useful thing you can send is a claim that does
not say what its paper says.

Every claim carries the sentence it was drawn from, so the two can be compared
without opening the PDF. If they disagree, say so — quoting the sentence the
paper actually uses is the whole correction.

Also worth sending: wrong metadata, a topic that does not fit, an attribution
that credits the wrong person, or a record that should not be here at all.

**If you wrote the work**, say so on the form. An author's verdict is recorded
as an author's, which is a fact about the reviewer rather than a higher score:
you are the highest authority on whether a claim says what your paper says, and
the least disinterested party on whether it overstates.

## Suggest something

**[Open the suggestion form →](https://github.com/AO-Commons/knowledge-graph/issues/new?template=suggest-addition.yml)**

One form for a paper, a tool, a deployment, an organization, a person or an
article. A link is usually enough.

A bot judges it against the scope test below, usually within a minute. If it
passes, the metadata is resolved and the record joins the corpus as
`unreviewed`, with your name on the proposal. If it does not, the reasoning is
posted on the issue — the boundary is meant to be contestable, and that is how
you contest it.

### The scope test

> An item belongs if it would change how you design, operate, oversee, or hold
> accountable an organization where agents act with real authority.

Work about human collective decision-making that would be the same without
machines does not belong, however good it is. The question that decides a hard
case is **what changes because machine agents hold authority**.

The [exclusion register](taxonomy/agentic-org-research-library-taxonomy-v3.md)
says what has been turned away and why, so the boundary is contestable rather
than invisible. It flags three exclusions as genuinely arguable. If yours is
relevant by transfer rather than directly — the economics and law the field
borrows its vocabulary from — say so, and it is held as background the library
points at rather than reads.

## Taxonomy changes

The v3 taxonomy is a seed, not scripture — but its codes are stable
identifiers other people's tags point at. In this order:

1. Would an **alias** solve it?
2. Would **multi-tagging** across existing topics cover it?
3. Would a **cross-link** between two topics express the relationship?
4. Only then, a **new topic** — through
   [the taxonomy form](https://github.com/AO-Commons/knowledge-graph/issues/new?template=taxonomy.yml),
   stating the code, its parent, the rationale, and why the existing nodes are
   insufficient.

Two rules that do not bend:

- **Codes are never renumbered or reused.** A deprecated topic keeps its code
  forever so old tags stay resolvable.
- **No new top-level sections** unless the corpus shows a gap none of the 16
  can hold.

## Code

```bash
pip install -e ".[dev]"
pytest
```

Keep it small and boring. A new dependency needs a reason, and "it is more
elegant" is not one. The taxonomy tests run against the real v3 file rather
than a fixture, so a change that breaks the actual source fails loudly.

If you add an edge type, it must be able to say where it came from. Anything
non-deterministic carries a `confidence_class` and the source it was drawn
from — a relationship nobody can trace is worse than a missing one.

## Reviewing claims

Judging a claim against its paper happens in the signed-in application rather
than here, so that an author can be invited to review claims about their own
work. If you want to review, say so on a correction form and you will be
invited.

## Terms

Contributions are licensed [CC BY 4.0](LICENSE); code is additionally MIT. By
contributing you confirm you have the right to license the material that way.

Please do not include personal information about third parties. Participation
is governed by our [Code of Conduct](CODE_OF_CONDUCT.md).
