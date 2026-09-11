"""Reading statements out of a paper, as a process rather than an afternoon.

The first forty claims were extracted in one sitting by one model over six
papers, and a person rereading them afterwards found five that were facts
about the artifact rather than about the field — "contains more than 80
scenarios" — and five more that were the paper reporting somebody else's
result. An 11% waste rate and a 12% misattribution rate, both discovered by
hand, in a batch small enough to reread.

That does not survive being multiplied by sixteen. So the gates that caught
those problems by hand are mechanical here, and the ones that cannot be
mechanical are asked of the extractor directly rather than left to be noticed
later.

**What to extract, by type.** The five types are not equal work.

*Findings and positions are the product.* They are what a researcher comes
looking for — what has been shown, and what has been argued — and ten of the
first twelve asserted relations run between them. A paper's yield is its
primary count, not its statement count: Melting Pot gives three primaries
and two context, Building the Loop gives one and two.

*Method statements are a query dimension, not filler.* "Who has found this,
working that way" joins a subject on a finding to a technique on a method
statement. Which makes the tag on a method a different job from the tag on a
finding: **tag a method with the technique, not with the paper's subject.**
A method tagged with what the paper is about answers nothing that its
findings do not already answer, and the gate below catches the common case.

*Background is where attribution concentrates.* It is usually somebody
else's result, asserted without evidence and dating badly — so the OWN/OTHER
question is asked hardest here.

*Limitations are rare and worth hunting.* One in thirty-two across the first
six papers. They live in discussion sections rather than abstracts, and they
are the part a downstream reader is most likely to drop.

**Five gates, and only the last needs a model to have been honest.**

1. *The quote is in the paper.* `fulltext.verbatim` searches the fetched
   source for the quoted sentence. A quote that cannot be found was
   reconstructed from memory, and a reconstructed quote invites a reviewer to
   confirm something the paper never said. This is the load-bearing check and
   it is free.

2. *The claim is about the field, not the artifact.* A statement whose
   subject is the paper's own instrument — its scenario count, its run count,
   its metric names — can never match a researcher's proposition, which is
   what this layer is for. Asked of the extractor, and checked against a
   pattern for the shapes that recurred.

3. *Attribution is stated.* Own or reported, and if reported, whose. Asked at
   extraction rather than found by rereading, because rereading is what does
   not scale.

4. *A method is tagged with its technique.* Checked by comparing a method
   statement's tags against the tags on the same paper's findings and
   positions: a method carrying nothing but its paper's subject has been
   tagged for what the work is about rather than how it was done, which
   makes it invisible to the query methods exist to answer. Reported rather
   than refused — sometimes the technique genuinely is the subject, as when
   a paper's contribution is the mechanism itself.

5. *Concepts resolve, or are proposed properly.* A tag that does not exist
   fails loudly; a new term goes through the collision check like any other,
   which is what keeps a vocabulary from growing two names for one idea while
   nobody is looking.

What remains unmeasured is whether the paraphrase says what the quote says.
That is the reviewer's question and no gate here substitutes for it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .concepts import Vocabulary, similar_terms

# Shapes that recurred in the first pass, every one of them a fact about the
# instrument. Deliberately narrow: this rejects, so a false positive silently
# loses a real claim.
#
# It is a partial gate and the docstring should not pretend otherwise.
# Measured against the five cut by hand from the first batch, it catches the
# four with a countable or metric shape and misses "exploiter agents and a
# random agent bound the performance range on each test scenario" — which is
# artifact trivia by meaning and not by form, and no pattern narrow enough to
# be safe will find it. That one is the extractor's job, which is why the
# rule is also given in words.
ARTIFACT_SHAPED = re.compile(
    r"\b("
    r"contains (more than |over |at least )?\d"      # "contains 80 scenarios"
    r"|comprises \d|consists of \d"
    r"|was trained with \d|were trained with \d"     # "trained with 21 runs"
    r"|\d+ runs?\b|\d+ seeds?\b|\d+ epochs?\b"
    # "…is Melting Pot's primary evaluation metric", "…is measured as a
    # secondary metric". The possessive and the passive both appeared.
    r"|(is|are|was|were)\b[^.]{0,40}\b(primary|secondary)\b[^.]{0,20}\bmetrics?\b"
    r"|\bmeasured as [^.]{0,30}\bmetrics?\b"
    r")",
    re.I,
)


@dataclass
class Rejection:
    """A candidate statement that did not survive a gate, and which one."""

    gate: str
    detail: str
    text: str


@dataclass
class Checked:
    """What survived, and what did not, from one paper."""

    kept: list[dict] = field(default_factory=list)
    rejected: list[Rejection] = field(default_factory=list)
    new_concepts: list[str] = field(default_factory=list)
    subject_tagged_methods: list[str] = field(default_factory=list)
    """Method statements tagged for what the paper is about rather than how
    it was done. A warning, not a rejection."""

    @property
    def primaries(self) -> int:
        """Findings and positions kept. The real yield — a paper's statement
        count says how much was written down, this says how much of it is
        what anybody came for."""
        return sum(1 for c in self.kept
                   if c.get("claim_type") in ("finding", "position"))

    @property
    def waste(self) -> float:
        total = len(self.kept) + len(self.rejected)
        return len(self.rejected) / total if total else 0.0

    def summary(self) -> str:
        return (f"{len(self.kept)} kept ({self.primaries} primary), "
                f"{len(self.rejected)} rejected ({self.waste:.0%} waste)")


def looks_like_artifact_trivia(text: str) -> bool:
    """Whether a statement is about the paper's instrument rather than the field.

    "Melting Pot contains more than 80 unique test scenarios" is true, useful
    for reproducing the paper, and can never be the answer to "who has argued
    X". Five of the first forty-five were this shape.

    Catches four of those five. The fifth — "exploiter agents and a random
    agent bound the performance range on each test scenario" — is trivia by
    meaning rather than by form, and widening the pattern far enough to reach
    it would start rejecting real findings. A partial mechanical gate plus the
    rule stated to the extractor beats a greedy one that quietly deletes work.
    """
    return bool(ARTIFACT_SHAPED.search(text or ""))


def method_tagged_by_subject(candidates: list[dict]) -> list[str]:
    """Method statements carrying only their paper's subject.

    A method's tag answers "how was this done", and is joined against a
    finding's "what was shown" to answer "who found this, working that way".
    A method tagged with the paper's subject instead is invisible to that
    query — it says the same thing its findings already say, one type down.

    Reported rather than refused, because sometimes the technique is the
    subject: a paper whose contribution is the mechanism itself will
    legitimately tag both the same way.

    On the first six papers it flagged three of five method statements,
    which is high and is mostly telling you about the papers rather than
    about the tagging. These are conceptual works — a taxonomy of trust
    models, a definition of dynamic evaluation, a construct called
    Artificial Organisational Intelligence — and for a paper whose
    contribution *is* the mechanism, subject and technique genuinely
    coincide. An empirical paper separates them cleanly: Melting Pot's
    method is scenario generation and its findings are about evaluation,
    and that one came back clean.

    So read a flag as a question rather than a defect. The one it caught
    that was a real mistake was Knowledge Organisation Infrastructure,
    tagged with the legibility it serves rather than the schema-sharing it
    does — invisible to "who has done this, working that way", which is the
    query methods exist to answer.
    """
    subject_tags: set[str] = set()
    for candidate in candidates:
        if candidate.get("claim_type") in ("finding", "position"):
            subject_tags.update(candidate.get("concept_tags") or [])

    flagged = []
    for candidate in candidates:
        if candidate.get("claim_type") != "method":
            continue
        tags = set(candidate.get("concept_tags") or [])
        if tags and tags <= subject_tags:
            flagged.append(candidate.get("text", "?"))
    return flagged


def check(candidates: list[dict], *, sections=None, vocabulary: Vocabulary | None = None,
          allow_new_concepts: bool = True) -> Checked:
    """Put extracted statements through the gates.

    `candidates` are dicts as the extractor produced them: text, quote,
    standalone, claim_type, attribution, attributed_to, concept_tags.
    `sections` is the parsed full text, when there is any — without it the
    verbatim gate cannot run and is skipped rather than faked.
    """
    from .fulltext import verbatim

    result = Checked()
    result.subject_tagged_methods = method_tagged_by_subject(candidates)
    seen_texts: set[str] = set()

    for candidate in candidates:
        text = (candidate.get("text") or "").strip()
        quote = (candidate.get("quote") or "").strip()

        if not text or not quote:
            result.rejected.append(Rejection("empty", "no text or no quote", text or "?"))
            continue

        # The same assertion twice is one claim, and a duplicate inflates
        # coverage while adding nothing linkable.
        key = re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()
        if key in seen_texts:
            result.rejected.append(Rejection("duplicate", "same assertion already kept", text))
            continue

        if looks_like_artifact_trivia(text):
            result.rejected.append(Rejection(
                "artifact", "about the paper's own instrument, not the field", text))
            continue

        if sections:
            where = verbatim(quote, sections)
            if not where:
                result.rejected.append(Rejection(
                    "not-in-source",
                    "the quoted sentence is not in the paper — reconstructed, not read",
                    text))
                continue
            candidate.setdefault("extracted_from", where)

        attribution = (candidate.get("attribution") or "").strip()
        if attribution not in ("own", "other"):
            result.rejected.append(Rejection(
                "attribution", f"attribution must be own or other, got {attribution!r}", text))
            continue
        if attribution == "other" and not (candidate.get("attributed_to") or "").strip():
            result.rejected.append(Rejection(
                "attribution", "reported from prior work but does not say whose", text))
            continue

        if vocabulary is not None:
            tags = candidate.get("concept_tags") or []
            unknown = vocabulary.unknown(tags)
            if unknown and not allow_new_concepts:
                result.rejected.append(Rejection(
                    "concept", f"tags do not resolve: {unknown}", text))
                continue
            for tag in unknown:
                # A proposed term goes through the same collision check as one
                # added by hand. Growing a vocabulary at extraction speed is
                # exactly when two names for one idea appear.
                close = similar_terms(tag.replace("-", " "), vocabulary)
                if close:
                    result.rejected.append(Rejection(
                        "concept",
                        f"new tag {tag!r} collides with {close[0][1].id!r} — "
                        "use that, or name yours so the difference is in the label",
                        text))
                    break
                if tag not in result.new_concepts:
                    result.new_concepts.append(tag)
            else:
                seen_texts.add(key)
                result.kept.append(candidate)
            continue

        seen_texts.add(key)
        result.kept.append(candidate)

    return result
