# The reader documentation

One file per section of what a reader meets first: what the corpus is, what it
is for, how it is put together. Rendered on graph.aocommons.com/docs, and
readable here on GitHub without any rendering step at all.

This is not the contributor documentation — that is `docs/*.md` one level up,
and it is longer, more specific, and written for somebody changing the corpus
rather than meeting it.

**Numbers are placeholders, never literals.** `{{statements}}` is filled from
the corpus at render time. A number typed in here would be wrong within a week
and nobody would notice, which is exactly what happened to the copy this
replaces: it lost its interpolations in an extraction and read "Today that is
of — the honest state of the library" for weeks.

Available: `{{records}}` `{{statements}}` `{{read}}` `{{topics}}`
`{{reviewed}}` `{{machineChecked}}` `{{primary}}` `{{questions}}`, and per
statement kind `{{kind.finding}}` `{{kind.position}}` `{{kind.method}}`
`{{kind.definition}}` `{{kind.background}}` `{{kind.gap}}`
`{{kind.limitation}}`.

Front matter sets `id` (the anchor), `title`, `kicker` and `order`. Tables,
lists and emphasis render; anything fancier does not, on purpose.
