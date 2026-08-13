"""arXiv's own record of a preprint.

The third source, and for an arXiv preprint the authoritative one. OpenAlex and
Semantic Scholar are indexes *over* the literature — they infer, they lag, and
they disambiguate authors by machine. arXiv is the submission itself.

It earns its place twice over:

  * OpenAlex does not have recent preprints at all. A paper posted this month
    returns 404, which the site was reporting as "could not reach OpenAlex" —
    an error message describing a network fault that had not happened.
  * OpenAlex's author disambiguation substitutes real, plausible, wrong people.
    It credited `2511.03434` to "Bin Hu" rather than Botao 'Amber' Hu.

It cannot be called from a browser: arXiv sends no `Access-Control-Allow-Origin`
header, so the filing site cannot reach it and falls back to Semantic Scholar,
which does. Server-side there is no such limit, which is why the intake bot can
resolve papers the page could not.
"""

from __future__ import annotations

import html
import re
import urllib.request
from dataclasses import dataclass, field

API = "https://export.arxiv.org/api/query"
CONTACT = "anke@stellar.org"

ENTRY = re.compile(r"<entry>(.*?)</entry>", re.S)
IDENTIFIER = re.compile(r"<id>https?://arxiv\.org/abs/([0-9.]+)v?\d*</id>")
NAME = re.compile(r"<name>(.*?)</name>", re.S)
TITLE = re.compile(r"<title>(.*?)</title>", re.S)
SUMMARY = re.compile(r"<summary>(.*?)</summary>", re.S)
PUBLISHED = re.compile(r"<published>(\d{4}-\d{2}-\d{2})")


class ArxivError(RuntimeError):
    """arXiv could not be asked, or has nothing under that id."""


@dataclass
class Preprint:
    arxiv_id: str
    title: str
    authors: list[str] = field(default_factory=list)
    abstract: str | None = None
    published: str | None = None


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def parse(payload: str) -> dict[str, Preprint]:
    """Read an Atom feed into preprints, keyed by arXiv id."""
    found: dict[str, Preprint] = {}
    for entry in ENTRY.findall(payload):
        identifier = IDENTIFIER.search(entry)
        title = TITLE.search(entry)
        if not identifier or not title:
            continue
        summary = SUMMARY.search(entry)
        published = PUBLISHED.search(entry)
        found[identifier.group(1)] = Preprint(
            arxiv_id=identifier.group(1),
            title=_clean(title.group(1)),
            authors=[_clean(name) for name in NAME.findall(entry)],
            abstract=_clean(summary.group(1)) if summary else None,
            published=published.group(1) if published else None,
        )
    return found


def http_fetcher():
    """The real one, over the standard library — no dependency for one GET."""

    def fetch(url: str) -> str:
        request = urllib.request.Request(
            url, headers={"User-Agent": f"ao-commons-kg ({CONTACT})"}
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read().decode("utf-8", "ignore")
        except Exception as error:  # noqa: BLE001 — one answer whatever the cause
            raise ArxivError(f"arXiv: {type(error).__name__}: {error}") from error

    return fetch


def resolve_many(arxiv_ids: list[str], fetch=None) -> dict[str, Preprint]:
    """Look up several ids in one request, which is what arXiv prefers."""
    if not arxiv_ids:
        return {}
    fetch = fetch or http_fetcher()
    return parse(fetch(f"{API}?id_list={','.join(arxiv_ids)}&max_results={len(arxiv_ids)}"))


def resolve(arxiv_id: str, fetch=None) -> Preprint:
    """One preprint. Raises rather than returning None: a silent miss during
    ingestion becomes a record with no metadata and nobody notices."""
    found = resolve_many([arxiv_id], fetch).get(arxiv_id)
    if found is None:
        raise ArxivError(f"arXiv has no entry for {arxiv_id}")
    return found
