"""Parse the v3 taxonomy markdown into Topic records.

The taxonomy file is the source of truth, so this parser is deliberately
forgiving about presentation and strict about meaning.

**Hierarchy comes from the codes, not from the nesting.** `2.2.1` is a child
of `2.2` because of its code, regardless of whether the file expresses that
with heading levels, indented bullets, or box-drawing characters. That choice
is what lets the same parser survive the taxonomy being reformatted, and it
means a mis-indented line is a cosmetic problem rather than a silent
restructuring of the graph.

Recognized line shapes, all equivalent:

    ## 2.2.1 Least privilege for agent principals
    - 2.2.1 Least privilege for agent principals
    │   └── 2.2.1 Least privilege for agent principals
    **2.2.1** Least privilege for agent principals
    2.2.1. Least privilege for agent principals
"""

from __future__ import annotations

import re
from pathlib import Path

from ..models import Topic, TopicStatus, UsageMode

# The 16 top-level sections, used to check that a parse found the taxonomy
# rather than some other numbered list in the document.
TOP_LEVEL_SECTIONS: dict[str, str] = {
    "1": "Definitional and conceptual foundations",
    "2": "Authority architecture",
    "3": "Organizational architecture",
    "4": "Human oversight and control",
    "5": "Multi-agent dynamics",
    "6": "Agent lifecycle and personnel analogues",
    "7": "Knowledge, memory, and institutional continuity",
    "8": "Resource allocation by agents",
    "9": "Verification, attestation, and audit",
    "10": "Security and adversarial dynamics",
    "11": "Failure modes",
    "12": "Legal accountability and liability",
    "13": "Economics of agentic organizations",
    "14": "Evaluation, assurance, and evidence",
    "15": "Borrowed foundations",
    "16": "Empirical study and methods",
}

CODING_SCHEME_SECTION = "11"
"""Section 11's topics are failure codes, not shelves. An incident normally
carries several at once."""

BORROWED_SECTION = "15"
"""Section 15 points into adjacent mature fields. It stays shallow on
purpose — the point is to reference those literatures, not re-ingest them."""

# Box-drawing and bullet decoration that carries no meaning for us.
_DECORATION = re.compile(r"^[\s>#*\-•─-╿|`]+")
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_TOPIC_LINE = re.compile(r"^(?P<code>\d+(?:\.\d+)*)[.)]?\s+(?P<title>\S.*?)\s*$")
_FENCE = re.compile(r"^\s*(```|~~~)")
_TRAILING_LINK = re.compile(r"\s*\[[^\]]*\]\([^)]*\)\s*$")
_SECTION_HEADING = re.compile(r"^##\s+(?P<text>\S.*?)\s*$")
_INDENTED_BULLET = re.compile(r"^\s+[-*]\s+(?P<text>\S.*?)\s*$")


class TaxonomyError(ValueError):
    """The taxonomy did not load deterministically."""


def _clean(line: str) -> str:
    # Bold markers come off first. Stripping decoration first would consume
    # the asterisks of `- **2.2.2** Title` along with the bullet, leaving a
    # code glued to a stray `**` that no longer parses.
    line = _BOLD.sub(r"\1", line.rstrip())
    line = _DECORATION.sub("", line)
    return line.strip()


def _clean_title(title: str) -> str:
    title = _BOLD.sub(r"\1", title)
    title = _TRAILING_LINK.sub("", title)
    # Trailing punctuation from headings and list items carries no meaning.
    return title.strip().rstrip(":;,").strip()


def parse_taxonomy(text: str, version: str = "v3") -> list[Topic]:
    """Turn taxonomy markdown into Topic records, in document order.

    A code appearing more than once — common when a file shows an outline and
    then expands it — keeps its first title. Later repeats are ignored rather
    than treated as conflicts, since an outline entry is usually the same
    heading abbreviated.
    """
    topics: dict[str, Topic] = {}
    in_fence = False
    current: Topic | None = None

    for raw in text.splitlines():
        if _FENCE.match(raw):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        cleaned = _clean(raw)

        # The taxonomy proper ends at the first unnumbered `##` section —
        # "Facet axes", "Exclusion register", "Notes on use". Those are
        # reference material, and the codes quoted inside them (15.1, 12.6.3)
        # are cross-references, not topic definitions.
        heading = _SECTION_HEADING.match(raw)
        if heading and topics and not _TOPIC_LINE.match(cleaned):
            break

        match = _TOPIC_LINE.match(cleaned)
        if match:
            code = match.group("code")
            title = _clean_title(match.group("title"))
            if not title:
                continue
            if code in topics:
                current = topics[code]
                continue

            section = code.split(".", 1)[0]
            current = Topic(
                code=code,
                title=title,
                taxonomy_version=version,
                usage_mode=(
                    UsageMode.CODING_SCHEME
                    if section == CODING_SCHEME_SECTION
                    else UsageMode.NAVIGATION
                ),
                status=TopicStatus.ACTIVE,
            )
            topics[code] = current
            continue

        # An indented bullet under a numbered topic is a subpoint: real
        # content that the source never gave a code.
        bullet = _INDENTED_BULLET.match(raw)
        if bullet and current is not None:
            text_ = _clean_title(bullet.group("text"))
            if text_ and text_ not in current.subpoints:
                current.subpoints.append(text_)

    return sorted(topics.values(), key=lambda t: [int(p) for p in t.code.split(".")])


def validate_topics(topics: list[Topic], *, strict_sections: bool = True) -> list[str]:
    """Return the reasons this parse should not be trusted.

    Empty means the taxonomy loaded deterministically.
    """
    problems: list[str] = []
    by_code = {topic.code: topic for topic in topics}

    if not topics:
        return ["no topics found — check the file's numbering format"]

    # Every non-top-level topic needs its parent present, or browsing has a
    # hole and ancestor rollup silently drops resources.
    for topic in topics:
        if topic.parent_code and topic.parent_code not in by_code:
            problems.append(
                f"{topic.code} ({topic.title!r}) has no parent {topic.parent_code}"
            )

    found_sections = {t.code: t.title for t in topics if t.depth == 0}
    missing = set(TOP_LEVEL_SECTIONS) - set(found_sections)
    unexpected = set(found_sections) - set(TOP_LEVEL_SECTIONS)

    if strict_sections:
        for code in sorted(missing, key=int):
            problems.append(
                f"top-level section {code} ({TOP_LEVEL_SECTIONS[code]!r}) not found"
            )
        for code in sorted(unexpected, key=int):
            problems.append(
                f"unexpected top-level section {code} ({found_sections[code]!r}); "
                "V1 does not add top-level sections"
            )

    # Section 11 is the failure coding scheme; if its topics come back as
    # navigation the multi-tagging behaviour downstream is wrong.
    for topic in topics:
        expected = (
            UsageMode.CODING_SCHEME
            if topic.top_level_section == CODING_SCHEME_SECTION
            else UsageMode.NAVIGATION
        )
        if topic.usage_mode is not expected:
            problems.append(
                f"{topic.code}: usage_mode {topic.usage_mode.value}, expected {expected.value}"
            )

    return problems


def load_taxonomy(
    path: str | Path, version: str = "v3", *, strict: bool = True
) -> list[Topic]:
    """Parse a taxonomy file, refusing to return a parse that isn't sound."""
    path = Path(path)
    if not path.exists():
        raise TaxonomyError(
            f"taxonomy file not found: {path}. The taxonomy is the source of "
            "truth — nothing downstream can be built without it."
        )

    topics = parse_taxonomy(path.read_text(encoding="utf-8"), version=version)
    problems = validate_topics(topics, strict_sections=strict)
    if problems and strict:
        raise TaxonomyError(
            f"{path} did not load cleanly ({len(problems)} problem(s)):\n  "
            + "\n  ".join(problems)
        )
    return topics
