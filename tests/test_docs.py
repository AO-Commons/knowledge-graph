"""The Docs tab: what the project is, said on the project's own page.

Two things are worth testing about a documentation page. That its numbers come
from the corpus rather than from whoever last edited the prose — a page that
states its own figures is the thing people check the figures against, so it
is the last place that should be able to drift. And that it did not break the
four screens it sits beside.
"""

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def page():
    return (ROOT / "site" / "template.html").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def built():
    return (ROOT / "site" / "index.html").read_text(encoding="utf-8")


