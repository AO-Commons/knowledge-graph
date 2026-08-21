"""Assign taxonomy topics to a resource automatically.

The scaling constraint. Ingestion is cheap — OpenAlex will hand over
thousands of works — but a corpus nobody has tagged is a pile, and the
taxonomy stops being branches that lead anywhere. Hand-tagging bounded the
library at whatever one person could read.

The method is deliberately boring: BM25 over topic text, no embeddings and no
vector store. The brief says to add one only when measurement shows it earns
its place, and this has to be beaten before that argument can be made.

What makes it work is that the taxonomy is unusually rich text. Each topic
carries a title, its ancestors' titles, any aliases, and the unnumbered
subpoints from the source file — which are often the most specific phrasing
available. 567 topics with that much context behind them is a real index.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field

from .models import Topic, UsageMode

WORD = re.compile(r"[a-z0-9]+")

# Words that appear in so many topics they carry no signal. Kept short and
# domain-specific: a generic English stoplist would leave "agent" and
# "governance" in, which are exactly the terms that discriminate nothing here.
STOP = frozenset("""
a an and are as at be by for from has in is it its of on or that the to with
these those their they this which while when where what who whom how why
agent agents agentic ai artificial intelligence machine system systems
""".split())


# Crude, deliberately. A real stemmer is a dependency and a vocabulary of its
# own; this collapses the endings that actually cost matches here — "evaluating"
# against "evaluation", "overspending" against "overspend", "permissions"
# against "permission". Measured at +3 points of recall@1 and +0.04 MRR.
_SUFFIXES = ("ations", "ation", "ising", "izing", "ments", "ment", "ing", "ness",
             "ence", "ance", "ies", "ed", "es", "s", "ity", "al")


def stem(word: str) -> str:
    for suffix in _SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            return word[: -len(suffix)]
    return word


def tokenize(text: str) -> list[str]:
    words = [w for w in WORD.findall((text or "").lower()) if w not in STOP and len(w) > 2]
    return [stem(w) for w in words]


def with_phrases(terms: list[str]) -> list[str]:
    """Terms plus adjacent pairs.

    A phrase carries meaning its words lose: "spend cap" is not "spend" plus
    "cap", and "human oversight" is not two common words. Worth +2 points of
    recall@3 and the largest single gain measured on MRR.
    """
    return terms + [f"{a}_{b}" for a, b in zip(terms, terms[1:])]


@dataclass
class Assignment:
    code: str
    score: float
    matched: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"code": self.code, "score": round(self.score, 3),
                "matched": self.matched[:6]}


class TopicIndex:
    """BM25 over the taxonomy.

    Each topic's document is its own title plus its ancestors' titles, its
    aliases, and its subpoints. Ancestors are included because a leaf like
    "Capability tokens and scoped credentials" is much easier to match when
    "Authority architecture" and "Permissioning and capability control" are
    part of its text — the tree carries meaning that the leaf alone does not.
    """

    K1 = 1.2
    B = 0.6

    def __init__(self, topics: list[Topic], aliases: dict[str, list[str]] | None = None):
        self.topics = {t.code: t for t in topics}
        aliases = aliases or {}
        by_code = {t.code: t for t in topics}

        self.documents: dict[str, list[str]] = {}
        for topic in topics:
            parts = [topic.title, *topic.subpoints, *aliases.get(topic.code, [])]
            # Ancestor titles, weighted less by appearing once each.
            parts += [by_code[c].title for c in topic.ancestor_codes() if c in by_code]
            if topic.description:
                parts.append(topic.description)
            self.documents[topic.code] = with_phrases(tokenize(" ".join(parts)))

        self.lengths = {c: len(d) for c, d in self.documents.items()}
        self.average_length = (sum(self.lengths.values()) / len(self.lengths)) or 1.0

        self.frequencies = {c: Counter(d) for c, d in self.documents.items()}
        appearances: Counter = Counter()
        for document in self.documents.values():
            appearances.update(set(document))
        total = len(self.documents)
        self.idf = {
            term: math.log(1 + (total - n + 0.5) / (n + 0.5))
            for term, n in appearances.items()
        }

    def score(self, query: list[str], code: str) -> tuple[float, list[str]]:
        frequencies = self.frequencies[code]
        length = self.lengths[code] or 1
        total = 0.0
        matched = []
        for term in set(query):
            frequency = frequencies.get(term, 0)
            if not frequency:
                continue
            idf = self.idf.get(term, 0.0)
            numerator = frequency * (self.K1 + 1)
            denominator = frequency + self.K1 * (
                1 - self.B + self.B * length / self.average_length
            )
            contribution = idf * numerator / denominator
            if contribution > 0:
                total += contribution
                matched.append(term)
        matched.sort(key=lambda t: -self.idf.get(t, 0))
        return total, matched

    def classify(
        self,
        text: str,
        *,
        limit: int = 6,
        min_score: float = 4.0,
        leaves_only: bool = False,
    ) -> list[Assignment]:
        """Multi-label, because a paper is usually about several things.

        Section 11 is a coding scheme rather than a set of shelves, so a
        record matching several failure codes should keep them all — the
        threshold is applied per topic, never "best one wins".
        """
        query = with_phrases(tokenize(text))
        if not query:
            return []

        scored = []
        for code in self.documents:
            if leaves_only and self.topics[code].depth == 0:
                continue
            value, matched = self.score(query, code)
            if value >= min_score:
                scored.append(Assignment(code, value, matched))

        scored.sort(key=lambda a: -a.score)
        return _prune_ancestors(scored, self.topics)[:limit]


def _prune_ancestors(
    assignments: list[Assignment], topics: dict[str, Topic]
) -> list[Assignment]:
    """Drop a parent when one of its own descendants also matched.

    Tagging both `2.2` and `2.2.2` says nothing the specific tag did not, and
    ancestor rollup already makes the leaf imply its parents for browsing.
    Keeping both would inflate coverage counts with tags that carry no
    information.
    """
    chosen = {a.code for a in assignments}
    return [
        a for a in assignments
        if not any(
            other != a.code and other.startswith(a.code + ".") for other in chosen
        )
    ]


def classify_resource(index: TopicIndex, resource, **kwargs) -> list[Assignment]:
    """Classify from whatever text a record has.

    Abstracts do most of the work; a title alone is the hard case and the
    scores reflect that honestly rather than being rescaled to look
    confident.
    """
    text = " ".join(
        part for part in (
            resource.title,
            resource.description,
            resource.abstract,
            " ".join(resource.authors or []) if False else "",
        ) if part
    )
    return index.classify(text, **kwargs)
