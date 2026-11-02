# Contributing to the AO Commons Knowledge Graph

The AO Commons Knowledge Graph is an open project to map research on autonomous organizations (AOs) and multi-agent systems, with a focus on how these systems are organized, governed, evaluated, and kept safe.

We're looking for contributions from researchers, authors, developers, and practitioners working in this field. You don't need to write code to contribute.

## Current status: Preview

The Knowledge Graph is in early preview. We're gradually adding research, improving the taxonomy, and testing how papers, authors, organizations, and research questions connect.

**It's not yet ready to be relied on as a research or discovery tool.** Coverage is incomplete, most records haven't been reviewed by a person, and some features are still in development.

For now, we're particularly interested in expanding and reviewing the research collection. We'll roll out additional functionality as the data and underlying tools improve.

## How you can contribute

### 1. Submit relevant research

**If you've authored research on autonomous organizations or multi-agent systems, we'd especially like to hear from you.**

We're looking for papers, preprints, technical reports, benchmarks, evaluations, and documented experiments covering topics such as:

- Multi-agent coordination, cooperation, and organizational behavior
- Delegation, authority, governance, and human oversight
- Multi-agent safety, security, alignment, and failure modes
- Autonomous organizations and real-world agent deployments
- Organizational design, incentives, and institutional mechanisms for AI systems

You can submit your own work or recommend relevant research by others. Tools, deployments, organizations, and articles are welcome too.

The test for what belongs: would it change how you design, operate, oversee, or hold accountable an organization where AI agents act with real authority? Work on human decision-making that would be the same without AI agents is out of scope.

[Suggest research with the suggestion form](https://github.com/AO-Commons/knowledge-graph/issues/new?template=suggest-addition.yml).

The form asks for a link, DOI, or arXiv ID and a short explanation of why it's relevant. We fill in the title, authors, and other details from the link. Links to associated code, datasets, or evaluations are helpful where available.

### 2. Help improve the research collection

If you're familiar with the field, you can help by:

- Suggesting important papers or research areas we're missing
- Correcting metadata, citations, or author information
- Flagging papers that have been incorrectly classified
- Suggesting changes to the research taxonomy
- Identifying useful connections between papers, methods, and open research questions

For corrections, [use the correction form](https://github.com/AO-Commons/knowledge-graph/issues/new?template=request-adjustment.yml) and include the relevant source. If you wrote the work in question, say so on the form. For taxonomy changes, [use the taxonomy form](https://github.com/AO-Commons/knowledge-graph/issues/new?template=taxonomy.yml).

### 3. Contribute to the code

Developers are welcome to help improve the data pipelines, classification methods, graph infrastructure, evaluations, and interfaces.

```bash
pip install -e ".[dev]"
pytest
```

Check the repository's [open issues](https://github.com/AO-Commons/knowledge-graph/issues) for current work. For larger changes, please open an issue to discuss your approach before submitting a pull request.

## What happens to contributions?

A bot checks each suggestion against the scope test above, usually within a minute. If it's in scope, the bot fills in the details and adds it to the collection marked as unreviewed. If it isn't, the bot posts its reasoning on the issue, and you can reply to dispute it.

Corrections and taxonomy changes are reviewed by a person. Inclusion in the collection doesn't mean AO Commons has independently verified a paper's findings.

We're developing this project openly and expect both the research collection and the tools around it to evolve.

For more about AO Commons and our research, visit [aocommons.org](https://aocommons.org).

## Terms

Contributions to the research collection are licensed [CC BY 4.0](LICENSE); contributions to the code are licensed [MIT](LICENSE-CODE). By contributing, you confirm you have the right to license your contribution that way.

Please don't include personal information about third parties. Participation is governed by our [Code of Conduct](CODE_OF_CONDUCT.md).
