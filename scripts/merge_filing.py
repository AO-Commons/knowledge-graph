#!/usr/bin/env python3
"""Turn a filing issue into a change against the gold set.

The contribution loop, without asking anyone to use git:

    site  →  prefilled issue  →  this script  →  pull request  →  gold set

Run by `.github/workflows/filing-to-pr.yml` on a labelled issue. Everything a
reviewer decided arrives as YAML in the issue body; this validates it against
the taxonomy and the corpus, merges it, and writes a summary the workflow
puts on the pull request.

Validation is strict on purpose. A filing is a human judgement entering the
only dataset that measures everything else, so a typo'd topic code should
stop the merge and be visible in review rather than land quietly and rot the
baseline.

Usage:  python3 scripts/merge_filing.py --body-file issue.md --author name
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from ao_commons_kg.claims import load_claims, save_claims  # noqa: E402
from ao_commons_kg.fulltext import FullTextError, sections_for, verbatim  # noqa: E402
from ao_commons_kg.models import Claim  # noqa: E402
from ao_commons_kg.resources import load_resources  # noqa: E402
from ao_commons_kg.taxonomy import load_taxonomy  # noqa: E402

GOLD = REPO / "evals" / "gold" / "tags.yml"
CLAIM_GOLD = REPO / "evals" / "gold" / "claims.yml"
TAXONOMY = REPO / "taxonomy" / "agentic-org-research-library-taxonomy-v3.md"

FENCE = re.compile(r"```(?:ya?ml)?\s*(.*?)```", re.S)

CLAIM_VERDICTS = frozenset({"accurate", "overstated", "not-in-source", "ambiguous"})
CLAIM_TYPES = frozenset({"finding", "method", "limitation", "position", "background"})

# A filing that is only claim verdicts still needs a shape for the tag half,
# so the summary reads "0 new decisions" rather than crashing on a missing key.
EMPTY_MERGE = {"added": [], "changed": [], "unchanged": [], "total": 0, "flagged": {}}


class FilingError(ValueError):
    """The filing cannot be merged, with a reason a contributor can act on."""


def extract(body: str) -> dict:
    """Pull the YAML out of an issue body.

    Contributors paste a fenced block from the site. Some will paste it bare,
    so a body that parses as YAML on its own is accepted too — being fussy
    here would reject good work for a formatting detail.

    A filing may carry `records:` (where a record belongs), `claims:` (whether
    a sentence was read correctly), or both — one reviewer, one sitting, two
    judgements, because the expensive part is reading the paper and it should
    be paid once.
    """
    for candidate in [m.group(1) for m in FENCE.finditer(body or "")] + [body or ""]:
        try:
            payload = yaml.safe_load(candidate)
        except yaml.YAMLError:
            continue
        if isinstance(payload, dict) and any(
            isinstance(payload.get(block), dict)
            for block in ("records", "claims", "new_statements")
        ):
            return payload
    raise FilingError(
        "No filing found. Paste the block the site's Submit screen produces, "
        "including the `records:` line."
    )


def validate_claims(payload: dict, *, known_claims: set[str]) -> dict[str, dict]:
    """Check the claim verdicts in a filing.

    Held to the same standard as the topic codes and for the same reason: a
    verdict against a claim id that does not exist is a judgement that will
    never be applied to anything, and finding that out later means the review
    was wasted.
    """
    verdicts = payload.get("claims") or {}
    if not isinstance(verdicts, dict):
        raise FilingError("`claims:` should map claim ids to verdicts.")

    problems: list[str] = []
    cleaned: dict[str, dict] = {}

    for claim_id, entry in verdicts.items():
        if claim_id not in known_claims:
            problems.append(f"{claim_id}: not a claim in this corpus")
            continue
        if isinstance(entry, str):
            entry = {"verdict": entry}
        if not isinstance(entry, dict):
            problems.append(f"{claim_id}: expected a verdict")
            continue

        verdict = entry.get("verdict")
        if verdict not in CLAIM_VERDICTS:
            problems.append(
                f"{claim_id}: unknown verdict {verdict!r}; "
                f"expected one of {sorted(CLAIM_VERDICTS)}"
            )
            continue

        record = {"verdict": verdict,
                  "reviewed_on": str(entry.get("reviewed_on") or date.today().isoformat())}
        if note := entry.get("note"):
            record["note"] = str(note).strip()
        cleaned[claim_id] = record

    if problems:
        raise FilingError(
            "The claim verdicts have problems that need fixing:\n  - "
            + "\n  - ".join(problems)
        )
    return cleaned


def merge_claims(cleaned: dict[str, dict], author: str, gold_path: Path = CLAIM_GOLD) -> dict:
    """Write claim verdicts to their own gold file.

    Separate from the tag gold set on purpose. Tags are what classifier
    accuracy is measured against; a claim verdict measures whether extraction
    read a sentence correctly. One file holding both would give a number that
    answers neither question.
    """
    existing = {}
    if gold_path.exists():
        payload = yaml.safe_load(gold_path.read_text(encoding="utf-8")) or {}
        existing = payload.get("claims") or {}

    added, changed = [], []
    for claim_id, entry in cleaned.items():
        entry = {**entry, "reviewer": author}
        previous = existing.get(claim_id)
        if previous is None:
            added.append(claim_id)
        elif previous.get("verdict") != entry["verdict"]:
            changed.append((claim_id, previous.get("verdict"), entry["verdict"],
                            previous.get("reviewer", "unknown")))
        existing[claim_id] = entry

    gold_path.parent.mkdir(parents=True, exist_ok=True)
    gold_path.write_text(
        yaml.safe_dump({"claims": dict(sorted(existing.items()))},
                       sort_keys=False, allow_unicode=True, width=88),
        encoding="utf-8",
    )
    return {
        "added": added, "changed": changed, "total": len(existing),
        "flagged": [c for c, e in cleaned.items()
                    if e["verdict"] in ("overstated", "not-in-source")],
    }


def validate_new_statements(payload: dict, *, known_records: set[str]) -> dict[str, list]:
    """Check statements a reviewer wrote themselves.

    Held to the same standard as the machine's: one assertion, and a quote that
    is actually in the paper. The quote is verified against the source in
    `merge_new_statements`, where the full text is available — a human writing
    from memory misremembers a sentence just as readily as a model does, and a
    statement nobody can check is the thing this layer exists to not have.
    """
    written = payload.get("new_statements") or {}
    if not isinstance(written, dict):
        raise FilingError("`new_statements:` should map record ids to lists of statements.")

    problems: list[str] = []
    cleaned: dict[str, list] = {}

    for resource_id, entries in written.items():
        if resource_id not in known_records:
            problems.append(f"{resource_id}: not a record in this corpus")
            continue
        if not isinstance(entries, list):
            problems.append(f"{resource_id}: expected a list of statements")
            continue

        for position, entry in enumerate(entries, start=1):
            where = f"{resource_id} statement {position}"
            if not isinstance(entry, dict):
                problems.append(f"{where}: expected a statement with text and quote")
                continue
            text = str(entry.get("text") or "").strip()
            quote = str(entry.get("quote") or "").strip()
            kind = str(entry.get("type") or "finding").strip()
            if len(text) < 10:
                problems.append(f"{where}: no statement text")
                continue
            if len(quote) < 15:
                problems.append(
                    f"{where}: no quote. A statement with no sentence behind it cannot be "
                    "checked by anyone later, which is the whole point of this layer."
                )
                continue
            if kind not in CLAIM_TYPES:
                problems.append(f"{where}: unknown type {kind!r}; "
                                f"expected one of {sorted(CLAIM_TYPES)}")
                continue
            cleaned.setdefault(resource_id, []).append(
                {"text": text, "quote": quote, "type": kind})

    if problems:
        raise FilingError(
            "The new statements have problems that need fixing:\n  - " + "\n  - ".join(problems)
        )
    return cleaned


def merge_new_statements(cleaned: dict[str, list], author: str, issue: int = 0) -> dict:
    """Write reviewer-written statements into the claim files.

    Verified against the paper's full text where we can reach it. A quote that
    is not in the source stops the merge and says so, exactly as it does for
    the machine's own extraction — the standard cannot depend on who wrote it.

    They enter `unreviewed`, like everything else. Writing a statement is not
    the same as a second person agreeing with it, and letting an author confirm
    their own reading would put the one unchecked thing in the corpus behind
    the label that means checked.
    """
    added, unverified, problems = [], [], []

    for resource_id, entries in cleaned.items():
        existing = [c for c in load_claims() if c.resource_id == resource_id]
        arxiv = resource_id.removeprefix("resource:arxiv:") if ":arxiv:" in resource_id else None
        sections = []
        if arxiv:
            try:
                sections = sections_for(arxiv)
            except FullTextError:
                sections = []

        fresh = list(existing)
        start = len(existing)
        for position, entry in enumerate(entries, start=1):
            where = "by hand"
            if sections:
                found = verbatim(entry["quote"], sections)
                if found is None:
                    problems.append(
                        f"{resource_id}: this quote is not in the paper — "
                        f"\"{entry['quote'][:90]}…\""
                    )
                    continue
                where = found
            else:
                unverified.append(resource_id)

            fresh.append(Claim(
                id=f"claim:{resource_id.removeprefix('resource:')}:{start + position}",
                resource_id=resource_id,
                text=entry["text"], quote=entry["quote"], claim_type=entry["type"],
                extracted_from=where,
                extraction_method=f"written by @{author}"
                                  + (f" in issue #{issue}" if issue else ""),
            ))
            added.append(resource_id)

        if fresh != existing:
            save_claims(resource_id, fresh)

    if problems:
        raise FilingError(
            "Some statements quote sentences the paper does not contain:\n  - "
            + "\n  - ".join(problems)
            + "\n\nPaste the sentence exactly as it appears in the source."
        )
    return {"added": added, "unverified": sorted(set(unverified))}


def validate(payload: dict, *, known_records: set[str], known_topics: set[str],
             require: bool = True) -> dict:
    """Check every id and code, and report all problems at once."""
    records = payload.get("records") or {}
    if not records:
        if not require:
            return {}
        raise FilingError("The filing is empty — no records to merge.")

    problems: list[str] = []
    cleaned: dict[str, dict] = {}

    for resource_id, entry in records.items():
        if resource_id not in known_records:
            problems.append(f"{resource_id}: not a record in this corpus")
            continue
        if not isinstance(entry, dict):
            problems.append(f"{resource_id}: expected topics and a date")
            continue

        topics = entry.get("topics") or []
        if isinstance(topics, str):
            topics = [t.strip() for t in topics.split(",") if t.strip()]

        # Unquoted codes parse as YAML floats, and the taxonomy has both 11.1
        # and 11.10 — so `11.10` would silently arrive as 11.1, a different
        # topic, with nothing to notice. Refuse rather than coerce: str(11.1)
        # cannot tell which one the reviewer meant.
        numeric = [t for t in topics if not isinstance(t, str)]
        if numeric:
            problems.append(
                f"{resource_id}: topic codes must be quoted — "
                f"{numeric} were read as numbers. Unquoted, 11.10 becomes 11.1, "
                "which is a different topic. Write topics: [\"11.10\", \"2.2\"]."
            )
            continue

        unknown = [t for t in topics if t not in known_topics]
        if unknown:
            problems.append(f"{resource_id}: not taxonomy codes: {', '.join(unknown)}")
            continue

        record = {
            "topics": sorted(set(topics), key=lambda c: [int(p) for p in c.split(".")]),
            "reviewed_on": str(entry.get("reviewed_on") or date.today().isoformat()),
        }

        # A reviewer's judgement about the record is worth as much as their
        # tags. "Out of scope" says the corpus should not hold this;
        # "nothing fits" says the taxonomy has a gap; an unsure call should
        # not be weighed like a confident one; and a note is usually the
        # sentence that explains a disagreement later.
        verdict = entry.get("verdict")
        if verdict in ("out-of-scope", "no-topic-fits"):
            record["verdict"] = verdict
        elif verdict not in (None, "filed"):
            problems.append(f"{resource_id}: unknown verdict {verdict!r}")
            continue
        if entry.get("unsure"):
            record["unsure"] = True
        if note := entry.get("note"):
            record["note"] = str(note).strip()

        cleaned[resource_id] = record

    if problems:
        raise FilingError(
            "The filing has problems that need fixing before it can be merged:\n  - "
            + "\n  - ".join(problems)
        )
    return cleaned


def merge(cleaned: dict[str, dict], author: str, gold_path: Path = GOLD) -> dict:
    """Write the filing into the gold set, and describe what changed.

    An existing decision is replaced rather than merged, and the summary says
    so. Two reviewers disagreeing is a real signal, and burying it under a
    union of both answers would destroy exactly the information a gold set is
    for.
    """
    existing = {}
    if gold_path.exists():
        payload = yaml.safe_load(gold_path.read_text(encoding="utf-8")) or {}
        existing = payload.get("records") or {}

    added, changed, unchanged = [], [], []
    for resource_id, entry in cleaned.items():
        entry = {**entry, "reviewer": author}
        previous = existing.get(resource_id)
        if previous is None:
            added.append(resource_id)
        elif previous.get("topics") != entry["topics"]:
            changed.append((resource_id, previous.get("topics", []), entry["topics"],
                            previous.get("reviewer", "unknown")))
        else:
            unchanged.append(resource_id)
        existing[resource_id] = entry

    gold_path.parent.mkdir(parents=True, exist_ok=True)
    gold_path.write_text(
        yaml.safe_dump(
            {"records": dict(sorted(existing.items()))},
            sort_keys=False, allow_unicode=True, width=88,
        ),
        encoding="utf-8",
    )
    flagged = {
        "out-of-scope": [r for r, e in cleaned.items() if e.get("verdict") == "out-of-scope"],
        "no-topic-fits": [r for r, e in cleaned.items() if e.get("verdict") == "no-topic-fits"],
        "notes": [(r, e["note"]) for r, e in cleaned.items() if e.get("note")],
    }
    return {"added": added, "changed": changed, "unchanged": unchanged,
            "total": len(existing), "flagged": flagged}


def summarize_claims(result: dict) -> list[str]:
    """The claim half of a filing, said in the reviewer's terms."""
    if not result:
        return []
    lines = [
        "",
        "",
        "### Claims checked",
        "",
        f"- {len(result['added'])} new verdict(s)",
        f"- {result['total']} claim verdict(s) recorded after this",
    ]
    if result["flagged"]:
        lines += [
            "",
            "**Extraction got these wrong** — the paraphrase says more than the source, "
            "or is not in it. Worth a look at the extractor, not just the claim:",
            "",
        ]
        lines += [f"- `{claim_id}`" for claim_id in result["flagged"]]
    if result["changed"]:
        lines += ["", "| Claim | Was | Now | Previously by |", "|---|---|---|---|"]
        for claim_id, before, after, who in result["changed"]:
            lines.append(f"| `{claim_id}` | {before or '—'} | {after} | {who} |")
    return lines


def summarize_new(result: dict) -> list[str]:
    if not result or not result["added"]:
        return []
    lines = ["", "", "### Statements you added", "",
             f"- {len(result['added'])} written by hand, each with its quote checked "
             "against the paper"]
    if result["unverified"]:
        lines += ["", "The quote could not be checked for "
                  + ", ".join(f"`{r}`" for r in result["unverified"])
                  + " — no full text is available for it, so this one is taken on trust."]
    lines += ["", "They enter `unreviewed`, like the machine's. Writing a statement is not "
              "the same as someone else agreeing with it."]
    return lines


def summarize(result: dict, author: str) -> str:
    flagged = result.get("flagged") or {}
    lines = [
        f"Filing from **{author}**.",
        "",
        f"- {len(result['added'])} new decision(s)",
        f"- {len(result['changed'])} that differ from an existing decision",
        f"- {len(result['unchanged'])} already recorded the same way",
        f"- {result['total']} record(s) in the gold set after this",
    ]
    if flagged.get("out-of-scope"):
        lines += ["", "**Flagged as out of scope** — these should probably leave the corpus:", ""]
        lines += [f"- `{r}`" for r in flagged["out-of-scope"]]
    if flagged.get("no-topic-fits"):
        lines += ["", "**Nothing in the taxonomy fitted** — each is a candidate for an alias "
                      "or a new topic:", ""]
        lines += [f"- `{r}`" for r in flagged["no-topic-fits"]]
    if flagged.get("notes"):
        lines += ["", "### Notes from the reviewer", ""]
        lines += [f"- `{r}` — {n}" for r, n in flagged["notes"]]
    if result["changed"]:
        lines += [
            "",
            "### Disagreements",
            "",
            "Two reviewers reading the same paper differently is signal, not noise —",
            "worth a look before merging.",
            "",
            "| Record | Was | Now | Previously by |",
            "|---|---|---|---|",
        ]
        for resource_id, before, after, who in result["changed"]:
            lines.append(
                f"| `{resource_id}` | {', '.join(before) or '—'} | "
                f"{', '.join(after) or 'none apply'} | {who} |"
            )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--body-file", required=True)
    parser.add_argument("--author", default="a contributor")
    parser.add_argument("--issue", type=int, default=0)
    parser.add_argument("--summary-file", default="")
    args = parser.parse_args(argv)

    known_topics = {t.code for t in load_taxonomy(TAXONOMY)}
    known_records = {r.id for r in load_resources()}
    known_claims = {c.id for c in load_claims()}

    try:
        payload = extract(Path(args.body_file).read_text(encoding="utf-8"))
        # A filing may be all tags, all claim verdicts, or both. Requiring
        # records would refuse a reviewer who only checked claims — which is
        # exactly the reviewer this layer needs most.
        claim_verdicts = validate_claims(payload, known_claims=known_claims)
        written = validate_new_statements(payload, known_records=known_records)
        cleaned = validate(payload, known_records=known_records, known_topics=known_topics,
                           require=not (claim_verdicts or written))
        if not cleaned and not claim_verdicts and not written:
            raise FilingError("The filing is empty — nothing to merge.")
        # Before the gold set moves: an unverifiable quote should stop the whole
        # filing, not leave half of it merged and half rejected.
        new_result = merge_new_statements(written, args.author, args.issue) if written else {}
    except FilingError as error:
        message = f"This filing could not be merged.\n\n{error}"
        if args.summary_file:
            Path(args.summary_file).write_text(message, encoding="utf-8")
        print(message, file=sys.stderr)
        return 1

    result = merge(cleaned, args.author) if cleaned else EMPTY_MERGE
    claim_result = merge_claims(claim_verdicts, args.author) if claim_verdicts else {}
    summary = (summarize(result, args.author)
               + "\n".join(summarize_claims(claim_result))
               + "\n".join(summarize_new(new_result)))
    if args.summary_file:
        Path(args.summary_file).write_text(summary, encoding="utf-8")
    print(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
