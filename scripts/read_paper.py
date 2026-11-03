#!/usr/bin/env python3
"""Read one paper down to its claims, from an issue asking for it.

    issue  →  this script  →  claims file  →  pull request  →  verdicts

    python3 scripts/read_paper.py --body-file issue.md --out /tmp/result.json

Run by `.github/workflows/read-paper.yml` on an issue labelled `reading`.

Reading is the expensive half of this library and the half that is behind: 27
of 399 records have claims. Nothing about that is a judgment problem — the
papers are held, in scope, and waiting on somebody's afternoon. This removes
the afternoon.

**Only a verified paper.** `data/verified.yml` is the set a person put on the
list, and it is the gate here: reading is a model call over a whole paper, on
a public repository, startable by anyone with an issue form. Tying it to the
set means the work queue is one somebody already chose, rather than one a
stranger can fill. A record outside the set is refused with that reason, which
is also the request it turns into: put it on the list first.

**Never over existing claims.** A paper already read is refused rather than
redrafted. Claims carry human verdicts and machine checks keyed to their text,
and a second drafting silently invalidates both.

**A reading that fails leaves nothing.** No key, no full text, an unparseable
reply, every claim refused by a gate — each is a refusal with a reason on the
issue, and no file. An empty claims file would say somebody looked and found
nothing, which is the one thing that did not happen.

Exit codes, because the workflow branches on them rather than parsing stdout:

    0   read — the claims file is written and named in --out
    2   refused — not verified, already read, no full text; reason in --out
    3   could not read — configuration or API problem; reason in --out
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

import yaml

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from ao_commons_kg import reader  # noqa: E402
from ao_commons_kg.claims import save_claims, slug_for  # noqa: E402
from ao_commons_kg.concepts import load_vocabulary  # noqa: E402
from ao_commons_kg.models import Claim  # noqa: E402
from ao_commons_kg.resources import load_resources  # noqa: E402

VERIFIED = REPO / "data" / "verified.yml"
CLAIMS = REPO / "data" / "claims"

#: A record id as the form carries it, with or without the `resource:` prefix,
#: bare or in a backtick fence the way GitHub renders one.
RECORD = re.compile(r"`?\s*(resource:[a-z0-9]+:[A-Za-z0-9._\-]+)\s*`?")


class Refused(RuntimeError):
    """The request was understood and will not be done."""


def verified_ids(path: pathlib.Path = VERIFIED) -> set[str]:
    """The set the site opens on, read from the one file that defines it."""
    if not path.exists():
        return set()
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    ids = {r for stream in doc.get("streams") or [] for r in stream.get("records") or []}
    return ids | set((doc.get("build_page") or {}).get("records") or [])


def record_in(body: str) -> str:
    """The record id the issue names.

    The form prefills it, so a body without one is a hand-written issue rather
    than a malformed form, and saying which field is missing is more use than
    saying the body did not parse.
    """
    if found := RECORD.search(body or ""):
        return found.group(1)
    raise Refused(
        "No record id in the issue. A reading is requested from a record's page "
        "on the site, which fills this in — the id looks like "
        "`resource:arxiv:2604.10290`.")


def sections_for(resource):
    """The paper's full text, parsed, or a refusal saying why there is none.

    arXiv is the only source with a parsed body today. A record held as
    metadata only cannot be read, and that is a fact about the corpus rather
    than about the request: saying so is what turns it into a fixable thing.
    """
    from ao_commons_kg import fulltext

    if not resource.arxiv_id:
        raise Refused(
            f"**{resource.title}** has no arXiv id, and arXiv is the only source "
            "this reads full text from today. A paper behind a publisher's page "
            "has to be read by hand.")
    try:
        return fulltext.sections_for(resource.arxiv_id)
    except Exception as error:   # noqa: BLE001 — any failure is no full text
        raise Refused(
            f"The full text of **{resource.title}** could not be fetched or "
            f"parsed: {error}") from error


def read(body: str, *, resources=None, verified=None, claims_dir=CLAIMS,
         make_reader=reader.anthropic_reader, vocabulary=None) -> dict:
    """Do the reading the issue asks for, and return what to say about it.

    Everything injectable, so the gates and the refusals are testable without
    a key or a network — which is the half that matters, because a gate that
    only runs against the real API is a gate nobody runs.
    """
    resource_id = record_in(body)
    resources = load_resources() if resources is None else resources
    held = {r.id: r for r in resources}
    if resource_id not in held:
        raise Refused(f"`{resource_id}` is not a record in the corpus.")
    resource = held[resource_id]

    verified = verified_ids() if verified is None else verified
    if resource_id not in verified:
        raise Refused(
            f"**{resource.title}** is in the graph but not in the verified set, "
            "and reading is limited to that set. Putting it on the list is the "
            "step before this one — `data/verified.yml` says what the set is "
            "and why.")

    held_claims = claims_dir / f"{slug_for(resource_id)}.yml"
    if held_claims.exists():
        # Read straight off the file rather than through `load_claims`, which
        # loads every paper's claims and joins the verdict and machine-check
        # stores to them. One question about one file does not need the corpus.
        doc = yaml.safe_load(held_claims.read_text(encoding="utf-8")) or {}
        existing = len(doc.get("claims") or [])
        raise Refused(
            f"**{resource.title}** has already been read — {existing} claims. "
            "Drafting it again would replace claims that carry verdicts and "
            "machine checks, so it is left alone. To correct one, use "
            "*Report an error* on the record.")

    sections = sections_for(resource)
    vocabulary = load_vocabulary() if vocabulary is None else vocabulary
    checked = reader.draft(resource.title, resource.authors or [], sections,
                           reader=make_reader(), vocabulary=vocabulary)

    if not checked.kept:
        raise Refused(
            f"Every claim drafted from **{resource.title}** was refused by a "
            "gate. That is a failed reading rather than an empty paper, so "
            "nothing was written.\n\n" + _rejections(checked))

    claims = []
    for n, kept in enumerate(checked.kept, start=1):
        claims.append(Claim(
            # `claim:arxiv:2604.10290:1` — the record's own id with its
            # `resource:` swapped, which is how every claim in the corpus is
            # named, rather than a second scheme built from the filename.
            id=f"claim:{resource_id.removeprefix('resource:')}:{n}",
            resource_id=resource_id,
            **{k: v for k, v in kept.items() if k in Claim.__dataclass_fields__
               and k not in ("id", "resource_id")}))
    path = save_claims(resource_id, claims, claims_dir)

    return {
        "resource_id": resource_id,
        "title": resource.title,
        "path": _repo_path(path),
        "kept": len(checked.kept),
        "rejected": len(checked.rejected),
        "new_concepts": checked.new_concepts,
        "summary": summarize(resource.title, checked, path),
    }


def _repo_path(path: pathlib.Path) -> str:
    """The path as the repository names it, when it is in the repository.

    It always is in a real run; it is not under a test's temporary directory,
    and a display string is not worth failing a reading over.
    """
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        return str(path)


def _rejections(checked) -> str:
    by_reason: dict[str, int] = {}
    for rejection in checked.rejected:
        by_reason[rejection.gate] = by_reason.get(rejection.gate, 0) + 1
    if not by_reason:
        return "_No gate recorded a reason, which is itself worth looking at._"
    lines = [f"- **{gate}** — {n}" for gate, n in sorted(by_reason.items())]
    return "Refused by gate:\n\n" + "\n".join(lines)


def summarize(title: str, checked, path: pathlib.Path) -> str:
    """What the bot says on the issue: what it did, and what to check."""
    lines = [
        f"**Read {title}.** {len(checked.kept)} claims drafted and kept, "
        f"{len(checked.rejected)} refused by a gate.",
        "",
        "Every claim here was drafted by a model and carries the sentence it "
        "came from, checked verbatim against the paper. None of it has been "
        "checked by a person — that is the next step, and the pull request is "
        "where to do it.",
    ]
    if checked.rejected:
        lines += ["", _rejections(checked)]
    if warnings := {k: v for k, v in checked.warnings.items() if v}:
        lines += ["", "Warnings, which are reported rather than refused:", ""]
        lines += [f"- **{gate}** — {len(items)}" for gate, items in sorted(warnings.items())]
    if checked.new_concepts:
        lines += ["", "New concept tags proposed: "
                  + ", ".join(f"`{c}`" for c in checked.new_concepts)]
    lines += ["", f"Written to `{path.name}`."]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--body-file", required=True)
    parser.add_argument("--out", default="")
    args = parser.parse_args(argv)

    body = pathlib.Path(args.body_file).read_text(encoding="utf-8")

    def record(payload: dict, code: int) -> int:
        if args.out:
            pathlib.Path(args.out).write_text(json.dumps(payload, indent=1),
                                              encoding="utf-8")
        print(payload.get("summary", ""), file=sys.stderr if code else sys.stdout)
        return code

    try:
        return record(read(body), 0)
    except Refused as refusal:
        return record({"summary": f"**This reading was not done.**\n\n{refusal}"}, 2)
    except reader.ReadingError as error:
        return record({"summary": (
            "**This reading could not be done**, which is a problem with the "
            f"reader rather than with the paper.\n\n{error}")}, 3)


if __name__ == "__main__":
    sys.exit(main())
