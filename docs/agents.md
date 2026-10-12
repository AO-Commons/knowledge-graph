# Agents

Who may act here, on whose behalf, and what an act is allowed to be.

**Status:** Koga is live. Connected agents are a proposal, argued here before
any code moves, because they change who can touch the corpus rather than how.

For what an agent may read, see [mcp.md](mcp.md). For what review is and why
it is the scarce good, see [pipeline.md](pipeline.md), stage 8.

## Two kinds of agent

**Koga** is the library's own, one per person who signs in. It runs on models
we pay for, which is why it meters credits: 20 a month, spent on the tokens an
answer actually read and wrote. It is the only agent that spends them.

**A connected agent** is somebody else's, brought with its own model and its
own bill. It costs the library nothing per act, so it meters nothing. The
asymmetry is not a favour to us or to them; it is just what is true. Credits
exist to bound our inference spend, and an agent we do not run does not touch
it.

Everything below is about connected agents. Koga's permissions are the same
minus the ones that need a key we do not hold.

## Identity

Every act carries two ids and neither is optional.

```
actor:agent:<name>      who performed it
actor:person:<login>    on whose behalf
```

An agent cannot exist without a person behind it, cannot be transferred
between people, and cannot act with only one of the two recorded. This is the
same rule the extraction pipeline already follows when a model drafts a
statement: a machine's act is attributable to a machine, and the person who
pointed it at the corpus is attributable too.

## Connecting one

1. **Name it**, on the Agents page. The name is part of its id and does not
   change, because ids outlive the sentences under them.
2. **Take the token.** Shown once, scoped to `actor:agent:<name>` acting for
   you, revocable at any time. It authenticates to the MCP server, which is
   already how an assistant reads the corpus; this adds a write surface beside
   the read one.
3. **Point your model at it.** We do not host, proxy, or see the model. What
   reaches us is the acts it takes.
4. **Watch it.** Every act appears in a log on your profile with its
   timestamp. Revoking kills the token and leaves the log, because a record of
   what something did is not undone by taking away its ability to do more.

## What a connected agent may do

**Read everything.** The corpus is public and a release is a file. Nothing is
gained by making an agent scrape what it could clone.

**See its person's review queue.** The statements drawn out of papers carrying
your byline, which are yours to judge and nobody else's. An agent that cannot
see them cannot help with the one job that matters.

**Draft a recommendation.** For any statement in that queue, an agent may
attach a proposed verdict — accurate, adjust with this wording, or
not-in-source — with its reasoning. A recommendation is a draft addressed to
its person. It is marked as the agent's, it is never counted as review, and it
changes nothing until that person files it under their own name.

This is the whole point of connecting one. Reading twelve statements against
their quotes is exactly the kind of work a model is good at and a person finds
tedious, and the bottleneck is not the reading. It is the judging. A
recommendation moves the reading off the person and leaves the judgment where
it belongs.

**Propose a record.** Same path as the Add form, same scope scan, same
refusal. It proposes and never admits, exactly as the scout does.

**File an issue on its person's behalf.** Feedback, a correction, a wrongly
clustered question. The issue body carries both ids, so a reader of the
repository can see that a machine wrote it and which person is answerable for
it.

## What it may not do

**File a verdict.** This is the one that matters and the one that will be
argued about. Review is the only thing in this pipeline no machine does, and
the whole trust model rests on a judgment being a named person's: a verdict is
recorded against a human name in a pull request anybody can read, and that is
what the number means. An agent filing on your behalf converts "machines
admit, people judge" into a slogan, and leaves the ledger unable to tell a
statement somebody read from one somebody's script approved. A recommendation
is one click from a verdict. That click is the product.

**Confirm authorship.** An identity claim about a person is made by that
person.

**Earn credits.** Koga's credits are ours to grant, and granting them for acts
a machine performed would be paying for volume. Reviewing earns, because
reviewing is scarce and a person did it. Proposing does not, from an agent or
otherwise: a corpus that pays for proposals is a corpus with a spam incentive
and a public repository at the end of it.

**Act anonymously.** No act without both ids.

## Rate and abuse

A connected agent costs us nothing per act and therefore has no credit bound,
which means it needs a different one. Proposals are capped per person per day,
at the same budget a person has, because the scope scan is ours to run and
refusals are the expensive half. A proposal rate that rises without the
refusal rate falling is the signal worth watching.

## What is not built

- Agent tokens, the write surface on MCP, and the act log.
- Recommendations: the storage, the review screen's second column, and the
  one-click path from a recommendation to a filed verdict.
- The per-person proposal cap.
- Anything that lets an agent see another person's queue. There is no design
  for this and there should not be one until somebody asks for it with a
  reason.
