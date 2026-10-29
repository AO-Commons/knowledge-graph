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
    # A claim here would assert something no paper said.
    with pytest.raises(ValueError, match="phrased as a question"):
        Question(id="question:x", text="It does not hold")


def test_a_question_nobody_asks_is_refused(tmp_path):
    path = write(tmp_path, minimal(addressed_by=[]))
    with pytest.raises(QuestionError, match="no claim addresses it"):
        load_questions(path)


def test_an_unexplained_edge_is_refused(tmp_path):
    path = write(tmp_path, minimal(addressed_by=[{"claim": "claim:arxiv:2509.14485:6"}]))
    with pytest.raises(QuestionError, match="missing `because`"):
        load_questions(path)


def test_an_edge_to_a_statement_we_do_not_hold_is_refused(tmp_path):
    path = write(tmp_path, minimal(
        addressed_by=[{"claim": "claim:arxiv:9999.99999:1", "because": "x"}]))
    with pytest.raises(QuestionError, match="not a claim we hold"):
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
    asked by two papers is a claim about a field. Counting them as one
    number would let the first pass for the second.
    """
    claims = list(load_claims())
    questions, edges = load_questions(claims=claims)
    counts = reach(questions, edges, claims)

    # Asked three times by two papers: a claim about a field.
    transfer = counts["question:capability-measurement-transfer"]
    assert transfer["occurrences"] == 3
    assert transfer["papers"] == 2

    # And at least one of the other case: asked more than once, all from one
    # paper, which is that paper's framing rather than a claim about a field.
    #
    # Found rather than named. This named a question twice — the identity
    # one, then the attribution one — and both times a later paper reached
    # it and turned it into an example of the case above, failing this test
    # on the corpus getting better. What has to hold is that the two counts
    # are kept apart, not which question happens to illustrate it.
    framings = [q for q, n in counts.items()
                if n["papers"] == 1 and n["occurrences"] > 1]
    assert framings, "no question is asked twice by one paper"
    for question in framings:
        assert counts[question]["occurrences"] > counts[question]["papers"]

    # The distinction is only worth testing if the corpus holds both kinds.
    crossing = [q for q, n in counts.items() if n["papers"] > 1]
    assert crossing, "no question is asked by more than one paper"


def test_the_corpus_questions_all_load_and_point_somewhere_real():
    claims = list(load_claims())
    held = {c.id for c in claims}
    questions, edges = load_questions(claims=claims)
    assert questions, "data/questions.yml should hold the corpus's questions"
    for question in questions:
        assert question.note, f"{question.id} must say why its claims are one question"
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
    assert gaps <= addressed, f"gap claims with no question: {sorted(gaps - addressed)}"


# --- proposing ----------------------------------------------------------

def test_propose_leaves_out_what_is_already_clustered():
    """Noise in a proposal list is what stops anybody reading it."""
    from ao_commons_kg.questions import propose

    claims = list(load_claims())
    questions, _ = load_questions(claims=claims)
    covered = {tag for q in questions for tag in q.concept_tags}
    for candidate in propose(claims, questions):
        assert candidate["concept"] not in covered


def test_propose_refuses_a_concept_something_has_been_shown_on():
    """The bound that separates "nobody has shown this" from "you have not read it".

    Loosening it would produce a longer list of weaker proposals, which is the
    failure the repository exists to avoid.
    """
    from ao_commons_kg.questions import propose

    claims = list(load_claims())
    has_finding = {
        tag
        for c in claims
        if (c.claim_type.value if hasattr(c.claim_type, "value") else c.claim_type) == "finding"
        for tag in (c.concept_tags or ())
    }
    for candidate in propose(claims, ()):
        assert candidate["concept"] not in has_finding


def test_propose_needs_more_than_one_paper():
    from ao_commons_kg.questions import propose

    claims = list(load_claims())
    for candidate in propose(claims, ()):
        assert len(candidate["papers"]) >= 2
        assert candidate["argued"] >= 2
