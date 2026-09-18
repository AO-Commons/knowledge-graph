# Profiling a tool

The mirror lists what to build with. This library answers a different question:
what does a tool let agents do, and what stops them. Getting from one to the
other means reading the tool's own documentation, and the mirror says so:

> Nothing here is a claim by AO Commons about a tool; a profiled record in
> `data/resources/` is.

`aokg profile` does the reading. It is the tooling counterpart of `aokg grow`:
growth admits a paper the corpus already cites, this reads a tool the mirror
already lists.

```sh
aokg profile --propose-only        # what is waiting, in the order it would be read
aokg profile --dry-run             # read and profile, write nothing
aokg profile --budget 3            # write three
aokg profile --only LangGraph      # one tool by name
```

## What a profile has to contain

Two answers and an admission. A draft missing any of them is refused rather
than written:

| Field | What it has to say |
|---|---|
| `agent_model` | What authority the tool hands a machine — what it can act on, spend, send, change, or decide |
| `human_controls` | What constrains that, and **whether it is the product or a setting somebody has to turn on** |
| *what is undocumented* | Written into `source_provenance`. Usually the most useful part of the record |

Every claim names the document it came from, in `sources[].supports`. A profile
where nothing traces to a fetched page is refused: it would look exactly like
one that does.

## What it refuses

Refusing is the common outcome and not a failure.

- **No key.** Profiling writes nothing without `ANTHROPIC_API_KEY`. The
  fallback for an unread document is an empty queue, not the upstream blurb
  with our name on it.
- **No readable documentation.** A tool whose README will not load is a tool
  this cannot profile.
- **A README that is a feature list.** The model is asked to set `confident`
  to false when the documents do not say what agents may do or what stops
  them. LangGraph was refused on its README alone, correctly — the answer is
  on its documentation site, and the profiler now follows the link.
- **A field no document supports.** Every tri-state field has an `unknown`
  value and `unknown` is never written out, because a field saying nothing
  reads as though somebody looked.

## What it deliberately does not do

**It does not file.** `taxonomy_topics` comes out empty. Filing moved to stage
7 and derives from what a record's statements say — see
[pipeline.md](pipeline.md) — and a profiler guessing at codes would add to the
28 records that carry none and the two thirds that carry more than one.

**It does not trust the shortlist.** `tooling.candidates` matches an authority
word in upstream's one-line summary. That is a good way to decide what to read
first and a poor way to decide what is worth reading at all: a keyword ranks,
it does not decide what exists. The queue is every unprofiled entry, shortlist
first. The shortlist being empty once meant fifty-two tools were invisible.

## Why it opens a pull request

`grow.yml` commits a paper straight to `main` on a blast-radius argument: a new
record changes no existing judgment, lands `unreviewed` like everything else,
and `git revert` undoes it completely.

That argument does not transfer. A profile asserts what somebody else's
software does and does not let agents do, under our name. A wrong paper record
is a row in our own pile; a wrong profile is a claim about a third party.
Claims about other people's software get a human.

Merging the pull request is not review. It is agreeing the profile is worth
reviewing — the record still lands `unreviewed`, like everything else.

## Reviewing one

In the order it is worth checking:

1. Does `human_controls` describe a mechanism that exists, or one the
   documentation implies? The second is the failure mode, and it is the one
   worth catching, because an oversight feature a tool *almost* has is exactly
   what somebody would rely on.
2. Does each `sources[].supports` entry actually back the fields it claims?
   Open the page.
3. Is anything asserted that no cited document says?

## Running it unattended

[`.github/workflows/profile.yml`](../.github/workflows/profile.yml) runs on
Wednesdays, after Monday's tooling sync and Tuesday's growth, with a budget of
three. The key lives on the `scope-scan` environment, which only admits `main`
— the same arrangement as the scope scan, for the same reason.

The budget is small on purpose. Fifty profiles landing at once is fifty claims
nobody checked.

## Saying so in Slack

The run posts what it profiled, what each tool's documentation does not say,
and what it refused, to `#knowledge-graph`.

It uses **its own Slack app**, not the internal task agent's. The small reason
is that this repository is public and that agent's token reads private channels
and writes to a CRM base. The real reason is that a bot's name is how a reader
decides what kind of claim they are reading: "Task Digest says three tools were
profiled" invites you to read it as something to action, and this is a
different process making a different claim about a public artifact.

Setting the app up is much smaller than the task agent's was, because nothing
comes back. No request URL, no signing secret, no relay, no event
subscriptions — it posts and stops.

1. Create a Slack app, name it for what it does (*AO Knowledge Graph*).
2. **OAuth & Permissions → Bot Token Scopes:** `chat:write`. That is the whole
   list.
3. Install to the workspace, copy the bot token (`xoxb-…`).
4. Invite it: `/invite @AO Knowledge Graph` in `#knowledge-graph`.
5. Add the token as the `SLACK_BOT_TOKEN` secret on the `scope-scan`
   environment, beside `ANTHROPIC_API_KEY`. Optionally set a `SLACK_CHANNEL`
   variable to post somewhere else.

Without the token the step prints the message it would have sent and the run
carries on. A missing credential is a quiet run, never a failed one — and
never a silent one, because a week of silence is indistinguishable from a
workflow that stopped running. That is also why it posts on a week when
nothing was profiled.
