"""Write a versioned graph release.

    releases/<version>/
    ├── nodes.jsonl
    ├── relationships.jsonl
    ├── taxonomy.json
    ├── metadata.json
    └── checksums.txt

Output is deterministic: nodes sort by id, relationships by their triple, and
keys are written in a fixed order. A release rebuilt from unchanged inputs
produces byte-identical files, which is what makes the checksums worth
publishing and a diff between two releases worth reading.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from ..models import Entity, Relationship, Resource, Topic

NODE_KINDS = {Topic: "topic", Resource: "resource", Entity: "entity"}


def _node_records(nodes: Iterable[Topic | Resource | Entity]) -> list[dict[str, Any]]:
    records = []
    for node in nodes:
        kind = NODE_KINDS.get(type(node))
        if kind is None:
            raise TypeError(f"not a node type: {type(node).__name__}")
        records.append({"kind": kind, **node.to_dict()})
    return sorted(records, key=lambda r: (r["kind"], r["id"]))


def _edge_records(edges: Iterable[Relationship]) -> list[dict[str, Any]]:
    return sorted(
        (edge.to_dict() for edge in edges),
        key=lambda r: (r["relation"], r["source_id"], r["target_id"]),
    )


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=False) + "\n")


def _checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_release(
    out_dir: str | Path,
    *,
    version: str,
    topics: Iterable[Topic],
    resources: Iterable[Resource] = (),
    entities: Iterable[Entity] = (),
    relationships: Iterable[Relationship] = (),
    taxonomy_version: str = "v3",
    built_at: str | None = None,
) -> Path:
    """Write a release directory and return its path.

    `built_at` is passed in rather than read from the clock so a release can
    be reproduced byte-for-byte from the same inputs.
    """
    topics = list(topics)
    resources = list(resources)
    entities = list(entities)
    relationships = list(relationships)

    release_dir = Path(out_dir) / version
    release_dir.mkdir(parents=True, exist_ok=True)

    nodes = _node_records([*topics, *resources, *entities])
    edges = _edge_records(relationships)

    _write_jsonl(release_dir / "nodes.jsonl", nodes)
    _write_jsonl(release_dir / "relationships.jsonl", edges)

    # The taxonomy also ships on its own: it's the part most consumers want
    # first, and making them reassemble a tree out of nodes.jsonl to browse
    # it would be a poor trade for one small file.
    (release_dir / "taxonomy.json").write_text(
        json.dumps(
            {
                "taxonomy_version": taxonomy_version,
                "topic_count": len(topics),
                "topics": [topic.to_dict() for topic in topics],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    metadata = {
        "version": version,
        "taxonomy_version": taxonomy_version,
        "counts": {
            "topics": len(topics),
            "resources": len(resources),
            "entities": len(entities),
            "relationships": len(edges),
            "nodes": len(nodes),
        },
        "relation_counts": _counts(edges, "relation"),
        "confidence_counts": _counts(edges, "confidence_class"),
        "license": "CC-BY-4.0",
        "attribution": "AO Commons — https://github.com/AO-Commons/knowledge-graph",
    }
    if built_at:
        metadata["built_at"] = built_at
    (release_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    # Checksums last, over everything else in the release.
    checksums = sorted(
        (path.name, _checksum(path))
        for path in release_dir.iterdir()
        if path.name != "checksums.txt"
    )
    (release_dir / "checksums.txt").write_text(
        "".join(f"{digest}  {name}\n" for name, digest in checksums), encoding="utf-8"
    )
    return release_dir


def _counts(records: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        value = record.get(key)
        if value is not None:
            counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))
