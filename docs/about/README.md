# The reader documentation

One file per section of what a reader meets first: what the corpus is, what it
is for, how it is put together. Rendered on graph.aocommons.com/docs, and
readable here on GitHub without any rendering step at all.

This is not the contributor documentation — that is `docs/*.md` one level up,
and it is longer, more specific, and written for somebody changing the corpus
rather than meeting it.

**Numbers are placeholders, never literals.** `{{claims}}` is filled from
the corpus at render time. A number typed in here would be wrong within a week
and nobody would notice, which is exactly what happened to the copy this
replaces: it lost its interpolations in an extraction and read "Today that is
of — the honest state of the library" for weeks.

Available: `{{records}}` `{{claims}}` `{{read}}` `{{topics}}`
`{{reviewed}}` `{{machineChecked}}` `{{primary}}` `{{questions}}`, and per
claim kind `{{kind.evidence}}` `{{kind.position}}` `{{kind.protocol}}`
`{{kind.definition}}` `{{kind.background}}` `{{kind.gap}}`
`{{kind.limitation}}`.

Front matter sets `id` (the anchor), `title` and `order`. Tables,
lists and emphasis render; anything fancier does not, on purpose.

A section had a `kicker` above its title until 2026-10-26 — "six decisions,
and what each one costs". Two titles where one was needed: the reader met an
explanation before they knew what it explained, and the nav showed one and
the page the other.

## Writing one

Short sentences. A reason is worth a clause, not a paragraph, and the reasons
worth a paragraph are rare enough to notice. Where a shape explains faster
than prose — a pipeline, a set of gates, a projection — draw it in a fenced
block: monospace renders on this page and on GitHub, so one drawing serves
both and neither can drift.

## Naming a section

A title is read in four places and only one of them has any context: the nav
here, a search result, an agent's retrieval snippet, and a link somebody
pasted. Titles like "How anything gets in" and "What has changed" work in the
first and fail in the other three, because they withhold the subject and put
the distinctive word last or nowhere.

1. **Lead with the subject noun.** The first two words should answer "what is
   this about?", because that is all a nav row and a snippet show.
2. **Use the word somebody would type.** *Admission*, *Review*, *Changelog*,
   *Roadmap*. The conventional term beats the clever one, for people and for
   retrieval alike.
3. **One subject per section, and the title is that subject.** A title that
   needs an "and" is usually two sections.
4. **Say it in the first sentence, not above the title.** The opening line
   of a section is where a sentence can be a sentence, and a reader meets it
   after they know what it is about rather than before.

`id` is the anchor and part of every link anybody has shared, so renaming a
title does not rename its `id`. They diverge, and that is the right trade.
