"""Where a scout looks.

Two sources, both free and neither needing a key, so the tool carries itself
without a subscription. A paid source can be added behind the same interface
later and must never become load-bearing: if its terms or pricing change, the
scout should lose a source rather than stop.

Both are asked for *recent* work, because the reason to scout at all is that
citation expansion cannot see a paper before anyone has cited it.
"""

from __future__ import annotations

import json
import re
import urllib.parse
from datetime import date, timedelta

from .scholarly.keys import canonical_key
from .scout import Find, Query

AGENT = "ao-commons-knowledge-graph (+https://github.com/AO-Commons/knowledge-graph)"


def _get(url: str, *, timeout: int = 30) -> str:
    """Over `requests`, like every other fetcher here.

    Not a preference. arXiv answers 406 to urllib and 200 to requests with
    the same URL and the same headers, and `scholarly/arxiv.py` already
    carries the note explaining why this project uses one transport: a
    second one means a second failure mode, discovered later and further
    from its cause.
    """
    import requests

    response = requests.get(url, headers={"User-Agent": AGENT}, timeout=timeout)
    response.raise_for_status()
    return response.text


def _since(days: int) -> str:
    return (date.today() - timedelta(days=days)).isoformat()


class ArxivSource:
    """arXiv's API: free, no key, and the freshest thing there is.

    Asked by category *and* phrase. Category alone is a firehose and phrase
    alone reaches across all of physics; together they are narrow enough that
    what comes back is worth scoring.
    """

    name = "arxiv"
    API = "https://export.arxiv.org/api/query"
    CATEGORIES = ("cs.MA", "cs.AI", "cs.CY", "cs.SE", "cs.HC")

    def __init__(self, categories: tuple[str, ...] | None = None, fetch=_get):
        self.categories = categories or self.CATEGORIES
        self.fetch = fetch

    def search(self, query: Query, *, limit: int = 10) -> list[Find]:
        # Every word, rather than the phrase. An exact phrase search on a
        # three-word concept mostly returns nothing — `agent reputation
        # systems` finds none while `multi-agent governance` finds four —
        # and recall is the thing to protect here: precision comes from the
        # category filter and from scoring against our own taxonomy, both of
        # which are free, while a paper never returned is never scored.
        cats = " OR ".join(f"cat:{c}" for c in self.categories)
        words = [w for w in re.split(r"\W+", query.text) if len(w) > 2]
        if not words:
            return []
        terms = " AND ".join(f"abs:{w}" for w in words[:4])
        search = f"({cats}) AND ({terms})"
        url = (f"{self.API}?"
               + urllib.parse.urlencode({
                   "search_query": search, "start": 0, "max_results": limit,
                   "sortBy": "submittedDate", "sortOrder": "descending"}))
        return self.parse(self.fetch(url))

    @staticmethod
    def parse(payload: str) -> list[Find]:
        finds = []
        for entry in re.findall(r"<entry>(.*?)</entry>", payload, re.S):
            def one(tag: str) -> str:
                found = re.search(rf"<{tag}>(.*?)</{tag}>", entry, re.S)
                return " ".join(found.group(1).split()) if found else ""

            link = re.search(r"<id>(.*?)</id>", entry, re.S)
            url = link.group(1).strip() if link else ""
            arxiv_id = url.rsplit("/", 1)[-1].split("v")[0] if url else ""
            if not arxiv_id:
                continue
            finds.append(Find(
                key=canonical_key({"arxiv": arxiv_id}),
                title=one("title"), abstract=one("summary"),
                date=one("published")[:10], url=url, source="arxiv"))
        return finds


class OpenAlexSource:
    """OpenAlex search: free, no key, and reaches past arXiv into journals.

    Filtered to recent work and to a minimum of nothing — a paper with no
    citations is exactly what this is for, so filtering by citation count
    here would reintroduce the blindness the scout exists to fix.
    """

    name = "openalex"
    API = "https://api.openalex.org/works"

    def __init__(self, days: int = 120, fetch=_get):
        self.days = days
        self.fetch = fetch

    def search(self, query: Query, *, limit: int = 10) -> list[Find]:
        url = (f"{self.API}?"
               + urllib.parse.urlencode({
                   "search": query.text,
                   "filter": f"from_publication_date:{_since(self.days)}",
                   "per-page": limit, "sort": "publication_date:desc"}))
        return self.parse(self.fetch(url))

    @staticmethod
    def parse(payload: str) -> list[Find]:
        try:
            works = (json.loads(payload) or {}).get("results") or []
        except json.JSONDecodeError:
            return []

        finds = []
        for work in works:
            ids = work.get("ids") or {}
            key = canonical_key({
                "doi": (work.get("doi") or "").replace("https://doi.org/", ""),
                "openalex": ids.get("openalex") or work.get("id"),
            })
            if not key:
                continue
            finds.append(Find(
                key=key,
                title=work.get("title") or work.get("display_name") or "",
                abstract=_abstract(work.get("abstract_inverted_index")),
                date=work.get("publication_date") or "",
                url=work.get("doi") or work.get("id") or "",
                source="openalex"))
        return finds


def _abstract(inverted: dict | None) -> str:
    """OpenAlex stores abstracts as an inverted index; rebuild the text."""
    if not inverted:
        return ""
    spots: dict[int, str] = {}
    for word, positions in inverted.items():
        for position in positions:
            spots[position] = word
    return " ".join(spots[i] for i in sorted(spots))
