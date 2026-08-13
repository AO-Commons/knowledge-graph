"""One person, one spelling.

OpenAlex and Semantic Scholar punctuate names differently, so the same
researcher arrives as "Joel Z. Leibo" from one and "Joel Z Leibo" from the
other. Left alone, anything that groups by author — a co-authorship view, a
"what has this person written" query, the community overlay — sees two people
where there is one.

The fix belongs at ingestion rather than at display. Papering over it in the
UI leaves the stored data wrong, and every new consumer has to rediscover the
problem.

Deliberately conservative about what counts as the same person. Punctuation
and accents are folded; initials are not expanded. "J. Leibo" and "Joel Z.
Leibo" stay separate, because merging them needs evidence this module does not
have, and a wrong merge is far harder to notice than a missed one.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter, defaultdict

PUNCTUATION = re.compile(r"[.'`\-‐‑’]")
SPACES = re.compile(r"\s+")


def fold(name: str) -> str:
    """The key two spellings of one person share.

    Accents and punctuation come off; word order and initials do not change.
    """
    decomposed = unicodedata.normalize("NFKD", name or "")
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return SPACES.sub(" ", PUNCTUATION.sub("", without_accents)).strip().lower()


def _richness(name: str) -> tuple[int, int, int]:
    """How complete a spelling looks.

    Accents first, then punctuation, then length. "Duéñez-Guzmán" beats
    "Duenez-Guzman"; "Rakshit S. Trivedi" beats "Rakshit S Trivedi". Both are
    cases where the fuller form is the more correct one, independent of which
    happens to be more common — which matters, because a tie on frequency is
    exactly when a rule is needed.
    """
    accents = sum(1 for c in unicodedata.normalize("NFKD", name) if unicodedata.combining(c))
    return accents, len(PUNCTUATION.findall(name)), len(name)


def canonical(spellings: dict[str, int]) -> str:
    """Pick the spelling to keep, from variants and how often each appears.

    Completeness outranks frequency: a single well-punctuated spelling beats
    a dozen stripped ones, because the stripped form is a lossy rendering of
    the same name rather than a competing opinion about it.
    """
    return max(
        spellings,
        key=lambda name: (*_richness(name), spellings[name], name),
    )


def build_index(names: list[str]) -> dict[str, str]:
    """Map every spelling seen to the canonical one for that person.

    Only variants that actually differ are included, so applying the index is
    a no-op for the overwhelming majority of names.
    """
    counts: dict[str, Counter] = defaultdict(Counter)
    for name in names:
        if name:
            counts[fold(name)][name] += 1

    index = {}
    for spellings in counts.values():
        if len(spellings) < 2:
            continue
        best = canonical(dict(spellings))
        for spelling in spellings:
            if spelling != best:
                index[spelling] = best
    return index


def apply_index(names: list[str], index: dict[str, str]) -> list[str]:
    """Rewrite a record's authors, preserving order and dropping duplicates.

    Order matters in bibliographic authorship, so this never sorts. A record
    holding both spellings of one person collapses to a single entry at the
    earlier position.
    """
    seen, out = set(), []
    for name in names or []:
        resolved = index.get(name, name)
        if resolved not in seen:
            seen.add(resolved)
            out.append(resolved)
    return out


def duplicates(names: list[str]) -> dict[str, dict[str, int]]:
    """Report people who appear under more than one spelling."""
    counts: dict[str, Counter] = defaultdict(Counter)
    for name in names:
        if name:
            counts[fold(name)][name] += 1
    return {
        canonical(dict(spellings)): dict(spellings)
        for spellings in counts.values()
        if len(spellings) > 1
    }
