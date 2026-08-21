# Adding many resources at once

For an agent working through a reading list. If you have one or two papers,
the [**Add** tab on the site](https://ao-commons.github.io/knowledge-graph/) is
quicker — it resolves the paper, suggests topics and opens the issue for you.

This path is for twenty.

## What you are doing

Turning a list of identifiers into records in `data/resources/`, one YAML file
each, and opening a pull request with them.

You are **not** deciding whether a paper belongs, or where it is filed. Records
arrive `unreviewed` and get their topics confirmed by a person later. Adding
something that turns out to be out of scope costs a revert; asserting a
judgement nobody made costs more.

## Steps

```bash
git clone https://github.com/AO-Commons/knowledge-graph.git
cd knowledge-graph
python3 -m pip install -e '.[scholarly]'
git checkout -b add/<something-describing-the-batch>
```

Put the identifiers in a file, one per line. DOIs, arXiv ids, arXiv URLs, or a
link to a tool's site. Markdown bullets, numbered lists, comments beginning `#`
and trailing punctuation are all fine:

```
# from the multi-agent safety reading list
- https://arxiv.org/abs/2502.14143
- 10.1145/3770291.3770333
2511.03434
- https://arxiv.org/abs/2401.11880 [14.2, 5.2]
```

Square brackets at the end of a line are taxonomy codes, if you already know
where something belongs. Leave them off if you do not — a wrong code is worse
than no code, because it looks like a judgement someone made.

Then look before you write:

```bash
python3 scripts/bulk_add.py papers.txt            # says what it would do
python3 scripts/bulk_add.py papers.txt --write    # writes the records
```

Read the dry run. It reports four things: what it would add, what is already in
the library, what repeats inside your own file, and what it could not resolve.

```bash
python3 -m pytest -q                              # the records must load
git add data/resources && git commit -m "Add N resources on <topic>"
git push -u origin add/<branch> && gh pr create --fill
```

## Duplicates

Handled for you, and reported rather than passed over.

An identifier already in the library is **skipped and the original kept** —
including across forms, so `10.48550/arXiv.2502.14143` is recognised as the
same paper as `https://arxiv.org/abs/2502.14143`. A repeat inside your own file
keeps its first appearance, by the same rule.

If a record you expected is reported as already held, that is the right
outcome. Do not force it in under a second id.

## What gets resolved for you

Title, authors, abstract, date and identifiers, from OpenAlex, then Semantic
Scholar, then arXiv — arXiv last and decisive for preprints, because it is the
submission itself rather than an index over it, and index author records are
sometimes a different person with a similar name.

If none of the three has the paper, that identifier is reported as failed
rather than filed under a guess. Add it through the site's Add tab with a title.

## Being kind to the APIs

All three are free and unauthenticated. The script pauses a second between
lookups; leave that alone unless the batch is small. A few hundred identifiers
is fine overnight. A few thousand is not — split it, or ask first.

## What a good pull request looks like

- One batch, one branch, described in a sentence: where the list came from.
- Only `data/resources/` touched.
- The dry-run output pasted into the description, so a reviewer can see what
  was skipped and why.
- No topic codes you are not sure of.
