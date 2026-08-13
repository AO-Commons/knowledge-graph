"""Optional layers applied on top of the core graph.

An overlay may change ranking. It may never be required for the graph to be
complete, and it is always switchable, so its contribution can be measured
rather than assumed.
"""

from .trust import TrustOverlay, apply

__all__ = ["TrustOverlay", "apply"]
