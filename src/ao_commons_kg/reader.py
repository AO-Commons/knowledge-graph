"""Drafting claims out of one paper, with a model, under the gates.

Reading a paper has been a thing somebody did in a session: a model read the
full text, drafted claims, and `extract.check` refused the ones that failed a
gate. That works and it does not scale past whoever is sitting there — 27 of
399 records have been read, and the ones waiting are not waiting on judgment.

This is the same reading with the sitting-there removed. The gates do not
move: `extract.check` runs on what comes back exactly as it ran on what a
session produced, and a claim whose quote is not in the paper is refused here
for the same reason it was refused there. What is new is only who starts it.

Three things this is careful about.

**It drafts from the body, not from the abstract.** `drafting_sections`
decides what the model sees, because an abstract yields a paper's advertising
and the gates cannot tell the difference. Reading Melting Pot from its
abstract gave three primaries; reading it whole gave nine.

**It never writes a claim it could not quote.** The model is told to quote,
the quote is checked verbatim against the parsed text, and a claim that fails
is dropped rather than repaired. A reconstructed quote is the one error that
survives every later check, because it reads exactly like a real one.

**A reading that cannot run produces nothing.** No key, no full text, an
unparseable reply — each raises. None of them yields an empty claims file,
which would record "this paper has nothing to say" as though somebody had
looked.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from .extract import Checked, check
from .fulltext import Section, drafting_sections

REPO = Path(__file__).resolve().parent.parent.parent
DEFAULT_MODEL = "claude-opus-5"

#: How much of the paper goes in one request. Long enough for a whole body in
#: almost every case; a paper over this is truncated at a section boundary and
#: the reading says so rather than silently reading half a paper.
MAX_CHARS = 400_000

INSTRUCTIONS = """You are reading one paper for a research library about autonomous \
organizations: organizations in which AI agents hold operational or decision-making \
authority. Draft the claims the paper makes.

A claim is one assertion, stated so it can be understood without the paper open, \
and carried by a sentence you quote from the paper verbatim.

THE SEVEN TYPES

- evidence: something the work reports as observed or measured. This and position \
are the product — they are what a researcher comes looking for.
- position: an argument or recommendation the work makes without evidence of its own.
- protocol: a technique, architecture or mechanism the work introduces or uses. Tag a \
protocol with the technique, NOT with what the paper is about.
- definition: a term the work introduces or fixes the meaning of. "We introduce X: the \
capacity for ..." is a definition, not a protocol. Tag it with the concept it defines.
- background: a statement about the field or prior work rather than this work's own \
contribution. Attribution matters most here.
- limitation: a limit the authors put on their own result. Rare, and worth hunting — \
they live in discussion sections.
- gap: a question the work says is still open.

THE RULES

1. QUOTE VERBATIM. Copy the sentence exactly as it appears, including its hedges. A \
quote you reconstruct or tidy will be checked against the paper and the claim dropped.
2. KEEP THE HEDGE. If the quote says "may" or "suggests", the claim says so too. A \
paraphrase surer than its source is a false claim.
3. ABOUT THE FIELD, NOT THE INSTRUMENT. "The benchmark contains 175 tasks" is a fact \
about the paper's artifact and is not a claim. "Agents completed 24% of tasks" is.
4. SAY WHOSE IT IS. attribution is "own" for the work's own assertion, "other" for one \
it reports from elsewhere — and then attributed_to names whose.
5. READ THE WHOLE BODY. Draw claims from every substantial section you are given, not \
only the first.
6. DO NOT INVENT COVERAGE. If a section says nothing claimable, draw nothing from it.

CONCEPT TAGS

Tag each claim with one to three concepts: existing ones where they fit, otherwise a \
new lowercase hyphenated term naming the idea the claim is about. Do not coin a \
variant of a term already on the list.

Existing concepts:
{vocabulary}

ANSWER

JSON only, no prose around it:

{{"claims": [{{"text": "...", "quote": "...", "standalone": "...", \
"claim_type": "evidence", "attribution": "own", "attributed_to": null, \
"concept_tags": ["..."]}}]}}

`standalone` is one or two sentences giving the claim enough context to be read on \
its own — what was done, to what, with what result.
"""


class ReadingError(RuntimeError):
    """A reading that could not be done. Never an empty reading."""


def _body(sections: list[Section]) -> str:
    """The paper as the model sees it: the body, in order, labelled.

    Through `drafting_sections` rather than by filtering here, because what
    counts as a body section is a judgment the full-text module already makes
    and two copies of it would drift.
    """
    chosen = drafting_sections(sections)
    if not chosen:
        raise ReadingError(
            "no body sections in the parsed full text — nothing to read. The "
            "paper may be held as metadata only, or its HTML may not have "
            "parsed into sections.")
    out, spent = [], 0
    for section in chosen:
        block = f"\n\n## {section.heading}\n\n{section.text}"
        if spent + len(block) > MAX_CHARS:
            out.append("\n\n[the rest of the paper did not fit in one reading]")
            break
        out.append(block)
        spent += len(block)
    return "".join(out).strip()


def prompt(title: str, authors: list[str], sections: list[Section],
           vocabulary=None) -> tuple[str, str]:
    """The system instructions and the user message, built separately.

    Separate because the instructions are the same for every paper and the
    paper is not: it is the cacheable half, and keeping the split visible here
    is what lets a caller use that.
    """
    terms = sorted(vocabulary.concepts) if vocabulary is not None else []
    listed = ", ".join(terms) if terms else "(none yet)"
    system = INSTRUCTIONS.format(vocabulary=listed)
    byline = ", ".join(authors or []) or "unattributed"
    return system, f"# {title}\n\n{byline}\n\n{_body(sections)}"


def parse(reply: str) -> list[dict]:
    """The claims out of a model's answer, or an error.

    A reply that is not JSON is a failed reading, not an empty one. The
    difference matters: an empty claims file says a person looked and found
    nothing, and nobody looked.
    """
    text = (reply or "").strip()
    if not text:
        raise ReadingError("the model returned nothing")
    if fenced := re.search(r"```(?:json)?\s*(.+?)```", text, re.S):
        text = fenced.group(1).strip()
    if (start := text.find("{")) > 0:
        text = text[start:]
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as error:
        raise ReadingError(f"the model's reply is not JSON: {error}") from error
    claims = payload.get("claims") if isinstance(payload, dict) else None
    if not isinstance(claims, list):
        raise ReadingError("the reply has no `claims` list")
    if not claims:
        raise ReadingError(
            "the model drew no claims from this paper. That is a reading that "
            "failed, not a paper with nothing in it — rather than file an empty "
            "record, say so and let somebody look.")
    return [c for c in claims if isinstance(c, dict)]


def anthropic_reader(model: str = DEFAULT_MODEL, *, api_key: str | None = None,
                     max_tokens: int = 16000):
    """A reader backed by the Anthropic API.

    Returns a callable so the drafting stays injectable and testable without a
    network or a key, the same shape as `scope_judge.anthropic_judge` and the
    HTTP fetchers.
    """
    # Before the import, so a missing secret reads as a missing secret rather
    # than as a broken install. The same ordering, for the same reason, as the
    # scope judge.
    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise ReadingError(
            "ANTHROPIC_API_KEY is not set. A reading needs a model, and a run "
            "without this key is a run that does nothing rather than a run "
            "that files an empty paper.")
    import anthropic

    client = anthropic.Anthropic(api_key=key)

    def read(system: str, paper: str) -> str:
        try:
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=[{"type": "text", "text": system,
                         "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": paper}],
            )
        except Exception as error:   # noqa: BLE001 — every failure is one failure
            raise ReadingError(f"the model could not be reached: {error}") from error
        return "".join(block.text for block in response.content
                       if getattr(block, "type", "") == "text")

    return read


def draft(title: str, authors: list[str], sections: list[Section], *,
          reader, vocabulary=None, method: str = DEFAULT_MODEL) -> Checked:
    """Read one paper and put what comes back through the gates.

    The gates are `extract.check`, unchanged and not re-implemented: the same
    five that ran when a person did this in a session, including the verbatim
    check against these sections.
    """
    system, paper = prompt(title, authors, sections, vocabulary)
    candidates = parse(reader(system, paper))
    for candidate in candidates:
        candidate.setdefault("confidence_class", "EXTRACTED")
        candidate["extraction_method"] = (
            f"{method}, drafted from full text under the gated process, "
            "by scripts/read_paper.py; every quote verified verbatim against "
            "the source")
    return check(candidates, sections=sections, vocabulary=vocabulary)
