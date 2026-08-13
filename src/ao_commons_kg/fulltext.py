"""Full text, split into the sections claims actually live in.

Extraction ran on abstracts until now, and the literature is blunt about the
cost: restricting extraction to abstracts "overlooks many key claims
distributed throughout the full text" (Echoes of Citations, AAAI 2026). An
abstract states conclusions and drops the evidence for them, which is exactly
the half a knowledge graph needs.

arXiv serves LaTeXML HTML at `arxiv.org/html/<id>` for the whole corpus we
hold, so this parses that rather than wrestling with PDFs. Records without an
arXiv id — a quarter of the corpus — get nothing here and fall back to the
abstract, which is a real limitation and is reported rather than hidden.

Parsed with the standard library. The package is deliberately thin, and a
LaTeXML document is regular enough that a dependency would buy little.
"""

from __future__ import annotations

import re
import urllib.request
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
CACHE = REPO / "data" / "cache" / "fulltext"
CONTACT = "anke@stellar.org"

# Where claims concentrate. Ordered by yield rather than by document order:
# a paper's own statement of what it showed sits in its conclusion and its
# results, while the introduction carries the contribution list and the
# related-work framing that a later section only alludes to.
CLAIM_BEARING = ("abstract", "introduction", "results", "discussion", "conclusion")

SECTION_KINDS = (
    ("abstract", ("abstract",)),
    ("introduction", ("introduction", "overview")),
    ("related", ("related work", "background", "prior work")),
    ("method", ("method", "approach", "model", "architecture", "design",
                "framework", "implementation", "setup")),
    ("results", ("result", "experiment", "evaluation", "finding", "analysis",
                 "benchmark", "study", "case stud")),
    ("discussion", ("discussion", "limitation", "threat", "implication")),
    ("conclusion", ("conclusion", "future work", "summary", "outlook")),
)


class FullTextError(RuntimeError):
    """Full text could not be had for this record."""


@dataclass
class Section:
    kind: str
    """One of SECTION_KINDS, or `other`. What the section is *for*, which is
    what decides how much a claim found in it is worth."""
    heading: str
    text: str

    @property
    def claim_bearing(self) -> bool:
        return self.kind in CLAIM_BEARING


def classify_heading(heading: str) -> str:
    """Map a heading onto a section kind.

    Matched on substrings because headings are written by authors, not by a
    schema: "5 Experiments and Results", "Evaluation setup", and "What we
    found" all mean the same thing to a reader looking for claims.
    """
    # Strip a leading section number, and only that. A character class of
    # roman numerals eats the "I" of "Introduction", which silently filed
    # every intro as `other` — the sort of bug that costs a section rather
    # than raising anything.
    plain = re.sub(r"^\s*(\d+(\.\d+)*|[IVX]+)[.)]?\s+", "", heading or "").strip().lower()
    for kind, needles in SECTION_KINDS:
        if any(needle in plain for needle in needles):
            return kind
    return "other"


# Chrome, and anything whose text would corrupt a quote. Removed by pattern
# before parsing rather than tracked during it: an earlier version walked a tag
# stack to decide what to skip, and on the first document with slightly
# unbalanced markup the stack drifted, the skip never lifted, and the parser
# returned zero sections for a paper that plainly had eight. Deleting the
# regions outright cannot drift.
STRIP = tuple(
    re.compile(rf"<{tag}\b.*?</{tag}>", re.S | re.I)
    for tag in ("script", "style", "svg", "nav", "header", "footer",
                "math", "figure", "table", "cite")
)
# The paper ends where its argument does. Everything past this point is
# references and proofs: real text, but not claims the paper is making.
ENDS_AT = re.compile(r'<(?:section|div)[^>]*class="[^"]*ltx_(?:bibliography|appendix)', re.I)

HEADING = re.compile(r'<h[1-6][^>]*class="[^"]*ltx_title[^"]*"[^>]*>(.*?)</h[1-6]>', re.S | re.I)
PARAGRAPH = re.compile(r'<p[^>]*class="[^"]*ltx_p[^"]*"[^>]*>(.*?)</p>', re.S | re.I)
TAG = re.compile(r"<[^>]+>")


def _plain(fragment: str) -> str:
    parser = HTMLParser(convert_charrefs=True)
    chunks: list[str] = []
    parser.handle_data = chunks.append  # type: ignore[method-assign]
    parser.feed(TAG.sub(" ", fragment))
    parser.close()
    text = re.sub(r"\s+", " ", "".join(chunks)).strip()
    # Removing <cite> leaves "A3C , V-MPO , and OPRE ." Harmless for matching,
    # since quotes are taken from this same text — but a reviewer is asked to
    # check a quote against the paper, and one littered with gaps where the
    # citations were reads as though we transcribed it badly.
    text = re.sub(r"\s+([,.;:)\]])", r"\1", text)
    text = re.sub(r"([(\[])\s+", r"\1", text)
    return re.sub(r"\(\s*\)|\[\s*\]", "", text).strip()


def parse(html: str) -> list[Section]:
    """Split a LaTeXML document into sections.

    Mathematics, figures and tables are dropped. A claim sentence with a
    rendered formula spliced through it cannot be matched back to the source
    verbatim, and a quote that will not match is worse than no quote — it is
    the one thing this whole design rests on.
    """
    for pattern in STRIP:
        html = pattern.sub(" ", html)
    if end := ENDS_AT.search(html):
        html = html[: end.start()]

    # Headings and paragraphs, interleaved in document order, so a paragraph
    # belongs to the heading above it.
    blocks: list[tuple[str, str]] = []
    for match in sorted(
        [*((m, "heading") for m in HEADING.finditer(html)),
         *((m, "text") for m in PARAGRAPH.finditer(html))],
        key=lambda pair: pair[0].start(),
    ):
        if text := _plain(match[0].group(1)):
            blocks.append((match[1], text))

    sections: list[Section] = []
    heading, paragraphs = "", []

    def close_section():
        if paragraphs:
            sections.append(Section(classify_heading(heading), heading or "—",
                                    "\n\n".join(paragraphs)))

    for kind, text in blocks:
        if kind == "heading":
            close_section()
            heading, paragraphs = text, []
        else:
            paragraphs.append(text)
    close_section()
    return sections


def fetch(arxiv_id: str, *, cache: Path = CACHE, refresh: bool = False) -> str:
    """The LaTeXML HTML for an arXiv id, cached on disk.

    Cached because a run over the corpus otherwise re-downloads tens of
    megabytes from arXiv every time an extraction prompt changes, which is
    rude to them and slow for us.
    """
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / f"{arxiv_id}.html"
    if path.exists() and not refresh:
        return path.read_text(encoding="utf-8")

    # No version suffix. `/html/2107.06857v1` is a different, often absent
    # document from `/html/2107.06857`, and asking for the wrong one is how
    # this first reported that no paper in the corpus had full text.
    url = f"https://arxiv.org/html/{arxiv_id}"
    request = urllib.request.Request(url, headers={"User-Agent": f"ao-commons-kg ({CONTACT})"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8", "ignore")
    except Exception as error:  # noqa: BLE001 — the reason varies, the answer does not
        raise FullTextError(f"{arxiv_id}: {type(error).__name__}: {error}") from error

    if "ltx_section" not in body and "ltx_abstract" not in body:
        raise FullTextError(
            f"{arxiv_id}: arXiv served a page with no LaTeXML body. Older "
            "submissions have no HTML rendering and only the PDF exists."
        )
    path.write_text(body, encoding="utf-8")
    return body


def sections_for(arxiv_id: str, **kwargs) -> list[Section]:
    return parse(fetch(arxiv_id, **kwargs))


def verbatim(quote: str, sections: list[Section]) -> str | None:
    """The section a quote appears in, or None if it appears in none.

    The load-bearing check of the whole claim layer. A quote that cannot be
    found in the source means the model reconstructed it from memory, and a
    reconstructed quote invites a reviewer to confirm something the paper
    never said.

    Whitespace is normalized on both sides because LaTeXML line-wraps
    mid-sentence; nothing else is relaxed.
    """
    needle = re.sub(r"\s+", " ", quote).strip()
    for section in sections:
        if needle in re.sub(r"\s+", " ", section.text):
            return section.kind
    return None
