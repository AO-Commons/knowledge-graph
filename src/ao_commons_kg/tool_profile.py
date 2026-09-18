"""Profiling a mirrored tool by reading its own documentation.

The mirror holds 60 entries and one of them has been promoted. That gap is not
an oversight — it is the cost of the rule the mirror is built on:

    Nothing here is a claim by AO Commons about a tool; a profiled record in
    data/resources/ is.

Upstream's one-line description is their judgment. A profile is ours, and it
answers two questions the list does not: what may agents do, and what stops
them. Answering those has meant somebody reading the tool's documentation, and
it has happened nine times in the life of the project.

This does the reading. It is the tooling counterpart of `scope_judge`, and it
borrows that module's discipline wholesale, because the failure it prevents is
the same one: a plausible answer nobody checked, indistinguishable afterwards
from one somebody did.

Three rules carried over, and one that is new.

**A profiler that cannot answer refuses.** No key, no documents, no profile —
never a profile assembled from the upstream blurb, which is the one source
explicitly ruled out.

**Every claim cites the document it came from.** `sources[].supports` names the
fields each document backs. A field no document supports is left unset, which
is what the tri-state `yes/no/partial/unknown` values are for: an unresearched
tool must never come out silently recorded as proprietary.

**What is not documented is written down.** The nine hand-made profiles do this
already — "Rate limits, recipient allowlists and the scope of audit logging are
not documented" is the most useful sentence in the AgentTeam record, because it
tells a reader what they would have to find out themselves.

**And the new one: this opens a pull request.** `grow.yml` commits a paper
straight to main on a blast-radius argument — a new record changes no existing
judgment and `git revert` undoes it. That argument does not transfer. A profile
asserts what somebody else's software does and does not let agents do, under
our name, and a wrong one is a claim about a third party rather than a row in
our own pile. Claims about other people's software get a human.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from .facets import BY_NAME
from .tooling import Entry

CONTACT = "anke@stellar.org"
DEFAULT_MODEL = "claude-opus-5"

REPO = Path(__file__).resolve().parent.parent.parent
RESOURCES = REPO / "data" / "resources"

# The fields a profile may assert. Anything the model returns outside this set
# is dropped rather than written: the schema is small on purpose, and a profile
# that invents a field is a profile nothing downstream can read.
PROFILE_FIELDS = (
    "agent_model", "human_controls", "maintainer", "open_source",
    "self_hostable", "model_agnostic", "status", "languages", "license",
)
TRI_STATE = {"yes", "no", "partial", "unknown"}


class ProfileUnavailable(RuntimeError):
    """Raised when a tool cannot be profiled, for any reason.

    One exception type because the caller does the same thing with all of
    them — skip the tool, say why, profile the next one. A run that cannot
    reach one tool's docs is not a failed run.
    """


@dataclass
class Document:
    """One page that was actually fetched, with the text it served."""

    url: str
    title: str
    text: str


@dataclass
class Draft:
    """A profile the model produced, before anything is written.

    `undocumented` is not decoration. It is the field that makes the profile
    honest about its own edges, and a draft without it is refused.
    """

    agent_model: str
    human_controls: str
    undocumented: str
    description: str = ""
    fields: dict = field(default_factory=dict)
    taxonomy_topics: list[str] = field(default_factory=list)
    facets: dict = field(default_factory=dict)
    supports: dict = field(default_factory=dict)
    """document url -> the profile fields that document backs."""
    profiled_by: str = DEFAULT_MODEL


# ---- fetching --------------------------------------------------------------

_RAW = re.compile(r"^https://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$")


def readme_urls(repo_url: str) -> list[str]:
    """Where a GitHub project's README might be, in the order worth trying.

    Raw rather than the API: no token, no rate limit worth worrying about,
    and the text arrives as text instead of base64 inside JSON.
    """
    match = _RAW.match(repo_url.strip())
    if not match:
        return [repo_url]
    owner, repo = match.groups()
    return [f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/{name}"
            for name in ("README.md", "readme.md", "README.rst", "docs/README.md")]


_SCRIPTISH = re.compile(r"<(script|style|noscript|svg|head)\b.*?</\1>", re.S | re.I)
_TAG = re.compile(r"<[^>]+>")
_BLANK = re.compile(r"\n{3,}")


def to_text(body: str) -> str:
    """HTML down to the words, or markdown through untouched.

    A documentation page is mostly not documentation. LangGraph's own
    human-in-the-loop page is 200,000 characters, and the first 60,000 — the
    slice that would reach the model — are script tags and navigation. The
    profiler refused the tool twice before this existed, on a page that
    answers the question directly.

    Deliberately crude: no parser, no dependency, no attempt to keep
    structure. The model is reading for two facts, not rendering the page.
    """
    if "<html" not in body[:2000].lower() and "<!doctype" not in body[:200].lower():
        return body
    text = _SCRIPTISH.sub(" ", body)
    text = _TAG.sub(" ", text)
    for entity, char in (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                         ("&quot;", '"'), ("&#39;", "'"), ("&nbsp;", " ")):
        text = text.replace(entity, char)
    text = re.sub(r"[ \t]+", " ", text)
    return _BLANK.sub("\n\n", "\n".join(line.strip() for line in text.splitlines())).strip()


def fetch(url: str, *, timeout: int = 30, limit: int = 200_000) -> str:
    """One document, as text.

    Capped, because a profile is built from a tool's front door and its
    oversight documentation, not from its whole site. The cap is generous
    enough that no README in the mirror comes close to it and small enough
    that a page serving a bundled JavaScript blob cannot blow up the prompt.
    """
    request = urllib.request.Request(
        url, headers={"User-Agent": f"ao-commons-kg ({CONTACT})"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            # Read past the cap and then trim: the cap exists to bound the
            # prompt, and trimming raw HTML at 200k leaves the words in the
            # last 140k of markup unread.
            return to_text(response.read(limit * 4).decode("utf-8", "ignore"))[:limit]
    except Exception as error:  # noqa: BLE001 — the reason varies, the answer does not
        raise ProfileUnavailable(f"{url}: {type(error).__name__}: {error}") from error


_MD_LINK = re.compile(r"\[[^\]]*\]\((https?://[^)\s]+)\)")

# Pages that tend to answer the two questions. A README is a feature list and
# usually says what the tool can do; what constrains an agent is written down
# somewhere else, if it is written down at all. The first live run refused
# LangGraph on its README alone, correctly — the answer is on its docs site.
_WORTH_READING = re.compile(
    r"(human|approval|approve|oversight|permission|guardrail|safety|security|"
    r"interrupt|breakpoint|checkpoint|auth|policy|limit|budget|audit|"
    r"concepts?/agents?|concepts?/tasks?)", re.I)
_NOT_DOCS = re.compile(
    r"(twitter\.com|x\.com|discord|slack\.com|youtube|linkedin|badge|shields\.io|"
    r"\.(png|jpg|jpeg|gif|svg|mp4|zip)$)", re.I)


def doc_links(readme: str, *, limit: int = 3) -> list[str]:
    """Documentation worth fetching, named by the README itself.

    Only links the project put in its own front page, and only ones whose URL
    suggests they are about what a person may or must do. Following everything
    would turn a profile into a crawl, and the cost of a crawl is not the
    bandwidth — it is that the prompt fills with marketing.
    """
    seen, out = set(), []
    for url in _MD_LINK.findall(readme):
        url = url.split("#")[0].rstrip("/")
        if url in seen or _NOT_DOCS.search(url) or not _WORTH_READING.search(url):
            continue
        seen.add(url)
        out.append(url)
        if len(out) >= limit:
            break
    return out


def documents_for(entry: Entry, *, fetcher=fetch, follow: int = 3) -> list[Document]:
    """The tool's own documentation, or nothing.

    Nothing is a real answer. A tool whose README cannot be read is a tool
    this cannot profile, and the record it would otherwise write would be the
    upstream description with our name on it.
    """
    readme = ""
    found: list[Document] = []
    for url in readme_urls(entry.url):
        try:
            text = fetcher(url)
        except ProfileUnavailable:
            continue
        if text.strip():
            readme = text
            found.append(Document(url=entry.url, title=f"{entry.name} — repository README",
                                  text=text))
            break
    if not found:
        raise ProfileUnavailable(f"{entry.name}: no readable documentation at {entry.url}")

    for url in doc_links(readme, limit=follow):
        try:
            text = fetcher(url)
        except ProfileUnavailable:
            continue        # a page that will not load is not a failed profile
        if text.strip():
            found.append(Document(url=url, title=f"{entry.name} — {page_title(url)}", text=text))
    return found


def page_title(url: str) -> str:
    """A readable name for a documentation page, from its own path.

    `LangGraph — https://docs.langchain.com/oss/python/langgraph/interrupts`
    is not a citation anybody reads. `LangGraph — Docs: interrupts` is.
    """
    tail = url.rstrip("/").split("/")[-1].split("?")[0]
    tail = re.sub(r"\.(html?|md)$", "", tail).replace("-", " ").replace("_", " ")
    return f"Docs: {tail}" if tail else "Documentation"


# ---- the prompt ------------------------------------------------------------

def build_prompt(entry: Entry, documents: list[Document]) -> str:
    """What the model is asked.

    The upstream description is shown and immediately disqualified as
    evidence. It is included because it says which shelf the list put the
    tool on, which is useful context for reading the docs — and excluded as
    a source because the whole point of a profile is that somebody went past
    it.
    """
    vocab = {name: BY_NAME[name].values for name in
             ("artifact_type", "evidence_strength", "autonomy_level_addressed",
              "source_independence", "maturity_of_subject", "temporal_relevance",
              "applicability")}
    facet_lines = "\n".join(f"- {name}: {' | '.join(values)}" for name, values in vocab.items())
    docs = "\n\n".join(
        f"### Document {i + 1} — {d.title}\n<{d.url}>\n\n{d.text[:60_000]}"
        for i, d in enumerate(documents))

    return f"""You are profiling a developer tool for a research library about \
agentic organizations: organizations where machine agents hold operational or \
decision authority.

The library already lists this tool. What it does not have is an answer to the \
two questions that matter here:

1. **What may agents do?** What authority does this tool actually hand to a \
machine — what can it act on, spend, send, change, or decide?
2. **What stops them?** What oversight ships with it — approvals, budgets, \
allowlists, audit logs, veto windows, rate limits, scopes, kill switches?

Answer only from the documents below. The tool is listed upstream as:

> {entry.description}

**That sentence is not evidence.** It is another project's judgment, and the \
reason this profile exists is that somebody read past it. Do not repeat it, \
and do not let it fill a gap the documents leave.

## Facet vocabularies

Use these exact values, or omit the facet:

{facet_lines}

## The documents

{docs}

## Answer

Reply with one JSON object and nothing else:

{{
  "agent_model": "What the tool lets agents do, in the documentation's own terms. Quote it where the wording matters.",
  "human_controls": "What constrains them. Name the mechanism, and say whether it is the product or a setting somebody has to turn on.",
  "undocumented": "What a reader would want to know and the documents do not say. Be specific — 'rate limits, recipient allowlists and the scope of audit logging are not documented' is useful; 'some details are missing' is not.",
  "description": "One or two sentences. What this is, and what makes it interesting to somebody designing an organization agents work in.",
  "fields": {{
    "maintainer": "who publishes it, or omit",
    "open_source": "yes | no | partial | unknown",
    "self_hostable": "yes | no | partial | unknown",
    "model_agnostic": "yes | no | partial | unknown",
    "status": "active | dormant | archived, or omit",
    "languages": ["as the repository reports them"],
    "license": "SPDX identifier, or omit"
  }},
  "facets": {{"artifact_type": "code-tool", "...": "..."}},
  "supports": {{"<document url>": ["agent_model", "human_controls", "..."]}},
  "confident": true
}}

Rules that decide whether this profile can be written at all:

- **Omit what the documents do not support.** Every tri-state field has an \
`unknown` value and every other field may be left out. A guess that reads like \
a finding is the failure this is written to avoid — nobody goes back to check.
- **`supports` must name a real document URL** from the list above, and only \
fields you actually took from it. This is how a reader gets from a claim to \
the page it came from.
- **Set `confident` to false** if the documents do not say enough to answer \
questions 1 and 2. That is a normal outcome for a tool whose README is a \
feature list, and a refusal is worth more than a profile assembled from \
adjacent facts."""


# ---- the model -------------------------------------------------------------

def parse_draft(body: str) -> dict:
    """The JSON object out of a reply, or an explanation of why there isn't one."""
    text = body.strip()
    start = text.find("{")
    if start == -1:
        raise ProfileUnavailable(f"no JSON object in the reply: {text[:160]!r}")
    depth = 0
    for index in range(start, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:index + 1])
                except json.JSONDecodeError as error:
                    raise ProfileUnavailable(f"malformed JSON: {error}") from error
    raise ProfileUnavailable(
        "the JSON object never closed, which usually means the reply hit "
        f"max_tokens: {text[-160:]!r}")


def anthropic_profiler(model: str = DEFAULT_MODEL, *, api_key: str | None = None):
    """A profiler backed by the Anthropic API.

    Returns a callable so the rest of this module stays testable without a
    network or a key, the same shape as `scope_judge.anthropic_judge` and the
    HTTP fetchers.
    """
    import anthropic

    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise ProfileUnavailable(
            "ANTHROPIC_API_KEY is not set. Profiling writes nothing without it, "
            "because the fallback for an unread document is an empty queue "
            "rather than the upstream blurb with our name on it.")
    client = anthropic.Anthropic(api_key=key)

    def profile(entry: Entry, documents: list[Document]) -> Draft:
        try:
            response = client.messages.create(
                model=model,
                # A profile is two paragraphs of prose plus a dozen short
                # fields. Generous anyway: a reply cut off mid-object parses
                # as nothing, and the whole tool is lost rather than degraded.
                max_tokens=4000,
                messages=[{"role": "user", "content": build_prompt(entry, documents)}],
            )
            body = "".join(block.text for block in response.content
                           if getattr(block, "type", "") == "text")
        except ProfileUnavailable:
            raise
        except Exception as error:  # noqa: BLE001 — any failure is a refusal
            raise ProfileUnavailable(
                f"{entry.name}: the profiler could not complete "
                f"({type(error).__name__}: {error})") from error

        return draft_from(entry, documents, parse_draft(body), model=model)

    return profile


def draft_from(entry: Entry, documents: list[Document], payload: dict, *,
               model: str = DEFAULT_MODEL) -> Draft:
    """Validate a reply into a Draft, or refuse it.

    Separate from the API call so the validation is testable on its own, and
    because this is where the rules actually live.
    """
    if payload.get("confident") is False:
        raise ProfileUnavailable(
            f"{entry.name}: the documentation does not say what agents may do "
            "or what constrains them; refused rather than guessed")

    agent_model = (payload.get("agent_model") or "").strip()
    human_controls = (payload.get("human_controls") or "").strip()
    undocumented = (payload.get("undocumented") or "").strip()
    if not agent_model or not human_controls:
        raise ProfileUnavailable(
            f"{entry.name}: a profile with no answer to what agents may do, or "
            "to what stops them, is the upstream description with more words")
    if not undocumented:
        raise ProfileUnavailable(
            f"{entry.name}: the profile does not say what the documents leave "
            "out. A profile that claims to be complete is the one to distrust")

    fields = {}
    for name, value in (payload.get("fields") or {}).items():
        if name not in PROFILE_FIELDS or value in (None, "", []):
            continue
        if name in ("open_source", "self_hostable", "model_agnostic"):
            value = str(value).strip().lower()
            if value not in TRI_STATE or value == "unknown":
                # `unknown` is the default. Writing it explicitly adds a
                # field that says nothing and reads as though somebody looked.
                continue
        fields[name] = value

    facets = {}
    for name, value in (payload.get("facets") or {}).items():
        facet = BY_NAME.get(name)
        if not facet:
            continue
        values = value if isinstance(value, list) else [value]
        allowed = [v for v in values if v in facet.values]
        if allowed:
            facets[name] = allowed if facet.multi else allowed[0]
    # Two of these are facts about the record rather than judgments about the
    # tool, and they are the same for every profile written this way.
    facets.setdefault("artifact_type", "code-tool")
    facets.setdefault("source_independence", "tooling-vendor")

    known = {d.url for d in documents}
    supports = {url: [f for f in fields_list if f in PROFILE_FIELDS]
                for url, fields_list in (payload.get("supports") or {}).items()
                if url in known}
    if not supports:
        raise ProfileUnavailable(
            f"{entry.name}: no claim was traced to a document. An untraceable "
            "profile is worse than no profile, because it looks like the others")

    return Draft(
        agent_model=agent_model,
        human_controls=human_controls,
        undocumented=undocumented,
        description=(payload.get("description") or "").strip(),
        fields=fields,
        taxonomy_topics=[t for t in (payload.get("taxonomy_topics") or []) if isinstance(t, str)],
        facets=facets,
        supports=supports,
        profiled_by=model,
    )


# ---- the record ------------------------------------------------------------

def slug(text: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", text.lower())).strip("-")


def record_for(entry: Entry, draft: Draft, documents: list[Document], *,
               today: str | None = None) -> dict:
    """The YAML payload for one profiled tool.

    Key order matches the hand-written profiles, because these files are read
    and corrected by people and a record that sorts its keys differently from
    its neighbours is harder to diff than it needs to be.
    """
    accessed = today or date.today().isoformat()
    resource_id = f"resource:tool:{slug(entry.name)}"
    by_url = {d.url: d for d in documents}

    tool = {"agent_model": draft.agent_model, "human_controls": draft.human_controls}
    for name in ("maintainer", "open_source", "self_hostable", "model_agnostic",
                 "status", "languages"):
        if name in draft.fields:
            tool[name] = draft.fields[name]

    payload = {
        "id": resource_id,
        "resource_type": "code-tool",
        "title": entry.name,
        "description": draft.description or None,
        "url": entry.url,
        "repository_url": entry.url,
        "license": draft.fields.get("license"),
        # No taxonomy codes. Filing moved to stage 7 and is being derived from
        # what a record's statements say (see docs/pipeline.md); a profiler that
        # guessed at codes would add to the two thirds of records that carry
        # more than one and the 28 that carry none. Left empty deliberately, for
        # derivation or a person to fill.
        "taxonomy_topics": draft.taxonomy_topics,
        "facets": draft.facets,
        "tool": tool,
        "sources": [
            {"url": url,
             "title": by_url[url].title,
             "accessed": accessed,
             "supports": supported}
            for url, supported in draft.supports.items()
        ],
        "source_provenance": (
            f"profiled by {draft.profiled_by} from the tool's own documentation on "
            f"{accessed}, promoted from the awesome-builder-tools mirror (Framework "
            f"Zero, MIT). Every claim about what agents may do and what constrains "
            f"them cites the document it came from. Not documented: {draft.undocumented} "
            f"Unreviewed: no person has checked this against the source."
        ),
        "ingested_at": accessed,
        "review_status": "unreviewed",
    }
    return {k: v for k, v in payload.items() if v not in (None, [], {})}


def existing_links(entries, directory: Path = RESOURCES) -> dict[str, str]:
    """Mirror entries a profile already exists for, keyed by entry name.

    Nine tools have been profiled and one mirror entry says so. The rest were
    written before `promoted_to` existed or by a hand that did not know to set
    it, which makes the shortlist offer up tools that are already done — and
    makes the mirror understate the library by a factor of nine.

    Matched on the repository URL rather than the name, because upstream
    spells two of them as `owner/repo`.
    """
    import yaml

    by_url: dict[str, str] = {}
    for path in sorted(directory.glob("tool-*.yml")):
        try:
            record = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception:  # noqa: BLE001 — a record we cannot read is not a link
            continue
        for key in ("repository_url", "url"):
            value = record.get(key)
            if isinstance(value, str) and record.get("id"):
                by_url[value.rstrip("/").lower()] = record["id"]

    return {entry.name: by_url[entry.url.rstrip("/").lower()]
            for entry in entries
            if not entry.promoted_to and entry.url.rstrip("/").lower() in by_url}


def path_for(resource_id: str, directory: Path = RESOURCES) -> Path:
    return directory / (resource_id.removeprefix("resource:").replace(":", "-") + ".yml")
