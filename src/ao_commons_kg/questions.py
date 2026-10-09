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
