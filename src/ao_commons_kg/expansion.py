"""Growing the corpus from its own citations, automatically and with a bound.

The corpus should grow without waiting for someone to read a queue. Human
promotion does not scale, and a library that only grows when a maintainer has
an afternoon is a library that stops growing.

But "admit everything our papers cite" is not the alternative. Measured over
the 29 papers whose references were resolved first: 1,772 distinct cited
works, of which 1,758 were not held, and **93% were cited by exactly one of
our papers**. Projected across the whole corpus that is roughly 4,900
records, most of them optimization and neural-architecture background that
fails the scope test on sight. Admitting them would destroy the property that
makes this worth citing — that 87 curated records beat 8,500 uncurated ones.

So expansion is automatic and bounded, by three mechanisms that each stop a
different failure:

**A rising threshold** makes each hop outward strictly harder. Generation 1
needs 2 of our papers to cite it, generation 2 needs 3, generation 3 needs 4.
Admitted papers bring their own references, so a fixed bar would only delay
the explosion by a round. Note what this does and does not promise: it slows
growth sharply, because agreement between our own papers gets rarer the
further out you go, but it is not a termination proof — a sufficiently
famous work could clear any bar. The budget is the hard bound; this is what
keeps the budget from being spent on noise.

**A budget** stops a single run. Even a correct threshold can admit hundreds
the first time reference coverage jumps. The cap is per run and takes the
best candidates first, leaving the rest queued — a corpus that grows at a
rate nobody can skim is one nobody is checking.

**A scope scan** stops the wrong papers. This is the judgement, and it is the
part that must not be a keyword score: the README already records that the
keyword pre-filter scores *Institutions as cached computation for
resource-rational negotiation* at 1 and it is squarely in scope. The scan is
a model reading the abstract against the scope statement and the exclusion
register, and writing its reasoning down. Keywords rank; they do not admit.

Every admitted record says which papers cited it, what generation it is, and
why the scan let it through. That is the difference between a corpus that
grew and a corpus that drifted — and it is what makes a bad rule show up as a
readable pattern rather than a mystery pile.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

BASE_THRESHOLD = 2
"""Citations from held papers needed to admit at generation 1."""

DEFAULT_BUDGET = 40
"""Admissions per run. A dial, not a law — the right value is however many a
person would actually skim in one sitting."""


def threshold_for(generation: int, base: int = BASE_THRESHOLD) -> int:
    """How many of our papers must cite a candidate at this generation.

    Generation 1 needs `base`, and each hop outward adds one. A work five
    hops from anybody's judgement would need six of our papers to cite it,
    and agreement between our own papers gets rarer the further out you go —
    so growth falls off sharply with depth. Sharply, not to zero: this is a
    brake, and the budget is the bound.
    """
    if generation < 1:
        raise ValueError("generation 0 is what a person chose; it is not admitted")
    return base + (generation - 1)


@dataclass(frozen=True)
class Candidate:
    """A cited work that is not in the corpus, and the case for admitting it."""

    key: str
    """Canonical key — the same identity the citation graph joins on."""
    cited_by: tuple[str, ...]
    """Held records that cite it. The evidence, and the reason this is a
    structural signal rather than a keyword one: a work several of our papers
    cite is part of this conversation by the field's own behaviour, whatever
    its title says."""
    generation: int
    """One hop beyond the *closest* paper that cites it. Closest, not
    furthest: being cited by an original seed is a stronger claim to
    relevance than being cited by something admitted three hops out, and the
    candidate should be judged at its best case."""

    @property
    def support(self) -> int:
        return len(self.cited_by)

    def clears(self, base: int = BASE_THRESHOLD) -> bool:
        return self.support >= threshold_for(self.generation, base)


@dataclass(frozen=True)
class ScopeVerdict:
    """What the scan decided, and why."""

    admit: bool
    reasoning: str
    judged_by: str

    def __post_init__(self) -> None:
        if not self.reasoning.strip():
            raise ValueError(
                "a scope verdict with no reasoning cannot be audited, and an "
                "unauditable admission is how a corpus drifts without anyone "
                "being able to say when"
            )


ScopeJudge = Callable[[Candidate, dict], ScopeVerdict]
"""Reads a candidate and its metadata, returns a verdict.

Injected rather than imported, on the same reasoning as the HTTP fetchers:
the decision logic has to be testable without a network or a model, and the
model behind it has to be swappable without touching the selection rules.
"""


@dataclass
class Selection:
    """What one expansion run decided."""

    admitted: list[Candidate] = field(default_factory=list)
    rejected: list[tuple[Candidate, ScopeVerdict]] = field(default_factory=list)
    below_threshold: list[Candidate] = field(default_factory=list)
    over_budget: list[Candidate] = field(default_factory=list)

    def summary(self) -> str:
        return (f"{len(self.admitted)} admitted, {len(self.rejected)} out of scope, "
                f"{len(self.below_threshold)} below threshold, "
                f"{len(self.over_budget)} deferred to the next run")


def find_candidates(
    references: dict[str, list[str]],
    held_keys: dict[str, str],
    generations: dict[str, int],
) -> list[Candidate]:
    """Every cited work we do not hold, with the papers that cite it.

    `references` maps a held record id to the canonical keys it cites,
    `held_keys` maps a canonical key to the record holding it, and
    `generations` gives each held record's generation.

    Sorted by support and then by key, so two runs over the same corpus
    propose the same things in the same order. An expansion whose output
    depends on dict ordering would make a diff between runs unreadable.
    """
    support: dict[str, set[str]] = {}
    closest: dict[str, int] = {}

    for citing_id, cited_keys in references.items():
        if citing_id not in generations:
            continue          # a reference list for a record we no longer hold
        citing_generation = generations[citing_id]
        for key in cited_keys:
            if key in held_keys:
                continue      # already in the corpus; this is a CITES edge, not a candidate
            support.setdefault(key, set()).add(citing_id)
            proposed = citing_generation + 1
            closest[key] = min(closest.get(key, proposed), proposed)

    return sorted(
        (Candidate(key=key, cited_by=tuple(sorted(ids)), generation=closest[key])
         for key, ids in support.items()),
        key=lambda c: (-c.support, c.generation, c.key),
    )


def select(
    candidates: Iterable[Candidate],
    *,
    judge: ScopeJudge | None = None,
    metadata: Callable[[Candidate], dict] | None = None,
    base: int = BASE_THRESHOLD,
    budget: int = DEFAULT_BUDGET,
) -> Selection:
    """Apply the threshold, the scope scan, and the budget, in that order.

    Order matters and is chosen for cost. The threshold is free arithmetic
    and removes ~93% of candidates, so it runs first. The scan costs a model
    call per candidate, so it only ever sees what cleared. The budget applies
    last, to what survived both, because deferring a paper that would have
    failed the scan anyway wastes a slot in the next run.

    With no `judge`, nothing is admitted. That is deliberate: the fallback for
    a missing scope test is not a keyword score, it is a queue. A run with no
    judge configured should look like it did nothing, not like it approved
    everything.
    """
    selection = Selection()
    cleared: list[Candidate] = []

    for candidate in candidates:
        (cleared if candidate.clears(base) else selection.below_threshold).append(candidate)

    if judge is None:
        selection.over_budget.extend(cleared)
        return selection

    for candidate in cleared:
        if len(selection.admitted) >= budget:
            selection.over_budget.append(candidate)
            continue
        verdict = judge(candidate, (metadata or (lambda _: {}))(candidate))
        if verdict.admit:
            selection.admitted.append(candidate)
        else:
            selection.rejected.append((candidate, verdict))
    return selection


def provenance(candidate: Candidate, verdict: ScopeVerdict, titles: dict[str, str]) -> str:
    """What an auto-admitted record says about how it got here.

    Written out in full rather than as a code, because this is the field a
    reader consults when they are surprised to find something in the corpus,
    and "expansion gen 2" answers nothing.
    """
    citing = "; ".join(sorted(titles.get(rid, rid)[:60] for rid in candidate.cited_by))
    return (
        f"admitted automatically at generation {candidate.generation} by citation "
        f"expansion: cited by {candidate.support} records already held, which is at "
        f"or above the threshold of {threshold_for(candidate.generation)} for this "
        f"generation. Citing records: {citing}. "
        f"Scope scan by {verdict.judged_by}: {verdict.reasoning} "
        f"Unreviewed, like everything that has not been through the review queue — "
        f"and machine-admitted as well as machine-resolved, so the scope judgement "
        f"here is a model's until a person confirms it."
    )
