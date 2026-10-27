"""The MIRA projection: that it says what we meant, and admits what it cannot.

The omission report is tested as hard as the graph. A projection that quietly
drops a third of the corpus and reports nothing would pass a schema validator
perfectly, which is exactly why conformance alone is not the test.
"""
from __future__ import annotations

import json

import pytest

from ao_commons_kg.export.mira import BASE, CLASS_OF, build_graph, write_mira
from ao_commons_kg.models import (
    Claim, ClaimType, ConfidenceClass, Question, Relationship, RelationType,
    Resource,
)


def _paper(rid="resource:arxiv:1234.5678", **kw):
    return Resource(
        id=rid, resource_type="preprint",
        title=kw.pop("title", "A paper about agents"),
        arxiv_id=kw.pop("arxiv_id", "1234.5678"), **kw,
    )


def _claim(cid="claim:arxiv:1234.5678:1", kind=ClaimType.POSITION, **kw):
    return Claim(
        id=cid, resource_id=kw.pop("resource_id", "resource:arxiv:1234.5678"),
        text=kw.pop("text", "Agents cannot be held to a role."),
        quote=kw.pop("quote", "we find that agents cannot be held to a role"),
        claim_type=kind, **kw,
    )


def _nodes(doc, typed):
    out = []
    for n in doc["@graph"]:
        t = n.get("@type")
        t = t if isinstance(t, list) else [t]
        if typed in t:
            out.append(n)
    return out


class TestTheProjection:
    def test_a_paper_becomes_a_source_document(self):
        doc, _ = build_graph(resources=[_paper()])
        docs = _nodes(doc, "SourceDocument")
        assert len(docs) == 1
        assert docs[0]["title"] == "A paper about agents"

    def test_a_doi_wins_the_identifier(self):
        # Somebody else's graph can join on a DOI and cannot join on ours.
        doc, _ = build_graph(resources=[_paper(doi="10.1000/xyz")])
        assert _nodes(doc, "SourceDocument")[0]["@id"] == "https://doi.org/10.1000/xyz"

    def test_a_statement_carries_its_kind_and_its_mira_class(self):
        doc, _ = build_graph(resources=[_paper()], claims=[_claim()])
        claims = _nodes(doc, "Claim")
        assert len(claims) == 1
        assert f"{BASE}/ns#kind/position" in claims[0]["@type"]

    def test_a_finding_is_evidence_and_names_its_paper(self):
        # Evidence is the only class with a slot for the document it came
        # from, which is why a finding is the one kind whose provenance MIRA
        # can state outright.
        doc, _ = build_graph(
            resources=[_paper()], claims=[_claim(kind=ClaimType.EVIDENCE)])
        evidence = _nodes(doc, "Evidence")
        assert len(evidence) == 1
        assert evidence[0]["sourceDocument"] == "https://arxiv.org/abs/1234.5678"

    def test_a_method_is_a_protocol(self):
        doc, _ = build_graph(
            resources=[_paper()], claims=[_claim(kind=ClaimType.PROTOCOL)])
        assert len(_nodes(doc, "Protocol")) == 1

    def test_every_kind_has_a_mira_class(self):
        # A kind added to the corpus with no mapping here would otherwise
        # raise at build time, on a Friday.
        assert set(CLASS_OF) == set(ClaimType)

    def test_a_quote_becomes_an_anchor_in_the_papers_container(self):
        doc, _ = build_graph(resources=[_paper()], claims=[_claim()])
        item = _nodes(doc, "Item")[0]
        assert item["content"] == "we find that agents cannot be held to a role"
        containers = _nodes(doc, "Container")
        assert item["has_container"] == containers[0]["@id"]
        # and the claim reaches it
        assert _nodes(doc, "Claim")[0]["description"] == item["@id"]

    def test_a_container_carries_nothing_else(self):
        # Its shape permits no properties at all. Adding a title here is the
        # obvious thing to do and it fails validation.
        doc, _ = build_graph(resources=[_paper()], claims=[_claim()])
        assert set(_nodes(doc, "Container")[0]) == {"@id", "@type"}

    def test_an_edge_is_reified_rather_than_a_property(self):
        # A supports property on a Claim fails the closed shape; a reified
        # claim touches no shape at all.
        doc, _ = build_graph(
            resources=[_paper()],
            claims=[_claim(kind=ClaimType.GAP)],
            questions=[Question(id="question:x", text="Can they?")],
            relationships=[Relationship(
                source_id="claim:arxiv:1234.5678:1", target_id="question:x",
                relation=RelationType.ADDRESSES,
                confidence_class=ConfidenceClass.INFERRED)],
        )
        edges = _nodes(doc, "addresses")
        assert len(edges) == 1
        assert edges[0]["source"] == f"{BASE}/claims/claim:arxiv:1234.5678:1"
        assert edges[0]["destination"] == f"{BASE}/problems/question:x"
        assert "RelationInstance" in edges[0]["@type"]
        assert not any("addresses" in n for n in _nodes(doc, "Claim"))


class TestItAdmitsWhatItCannotSay:
    def test_a_tool_is_not_called_a_document(self):
        # SourceDocument is_a CreativeWork. Typing a deployment as one to get
        # it into the file would put a false claim in the data.
        tool = Resource(id="resource:tool:x", resource_type="code-tool",
                        title="A framework")
        doc, report = build_graph(resources=[tool])
        assert _nodes(doc, "SourceDocument") == []
        assert report.omitted_nodes["resource:code-tool"] == 1

    def test_an_edge_with_no_mira_term_is_counted_not_dropped(self):
        doc, report = build_graph(
            resources=[_paper()], claims=[_claim()],
            relationships=[Relationship(
                source_id="resource:arxiv:1234.5678",
                target_id="claim:arxiv:1234.5678:1",
                relation=RelationType.MAKES_CLAIM,
                confidence_class=ConfidenceClass.EXTRACTED)],
        )
        assert report.omitted_edges["MAKES_CLAIM"] == 1
        assert any("MAKES_CLAIM" in n for n in report.notes)

    def test_a_dangling_edge_is_counted_apart_from_an_unmapped_one(self):
        # One is MIRA's limit and one is our bug, and a single number would
        # hide the second behind the first.
        doc, report = build_graph(
            claims=[_claim(kind=ClaimType.GAP)],
            relationships=[Relationship(
                source_id="claim:arxiv:1234.5678:1", target_id="question:missing",
                relation=RelationType.ADDRESSES,
                confidence_class=ConfidenceClass.INFERRED)],
        )
        assert report.omitted_edges["ADDRESSES:dangling"] == 1

    def test_the_unhomed_fields_are_named_not_counted(self):
        _, report = build_graph(resources=[_paper()], claims=[_claim()])
        unhomed = report.to_dict()["unhomed_claim_fields"]
        assert "attribution" in unhomed
        assert "standalone" in unhomed
        # each one says why, so the report can be read by somebody who did not
        # write it
        assert all(len(why) > 40 for why in unhomed.values())


class TestItIsReproducible:
    def test_two_runs_of_one_corpus_match(self, tmp_path):
        # The release checksums are only worth having if this holds.
        parts = dict(resources=[_paper()], claims=[_claim()])
        a, _ = write_mira(tmp_path / "a", **parts)
        b, _ = write_mira(tmp_path / "b", **parts)
        assert a.read_text() == b.read_text()

    def test_no_clock_is_read(self, tmp_path):
        # built_at is passed in or absent, never taken from the clock, or the
        # byte-identical property above would be false by a second.
        path, _ = write_mira(tmp_path / "a", resources=[_paper()])
        assert "created" not in json.loads(path.read_text())["@graph"][0]


class TestIdentifiers:
    @pytest.mark.parametrize("name,slug", [
        ("Dario Amodei", "dario-amodei"),
        ("Joon-Sung Park", "joon-sung-park"),
        ("Sheer El Showk", "sheer-el-showk"),
        ("  Odd   Spacing  ", "odd-spacing"),
    ])
    def test_a_byline_becomes_something_that_can_be_an_iri(self, name, slug):
        # A space in an IRI is not an IRI: a validator resolves it against the
        # file it was parsed from and reports a type error three steps from
        # the cause.
        from ao_commons_kg.export.mira import _slug
        assert _slug(name) == slug

    def test_two_spellings_of_one_name_are_one_account(self):
        doc, report = build_graph(resources=[
            _paper(rid="r:1", arxiv_id="1111.1111", authors=["Joon Sung Park"]),
            _paper(rid="r:2", arxiv_id="2222.2222", authors=["Joon-Sung Park"]),
        ])
        accounts = _nodes(doc, "UserAccount")
        people = [a for a in accounts if "/people/" in a["@id"]]
        assert len(people) == 1
        assert all(isinstance(a["accountName"], str) for a in accounts)
        assert any("byline pairs" in n for n in report.notes)
