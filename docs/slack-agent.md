# The Slack agent

Tag it in `#knowledge-graph` and it answers from the graph, or files what you
give it.

```
@AO Knowledge Graph what do we hold on humans approving what an agent spends?
```

> *Nothing in the library evaluates whether human spend approval works.* The
> branch exists — `8.1` Autonomous treasury and capital operations — but it
> holds 4 records and none is a study of an approval gate's effect…
>
> Counter-pressure worth reading before you cite approval as a control:
> `resource:arxiv:2608.23642` argues current designs "do not support effective
> human oversight — they contribute to its degradation."
>
> 0 of 141 records reviewed by a person, and these have 0 claims extracted.

It reads the graph through `queries.py` — the same tools the MCP server
exposes, so an answer here and an answer in Claude Desktop come from one place.
It cannot reach the internet, and it is told that a paper it knows from training
which the graph does not hold is a gap in the graph, not a fact to state.

## The two things it does

**Answer.** Anything that is not the second thing.

**File.** A message carrying an identifier *and* asking for it —
`add 2502.14143 — agents approving each other's spend` — opens a
`new-resource` issue, which is the door the site's Add tab already uses.
`new-resource.yml` resolves it and writes the record.

Which of the two happens is decided **before any model runs**, by a regex.
`arxiv.org/abs/2502.14143 is the one Rakshit mentioned` is a question; a link
plus "add" is a filing. *Machines admit, humans judge* stops meaning anything
if a model can decide it was asked — the person's sentence is the judgment, and
this only carries it.

Your words become the issue's *why*. If you gave no reason it says so rather
than inventing one, because an invented rationale is exactly what the scope
test cannot catch.

## Setting up the Slack app

This one listens, so it needs more than the profiler's notifier. The Request
URL has to answer Slack's challenge before the app can be saved, so the relay
goes first.

### 1. Deploy the relay

```sh
cd relay
npx wrangler login              # once, opens a browser
npx wrangler deploy             # prints the URL you need below
```

Then its two secrets. `wrangler secret put` prompts for the value; it is not
echoed, not written to disk, and never goes in `wrangler.toml`:

```sh
npx wrangler secret put SLACK_SIGNING_SECRET
npx wrangler secret put GITHUB_TOKEN
```

- **`SLACK_SIGNING_SECRET`** — Slack app → *Basic Information* → *App
  Credentials* → *Signing Secret*. You will not have this until step 2 creates
  the app, so do step 2 up to the token, then come back.
- **`GITHUB_TOKEN`** — a fine-grained PAT, this repository only, **Contents:
  read and write**. Contents is what `repository_dispatch` needs. It is not
  what opens the issue — the workflow does that with the token Actions provides.

A second Worker rather than another route on `aoyeah-digest-relay`, because a
Worker verifies against exactly one signing secret and these are two apps.

### 2. Create the Slack app

api.slack.com/apps → *From scratch* → name it *AO Knowledge Graph*.

**OAuth & Permissions → Bot Token Scopes:**

| Scope | Why |
|---|---|
| `app_mentions:read` | receive the tag |
| `channels:history` | read the thread it was tagged in, in a **public** channel |
| `groups:history` | the same, in a **private** one — `#agent-test` is private |
| `chat:write` | reply |
| `reactions:write` | 👀 on your message the moment the run picks it up |

Slack splits channel history by channel type, and the mention arrives either
way: `app_mention` fires, the relay dispatches, and the run then fails on
`conversations.replies: missing_scope` because it cannot read the thread it was
invited to. Add both and the app works wherever you invite it.

**Event Subscriptions** → on. Request URL: the Worker URL from step 1. It must
go green immediately; if it says *"didn't respond with the value of the
challenge parameter"*, `SLACK_SIGNING_SECRET` is wrong or unset — the Worker
rejects with 401 before it ever reaches the challenge. Subscribe to bot events:
**`app_mention`**, and nothing else.

**Interactivity**: leave off. Nothing is approved in Slack; the issue is the
approval.

Install to the workspace, copy the `xoxb-` token, `/invite` it to
`#knowledge-graph`.

A run takes most of a minute, and a message that looks ignored for a minute
reads as broken. So the first thing a run does is react 👀 — before reading the
thread, before any model call. It claims only that the mention arrived; the
reply claims the rest.

### 3. The repository side

On the `scope-scan` environment, beside `ANTHROPIC_API_KEY`:

- `SLACK_BOT_TOKEN` — the `xoxb-` token from step 2.

That is the whole repository side. `mention.yml` opens issues with the
`GITHUB_TOKEN` Actions provides.

## When it goes wrong

A question that gets no answer is worse than a slow one, so a failed run posts
into the thread you asked in with a link to the run. The usual causes:

| What you see | What it is |
|---|---|
| Nothing at all | The relay did not fire. `npx wrangler tail` while you tag it — no line means Slack is not delivering, so check the Request URL and that `app_mention` is subscribed |
| `dispatch failed: 403` in the tail | The PAT lacks Contents: write, or `GITHUB_REPO` in `wrangler.toml` is wrong |
| The agent answers a mention in another channel | `CHANNELS` in `wrangler.toml` lists channel ids. Add it there and redeploy |
| It answers twice | Two runs raced. The workflow serializes per thread; check `concurrency` |

The relay is scoped to channel ids in `wrangler.toml`. That is the setting that
silently stopped the *other* relay working when its digest moved channel, so
when you invite this app somewhere new, add the id there and redeploy.

## What it deliberately cannot do

It does not search the web. `CLAUDE.md` puts a general research agent on the
do-not-build list for V1, and the reason 87 curated records beat 8,500 is scope
discipline. Autonomous addition already exists and is bounded:
`aokg grow` walks the corpus's own citations behind a rising threshold and a
scope scan. Widening beyond that is a decision to make on purpose.

It does not recommend tools, and it does not present anything as reviewed,
because nothing is.
