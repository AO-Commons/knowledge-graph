"""OpenAlex resolution and neighbourhood expansion.

The rule from the brief: store the AO Commons subset, never rebuild a global
index. OpenAlex answers *what is this paper and what does it cite*; the
taxonomy and the scope test answer *does it belong here*, and the second
question is what keeps the graph small enough to be worth querying.

Network access is injected rather than imported, so the whole module is
testable against recorded payloads. That is not only for convenience: the
expansion logic is where a subtle change quietly alters what the corpus
becomes, and it deserves tests that do not depend on a live API.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Callable, Iterable, Protocol

API = "https://api.openalex.org"
CONTACT = "anke@stellar.org"
"""OpenAlex asks for a contact address and gives the polite pool in return —
anonymous requests get rate-limited hard, which is worth knowing before
blaming the expansion for being slow."""


class OpenAlexError(RuntimeError):
    pass


class Fetcher(Protocol):
    def __call__(self, url: str) -> dict: ...


def http_fetcher() -> Fetcher:
    """The real one. Imported lazily so the package works without requests."""
    import requests

    def fetch(url: str) -> dict:
        joiner = "&" if "?" in url else "?"
        response = requests.get(f"{url}{joiner}mailto={CONTACT}", timeout=30)
        if response.status_code in (429, 503):
            raise OpenAlexError(
                f"OpenAlex is rate-limiting ({response.status_code}). "
                "Retry-After: " + response.headers.get("Retry-After", "unknown")
            )
        if not response.ok:
            raise OpenAlexError(f"{response.status_code} for {url}")
        return response.json()

    return fetch


# --- Identity ---------------------------------------------------------------

ARXIV = re.compile(r"^\d{4}\.\d{4,5}(v\d+)?$")


def work_url(identifier: str) -> str:
    """Turn any identifier we hold into an OpenAlex lookup URL."""
    identifier = identifier.strip()
    if identifier.startswith("W"):
        return f"{API}/works/{identifier}"
    if ARXIV.match(identifier):
        base = identifier.split("v")[0]
        return f"{API}/works/https://doi.org/10.48550/arXiv.{base}"
    if identifier.lower().startswith("10."):
        return f"{API}/works/https://doi.org/{identifier}"
    raise OpenAlexError(f"not an identifier OpenAlex can resolve: {identifier!r}")


def short_id(openalex_id: str | None) -> str | None:
    """`https://openalex.org/W123` -> `W123`. Ids are compared constantly."""
    if not openalex_id:
        return None
    return openalex_id.rstrip("/").rsplit("/", 1)[-1]


# --- Resolution -------------------------------------------------------------

@dataclass
class Work:
    """The subset of an OpenAlex record this project stores."""

    openalex_id: str
    title: str
    doi: str | None = None
    arxiv_id: str | None = None
    publication_date: str | None = None
    authors: list[str] = field(default_factory=list)
    institutions: list[str] = field(default_factory=list)
    abstract: str | None = None
    cited_by_count: int = 0
    is_open_access: bool | None = None
    is_retracted: bool | None = None
    referenced_works: list[str] = field(default_factory=list)
    type: str | None = None


def _abstract(inverted: dict | None) -> str | None:
    """OpenAlex stores abstracts as an inverted index; rebuild the text."""
    if not inverted:
        return None
    positions: dict[int, str] = {}
    for word, spots in inverted.items():
        for spot in spots:
            positions[spot] = word
    if not positions:
        return None
    return " ".join(positions[i] for i in sorted(positions))


def parse_work(payload: dict) -> Work:
    ids = payload.get("ids") or {}
    doi = (payload.get("doi") or "").removeprefix("https://doi.org/") or None

    arxiv_id = None
    if doi and doi.lower().startswith("10.48550/arxiv."):
        arxiv_id = doi.split(".", 2)[-1]

    authors, institutions = [], []
    for authorship in payload.get("authorships") or []:
        if name := (authorship.get("author") or {}).get("display_name"):
            authors.append(name)
        for institution in authorship.get("institutions") or []:
            if display := institution.get("display_name"):
                institutions.append(display)

    return Work(
        openalex_id=short_id(payload.get("id")) or "",
        title=payload.get("title") or payload.get("display_name") or "",
        doi=doi,
        arxiv_id=arxiv_id,
        publication_date=payload.get("publication_date"),
        authors=authors,
        institutions=sorted(set(institutions)),
        abstract=_abstract(payload.get("abstract_inverted_index")),
        cited_by_count=payload.get("cited_by_count") or 0,
        is_open_access=(payload.get("open_access") or {}).get("is_oa"),
        is_retracted=payload.get("is_retracted"),
        referenced_works=[short_id(w) for w in payload.get("referenced_works") or [] if w],
        type=payload.get("type"),
    )


def resolve_work(identifier: str, fetch: Fetcher) -> Work:
    """Resolve one identifier to a Work. Raises rather than returning None —
    a silent miss during ingestion becomes a record with no metadata."""
    return parse_work(fetch(work_url(identifier)))


# --- The scope filter -------------------------------------------------------
#
# This is a *pre-filter*, not the scope test. Measured against a hand pass
# over ~90 works, keyword scoring alone reproduced roughly the right
# shortlist but could not tell an agent-run organization from a paper that
# merely mentions agents. It exists to make a human review queue tractable,
# and the docstring says so because someone will eventually be tempted to
# auto-merge on it.

STRONG = (
    "agentic organization", "autonomous organization", "agent governance",
    "multi-agent", "agent delegation", "llm agent", "agent authority",
    "agentic ai", "ai agent", "agent economy", "human oversight",
    "agent oversight", "autonomous agent", "agent-based",
)
# `multi-agent` earns a strong score on its own. Tuned against the corpus:
# scoring only the longer phrases ("multi-agent system", "multi-agent llm")
# dropped Melting Pot to 2 and would have filtered out a paper already in
# the library. Over-including at the pre-filter is the cheaper mistake —
# these are candidates for review, and the multi-agent RL work that arrives
# as a side effect is what `is_borrowed_background` exists to label.
SUPPORTING = (
    "delegation", "governance", "oversight", "accountability", "authority",
    "coordination", "collusion", "principal-agent", "institution",
    "benchmark", "evaluation", "failure", "audit", "permission", "autonomy",
)
# Terms that reliably indicate the other literature the scope test excludes.
#
# The second group was added after the first live expansion run. Seeding from
# borrowed multi-agent RL benchmarks pulled in robot swarms, Q-learning
# variants, and a telecoms paper about "inter-operator cooperation to save
# radio resources" — all of which score well on "agent" and "cooperation" and
# none of which change how you run an organization. Section 15 says to point
# at adjacent fields rather than ingest them; this is that rule in code.
AGAINST = (
    "randomized controlled trial", "clinical", "patient", "gene", "protein",
    "rheumatology", "endoscopy", "infant", "covid-19 transmission",
    "quantum", "superconduct", "graphblas", "packet", "wireless",
    "robot swarm", "swarms of robots", "radio resource", "base station",
    "q-learning", "traffic signal", "autonomous driving", "path planning",
    "wireless sensor", "uav", "warehouse robot",
)

# Domain applications: agents used as a tool for a task, rather than holding
# authority in an organization. The dominant noise in the second live run —
# "agentic AI in smart manufacturing", "for hydrologic modeling", "home energy
# management", "plant phenotyping", "in recruiting". They score well because
# they genuinely are about AI agents; they fail the scope test because nothing
# about how you run an organization changes.
#
# These FLAG rather than penalize. A paper about agents running a
# manufacturing *business* would be in scope, and a keyword cannot tell it
# from one that uses agents to schedule maintenance. Subtracting would hide
# the first to suppress the second; flagging shows the reviewer why the
# candidate is suspicious and lets them decide.
#
# This is the ceiling of keyword scoring, and worth stating plainly: the
# scope test asks whether agents hold organizational authority, which is a
# semantic judgement. The pre-filter ranks; it does not decide.
DOMAIN = (
    "smart manufacturing", "preventive maintenance", "healthcare", "clinical",
    "hydrologic", "energy management", "phenotyping", "agriculture", "crop",
    "recruiting", "recruitment", "construction", "retail", "supply chain optimization",
    "medical imaging", "drug discovery", "materials discovery", "education",
    "e-learning", "tutoring", "customer service", "network intrusion",
    "sandbox for dynamic behavioral analysis", "classification pipeline",
)


AGENT = re.compile(r"\bagents?\b")
ORGANIZATIONAL = re.compile(
    r"\b(econom\w+|organi[sz]ation\w*|governance|oversight|delegation|"
    r"authority|institution\w*|firm|firms|team|teams|workforce|market\w*|"
    r"principal|coordination|negotiat\w+)\b"
)


def scope_score(work: Work) -> tuple[int, list[str]]:
    """A cheap relevance score and the terms behind it.

    Scores title and abstract together; a title alone is the worst case and
    the calibration is tuned to survive it.

    Returns the score and its reasons, because a queue a reviewer cannot
    interrogate is a queue they will stop trusting.
    """
    haystack = f"{work.title} {work.abstract or ''}".lower()
    reasons: list[str] = []
    score = 0

    # A compound rule rather than more phrases. Phrase lists lose to plurals
    # and word order — "agent economy" missed "Virtual Agent Economies" — so
    # the general shape is what gets scored: an agent, plus something
    # organizational for it to act within.
    if AGENT.search(haystack) and (match := ORGANIZATIONAL.search(haystack)):
        score += 3
        reasons.append(f"+3 agent × {match.group(0)}")

    for term in STRONG:
        if term in haystack:
            score += 3
            reasons.append(f"+3 {term}")
    for term in SUPPORTING:
        if term in haystack:
            score += 1
            reasons.append(f"+1 {term}")
    for term in AGAINST:
        if term in haystack:
            score -= 4
            reasons.append(f"-4 {term}")
    for term in DOMAIN:
        if term in haystack:
            reasons.append(f"?? domain application: {term}")

    return score, reasons


# --- Expansion --------------------------------------------------------------

@dataclass
class Candidate:
    openalex_id: str
    title: str
    doi: str | None
    publication_date: str | None
    cited_by_count: int
    score: int
    reasons: list[str]
    found_via: str
    authors: list[str] = field(default_factory=list)
    institutions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "openalex_id": self.openalex_id,
            "title": self.title,
            "doi": self.doi,
            "date": self.publication_date,
            "cited_by_count": self.cited_by_count,
            "score": self.score,
            "found_via": self.found_via,
            "authors": self.authors[:8],
            "institutions": self.institutions[:4],
            "reasons": self.reasons,
        }


def expand_neighborhood(
    seeds: Iterable[str],
    fetch: Fetcher,
    *,
    known: set[str],
    min_score: int = 3,
    per_seed: int = 25,
    on_progress: Callable[[str], None] | None = None,
) -> tuple[list[Candidate], dict[str, Work]]:
    """Walk one hop out from each seed, through both references and citers.

    Both directions, because they answer different questions: references are
    what a paper builds on, citers are what built on it. A corpus grown only
    forward drifts toward the recent; only backward, toward the foundational.

    Returns candidates above the score threshold, and the resolved seed works
    so their reference lists can be stored without fetching twice.
    """
    seen: dict[str, Candidate] = {}
    resolved: dict[str, Work] = {}

    for seed in seeds:
        try:
            work = resolve_work(seed, fetch)
        except OpenAlexError as error:
            if on_progress:
                on_progress(f"  {seed}: {error}")
            continue
        resolved[work.openalex_id] = work
        if on_progress:
            on_progress(f"  {work.openalex_id} {work.title[:60]}")

        # Backward: what it builds on.
        for referenced in work.referenced_works[:per_seed]:
            if referenced in known or referenced in seen:
                continue
            try:
                candidate_work = resolve_work(referenced, fetch)
            except OpenAlexError:
                continue
            score, reasons = scope_score(candidate_work)
            if score >= min_score:
                seen[referenced] = _candidate(candidate_work, score, reasons,
                                              f"cited by {work.openalex_id}")

        # Forward: what built on it.
        try:
            citing = fetch(
                f"{API}/works?filter=cites:{work.openalex_id}"
                f"&per-page={per_seed}&sort=cited_by_count:desc"
            )
        except OpenAlexError:
            citing = {"results": []}
        for payload in citing.get("results", []):
            candidate_work = parse_work(payload)
            if candidate_work.openalex_id in known or candidate_work.openalex_id in seen:
                continue
            score, reasons = scope_score(candidate_work)
            if score >= min_score:
                seen[candidate_work.openalex_id] = _candidate(
                    candidate_work, score, reasons, f"cites {work.openalex_id}"
                )

    ranked = sorted(seen.values(), key=lambda c: (-c.score, -c.cited_by_count))
    return ranked, resolved


def _candidate(work: Work, score: int, reasons: list[str], via: str) -> Candidate:
    return Candidate(
        openalex_id=work.openalex_id,
        title=work.title,
        doi=work.doi,
        publication_date=work.publication_date,
        cited_by_count=work.cited_by_count,
        score=score,
        reasons=reasons,
        found_via=via,
        authors=work.authors,
        institutions=work.institutions,
    )
