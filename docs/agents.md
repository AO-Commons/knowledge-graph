# Agents

Who may act here, on whose behalf, and how somebody connects an agent of their
own.

**Status:** Koga is live. Connected agents are a proposal, argued here before
any code moves, because they change who can touch the corpus rather than how.

See also [mcp.md](mcp.md) for the read surface this extends, and
[pipeline.md](pipeline.md) stage 8 for what review is.

## Start from what is already possible

A capable agent can clone this repository today. It can read every statement
and quote, write a filing by hand, open an issue, open a pull request. Nothing
stops it and nothing should: the corpus is public and that is the point.

So a connected-agent surface cannot be justified as access. It has to be
justified as **shape** — and it is, on four counts.

**It knows what needs doing.** The scarce information is not the statements,
it is which of them are waiting on *you*: drawn out of papers carrying your
byline, not yet judged, with their quotes beside them. That list does not
exist in the repository. It is computed from the corpus joined to an
authorship claim, and an agent with a clone has no way to derive it.

**It fails before the corpus does.** A hand-written filing that names a claim
id that was re-extracted last week, or a tag that no longer resolves, becomes
a bad issue, then a bot comment, then somebody's afternoon. The same filing
through a typed call fails in the agent's own loop, with a message saying
which id is wrong, before anything is opened.

**It carries attribution it cannot forge.** An agent with a clone opens a pull
request as whoever's GitHub token it holds, and the corpus learns nothing
about what made it. Through this surface every act carries both ids, because
the server writes them rather than the client asserting them.

**It is a day of work less.** No clone, no YAML schema, no knowledge of how
`data/claims/` is laid out, no bot protocol to reverse-engineer. A token and
five calls.

None of that is capability. All of it is the difference between something a
determined agent could do and something an ordinary one will.

## What an agent gets out of it

For the person: the reviewing their own papers need gets read, not judged, by
something tireless, and arrives as a queue of decisions rather than a pile of
PDFs. The judgment stays theirs and takes a click.

For the library: review is the binding constraint on every other number here,
and this is the only idea anybody has had that moves it without moving who is
accountable for it.

## Identity

Every act carries two ids and neither is optional.

```
actor:agent:<name>      who performed it
actor:person:<login>    on whose behalf
```

The server writes both from the token. An agent cannot assert its own
identity, cannot act for a person who has not connected it, and cannot act
with one id missing.

## Connecting one

```
  your agent ──token──▶ MCP server ──▶ validation ──▶ GitHub issue
                            │                              │
                            │                        the existing bot
                            ▼                              ▼
                      queue, statements,            pull request
                      quotes (read)                        │
                                                   you merge it
                                                           ▼
                                                   verdict in the corpus
```

1. **Name it** on the Agents page. The name is part of its id and does not
   change; ids outlive the sentences under them.
2. **Take the token.** Shown once, scoped to that agent acting for you,
   revocable. It authenticates to the MCP server, which already serves the
   corpus read-only; this adds a handful of write calls beside the read ones.
3. **Point your model at it.** We do not host, proxy, meter or see the model.
   What reaches us is the calls it makes.
4. **Watch it.** Every act lands in a log on your profile. Revoking kills the
   token and keeps the log, because a record of what something did is not
   undone by stopping it doing more.

## The surface

Five calls, on top of the read tools already in [mcp.md](mcp.md).

| Call | Does | Returns |
| --- | --- | --- |
| `queue.list` | the statements waiting on this agent's person | ids, text, quote, kind, paper, what is missing |
| `statement.get` | one of them, in full | text, quote, section, tags, extraction method |
| `filing.draft` | validate a verdict without opening anything | ok, or exactly which id or tag is wrong |
| `filing.open` | open the filing issue on its person's behalf | the issue url |
| `record.propose` | put a paper or tool to the scope scan | the candidate, and the scan's verdict |

`filing.draft` is the one that earns its place. An agent should be able to
check its work against the live corpus as many times as it likes and open
nothing, which is both kinder to the repository and the only way an agent can
tell a disagreement from a mistake.

## Where the line is

**An agent may open the filing issue. A person merges the pull request.**

That is the whole boundary, and it falls where it does because merging is
already the act that records a verdict against a name. Nothing has to be
invented to keep judgment human: the existing flow has a human step in it, and
this puts the agent on the near side of it.

Two consequences worth stating. The bot must read `acting for` and attribute
the verdict to the person rather than to whatever opened the issue, and it
must refuse an issue from an agent that person has not connected. And the
person merging is the consent — so the pull request has to show the quote and
the proposed wording, not just a claim id, or the click is not a judgment.

**Also refused:**

- **Confirming authorship.** An identity claim about a person is made by that
  person.
- **Earning credits.** Reviewing earns because reviewing is scarce and a
  person did it. Proposing earns nothing from anyone: a corpus that pays for
  proposals has a spam incentive and a public repository at the end of it.
- **Acting anonymously.** No act without both ids.
- **Reading somebody else's queue.** There is no design for this and there
  should not be one until somebody asks with a reason.

## Credits, and why a connected agent has none

Koga runs on models the library pays for, which is the only reason it meters
anything: 20 credits a month, spent on the tokens an answer read and wrote.

A connected agent brings its own model and its own bill. It costs us nothing
per act, so it meters nothing. This is not generosity, it is just what is
true — credits bound our inference spend, and an agent we do not run does not
touch it.

Which leaves it unbounded, so it needs a different bound. Proposals and
filings are capped per person per day at the same budget a person has. The
scope scan is ours to run and refusals are its expensive half, so the number
to watch is not the proposal rate but the proposal rate rising while the
refusal rate does not fall.

## What is not built

- Agent tokens, the five calls, and the act log.
- `queue.list` at all: the queue is currently a page, not a value.
- Attribution through `acting for` in the filing bot, and its refusal of
  unconnected agents.
- Quote and proposed wording in the pull request body, which the merge-as-
  consent argument depends on.
- The per-person cap.
