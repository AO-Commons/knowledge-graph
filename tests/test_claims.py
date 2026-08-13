"""Claims: the layer that makes an answer checkable.

The tests here are mostly about refusing to lose provenance. A claim without
its source text, or an extracted claim that presents as reviewed, is worse than
no claim at all — it makes the graph confident about something nobody checked.
"""

import pytest
import yaml

from ao_commons_kg.claims import (
    ClaimError,
    claim_edges,
    coverage,
    load_claims,
    save_claims,
    slug_for,
)
from ao_commons_kg.models import Claim, ClaimType, ConfidenceClass, RelationType, ReviewStatus

QUOTE = ("Agents operating under per-task budget caps exceeded their allocation in "
         "3% of runs, against 27% for the unconstrained baseline.")


def a_claim(**kwargs):
    return Claim(
        id=kwargs.pop("id", "claim:arxiv:2502.14143:1"),
        resource_id=kwargs.pop("resource_id", "resource:arxiv:2502.14143"),
        text=kwargs.pop("text", "Per-task budget caps reduced overspending from 27% to 3%."),
        quote=kwargs.pop("quote", QUOTE),
        **kwargs,
    )


class TestClaim:
    def test_a_claim_without_its_source_text_is_refused(self):
        """Review has to cost seconds, not a re-read of the paper. A claim with
        no quote makes checking it as expensive as writing it, and a layer
        nobody checks is a layer that quietly invents things."""
        with pytest.raises(ValueError, match="no quote"):
            a_claim(quote="   ")

    def test_extraction_never_promotes_a_claim(self):
        assert a_claim().review_status is ReviewStatus.UNREVIEWED
        assert a_claim().confidence_class is ConfidenceClass.EXTRACTED

    def test_a_reviewer_without_a_review_is_refused(self):
        with pytest.raises(ValueError, match="reviewer without a review"):
            a_claim(reviewed_by="anke")

    def test_findings_and_positions_are_kept_apart(self):
        """"We measured X" and "X should be adopted" read alike in an abstract
        and answer different questions. Flattening them lets the graph report
        that something has been shown when it has only been argued."""
        assert ClaimType("finding") is not ClaimType("position")

    def test_overstated_is_a_verdict_of_its_own(self):
        """The characteristic failure of extraction is a paraphrase that says
        more than its source. A yes/no verdict cannot express it."""
        assert a_claim(review_status="reviewed", reviewed_by="anke",
                       verdict="overstated").verdict == "overstated"

    def test_an_unknown_verdict_is_refused(self):
        with pytest.raises(ValueError, match="unknown verdict"):
            a_claim(review_status="reviewed", reviewed_by="anke", verdict="wrong-ish")

    def test_a_topic_code_that_is_not_a_code_is_refused(self):
        with pytest.raises(ValueError, match="not a topic code"):
            a_claim(topic_codes=["governance"])

    def test_review_status_is_always_emitted(self):
        """As on Resource: an absent field must never have to be read as
        'unreviewed'."""
        assert a_claim().to_dict()["review_status"] == "unreviewed"

    def test_where_it_was_read_from_survives(self):
        """A claim from an abstract supports a weaker reading than the same
        claim from a results section, and a consumer cannot tell unless the
        record says so."""
        assert a_claim().to_dict()["extracted_from"] == "abstract"


class TestRoundTrip:
    def test_claims_survive_a_save_and_load(self, tmp_path):
        save_claims("resource:arxiv:2502.14143", [a_claim()], tmp_path)
        loaded = load_claims(tmp_path)
        assert [c.id for c in loaded] == ["claim:arxiv:2502.14143:1"]
        assert loaded[0].quote == QUOTE
        assert loaded[0].resource_id == "resource:arxiv:2502.14143"

    def test_the_file_is_named_after_the_resource(self, tmp_path):
        path = save_claims("resource:tool:buzz", [a_claim(id="claim:tool:buzz:1",
                                                          resource_id="resource:tool:buzz")],
                           tmp_path)
        assert path.name == "tool-buzz.yml"

    def test_extraction_order_is_preserved(self, tmp_path):
        """A paper's claims read as an argument. Sorting them would scramble it."""
        claims = [a_claim(id=f"claim:arxiv:2502.14143:{n}", text=f"Claim {n}.")
                  for n in (1, 2, 3)]
        save_claims("resource:arxiv:2502.14143", claims, tmp_path)
        assert [c.text for c in load_claims(tmp_path)] == ["Claim 1.", "Claim 2.", "Claim 3."]

    def test_the_resource_id_is_not_repeated_on_every_claim(self, tmp_path):
        save_claims("resource:arxiv:2502.14143", [a_claim()], tmp_path)
        payload = yaml.safe_load((tmp_path / "arxiv-2502.14143.yml").read_text())
        assert "resource_id" not in payload["claims"][0]

    def test_a_misnamed_file_is_refused(self, tmp_path):
        (tmp_path / "wrong-name.yml").write_text(
            "resource_id: resource:arxiv:2502.14143\nclaims: []\n")
        with pytest.raises(ClaimError, match="implies"):
            load_claims(tmp_path)

    def test_a_claim_with_no_resource_is_refused(self, tmp_path):
        (tmp_path / "arxiv-2502.14143.yml").write_text("claims: []\n")
        with pytest.raises(ClaimError, match="no resource_id"):
            load_claims(tmp_path)

    def test_an_absent_directory_is_not_an_error(self, tmp_path):
        assert load_claims(tmp_path / "nothing-here") == []

    def test_slugs_match_the_resource_convention(self):
        assert slug_for("resource:arxiv:2502.14143") == "arxiv-2502.14143"


class TestEdges:
    def test_a_claim_links_back_to_its_resource(self):
        edge = claim_edges([a_claim()])[0]
        assert edge.relation is RelationType.MAKES_CLAIM
        assert edge.source_id == "resource:arxiv:2502.14143"
        assert edge.confidence_class is ConfidenceClass.EXTRACTED

    def test_the_edge_says_which_text_it_came_from(self):
        """An edge met on its own, lifted into someone else's graph, must still
        carry enough to be checked."""
        assert claim_edges([a_claim()])[0].source_location == "abstract"

    def test_a_topic_edge_is_inferred_not_extracted(self):
        """The claim was read out of the source. Which branch it belongs under
        is our inference about it, and the two should not look alike."""
        edges = claim_edges([a_claim(topic_codes=["11.6"])])
        about = [e for e in edges if e.relation is RelationType.ABOUT][0]
        assert about.confidence_class is ConfidenceClass.INFERRED
        assert about.target_id == "topic:11.6"

    def test_a_topic_outside_the_taxonomy_is_dropped_rather_than_dangling(self):
        edges = claim_edges([a_claim(topic_codes=["11.6", "99.9"])], topic_codes={"11.6"})
        assert [e.target_id for e in edges if e.relation is RelationType.ABOUT] == ["topic:11.6"]


class TestCoverage:
    def test_it_counts_what_a_person_actually_checked(self):
        claims = [
            a_claim(id="claim:a:1"),
            a_claim(id="claim:a:2", review_status="reviewed", reviewed_by="anke",
                    verdict="accurate"),
            a_claim(id="claim:a:3", review_status="reviewed", reviewed_by="anke",
                    verdict="overstated"),
        ]
        assert coverage(claims) == {
            "claims": 3, "resources": 1, "reviewed": 2,
            "accurate": 1, "overstated": 1, "not_in_source": 0,
        }


class TestVerdicts:
    """Verdicts live apart from the claims they judge, because the claim files
    are regenerated by the next extraction pass and a judgement someone spent
    time on must not be in the blast radius of that."""

    def _corpus(self, tmp_path):
        save_claims("resource:arxiv:2502.14143",
                    [a_claim(), a_claim(id="claim:arxiv:2502.14143:2", text="Second.")],
                    tmp_path)
        return tmp_path

    def test_a_verdict_promotes_the_claim(self, tmp_path):
        claims = load_claims(self._corpus(tmp_path), verdicts={
            "claim:arxiv:2502.14143:1": {"verdict": "accurate", "reviewer": "anke"},
        })
        checked = {c.id: c for c in claims}
        assert checked["claim:arxiv:2502.14143:1"].review_status is ReviewStatus.REVIEWED
        assert checked["claim:arxiv:2502.14143:1"].reviewed_by == "anke"

    def test_an_unjudged_claim_stays_unreviewed(self, tmp_path):
        claims = load_claims(self._corpus(tmp_path), verdicts={
            "claim:arxiv:2502.14143:1": {"verdict": "accurate", "reviewer": "anke"},
        })
        assert {c.id: c for c in claims}["claim:arxiv:2502.14143:2"].review_status \
            is ReviewStatus.UNREVIEWED

    def test_re_extraction_cannot_erase_a_verdict(self, tmp_path):
        """The whole reason verdicts are stored elsewhere: this rewrite is what
        a better extractor does, and it must not cost the review."""
        directory = self._corpus(tmp_path)
        verdicts = {"claim:arxiv:2502.14143:1": {"verdict": "overstated", "reviewer": "anke"}}
        save_claims("resource:arxiv:2502.14143",
                    [a_claim(text="A sharper paraphrase.")], directory)
        reloaded = load_claims(directory, verdicts=verdicts)
        assert reloaded[0].text == "A sharper paraphrase."
        assert reloaded[0].verdict == "overstated"

    def test_a_bad_verdict_in_the_gold_file_is_refused(self, tmp_path):
        with pytest.raises(ClaimError, match="unknown verdict"):
            load_claims(self._corpus(tmp_path), verdicts={
                "claim:arxiv:2502.14143:1": {"verdict": "seems-fine", "reviewer": "anke"},
            })

    def test_no_verdict_file_is_the_normal_state(self, tmp_path):
        assert load_claims(self._corpus(tmp_path), verdicts=None)[0].review_status \
            is ReviewStatus.UNREVIEWED
