"""Open questions, and the statements that address them.

A `gap` statement is one paper saying something is unresolved. A question is
the thing several of those turn out to be asking. Clustering them is the layer
the roadmap called for and the reason the extraction pass hunts gaps
separately in the first place: it is the query nobody else can answer with
provenance, because nobody else holds the sentences.

Kept in one file rather than inside each paper's claims, for the reason
claim-relations.yml gives: the edge belongs to neither end, and filing it
under one paper would make the corpus read differently depending on which
paper you opened.

Every ADDRESSES edge is INFERRED. No paper says "my open question is an
instance of yours" — somebody read several and decided. So each carries its
reasoning, and a question carries the note saying why its statements are one
question, which is the judgment a reader most needs to be able to disagree
with.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import yaml

from .models import (
    ConfidenceClass,
    Question,
    Relationship,
    RelationType,
)

REPO = Path(__file__).resolve().parent.parent.parent
DEFAULT_QUESTIONS = REPO / "data" / "questions.yml"


class QuestionError(ValueError):
    """A question file that cannot be trusted as written."""


def load_questions(
    path: str | Path = DEFAULT_QUESTIONS,
    claims: Iterable | None = None,
) -> tuple[list[Question], list[Relationship]]:
    """Read the questions and their ADDRESSES edges, refusing any that dangle.

    Pass `claims` and every statement named here must be one we hold. A
    question pointing at a cut statement is not a small problem: the layer's
    whole claim is that these questions are asked by papers in the corpus, and
    an edge to nothing would make that claim false while still rendering.
    """
    path = Path(path)
    if not path.exists():
        return [], []

    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    entries = payload.get("questions") or []
    held = {c.id for c in claims} if claims is not None else None

    questions: list[Question] = []
    edges: list[Relationship] = []
    seen: set[str] = set()

    for position, entry in enumerate(entries, start=1):
        where = f"{path.name} question {position}"
        for required in ("id", "text", "note"):
            if not entry.get(required):
                raise QuestionError(f"{where}: missing `{required}`")

        qid = entry["id"]
        if not qid.startswith("question:"):
            raise QuestionError(f"{where}: id must start with 'question:'")
        if qid in seen:
            raise QuestionError(f"{where}: duplicate id {qid!r}")
        seen.add(qid)

        try:
            question = Question(
                id=qid,
                text=entry["text"],
                concept_tags=list(entry.get("concept_tags") or []),
                status=entry.get("status", "open"),
                note=entry["note"],
                asserted_by=entry.get("asserted_by"),
                asserted_on=str(entry["asserted_on"]) if entry.get("asserted_on") else None,
            )
        except ValueError as error:
            raise QuestionError(f"{where}: {error}") from error

        addressed = entry.get("addressed_by") or []
        if not addressed:
            raise QuestionError(
                f"{where}: no statement addresses it — a question the corpus "
                "cannot show anybody asking is an opinion, not a finding")

        for index, occurrence in enumerate(addressed, start=1):
            at = f"{where}, occurrence {index}"
            claim_id = occurrence.get("claim")
            because = occurrence.get("because")
            if not claim_id:
                raise QuestionError(f"{at}: missing `claim`")
            if not because:
                raise QuestionError(
                    f"{at}: missing `because` — this edge is a judgment, and "
                    "an unexplained one cannot be told from a guess")
            if held is not None and claim_id not in held:
                raise QuestionError(
                    f"{at}: {claim_id!r} is not a statement we hold — it was "
                    "cut, renamed, or never extracted")

            edges.append(Relationship(
                source_id=claim_id,
                target_id=qid,
                relation=RelationType.ADDRESSES,
                confidence_class=ConfidenceClass(
                    occurrence.get("confidence_class", "INFERRED")),
                source_location=because,
                extraction_method=(
                    f"asserted by {entry.get('asserted_by', 'unattributed')}"
                    f" on {entry.get('asserted_on', 'an unrecorded date')}"),
            ))

        questions.append(question)

    return questions, edges


def reach(questions: Iterable[Question], edges: Iterable[Relationship],
          claims: Iterable) -> dict[str, dict]:
    """How far each question reaches, counted in the units it is counted in.

    Two numbers, because they are two different things and showing them
    unlabelled beside each other is how the old page confused everybody:

      `papers`      distinct papers holding a statement that addresses it
      `occurrences` statements that address it

    A question asked twice by one paper is one paper's framing. A question
    asked by two papers is a statement about a field, and that difference is
    the only reason this layer is worth having — so it is counted, not
    implied.
    """
    by_claim = {c.id: c for c in claims}
    out: dict[str, dict] = {q.id: {"papers": set(), "occurrences": 0} for q in questions}
    for edge in edges:
        if edge.relation is not RelationType.ADDRESSES:
            continue
        bucket = out.get(edge.target_id)
        claim = by_claim.get(edge.source_id)
        if bucket is None or claim is None:
            continue
        bucket["occurrences"] += 1
        bucket["papers"].add(claim.resource_id)
    return {
        qid: {"papers": len(v["papers"]), "occurrences": v["occurrences"]}
        for qid, v in out.items()
    }


# --- proposing ----------------------------------------------------------

#: A concept must be argued about by at least this many distinct papers before
#: it is worth proposing as a question. Two is the lowest number that makes a
#: proposal a statement about a field rather than about one author's framing,
#: and it is the same bound the questions themselves are judged by.
MIN_PAPERS = 2

#: And by at least this many statements. A concept two papers mention once
#: each is a shared word, not a shared question.
MIN_ARGUED = 2

ARGUING = frozenset({"position", "gap", "limitation"})


def propose(claims, questions=(), *, min_papers: int = MIN_PAPERS,
            min_argued: int = MIN_ARGUED) -> list[dict]:
    """Concepts that look like questions nobody has clustered yet.

    Proposes and never admits, exactly as the scout does for papers. A concept
    several papers argue about and none has shown anything on is a reasonable
    place to look for a question — it is not a question, because a question is
    the sentence somebody writes after reading the statements, and no counting
    produces that sentence.

    The zero-findings bound is the one worth arguing about. It separates
    "nobody has shown this" from "somebody has, and you have not read it",
    and loosening it would produce a longer list of weaker proposals, which
    is the failure this repository exists to avoid.

    Concepts already covered by a question are left out: proposing what is
    already clustered is noise, and noise in a proposal list is what stops
    anybody reading it.
    """
    covered = {tag for q in questions for tag in q.concept_tags}

    by_tag: dict[str, dict] = {}
    for claim in claims:
        kind = claim.claim_type.value if hasattr(claim.claim_type, "value") else claim.claim_type
        for tag in claim.concept_tags or ():
            bucket = by_tag.setdefault(tag, {"papers": set(), "argued": 0, "found": 0, "claims": []})
            bucket["papers"].add(claim.resource_id)
            if kind in ARGUING:
                bucket["argued"] += 1
                bucket["claims"].append(claim.id)
            elif kind == "finding":
                bucket["found"] += 1

    out = []
    for tag, bucket in sorted(by_tag.items()):
        if tag in covered:
            continue
        if bucket["found"]:
            continue
        if len(bucket["papers"]) < min_papers or bucket["argued"] < min_argued:
            continue
        out.append({
            "concept": tag,
            "papers": sorted(bucket["papers"]),
            "argued": bucket["argued"],
            "statements": sorted(bucket["claims"]),
        })
    out.sort(key=lambda c: (-len(c["papers"]), -c["argued"], c["concept"]))
    return out
