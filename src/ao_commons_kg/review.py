"""Reviewing records to build a gold set.

The problem this solves: assigning topics by hand means choosing from 567
codes, which nobody can hold in their head. The classifier is not accurate
enough to trust, but it is easily good enough to *shortlist* — retrieval puts
a correct topic in the top 25 for 83% of records. So the reviewer picks from
fifteen rather than searching five hundred, and the work goes from an
afternoon to about an hour.

Two things this is careful about.

**The sample is stratified, not cherry-picked.** It would be easy to review
the records the classifier finds hardest, and the resulting accuracy number
would be both pessimistic and unrepresentative. A gold set has to look like
the corpus.

**Reviewer decisions are never overwritten by a machine pass.** The gold file
is separate from `data/resources/`, so a re-run of `resolve` or `ingest`
cannot touch it, and a disagreement between the two is preserved as evidence
rather than resolved silently.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import yaml


@dataclass
class GoldSet:
    """Human-assigned topics, kept apart from generated data."""

    path: Path
    reviewer: str = ""
    entries: dict[str, dict] = field(default_factory=dict)

    @classmethod
    def load(cls, path: str | Path) -> GoldSet:
        path = Path(path)
        if not path.exists():
            return cls(path=path)
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return cls(
            path=path,
            reviewer=payload.get("reviewer", ""),
            entries=payload.get("records") or {},
        )

    def record(
        self, resource_id: str, topics: list[str], *, note: str = "", reviewer: str = ""
    ) -> None:
        self.entries[resource_id] = {
            "topics": sorted(topics, key=lambda c: [int(p) for p in c.split(".")]),
            "reviewed_on": date.today().isoformat(),
            **({"reviewer": reviewer} if reviewer else {}),
            **({"note": note} if note else {}),
        }

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            yaml.safe_dump(
                {"reviewer": self.reviewer, "records": dict(sorted(self.entries.items()))},
                sort_keys=False, allow_unicode=True, width=88,
            ),
            encoding="utf-8",
        )

    def __contains__(self, resource_id: str) -> bool:
        return resource_id in self.entries


def select_for_review(resources, gold: GoldSet, *, limit: int = 50) -> list:
    """Choose a representative sample, not the interesting cases.

    Stratified across the taxonomy sections the corpus already touches, so
    the gold set resembles the corpus rather than one corner of it. Records
    with abstracts come first within each section — a reviewer cannot fairly
    judge a record from its title alone, and neither can the classifier.
    """
    pending = [r for r in resources if r.id not in gold]
    by_section: dict[str, list] = defaultdict(list)
    for resource in pending:
        section = (resource.taxonomy_topics or ["?"])[0].split(".")[0]
        by_section[section].append(resource)

    for section in by_section:
        by_section[section].sort(key=lambda r: (not r.abstract, r.id))

    # Round-robin across sections until the quota is met, so a section with
    # twenty records cannot crowd out one with three.
    selected, exhausted = [], False
    while len(selected) < limit and not exhausted:
        exhausted = True
        for section in sorted(by_section):
            if by_section[section]:
                selected.append(by_section[section].pop(0))
                exhausted = False
                if len(selected) >= limit:
                    break
    return selected


def present(resource, candidates, index) -> str:
    """The screen a reviewer sees for one record."""
    lines = [
        "",
        "═" * 78,
        f"  {resource.title}",
        f"  {resource.id}   {resource.published_at or 'undated'}",
    ]
    if resource.authors:
        lines.append(f"  {', '.join(resource.authors[:4])}"
                     + (" et al." if len(resource.authors) > 4 else ""))
    lines.append("─" * 78)

    text = resource.abstract or resource.description
    if text:
        words = text.split()
        lines += ["  " + " ".join(words[i:i + 11]) for i in range(0, min(len(words), 88), 11)]
        if len(words) > 88:
            lines.append("  …")
    else:
        lines.append("  (no abstract — judge with care, or press s to skip)")

    if resource.taxonomy_topics:
        current = ", ".join(resource.taxonomy_topics)
        lines += ["", f"  current tags (unreviewed): {current}"]

    lines += ["", "  suggested topics:"]
    for number, assignment in enumerate(candidates, 1):
        topic = index.topics[assignment.code]
        trail = " › ".join(
            index.topics[c].title for c in topic.ancestor_codes() if c in index.topics
        )
        marker = "*" if assignment.code in (resource.taxonomy_topics or []) else " "
        lines.append(f"  {marker}{number:>2}. {assignment.code:<9} {topic.title}")
        if trail:
            lines.append(f"        {trail}")

    lines += [
        "",
        "  numbers to accept (e.g. 1 3 7)   /text to search   c code[,code] to enter directly",
        "  k keep current   n none apply   s skip   q save and quit",
    ]
    return "\n".join(lines)


@dataclass
class Decision:
    action: str
    """accept | search | skip | quit"""
    topics: list[str] = field(default_factory=list)
    query: str = ""


def parse_decision(raw: str, candidates) -> Decision:
    """Turn a keystroke into an action.

    Deliberately forgiving about separators — a reviewer typing "1,3 7" means
    the same thing as "1 3 7", and being pedantic about it slows the only
    part of this that costs human time.
    """
    raw = (raw or "").strip()
    if not raw:
        return Decision("skip")
    lowered = raw.lower()

    if lowered in ("q", "quit"):
        return Decision("quit")
    if lowered in ("s", "skip"):
        return Decision("skip")
    if lowered in ("n", "none"):
        return Decision("accept", [])
    if lowered in ("k", "keep"):
        return Decision("keep")
    if raw.startswith("/"):
        return Decision("search", query=raw[1:].strip())
    if lowered.startswith("c "):
        codes = [c.strip() for c in raw[2:].replace(",", " ").split() if c.strip()]
        return Decision("accept", codes)

    chosen = []
    for token in raw.replace(",", " ").split():
        if token.isdigit() and 1 <= int(token) <= len(candidates):
            chosen.append(candidates[int(token) - 1].code)
    return Decision("accept", chosen) if chosen else Decision("skip")


def search_topics(index, query: str, limit: int = 15):
    """Free-text search over the taxonomy, for when nothing suggested fits."""
    from .classify import Assignment, tokenize

    tokens = tokenize(query)
    if not tokens:
        return []
    scored = []
    for code in index.documents:
        value, matched = index.score(tokens, code)
        if value > 0:
            scored.append(Assignment(code, value, matched))
    scored.sort(key=lambda a: -a.score)
    return scored[:limit]


def agreement(gold: GoldSet, predictions: dict[str, list[str]]) -> dict:
    """Score predictions against reviewed tags, hierarchy-aware.

    Predicting `2.2.2` where the reviewer said `2.2` counts: same branch,
    more specific. The reverse counts too — a reviewer choosing a leaf and a
    predictor choosing its parent have not disagreed about the subject.
    """
    def compatible(left: str, right: str) -> bool:
        return left == right or left.startswith(right + ".") or right.startswith(left + ".")

    recovered = total = exact = 0
    records_hit = 0
    for resource_id, entry in gold.entries.items():
        wanted = entry.get("topics") or []
        if not wanted:
            continue
        predicted = predictions.get(resource_id, [])
        hits = sum(1 for w in wanted if any(compatible(p, w) for p in predicted))
        exact += len(set(wanted) & set(predicted))
        recovered += hits
        total += len(wanted)
        records_hit += bool(hits)

    reviewed = sum(1 for e in gold.entries.values() if e.get("topics"))
    return {
        "reviewed_records": reviewed,
        "gold_tags": total,
        "recovered": recovered,
        "recall": recovered / total if total else 0.0,
        "exact": exact,
        "records_with_a_hit": records_hit,
        "record_hit_rate": records_hit / reviewed if reviewed else 0.0,
    }
