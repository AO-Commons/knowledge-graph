"""Portable graph releases.

The export is the product for anyone who doesn't want to run our
infrastructure — the same reasoning behind Learning Commons publishing
JSONL rather than only an API. `nodes.jsonl` and `relationships.jsonl` are
readable with standard tools and loadable into a graph database, without
either being required.

`graph.mira.jsonld` is the same release in MIRA's vocabulary, written beside
them rather than instead of them. See mira.py for what that projection can and
cannot say.
"""

from .jsonl import write_release
from .mira import write_mira

__all__ = ["write_release", "write_mira"]
