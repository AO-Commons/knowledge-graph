"""Load curated Resource records from `data/resources/`.

These are the first-party, hand-curated end of the corpus — tools, memos,
standards — as opposed to the papers that arrive by the OpenAlex and Semantic
Scholar discovery paths. Both end up as Resources; only the provenance
differs, and `source_provenance` records which is which.

YAML rather than JSONL because humans edit these, and Airtable is the
curation surface they are exported from.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import yaml

from .models import Resource

REPO = Path(__file__).resolve().parent.parent.parent
DEFAULT_DIR = REPO / "data" / "resources"


class ResourceError(ValueError):
    """A curated resource file that will not load."""


def _loader() -> type[yaml.SafeLoader]:
    """SafeLoader that leaves dates as strings.

    The schema wants ISO-8601 date strings; PyYAML would otherwise hand back
    datetime.date for unquoted values and every date field would round-trip
    to a different type than it came in as.
    """

    class _Loader(yaml.SafeLoader):
        pass

    _Loader.yaml_implicit_resolvers = {
        prefix: [(tag, regexp) for tag, regexp in resolvers
                 if tag != "tag:yaml.org,2002:timestamp"]
        for prefix, resolvers in _Loader.yaml_implicit_resolvers.items()
    }
    return _Loader


def load_resources(directory: str | Path = DEFAULT_DIR) -> list[Resource]:
    """Read every resource file, failing loudly on the first bad one."""
    directory = Path(directory)
    if not directory.exists():
        return []

    loader = _loader()
    resources: list[Resource] = []
    seen: dict[str, Path] = {}

    for path in sorted(directory.glob("*.yml")):
        try:
            payload = yaml.load(path.read_text(encoding="utf-8"), Loader=loader)
        except yaml.YAMLError as error:
            raise ResourceError(f"{path.name}: invalid YAML: {error}") from error
        if not isinstance(payload, dict):
            raise ResourceError(f"{path.name}: expected a single resource object")

        try:
            resource = Resource(**payload)
        except (TypeError, ValueError) as error:
            raise ResourceError(f"{path.name}: {error}") from error

        # `resource:tool:buzz` lives in `tool-buzz.yml`. Keeping the filename
        # derivable from the id means a record can be found from a citation
        # without consulting an index.
        expected = resource.id.removeprefix("resource:").replace(":", "-")
        if expected != path.stem:
            raise ResourceError(
                f"{path.name}: id {resource.id!r} implies {expected}.yml"
            )
        if resource.id in seen:
            raise ResourceError(
                f"{path.name}: duplicate id {resource.id!r}, also in {seen[resource.id].name}"
            )
        seen[resource.id] = path
        resources.append(resource)

    return resources


def tagged_edges(resources: Iterable[Resource], topic_codes: set[str]) -> list:
    """TAGGED_WITH edges for resources, skipping tags to unknown topics.

    A tag pointing at a code the taxonomy doesn't define is a curation error,
    surfaced by the caller rather than silently written into the graph.
    """
    from .models import ConfidenceClass, Relationship, RelationType

    edges = []
    for resource in resources:
        for code in resource.taxonomy_topics:
            if code not in topic_codes:
                continue
            edges.append(
                Relationship(
                    resource.id,
                    f"topic:{code}",
                    RelationType.TAGGED_WITH,
                    confidence_class=ConfidenceClass.EXTRACTED,
                    source_resource_id=resource.id,
                    extraction_method="curated",
                )
            )
    return edges


def unknown_tags(resources: Iterable[Resource], topic_codes: set[str]) -> dict[str, list[str]]:
    return {
        resource.id: bad
        for resource in resources
        if (bad := [c for c in resource.taxonomy_topics if c not in topic_codes])
    }
