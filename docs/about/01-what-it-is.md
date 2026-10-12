---
id: what
title: The corpus
kicker: what it is, in one paragraph
order: 1
---

A curated, versioned, machine-readable record of what has been shown and what
has been argued about organizations run partly by machines. The unit is the
**statement**: one assertion, carrying the sentence from the paper it was read
out of, the kind of claim it is, whose result it is, and tags specific enough
to be worth joining on. Papers are containers for those. Currently
{{statements}} statements read out of {{read}} papers, inside a corpus of
{{records}} records.

Everything is a file in a public git repository. There is no database and no
account: the corpus can be read, diffed, forked, cited at a fixed version, and
queried by an assistant through a read-only MCP server. Every statement
carries its quote, so anything it says can be checked against the source
without re-reading the paper.
