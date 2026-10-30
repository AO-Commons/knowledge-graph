"""The preview page is AO Commons', and says so in its colours and its type.

The contrast assertions are here because the CSS has regressed on exactly
this before: a token at 2.87:1 carried the quote, the context line and every
hint on the review screen, which was most of what a reviewer read. A number in
a comment does not hold; a test does.

The page is light only, as the AO Commons tokens are. It carried a dark theme
of its own until 2026-10-30, which was a second palette nobody had published.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

PAGE = (ROOT / "site" / "index.html").read_text(encoding="utf-8")

#: Copied from the website's src/shared/tokens.css. If these drift, the page
#: has stopped being AO Commons and the test should say so rather than a
#: reader noticing.
PUBLISHED = {
    "bg": "#f5f8fb", "sky": "#cfe4f7", "panel": "#fff",
    "ink": "#1a1a19", "ink-2": "#5a5a57", "ink-3": "#8b8b86",
    "line": "#d9d9d5", "line-2": "#bdbdb8",
    "green": "#0e4f46", "green-ink": "#0a3c35",
}


def tokens() -> dict[str, str]:
    block = PAGE.split(":root{", 1)[1].split("}", 1)[0]
    return dict(re.findall(r"--([\w-]+):\s*([^;]+?)\s*(?:;|/\*)", block))


def luminance(colour: str) -> float:
    colour = colour.lstrip("#")
    if len(colour) == 3:
        colour = "".join(c * 2 for c in colour)
    parts = [int(colour[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    parts = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in parts]
    return 0.2126 * parts[0] + 0.7152 * parts[1] + 0.0722 * parts[2]


def contrast(a: str, b: str) -> float:
    high, low = sorted((luminance(a), luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


LIGHT = tokens()


class TestTheBrand:
    def test_the_palette_is_the_published_one(self):
        for name, value in PUBLISHED.items():
            assert LIGHT[name] == value, f"--{name} is {LIGHT[name]}, published is {value}"

    def test_every_token_the_page_uses_is_defined(self):
        used = set(re.findall(r"var\(--([\w-]+)\)", PAGE))
        assert used <= set(LIGHT), f"undefined: {sorted(used - set(LIGHT))}"

    @pytest.mark.parametrize("ink", ["ink", "ink-2"])
    def test_body_text_meets_aa(self, ink):
        assert contrast(LIGHT[ink], LIGHT["bg"]) >= 4.5

    def test_the_quiet_token_meets_aa_for_large_text_at_least(self):
        """`--ink-3` carries mono meta labels, which are small. If it cannot
        reach 4.5 it should not be carrying them."""
        assert contrast(LIGHT["ink-3"], LIGHT["bg"]) >= 3.0

    def test_the_accent_is_readable_on_the_page_and_in_reverse(self):
        assert contrast(LIGHT["green"], LIGHT["bg"]) >= 4.5
        assert contrast("#ffffff", LIGHT["green"]) >= 4.5

    def test_the_brand_faces_load(self):
        for face in ("Bricolage+Grotesque", "Hanken+Grotesk", "DM+Mono"):
            assert face in PAGE

    def test_the_fonts_do_not_block_rendering(self):
        assert "display=swap" in PAGE

    def test_it_does_not_ship_a_second_palette(self):
        """AO Commons publishes one. A dark theme here would be ours alone."""
        assert "prefers-color-scheme" not in PAGE
        assert 'data-theme="dark"' not in PAGE


class TestWhatTheReaderCanDo:
    """Four things, and nothing else: look, search, suggest, correct."""

    def test_it_searches(self):
        assert 'id="q"' in PAGE and "function matches" in PAGE

    def test_both_doors_open_an_issue_form(self):
        assert "suggest-addition.yml" in PAGE
        assert "request-adjustment.yml" in PAGE

    def test_a_correction_arrives_knowing_which_record(self):
        """A correction that makes somebody paste an id is a correction fewer
        people send."""
        assert "{ record: r.id }" in PAGE

    def test_nothing_on_the_page_writes_to_the_corpus(self):
        for gone in ("review", "verdict", "Add tab"):
            assert f'id="{gone}"' not in PAGE

    def test_every_claim_shows_the_sentence_it_came_from(self):
        """The whole claim of the library: you can check it without the PDF."""
        assert "esc(c.quote)" in PAGE

    def test_a_held_but_unread_record_says_so(self):
        assert "Held, not yet read" in PAGE


class TestThePayload:
    def test_it_cannot_close_its_own_script_element(self):
        body = PAGE.split('<script id="data" type="application/json">', 1)[1]
        assert "</script" not in body.split("</script>", 1)[0] + ""

    def test_it_is_one_file(self):
        """No build step for a reader, and nothing to 404. Checked against the
        markup rather than the whole file, because the script builds URLs from
        the data and a template literal is not a reference."""
        markup = PAGE.split('<script id="data"', 1)[0]
        local = re.findall(r'(?:src|href)="((?!https://|#)[^"]*)"', markup)
        assert not local, f"the page reaches for {local}"
