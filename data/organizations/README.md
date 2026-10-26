# Organizations

One file per organization, as for people and resources. Adding one is writing
a file, and the pull request shows exactly what was asserted.

```yaml
id: org:framework-zero
name: Framework Zero
kind: company                     # what it is — exactly one
roles: [research, infrastructure] # what it does here — any number, or none
aliases: [FrameworkZero]          # other spellings the corpus may carry
city: Melbourne
country: Australia
ror: https://ror.org/...          # the identifier everyone else joins on
website: https://frameworkzero.com
source_provenance: added by hand, 2026-10-26
```

Only `id`, `name` and `kind` are required. `id` is `org:` plus the slug of the
name, and the filename matches the slug.

## Two axes, and why

`kind` is what the organization **is**. `roles` are what it **does in this
ecosystem**. A research institute that also ships tooling is both, routinely,
and one field would force a choice that is wrong half the time and painful to
undo once edges point at it.

| `kind` | |
|---|---|
| `university` | degree-granting |
| `research-institute` | research, not degree-granting: a national lab, an institute |
| `frontier-lab` | builds frontier models; the field treats these as their own thing |
| `company` | any other commercial organization |
| `foundation` | non-profit: grant-making, stewarding, or both |
| `government` | an agency, ministry or public body |
| `standards-body` | exists to write specifications |
| `collective` | a DAO or autonomous organization: a subject of this corpus |

| `roles` | |
|---|---|
| `research` | publishes research in this field |
| `infrastructure` | builds the tooling agents run on |
| `deployment` | runs an autonomous organization |
| `standards` | writes specifications |
| `evaluation` | builds or runs benchmarks and evaluations |
| `funding` | grants money |
| `convening` | events, community, coordination |

**An empty `roles` is honest.** Most of these organizations have published a
paper this corpus holds and done nothing else here. `research` is left off
them on purpose: a role every organization has sorts nothing.

## Where the records came from

`scripts/seed_organizations.py` reads the affiliations already on records,
canonicalises them through `organizations.py`, and asks OpenAlex for `city`,
`country`, `ror` and `website` — those go stale and ROR is the identifier the
rest of the world uses, so neither is typed by hand. `kind` is guessed from
OpenAlex's own type, or from the name when OpenAlex cannot be reached, and is
meant to be corrected. `roles` is never guessed.

The seeder never overwrites a file that exists. The file holds the judgments,
and a seeder that clobbers them is one nobody can run twice.

```sh
python3 scripts/seed_organizations.py                  # say what it would write
python3 scripts/seed_organizations.py --write          # write the new ones
python3 scripts/seed_organizations.py --write --min 5  # only the well-cited
```

**OpenAlex rate-limits a shared IP.** 138 of the first 191 came back empty for
that reason, not because the organization is unknown; their `kind` was
inferred from the name instead and `source_provenance` says so. Re-running
later fills them in, and a free API key removes the limit.
