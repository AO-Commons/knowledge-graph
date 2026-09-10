"""One organization, one spelling — and two organizations left as two.

The same problem `people.py` solves for bylines, with the failure modes
reversed. Author names vary by punctuation and initials, and a wrong merge
is hard to notice. Organization names vary by *country suffix and
sub-entity*, and a wrong merge is easy to notice and much worse:

    Google (United States)
    Google (United Kingdom)
    Google DeepMind (United Kingdom)

The first two are one company reported from two OpenAlex country records.
The third is not the same thing as the first two in any sense a researcher
would accept, and merging it would put every DeepMind paper under Google
and quietly delete a distinction the field cares about.

So the rule is narrow on purpose. Only the country suffix comes off. No
substring matching, no acronym expansion, no "starts with the same word" —
`Google` and `Google DeepMind` stay separate, `University of California,
Berkeley` and `University of California, Davis` stay separate, and anything
this module is unsure about it reports rather than merges.

An alias file carries the judgements a rule cannot make. That is where
`DeepMind` and `Google DeepMind` get joined, by a person, once.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent.parent
ALIASES = REPO / "taxonomy" / "organization-aliases.yml"

# "Google (United States)" -> "Google". Only a trailing parenthesised
# country, and only when it looks like a place rather than a qualifier:
# "(United Kingdom)" goes, "(Fictional Division)" stays, because the second
# is carrying meaning we would be throwing away.
_COUNTRY = re.compile(
    r"\s*\((?:the\s+)?[A-Z][A-Za-z.\- ]*(?:United States|United Kingdom|Kingdom|Republic|"
    r"States|Federation|Germany|France|Canada|China|Japan|Australia|Netherlands|"
    r"Switzerland|Sweden|Denmark|Norway|Finland|Belgium|Austria|Ireland|Israel|India|"
    r"Singapore|Korea|Spain|Italy|Poland|Portugal|Brazil|Mexico|Chile|"
    r"New Zealand|South Africa)\)\s*$"
)
_SPACES = re.compile(r"\s+")


def strip_country(name: str) -> str:
    """Drop a trailing country in parentheses, and nothing else."""
    return _SPACES.sub(" ", _COUNTRY.sub("", name or "")).strip()


def fold(name: str) -> str:
    """The key two spellings of one organization share.

    Accents and case go; word order, punctuation between words, and every
    substantive token stay. Deliberately weaker than the people equivalent
    — it will not join `Google` to `Google DeepMind`, and it should not.
    """
    plain = strip_country(name)
    decomposed = unicodedata.normalize("NFKD", plain)
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return _SPACES.sub(" ", without_accents).strip().lower()


@dataclass
class Registry:
    """Canonical organization names, and the aliases pointing at them."""

    canonical: dict[str, str] = field(default_factory=dict)
    """Folded key -> the spelling to display."""
    aliases: dict[str, str] = field(default_factory=dict)
    """Folded alias -> folded canonical key. Human judgements only."""

    def resolve(self, name: str) -> str:
        key = fold(name)
        key = self.aliases.get(key, key)
        return self.canonical.get(key, strip_country(name))

    def __len__(self) -> int:
        return len(set(self.canonical.values()))


def load_registry(path: Path | str = ALIASES) -> Registry:
    """Aliases a rule cannot infer, written down by a person."""
    registry = Registry()
    path = Path(path)
    if not path.exists():
        return registry
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    for entry in payload.get("organizations", []):
        canonical = entry.get("canonical")
        if not canonical:
            continue
        key = fold(canonical)
        registry.canonical[key] = canonical
        for alias in entry.get("aliases") or []:
            registry.aliases[fold(alias)] = key
    return registry


def build_index(names: list[str], registry: Registry | None = None) -> dict[str, str]:
    """Map every spelling seen to the one to keep.

    Country-suffix variants collapse; everything else is left alone. The
    surviving spelling is the most common one, and on a tie the longest,
    because the fuller form is usually the more informative rendering
    rather than a competing opinion.
    """
    registry = registry or Registry()
    counts: dict[str, Counter] = defaultdict(Counter)
    for name in names:
        if name:
            key = fold(name)
            counts[registry.aliases.get(key, key)][strip_country(name)] += 1

    index: dict[str, str] = {}
    for key, spellings in counts.items():
        best = registry.canonical.get(key) or max(
            spellings, key=lambda n: (spellings[n], len(n), n))
        for name in names:
            if name and registry.aliases.get(fold(name), fold(name)) == key:
                if name != best:
                    index[name] = best
    return index


def apply_index(names: list[str], index: dict[str, str]) -> list[str]:
    """Rewrite a list of organizations, order preserved, duplicates dropped."""
    seen, out = set(), []
    for name in names or []:
        resolved = index.get(name, name)
        if resolved not in seen:
            seen.add(resolved)
            out.append(resolved)
    return out


def near_misses(names: list[str]) -> list[tuple[str, str]]:
    """Pairs that look related and are deliberately not merged.

    Reported so a person can decide. `Google` and `Google DeepMind` show up
    here every time, which is correct — the answer is an alias entry or
    nothing, never a rule that guesses.
    """
    distinct = sorted({strip_country(n) for n in names if n})
    pairs = []
    for i, left in enumerate(distinct):
        for right in distinct[i + 1:]:
            lf, rf = fold(left), fold(right)
            if lf != rf and (lf.startswith(rf) or rf.startswith(lf)):
                pairs.append((left, right))
    return pairs


def resolves_to_the_same_paper(record_title: str, record_authors, work) -> bool:
    """Whether a fetched work is plausibly the record we asked about.

    An identifier can be wrong. `doi-10-48550-arxiv-1903-09376` in this
    corpus is titled *Multiparty Dynamics and Failure Modes for Machine
    Learning and AI* and its DOI belongs to *Deep Fictitious Play for
    Stochastic Differential Games* — so a backfill that trusts resolution
    writes a stranger's institution onto the record, and nothing about the
    result looks wrong.

    Cheap agreement on either title or byline is enough; both being absent
    is not. Deliberately permissive about *how* they agree, because
    retitling between preprint and publication is normal, and strict about
    requiring some agreement at all.
    """
    import difflib

    from .people import same_person

    fetched_title = (getattr(work, "title", "") or "").lower().strip()
    mine = (record_title or "").lower().strip()
    if mine and fetched_title:
        if difflib.SequenceMatcher(None, mine, fetched_title).ratio() > 0.75:
            return True

    fetched_authors = list(getattr(work, "authors", []) or [])
    held = list(record_authors or [])
    if held and fetched_authors:
        shared = sum(1 for h in held if any(same_person(h, f) for f in fetched_authors))
        if shared and shared / min(len(held), len(fetched_authors)) >= 0.5:
            return True

    return False
