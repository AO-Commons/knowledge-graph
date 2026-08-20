"""The taxonomy must load deterministically — that is Milestone 1's whole bar.

The real v3 file is checked in, so these run against it rather than only
against a fixture. A parser that works on a tidied sample and not on the
actual source would be worse than no parser.
"""

from pathlib import Path

import pytest

from ao_commons_kg.models import UsageMode
from ao_commons_kg.taxonomy import (
    TOP_LEVEL_SECTIONS,
    TaxonomyError,
    load_taxonomy,
    parse_taxonomy,
    validate_topics,
)

REPO = Path(__file__).resolve().parent.parent
TAXONOMY = REPO / "taxonomy" / "agentic-org-research-library-taxonomy-v3.md"
FIXTURE = REPO / "tests" / "fixtures" / "taxonomy-sample.md"


@pytest.fixture(scope="module")
def topics():
    return load_taxonomy(TAXONOMY)


def test_real_taxonomy_loads_without_problems(topics):
    assert validate_topics(topics) == []
    # The tree is two levels now — the leaf layer was demoted to notes when it
    # turned out to take 7% of filings while forcing a choice on every record.
    # The guard still earns its place: a format miss shows up as far fewer than
    # this, so the shape is asserted rather than just the count.
    assert len(topics) > 90, "a small parse means a format miss"
    assert sum(1 for t in topics if t.depth == 0) == 16
    assert sum(1 for t in topics if t.depth == 1) == 87


def test_all_sixteen_sections_present(topics):
    sections = {t.code: t.title for t in topics if t.depth == 0}
    assert set(sections) == set(TOP_LEVEL_SECTIONS)


def test_no_topic_is_orphaned(topics):
    """Ancestor rollup silently drops resources if a parent is missing."""
    codes = {t.code for t in topics}
    assert [t.code for t in topics if t.parent_code and t.parent_code not in codes] == []


def test_codes_are_the_hierarchy(topics):
    for topic in topics:
        if topic.depth:
            assert topic.parent_code == topic.code.rsplit(".", 1)[0]
        assert topic.top_level_section == topic.code.split(".", 1)[0]


def test_section_11_is_a_coding_scheme(topics):
    """Section 11 nodes are failure codes; an incident carries several."""
    eleven = [t for t in topics if t.top_level_section == "11"]
    assert eleven, "section 11 should not be empty"
    assert all(t.usage_mode is UsageMode.CODING_SCHEME for t in eleven)
    others = [t for t in topics if t.top_level_section != "11"]
    assert all(t.usage_mode is UsageMode.NAVIGATION for t in others)


def test_unnumbered_subpoints_are_kept(topics):
    """They are the most specific phrasing in the file and carry no codes.

    Dropping them would lose exactly the strings candidate-topic retrieval
    most wants to match on.
    """
    # Far more of them since the demotion: every former leaf title is now a
    # note on its subsection, which is what keeps the vocabulary searchable
    # after the codes went away.
    assert sum(len(t.subpoints) for t in topics) >= 400
    agency = next(t for t in topics if t.code == "1.2")
    assert "Moral hazard without self-interest" in agency.subpoints
    assert "Principal-agent theory where the agent is literally artificial" in agency.subpoints


def test_reference_sections_are_not_parsed_as_topics(topics):
    """Facet axes, the exclusion register, and the closing notes are not
    taxonomy, and the codes quoted inside them are cross-references."""
    titles = {t.title.lower() for t in topics}
    assert "facet axes" not in titles
    assert "exclusion register" not in titles
    assert "notes on use" not in titles
    # The register mentions 15.1 and 12.6.3 in prose; those topics should
    # come from their real definitions, not from the table.
    assert next(t for t in topics if t.code == "15.1").title != "Reason"


def test_ancestors_roll_up(topics):
    """Checked on the tree as it is, and on a code shaped like the leaves it no
    longer has — the roll-up has to keep working if a third level ever earns
    its way back in, and there is nothing in the file to exercise that now."""
    subsection = next(t for t in topics if t.depth == 1)
    assert subsection.ancestor_codes() == [subsection.code.split(".")[0]]

    from ao_commons_kg.models import Topic

    # depth is derived from the code, not passed in.
    leaf = Topic(code="5.1.2", title="A leaf, hypothetically",
                 taxonomy_version="v3", parent_code="5.1", top_level_section="5")
    assert leaf.depth == 2
    assert leaf.ancestor_codes() == ["5", "5.1"]


def test_ids_are_stable_and_database_independent(topics):
    topic = next(t for t in topics if t.code == "2.2")
    assert topic.id == "topic:2.2"


def test_parser_tolerates_every_line_style():
    """Headings, bullets, bold codes, and box-drawing all mean the same thing."""
    parsed = parse_taxonomy(FIXTURE.read_text(encoding="utf-8"))
    codes = {t.code for t in parsed}
    for code in ("1", "2", "2.2", "2.2.1", "2.2.2", "2.2.3", "2.3.1", "11.3.4"):
        assert code in codes, f"{code} not parsed"
    assert next(t for t in parsed if t.code == "2.2.2").title == (
        "Capability tokens and scoped credentials"
    )
    # Inside a fenced block, the same lines must be ignored, not double-counted.
    assert sum(1 for t in parsed if t.code == "2.2.1") == 1
    # A trailing markdown link is decoration, not part of the title.
    assert next(t for t in parsed if t.code == "15.1").title == "Organizational theory"


def test_missing_file_is_a_clear_error(tmp_path):
    with pytest.raises(TaxonomyError, match="source of truth"):
        load_taxonomy(tmp_path / "nope.md")


def test_a_bad_parse_refuses_to_load(tmp_path):
    """Strict loading exists so a format change fails loudly instead of
    producing a half-empty graph."""
    partial = tmp_path / "partial.md"
    partial.write_text("## 1. Definitional and conceptual foundations\n- 1.1 Something\n")
    with pytest.raises(TaxonomyError, match="not found"):
        load_taxonomy(partial)


def test_orphan_is_reported():
    orphaned = parse_taxonomy("- 4.7.2 A leaf with no parent anywhere\n")
    assert any("no parent 4.7" in problem for problem in validate_topics(orphaned))


def test_every_alias_points_at_a_live_code(topics):
    """An alias on a code that no longer exists is silent: retrieval ignores it
    and the search box never offers it, so the words a researcher would type
    stop working with nothing to show that they have.

    This caught `14.5.5` still keyed after the topic moved to `15.6`.
    """
    import yaml
    from pathlib import Path

    path = Path(__file__).resolve().parent.parent / "taxonomy" / "aliases.yaml"
    aliases = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    codes = {t.code for t in topics}
    assert not [code for code in aliases if code not in codes]
