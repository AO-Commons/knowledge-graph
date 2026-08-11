"""Releases must be reproducible.

Published checksums are only meaningful if the same inputs produce the same
bytes, and a diff between two releases is only readable if ordering doesn't
churn.
"""

import json

from ao_commons_kg.export import write_release
from ao_commons_kg.models import ConfidenceClass, Entity, RelationType, Relationship, Resource, Topic


def build(tmp_path, version="v0.1.0"):
    topics = [
        Topic(code="2", title="Authority architecture", taxonomy_version="v3"),
        Topic(code="2.2", title="Permissioning", taxonomy_version="v3"),
    ]
    resources = [
        Resource(id="resource:openalex:W2", resource_type="paper", title="Second"),
        Resource(id="resource:openalex:W1", resource_type="paper", title="First",
                 taxonomy_topics=["2.2"], facets={"artifact_type": "preprint"}),
    ]
    entities = [Entity(id="entity:capability-token", entity_type="approach",
                       name="Capability token")]
    edges = [
        Relationship("resource:openalex:W1", "resource:openalex:W2", RelationType.CITES),
        Relationship("resource:openalex:W1", "topic:2.2", RelationType.TAGGED_WITH,
                     confidence_class=ConfidenceClass.INFERRED, confidence_score=0.8),
        Relationship("resource:openalex:W2", "resource:openalex:W1",
                     RelationType.SIMILAR_TO, method="co-citation", score=0.31),
    ]
    return write_release(tmp_path, version=version, topics=topics, resources=resources,
                         entities=entities, relationships=edges)


def test_release_has_the_expected_artifacts(tmp_path):
    out = build(tmp_path)
    names = {p.name for p in out.iterdir()}
    assert names == {"nodes.jsonl", "relationships.jsonl", "taxonomy.json",
                     "metadata.json", "checksums.txt"}


def test_rebuilding_produces_identical_bytes(tmp_path):
    """Without this the published checksums mean nothing."""
    first = (build(tmp_path / "a") / "nodes.jsonl").read_bytes()
    second = (build(tmp_path / "b") / "nodes.jsonl").read_bytes()
    assert first == second


def test_nodes_are_sorted_and_typed(tmp_path):
    out = build(tmp_path)
    rows = [json.loads(line) for line in (out / "nodes.jsonl").read_text().splitlines()]
    assert [r["kind"] for r in rows] == ["entity", "resource", "resource", "topic", "topic"]
    assert [r["id"] for r in rows if r["kind"] == "resource"] == [
        "resource:openalex:W1", "resource:openalex:W2"
    ]


def test_metadata_counts_edges_by_kind(tmp_path):
    meta = json.loads((build(tmp_path) / "metadata.json").read_text())
    assert meta["counts"] == {"topics": 2, "resources": 2, "entities": 1,
                              "relationships": 3, "nodes": 5}
    assert meta["relation_counts"] == {"CITES": 1, "SIMILAR_TO": 1, "TAGGED_WITH": 1}
    assert meta["confidence_counts"] == {"INFERRED": 1}
    assert meta["license"] == "CC-BY-4.0"


def test_taxonomy_ships_separately(tmp_path):
    """Consumers who only want to browse the tree shouldn't have to
    reassemble it out of nodes.jsonl."""
    payload = json.loads((build(tmp_path) / "taxonomy.json").read_text())
    assert payload["taxonomy_version"] == "v3"
    assert [t["code"] for t in payload["topics"]] == ["2", "2.2"]


def test_checksums_cover_every_other_file(tmp_path):
    out = build(tmp_path)
    listed = {line.split("  ", 1)[1] for line in
              (out / "checksums.txt").read_text().splitlines()}
    assert listed == {"nodes.jsonl", "relationships.jsonl", "taxonomy.json", "metadata.json"}


def test_built_at_is_injected_not_read_from_the_clock(tmp_path):
    """Reading the clock here would make releases irreproducible."""
    out = write_release(tmp_path, version="v0.1.0", topics=[], built_at="2026-08-07")
    assert json.loads((out / "metadata.json").read_text())["built_at"] == "2026-08-07"
