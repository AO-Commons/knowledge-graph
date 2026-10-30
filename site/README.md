# The preview page

One file, `index.html`, built by [`scripts/build_site.py`](../scripts/build_site.py)
and served from GitHub Pages at
[ao-commons.github.io/knowledge-graph](https://ao-commons.github.io/knowledge-graph/).

Four tabs — records, people, organizations, open questions — each searchable.
Two buttons, which open a GitHub issue with the fields filled in: suggest
something missing, or say something here is wrong. Nothing on the page writes
to the corpus.

It opens by saying it is a preview and incomplete, because it is: 363 records
of a field that has more, 27 of them read down to their claims. A reader who
assumes an absence is a judgment will draw the wrong conclusion from it.

## One bug worth remembering

The record sheet was opened by a function called `open`. A top-level
`function open` in a classic script *is* `window.open`, so every issue link
called the record opener with a URL, found no record with that id, and
returned — both buttons dead, nothing thrown, nothing in the console.
`tests/test_site_brand.py` now fails if the script defines any name that
shadows a `window` method.

## What it replaced

Until 2026-10-30 this was a nine-tab application of about 1.3 MB: Explore, Add,
Tools, Docs, a review screen, a classifier index, a force-directed graph, a
gold set and a contributions ledger. Most of it was built for whoever maintains
the corpus rather than whoever reads it, and it had grown faster than the 363
records it was describing.

Reviewing — judging a claim against its paper — moved to the signed-in
application, where an author can be invited to review claims about their own
work. Adding moved to an issue form with a scope judge in front of it. The
documentation is still in [`docs/about/`](../docs/about/) and is rendered by
that application.

## Style

AO Commons', with the tokens copied from `src/shared/tokens.css` in the website
repository rather than imported. A preview page should not stop rendering
because a sibling repository moved a file. `tests/test_site_brand.py` asserts
the palette still matches what is published there, so the copy cannot drift
quietly.

Light only, as the AO Commons tokens are. This page carried a dark theme of its
own until the rebuild, which was a second palette nobody had published.

## Building it

```bash
python3 scripts/build_site.py
```

Deterministic apart from the build date. The payload is the records, the claims
with their quotes, the topic titles, the open questions, and an index of
authors who appear on more than one record — about 500 KB, embedded rather than
fetched so the page is one file with nothing to 404.
