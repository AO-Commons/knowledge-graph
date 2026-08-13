"""Reading a paper rather than its abstract.

Both bugs these guard against were silent: one filed every introduction as an
unrecognized section, the other returned zero sections for a paper that plainly
had thirty-five. Neither raised anything — they just quietly produced less
text, which is the failure mode that survives longest in a pipeline whose
output nobody counts.
"""

import pytest

from ao_commons_kg.fulltext import Section, classify_heading, parse, verbatim

PAPER = """
<html><head><style>.x{color:red}</style></head><body>
<header><nav><svg><path d="M1 2"></path></svg>Skip navigation</nav></header>
<div class="ltx_authors"><span class="ltx_personname">Helena Rong</span></div>
<div class="ltx_abstract"><h6 class="ltx_title ltx_title_abstract">Abstract</h6>
<p class="ltx_p">We show that agents with budget caps overspend less.</p></div>
<section class="ltx_section"><h2 class="ltx_title ltx_title_section">1 Introduction</h2>
<div class="ltx_para"><p class="ltx_p">Agents increasingly hold real authority.</p></div>
</section>
<section class="ltx_section"><h2 class="ltx_title ltx_title_section">4 Experiments</h2>
<div class="ltx_para"><p class="ltx_p">Overspending fell from <math><mi>x</mi></math>27% to 3%.</p></div>
<figure><p class="ltx_p">Figure 1: a caption nobody claims anything in.</p></figure>
</section>
<section class="ltx_appendix"><h2 class="ltx_title ltx_title_section">Appendix A</h2>
<div class="ltx_para"><p class="ltx_p">Proof of Lemma 3.</p></div>
</section>
<section class="ltx_bibliography"><p class="ltx_p">[1] Someone else entirely.</p></section>
</body></html>
"""


@pytest.fixture
def sections():
    return parse(PAPER)


class TestHeadings:
    def test_a_numbered_introduction_is_an_introduction(self):
        """A character class of roman numerals ate the I of Introduction, so
        every intro in the corpus filed as `other` and its claims went
        unread. Nothing raised; there was simply less text."""
        assert classify_heading("1 Introduction") == "introduction"

    def test_roman_numerals_are_still_stripped(self):
        assert classify_heading("IV. Results") == "results"

    def test_subsection_numbers_are_stripped(self):
        assert classify_heading("4.4 Secondary evaluation metrics") == "results"

    def test_authors_own_words_are_matched_loosely(self):
        """Headings are written by authors, not to a schema."""
        assert classify_heading("5 Experiments and Evaluation") == "results"
        assert classify_heading("Limitations and threats to validity") == "discussion"

    def test_an_unknown_heading_is_other_rather_than_a_guess(self):
        assert classify_heading("7 What does Melting Pot evaluate?") == "other"


class TestParse:
    def test_the_abstract_is_found_under_an_h6(self, sections):
        """LaTeXML sets the abstract heading as h6. Looking only at h1-h4
        lost the abstract on every paper that used one."""
        assert sections[0].kind == "abstract"
        assert "budget caps overspend less" in sections[0].text

    def test_sections_come_back_in_document_order(self, sections):
        assert [s.kind for s in sections] == ["abstract", "introduction", "results"]

    def test_the_appendix_and_bibliography_are_cut(self, sections):
        text = " ".join(s.text for s in sections)
        assert "Proof of Lemma" not in text
        assert "Someone else entirely" not in text

    def test_navigation_and_author_blocks_do_not_become_text(self, sections):
        text = " ".join(s.text for s in sections)
        assert "Skip navigation" not in text and "Helena Rong" not in text

    def test_figure_captions_are_dropped(self, sections):
        """A caption is not a claim the paper makes, and it reads like one."""
        assert "a caption nobody claims" not in " ".join(s.text for s in sections)

    def test_maths_is_removed_so_a_quote_can_still_match(self, sections):
        """A sentence with a rendered formula spliced through it can never be
        matched back to the source, and an unmatched quote is the one failure
        this design cannot absorb."""
        results = [s for s in sections if s.kind == "results"][0]
        assert results.text == "Overspending fell from 27% to 3%."

    def test_claim_bearing_is_a_property_of_the_kind(self, sections):
        assert all(s.claim_bearing for s in sections)
        assert not Section("related", "3 Related work", "Others did things.").claim_bearing


class TestVerbatim:
    def test_a_real_quote_returns_the_section_it_came_from(self, sections):
        assert verbatim("Agents increasingly hold real authority.", sections) == "introduction"

    def test_line_wrapping_does_not_break_a_match(self, sections):
        """LaTeXML wraps mid-sentence; whitespace is the only thing relaxed."""
        assert verbatim("Agents increasingly\n  hold real authority.", sections) == "introduction"

    def test_a_quote_the_paper_does_not_contain_is_refused(self, sections):
        """The load-bearing check. A quote that cannot be found means the model
        wrote it from memory, and a reviewer would be confirming something the
        paper never said."""
        assert verbatim("Agents reliably exceed their budgets.", sections) is None

    def test_a_near_miss_is_still_a_miss(self, sections):
        """No fuzzy matching: a paraphrase that drifted into the quote field is
        exactly what this is for."""
        assert verbatim("Agents increasingly hold authority.", sections) is None
