# Reading things that were never papers

A lab write-up, a research blog post, an open proceedings page. These carry
findings that often appear there first and nowhere else for a year, and until
now the pipeline could not see them — not refused on scope, just invisible.

## What was actually blocking it

Two things, and neither was the intake refusing the link.

`identify()` already accepted a bare URL. It routed everything to
`thing_record()`, which is built for **tools and platforms** and asks what the
thing does, how agents participate and what oversight it ships. Those questions
make no sense about an essay, so a research post either failed or got described
as if it were software.

Then separately, `fulltext.py` read `arxiv.org/html/<id>` and nothing else. So
even once admitted, a page produced no statements — and statements are the
corpus's unit now.

## What a page does not come with

Papers gave us three things for free. Each one is handled rather than assumed.

**The source can change or vanish.** An arXiv id resolves to the same bytes
forever; a blog post does not. The whole extraction method rests on a quote
that can be checked against its source, so reading a page also writes a
snapshot — the extracted text, the retrieval date, and the SHA-256 of the HTML
it came from. The snapshot is **committed, not cached**: `data/cache/` is
ignored by git, and an archive that disappears when somebody clears a directory
is not an archive. Everything after the fetch reads the snapshot, so a quote
stays checkable after the page is gone or rewritten.

**There is no structure to trust.** LaTeXML marks its sections; a web page
marks whatever its theme felt like. Headings are found generically, chrome is
removed by name, and a run of text under a heading like "Cookie notice" or
"Related posts" is dropped — a cookie banner reads as prose and would otherwise
be extracted from. Anything under about 220 characters is a caption or a
byline, not a section.

**There is no scholarly identity.** No DOI, no OpenAlex record, so no
references out and no way to be cited in. **A record read this way can never be
admitted by citation expansion and can never help admit anything else.** It is
a leaf, permanently. Under "machines admit, humans judge" that means every such
record spends a human judgment that a paper might not have — which is the real
cost, not the code.

## Prefer the paper, and the intake says so

Because of that last point, a page naming a companion paper hands over to it:

```
the page names a companion paper (2604.10290); prefer that record if it
covers the same work, because it carries references and citations and
this does not
```

This fired on the first real link tried. The post was *AI Organizations Can Be
More Effective but Less Aligned than Individual Agents*; it names its arXiv
preprint; that record went in instead and arrived with **45 references stored,
joining the citation graph**. The blog record would have joined nothing.

So the honest guidance is: paste the link either way, and let the intake find
the paper if there is one. The web path is for work that genuinely has no
paper behind it.

## How a link is routed

Decided on what the contributor filled in and where the link points, never on
reading the page — a tool's landing page is prose too, and a heuristic over its
wording would misfile the awkward cases silently.

| signal | routed as |
|---|---|
| `github.com`, `gitlab.com`, `huggingface.co` | tool |
| the tool form answered (how agents participate, oversight, maintainer, license) | tool |
| a DOI or arXiv id | paper |
| anything else that parses as an article | written work |
| anything else that does not | refused, with the tool fields suggested |

A page that cannot be read is refused rather than filed empty. The reader does
not run JavaScript, so a site that renders its content client-side will fail
here, and saying so is better than storing a record with no text.

## Using it

```python
from ao_commons_kg import article

piece = article.read("https://lab.example/post")   # fetch, parse, hash
article.save(piece, "resource:web:a-post")          # commit the snapshot
article.sections_for("resource:web:a-post")         # read it back, no network
```

`article.parse` returns the same `Section` objects `fulltext.parse` does, so
gap hunting, verbatim checking and extraction work on a blog post exactly as
they work on a paper. Borrowing the type rather than inventing a parallel one
is what keeps that true.
