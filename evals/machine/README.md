# Machine verification

An independent pass over the reading, kept apart from the human gold set
in `../gold/`.

The five gates in `extract.py` run inside the reading. The thing none of
them measures is the one the drafting model is least able to judge about itself —
whether the paraphrase says what the quote says. This directory holds the
answer to that question when a *different* reader gave it.

    python3 scripts/verify_extraction.py packet --paper resource:arxiv:2606.03237
    python3 scripts/verify_extraction.py record --answers answers.yml --by <verifier>

The verifier must not be whoever drafted the statements, and is given the
statement, its quote and its section — no gloss, no tags, no attribution, and
in an order that is not the order they were produced in.

**This is triage, not review.** A disagreement moves a statement to
`needs-review` so a person reaches it first. Agreement changes nothing. Only a
named human's verdict in `../gold/claims.yml` ever reaches `reviewed`, and the
two files are separate so a number drawn from one can never quietly include
the other.

Each answer is bound to a fingerprint of the wording it judged, so a
re-reading invalidates it exactly as it invalidates a human verdict.
