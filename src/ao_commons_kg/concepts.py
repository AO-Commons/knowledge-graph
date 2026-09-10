"""The concept vocabulary: what a claim is arguing about.

Two tagging layers, and the distinction is the point.

A **topic code** says what a record is *about*, and is coarse on purpose.
Fifteen of the first forty-five claims sit on 14.1, which tells you they
concern capability evaluation and stops there. Topics are filing targets:
there are 103, they are stable, and renumbering one breaks every reference to
it.

A **concept tag** says what is actually at stake in a sentence — "evaluation
gaming", "sanction sensitivity", "endogenous non-stationarity". Concepts are
not filing targets. They are how two claims from different papers become
findable as candidates for a relation, and how a researcher arrives with a
question rather than guessing which branch it lives under.

The vocabulary comes from two places, and never from a third:

1. **The taxonomy's own subpoints.** 514 leaf titles were demoted to notes in
   August, when measurement showed the leaf layer was forcing a hard choice on
   every record and earning almost nothing — 93% of tags landed at subsection
   level. The titles survived, one indent deeper. They are the most specific
   vocabulary this project has already agreed on, so they are read from the
   taxonomy file rather than copied here. One source of truth.

2. **Terms that arrived from claims**, in `taxonomy/concepts-extra.yml`. A
   claim can be about something the taxonomy never needed a shelf for. Adding
   one is cheap and reversible, which is exactly what a new topic code is not.

That asymmetry is deliberate. The taxonomy stays top-down and stable; the
concept layer grows bottom-up from what the corpus turns out to argue about.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent.parent
TAXONOMY = REPO / "taxonomy" / "agentic-org-research-library-taxonomy-v3.md"
EXTRA = REPO / "taxonomy" / "concepts-extra.yml"

_SLUG_STRIP = re.compile(r"[^a-z0-9]+")


def slug(label: str) -> str:
    """A stable id for a concept, from its label.

    Accents fold and punctuation goes, so "Duéñez-Guzmán's rule" and
    "Duenez Guzman's rule" cannot become two concepts. Deliberately lossy:
    the label is the display form, this is only the key.
    """
    decomposed = unicodedata.normalize("NFKD", label or "")
    plain = "".join(c for c in decomposed if not unicodedata.combining(c))
    return _SLUG_STRIP.sub("-", plain.lower()).strip("-")


@dataclass(frozen=True)
class Concept:
    """One term in the vocabulary."""

    id: str
    label: str
    topics: tuple[str, ...] = ()
    """Where in the taxonomy this concept sits, for navigation. A concept
    under 14.3 is reachable from 14.3; it is not filed there, because
    concepts are not filing targets."""
    origin: str = "taxonomy"
    """`taxonomy` for a demoted subpoint, `claim` for a term the corpus
    needed and the taxonomy did not have. Worth keeping: a concept layer
    that drifts away from the taxonomy is telling you something about the
    taxonomy."""
    note: str | None = None
    added: str | None = None

    def to_dict(self) -> dict:
        payload = {"id": self.id, "label": self.label, "origin": self.origin}
        if self.topics:
            payload["topics"] = list(self.topics)
        if self.note:
            payload["note"] = self.note
        if self.added:
            payload["added"] = self.added
        return payload


@dataclass
class Vocabulary:
    """Every concept, keyed by id."""

    concepts: dict[str, Concept] = field(default_factory=dict)

    def __contains__(self, concept_id: str) -> bool:
        return concept_id in self.concepts

    def __len__(self) -> int:
        return len(self.concepts)

    def get(self, concept_id: str) -> Concept | None:
        return self.concepts.get(concept_id)

    def unknown(self, concept_ids) -> list[str]:
        """Which of these are not in the vocabulary.

        Reported rather than dropped, on the same reasoning as a bad topic
        code: a tag that does not resolve is usually a near-miss for one that
        does, and discarding it silently loses a judgement somebody made.
        """
        return [c for c in concept_ids if c not in self.concepts]

    def by_topic(self, code: str) -> list[Concept]:
        return sorted(
            (c for c in self.concepts.values() if code in c.topics),
            key=lambda c: c.label,
        )

    def search(self, phrase: str) -> list[Concept]:
        """Substring match over labels. The navigation Rakshit asked for —
        arrive with a phrase, land on the concepts that mention it."""
        needle = (phrase or "").strip().lower()
        if not needle:
            return []
        return sorted(
            (c for c in self.concepts.values() if needle in c.label.lower()),
            key=lambda c: (len(c.label), c.label),
        )


def load_vocabulary(taxonomy_path: Path | str = TAXONOMY,
                    extra_path: Path | str = EXTRA) -> Vocabulary:
    """Build the vocabulary: taxonomy subpoints, then the extras.

    A subpoint that appears under two subsections becomes one concept
    carrying both topic codes, rather than two concepts with the same label —
    which is the same "one person, one spelling" rule the people module
    applies to bylines, for the same reason.
    """
    from .taxonomy import load_taxonomy

    concepts: dict[str, Concept] = {}
    for topic in load_taxonomy(taxonomy_path):
        for label in topic.subpoints or []:
            key = slug(label)
            if not key:
                continue
            if existing := concepts.get(key):
                if topic.code not in existing.topics:
                    concepts[key] = Concept(
                        id=key, label=existing.label,
                        topics=tuple(sorted({*existing.topics, topic.code})),
                        origin=existing.origin, note=existing.note,
                        added=existing.added,
                    )
            else:
                concepts[key] = Concept(id=key, label=label, topics=(topic.code,))

    extra_path = Path(extra_path)
    if extra_path.exists():
        payload = yaml.safe_load(extra_path.read_text(encoding="utf-8")) or {}
        for entry in payload.get("concepts", []):
            label = entry.get("label", "")
            key = entry.get("id") or slug(label)
            if not key:
                continue
            # One concept, one identifier. A hand-written id that drifts from
            # its label is how the same idea ends up tagged two ways, which
            # silently halves every relation those tags would have proposed.
            if key != slug(label):
                raise ValueError(
                    f"concept {key!r} does not match its label {label!r} "
                    f"(expected id {slug(label)!r}). Shorten the label or "
                    "change the id — they have to agree."
                )
            if key in concepts:
                # A term that has since been given a home in the taxonomy.
                # The taxonomy wins and the extra is redundant; say so rather
                # than letting the file quietly grow stale entries.
                raise ValueError(
                    f"concept {key!r} is in concepts-extra.yml and is also a "
                    f"taxonomy subpoint under {concepts[key].topics}. Remove it "
                    "from the extras file — the taxonomy is the source of truth."
                )
            concepts[key] = Concept(
                id=key, label=label,
                topics=tuple(entry.get("topics") or ()),
                origin=entry.get("origin", "claim"),
                note=entry.get("note"),
                added=entry.get("added"),
            )
    return Vocabulary(concepts=concepts)


def propose(label: str, topics, note: str | None = None) -> dict:
    """The shape an addition to `concepts-extra.yml` takes."""
    return {
        "id": slug(label),
        "label": label,
        "topics": sorted(topics),
        "origin": "claim",
        "note": note,
        "added": date.today().isoformat(),
    }
