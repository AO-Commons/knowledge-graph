"""The README's figures table is rewritten by a script, and only the table."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import update_readme_stats as stats  # noqa: E402

COUNTS = {"records": 5, "read": 2, "claims": 9, "reviewed": 1, "questions": 3, "topics": 7}


def test_only_the_marked_span_changes():
    text = f"intro\n\n{stats.START}\n| old |\n{stats.END}\n\nrest\n"
    out = stats.rewrite(text, COUNTS, 4)
    assert out.startswith("intro\n\n") and out.endswith("\n\nrest\n")
    assert "| old |" not in out
    assert "| Records | 5 " in out and "7, in 4 sections" in out


def test_a_readme_without_markers_fails_loudly():
    with pytest.raises(SystemExit):
        stats.rewrite("no markers here", COUNTS, 4)


def test_the_real_readme_has_the_markers():
    text = (REPO / "README.md").read_text(encoding="utf-8")
    assert text.count(stats.START) == 1 and text.count(stats.END) == 1
