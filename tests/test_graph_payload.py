"""The payload the 3D graph reads.

Mostly one concern: a link pointing at a node that is not in the graph makes
the layout engine throw rather than draw, and the only symptom is a blank
canvas on a page nobody has open.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from build_graph import build  # noqa: E402


@pytest.fixture(scope="module")
def graph():
    return build()


def test_every_link_lands_on_a_node(graph):
    """The check that matters. `build` raises rather than writing a broken
    payload, so this pins that the real corpus stays whole."""
    known = {node["id"] for node in graph["nodes"]}
    dangling = [link for link in graph["links"]
                if link["source"] not in known or link["target"] not in known]
    assert dangling == []


def test_node_ids_are_unique(graph):
    ids = [node["id"] for node in graph["nodes"]]
    assert len(ids) == len(set(ids))


def test_each_kind_of_thing_is_present(graph):
    kinds = {node["kind"] for node in graph["nodes"]}
    assert kinds == {"section", "topic", "resource", "claim"}


def test_the_edge_kinds_stay_distinguishable(graph):
    """A citation, a computed similarity and a machine-extracted statement are
    three different kinds of assertion. Collapsing them into one edge type
    would let a viewer read a resemblance as a fact."""
    kinds = {link["kind"] for link in graph["links"]}
    assert {"cites", "similar", "claim", "about"} <= kinds


def test_a_similarity_carries_its_score(graph):
    """Unscored, a computed edge is indistinguishable from a stated one."""
    similar = [link for link in graph["links"] if link["kind"] == "similar"]
    assert similar and all("score" in link for link in similar)


def test_claims_know_which_record_makes_them(graph):
    claims = [node for node in graph["nodes"] if node["kind"] == "claim"]
    resources = {node["id"] for node in graph["nodes"] if node["kind"] == "resource"}
    assert claims and all(claim["of"] in resources for claim in claims)


def test_topics_carry_how_much_is_filed_under_them(graph):
    """Drives both the drawn size and the default view, which hides the empty
    ones — 465 of 567 leaves are empty and together they bury the records."""
    topics = [node for node in graph["nodes"] if node["kind"] in ("topic", "section")]
    assert all("held" in node for node in topics)
    assert any(node["held"] for node in topics)


def test_the_payload_is_deterministic():
    """Written into a published site, so a rebuild from unchanged inputs should
    not produce a diff."""
    assert build() == build()
