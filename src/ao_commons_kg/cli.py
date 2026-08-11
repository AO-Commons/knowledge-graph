"""Command line entry points.

    aokg taxonomy --stats        parse the taxonomy and report what loaded
    aokg build --version v0.1.0  write a release into data/releases/
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from .export import write_release
from .models import Relationship, RelationType
from .taxonomy import TaxonomyError, load_taxonomy

REPO = Path(__file__).resolve().parent.parent.parent
DEFAULT_TAXONOMY = REPO / "taxonomy" / "agentic-org-research-library-taxonomy-v3.md"
DEFAULT_RELEASES = REPO / "data" / "releases"


def _parent_edges(topics) -> list[Relationship]:
    """PARENT_OF edges are structural, so they're derived rather than stored."""
    codes = {topic.code for topic in topics}
    return [
        Relationship(f"topic:{t.parent_code}", t.id, RelationType.PARENT_OF)
        for t in topics
        if t.parent_code and t.parent_code in codes
    ]


def cmd_taxonomy(args) -> int:
    topics = load_taxonomy(args.path, strict=not args.lenient)
    by_depth = Counter(topic.depth for topic in topics)
    coding = sum(1 for t in topics if t.usage_mode.value == "coding_scheme")

    print(f"{len(topics)} topics from {Path(args.path).name}")
    print(f"  sections {by_depth[0]} · subsections {by_depth[1]} · leaves {by_depth[2]}")
    print(f"  coding-scheme topics (section 11): {coding}")
    print(f"  unnumbered subpoints carried: {sum(len(t.subpoints) for t in topics)}")

    if args.stats:
        print("\n  per section:")
        counts = Counter(topic.top_level_section for topic in topics)
        titles = {t.code: t.title for t in topics if t.depth == 0}
        for section in sorted(counts, key=int):
            print(f"    {section:>2}  {counts[section]:>3}  {titles.get(section, '?')}")
        # Deliberately no "research gap" marker here. A thin *literature* is
        # not a small branch of the tree — section 6 is among the largest and
        # has almost nothing written about it. Coverage is a property of
        # resources per topic, so that signal belongs with the corpus.
    return 0


def cmd_build(args) -> int:
    topics = load_taxonomy(args.taxonomy)
    out = write_release(
        args.out,
        version=args.version,
        topics=topics,
        relationships=_parent_edges(topics),
        built_at=args.built_at,
    )
    print(f"wrote {out}")
    for path in sorted(out.iterdir()):
        print(f"  {path.name:<22} {path.stat().st_size:>9,} bytes")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aokg", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    tax = sub.add_parser("taxonomy", help="parse and report on the taxonomy")
    tax.add_argument("--path", default=str(DEFAULT_TAXONOMY))
    tax.add_argument("--stats", action="store_true", help="per-section counts")
    tax.add_argument("--lenient", action="store_true",
                     help="report problems instead of refusing to load")
    tax.set_defaults(func=cmd_taxonomy)

    build = sub.add_parser("build", help="write a graph release")
    build.add_argument("--version", required=True)
    build.add_argument("--taxonomy", default=str(DEFAULT_TAXONOMY))
    build.add_argument("--out", default=str(DEFAULT_RELEASES))
    build.add_argument("--built-at", default=None,
                       help="ISO date recorded in metadata; omit for a reproducible build")
    build.set_defaults(func=cmd_build)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except TaxonomyError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
