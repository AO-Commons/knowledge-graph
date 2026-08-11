"""Portable graph releases.

The export is the product for anyone who doesn't want to run our
infrastructure — the same reasoning behind Learning Commons publishing
JSONL rather than only an API. `nodes.jsonl` and `relationships.jsonl` are
readable with standard tools and loadable into a graph database, without
either being required.
"""

from .jsonl import write_release

__all__ = ["write_release"]
