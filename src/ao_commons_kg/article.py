"""Full text for things that were never papers.

The corpus reads arXiv's LaTeXML and nothing else, which quietly decided what
kind of knowledge it could hold. A lab write-up, a research blog post or an
open proceedings page carries findings that often appear there first and
nowhere else for a year, and all of it was unreadable — not refused on scope,
just invisible to the pipeline.

Papers gave us three things for free that a web page does not, and each one is
handled here rather than assumed away:

**The source can change or vanish.** An arXiv id resolves to the same bytes
forever. A blog post does not, and the whole extraction method rests on a quote
that can be checked against its source. So reading a page also writes a
snapshot: the extracted text, the retrieval date and the SHA-256 of the HTML it
came from. The snapshot is committed, not cached — `data/cache/` is ignored by
git, and an archive that disappears when somebody clears a directory is not an
archive. Everything after the fetch reads the snapshot, so a quote stays
checkable after the page is gone or rewritten.

**There is no structure to trust.** LaTeXML marks its sections; a web page
marks whatever its theme felt like. Headings are found generically and the
chrome is removed by name, because the alternative — trusting a site's markup —
fails differently on every site.

**There is no scholarly identity.** No DOI, no OpenAlex record, so no
references out and no way to be cited in. A record read this way can never be
admitted by citation expansion and can never help admit anything else. That is
a real cost and it is not fixable here: it means every such record spends a
human judgment that a paper might not have.
"""

from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from . import CONTACT
from .fulltext import FullTextError, Section, _plain, classify_heading

REPO = Path(__file__).resolve().parent.parent.parent
CACHE = REPO / "data" / "cache" / "article"
SNAPSHOTS = REPO / "data" / "snapshots"

# Removed before anything is parsed, for the reason the LaTeXML reader gives:
# deleting a region outright cannot drift, where tracking a tag stack can.
STRIP = tuple(
    re.compile(rf"<{tag}\b.*?</{tag}>", re.S | re.I)
    for tag in ("script", "style", "svg", "nav", "header", "footer", "aside",
                "form", "noscript", "figure", "table", "iframe", "button")
)

# Where the article proper starts, best first. A page that marks its content
# saves us from guessing; one that does not falls back to the whole body.
CONTAINERS = (
    re.compile(r"<d-article\b", re.I),
    re.compile(r"<article\b", re.I),
    re.compile(r"<main\b", re.I),
    re.compile(r"<[a-z]+[^>]*\brole=[\"']main[\"']", re.I),
)
CONTAINER_ENDS = re.compile(r"</(?:d-article|article|main)>", re.I)

HEADING = re.compile(r"<h([1-4])\b[^>]*>(.*?)</h\1>", re.S | re.I)
PARAGRAPH = re.compile(r"<(p|li)\b[^>]*>(.*?)</\1>", re.S | re.I)

# Headings that are furniture, not argument. Matched on the normalized heading.
FURNITURE = (
    "cookie", "rss feed", "newsletter", "subscribe", "share this", "comments",
    "related posts", "related reading", "footnotes", "references",
    "bibliography", "about the author", "acknowledgement", "acknowledgment",
    "citation", "cite this", "attachments", "appendix", "table of contents",
    "sign up", "follow us", "privacy", "terms of", "articles in", "more from",
    "latest posts", "in this issue", "also read",
)

# Below this, a "section" is a caption, a byline or a stray list item.
MIN_SECTION = 220


@dataclass
class Article:
    """A web page read as text, with what is needed to check a quote later."""

    url: str
    title: str
    retrieved_on: str
    sha256: str
    sections: list[Section]

    @property
    def text(self) -> str:
        return "\n\n".join(s.text for s in self.sections)


def _slug(url: str) -> str:
    """A filename for a URL. The hash is what makes it unique; the readable
    part is so a directory listing means something to a person."""
    readable = re.sub(r"[^a-z0-9]+", "-", url.lower().split("://")[-1]).strip("-")
    return f"{readable[:60]}-{hashlib.sha256(url.encode()).hexdigest()[:8]}"


def fetch(url: str, *, cache: Path | None = None, refresh: bool = False) -> str:
    """The page's HTML, cached on disk between runs."""
    cache = CACHE if cache is None else cache
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / f"{_slug(url)}.html"
    if path.exists() and not refresh:
        return path.read_text(encoding="utf-8")
    request = urllib.request.Request(
        url, headers={"User-Agent": f"ao-commons-kg ({CONTACT})"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8", "ignore")
    except Exception as error:  # noqa: BLE001 — the reason varies, the answer does not
        raise FullTextError(f"{url}: {type(error).__name__}: {error}") from error
    path.write_text(body, encoding="utf-8")
    return body


def _title(html: str) -> str:
    if found := re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I):
        return _plain(found.group(1)).split(" | ")[0].split(" // ")[0].strip()
    return ""


def parse(html: str) -> list[Section]:
    """Split a web page into the same Sections the LaTeXML reader produces.

    Downstream — gap hunting, verbatim checking, extraction — then works on a
    blog post exactly as it works on a paper, which is the point of borrowing
    the type rather than inventing a parallel one.
    """
    for pattern in STRIP:
        html = pattern.sub(" ", html)

    for container in CONTAINERS:
        if found := container.search(html):
            body = html[found.start():]
            if end := CONTAINER_ENDS.search(body):
                body = body[: end.end()]
            html = body
            break

    blocks: list[tuple[str, str]] = []
    for match, kind in sorted(
        [*((m, "heading") for m in HEADING.finditer(html)),
         *((m, "text") for m in PARAGRAPH.finditer(html))],
        key=lambda pair: pair[0].start(),
    ):
        if text := _plain(match.group(2)):
            blocks.append((kind, text))

    sections: list[Section] = []
    heading, paragraphs = "", []

    def close():
        if not paragraphs:
            return
        body = "\n\n".join(paragraphs)
        plain = (heading or "").strip().lower()
        if any(word in plain for word in FURNITURE):
            return
        if len(body) < MIN_SECTION:
            return
        sections.append(Section(classify_heading(heading), heading or "—", body))

    for kind, text in blocks:
        if kind == "heading":
            close()
            heading, paragraphs = text, []
        else:
            paragraphs.append(text)
    close()
    return sections


def read(url: str, **kwargs) -> Article:
    """Fetch and parse a page, with the provenance needed to re-check a quote."""
    html = fetch(url, **kwargs)
    sections = parse(html)
    if not sections:
        raise FullTextError(
            f"{url}: no article text found. The page may be a landing page, or "
            "render its content with JavaScript, which this reader does not run."
        )
    return Article(url=url, title=_title(html), retrieved_on=date.today().isoformat(),
                   sha256=hashlib.sha256(html.encode("utf-8", "ignore")).hexdigest(),
                   sections=sections)


def snapshot_path(resource_id: str, *, directory: Path | None = None) -> Path:
    """Where a record's snapshot lives.

    `directory` resolves at call time rather than binding SNAPSHOTS as a
    default, because a default argument is evaluated once at import and then
    cannot be redirected — which makes the archive untestable and silently
    pins every caller to one location.
    """
    directory = SNAPSHOTS if directory is None else directory
    return directory / f"{re.sub(r'[^a-z0-9]+', '-', resource_id.lower()).strip('-')}.json"


def save(article: Article, resource_id: str, *, directory: Path | None = None) -> Path:
    """Commit the text a quote will be checked against.

    Stored as text rather than HTML: it is what the quote has to match, it is a
    tenth the size, and a diff on it says what changed in the argument rather
    than what changed in the theme.
    """
    directory = SNAPSHOTS if directory is None else directory
    directory.mkdir(parents=True, exist_ok=True)
    path = snapshot_path(resource_id, directory=directory)
    path.write_text(json.dumps({
        "resource_id": resource_id, "url": article.url, "title": article.title,
        "retrieved_on": article.retrieved_on, "sha256": article.sha256,
        "sections": [{"kind": s.kind, "heading": s.heading, "text": s.text}
                     for s in article.sections],
    }, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def load(resource_id: str, *, directory: Path | None = None) -> Article:
    """The committed snapshot. Reads no network, so a quote stays checkable
    after the page has changed or gone."""
    path = snapshot_path(resource_id, directory=directory)
    if not path.exists():
        raise FullTextError(f"{resource_id}: no snapshot at {path.name}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    return Article(
        url=payload["url"], title=payload.get("title", ""),
        retrieved_on=payload["retrieved_on"], sha256=payload["sha256"],
        sections=[Section(s["kind"], s["heading"], s["text"])
                  for s in payload["sections"]])


def sections_for(resource_id: str, **kwargs) -> list[Section]:
    """Mirrors `fulltext.sections_for`, so callers need not know which kind of
    record they hold."""
    return load(resource_id, **kwargs).sections
