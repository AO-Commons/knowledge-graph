"""The curated set: what the preview site opens on.

`data/curated.yml` is a list of record ids written by hand, and a hand-written
list of ids rots the moment a record is renamed. The site would not fail when
that happens — it would quietly show one fewer paper, which is the failure
nobody notices. These tests are the noise.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

from ao_commons_kg.resources import load_resources  # noqa: E402

CURATED = REPO / "data" / "curated.yml"


@pytest.fixture(scope="module")
def doc():
    return yaml.safe_load(CURATED.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def listed(doc) -> list[str]:
    ids = [r for stream in doc["streams"] for r in stream["records"]]
    return ids + list(doc["build_page"]["records"])


@pytest.fixture(scope="module")
def held() -> set[str]:
    return {r.id for r in load_resources()}


class TestTheSet:
    def test_every_id_is_a_record_the_corpus_holds(self, listed, held):
        missing = sorted(set(listed) - held)
        assert not missing, (
            "data/curated.yml names records the corpus does not hold: "
            + ", ".join(missing)
            + ". Either the record was renamed, or it was never filed — in which "
            "case it belongs under `not_held` with the reason."
        )

    def test_a_work_may_appear_in_several_streams(self, listed):
        # Deliberate: Intelligent AI Delegation is on three of the nine, and
        # flattening that away would lose what the streams are for.
        assert len(listed) > len(set(listed))

    def test_the_set_is_a_subset_and_not_the_corpus(self, listed, held):
        # If these ever match, the distinction the site draws has stopped
        # meaning anything and the page should say so rather than imply it.
        assert set(listed) < held

    def test_what_is_not_held_says_why(self, doc):
        for entry in doc.get("not_held") or []:
            assert entry.get("cite"), "an entry with no citation names nothing"
            assert entry.get("why"), f"{entry['cite']}: no reason given"


class TestTheSiteReadsIt:
    def test_build_site_marks_exactly_these_records(self, listed):
        import build_site

        assert build_site.curated_ids() == set(listed)

    def test_a_record_outside_the_set_is_not_marked(self, listed):
        import build_site

        data = build_site.payload()
        marked = {r["id"] for r in data["records"] if r["curated"]}
        assert marked == set(listed)
        assert data["counts"]["curated"] == len(set(listed))
