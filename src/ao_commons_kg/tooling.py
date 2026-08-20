"""The mirrored builder-tooling index, and its link to the library.

`awesome-builder-tools` (Framework Zero, MIT) curates open-source tools for
running an AI-staffed company. It is good and it is not this library: it
answers *what should I build with*, organised by the builder's job, while this
corpus answers *what does a tool let agents do, and what stops them*, organised
by the taxonomy.

Mirroring rather than copying, and mirroring rather than absorbing, for one
measured reason. Of its 60 entries, 7 describe agents holding authority or
being constrained; the rest are CRMs, ad tooling and billing — things a company
buys, not things that give an agent authority. Pouring all 60 into
`data/resources/` would drown a corpus scoped to agentic organizations in a
shopping list.

So the index sits apart, complete and attributed, and entries cross into the
library one at a time when someone has read the tool's own documentation and
can say what oversight it actually ships. The mirror is upstream's claim; a
resource record is ours, and the two should not be confused.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent.parent
DEFAULT_PATH = REPO / "data" / "tooling" / "awesome-builder-tools.yml"

UPSTREAM = "https://github.com/framework-zero/awesome-builder-tools"

_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


@dataclass
class Entry:
    """One tool as upstream lists it. Their words, not ours."""

    name: str
    url: str
    section: str
    subsection: str | None = None
    description: str = ""
    stars: str | None = None
    promoted_to: str | None = None
    """The resource id, once somebody has profiled this tool for the library.
    Absent means it is listed but not yet assessed — which is most of them, and
    should stay visible rather than being read as a judgement."""


@dataclass
class Index:
    source: dict = field(default_factory=dict)
    entries: list[Entry] = field(default_factory=list)

    @property
    def promoted(self) -> list[Entry]:
        return [e for e in self.entries if e.promoted_to]


def parse_readme(markdown: str) -> list[Entry]:
    """Read the tables out of upstream's README.

    Headings carry the organising idea — a tool's section is the builder's job
    it belongs to — so they are tracked rather than flattened away.
    """
    entries: list[Entry] = []
    section = subsection = None

    for line in markdown.split("\n"):
        if line.startswith("## "):
            section, subsection = line[3:].strip(), None
        elif line.startswith("### "):
            subsection = line[4:].strip()
        elif line.startswith("|") and "---" not in line and section:
            cells = [c.strip() for c in line.strip("|").split("|")]
            link = _LINK.match(cells[0]) if cells else None
            if not link:
                continue  # a header row, or prose in a table
            entries.append(Entry(
                name=link.group(1).strip(),
                url=link.group(2).strip(),
                section=section,
                subsection=subsection,
                description=cells[1] if len(cells) > 1 else "",
                # The third column is stars in some tables and the licence in
                # others, so it is kept only when it looks like a count.
                stars=cells[2] if len(cells) > 2 and re.search(r"\d", cells[2]) and
                      any(c in cells[2] for c in "k+0123456789") and "/" not in cells[2] else None,
            ))
    return entries


def load(path: str | Path = DEFAULT_PATH) -> Index:
    path = Path(path)
    if not path.exists():
        return Index()
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return Index(
        source=payload.get("source") or {},
        entries=[Entry(**e) for e in payload.get("entries") or []],
    )


def save(index: Index, path: str | Path = DEFAULT_PATH) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": index.source,
        "entries": [
            {k: v for k, v in vars(entry).items() if v not in (None, "")}
            for entry in index.entries
        ],
    }
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True, width=88),
        encoding="utf-8",
    )
    return path


def diff(before: Index, after: Index) -> dict:
    """What changed upstream, keyed by url so a rename is not read as a removal."""
    was = {e.url: e for e in before.entries}
    now = {e.url: e for e in after.entries}

    added = [now[u] for u in now if u not in was]
    removed = [was[u] for u in was if u not in now]
    changed = [
        (was[u], now[u]) for u in now
        if u in was and (was[u].description != now[u].description
                         or was[u].name != now[u].name
                         or was[u].section != now[u].section
                         or was[u].subsection != now[u].subsection)
    ]
    return {"added": added, "removed": removed, "changed": changed}


# Words that suggest a tool does something to an agent's authority rather than
# sitting beside it. A shortlist for a person, not a filter: the text being
# matched is upstream's one-line summary, so a miss means nothing and a hit
# means "read the documentation", which is the only thing that settles it.
_AUTHORITY = re.compile(
    r"\bagent(s|ic)?\b.{0,90}(approv|budget|spend|permission|autonom|delegat|"
    r"orchestrat|authority|oversight|human.in.the.loop|audit)|"
    r"(approv|budget|permission|autonom|oversight|audit).{0,90}\bagent",
    re.I | re.S,
)


def candidates(index: Index) -> list[Entry]:
    """Mirrored entries that look in scope and have not been profiled yet.

    This is the tooling equivalent of the review queue: the point is not to
    decide anything automatically, it is to stop the work being invisible.
    """
    return [e for e in index.entries
            if not e.promoted_to and _AUTHORITY.search(e.description or "")]


def carry_promotions(before: Index, after: Index) -> Index:
    """Keep our own links to the library across a resync.

    Upstream does not know which of its entries we have profiled, so a sync
    that dropped `promoted_to` would silently unlink every tool in the corpus
    from the list it came from.
    """
    promoted = {e.url: e.promoted_to for e in before.entries if e.promoted_to}
    for entry in after.entries:
        if entry.url in promoted:
            entry.promoted_to = promoted[entry.url]
    return after
