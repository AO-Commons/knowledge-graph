"""The question layer: what it must refuse, and what it must count."""

from __future__ import annotations

import pytest
import yaml

from ao_commons_kg.claims import load_claims
from ao_commons_kg.models import Question, RelationType
from ao_commons_kg.questions import QuestionError, load_questions, reach


def write(tmp_path, payload):
    path = tmp_path / "questions.yml"
    path.write_text(yaml.safe_dump(payload, allow_unicode=True), encoding="utf-8")
    return path


OCCURRENCE = {"claim": "claim:arxiv:2509.14485:6", "because": "it says so"}


def minimal(**over):
    entry = {
        "id": "question:x",
        "text": "Does it hold?",
        "note": "because they ask the same thing",
        "addressed_by": [OCCURRENCE],
    }
    entry.update(over)
    return {"questions": [entry]}


def test_a_question_must_be_a_question():
    # A statement here would assert something no paper said.
    with pytest.raises(ValueError, match="phrased as a question"):
        Question(id="question:x", text="It does not hold")


def test_a_question_nobody_asks_is_refused(tmp_path):
    path = write(tmp_path, minimal(addressed_by=[]))
    with pytest.raises(QuestionError, match="no statement addresses it"):
        load_questions(path)


def test_an_unexplained_edge_is_refused(tmp_path):
    path = write(tmp_path, minimal(addressed_by=[{"claim": "claim:arxiv:2509.14485:6"}]))
    with pytest.raises(QuestionError, match="missing `because`"):
        load_questions(path)


def test_an_edge_to_a_statement_we_do_not_hold_is_refused(tmp_path):
    path = write(tmp_path, minimal(
        addressed_by=[{"claim": "claim:arxiv:9999.99999:1", "because": "x"}]))
    with pytest.raises(QuestionError, match="not a statement we hold"):
        load_questions(path, claims=load_claims())


def test_duplicate_ids_are_refused(tmp_path):
    payload = minimal()
    payload["questions"].append(dict(payload["questions"][0]))
    with pytest.raises(QuestionError, match="duplicate id"):
        load_questions(write(tmp_path, payload))


def test_every_edge_is_inferred_and_carries_its_reasoning(tmp_path):
    _, edges = load_questions(write(tmp_path, minimal()))
    assert [e.relation for e in edges] == [RelationType.ADDRESSES]
    assert edges[0].confidence_class.value == "INFERRED"
    assert edges[0].source_location == "it says so"


def test_papers_and_occurrences_are_counted_apart():
    """The difference is the only reason the layer is worth having.

    A question asked twice by one paper is that paper's framing. A question
    asked by two papers is a statement about a field. Counting them as one
    number would let the first pass for the second.
    """
    claims = list(load_claims())
    questions, edges = load_questions(claims=claims)
    counts = reach(questions, edges, claims)

    # Asked three times by two papers: a statement about a field.
    transfer = counts["question:capability-measurement-transfer"]
    assert transfer["occurrences"] == 3
    assert transfer["papers"] == 2

    # Asked twice by one paper: that paper's framing, and a single number
    # over both would let it pass for the one above.
    identity = counts["question:accountability-under-unstable-identity"]
    assert identity["occurrences"] == 2
    assert identity["papers"] == 1


def test_the_corpus_questions_all_load_and_point_somewhere_real():
    claims = list(load_claims())
    held = {c.id for c in claims}
    questions, edges = load_questions(claims=claims)
    assert questions, "data/questions.yml should hold the corpus's questions"
    for question in questions:
        assert question.note, f"{question.id} must say why its statements are one question"
        assert question.asserted_by, f"{question.id} must say who made the judgment"
    for edge in edges:
        assert edge.source_id in held
        assert edge.target_id in {q.id for q in questions}


def test_every_gap_statement_is_accounted_for():
    """A gap the layer silently drops is worse than one it clusters wrongly.

    The point of hunting gaps separately at extraction is that each one is a
    question somebody asked. One that reaches no question is invisible on the
    surface the layer exists to produce, so it fails here instead.
    """
    claims = list(load_claims())
    gaps = {c.id for c in claims if c.claim_type.value == "gap"}
    _, edges = load_questions(claims=claims)
    addressed = {e.source_id for e in edges}
    assert gaps <= addressed, f"gap statements with no question: {sorted(gaps - addressed)}"
