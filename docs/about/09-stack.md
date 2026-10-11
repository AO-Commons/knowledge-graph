---
id: stack
title: What it runs on
kicker: no server, no database
order: 9
---

The whole thing is files in a public git repository and a static page. That is
a deliberate constraint: it makes every change reviewable as a diff, every
release reproducible, and the corpus outlive whoever is maintaining it.

| Layer | What | Why this |
| --- | --- | --- |
| Storage | YAML and JSONL in git | a diff is the review surface; no database to outlive |
| Library | Python 3.11+, PyYAML the only hard dependency | installable anywhere, few moving parts |
| Identity and citations | OpenAlex | the backbone: ids, citation counts, institutions |
| Preprint text | Semantic Scholar | abstracts and references OpenAlex does not carry for preprints |
| Bylines | arXiv | the submission itself, not an index's guess |
| Judgment | Claude — scope scans, extraction, tagging drafts | marked unconfirmed, never readable as a person's judgment |
| Automation | GitHub Actions | intake, growth, filings-to-pull-requests, deploys |
| Agents | a read-only MCP server | so an assistant can query the corpus directly |

The page you are reading was generated from the corpus it describes, so its
numbers cannot disagree with it.
