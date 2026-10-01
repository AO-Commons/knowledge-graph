"""Reading statements out of a paper, as a process rather than an afternoon.

The first forty claims were drafted in one sitting by one model over six
papers, and a person rereading them afterwards found five that were facts
about the artifact rather than about the field — "contains more than 80
scenarios" — and five more that were the paper reporting somebody else's
result. An 11% waste rate and a 12% misattribution rate, both discovered by
hand, in a batch small enough to reread.

That does not survive being multiplied by sixteen. So the gates that caught
those problems by hand are mechanical here, and the ones that cannot be
mechanical are asked of the drafting model directly rather than left to be noticed
later.

**What to draft, by type.** The seven types are not equal work.

*Findings and positions are the product.* They are what a researcher comes
looking for — what has been shown, and what has been argued — and ten of the
first twelve asserted relations run between them. A paper's yield is its
primary count, not its statement count. Drafted from their abstracts and
conclusions, Melting Pot gave three primaries and two context statements and
Building the Loop one and two. Read in full, they give nine and four, and eight
and twelve.

*Method statements are a query dimension, not filler.* "Who has found this,
working that way" joins a subject on a finding to a technique on a method
statement. Which makes the tag on a method a different job from the tag on a
finding: **tag a method with the technique, not with the paper's subject.**
A method tagged with what the paper is about answers nothing that its
findings do not already answer, and the gate below catches the common case.

*A term the paper introduces is a definition, not a method.* "We introduce
X: the capacity for ..." names something without saying how anything is
done, and filed as a method it answers "working that way" for a paper that
never worked that way. Tag a definition with the concept it defines; a term
the paper coins is a new concept, and its definition is where the concept
comes from.

*A system the paper builds on is background.* When the paper describes
infrastructure somebody else designed, even a co-author's firm, that is
prior work and its attribution says whose. The paper's own method is what
the authors did with it.

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
   what this layer is for. Asked of the drafting model, and checked against a
   pattern for the shapes that recurred.

3. *Attribution is stated.* Own or reported, and if reported, whose. Asked while
   drafting rather than found by rereading, because rereading is what does
   not scale.

4. *A method is tagged with its technique.* Checked by comparing a method
   statement's tags against the tags on the same paper's findings and
   positions: a method carrying nothing but its paper's subject has been
   tagged for what the work is about rather than how it was done, which
   makes it invisible to the query methods exist to answer. Reported rather
   than refused — sometimes the technique genuinely is the subject, as when
   a paper's contribution is the mechanism itself.

0. *One spelling.* Statements and tags are normalized to American spelling
   before any of the gates run, because a tag is a slug and
   `organisational-knowledge-legibility` would otherwise enter as a second
   concept beside `organizational-`, connected to nothing. Quotes keep the
   paper's spelling, which is the point of a quote.

5. *Concepts resolve, or are proposed properly.* A tag that does not exist
   fails loudly; a new term goes through the collision check like any other,
   which is what keeps a vocabulary from growing two names for one idea while
   nobody is looking.

**Six checks, reported rather than refused.** An audit of the first seven
papers against their full texts (evals/results/2026-10-01-statement-audit.md)
found the same five failures in nearly every paper. Each check below reads form
for meaning, so each is partial and each says so; a flag is a question for a
person, and "this one is right" is an answer.

- *A method tagged with its paper's subject* — gate 4 above.
- *A paraphrase surer than its quote.* The quote hedges, the text does not.
- *A finding quoted as argued.* The quote says "we argue", "plausible", "should".
- *A term introduced and not typed definition.*
- *A tag on more than half of a paper's statements.*
- *A substantial body section with no statement.* The commonest failure of
  all: statements drawn from the abstract and conclusion, and none from the
  sections where the work was done.

`scripts/check_statements.py` runs them over statements already held.

What remains unmeasured is whether the paraphrase says what the quote says.
That is the reviewer's question and no gate here substitutes for it. The
brief a drafting model is given is docs/reading-a-paper.md.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .concepts import Vocabulary, similar_terms
from .spelling import to_american

# Shapes that recurred in the first pass, every one of them a fact about the
# instrument. Deliberately narrow: this rejects, so a false positive silently
# loses a real claim.
#
# It is a partial gate and the docstring should not pretend otherwise.
# Measured against the five cut by hand from the first batch, it catches the
# four with a countable or metric shape and misses "exploiter agents and a
# random agent bound the performance range on each test scenario" — which is
# artifact trivia by meaning and not by form, and no pattern narrow enough to
# be safe will find it. That one is the drafting model's job, which is why the
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



# Open questions are the one kind of statement authors mark for you.
#
# Every other type has to be recognized: a finding looks like a sentence. An
# open question is almost always announced — "remains an open question", "we
# leave to future work", "it is not yet known whether" — because an author
# stating one wants it found and worked on. That makes this the opposite of
# `ARTIFACT_SHAPED`, which rejects: this one *finds*, and so it is allowed to
# be generous. A false positive costs a passage a drafting model glances at and
# discards; a false negative costs a problem nobody in the corpus knows is
# open.
#
# Measured against the passages Emergent Mind quotes for its own open
# problems, the markers below catch both of the two on the page I checked —
# "remains an open question" and "genuinely open" — which is the shape to
# expect: the marker is a stock phrase and the question around it is not.
GAP_MARKERS = re.compile(
    r"\b("
    # `open` is a busy word in this literature — open source, open weights,
    # open-ended, an open specification, open to interpretation. A blacklist
    # of the nouns that can follow it would never finish; the distinction is
    # grammatical instead. The sense that means unresolved is predicative:
    # the sentence ends there, or carries on with the question itself.
    # "A2A is an open specification" is the attributive use and is not a gap;
    # "whether it survives is genuinely open." is.
    r"(remains?|is|are|stays?) (an? )?(genuinely |largely |still |very much )?open\b"
    r"(?=\s*[.,;:)\]]|\s+(whether|how|if|why|to what|as to)\b|\s*$)"
    r"|open (question|problem|challenge|issue)s?\b"
    r"|(remains?|is|are) (still )?(unclear|unknown|unanswered|unresolved|untested|unexplored)\b"
    r"|(it|this) is not (yet )?(known|clear|understood|established)\b"
    r"|(we|authors?) (leave|defer)s? .{0,40}\bto future work\b"
    r"|(is|are|remains?) (an )?(important |promising )?(direction|avenue)s? for future work\b"
    r"|future work (should|will|must|could)\b"
    r"|(has|have) (not )?yet to be (shown|established|demonstrated|answered|tested)\b"
    r"|no (accepted|established|agreed|standard|existing) (benchmark|method|approach|measure|definition)\b"
    r"|(little|no) (prior |existing )?(work|research|evidence) (has |exists)"
    r"|(warrants?|requires?|calls for) further (study|investigation|research)\b"
    r"|(an|the) important (open )?(question|problem) (is|remains)\b"
    r")",
    re.I,
)


@dataclass
class Passage:
    """Somewhere an author said something is unresolved."""

    section: str
    """Which section it was found in. A gap stated in a conclusion is the
    authors' own; one in an introduction is usually about the field."""
    marker: str
    """The phrase that flagged it, so a reader can see why this was surfaced."""
    text: str

    def __str__(self) -> str:
        return f"[{self.section}] …{self.text}…  ({self.marker!r})"


def gap_passages(sections, *, window: int = 320) -> list[Passage]:
    """Where in a paper somebody said a question is open.

    Not a drafting model. This hands back passages for one to read, which is the
    whole point of separating them: the drafting model decides what the statement
    is and writes the quote, and this only says where to look. Abstracts are
    skipped — an abstract that mentions an open question is selling the
    paper's contribution, and the question itself is stated properly further
    down.
    """
    found: list[Passage] = []
    for section in sections or []:
        kind = getattr(section, "kind", "") or ""
        if kind == "abstract":
            continue
        text = getattr(section, "text", "") or ""
        for match in GAP_MARKERS.finditer(text):
            start = max(0, match.start() - window)
            end = min(len(text), match.end() + window)
            found.append(Passage(
                section=kind or getattr(section, "heading", "") or "other",
                marker=match.group(0),
                text=" ".join(text[start:end].split()),
            ))
    return found

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
    hedges_dropped: list[str] = field(default_factory=list)
    """Statements whose paraphrase is surer than their quote. See
    `hedges_dropped`."""
    argued_findings: list[str] = field(default_factory=list)
    """Findings whose own quote says they were argued. See `argued_findings`."""
    undeclared_definitions: list[str] = field(default_factory=list)
    """Statements that introduce a term and are typed as something else."""
    blanket_tags: list[str] = field(default_factory=list)
    """Tags on most of one paper's statements. See `blanket_tags`."""
    unread_sections: list[str] = field(default_factory=list)
    """Body sections of the paper that no statement was drawn from. See
    `unread_sections`."""

    @property
    def warnings(self) -> dict[str, list[str]]:
        """Everything reported rather than refused, by the check that raised it."""
        return {name: found for name, found in (
            ("method tagged with its paper's subject", self.subject_tagged_methods),
            ("paraphrase surer than its quote", self.hedges_dropped),
            ("typed finding, quoted as argued", self.argued_findings),
            ("introduces a term, not typed definition", self.undeclared_definitions),
            ("tag on most of the paper's statements", self.blanket_tags),
            ("body section with no statement", self.unread_sections),
        ) if found}

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
    rule stated to the drafting model beats a greedy one that quietly deletes work.
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
    which is high and was mostly telling you about the types rather than
    the tagging. These are conceptual works — a taxonomy of trust models, a
    definition of dynamic evaluation, a construct called Artificial
    Organizational Intelligence — and two of the three flags were not
    methods at all but definitions, which are tagged with what they define
    and so trip this gate every time. That type now exists and the gate
    does not look at it. An empirical paper separates subject and technique
    cleanly: Melting Pot's method is scenario generation and its findings
    are about evaluation, and that one came back clean.

    So read a flag as a question rather than a defect, and ask first
    whether the statement is a method at all. Knowledge Organization
    Infrastructure was flagged too, and was retagged at the time to
    `shared-schemas-for-agentic-organization-data` — the opposite of what
    it does, since KOI joins systems *without* a shared schema. It was
    never this paper's method. It is a system the paper builds on, which
    makes it background, and a wrong type invites a wrong tag because the
    tagger is answering a question the statement was never asking.
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


# How an author says how sure they are. The audit of the first seven papers
# found the same failure in every one of them: "seems to require" became
# "requires", "it is then plausible that" became a fact, "can be governed"
# became "are governed". Each was a summary saying more than its source,
# which is the thing an author is most entitled to object to.
HEDGES = re.compile(
    r"\b(may|might|can|could|would|seems?|appears?|suggests?|suggesting|"
    r"plausibl[ey]|likely|possibl[ey]|potentially|perhaps|arguably|"
    r"tends? to|in principle|expect(s|ed)?)\b", re.I)


def hedges_dropped(candidates: list[dict]) -> list[str]:
    """Statements whose quote hedges and whose paraphrase does not.

    Deliberately crude: it asks only whether *any* hedge survived, so a
    paraphrase that swaps "seems to" for "may" passes, and one that keeps a
    stray "can" while dropping "plausibly" passes too. What it catches is
    the common case, where every qualifier went at once. `must` in the
    quote and `should` in the text is caught as well, because softening an
    author is as much a misreading as hardening one.
    """
    flagged = []
    for candidate in candidates:
        quote, text = candidate.get("quote") or "", candidate.get("text") or ""
        if HEDGES.search(quote) and not HEDGES.search(text):
            flagged.append(text)
        elif (re.search(r"\bmust\b", quote, re.I) and re.search(r"\bshould\b", text, re.I)
              and not re.search(r"\bmust\b", text, re.I)):
            flagged.append(text)
    return flagged


# A finding is something this work observed or measured. These are the
# words of somebody arguing, and a quote that contains them is the author
# saying so.
ARGUED = re.compile(
    r"\b(we (argue|posit|propose|contend|believe|recommend|suggest)|"
    r"it is (then )?plausible|this suggests|we expect|should|must|ought to)\b", re.I)


def argued_findings(candidates: list[dict]) -> list[str]:
    """Statements typed `finding` whose own quote marks them as argued.

    The distinction the type system exists for. Conceptual papers have no
    findings in this sense and their conclusions are still worth holding,
    as positions. Partial: "our study finds that no single mechanism
    suffices" is the conclusion of an argument and uses the word *finds*,
    which no pattern can see through.
    """
    return [c.get("text", "?") for c in candidates
            if c.get("claim_type") == "finding" and ARGUED.search(c.get("quote") or "")]


DEFINES = re.compile(
    r"\b(we (introduce|define|call|term|coin)|is defined as|we use the term|"
    r"what we call|by this we mean|refers to|is what we|we posit that \w+ \w+ are|"
    r"is (the )?one (in which|where|whose))\b", re.I)


def undeclared_definitions(candidates: list[dict]) -> list[str]:
    """Statements that introduce a term and are typed as something else.

    "We introduce Artificial Organizational Intelligence: the capacity for
    ..." was a method for a month, and "a dynamic evaluation is the one in
    which ..." until the audit. Partial, like every check here that reads form for
    meaning: "we identify and compare six distinct trust models" introduces a
    typology without saying so.
    """
    return [c.get("text", "?") for c in candidates
            if c.get("claim_type") != "definition" and DEFINES.search(c.get("quote") or "")]


def blanket_tags(candidates: list[dict], *, share: float = 0.5, at_least: int = 5) -> list[str]:
    """Tags on most of one paper's statements.

    A tag on nearly everything a paper says tells its statements apart from
    nothing, and if no other paper carries it, connects them to nothing.
    Building the Loop had one concept on ten of eleven statements, filed under
    a topic the paper never discusses, and the derived topics built on it
    reported a gain that was not there. More than half, because the next
    worst was seven of twelve. Below five statements a paper can
    legitimately be about one thing.
    """
    if len(candidates) < at_least:
        return []
    counts: dict[str, int] = {}
    for candidate in candidates:
        for tag in set(candidate.get("concept_tags") or []):
            counts[tag] = counts.get(tag, 0) + 1
    return [f"{tag} ({n} of {len(candidates)})" for tag, n in sorted(counts.items())
            if n / len(candidates) > share]


# Body sections where a paper says what it did and what it found. A paper
# can have an introduction with nothing new in it; a results section with no
# statement means the results were read from the abstract's account of them.
BODY = ("method", "results", "discussion", "other")


def unread_sections(candidates: list[dict], sections, *, min_chars: int = 1500) -> list[str]:
    """Substantial body sections that no statement was drawn from.

    The finding that held across every paper audited: statements came from
    the abstract, the introduction and the conclusion, and the sections
    where the work was actually done carried none. Building the Loop's
    method, architecture and deployment, Melting Pot's experiments,
    Vending-Bench's trace analyses, and the whole argument of two
    conceptual papers. A reader asking what a paper found was getting the
    paper's summary of itself.

    Reported per section rather than refused, because a section can be
    rightly empty: an instrument's specification, a related-work survey
    whose claims belong to the papers it surveys.
    """
    quotes = [re.sub(r"\s+", " ", c.get("quote") or "").strip() for c in candidates]
    empty = []
    for section in sections or []:
        if section.kind not in BODY or len(section.text) < min_chars:
            continue
        haystack = re.sub(r"\s+", " ", section.text)
        if not any(q and q in haystack for q in quotes):
            empty.append(section.heading or section.kind)
    return empty


def check(candidates: list[dict], *, sections=None, vocabulary: Vocabulary | None = None,
          allow_new_concepts: bool = True) -> Checked:
    """Put drafted statements through the gates.

    `candidates` are dicts as the drafting model produced them: text, quote,
    standalone, claim_type, attribution, attributed_to, concept_tags.
    `sections` is the parsed full text, when there is any — without it the
    verbatim gate cannot run and is skipped rather than faked.
    """
    from .fulltext import verbatim

    # One spelling, before anything is compared against anything.
    #
    # A tag is a slug: a statement proposing `organisational-knowledge-legibility`
    # would pass the vocabulary check as a brand new concept, sitting beside the
    # `organizational-` one, joined to nothing. The collision guard would not
    # catch it either, since by its own measure the two labels are the same term
    # spelled two ways — which is exactly the case it treats as one idea. So it
    # is settled here, before the tag is looked up, and the statement is just
    # written the same way every time. The quote is not touched: it is checked
    # verbatim against the paper, and our spelling is not the paper's business.
    for candidate in candidates:
        for field in ("text", "standalone"):
            if isinstance(candidate.get(field), str):
                candidate[field] = to_american(candidate[field])
        tags = candidate.get("concept_tags")
        if isinstance(tags, list):
            candidate["concept_tags"] = [
                to_american(tag) if isinstance(tag, str) else tag for tag in tags]

    result = Checked()
    result.subject_tagged_methods = method_tagged_by_subject(candidates)
    result.hedges_dropped = hedges_dropped(candidates)
    result.argued_findings = argued_findings(candidates)
    result.undeclared_definitions = undeclared_definitions(candidates)
    result.blanket_tags = blanket_tags(candidates)
    result.unread_sections = unread_sections(candidates, sections)
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
                # added by hand. Growing a vocabulary at reading speed is
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
                candidate.setdefault("review_status", "machine-checked")
                result.kept.append(candidate)
            continue

        seen_texts.add(key)
        # Passing the gates is a fact about the statement and belongs on it.
        # Recording it here rather than by hand keeps the claim that every
        # kept statement was mechanically checked true by construction.
        candidate.setdefault("review_status", "machine-checked")
        result.kept.append(candidate)

    return result
