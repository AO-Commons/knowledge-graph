#!/usr/bin/env python3
"""Validate a release's MIRA projection against MIRA's own SHACL shapes.

Alignment checked rather than claimed. The shapes are the ones MIRA generates
from its LinkML source, vendored at the commit named in schema/PINNED, so a
result here means something a month from now.

    python3 scripts/validate_mira.py data/releases/v0.10.0

Exits non-zero when the graph does not conform, and prints the violations
grouped by shape and property so a hundred instances of one mistake read as
one mistake.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCHEMA = REPO / "schema" / "mira"


def main(argv: list[str]) -> int:
    argv = [a for a in argv if a != "--infer"]
    if len(argv) != 2:
        print(__doc__)
        return 2
    release = Path(argv[1])
    graph_path = release / "graph.mira.jsonld"
    if not graph_path.exists():
        print(f"no MIRA projection in {release} — run `aokg build` first")
        return 2

    try:
        from rdflib import Graph
        from pyshacl import validate
    except ImportError:
        print("needs rdflib and pyshacl:  pip install '.[mira]'")
        return 2

    # The context is read from the vendored copy rather than fetched, so this
    # works offline and cannot silently validate against a newer schema than
    # the one in schema/PINNED.
    document = json.loads(graph_path.read_text(encoding="utf-8"))
    document["@context"] = json.loads(
        (SCHEMA / "mira.jsonld").read_text(encoding="utf-8")
    )["@context"]

    data = Graph().parse(data=json.dumps(document), format="json-ld")
    shapes = Graph().parse(SCHEMA / "mira.shacl", format="turtle")
    ontology = Graph().parse(SCHEMA / "mira.ttl", format="turtle")

    # No RDFS inference. Their generated shapes include a closed shape on
    # rdfs:Resource that permits no properties at all, and under inference
    # every node in any graph is an rdfs:Resource — so every property on
    # everything violates and the run says nothing. Reported upstream; until
    # it changes, inference off is the only setting that produces a readable
    # result. `--infer` turns it back on to re-check.
    conforms, results_graph, _ = validate(
        data, shacl_graph=shapes, ont_graph=ontology,
        advanced=True,
        inference="rdfs" if "--infer" in sys.argv else "none",
        abort_on_first=False,
    )

    pin = (REPO / "schema" / "PINNED").read_text(encoding="utf-8").strip().splitlines()
    print(f"{len(data):,} triples against {pin[0]} @ {pin[1][:8]}")

    if conforms:
        print("conforms")
        return 0

    from rdflib import Namespace
    SH = Namespace("http://www.w3.org/ns/shacl#")
    grouped: Counter = Counter()
    for result in results_graph.subjects(None, SH.ValidationResult):
        shape = results_graph.value(result, SH.sourceShape)
        path = results_graph.value(result, SH.resultPath)
        constraint = results_graph.value(result, SH.sourceConstraintComponent)
        grouped[(
            str(path).rsplit("#", 1)[-1].rsplit("/", 1)[-1] if path else "—",
            str(constraint).rsplit("#", 1)[-1],
        )] += 1

    total = sum(grouped.values())
    print(f"does not conform — {total:,} violations, {len(grouped)} distinct\n")
    for (path, constraint), n in grouped.most_common():
        print(f"  {n:>6,}  {constraint:<28} on {path}")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
