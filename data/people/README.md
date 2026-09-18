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
link_status: verified      # or `claimed`
verified_by: ankeliu       # who confirmed it, and how
verified_how: >-
  …
```

`claimed` means the link is plausible and nobody has checked it — a matching
name is not a verification. `verified` means a named maintainer confirmed it
and wrote down how. Only a `verified` link makes a verdict count as an
author's.

An author's verdict is not worth more than anyone else's. It is worth
something *different*: an author is the highest authority on whether a
statement says what their paper says, and the least disinterested party on
whether it overstates. Recording the link lets a reader weigh that for
themselves, which is the whole reason it is written down rather than assumed.
