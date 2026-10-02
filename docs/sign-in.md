# Signing in

Not switched on. The Worker is written, the site works without it, and turning
it on needs two things only a maintainer can do.

## Why it needs a server at all

The site is static and served from GitHub Pages — `pages.yml` says, correctly,
that it "needs no server". OAuth needs a client secret, and a secret cannot
live in a page, so `auth/worker.js` sits beside the site and holds the one
thing the browser must never see. It is a sibling of `relay/worker.js` and a
separate Worker for the reason given there: a Worker should answer to exactly
one set of credentials.

**Most of what sign-in is for does not need it.** The contribution log is
committed and public, so the People view already shows who built what and
traces any statement back through everyone it rests on, for everybody, signed
in or not. Sign-in adds *this is me* — your own acts marked as yours — and, in
time, the ability to act as yourself.

## Turning it on

1. Register a GitHub OAuth App. Callback URL is the Worker's `/callback`.
2. `wrangler secret put GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, and
   `SESSION_SECRET` (any long random string).
3. Set `SITE_ORIGIN` in `auth/wrangler.toml` to the Pages origin, and deploy.

Step 1 cannot be automated and is the only manual part.

## What a session is, and is not

A session says which GitHub account is present. It carries the **numeric
account id**, not the login: GitHub lets an account rename and then releases
the old handle for anybody to claim, so a session keyed on the handle would
hand a departed contributor's history to whoever registers it next. The handle
rides along for display.

The access token is **not kept**. The read path does not need it, and a token
at rest is a liability with no current use. The flow asks for no scope at all,
so even a leaked token could not write.

**Signing in confers nothing.** Whether an account's judgment counts as an
author's is decided by the attestation ladder in `data/people/`, offline, by a
person who wrote down how they checked. A session that could set `by_author`
would make that ladder decorative. Sign-in must never become a second route to
a rung nobody earned.

## The write path, and the question it turns on

Filing a resource or a verdict from the site means writing to the corpus. Two
ways, and they pull against each other:

**(a) The signed-in person's own token.** The pull request is genuinely theirs,
which is the whole point of the contribution layer. Needs `public_repo` scope
and a user token held for the length of a session — a real liability.

**(b) A bot token, recording who asked.** No user token at rest. But git
history then says a bot did something a person decided, and this corpus has a
worked example of why that is bad: nine claim relations carried
`asserted_by: ankeliu` when a model had drafted them, and correcting that was
the point of the confidence class.

(a) is right for attribution, (b) is right for security, and the choice belongs
to whoever accepts the risk. It is not made in the code.

Either way, two things hold. A filing lands as a pull request and never as a
direct commit — `merge_filing.py` and the review path both assume it. And an
act performed through the site is recorded in `data/contributions.json` like
any other, against whoever performed it.

## Trusted reviewers

The open question worth settling alongside the write path is what a trusted
reviewer is. The ladder already has the shape: `claimed`, `vouched`,
`verified`, with `verified` deliberately empty because nothing can yet produce
a proof a stranger could re-check. A sign-in that proves control of a GitHub
account proves exactly that and no more — it is evidence for a vouch, not a
substitute for one.
