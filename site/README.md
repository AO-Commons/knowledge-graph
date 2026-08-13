# site/

The filing site: a single self-contained page for tagging records against the
taxonomy, together, without anyone installing Python.

```sh
python3 scripts/build_site.py
open site/index.html
```

`template.html` is the source. `index.html` is generated — data inlined, so it
works from a `file://` URL, from Pages, or from anywhere it is dropped. No
server, no CORS, no build step for a contributor who only wants to help tag.

## Why suggestions are precomputed

The classifier is already written and tested in Python. Reimplementing BM25 in
JavaScript would be a second thing to keep correct, and the two would drift.
So `build_site.py` scores every record at build time and inlines the top
fourteen topics per record.

## Dividing the work

Nobody needs to review everything. Click a branch in the tree and the queue
narrows to records that branch plausibly covers, so two people can take
section 11 and section 2 and not collide. The search box finds a topic, an
author, or a paper by title.

There is no server behind this page, so there is no live lock on a record.
Coordination is social: agree who takes which sections, and the ledger shows
what has already been filed.

## The ledger

Everything filed appears at the bottom of the review screen, newest first —
what it was filed under, by whom, and when. Your own filings appear
immediately. Work that has been merged appears once a maintainer writes
 next to the page, which the site fetches same-origin on
load; off Pages that request 404s and the ledger simply shows your own.

## What a contributor does

Review a record, pick the topics that apply, file it. The tree on the left
lights the path to whatever they picked and the counts move — the point being
that filing visibly builds the thing, rather than feeling like data entry.

Decisions live in the contributor's own browser until they open Submit, copy
the YAML, and paste it into an issue. Nothing uploads on its own, and the page
says so.

A maintainer merges submissions into `evals/gold/tags.yml`, which is what every
classification figure is measured against.

## Publishing

`.github/workflows/pages.yml` deploys this on push. It is inert while the
repository is private — Pages needs a public repo on a free plan — and turns
on with no further change once visibility flips.
