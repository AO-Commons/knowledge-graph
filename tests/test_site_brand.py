"""The site's brand tokens, and the contributors view.

The contrast assertions are here because the CSS has regressed on exactly this
before: a `--faint` at 2.87:1 carried the quote, the context line and every
hint on the review screen, which is most of what a reviewer reads. A number in
a comment does not hold; a test does.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

TEMPLATE = (ROOT / "site" / "template.html").read_text(encoding="utf-8")
BUILT = (ROOT / "site" / "index.html").read_text(encoding="utf-8")


def tokens(selector: str) -> dict[str, str]:
    block = TEMPLATE.split(selector + " {", 1)[1].split("}", 1)[0]
    return dict(re.findall(r"--([\w-]+):\s*([^;]+?)\s*(?:;|/\*)", block))


def luminance(colour: str) -> float:
    colour = colour.lstrip("#")
    parts = [int(colour[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    parts = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in parts]
    return 0.2126 * parts[0] + 0.7152 * parts[1] + 0.0722 * parts[2]


def contrast(a: str, b: str) -> float:
    high, low = sorted((luminance(a), luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


LIGHT = tokens(":root")
DARK = tokens(':root[data-theme="dark"]')


class TestTheBrand:
    def test_both_themes_define_the_same_tokens(self):
        """A token defined only in light falls back to the light value in dark,
        which is how a dark page ends up with one white panel on it."""
        assert set(LIGHT) == set(DARK), set(LIGHT) ^ set(DARK)

    def test_every_token_the_css_uses_is_defined(self):
        """`--accent-ink` was referenced twice and defined nowhere, so the chip
        text silently fell back to inherit. CSS does not warn about this."""
        used = set(re.findall(r"var\(--([\w-]+)\)", TEMPLATE))
        defined = set(LIGHT) | set(re.findall(r"^\s+--([\w-]+):", TEMPLATE, re.M))
        assert not used - defined, f"undefined tokens: {sorted(used - defined)}"

    @pytest.mark.parametrize("theme", ["light", "dark"])
    @pytest.mark.parametrize("ink", ["ink", "muted", "faint"])
    @pytest.mark.parametrize("ground", ["paper", "card", "sunk"])
    def test_text_meets_aa_on_every_surface(self, theme, ink, ground):
        palette = LIGHT if theme == "light" else DARK
        ratio = contrast(palette[ink], palette[ground])
        assert ratio >= 4.5, f"{theme}: {ink} on {ground} is {ratio:.2f}:1"

    @pytest.mark.parametrize("theme", ["light", "dark"])
    def test_the_accent_is_readable(self, theme):
        palette = LIGHT if theme == "light" else DARK
        assert contrast(palette["accent"], palette["paper"]) >= 4.5
        assert contrast(palette["on-accent"], palette["accent"]) >= 4.5

    def test_the_brand_palette_is_the_published_one(self):
        """Light is aocommons.org's own, so the two sites do not drift apart.
        `faint` is deliberately not the brand's --ink-3: see the contrast test."""
        assert LIGHT["paper"] == "#f5f8fb"   # brand --bg
        assert LIGHT["sky"] == "#cfe4f7"     # brand --sky
        assert LIGHT["ink"] == "#1a1a19"     # brand --ink
        assert LIGHT["accent"] == "#0e4f46"  # brand --green

    def test_the_brand_faces_load(self):
        for face in ("Bricolage+Grotesque", "Hanken+Grotesk", "DM+Mono"):
            assert face in TEMPLATE
        assert "fonts.googleapis.com" in TEMPLATE

    def test_the_fonts_do_not_block_rendering(self):
        """A stylesheet in the head blocks paint. The corpus should be readable
        before the brand arrives, not after."""
        assert 'media="print" onload="this.media=' in TEMPLATE

    def test_dark_mode_survives(self):
        """The brand has no dark mode and the site has always had one. Dropping
        it to match the brand would be matching a page that does not exist."""
        assert ':root[data-theme="dark"]' in TEMPLATE
        assert "prefers-color-scheme: dark" in TEMPLATE


class TestThePeopleView:
    def test_its_styles_are_scoped(self):
        """The same hazard the docs block has: a class name this view chose was
        already doing a job elsewhere, and CSS does not warn."""
        block = TEMPLATE.split("/* ---------- people ---------- */")[1] \
                        .split("/* ---- Docs ---")[0]
        for rule in re.findall(r"(?m)^  (\.[\w.\- ]+?) \{", block):
            assert rule.startswith(".people"), f"{rule} is not scoped to the people view"

    def test_no_class_it_uses_is_already_styled_by_docs(self):
        """Scoping my own rules is not enough. The view's wrapper is
        `class="docs people"`, so a `.docs .x` rule anywhere reaches an element
        this view calls `x` — and `.docs .who` already existed, uppercasing
        every contributor name. CSS does not warn, and the rule that wins is
        whichever set the property, not whichever is more specific.
        """
        # Deliberately shared with Docs: this view wants the reading styles
        # that page already defines, and inheriting them is the point. Anything
        # NOT on this list sharing a name with a `.docs` rule is an accident.
        BORROWED = {"lede", "body", "caption"}
        block = TEMPLATE.split("function renderPeople()")[1].split("\n  function ")[0]
        mine = set(re.findall(r'className: "([\w\- ]+)"', block))
        names = {part for value in mine for part in value.split()
                 if part not in ("docs", "people") and part not in BORROWED}
        for name in sorted(names):
            assert f".docs .{name} " not in TEMPLATE and f".docs .{name}{{" not in TEMPLATE, (
                f".docs .{name} already exists and will reach this view")

    def test_the_sidebar_is_not_left_showing(self):
        """The paper list belongs to Explore. It is not wrong on this screen,
        it is answering a question nobody reading it is asking."""
        assert 'mode === "docs" || mode === "people"' in TEMPLATE

    def test_the_tab_is_in_the_masthead_and_wired(self):
        assert '<button id="mode-people"' in TEMPLATE
        assert '"mode-people").addEventListener' in TEMPLATE
        assert "people: renderPeople" in TEMPLATE

    def _payload(self):
        return json.loads(re.search(
            r'"contributions":(\{.*?"authors":\[.*?\]\})', BUILT).group(1))

    def test_the_page_agrees_with_the_ledger(self):
        """The view is derived, so it must not disagree with the file it is
        derived from."""
        ledger = json.loads(
            (ROOT / "data" / "contributions.json").read_text(encoding="utf-8"))
        payload = self._payload()
        workers = [p for p in ledger["people"] if any(k != "wrote" for k in p["counts"])]
        authors = [p for p in ledger["people"] if list(p["counts"]) == ["wrote"]]
        assert len(payload["workers"]) == len(workers)
        assert len(payload["authors"]) == len(authors)
        assert len(payload["machines"]) == len(ledger["machines"])

    def test_every_worker_keeps_their_counts(self):
        ledger = json.loads(
            (ROOT / "data" / "contributions.json").read_text(encoding="utf-8"))
        by_name = {p["contributor"]: p["counts"] for p in ledger["people"]}
        for worker in self._payload()["workers"]:
            assert worker["counts"] == by_name[worker["contributor"]]

    def test_authors_and_workers_are_never_summed(self):
        """Writing a paper the library holds and judging a statement in it are
        different in kind. One list would make 1,600 names look like the whole
        story and four look like a rounding error."""
        payload = self._payload()
        names = {w["contributor"] for w in payload["workers"]}
        assert not names & {a["name"] for a in payload["authors"]}

    def test_machines_are_listed_apart(self):
        """`machines admit, people judge` is the line this project draws, and
        the page has to draw it too."""
        assert "machines" in self._payload()
        block = TEMPLATE.split("/* ---------- people ---------- */")[1] \
                        .split("/* ---- Docs ---")[0]
        assert ".people .maker.machine" in block

    def test_it_computes_no_score(self):
        """String literals are stripped first: the view's own copy says there
        are no scores here, and a test that cannot tell prose from code would
        fail on the sentence explaining why it passes."""
        block = TEMPLATE.split("function renderPeople()")[1].split("\n  function ")[0]
        code = re.sub(r'"[^"]*"|\'[^\']*\'|//.*', " ", block).lower()
        for word in ("score", "rank", "points", "leaderboard", "weight"):
            assert word not in code, f"the view computes a {word}"

    def test_contributors_are_not_ordered_by_volume(self):
        block = TEMPLATE.split("function renderPeople()")[1].split("\n  function ")[0]
        assert "sort((a, b) => b." not in block
