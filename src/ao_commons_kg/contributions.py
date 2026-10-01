"""Who made this library, and what each contribution rests on.

A library of statements drawn from papers is built from other people's work
twice over. The papers are somebody's. So is everything done to make them
findable: proposing a record, judging a statement, confirming who a reviewer
is. Every one of those is already written down somewhere in this repository,
in the field that made it — a reviewer on a verdict, a login in a record's
provenance, a model named on a draft. Nothing collected them, so the
question "who made this, and what did they make" had no answer short of
reading every file.

This collects them. It reads only what is already recorded, and adds no
field anybody has to fill in.

It follows four of Rennie and Potts' design principles for contribution
systems (2025, SSRN 5190625), because this library is a small one:

- **Value travels through dependencies.** A verdict rests on a statement,
  which rests on a draft, which rests on a paper somebody wrote. Each
  contribution records what it `builds_on`, so credit can be followed upstream
  to the authors the whole thing depends on.
- **Valuation is continuous.** A contribution is used after it is made: a
  paper is cited by records admitted later, a statement is joined to another
  by a relation. `used_by` is recomputed on every build, so it grows with the
  library rather than freezing at the moment of contribution.
- **Recognition is legible.** Nothing is weighted, scored or ranked. Every
  entry names the file it was read from, so anyone can check how they are
  counted and contest it. SourceCred became a problem when its weights were
  hidden from the people they weighed. The way to keep that from happening
  here is to have no weights at all, until somebody proposes a valuation in
  the open.
- **Machine contributions are machine-readable, and kept apart.** A model
  drafting a statement and a citation crawl admitting a record are recorded,
  because they are real work the library rests on. They are listed
  separately, and they are never counted as a person's judgment. That is the
  line this project already draws: machines admit, people judge.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent.parent

KINDS = {
    "wrote": "wrote a paper the library holds",
    "proposed": "proposed a record for the library",
    "reviewed-statement": "judged whether a statement says what its paper says",
    "reviewed-filing": "decided where a record belongs in the taxonomy",
    "asserted-relation": "judged how two statements relate",
    "verified-identity": "confirmed who a reviewer is",
    "drafted": "drafted statements from a paper",
    "admitted": "admitted a record because the corpus cites it",
}
MACHINE_KINDS = {"drafted", "admitted"}

DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
PROPOSER = re.compile(r"from issue #\d+ by @([A-Za-z0-9][A-Za-z0-9-]*)")


@dataclass(frozen=True)
class Contribution:
    contributor: str
    """A byline name, a GitHub login written `@login`, or a machine's name."""
    kind: str
    on: str
    """The id of what was contributed to: a record, a statement, a relation."""
    source: str
    """The file this was read from, relative to the repository."""
    date: str | None = None
    machine: bool = False
    by_author: bool = False
    """For a verdict: whether the reviewer is an author of the paper."""
    builds_on: tuple[str, ...] = ()


@dataclass
class Ledger:
    contributions: list[Contribution] = field(default_factory=list)
    used_by: dict[str, dict[str, int]] = field(default_factory=dict)
    """For an id, how later work uses it: records citing it, statements
    drawn from it, relations and verdicts on it."""


def _first_date(text: str | None) -> str | None:
    found = DATE.search(text or "")
    return found.group(0) if found else None


def _who(login: str | None, identities) -> str | None:
    """A login as the name a byline would use, when the link is verified.

    Without the link a person's reviews and their papers would be two
    contributors who never meet. With an unverified one they would be joined
    on a guess, which is worse.
    """
    if not login:
        return None
    identity = identities.get(login.lower())
    if identity is not None and identity.verified:
        return identity.name
    return f"@{login}"


def collect(*, resources, claims, relations=None, gold_claims=None, gold_tags=None,
            identities=None, citations=None) -> Ledger:
    """Every contribution the records already hold, and how each is used.

    All inputs are passed in rather than read here, so a test can build a
    ledger from five lines and the build reads the real files.
    """
    from .people import build_index, same_person

    identities = identities or {}
    relations = relations or []
    gold_claims = gold_claims or {}
    gold_tags = gold_tags or {}
    citations = citations or []
    found: list[Contribution] = []

    names = build_index([a for r in resources for a in (r.authors or [])])
    by_resource = {r.id: r for r in resources}
    claims_by_id = {c.id: c for c in claims}

    for resource in resources:
        src = f"data/resources/{resource.id.split(':', 1)[1].replace(':', '-')}.yml"
        for author in dict.fromkeys(names.get(a, a) for a in resource.authors or []):
            found.append(Contribution(author, "wrote", resource.id, src,
                                      date=str(resource.published_at or "") or None))
        provenance = resource.source_provenance or ""
        if proposer := PROPOSER.search(provenance):
            found.append(Contribution(_who(proposer.group(1), identities), "proposed",
                                      resource.id, src, date=resource.ingested_at))
        elif provenance.startswith("admitted automatically"):
            found.append(Contribution("citation expansion", "admitted", resource.id, src,
                                      date=resource.ingested_at, machine=True,
                                      builds_on=tuple(sorted(
                                          s for s, t in citations if t == resource.id))))

    for claim in claims:
        if not claim.extraction_method:
            continue
        model = claim.extraction_method.split(",", 1)[0].strip()
        src = f"data/claims/{claim.resource_id.split(':', 1)[1].replace(':', '-')}.yml"
        found.append(Contribution(model, "drafted", claim.id, src,
                                  date=_first_date(claim.extraction_method), machine=True,
                                  builds_on=(claim.resource_id,)))

    for claim_id, verdict in sorted(gold_claims.items()):
        who = _who((verdict or {}).get("reviewer"), identities)
        if not who:
            continue
        claim = claims_by_id.get(claim_id)
        resource = by_resource.get(claim.resource_id) if claim else None
        by_author = bool(verdict.get("by_author")) or bool(
            resource and any(same_person(who, a) for a in resource.authors or []))
        found.append(Contribution(who, "reviewed-statement", claim_id, "evals/gold/claims.yml",
                                  date=verdict.get("reviewed_on"), by_author=by_author,
                                  builds_on=(claim_id,)))

    for record_id, verdict in sorted(gold_tags.items()):
        who = _who((verdict or {}).get("reviewer"), identities)
        if who:
            found.append(Contribution(who, "reviewed-filing", record_id, "evals/gold/tags.yml",
                                      date=verdict.get("reviewed_on"), builds_on=(record_id,)))

    for relation in relations:
        asserted = relation.get("asserted_by") or ""
        machine = "drafted" in asserted or asserted.startswith("claude")
        who = asserted.split(" (", 1)[0] if machine else _who(asserted, identities)
        if not who:
            continue
        on = f"{relation['source']} {relation['relation']} {relation['target']}"
        found.append(Contribution(who, "asserted-relation", on, "data/claim-relations.yml",
                                  date=relation.get("asserted_on"), machine=machine,
                                  builds_on=(relation["source"], relation["target"])))

    for login, identity in sorted(identities.items()):
        if identity.verified:
            found.append(Contribution(_who(identity.verified_by, identities),
                                      "verified-identity", identity.name, "data/people/",
                                      date=_first_date(identity.verified_how)))

    used: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for source, target in citations:
        used[target]["cited by records"] += 1
    for claim in claims:
        used[claim.resource_id]["statements drawn from it"] += 1
    for claim_id in gold_claims:
        used[claim_id]["verdicts"] += 1
    for relation in relations:
        for end in (relation["source"], relation["target"]):
            used[end]["relations"] += 1

    return Ledger(
        contributions=sorted(found, key=lambda c: (c.contributor, c.kind, c.on)),
        used_by={k: dict(sorted(v.items())) for k, v in sorted(used.items())},
    )


def summarize(ledger: Ledger) -> dict:
    """The ledger as one object per contributor, people and machines apart.

    Sorted by name and never by count. An order by count is a ranking, and a
    ranking is a weighting nobody has agreed to.
    """
    grouped: dict[str, list[Contribution]] = defaultdict(list)
    for c in ledger.contributions:
        grouped[c.contributor].append(c)

    def entry(name, items):
        counts: dict[str, int] = defaultdict(int)
        rows = []
        for c in items:
            counts[c.kind] += 1
            row = {"kind": c.kind, "on": c.on, "source": c.source}
            if c.date:
                row["date"] = c.date
            if c.by_author:
                row["by_author"] = True
            if c.builds_on:
                row["builds_on"] = list(c.builds_on)
            use = dict(ledger.used_by.get(c.on) or {})
            if c.kind == "reviewed-statement":
                # Its own verdict is not a use of it.
                use.pop("verdicts", None)
            if use:
                row["used_by"] = use
            rows.append(row)
        # When they started contributing to this library. A paper's publication
        # date is when it was written, not when anybody here touched it.
        dates = sorted(c.date for c in items if c.date and c.kind != "wrote")
        out = {"contributor": name, "counts": dict(sorted(counts.items()))}
        if dates:
            out["since"] = dates[0]
        out["contributions"] = rows
        return out

    people = [entry(n, cs) for n, cs in sorted(grouped.items()) if not cs[0].machine]
    machines = [entry(n, cs) for n, cs in sorted(grouped.items()) if cs[0].machine]
    by_kind: dict[str, int] = defaultdict(int)
    for c in ledger.contributions:
        by_kind[c.kind] += 1
    return {
        "kinds": KINDS,
        "counts": {
            "people": len(people),
            "machines": len(machines),
            "contributions": len(ledger.contributions),
            "by_kind": dict(sorted(by_kind.items())),
        },
        "people": people,
        "machines": machines,
    }


def load_ledger() -> Ledger:
    """The ledger from the repository's own files."""
    from .claims import load_claims
    from .people import load_identities
    from .resources import load_resources
    from .scholarly.keys import keys_for_corpus
    from .scholarly.store import ReferenceStore

    resources = load_resources()
    store = ReferenceStore.load(REPO / "data" / "scholarly" / "references.jsonl")

    def read(path, key):
        p = REPO / path
        return (yaml.safe_load(p.read_text(encoding="utf-8")) or {}).get(key) or {} \
            if p.exists() else {}

    return collect(
        resources=resources,
        claims=load_claims(),
        relations=read("data/claim-relations.yml", "relations") or [],
        gold_claims=read("evals/gold/claims.yml", "claims"),
        gold_tags=read("evals/gold/tags.yml", "records"),
        identities=load_identities(),
        citations=store.citation_pairs(keys_for_corpus(resources)),
    )
