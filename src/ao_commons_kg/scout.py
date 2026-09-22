"""Finding work the citation graph cannot see.

`grow` walks citations and is bounded by its budget rather than by a shortage
of candidates. What it cannot do is find a paper that neither cites us nor is
cited by us: `Candidate` support counts held records connected by a citation,
and a paper with no connection scores zero against a threshold of two,
however plainly it belongs.

One arXiv query for `cat:cs.MA AND abs:"delegation"` returned *Capability-
Based Delegation of Privileges in Multi-Agent Systems*, published while this
corpus held 141 records and none of them that one. Expansion would never have
reached it.

Removing citation support removes the threshold, which would leave a model's
opinion as the only gate — the unbounded admission this project exists to
avoid. So a scout needs a bound the corpus can compute about *itself*:
`topical support`, which is BM25 against our own published taxonomy plus
overlap with the concepts statements have actually needed. A find clears it
the way a cited candidate clears a citation threshold, and only then costs a
model call.

See `docs/scouting.md` for the argument, including what could go wrong.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from typing import Callable, Iterable, Protocol

from .classify import TopicIndex


@dataclass(frozen=True)
class Query:
    """One search, and why it is being made."""

    text: str
    reason: str
    """`deepen` or `widen`, which is the distinction the whole design turns
    on — see `queries_from_corpus`."""


@dataclass
class Find:
    """A work a source returned, before anything has judged it."""

    key: str | None
    """Canonical key, when the source gave enough to build one. A find with
    no key cannot be deduplicated against the corpus and is dropped."""
    title: str
    abstract: str = ""
    date: str = ""
    url: str = ""
    source: str = ""
    queries: tuple[str, ...] = ()
    """Every query that returned it. A work several queries agree on is a
    better bet than one a single phrasing turned up, and this records that
    without yet deciding what it is worth."""
    topics: tuple[tuple[str, float], ...] = ()
    concepts: tuple[str, ...] = ()
    score: float = 0.0

    @property
    def text(self) -> str:
        return " ".join(part for part in (self.title, self.abstract) if part)


class Source(Protocol):
    """Somewhere to look. Kept behind an interface so the free ones can carry
    the tool on their own and a paid one is never load-bearing."""

    name: str

    def search(self, query: Query, *, limit: int) -> list[Find]:
        ...


def queries_from_corpus(
    concepts_in_use: Iterable[str],
    unreached: Iterable[str],
    *,
    deepen: int = 6,
    widen: int = 6,
    seed: int = 0,
) -> list[Query]:
    """What to search for, taken from the corpus rather than from a list.

    Two halves doing opposite jobs.

    **Deepen** draws on the concepts statements have actually needed. A term
    is in the working vocabulary because somebody read a paper and needed it,
    so searching those finds more of what the library has turned out to be
    about.

    **Widen** draws on taxonomy subpoints nothing has ever been filed under.
    Those are things somebody thought mattered enough to name and about which
    the corpus holds nothing — a map of its blind spots, written down in
    advance.

    Without the second half a scout deepens a rut: it returns neighbours of
    what we already hold, which is what citation expansion already does
    better. The measure of whether it is working is the share of admissions
    arriving under a concept the corpus had no paper for.

    Rotated by a seed rather than taken from the top, because 493 unreached
    subpoints cannot all be searched every run and always taking the first
    few would mean the rest are never looked for at all.
    """
    rng = random.Random(seed)

    used = sorted({_phrase(c) for c in concepts_in_use if _phrase(c)})
    blind = sorted({_phrase(c) for c in unreached if _phrase(c)})
    rng.shuffle(used)
    rng.shuffle(blind)

    return ([Query(text=t, reason="deepen") for t in used[:deepen]]
            + [Query(text=t, reason="widen") for t in blind[:widen]])


def _phrase(concept: str) -> str:
    """A concept id or label as something a search engine can use."""
    text = re.sub(r"[-_]+", " ", (concept or "").strip())
    text = re.sub(r"\s+", " ", text)
    # Long taxonomy subpoints are sentences, not search terms. Their first
    # clause carries the subject; the rest is the explanation.
    text = re.split(r"[,:;(]| — | - ", text)[0].strip()
    return text if len(text.split()) >= 2 else ""


def topical_support(
    find: Find,
    index: TopicIndex,
    concepts_in_use: Iterable[str],
    *,
    min_topic_score: float = 4.0,
) -> tuple[float, tuple[tuple[str, float], ...], tuple[str, ...]]:
    """How much this looks like the library, by the library's own measure.

    BM25 against the published taxonomy, plus concepts the corpus already
    uses appearing in the text. Both are computed locally and for free, which
    matters: this runs on everything a source returns, and only what clears
    it costs a model call.

    A title-only find scores far lower than one with an abstract, and that is
    honest rather than a problem to correct — there is genuinely less to go
    on.
    """
    assignments = index.classify(find.text, limit=6, min_score=min_topic_score)
    topics = tuple((a.code, round(a.score, 2)) for a in assignments)

    haystack = find.text.lower()
    hits = tuple(sorted(
        c for c in {str(c) for c in concepts_in_use}
        if (phrase := _phrase(c)) and phrase.lower() in haystack))

    # Topic evidence dominates and concept hits add to it. A find matching
    # three taxonomy topics is on-topic by the taxonomy's own definition; a
    # find that merely contains a concept phrase might only be using the
    # words.
    score = sum(s for _, s in topics) + 2.0 * len(hits)
    return score, topics, hits


# The scope test is "what changes *because machine agents hold authority*",
# and BM25 against our taxonomy only measures the second half of that. The
# taxonomy is about organizations, so a paper on organizational governance
# scores well whether or not a machine is anywhere near it: the first run of
# this scout ranked "Organized Violence and Crime in Urban Nigeria" and "The
# ecology of insolvency" above everything, on topic scores of 116 and 108.
#
# So a find has to show the agent half too. Cheap, local, and a restatement
# of the library's own scope rather than a new judgement — a candidate with
# no machine agent in it is out of scope by definition, and refusing it here
# saves the model call that would refuse it later.
AGENTIC = re.compile(
    r"\b(ai|artificial intelligence|machine learning|llms?|large language model"
    r"|agent|agents|agentic|multi-?agent|autonomous|automation|automated"
    r"|bot|bots|chatbot|copilot|foundation model|reinforcement learning)\b",
    re.I,
)


def mentions_agents(text: str) -> bool:
    """Whether machines appear at all.

    Deliberately generous. This is not deciding whether agents hold
    authority — that is the scan's job and needs a model. It only refuses
    the case where nothing mechanical is present, which no amount of
    organizational relevance can rescue.
    """
    return bool(AGENTIC.search(text or ""))


@dataclass
class Sweep:
    """What one run of the scout found, and what it decided about it."""

    kept: list[Find] = field(default_factory=list)
    below_threshold: list[Find] = field(default_factory=list)
    already_held: list[Find] = field(default_factory=list)
    not_agentic: list[Find] = field(default_factory=list)
    """Scored well against the taxonomy and mentions no machine at all."""
    unusable: list[Find] = field(default_factory=list)
    """Returned without enough identity to deduplicate — no DOI, no arXiv id.
    Dropped rather than guessed at, because a find we cannot key is one we
    cannot tell we already hold."""

    def summary(self) -> str:
        return (f"{len(self.kept)} kept, {len(self.below_threshold)} below threshold, "
                f"{len(self.not_agentic)} with no machine in them, "
                f"{len(self.already_held)} already held, {len(self.unusable)} unusable")


def sweep(
    sources: list[Source],
    queries: list[Query],
    *,
    index: TopicIndex,
    concepts_in_use: Iterable[str],
    held_keys: dict[str, str],
    threshold: float = 12.0,
    per_query: int = 10,
    budget: int = 40,
    on_query: Callable[[Query, str, int], None] | None = None,
) -> Sweep:
    """Search, score locally, and keep what clears the bound.

    Everything here is free. No model is called and nothing is admitted: a
    scout proposes, and the scan and a person decide. Growth admits
    automatically because two held papers citing something is the corpus
    voting for it, and a scout has no such vote.
    """
    concepts_in_use = list(concepts_in_use)
    found: dict[str, Find] = {}
    result = Sweep()

    for query in queries:
        for source in sources:
            try:
                hits = source.search(query, limit=per_query)
            except Exception:  # noqa: BLE001 — one source failing is not the run failing
                hits = []
            if on_query:
                on_query(query, source.name, len(hits))
            for hit in hits:
                if not hit.key:
                    result.unusable.append(hit)
                    continue
                if hit.key in found:
                    seen = found[hit.key]
                    if query.text not in seen.queries:
                        seen.queries = seen.queries + (query.text,)
                    continue
                hit.queries = (query.text,)
                found[hit.key] = hit

    for key, hit in sorted(found.items()):
        if key in held_keys:
            result.already_held.append(hit)
            continue
        if not mentions_agents(hit.text):
            result.not_agentic.append(hit)
            continue
        score, topics, concepts = topical_support(hit, index, concepts_in_use)
        hit.score, hit.topics, hit.concepts = score, topics, concepts
        (result.kept if score >= threshold else result.below_threshold).append(hit)

    result.kept.sort(key=lambda f: (-f.score, f.key or ""))
    if budget and len(result.kept) > budget:
        result.below_threshold.extend(result.kept[budget:])
        result.kept = result.kept[:budget]
    return result
