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
from dataclasses import dataclass
from pathlib import Path

import yaml
import unicodedata
from collections import Counter, defaultdict

PUNCTUATION = re.compile(r"[.'`\-‐‑’]")
SPACES = re.compile(r"\s+")


IDENTITIES = Path(__file__).resolve().parent.parent.parent / "data" / "people"

# Suffixes that follow a comma legitimately. "King, Jr." is one person's name
# written correctly; "Damani, Mehul" is a catalogue entry that escaped.
_SUFFIXES = {"jr", "jr.", "sr", "sr.", "ii", "iii", "iv", "phd", "ph.d.", "md", "m.d."}


def uninvert(name: str) -> str:
    """`Damani, Mehul` -> `Mehul Damani`. A byline, not a catalogue entry.

    Indexes sort people by surname and hand the name back sorted. arXiv gives
    the byline as submitted, which is why it is asked last and treated as
    decisive — but it answers only for preprints, and for everything else an
    inverted name goes in exactly as the index spelled it. Thirty-five of them
    across six records reached the corpus that way, and they read as different
    people from their own co-authors.

    Only a single comma is touched, and only when what follows is not a
    suffix, so `Martin Luther King, Jr.` survives.
    """
    text = " ".join((name or "").split())
    if text.count(",") != 1:
        return text
    surname, given = (part.strip() for part in text.split(","))
    if not surname or not given or given.lower().rstrip(".") in {
            s.rstrip(".") for s in _SUFFIXES}:
        return text
    return f"{given} {surname}"


def fold(name: str) -> str:
    """The key two spellings of one person share.

    Accents and punctuation come off; word order and initials do not change.

    ß is expanded to ss before the accent pass, because NFKD leaves it alone —
    it is a letter, not an accented s. Without this, "Wolfram Barfuß" and
    "Wolfram Barfuss" are two people.
    """
    decomposed = unicodedata.normalize("NFKD", (name or "").replace("ß", "ss"))
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return SPACES.sub(" ", PUNCTUATION.sub("", without_accents)).strip().lower()


def same_person(a: str, b: str) -> bool:
    """Whether two bylines name the same person, allowing for how bylines vary.

    Looser than `fold`, and deliberately so: `fold` is used to decide whether to
    *merge* two spellings, where a wrong merge is hard to notice, so it refuses
    to expand initials. This answers a different question — whether a byline
    from one source has been substituted for a different human being — where the
    expensive mistake is the opposite one. Calling "Michael E. Houle" and
    "Michael Houle" different people would send someone to correct a record that
    is already right.

    Same surname plus a compatible first name, in either order. It will not
    reconcile "Bin Hu" with "Botao 'Amber' Hu", which is the case this exists
    to catch.
    """
    left, right = fold(a).split(), fold(b).split()
    if not left or not right:
        return False
    if left == right or sorted(left) == sorted(right):
        return True  # the same tokens, sometimes in the order the other source chose
    if left[-1] != right[-1]:
        return False  # different surname

    first_left, first_right = left[0], right[0]
    if first_left == first_right:
        return True
    # An initial stands for the name it begins. "S. S. Zhu" is "Shenzhe Zhu";
    # "Bin Hu" is not "Botao Hu", because neither is an abbreviation of the other.
    if len(first_left) == 1 or len(first_right) == 1:
        return first_left[0] == first_right[0]
    return False


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


@dataclass
class Identity:
    """A filing account joined to a name on a byline."""

    name: str
    github: str | None = None
    orcid: str | None = None
    link_status: str = "claimed"
    verified_by: str | None = None
    verified_how: str | None = None

    @property
    def verified(self) -> bool:
        """A matching name is a coincidence until somebody says otherwise.

        `claimed` is the honest default and it does not carry weight: the link
        has to be confirmed by a named person before a verdict filed from that
        account counts as an author's.
        """
        return self.link_status == "verified" and bool(self.verified_by)


def load_identities(directory: str | Path = IDENTITIES) -> dict[str, Identity]:
    """Identity links, keyed by GitHub login in lower case."""
    directory = Path(directory)
    if not directory.exists():
        return {}
    found: dict[str, Identity] = {}
    for path in sorted(directory.glob("*.yml")):
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not payload.get("name"):
            raise ValueError(f"{path.name}: an identity link with no name links nothing")
        identity = Identity(**{k: payload.get(k) for k in Identity.__dataclass_fields__
                               if payload.get(k) is not None})
        if identity.github:
            found[identity.github.lower()] = identity
    return found


def wrote(login: str, authors: list[str],
          identities: dict[str, Identity] | None = None) -> bool:
    """Whether this filing account belongs to somebody on this byline.

    Derived rather than claimed. A filing can say it comes from an author and
    that is worth nothing on its own; this asks the link table, and the link
    table only answers for a link a named person has confirmed.
    """
    if identities is None:
        identities = load_identities()
    identity = identities.get((login or "").lower())
    if identity is None or not identity.verified:
        return False
    return any(same_person(identity.name, author) for author in authors or [])
