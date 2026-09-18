#!/usr/bin/env python3
"""An independent pass over extracted statements, by somebody who did not
extract them.

The five gates in `extract.py` are mechanical and they run inside the
extraction. What none of them measures is the thing the extractor is least
able to judge about itself: whether the paraphrase says what the quote says.
`extract.py` says so in as many words and leaves it to the reviewer — and the
reviewer is the scarce good, so in practice it went unmeasured.

Paper2Agent's rule is the fix, and it is a rule about *who*, not about what:
every verifier is a fresh agent, distinct from every implementer. Applied
here that means a second pass that never sees the extractor's reasoning. So
this script hands out a packet with the statement, the quote and the section
it came from, and nothing else — no `standalone` gloss written to justify the
reading, no tags, no attribution, no extraction method, and the statements in
an order that is not the order they were produced in. A verifier answering
from that packet is answering the question, not grading its own homework.

What comes back is machine verification and never review. It is recorded in
its own file, keyed by the fingerprint of what was actually judged, and it
cannot promote a statement to `reviewed` — only a named human's verdict does
that. The two files are separate so that a number drawn from one can never
quietly include the other.

    # hand a verifier the packet
    python3 scripts/verify_extraction.py packet --paper resource:arxiv:2606.03237

    # record what they answered
    python3 scripts/verify_extraction.py record --answers answers.yml --by claude-opus-5
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import date
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from ao_commons_kg.claims import load_claims  # noqa: E402

MACHINE = REPO / "evals" / "machine" / "extraction.yml"

VERDICTS = {
    "supported": "the quote says this, no more",
    "overstated": "the quote is about this but the statement claims more than it says",
    "not-in-source": "the quote does not say this",
    "unclear": "the quote is too partial to tell",
}

BRIEF = """\
You are checking statements somebody else read out of a paper. For each one
you are given the statement, the sentence it was drawn from, and the section
that sentence came from. You are not given their reasoning, their tags, or
their notes, because the question is not whether their reasoning was sound —
it is whether the statement says what the quote says.

For each id, answer with one of:

  supported      the quote says this, no more
  overstated     the quote is about this but the statement claims more
  not-in-source  the quote does not say this
  unclear        the quote is too partial to tell

`overstated` is the one worth being strict about. A statement that is true of
the paper as a whole but not supported by the sentence under it is overstated,
not supported. Answer in YAML: `<claim id>: {verdict: <one of the above>,
because: <one sentence>}`.
"""


def packet(paper: str | None, seed: int) -> str:
    """What a verifier sees: the claim, the quote, the section. Nothing else."""
    claims = [c for c in load_claims() if not paper or c.resource_id == paper]
    if not claims:
        raise SystemExit(f"no statements found for {paper!r}")

    # Shuffled, so the order carries none of the extractor's sequence — a
    # verifier reading them in production order infers a narrative that the
    # extractor wrote rather than one the paper supports.
    random.Random(seed).shuffle(claims)

    lines = [BRIEF, "", f"{len(claims)} statement(s) to check.", ""]
    for claim in claims:
        lines += [
            f"## {claim.id}",
            "",
            f"statement: {claim.text}",
            f"quote:     {claim.quote}",
            f"section:   {claim.extracted_from}",
            f"saw:       {claim.fingerprint}",
            "",
        ]
    return "\n".join(lines)


def record(answers: dict, by: str) -> dict:
    """Write an independent pass into its own file, bound to what it judged."""
    claims = {c.id: c for c in load_claims()}
    problems, entries = [], {}

    for claim_id, answer in (answers or {}).items():
        claim = claims.get(claim_id)
        if claim is None:
            problems.append(f"{claim_id}: not a statement in this corpus")
            continue
        if isinstance(answer, str):
            answer = {"verdict": answer}
        verdict = str(answer.get("verdict") or "").strip()
        if verdict not in VERDICTS:
            problems.append(
                f"{claim_id}: unknown verdict {verdict!r}; expected one of "
                f"{sorted(VERDICTS)}")
            continue
        because = str(answer.get("because") or "").strip()
        if not because:
            problems.append(f"{claim_id}: no reason given, and a verdict without one "
                            "cannot be argued with")
            continue
        entries[claim_id] = {
            "verdict": verdict,
            "because": because,
            # Bound to the wording judged, exactly as a human verdict is. A
            # re-extraction must invalidate this pass too, or the corpus would
            # carry a machine check of a sentence that no longer exists.
            "saw": claim.fingerprint,
            "by": by,
            "on": date.today().isoformat(),
        }

    if problems:
        raise SystemExit("The answers have problems:\n  - " + "\n  - ".join(problems))

    existing = {}
    if MACHINE.exists():
        existing = (yaml.safe_load(MACHINE.read_text(encoding="utf-8")) or {}).get(
            "statements") or {}
    existing.update(entries)
    MACHINE.parent.mkdir(parents=True, exist_ok=True)
    MACHINE.write_text(
        yaml.safe_dump({"statements": dict(sorted(existing.items()))},
                       sort_keys=False, allow_unicode=True, width=88),
        encoding="utf-8")

    disputed = [c for c, e in entries.items() if e["verdict"] != "supported"]
    return {"recorded": len(entries), "total": len(existing), "disputed": disputed}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    out = sub.add_parser("packet", help="what a verifier sees")
    out.add_argument("--paper", default=None, help="a resource id; omit for the whole corpus")
    out.add_argument("--seed", type=int, default=0)
    out.add_argument("--out", default="", help="write here instead of stdout")

    took = sub.add_parser("record", help="write an independent pass into its own file")
    took.add_argument("--answers", required=True, help="YAML the verifier returned")
    took.add_argument("--by", required=True, help="who or what answered")

    args = parser.parse_args(argv)

    if args.command == "packet":
        text = packet(args.paper, args.seed)
        if args.out:
            Path(args.out).write_text(text, encoding="utf-8")
            print(f"wrote {args.out}")
        else:
            print(text)
        return 0

    answers = yaml.safe_load(Path(args.answers).read_text(encoding="utf-8")) or {}
    if isinstance(answers, dict) and "statements" in answers:
        answers = answers["statements"]
    result = record(answers, args.by)
    print(f"recorded {result['recorded']}, {result['total']} in the file")
    if result["disputed"]:
        print("\nthe verifier did not agree with extraction on:")
        for claim_id in result["disputed"]:
            print(f"  {claim_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
