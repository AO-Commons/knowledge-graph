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
