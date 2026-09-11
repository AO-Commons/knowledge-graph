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

Expansion walks **both directions**, and that is what keeps it from only ever
finding old work. Backward: works our papers cite, read free from the
reference store. Forward: works that cite ours, one query per held record and
the only route by which a paper published this month can be reached — it has
been cited by nobody and can never clear a backward threshold, but it can
cite three of ours the day it appears.

Both count the same toward support, because "three of ours cite it" and "it
cites three of ours" are equally strong evidence of belonging to this
conversation.

It is bounded by three mechanisms that each stop a different failure:

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
    """A work not in the corpus, and the case for admitting it."""

    key: str
    """Canonical key — the same identity the citation graph joins on."""
    cited_by: tuple[str, ...]
    """Held records that cite it — the backward direction. Our corpus builds
    on this work."""
    generation: int = 1
    """One hop beyond the *closest* connected paper. Closest, not furthest:
    being connected to an original seed is a stronger claim to relevance than
    being connected to something admitted three hops out, and the candidate
    should be judged at its best case."""
    cites: tuple[str, ...] = ()
    """Held records that *it* cites — the forward direction. This work builds
    on our corpus.

    The direction that makes new research reachable. A paper published last
    month has been cited by nobody and can never clear a backward threshold,
    however plainly it belongs; but it can cite three of ours on the day it
    appears. Growing only backward drifts toward the foundational, which is
    the failure `expand_neighborhood` was already written to avoid and this
    path had quietly reintroduced.

    Last in the field order on purpose: `generation` stays third so every
    existing positional construction keeps meaning what it did."""

    @property
    def connected(self) -> tuple[str, ...]:
        """Held records connected by a citation in either direction."""
        return tuple(sorted(set(self.cited_by) | set(self.cites)))

    @property
    def support(self) -> int:
        """How much of our corpus is connected to this work.

        Both directions count the same, and that symmetry is the point. "Three
        of our papers cite it" and "it cites three of our papers" are equally
        strong evidence that a work is part of this conversation — the first
        says the corpus builds on it, the second says it builds on the corpus.
        Counting only the first makes the library structurally unable to admit
        anything published recently.
        """
        return len(self.connected)

    @property
    def direction(self) -> str:
        if self.cited_by and self.cites:
            return "both"
        return "cites us" if self.cites else "we cite"

    def clears(self, base: int = BASE_THRESHOLD) -> bool:
        return self.support >= threshold_for(self.generation, base)


@dataclass(frozen=True)
class ScopeVerdict:
    """What the scan decided, and why.

    Three states, not two. The corpus already distinguishes a record that
    is about agentic organizations from one it holds as *borrowed
    background* — Melting Pot and SocialJax are both marked
    `is_borrowed_background`, and section 15 exists to point at adjacent
    literatures rather than ingest them.

    A binary scan cannot express that, so it was forced to refuse work the
    corpus's own convention would admit-and-flag. The first live run turned
    away a MARL benchmark on exactly those grounds while holding two others.
    """

    admit: bool
    reasoning: str
    judged_by: str
    borrowed_background: bool = False
    """Admitted, but as adjacent material rather than as core scope. Sets
    `is_borrowed_background` on the record, which is how a reader and the
    query layer already tell the two apart."""

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

    unresolvable: list[Candidate] = field(default_factory=list)
    """Candidates with no title, so nothing to judge.

    Kept apart from refusals because they are a different fact. A refusal
    says a work does not belong; this says the index could not tell us what
    the work is. Filing the second as the first pays for a model call to
    learn what an empty title already said, and buries a data problem inside
    a scope decision — where it would be re-proposed and re-refused every
    week, looking like a judgement."""

    admitted: list[tuple[Candidate, ScopeVerdict]] = field(default_factory=list)
    """Kept with the verdict that let each one in, not just the candidate.
    The reasoning goes into the record's `source_provenance`, and fetching
    it again later would mean paying for the model call twice and possibly
    getting a different answer than the one the record was admitted on."""
    rejected: list[tuple[Candidate, ScopeVerdict]] = field(default_factory=list)
    below_threshold: list[Candidate] = field(default_factory=list)
    over_budget: list[Candidate] = field(default_factory=list)

    def summary(self) -> str:
        parts = [f"{len(self.admitted)} admitted",
                 f"{len(self.rejected)} out of scope",
                 f"{len(self.below_threshold)} below threshold",
                 f"{len(self.over_budget)} deferred to the next run"]
        if self.unresolvable:
            parts.append(f"{len(self.unresolvable)} unresolvable")
        return ", ".join(parts)


def find_candidates(
    references: dict[str, list[str]],
    held_keys: dict[str, str],
    generations: dict[str, int],
    citers: dict[str, list[str]] | None = None,
) -> list[Candidate]:
    """Every work we do not hold that is connected to one we do.

    `references` maps a held record id to the canonical keys it cites — the
    backward direction, free, read from the store. `citers` maps a held
    record id to the canonical keys of works citing *it* — the forward
    direction, which costs a query per held record and is the only way a
    paper published this month can ever be found.

    `held_keys` maps a canonical key to the record holding it, and
    `generations` gives each held record's generation.

    Sorted by support and then by key, so two runs over the same corpus
    propose the same things in the same order. An expansion whose output
    depends on dict ordering would make a diff between runs unreadable.
    """
    backward: dict[str, set[str]] = {}
    forward: dict[str, set[str]] = {}
    closest: dict[str, int] = {}

    def note(key: str, held_id: str, bucket: dict[str, set[str]]) -> None:
        bucket.setdefault(key, set()).add(held_id)
        proposed = generations[held_id] + 1
        closest[key] = min(closest.get(key, proposed), proposed)

    for held_id, cited_keys in references.items():
        if held_id not in generations:
            continue          # a reference list for a record we no longer hold
        for key in cited_keys:
            if key not in held_keys:
                note(key, held_id, backward)

    for held_id, citing_keys in (citers or {}).items():
        if held_id not in generations:
            continue
        for key in citing_keys:
            if key not in held_keys:
                note(key, held_id, forward)

    return sorted(
        (Candidate(key=key,
                   cited_by=tuple(sorted(backward.get(key, ()))),
                   cites=tuple(sorted(forward.get(key, ()))),
                   generation=closest[key])
         for key in set(backward) | set(forward)),
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
        facts = metadata(candidate) if metadata else {}
        # Nothing to judge. Observed on a live run: an identifier 404s at
        # OpenAlex, metadata comes back empty, and the scan is asked to
        # assess a blank — which it correctly refuses, having cost a model
        # call to do it.
        #
        # Only when a provider was configured and came back with nothing.
        # No provider at all is a different situation — a judge that does
        # not need one, which is every offline test — and treating the two
        # alike would make the gate fire on exactly the cases it should not.
        if metadata and not (facts.get("title") or "").strip():
            selection.unresolvable.append(candidate)
            continue
        verdict = judge(candidate, facts)
        if verdict.admit:
            selection.admitted.append((candidate, verdict))
        else:
            selection.rejected.append((candidate, verdict))
    return selection


def provenance(candidate: Candidate, verdict: ScopeVerdict, titles: dict[str, str]) -> str:
    """What an auto-admitted record says about how it got here.

    Written out in full rather than as a code, because this is the field a
    reader consults when they are surprised to find something in the corpus,
    and "expansion gen 2" answers nothing.
    """
    connected = "; ".join(sorted(titles.get(rid, rid)[:60] for rid in candidate.connected))
    how = {
        "we cite": "cited by",
        "cites us": "cites",
        "both": "mutually connected to",
    }[candidate.direction]
    return (
        f"admitted automatically at generation {candidate.generation} by citation "
        f"expansion: {how} {candidate.support} records already held, which is at "
        f"or above the threshold of {threshold_for(candidate.generation)} for this "
        f"generation. Connected records: {connected}. "
        f"Scope scan by {verdict.judged_by}: {verdict.reasoning} "
        f"Unreviewed, like everything that has not been through the review queue — "
        f"and machine-admitted as well as machine-resolved, so the scope judgement "
        f"here is a model's until a person confirms it."
    )


# ---- remembering what was refused -----------------------------------------
#
# A refusal used to leave no trace. Three consequences, all bad: the same
# candidate was re-scanned and re-paid for every run; a verdict that flipped
# between runs was invisible; and nobody could ask what the scan had been
# turning away. ReAct was refused twice and admitted once from the same
# prompt against the same corpus, and only a human reading three logs
# noticed.
#
# So refusals are written down. Not to make them permanent — a refused
# candidate is reconsidered, and should be, because the corpus around it
# changes — but so that changing one's mind is a visible event.

REFUSALS = "data/candidates/refused.yml"


def refusal_record(candidate: Candidate, verdict: ScopeVerdict, when: str) -> dict:
    return {
        "key": candidate.key,
        "generation": candidate.generation,
        "support": candidate.support,
        "cited_by": list(candidate.cited_by),
        "reasoning": verdict.reasoning,
        "judged_by": verdict.judged_by,
        "refused_on": when,
    }


def merge_refusals(existing: list[dict], fresh: list[dict]) -> tuple[list[dict], list[dict]]:
    """Fold this run's refusals into the history, and report the flips.

    Returns the merged history and the candidates whose verdict changed
    direction since last time. A flip is the number worth watching: it is
    the scan disagreeing with itself, and the honest measure of how much
    the boundary can be trusted.
    """
    by_key = {entry["key"]: entry for entry in existing}
    flips = []
    for entry in fresh:
        if previous := by_key.get(entry["key"]):
            entry["times_refused"] = previous.get("times_refused", 1) + 1
            entry["first_refused_on"] = previous.get("first_refused_on",
                                                     previous.get("refused_on"))
        else:
            entry["times_refused"] = 1
            entry["first_refused_on"] = entry["refused_on"]
        by_key[entry["key"]] = entry
    return sorted(by_key.values(), key=lambda e: e["key"]), flips


def admissions_that_were_previously_refused(
        admitted: list[str], existing: list[dict]) -> list[dict]:
    """Candidates the scan refused before and has now let in.

    The flip, caught from the other side. Worth surfacing loudly: it means
    a record entered the corpus on a judgement the same scan had already
    made the other way, and a reader is entitled to know that.
    """
    refused = {entry["key"]: entry for entry in existing}
    return [refused[key] for key in admitted if key in refused]


DUPLICATES = "data/candidates/known-duplicates.yml"


def load_excluded(path) -> set[str]:
    """Canonical keys that must never be proposed again.

    A candidate found to duplicate a held record is skipped at write time —
    but it is still cited by the same papers next week, so it clears the
    threshold again, and the run pays for a scope scan and a metadata fetch
    before rediscovering what it already knew. The ACM version of Generative
    Agents did exactly this: refused as a duplicate, then top of the
    candidate list on the very next run.

    Kept separate from refusals because it is a different kind of fact. A
    refusal is a scope judgement and is meant to be revisited; this is an
    identity finding and revisiting it just costs money.
    """
    import yaml

    path = __import__("pathlib").Path(path)
    if not path.exists():
        return set()
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {entry["key"] for entry in payload.get("duplicates", []) if entry.get("key")}


def record_duplicate(path, key: str, twin_id: str, why: str, when: str) -> None:
    """Remember that this candidate is a record we already hold."""
    import yaml

    path = __import__("pathlib").Path(path)
    payload = {}
    if path.exists():
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    entries = {e["key"]: e for e in payload.get("duplicates", [])}
    entries[key] = {"key": key, "duplicates": twin_id, "why": why, "found_on": when}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump({"duplicates": [entries[k] for k in sorted(entries)]},
                       sort_keys=False, allow_unicode=True, width=94),
        encoding="utf-8")
