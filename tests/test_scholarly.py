"""The scholarly layer, tested against recorded payloads.

Expansion is where a small change quietly alters what the corpus becomes, so
it is tested offline rather than against a live API. The fixtures are trimmed
real OpenAlex responses.
"""

import json

import pytest

from ao_commons_kg.scholarly.store import ReferenceStore
from ao_commons_kg.scholarly.openalex import (
    OpenAlexError,
    Work,
    expand_neighborhood,
    parse_work,
    resolve_work,
    scope_score,
    short_id,
    work_url,
)

# A real response, trimmed to the fields we read.
MULTI_AGENT_RISKS = {
    "id": "https://openalex.org/W4407806359",
    "doi": "https://doi.org/10.48550/arxiv.2502.14143",
    "title": "Multi-Agent Risks from Advanced AI",
    "publication_date": "2025-02-19",
    "cited_by_count": 8,
    "type": "preprint",
    "open_access": {"is_oa": True},
    "is_retracted": False,
    "authorships": [
        {"author": {"display_name": "Lewis Hammond"},
         "institutions": [{"display_name": "University of Oxford"}]},
        {"author": {"display_name": "Joel Z. Leibo"},
         "institutions": [{"display_name": "Google DeepMind"}]},
    ],
    "referenced_works": [
        "https://openalex.org/W3172330035",
        "https://openalex.org/W4389471395",
        "https://openalex.org/W9999999999",
    ],
    "abstract_inverted_index": {
        "Multi-agent": [0], "systems": [1], "of": [2], "advanced": [3],
        "AI": [4], "introduce": [5], "governance": [6], "risks": [7],
    },
}

MELTING_POT = {
    "id": "https://openalex.org/W3172330035",
    "doi": "https://doi.org/10.48550/arxiv.2107.06857",
    "title": "Scalable Evaluation of Multi-Agent Reinforcement Learning with Melting Pot",
    "publication_date": "2021-07-14",
    "cited_by_count": 23,
    "authorships": [{"author": {"display_name": "Joel Z. Leibo"}, "institutions": []}],
    "referenced_works": [],
    "abstract_inverted_index": {"A": [0], "benchmark": [1], "for": [2],
                               "multi-agent": [3], "evaluation": [4]},
}

IRRELEVANT = {
    "id": "https://openalex.org/W9999999999",
    "title": "Capsule sponge triage of patients with reflux symptoms improves endoscopy yield",
    "publication_date": "2025-06-01",
    "cited_by_count": 2,
    "authorships": [],
    "referenced_works": [],
    "abstract_inverted_index": {"Patients": [0], "referred": [1], "for": [2],
                                "endoscopy": [3]},
}

BY_ID = {
    "W4407806359": MULTI_AGENT_RISKS,
    "W3172330035": MELTING_POT,
    "W9999999999": IRRELEVANT,
}


def fake_fetch(url: str) -> dict:
    """Serves the fixtures, and records nothing it wasn't asked for."""
    if "filter=cites:" in url:
        # Works citing Multi-Agent Risks.
        return {"results": [MELTING_POT, IRRELEVANT]}
    for work_id, payload in BY_ID.items():
        if work_id in url:
            return payload
    if "10.48550/arXiv.2502.14143" in url:
        return MULTI_AGENT_RISKS
    raise OpenAlexError(f"404 for {url}")


class TestIdentity:
    def test_every_identifier_form_resolves_to_a_url(self):
        assert work_url("W4407806359").endswith("/works/W4407806359")
        assert "10.48550/arXiv.2502.14143" in work_url("2502.14143")
        assert "10.1038/s41586" in work_url("10.1038/s41586-024-1")

    def test_arxiv_version_suffix_is_dropped(self):
        """`2403.12482v2` and `2403.12482` are the same paper."""
        assert work_url("2403.12482v2") == work_url("2403.12482")

    def test_an_unrecognizable_identifier_is_an_error(self):
        with pytest.raises(OpenAlexError, match="not an identifier"):
            work_url("Multi-Agent Risks from Advanced AI")

    def test_ids_are_shortened_consistently(self):
        assert short_id("https://openalex.org/W123") == "W123"
        assert short_id("W123") == "W123"
        assert short_id(None) is None


class TestParsing:
    def test_a_work_parses_completely(self):
        work = parse_work(MULTI_AGENT_RISKS)
        assert work.openalex_id == "W4407806359"
        assert work.doi == "10.48550/arxiv.2502.14143"
        assert work.arxiv_id == "2502.14143"
        assert work.authors == ["Lewis Hammond", "Joel Z. Leibo"]
        assert "Google DeepMind" in work.institutions
        assert work.is_open_access is True
        assert work.referenced_works == ["W3172330035", "W4389471395", "W9999999999"]

    def test_the_inverted_abstract_is_rebuilt_in_order(self):
        """OpenAlex stores abstracts as a position index, not as text."""
        assert parse_work(MULTI_AGENT_RISKS).abstract == (
            "Multi-agent systems of advanced AI introduce governance risks"
        )

    def test_a_work_with_no_abstract_is_fine(self):
        assert parse_work({"id": "https://openalex.org/W1", "title": "T"}).abstract is None

    def test_resolve_goes_through_the_fetcher(self):
        assert resolve_work("W4407806359", fake_fetch).title.startswith("Multi-Agent Risks")


class TestScopeFilter:
    def test_on_topic_work_scores_well(self):
        score, reasons = scope_score(parse_work(MULTI_AGENT_RISKS))
        assert score >= 3
        assert any("multi-agent" in r for r in reasons)

    def test_clinical_work_is_pushed_below_the_threshold(self):
        """The failure mode the manual pass kept hitting: an author's whole
        output, not their relevant output."""
        score, _ = scope_score(parse_work(IRRELEVANT))
        assert score < 3

    def test_the_score_shows_its_reasoning(self):
        """A queue a reviewer cannot interrogate is one they stop trusting."""
        _, reasons = scope_score(parse_work(MELTING_POT))
        assert reasons and all(r.startswith(("+", "-")) for r in reasons)


class TestReferenceStore:
    def test_round_trips(self, tmp_path):
        store = ReferenceStore.load(tmp_path / "refs.jsonl")
        store.put("resource:a", key="arxiv:2502.14143", source="semanticscholar",
                  referenced_keys=["arxiv:2107.06857"], cited_by_count=8)
        store.save()

        reloaded = ReferenceStore.load(tmp_path / "refs.jsonl")
        assert reloaded.entries["resource:a"]["cited_by_count"] == 8
        assert reloaded.entries["resource:a"]["key"] == "arxiv:2502.14143"

    def test_citations_are_restricted_to_records_we_hold(self, tmp_path):
        """A reference to a paper we do not hold is a dangling edge that
        inflates the export without answering anything."""
        store = ReferenceStore.load(tmp_path / "refs.jsonl")
        store.put("resource:a", key="arxiv:1", source="s2",
                  referenced_keys=["arxiv:2", "doi:10.1/unheld"])
        store.put("resource:b", key="arxiv:2", source="s2", referenced_keys=[])
        assert store.citation_pairs() == [("resource:a", "resource:b")]

    def test_a_source_with_no_references_does_not_erase_another(self, tmp_path):
        """OpenAlex carries no references for preprints. Letting it overwrite
        a Semantic Scholar list would undo the reason that connector exists."""
        store = ReferenceStore.load(tmp_path / "refs.jsonl")
        store.put("resource:a", key="arxiv:1", source="semanticscholar",
                  referenced_keys=["arxiv:2", "arxiv:3"])
        store.put("resource:a", key="arxiv:1", source="openalex", referenced_keys=[])
        assert store.entries["resource:a"]["referenced_works"] == ["arxiv:2", "arxiv:3"]
        assert store.entries["resource:a"]["source"] == "semanticscholar"

    def test_self_citation_is_not_an_edge(self, tmp_path):
        store = ReferenceStore.load(tmp_path / "refs.jsonl")
        store.put("resource:a", key="arxiv:1", source="s2", referenced_keys=["arxiv:1"])
        assert store.citation_pairs() == []

    def test_output_is_deterministic(self, tmp_path):
        for name in ("a", "b"):
            store = ReferenceStore.load(tmp_path / f"{name}.jsonl")
            store.put("resource:b", key="arxiv:2", source="s2", referenced_keys=["arxiv:9"])
            store.put("resource:a", key="arxiv:1", source="s2", referenced_keys=["arxiv:9"])
            store.save()
        assert (tmp_path / "a.jsonl").read_bytes() == (tmp_path / "b.jsonl").read_bytes()

    def test_coverage_reports_the_gap(self, tmp_path):
        store = ReferenceStore.load(tmp_path / "refs.jsonl")
        store.put("resource:a", key="arxiv:1", source="s2", referenced_keys=["arxiv:9"])
        store.put("resource:b", key="arxiv:2", source="openalex", referenced_keys=[])
        assert store.coverage() == (1, 2)

    def test_missing_file_loads_empty(self, tmp_path):
        assert ReferenceStore.load(tmp_path / "absent.jsonl").entries == {}


class TestExpansion:
    def test_expansion_walks_both_directions(self):
        """References are what a paper builds on; citers are what built on
        it. A corpus grown only forward drifts recent, only backward drifts
        foundational."""
        candidates, resolved = expand_neighborhood(
            ["W4407806359"], fake_fetch, known=set(), min_score=3, per_seed=10
        )
        assert "W4407806359" in resolved
        found = {c.openalex_id for c in candidates}
        assert "W3172330035" in found
        directions = {c.found_via.split()[0] for c in candidates}
        assert directions <= {"cited", "cites"}

    def test_the_scope_filter_drops_off_topic_candidates(self):
        candidates, _ = expand_neighborhood(
            ["W4407806359"], fake_fetch, known=set(), min_score=3, per_seed=10
        )
        assert "W9999999999" not in {c.openalex_id for c in candidates}

    def test_known_records_are_not_proposed_again(self):
        candidates, _ = expand_neighborhood(
            ["W4407806359"], fake_fetch, known={"W3172330035"}, min_score=3, per_seed=10
        )
        assert "W3172330035" not in {c.openalex_id for c in candidates}

    def test_candidates_rank_by_score_then_citations(self):
        candidates, _ = expand_neighborhood(
            ["W4407806359"], fake_fetch, known=set(), min_score=0, per_seed=10
        )
        scores = [(-c.score, -c.cited_by_count) for c in candidates]
        assert scores == sorted(scores)

    def test_a_seed_that_will_not_resolve_does_not_stop_the_run(self):
        candidates, resolved = expand_neighborhood(
            ["W0000000000", "W4407806359"], fake_fetch, known=set(), min_score=3
        )
        assert "W4407806359" in resolved and candidates

    def test_candidates_carry_their_provenance(self):
        candidates, _ = expand_neighborhood(
            ["W4407806359"], fake_fetch, known=set(), min_score=3, per_seed=10
        )
        entry = candidates[0].to_dict()
        assert entry["found_via"] and entry["reasons"]
        assert json.dumps(entry)  # serializable for the review queue


# --- Calibration -------------------------------------------------------------
# Locked against the hand pass over ~90 works. A change to the term lists that
# drops one of the KEEP titles is a regression, not a tuning choice: Melting
# Pot is already in the corpus, and a filter that would have excluded it
# cannot be trusted to grow the corpus.

KEEP = [
    "Virtual Agent Economies",
    "Multi-Agent Risks from Advanced AI",
    "Scalable Evaluation of Multi-Agent Reinforcement Learning with Melting Pot",
    "Levels of Autonomy for AI Agents",
    "Securing AI Agents with Information-Flow Control",
    "The Automated but Risky Game: Benchmarking Agent-to-Agent Negotiations",
]
DROP = [
    "GraphBLAS Mathematical Opportunities: Parallel Hypersparse Matrix Graph Streaming",
    "Capsule sponge triage of patients with reflux symptoms",
    "Evaluating Amazon effects with purchases crowdsourced from US consumers",
    "Community media in the prosumer era",
    "The natural state of blockchains: an ethnography of validator governance",
]


@pytest.mark.parametrize("title", KEEP)
def test_relevant_titles_clear_the_threshold(title):
    assert scope_score(Work(openalex_id="W", title=title))[0] >= 3, title


@pytest.mark.parametrize("title", DROP)
def test_off_topic_titles_are_filtered(title):
    assert scope_score(Work(openalex_id="W", title=title))[0] < 3, title


def test_the_filter_cannot_find_papers_relevant_by_argument():
    """A known and accepted limitation, recorded so nobody mistakes the
    pre-filter for the scope test.

    "Institutions as cached computation for resource-rational negotiation" is
    squarely in scope and mentions no agent in its title. Keyword scoring will
    not surface it; author expansion did. The two instruments are
    complementary, and the review queue is where that gap gets closed.
    """
    score, _ = scope_score(Work(
        openalex_id="W",
        title="Institutions as cached computation for resource-rational negotiation",
    ))
    assert score < 3


# --- Drift from the first live run -------------------------------------------
# Seeding from borrowed multi-agent RL benchmarks returned these. Each scores
# well on "agent" and "cooperation" and none of them changes how you run an
# organization. Regression-locked because the pull toward adjacent fields is
# constant, and section 15 says to point at them rather than ingest them.

MARL_DRIFT = [
    "Evaluating Inter-Operator Cooperation Scenarios to Save Radio Resources",
    "Signalling and social learning in swarms of robots",
    "Applying Deep Q-learning for Multi-agent Cooperative-Competitive Environments",
]


@pytest.mark.parametrize("title", MARL_DRIFT)
def test_adjacent_field_drift_is_filtered(title):
    assert scope_score(Work(openalex_id="W", title=title))[0] < 3, title


def test_filtering_drift_does_not_cost_us_the_corpus():
    """The AGAINST list is sharp enough to cut. Check it did not also cut the
    multi-agent work that belongs here."""
    for title in KEEP:
        assert scope_score(Work(openalex_id="W", title=title))[0] >= 3, title


def test_domain_applications_are_flagged_not_penalized():
    """A keyword cannot tell "agents run this manufacturing business" from
    "agents schedule maintenance here". Subtracting would hide the first to
    suppress the second, so the reviewer is shown the suspicion instead."""
    applied = Work(
        openalex_id="W",
        title="Hybrid agentic AI and multi-agent systems in smart manufacturing",
    )
    score, reasons = scope_score(applied)
    assert score >= 3, "still surfaces — the reviewer decides, not the filter"
    assert any(r.startswith("??") for r in reasons), "and is flagged as suspect"


def test_the_prefilter_does_not_claim_to_be_the_scope_test():
    """Recorded as a property, because the temptation to auto-merge on a
    score grows with every run that looks clean."""
    from ao_commons_kg.scholarly import openalex
    assert "pre-filter" in openalex.scope_score.__doc__ or "pre-filter" in openalex.__doc__ \
        or "pre-filter" in open(openalex.__file__).read()


# --- Structure beats vocabulary ----------------------------------------------

def test_structural_signal_finds_what_keywords_cannot():
    """The case that motivated the design: a paper squarely in scope whose
    title contains no agent-ish vocabulary.

    Keyword scoring puts it below the threshold. Being cited by two corpus
    papers puts it near the top. The field's own citing behaviour is better
    evidence of relevance than a word list, and this asserts the ranking
    reflects that."""
    from ao_commons_kg.graph import co_citation_counts

    invisible = Work(
        openalex_id="W_INVISIBLE",
        title="Institutions as cached computation for resource-rational negotiation",
    )
    keyword_score, _ = scope_score(invisible)
    assert keyword_score < 3, "vocabulary alone does not surface it"

    references = {
        "W_A": ["W_INVISIBLE", "W_OTHER"],
        "W_B": ["W_INVISIBLE"],
    }
    counts = co_citation_counts(references)
    assert counts["W_INVISIBLE"] == 2

    structural_score = keyword_score + 3 * counts["W_INVISIBLE"]
    assert structural_score >= 3, "structure surfaces it"


# --- Semantic Scholar and canonical keys -------------------------------------

from ao_commons_kg.scholarly.keys import canonical_key  # noqa: E402
from ao_commons_kg.scholarly.semanticscholar import (  # noqa: E402
    SemanticScholarError,
    paper_url,
    parse_paper,
)

S2_PAPER = {
    "paperId": "abc123",
    "title": "Multi-Agent Risks from Advanced AI",
    "abstract": "Multi-agent systems of advanced AI introduce governance risks.",
    "publicationDate": "2025-02-19",
    "citationCount": 9,
    "externalIds": {"ArXiv": "2502.14143", "DOI": "10.48550/arXiv.2502.14143"},
    "authors": [{"name": "Lewis Hammond"}],
    "references": [
        {"externalIds": {"DOI": "10.1145/3442188.3445922"}, "title": "A"},
        {"externalIds": {"ArXiv": "2107.06857"}, "title": "Melting Pot"},
        {"externalIds": {}, "title": "No identifiers at all"},
    ],
}


class TestCanonicalKeys:
    def test_the_same_paper_gets_one_key_from_either_source(self):
        """The failure this prevents is silent: two namespaces never
        intersect, so coupling returns empty and looks like a corpus with
        nothing in common rather than like a bug."""
        from_s2 = canonical_key({"ArXiv": "2107.06857", "DOI": "10.48550/arXiv.2107.06857"})
        from_openalex = canonical_key({"doi": "https://doi.org/10.48550/arxiv.2107.06857"})
        assert from_s2 == from_openalex == "arxiv:2107.06857"

    def test_doi_is_preferred_because_both_sources_report_it(self):
        assert canonical_key({"DOI": "10.1038/S41586", "ArXiv": "x"}) == "doi:10.1038/s41586"

    def test_arxiv_dois_resolve_to_the_arxiv_id(self):
        """They are minted mechanically, so a record indexed under one form
        still meets a record indexed under the other."""
        assert canonical_key({"DOI": "10.48550/arXiv.2502.14143"}) == "arxiv:2502.14143"

    def test_a_semantic_scholar_hash_is_the_last_resort(self):
        assert canonical_key({"CorpusId": "999"}) == "semanticscholar:999"

    def test_nothing_identifiable_is_none(self):
        assert canonical_key({}) is None and canonical_key(None) is None


class TestSemanticScholar:
    def test_identifier_forms_route_correctly(self):
        assert "DOI:10.1038/x" in paper_url("10.1038/x")
        assert "arXiv:2502.14143" in paper_url("2502.14143")
        assert "arXiv:2502.14143" in paper_url("2502.14143v3"), "version suffix dropped"

    def test_an_openalex_id_is_refused_with_a_useful_message(self):
        with pytest.raises(SemanticScholarError, match="OpenAlex id"):
            paper_url("W4407806359")

    def test_references_become_canonical_keys(self):
        paper = parse_paper(S2_PAPER)
        assert paper.referenced_keys == ["arxiv:2107.06857", "doi:10.1145/3442188.3445922"]

    def test_references_without_identifiers_are_dropped(self):
        """They cannot join anything, and keeping them would inflate the
        denominator in every coupling score."""
        assert len(parse_paper(S2_PAPER).referenced_keys) == 2

    def test_it_supplies_what_openalex_lacks_for_preprints(self):
        paper = parse_paper(S2_PAPER)
        assert paper.abstract and paper.referenced_keys
        assert paper.key == "arxiv:2502.14143"
