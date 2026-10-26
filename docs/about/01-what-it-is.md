---
id: what
title: The corpus
order: 1
---

A library for people building and studying **autonomous organizations**:
those in which machine agents hold operational or decision authority.

It holds {{records}} records. Most are research: preprints, peer-reviewed
papers, technical reports and articles. The rest are what that research is
about — the tools people build, the suites those tools are measured against,
and the deployments running them. They are records too, so a claim can
point at one.

**The unit is not the paper. It is the claim.** One thing a paper
asserts, stored with the exact sentence it came from, what kind of claim it
is, whose result it is, and tags specific enough to join on. There are
{{claims}} claims so far, read out of {{read}} of those records.

That is what lets you check a claim rather than trust it. Every claim
carries its quote, so what the paper said sits beside what we say it said.
You can disagree with us without opening the PDF.

Everything is a file in a public git repository. There is no database and no
account: it can be read, diffed, forked, cited at a fixed version, and queried
by an assistant through a read-only MCP server. A release is checksummed and
keeps its mistakes, so a citation to one means the same thing next year.

Every release also ships in [MIRA](https://github.com/MIRA-science/schema), an
open schema for research graphs.
