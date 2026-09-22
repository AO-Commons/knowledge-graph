"""Answering a question about the library, in Slack.

The same tools the MCP server exposes, with a different mouth. Not a second
retrieval path: `queries.py` is the only way into the graph, and adding a
parallel one is how two surfaces start quietly disagreeing about what the
corpus says.

What makes this worth building rather than pointing people at the site is the
shape of the questions. "Has anyone shown that agent-to-agent approval actually
catches anything?" is not a search box query. It is two or three lookups and a
judgment about what the results do not cover, and the last part is the part a
person is asking for.

Three things it is built to keep saying.

**Graph first, source second.** Search the taxonomy, return compact records,
name five to fifteen sources. Never send the corpus to a model — the tool
results are briefs, the same ones MCP returns, and the papers stay where they
are.

**Nothing here is reviewed.** Zero records reviewed, forty claims extracted out
of a hundred and forty records. An answer that does not say so is a confident
answer assembled from unchecked parts, and the confidence is the part that
travels. `coverage` and `claims_caveat` exist for this and the prompt makes
using them non-optional.

**A gap is an answer.** "The library holds nothing on that" is the single most
useful thing this can say, because it is what turns a question into an
addition. It is also the answer a model is least inclined to give.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from . import queries

DEFAULT_MODEL = "claude-opus-5"

# The tools, and only these. Each is a function in queries.py that returns a
# compact brief — the same contract the MCP server publishes, so an answer here
# and an answer in Claude Desktop come from the same place.
TOOLS = [
    {
        "name": "coverage",
        "description": (
            "How much of the library has been checked by a person. Call this before "
            "relying on anything else: it says how many records are reviewed and how "
            "many claims verified, which decides how much weight any other answer "
            "can carry."),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "search_topics",
        "description": (
            "Find topics in the 103-code taxonomy by word, including aliases. The "
            "taxonomy is what the library is organized by, so this is usually the "
            "first call for a question about a subject rather than a specific paper."),
        "input_schema": {
            "type": "object",
            "properties": {"term": {"type": "string"},
                           "limit": {"type": "integer", "default": 10}},
            "required": ["term"],
        },
    },
    {
        "name": "get_topic",
        "description": "One topic by its code, with its parent, children and what is filed under it.",
        "input_schema": {
            "type": "object",
            "properties": {"code": {"type": "string", "description": "dotted, e.g. 2.2.1"}},
            "required": ["code"],
        },
    },
    {
        "name": "search_records",
        "description": "Find records by words in their title, description or abstract.",
        "input_schema": {
            "type": "object",
            "properties": {"term": {"type": "string"},
                           "limit": {"type": "integer", "default": 10}},
            "required": ["term"],
        },
    },
    {
        "name": "get_record",
        "description": ("One record in full by id, an arXiv id, a DOI, or the URL of "
                        "either. Carries a `link` field — cite that, never the id."),
        "input_schema": {
            "type": "object",
            "properties": {"resource_id": {"type": "string"}},
            "required": ["resource_id"],
        },
    },
    {
        "name": "get_claims",
        "description": (
            "Statements extracted from records, each with the sentence it came from. "
            "A claim is a machine's reading of that sentence until a person has "
            "verified it — quote the sentence, not the paraphrase."),
        "input_schema": {
            "type": "object",
            "properties": {"record": {"type": "string"},
                           "claim_type": {"type": "string"},
                           "limit": {"type": "integer", "default": 20}},
        },
    },
    {
        "name": "related_records",
        "description": (
            "What a record connects to — shared citations, co-citation, shared topics. "
            "Each edge says how it was made."),
        "input_schema": {
            "type": "object",
            "properties": {"resource_id": {"type": "string"},
                           "limit": {"type": "integer", "default": 10}},
            "required": ["resource_id"],
        },
    },
    {
        "name": "tools_for",
        "description": (
            "What the library holds bearing on a builder's problem — profiled tools "
            "with the oversight they ship, and the research filed on the same branch. "
            "Resolves through the taxonomy, not by product category. Deliberately not "
            "a recommendation."),
        "input_schema": {
            "type": "object",
            "properties": {"need": {"type": "string"},
                           "limit": {"type": "integer", "default": 8}},
            "required": ["need"],
        },
    },
    {
        "name": "get_author",
        "description": "What one person has in the library, and who they wrote it with.",
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    },
]

SYSTEM = """You answer questions about the AO Commons knowledge graph in Slack: a \
map of research on agentic organizations — organizations where machine agents hold \
operational or decision authority.

You are talking to the people who maintain this library. They know the field. They \
are asking because they want the specific thing the graph holds, not an overview.

## How to answer

Use the tools. Everything you say about the corpus has to come from one of them — \
if you know a paper from training and the graph does not hold it, that is a gap in \
the graph and worth saying, not a fact to state as though you looked it up.

Search the taxonomy before searching records. The library is organized by 103 topic \
codes and a question about a subject is a question about a branch.

**Name a record the way a person would.** The title in quotes, linked, then the \
first author and "et al." if there are others:

    <https://arxiv.org/abs/2506.12469|"Levels of Autonomy for AI Agents"> (Feng et al.)

The link is the record's `link` field, which is always present. **Never print a \
record id.** `resource:arxiv:2506.12469` is a database key; it tells a reader \
nothing and they cannot click it. Give an id only if somebody asks for one.

Topic codes are different — they are how the library is organized and the people \
reading you use them. Give the code with its title: `1.1 Defining the object`.

## What you must not do

**Do not present unreviewed material as settled.** No record in this corpus has been \
reviewed by a person, and claims are a model's reading of a quoted sentence until \
verified. When an answer leans on a claim, quote the sentence it came from rather \
than the paraphrase, and say it is unverified. Call `coverage` when the weight of \
the answer depends on how much has been checked.

**Do not fill a gap.** If the library holds nothing on the question, say exactly \
that. That answer is more useful than an assembled one: it is what turns a question \
into an addition. Never round "three loosely related records" up to "the literature \
says".

**Do not recommend a tool.** Say what oversight each ships and what its \
documentation does not say. Most tools in the mirror are unprofiled.

## How to write

Slack, not a paper. Lead with the answer — the finding or the gap, in the first \
line. No preamble, no restating the question, no offering to help further. Use \
*bold* and `code` sparingly; Slack renders neither markdown headings nor tables, \
and a bullet list beats a paragraph when the shape is a list.

As short as the question allows and no shorter. If the honest answer is one \
sentence, write one sentence; if four records each need a different caveat, that is \
four lines, not a summary that loses which caveat belongs to which."""


@dataclass
class Answer:
    text: str
    tool_calls: list = field(default_factory=list)
    model: str = DEFAULT_MODEL
    stopped_early: bool = False


def run_tool(corpus: queries.Corpus, name: str, args: dict):
    """One tool call against the graph.

    Every branch is a call into queries.py. A tool that did anything else would
    be a second retrieval path, which is how two surfaces start disagreeing.
    """
    if name == "coverage":
        return queries.coverage(corpus)
    if name == "search_topics":
        return queries.search_topics(corpus, args["term"], args.get("limit", 10))
    if name == "get_topic":
        return queries.get_topic(corpus, args["code"])
    if name == "search_records":
        return queries.search_records(corpus, args["term"], args.get("limit", 10))
    if name == "get_record":
        return queries.get_record(corpus, args["resource_id"])
    if name == "get_claims":
        return queries.get_claims(
            corpus, record=args.get("record") or None,
            claim_type=args.get("claim_type") or None, limit=args.get("limit", 20))
    if name == "related_records":
        return queries.related_records(corpus, args["resource_id"], args.get("limit", 10))
    if name == "tools_for":
        return queries.tools_for(corpus, args["need"], args.get("limit", 8))
    if name == "get_author":
        return queries.get_author(corpus, args["name"])
    raise KeyError(name)


def answer(question: str, *, corpus: queries.Corpus | None = None,
           model: str = DEFAULT_MODEL, api_key: str | None = None,
           max_turns: int = 8, history: str = "") -> Answer:
    """Answer one question, using the graph.

    `max_turns` is a ceiling on tool calls, not a target. A question that needs
    more than eight lookups is usually a question the graph cannot answer, and
    the bounded version of "I could not find it" is better than an unbounded
    search that eventually says the same thing more expensively.
    """
    import anthropic

    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. There is no useful fallback here: an "
            "answer about the corpus assembled without reading it is the thing "
            "this is built not to produce.")

    corpus = corpus or queries.Corpus()
    client = anthropic.Anthropic(api_key=key)

    prompt = f"{history}\n\n{question}".strip() if history else question
    messages = [{"role": "user", "content": prompt}]
    calls: list = []

    for _ in range(max_turns):
        response = client.messages.create(
            model=model, max_tokens=2000, system=SYSTEM, tools=TOOLS, messages=messages)
        messages.append({"role": "assistant", "content": response.content})

        uses = [b for b in response.content if getattr(b, "type", "") == "tool_use"]
        if not uses:
            text = "".join(b.text for b in response.content
                           if getattr(b, "type", "") == "text").strip()
            return Answer(text=text, tool_calls=calls, model=response.model)

        results = []
        for use in uses:
            calls.append({"name": use.name, "input": dict(use.input)})
            try:
                payload = run_tool(corpus, use.name, dict(use.input))
                body = json.dumps(payload, ensure_ascii=False, default=str)
            except Exception as error:  # noqa: BLE001 — the model handles this better than a crash
                body = json.dumps({"error": f"{type(error).__name__}: {error}"})
            results.append({"type": "tool_result", "tool_use_id": use.id, "content": body})
        messages.append({"role": "user", "content": results})

    # Out of turns. Say so rather than returning the last partial thought as
    # though it were the answer.
    return Answer(
        text="I could not get to an answer within the lookups I am allowed — which "
             "usually means the graph does not hold this. Worth adding if you have a "
             "source.",
        tool_calls=calls, model=model, stopped_early=True)
