"""The scope test, run by a model, on a candidate nobody has read.

This is the judgement that replaces "a human promotes it". The corpus can
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
    """What the model is shown. One candidate, its abstract, and who cites it."""
    citers = "\n".join(f"  - {t}" for t in citing_titles) or "  (titles unavailable)"
    return f"""You are deciding whether one paper belongs in a research library about \
**agentic organizations**: organizations in which machine agents hold operational or \
decision authority.

THE SCOPE TEST
{SCOPE_TEST}

THE EXCLUSION REGISTER — these were deliberately removed and must stay out:
{_exclusion_register()}

THE CANDIDATE
Title: {metadata.get('title') or '(unknown)'}
Venue/date: {metadata.get('venue') or '?'} {metadata.get('date') or ''}
Abstract: {metadata.get('abstract') or '(no abstract available)'}

It is cited by {candidate.support} papers already in the library:
{citers}

Being cited by several of our papers means the field treats it as part of this \
conversation. It does not mean it passes the scope test — our papers cite optimization, \
neural architectures and game theory generally, and none of that belongs here.

Answer with JSON only:
{{"admit": true|false,
  "changes_because_agents_hold_authority": "<one sentence: what about designing, \
operating, overseeing or holding accountable an agent-authority organization is \
different because of this work. If nothing, say so plainly and admit must be false>",
  "reasoning": "<two sentences at most, naming the exclusion-register line if one applies>"}}

Refuse anything you are unsure about. A wrong admission is expensive and quiet — it sits \
in the corpus looking like a curated record — while a wrong refusal costs one paper that \
a person can add by hand."""


def anthropic_judge(model: str = DEFAULT_MODEL, *, api_key: str | None = None,
                    metadata_for=None, titles: dict[str, str] | None = None):
    """A `ScopeJudge` backed by the Anthropic API.

    Returns a callable so the decision logic stays injectable and testable
    without a network or a key — the same shape as the HTTP fetchers.

    A judge that cannot answer refuses. An exception here must never become
    an admission: the failure mode of "the API was down so everything got
    in" is exactly the drift this layer exists to prevent.
    """
    import anthropic

    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Expansion admits nothing without a "
            "scope judge, so a run without this key is a run that does nothing "
            "rather than a run that approves everything.")
    client = anthropic.Anthropic(api_key=key)
    titles = titles or {}

    def judge(candidate: Candidate, metadata: dict) -> ScopeVerdict:
        citing = [titles.get(rid, rid) for rid in candidate.cited_by]
        try:
            response = client.messages.create(
                model=model,
                max_tokens=600,
                messages=[{"role": "user",
                           "content": build_prompt(candidate, metadata, citing)}],
            )
            body = "".join(block.text for block in response.content
                           if getattr(block, "type", "") == "text")
            payload = json.loads(re.search(r"\{.*\}", body, re.S).group(0))
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
            reasoning=f"{reasoning} What changes because agents hold authority: {because}",
            judged_by=model)

    return judge
