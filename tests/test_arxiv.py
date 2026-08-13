"""arXiv as a source in its own right.

The index services are inferences over the literature; this is the submission.
It exists because OpenAlex answers 404 for anything posted recently, and
because its author disambiguation credits real, plausible, wrong people.
"""

import pytest

from ao_commons_kg.scholarly.arxiv import ArxivError, Preprint, parse, resolve, resolve_many

FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2608.10218v1</id>
    <published>2026-08-11T17:22:03Z</published>
    <title>Mind Viruses: Self-Propagating Ideas
  in Multi-Agent LLM Systems</title>
    <summary>  Ideas spread between agents without
  any human in the loop.
</summary>
    <author><name>Vassilis Papadopoulos</name></author>
    <author><name>Botao &#x27;Amber&#x27; Hu</name></author>
  </entry>
</feed>
"""


@pytest.fixture
def preprint():
    return parse(FEED)["2608.10218"]


class TestParse:
    def test_the_version_suffix_is_dropped_from_the_key(self):
        """v1 and v2 are one paper. Keyed by version, a lookup for the paper
        would miss the entry that answers it."""
        assert list(parse(FEED)) == ["2608.10218"]

    def test_titles_are_unwrapped(self, preprint):
        """arXiv line-wraps titles mid-phrase. Stored as-is, the newline
        reaches every consumer and no title comparison ever matches."""
        assert preprint.title == "Mind Viruses: Self-Propagating Ideas in Multi-Agent LLM Systems"

    def test_the_abstract_is_unwrapped_and_trimmed(self, preprint):
        assert preprint.abstract == "Ideas spread between agents without any human in the loop."

    def test_entities_are_decoded(self, preprint):
        """&#x27; is an apostrophe. Left encoded it makes a second, spurious
        spelling of a person who is already in the corpus."""
        assert preprint.authors[1] == "Botao 'Amber' Hu"

    def test_the_byline_keeps_its_order(self, preprint):
        assert preprint.authors[0] == "Vassilis Papadopoulos"

    def test_the_publication_date_is_a_plain_iso_day(self, preprint):
        assert preprint.published == "2026-08-11"

    def test_an_empty_feed_yields_nothing(self):
        assert parse("<feed></feed>") == {}


class TestResolve:
    def test_it_looks_up_one_id(self):
        found = resolve("2608.10218", lambda url: FEED)
        assert isinstance(found, Preprint)
        assert found.arxiv_id == "2608.10218"

    def test_a_missing_entry_raises_rather_than_returning_none(self):
        """A silent miss during ingestion becomes a record with no metadata,
        and nobody notices until someone reads it."""
        with pytest.raises(ArxivError, match="no entry"):
            resolve("9999.99999", lambda url: "<feed></feed>")

    def test_several_ids_go_in_one_request(self):
        seen = []

        def fetch(url):
            seen.append(url)
            return FEED

        resolve_many(["2608.10218", "2107.06857"], fetch)
        assert len(seen) == 1 and "2608.10218,2107.06857" in seen[0]

    def test_no_ids_makes_no_request(self):
        assert resolve_many([], lambda url: pytest.fail("should not fetch")) == {}
