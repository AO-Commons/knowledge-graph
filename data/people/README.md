# Identity links

Who a filing came from, in the corpus's own terms.

A filing arrives as a GitHub login. A byline is a name. Nothing connects the
two, which is why the first twelve verdicts in this library — all filed by an
author on her own papers — carry no sign of it.

One file per person, and the only thing it asserts is the link:

```yaml
name: Helena Rong          # exactly as the byline spells it
github: helenarong2703
orcid: null
github_id: 217204813       # immutable — this is the key
attestation: vouched       # claimed | vouched | verified
attested_by: ankeliu       # who stood behind it, and how
attested_how: >-
  …
```

## A login is not a key

`github_id` is the number GitHub assigns an account once and never reuses.
`github` is the handle, which an account can change — and GitHub then releases
the old handle for anybody to claim. Anything that joins on the handle hands a
departed contributor's history, and their vouched status, to whoever registers
the name next. That is fine for attributing a filing, which a person checks
before it merges, and it is an account takeover in anything that signs people
in. The handle stays because it is how a filing arrives and how a person
recognizes themselves here.

Three rungs, not two.

`claimed` — the account asserts it and nobody has checked. A matching name is
not a verification.

`vouched` — a named maintainer confirmed it on their own word and wrote down
how. **This is what both links here actually are.** They said `verified` until
2026-10-01, which overclaimed: Anke confirming that an account belongs to a
paper's author is her word, not evidence a stranger can re-check.

`verified` — a proof exists that a third party could check without trusting the
maintainer. **Nothing has reached this rung and nothing will until there is a
protocol to produce one.** Leaving it visibly empty is what stops the weaker
claim standing in for the stronger one.

Either upper rung makes a verdict count as an author's. That test has always
meant "a named party stood behind this link", which is exactly what separates
`vouched` from `claimed`.

An author's verdict is not worth more than anyone else's. It is worth
something *different*: an author is the highest authority on whether a
statement says what their paper says, and the least disinterested party on
whether it overstates. Recording the link lets a reader weigh that for
themselves, which is the whole reason it is written down rather than assumed.
