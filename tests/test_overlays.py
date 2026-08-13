"""The trust overlay must be optional, and provably so."""

from ao_commons_kg.overlays import TrustOverlay, apply

RANKED = [("resource:a", 10.0), ("resource:b", 8.0), ("resource:c", 6.0)]


def test_absent_overlay_file_is_normal_not_an_error(tmp_path):
    """The public graph builds without one; every caller must keep working."""
    assert TrustOverlay.load(tmp_path / "absent.yml").is_empty
    assert TrustOverlay.load(None).is_empty


def test_no_overlay_leaves_ranking_untouched():
    """`overlay off` and `no overlay file` must be the same code path, or the
    comparison it exists to enable is not honest."""
    assert apply(RANKED, TrustOverlay()) is RANKED


def test_an_overlay_can_change_the_order():
    overlay = TrustOverlay(authors={"m1": ["resource:c"]}, endorsements={"m2": ["resource:c"]})
    reranked = apply(RANKED, overlay)
    assert [key for key, _ in reranked][0] == "resource:a"
    assert dict(reranked)["resource:c"] > 6.0, "c was boosted"


def test_authorship_outweighs_endorsement():
    """Writing a thing is a stronger signal than pointing at it."""
    wrote = TrustOverlay(authors={"m": ["resource:x"]}).affinity()["resource:x"]
    pointed = TrustOverlay(endorsements={"m": ["resource:x"]}).affinity()["resource:x"]
    assert wrote > pointed


def test_attention_saturates():
    """Ten endorsements is not ten times more relevant. Without this the
    overlay becomes a popularity contest among a small group."""
    few = TrustOverlay(endorsements={f"m{i}": ["resource:x"] for i in range(2)}).affinity()
    many = TrustOverlay(endorsements={f"m{i}": ["resource:x"] for i in range(20)}).affinity()
    assert many["resource:x"] < 10 * few["resource:x"]


def test_overlay_edges_declare_how_they_were_made():
    overlay = TrustOverlay(authors={"m": ["resource:a"]}, endorsements={"m": ["resource:b"]})
    methods = {e.extraction_method for e in overlay.edges()}
    assert methods == {"trust-overlay:authorship", "trust-overlay:endorsement"}
    for edge in overlay.edges():
        assert edge.confidence_class is not None, "community attachment is not deterministic"


def test_overlay_edges_are_not_in_the_core_graph_by_default():
    """They exist only when a build explicitly includes the overlay."""
    from ao_commons_kg import cli
    assert "TrustOverlay" not in open(cli.__file__).read(), (
        "the core build path must not import the overlay"
    )
