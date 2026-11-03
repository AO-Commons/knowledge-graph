# AO Commons Knowledge Graph

The AO Commons Knowledge Graph is an open project to map research on **autonomous organizations** (AOs): organizations in which AI agents hold operational or decision-making authority. It focuses on how these organizations are run, governed, evaluated, and kept safe.

**[Browse it](https://ao-commons.github.io/knowledge-graph/)**

## Current status: Preview

The Knowledge Graph is in early preview. We're gradually adding research, improving the taxonomy, and testing how papers, authors, organizations, and research questions connect.

**It's not yet ready to be relied on as a research or discovery tool.** Coverage is incomplete, a model drafts the claims, and most of them haven't been checked by a person.

<!-- stats:start -->
| | |
|---|---|
| Records | 399 papers, tools, deployments, benchmarks, and reports |
| Papers with claims | 27 |
| Claims | 349, of which 43 have been checked by a person against the paper |
| Open questions | 13, grouped from questions the papers say are unanswered |
| Topics | 103, in 16 sections |
<!-- stats:end -->

Collecting research is the easy part. Reading papers and checking claims is what limits how fast this grows.

## What's in it

Each **record** is a paper, tool, deployment, benchmark, or report, with its authors, their organizations, and its topics.

For papers that have been read, the record also lists the **claims** the paper makes. Each claim is stored with:

- the exact sentence it was taken from, so you can check it without opening the paper
- what kind of claim it is: evidence, an argument, a definition, a limitation, or an open question
- whose result it is, when the paper reports someone else's work

**Open questions** group the unanswered questions that different papers raise, so you can see where several papers point to the same gap.

## How to use it

**Browse and search** on the [preview site](https://ao-commons.github.io/knowledge-graph/).

**Query it from an AI agent.** The repository includes a read-only MCP server:

```bash
python3 -m pip install -e '.[mcp]'
claude mcp add ao-commons -- aokg-mcp
```

**Use the data directly.** Everything is a file in this repository. See [Layout](#layout).

## How to contribute

- **Suggest research** with the [suggestion form](https://github.com/AO-Commons/knowledge-graph/issues/new?template=suggest-addition.yml). Papers, tools, deployments, organizations, and articles are all welcome. A bot checks each suggestion against the scope test below, usually within a minute, and either adds it marked as unreviewed or explains on the issue why it doesn't fit.
- **Correct a record** with the [correction form](https://github.com/AO-Commons/knowledge-graph/issues/new?template=request-adjustment.yml). Corrections are especially useful right now, because most of the collection hasn't been checked by a person.
- **Improve the code.** See [CONTRIBUTING.md](CONTRIBUTING.md).

### What belongs

> Work belongs if it would change how you design, operate, oversee, or hold accountable an organization where AI agents act with real authority.

Work on human decision-making that would be the same without AI agents is out of scope. The [exclusion register](taxonomy/agentic-org-research-library-taxonomy-v3.md) lists what has been turned away and why, including three exclusions we think are arguable.

Some foundational work from economics and law, such as Coase, Williamson, and Aghion and Tirole, is kept as background in section 15 of the taxonomy. It's listed for reference but not read for claims.

## For authors

If your work is in the collection, this is what we aim for:

- **Your words are quoted, not replaced.** Every claim includes the sentence it was taken from.
- **Your hedges are kept.** A "may" stays a "may", and a limitation you put on a result stays beside it.
- **What you showed and what you argued are kept apart.**
- **Credit goes where it belongs.** A result you report from someone else is credited to them, not to you.
- **You can correct it.** Use the correction form and say you're an author. Your review is recorded as the author's.

If a record falls short of this, please tell us through the correction form.

## Running it

```bash
python3 -m pip install -e ".[scholarly]"
aokg taxonomy --stats          # what loaded, per section
aokg resolve                   # metadata and reference lists from OpenAlex
aokg grow --propose-only       # papers the citation graph suggests adding
aokg build --version v0.12.0   # a portable, checksummed release
pytest
```

Each release is deterministic and checksummed. It's also published as a [MIRA](https://github.com/MIRA-science/schema) graph, an open schema for research graphs, so any tool that reads MIRA can read it.

## Layout

| Path | Contents |
|---|---|
| [taxonomy/](taxonomy/) | The v3 taxonomy, aliases, cross-links, and proposals |
| [data/resources/](data/resources/) | One file per record |
| [data/claims/](data/claims/) | The claims each paper makes, with source sentences |
| [data/questions.yml](data/questions.yml) | Open questions and the claims that raise them |
| [data/claim-relations.yml](data/claim-relations.yml) | Where claims support, qualify, extend, or disagree with each other |
| [data/organizations/](data/organizations/) · [data/people/](data/people/) | Organizations and people |
| [data/releases/](data/releases/) | Published releases |
| [src/ao_commons_kg/](src/ao_commons_kg/) | Models, parser, exports, and MCP server |
| [docs/](docs/) | How the pipeline works, and why |
| [site/](site/) | The preview site, built by `scripts/build_site.py` |

## How it's built

[docs/pipeline.md](docs/pipeline.md) describes the nine stages, how much of the collection has passed each one, and which stages run automatically and which need a person. In short: finding, adding, and filing research runs automatically. Reading papers and reviewing claims need people.

Two rules apply throughout:

- **Every connection records where it came from.** A citation and a model's guess are kept distinct.
- **Models can add, but only people decide.** Nothing a model drafted is presented as a person's judgment.

## License and citing

The research collection (taxonomy, records, claims, and documentation) is licensed [CC BY 4.0](LICENSE). The code is licensed [MIT](LICENSE-CODE). [NOTICE.md](NOTICE.md) explains which applies where.

To cite it, use the **Cite this repository** button. Where you can, cite a specific release rather than the repository.

For more about AO Commons, visit [aocommons.org](https://aocommons.org).
