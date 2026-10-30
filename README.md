# AO Commons — Knowledge Graph

A maintained map of research on **autonomous organizations**: organizations in
which machine agents hold operational or decision authority.

**[Browse it →](https://ao-commons.github.io/knowledge-graph/)**

The unit is not the paper. It is the **claim** — one thing a paper asserts,
stored with the exact sentence it came from, what kind of claim it is, and
whose result it is. That is what lets you check a claim rather than trust it.

| | |
|---|---|
| Records | 363 |
| Papers read down to claims | 27 |
| Claims | 349, of which 43 checked by a person against the paper |
| Open questions | 13, clustered from the gaps papers name themselves |
| Topics | 103, in 16 sections |

Early, and the binding constraint is reading rather than collecting.

## What you can do

**Browse and search** on the site above. Every claim shows the sentence it was
drawn from, so you can disagree without opening the PDF.

**Suggest something** — a paper, tool, deployment, organization, person or
article. [One form](https://github.com/AO-Commons/knowledge-graph/issues/new?template=suggest-addition.yml).
A bot judges it against the scope test, and if it passes, resolves the metadata
and files the record within a minute. If it does not, you get the reasoning
rather than a closed issue.

**Correct something.** [The other form](https://github.com/AO-Commons/knowledge-graph/issues/new?template=request-adjustment.yml).
Corrections are the most useful thing anyone sends: nothing here has been
checked by more than one person and most of it has not been checked by one.

**Query it from an agent.** A read-only MCP server ships with the repository.

```bash
python3 -m pip install -e '.[mcp]'
claude mcp add ao-commons -- aokg-mcp
```

## The scope test

> An item belongs if it would change how you design, operate, oversee, or hold
> accountable an organization where agents act with real authority.

Work about human collective decision-making that would be the same without
machines does not belong, however good it is. That boundary is what keeps the
library small enough to be worth querying, and the
[exclusion register](taxonomy/agentic-org-research-library-taxonomy-v3.md)
names what it has turned away — including three exclusions we already think
are arguable.

Adjacent literature the field borrows its vocabulary from — Coase, Williamson,
Aghion and Tirole — is held at section 15 as background the library points at
rather than reads.

## What a record carries

Claims, each with its quote, its kind (shown, argued, defined, bounded or left
open) and whose result it is. Authors and the organizations they were at.
Topics, derived from the concepts on its claims rather than assigned by hand.
The open questions it bears on.

Every release is deterministic and checksummed, and also ships as a
[MIRA](https://github.com/MIRA-science/schema) graph — an open schema for
research graphs — so the corpus is readable by anything that already speaks it.

## For authors

If your work is here, the library holds itself to this:

- **Your words are quoted, not replaced.** Every claim carries the sentence it
  was drawn from.
- **Your hedges travel.** A "may" stays a "may", and a limitation you put on a
  result stays beside it.
- **What you showed and what you argued stay apart.**
- **Credit goes where it belongs.** A result you report from somebody else is
  credited to them, not to you.
- **You can correct it**, and an author's verdict is recorded as an author's.

Where it falls short of that, it is a defect to fix. Use the correction form.

## Running it

```bash
python3 -m pip install -e ".[scholarly]"
aokg taxonomy --stats          # what loaded, per section
aokg resolve                   # metadata and reference lists from OpenAlex
aokg grow --propose-only       # what the citation graph suggests admitting
aokg build --version v0.12.0   # a portable, checksummed release
pytest
```

## Layout

| Path | Contents |
|---|---|
| [taxonomy/](taxonomy/) | The v3 source file, aliases, cross-links, proposals |
| [data/resources/](data/resources/) | One file per record |
| [data/claims/](data/claims/) | What each paper asserts, with its source sentence |
| [data/questions.yml](data/questions.yml) | Open questions and the gaps that ask them |
| [data/claim-relations.yml](data/claim-relations.yml) | How claims support, qualify, extend or disagree |
| [data/organizations/](data/organizations/) · [data/people/](data/people/) | The ecosystem layer |
| [data/releases/](data/releases/) | Published releases |
| [src/ao_commons_kg/](src/ao_commons_kg/) | Models, parser, exports, MCP server |
| [docs/](docs/) | How the pipeline works, and why it is shaped this way |
| [site/](site/) | The preview page, built by `scripts/build_site.py` |

## How it is built

[docs/pipeline.md](docs/pipeline.md) walks the nine stages with measured
coverage at each, and says what runs unattended and what waits for a person.
The short version: everything up to filing runs on its own, and the reading and
the reviewing are where people are needed.

Two rules that do not bend. **Every edge says where it came from** — a citation
and a model's guess are different claims and must never look alike. **Machines
admit, people judge** — nothing a model drafted is readable as a person's
decision.

## Contributing

[CONTRIBUTING.md](CONTRIBUTING.md). Corrections first, missing research second.

## License

Content and data [CC BY 4.0](LICENSE); code in `src/` additionally MIT.
