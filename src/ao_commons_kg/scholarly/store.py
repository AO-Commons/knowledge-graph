"""Reference lists, kept out of the resource files.

Keyed by our own resource id and storing canonical reference keys, so
OpenAlex and Semantic Scholar write into one store and their references meet.
A record's own metadata is small and human-editable; its reference list is
neither, and inlining a hundred identifiers into a YAML a person is expected
to correct by hand would be a poor trade.

Bibliographic coupling and co-citation both read from here.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ReferenceStore:
    path: Path
    entries: dict[str, dict] = field(default_factory=dict)

    @classmethod
    def load(cls, path: str | Path) -> ReferenceStore:
        path = Path(path)
        entries = {}
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    record = json.loads(line)
                    # Records written before the store was keyed by resource
                    # id are dropped rather than migrated: they hold OpenAlex
                    # reference ids that cannot join canonical keys, and a
                    # silent half-join is worse than a rebuild.
                    if record.get("resource_id"):
                        entries[record["resource_id"]] = record
        return cls(path=path, entries=entries)

    def put(
        self,
        resource_id: str,
        *,
        key: str | None,
        source: str,
        referenced_keys: list[str],
        cited_by_count: int = 0,
    ) -> None:
        existing = self.entries.get(resource_id, {})
        # A source that returns nothing must not erase what another found.
        # OpenAlex has no references for preprints; letting it overwrite a
        # Semantic Scholar list would undo the reason that connector exists.
        if not referenced_keys and existing.get("referenced_works"):
            referenced_keys = existing["referenced_works"]
            source = existing.get("source", source)

        self.entries[resource_id] = {
            "resource_id": resource_id,
            "key": key or existing.get("key"),
            "source": source,
            "cited_by_count": max(cited_by_count, existing.get("cited_by_count", 0)),
            "referenced_works": sorted(set(referenced_keys)),
        }

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lines = [json.dumps(self.entries[k], sort_keys=True) for k in sorted(self.entries)]
        self.path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

    def references(self) -> dict[str, list[str]]:
        """Resource id -> canonical keys it cites."""
        return {
            resource_id: entry.get("referenced_works", [])
            for resource_id, entry in self.entries.items()
            if entry.get("referenced_works")
        }

    def citation_pairs(self, by_key: dict[str, str]) -> list[tuple[str, str]]:
        """Citations where both ends are records we hold.

        Everything a paper cites is not a graph anyone can use; the subgraph
        among things we actually hold is.

        `by_key` maps a canonical key to the record holding it and comes from
        the corpus — `keys_for_corpus()` builds it. It used to be derived from
        this store instead, which quietly meant something narrower: a record
        could be a citation source only once resolved, and a citation *target*
        never, because an unresolved record has no entry here and so no key to
        match against. Half the edges in the graph were dropped that way, and
        nothing showed it, because a missing citation looks exactly like a
        paper nobody cited.
        """
        held = set(by_key.values())
        pairs = [
            (resource_id, by_key[cited])
            for resource_id, cited_keys in self.references().items()
            if resource_id in held
            for cited in cited_keys
            if cited in by_key and by_key[cited] != resource_id
        ]
        return sorted(set(pairs))

    def coverage(self) -> tuple[int, int]:
        """(records with a reference list, records stored)."""
        return sum(1 for e in self.entries.values() if e.get("referenced_works")), len(self.entries)
