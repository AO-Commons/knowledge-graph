"""The scope test, run by a model, on a candidate nobody has read.

This is the judgment that replaces "a human promotes it". The corpus can
grow from its own citations without waiting for an afternoon, and what makes
that safe is not the threshold — structure only says a work is *cited*, never
that it *belongs*. This says whether it belongs.

It deliberately is not the keyword score. `openalex.scope_score` is a
pre-filter and the README already records its ceiling: *Institutions as
cached computation for resource-rational negotiation* scores 1 and is
squarely in scope, while "agentic AI in smart manufacturing" scores well and
usually is not. Keywords rank; they do not admit.

What the model is asked is the scope test as written, plus the exclusion
register, plus a demand that it state what changes *because machine agents
hold authority* — the same sentence the taxonomy requires of a human
proposing an excluded resource. Its answer and its reasoning go into
`source_provenance`, so a bad rule shows up later as a readable pattern
across admitted records rather than a pile nobody can account for.

Trust here is meant to move. Early on every auto-admitted record is a
candidate for human review, and review of those records doubles as the
scan's accuracy score — which is the evidence for relaxing the threshold, or
for tightening it. Until that evidence exists the settings are conservative
on purpose.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from .expansion import Candidate, ScopeVerdict

REPO = Path(__file__).resolve().parent.parent.parent
TAXONOMY = REPO / "taxonomy" / "agentic-org-research-library-taxonomy-v3.md"

DEFAULT_MODEL = "claude-opus-5"

SCOPE_TEST = """An item belongs if it would change how you design, operate, oversee, or hold \
accountable an organization where agents act with real authority. Material about \
collective human decision-making that is unchanged by the presence of agents does not \
belong, however good it is."""


def _exclusion_register(taxonomy_path: Path = TAXONOMY) -> str:
    """The register, read from the taxonomy rather than restated here.

    Restating it would create a second copy that drifts, and the drift would
    be invisible: the model would enforce last month's boundary while the
    document said something else.
    """
    if not taxonomy_path.exists():
        return ""
    text = taxonomy_path.read_text(encoding="utf-8")
    match = re.search(r"## Exclusion register(.*?)(?=\n---|\n## )", text, re.S)
    return match.group(1).strip() if match else ""


def build_prompt(candidate: Candidate, metadata: dict, citing_titles: list[str]) -> str:
    """What the model is shown for a candidate the citation graph proposed."""
    citers = "\n".join(f"  - {t}" for t in citing_titles) or "  (titles unavailable)"
    return _prompt(metadata, f"""It is cited by {candidate.support} papers already in the library:
{citers}

Being cited by several of our papers means the field treats it as part of this \
conversation. It does not mean it passes the scope test — our papers cite optimization, \
neural architectures and game theory generally, and none of that belongs here.""")


def build_scout_prompt(metadata: dict, *, queries: list[str],
                       topics: list[tuple[str, float]], concepts: list[str]) -> str:
    """What the model is shown for a candidate a search proposed.

    The policy above is identical and must stay that way — one scope test,
    one exclusion register, one standard of proof. Only the evidence differs,
    and it differs in a way the model needs told: nothing in the library
    cites this paper, so the usual signal is absent rather than negative.

    Saying "cited by 0 papers" instead, which reusing the citation prompt
    would do, reads as weak evidence when the truth is different evidence.
    """
    asked = "\n".join(f"  - {q}" for q in queries) or "  (unknown)"
    matched = "\n".join(f"  - {code} (score {score})" for code, score in topics[:5]) \
        or "  (none above threshold)"
    seen = ", ".join(concepts) or "none"
    return _prompt(metadata, f"""Nothing in the library cites this paper and it cites nothing \
in the library. It was not proposed by the citation graph at all — it was found by \
searching for what the library is about, so the usual signal is absent rather than \
negative. Judge it on the abstract.

It was returned by these searches:
{asked}

Its text scores against these taxonomy topics:
{matched}

Concepts the library already uses that appear in it: {seen}

A high topic score means the words match a taxonomy about organizations. It is not \
evidence that machine agents hold authority in the work, which is the thing to check.""")


def _prompt(metadata: dict, evidence: str) -> str:
    """The standing policy, which both routes share.

    Split out when the scout arrived so there is one scope test and one
    exclusion register rather than two that drift apart — the second copy
    being the one nobody remembers to update.
    """
    return f"""You are deciding whether one paper belongs in a research library about \
**agentic organizations**: organizations in which machine agents hold operational or \
decision authority.

THE SCOPE TEST
{SCOPE_TEST}

THE EXCLUSION REGISTER — these were deliberately removed and must stay out:
{_exclusion_register()}

HOW THE REGISTER'S DELIBERATIVE-DEMOCRACY LINE IS READ (settled 2026-09-10)
That line excludes human collective decision-making that would be the same
without machines. It does **not** exclude human-AI hybrid decision-making, where
a machine drafts, mediates, advises, or designs the mechanism and humans decide.
The first generation of agentic organizations is overwhelmingly hybrid, so how
authority is shared between people and machines is the live design question
rather than an adjacent one.

The test is whether removing the machine would leave the finding intact. A study
of deliberation quality that happens to use software is out. A study of what
changes when an AI drafts the group's position, or designs the rule people then
ratify, is in.

THE CANDIDATE
Title: {metadata.get('title') or '(unknown)'}
Venue/date: {metadata.get('venue') or '?'} {metadata.get('date') or ''}
Abstract: {metadata.get('abstract') or '(no abstract available)'}

{evidence}

Some work is neither in scope nor to be refused: it is **borrowed
background** — adjacent literature the library points at rather than ingests,
such as an evaluation suite or a foundational method the field builds on.
Section 15 exists for this, and records like Melting Pot are held this way.
Choose it when the work is genuinely load-bearing for this field but is not
itself about organizations where agents hold authority.

Answer with JSON only:
{{"admit": true|false,
  "borrowed_background": true|false,
  "changes_because_agents_hold_authority": "<one sentence: what about designing, \
operating, overseeing or holding accountable an agent-authority organization is \
different because of this work. If nothing, say so plainly and admit must be false>",
  "reasoning": "<two sentences at most, naming the exclusion-register line if one applies>"}}

Refuse anything you are unsure about. A wrong admission is expensive and quiet — it sits \
in the corpus looking like a curated record — while a wrong refusal costs one paper that \
a person can add by hand."""


class ScanUnreadable(ValueError):
    """The model answered, and the answer was not usable."""


def parse_verdict(body: str) -> dict:
    r"""Pull the JSON object out of a model response.

    Separated from the API call so the fragile half is testable without a
    key. The first version was `re.search(r"\{.*\}", body, re.S).group(0)`,
    which returns None on anything unexpected and then raises AttributeError
    three frames away — 12 of 32 candidates in the first live run failed
    that way, and the error said nothing about what had actually come back.

    Handles the three shapes that turned up: a bare object, an object inside
    a ```json fence, and an object with prose before or after it. Brace
    matching rather than a regex, because a regex cannot tell a closing
    brace inside a string from the end of the object.
    """
    if not body or not body.strip():
        raise ScanUnreadable("the model returned no text at all")

    text = body.strip()
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            candidate = part[4:] if part.lower().startswith("json") else part
            if candidate.strip().startswith("{"):
                text = candidate.strip()
                break

    start = text.find("{")
    if start < 0:
        raise ScanUnreadable(f"no JSON object in the response: {text[:160]!r}")

    depth, in_string, escaped = 0, False, False
    for index in range(start, len(text)):
        char = text[index]
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
        elif char == '"':
            in_string = not in_string
        elif not in_string:
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:index + 1])
                    except json.JSONDecodeError as error:
                        raise ScanUnreadable(f"malformed JSON: {error}") from error
    raise ScanUnreadable(
        "the JSON object never closed, which usually means the reply hit "
        f"max_tokens: {text[-160:]!r}")


def anthropic_scout_judge(model: str = DEFAULT_MODEL, *, api_key: str | None = None):
    """A scope judge for candidates a search proposed rather than a citation.

    The same model, the same policy and the same refusal discipline: a judge
    that cannot answer refuses, because "the API was down so everything got
    in" is the drift this layer exists to prevent.
    """
    # The key check comes before the import on purpose. A missing key is a
    # configuration fact and the refusal is the same either way, but reaching
    # for the SDK first turns it into ModuleNotFoundError — which reads as a
    # broken install rather than an unset secret, and takes the test that
    # asserts the refusal down with it.
    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. A scout without a scan lists what it "
            "found and judges none of it, which is a sweep that proposes rather "
            "than a sweep that approves.")
    import anthropic

    client = anthropic.Anthropic(api_key=key)

    def judge(find) -> ScopeVerdict:
        try:
            response = client.messages.create(
                model=model,
                max_tokens=2000,
                messages=[{"role": "user", "content": build_scout_prompt(
                    {"title": find.title, "abstract": find.abstract, "date": find.date},
                    queries=list(find.queries),
                    topics=[(c, s) for c, s in find.topics],
                    concepts=list(find.concepts))}],
            )
            body = "".join(block.text for block in response.content
                           if getattr(block, "type", "") == "text")
            payload = parse_verdict(body)
        except Exception as error:  # noqa: BLE001 — any failure is a refusal
            return ScopeVerdict(
                admit=False,
                reasoning=f"scope scan could not complete ({type(error).__name__}: "
                          f"{error}); refused rather than admitted",
                judged_by=model)

        because = (payload.get("changes_because_agents_hold_authority") or "").strip()
        reasoning = (payload.get("reasoning") or "").strip()
        if not because or not reasoning:
            return ScopeVerdict(
                admit=False,
                reasoning="scope scan returned no reasoning; refused, because an "
                          "admission nobody can audit is how a corpus drifts",
                judged_by=model)
        return ScopeVerdict(
            admit=bool(payload.get("admit")),
            reasoning=f"{because} {reasoning}".strip(),
            judged_by=model,
            borrowed_background=bool(payload.get("borrowed_background")),
        )

    return judge


def anthropic_judge(model: str = DEFAULT_MODEL, *, api_key: str | None = None,
                    metadata_for=None, titles: dict[str, str] | None = None):
    """A `ScopeJudge` backed by the Anthropic API.

    Returns a callable so the decision logic stays injectable and testable
    without a network or a key — the same shape as the HTTP fetchers.

    A judge that cannot answer refuses. An exception here must never become
    an admission: the failure mode of "the API was down so everything got
    in" is exactly the drift this layer exists to prevent.
    """
    # The key check comes before the import on purpose. A missing key is a
    # configuration fact and the refusal is the same either way, but reaching
    # for the SDK first turns it into ModuleNotFoundError — which reads as a
    # broken install rather than an unset secret, and takes the test that
    # asserts the refusal down with it.
    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Expansion admits nothing without a "
            "scope judge, so a run without this key is a run that does nothing "
            "rather than a run that approves everything.")
    import anthropic

    client = anthropic.Anthropic(api_key=key)
    titles = titles or {}

    def judge(candidate: Candidate, metadata: dict) -> ScopeVerdict:
        citing = [titles.get(rid, rid) for rid in candidate.cited_by]
        try:
            response = client.messages.create(
                # Generous, because the failure it prevents is silent: a
                # reply cut off mid-object parses as nothing, and the first
                # run lost 12 of 32 candidates that way. Answers are a few
                # hundred tokens; the ceiling is not the cost driver.
                model=model,
                max_tokens=2000,
                messages=[{"role": "user",
                           "content": build_prompt(candidate, metadata, citing)}],
            )
            body = "".join(block.text for block in response.content
                           if getattr(block, "type", "") == "text")
            payload = parse_verdict(body)
        except Exception as error:  # noqa: BLE001 — any failure is a refusal
            return ScopeVerdict(
                admit=False,
                reasoning=f"scope scan could not complete ({type(error).__name__}: "
                          f"{error}); refused rather than admitted",
                judged_by=model)

        because = (payload.get("changes_because_agents_hold_authority") or "").strip()
        reasoning = (payload.get("reasoning") or "").strip()
        if not because or not reasoning:
            return ScopeVerdict(
                admit=False,
                reasoning="scope scan returned no reasoning; refused, because an "
                          "admission nobody can audit is how a corpus drifts",
                judged_by=model)

        return ScopeVerdict(
            admit=bool(payload.get("admit")),
            borrowed_background=bool(payload.get("borrowed_background")),
            reasoning=f"{reasoning} What changes because agents hold authority: {because}",
            judged_by=model)

    return judge
