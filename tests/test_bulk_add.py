"""Adding a reading list in one go.

The duplicate rules are the whole risk. A bulk path that is laxer than the
one-at-a-time path is how a corpus fills with near-duplicates nobody notices,
so these check that the same paper written three ways collapses to one — which
it did not, at first.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from bulk_add import main, read_list  # noqa: E402


class TestReadList:
    def test_bare_identifiers(self):
        assert read_list("2502.14143\n10.1145/3770291.3770333") == [
            ("2502.14143", ""), ("10.1145/3770291.3770333", "")]

    def test_markdown_bullets_and_numbered_lists(self):
        """A list someone already wrote should not have to be reformatted."""
        text = "- https://arxiv.org/abs/2502.14143\n1. 2511.03434\n* 10.1145/x.y"
        assert [i for i, _ in read_list(text)] == [
            "https://arxiv.org/abs/2502.14143", "2511.03434", "10.1145/x.y"]

    def test_comments_and_blank_lines_are_skipped(self):
        assert read_list("# a heading\n\n2502.14143\n// a note") == [("2502.14143", "")]

    def test_trailing_topic_codes_are_read(self):
        assert read_list("2502.14143 [14.2, 5.2]") == [("2502.14143", "14.2, 5.2")]

    def test_trailing_punctuation_is_trimmed(self):
        assert read_list("2502.14143,") == [("2502.14143", "")]

    def test_the_identifier_is_found_inside_a_citation(self):
        line = "Hammond et al., Multi-Agent Risks, https://arxiv.org/abs/2502.14143"
        assert read_list(line)[0][0] == "https://arxiv.org/abs/2502.14143"


class TestDuplicates:
    """The rule: keep the original, in both directions."""

    def run(self, tmp_path, capsys, lines):
        listing = tmp_path / "papers.txt"
        listing.write_text(lines, encoding="utf-8")
        main([str(listing), "--offline"])
        return capsys.readouterr().out

    def test_one_paper_written_three_ways_collapses_to_the_first(self, tmp_path, capsys):
        """`10.48550/arXiv.<id>` is the same paper as `arxiv.org/abs/<id>`.
        The corpus check knew that through the canonical key; the in-file check
        did not until it was made to use the same key."""
        out = self.run(tmp_path, capsys,
                       "2608.10218\nhttps://arxiv.org/abs/2608.10218\n10.48550/arXiv.2608.10218\n")
        assert "2 repeated inside the file" in out
        assert "first one kept" in out

    def test_something_already_in_the_library_is_kept_as_it_is(self, tmp_path, capsys):
        out = self.run(tmp_path, capsys, "2107.06857\n")
        assert "already in the library, kept as they are" in out
        assert "resource:arxiv:2107.06857" in out

    def test_a_duplicate_is_reported_rather_than_passed_over(self, tmp_path, capsys):
        """A list that turns out to be half duplicates is worth knowing about."""
        out = self.run(tmp_path, capsys, "2107.06857\n2107.06857\n")
        assert "repeated inside the file" in out

    def test_nothing_is_written_without_being_asked(self, tmp_path, capsys):
        out = self.run(tmp_path, capsys, "2107.06857\n")
        assert "Nothing written" in out


class TestFailures:
    def test_an_unparseable_line_is_reported_and_the_rest_continue(self, tmp_path, capsys):
        """One bad row in a list of forty must not end the run."""
        listing = tmp_path / "papers.txt"
        listing.write_text("not-an-identifier\n2107.06857\n", encoding="utf-8")
        main([str(listing), "--offline"])
        out = capsys.readouterr().out
        assert "could not be added" in out
        assert "resource:arxiv:2107.06857" in out

    def test_an_empty_list_says_so(self, tmp_path, capsys):
        listing = tmp_path / "papers.txt"
        listing.write_text("# nothing but a comment\n", encoding="utf-8")
        assert main([str(listing), "--offline"]) == 1


def test_the_site_points_at_the_instructions():
    """The Add tab is where somebody with twenty papers finds out there is a
    better way than pasting for an hour."""
    page = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    assert "docs/bulk-add.md" in page
    assert (ROOT / "docs" / "bulk-add.md").exists()
