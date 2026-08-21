"""The page's scorer and this one must agree.

The Add tab scores a paper that is not in the corpus yet, against the index
built here. That is the one thing the server cannot precompute, so the scoring
logic genuinely exists twice — in Python and in the page's JavaScript.

Constants are injected now, so they cannot drift. Logic still can, and it
drifts silently: a query built from terms the index does not hold scores zero
against them and simply returns worse suggestions. Nothing throws, nothing
looks broken, and a contributor adding a paper gets quietly worse topics.

So this runs the page's own tokenizer under Node and compares it, string for
string, with the Python one.
"""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from ao_commons_kg.classify import tokenize

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "site" / "index.html"

# Real text, including the shapes that break naive tokenizers: hyphens,
# capitals, digits inside words, and the stopwords the index drops.
SAMPLES = [
    "Agents operating under per-task budget caps exceeded their allocation in 3% of runs",
    "Multi-Agent Reinforcement Learning with Melting Pot",
    "Permissions, permission scopes and least privilege for autonomous agents",
    "Evaluating evaluation: continuous assurance in production",
    "spend caps, rate limits, and cumulative budgets",
    "A2A, AP2, ERC-8004 and the agentic web",
    "",
    "the and of a an",
]


def browser_tokenizer() -> str:
    """Lift the tokenizer and its constants out of the built page."""
    page = PAGE.read_text(encoding="utf-8")
    data = re.search(r'<script type="application/json" id="graph">(.*?)</script>', page, re.S)
    scoring = json.loads(data.group(1).replace("<\\/", "</"))["scoring"]

    functions = []
    for name in ("stem", "tokens"):
        found = re.search(rf"\n  function {name}\(.*?\n  }}\n", page, re.S)
        assert found, f"could not find {name}() in the page"
        functions.append(found.group(0))

    return f"""
const SCORING = {json.dumps(scoring)};
const STOP = new Set(SCORING.stop);
const WORD = new RegExp(SCORING.word, "g");
{"".join(functions)}
const samples = {json.dumps(SAMPLES)};
console.log(JSON.stringify(samples.map(tokens)));
"""


@pytest.mark.skipif(not shutil.which("node"), reason="node is not installed")
def test_the_page_tokenizes_exactly_as_python_does(tmp_path):
    script = tmp_path / "parity.js"
    script.write_text(browser_tokenizer(), encoding="utf-8")
    result = subprocess.run(["node", str(script)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr

    from_browser = json.loads(result.stdout)
    from_python = [tokenize(text) for text in SAMPLES]
    from_python = [terms + [f"{a}_{b}" for a, b in zip(terms, terms[1:])]
                   for terms in from_python]

    for sample, browser, python in zip(SAMPLES, from_browser, from_python):
        assert browser == python, f"the two disagree on {sample!r}"


@pytest.mark.skipif(not shutil.which("node"), reason="node is not installed")
def test_the_page_takes_its_constants_from_python(tmp_path):
    """Not a copy that happens to match — the same values, injected."""
    from ao_commons_kg.classify import _SUFFIXES, STOP, TopicIndex

    page = PAGE.read_text(encoding="utf-8")
    data = re.search(r'<script type="application/json" id="graph">(.*?)</script>', page, re.S)
    scoring = json.loads(data.group(1).replace("<\\/", "</"))["scoring"]

    assert set(scoring["stop"]) == set(STOP)
    assert tuple(scoring["suffixes"]) == _SUFFIXES
    assert scoring["k1"] == TopicIndex.K1
    assert scoring["b"] == TopicIndex.B


def test_the_page_does_not_hardcode_the_constants_any_more():
    """A literal creeping back is how this returns."""
    page = PAGE.read_text(encoding="utf-8")
    assert 'const STOP = new Set(("a an and' not in page
    assert "const K1 = 1.2, B = 0.6;" not in page
