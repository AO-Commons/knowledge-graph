"""The mirrored builder-tooling index.

The parser reads somebody else's README, so it will break when they reformat
it — the tests that matter are the ones that make that loud rather than
silent, and the one that stops a sync from severing our own links.
"""

import pytest

from ao_commons_kg.tooling import (
    Entry,
    Index,
    candidates,
    carry_promotions,
    diff,
    load,
    parse_readme,
    save,
)

README = """# awesome-builder-tools

Some prose that is not a table.

## Quick Start: The Anchor Stack

| Project | Description |
|---|---|
| [Open SaaS](https://github.com/wasp-lang/open-saas) | A free SaaS template. |

## Managing the Company

### Agentic Orchestration

| Project | Description | Stars |
|---|---|---|
| [LangGraph](https://github.com/langchain-ai/langgraph) | Stateful multi-agent workflows. | 24.8k+ |
| [Composio](https://github.com/ComposioHQ/composio) | 250+ integrations for agents. | 15k+ |

### Legal, DAO & Governance Infra

| Project | Description |
|---|---|
| [Aragon](https://github.com/aragon/osx) | On-chain governance. |

## Contributing

Open a pull request.
"""


@pytest.fixture
def entries():
    return parse_readme(README)


class TestParse:
    def test_it_finds_every_linked_entry(self, entries):
        assert [e.name for e in entries] == ["Open SaaS", "LangGraph", "Composio", "Aragon"]

    def test_the_builders_job_is_kept(self, entries):
        """Their section headings are the organising idea of the list — which
        job a tool belongs to. Flattening them would throw away the part that
        makes it navigable."""
        aragon = entries[-1]
        assert aragon.section == "Managing the Company"
        assert aragon.subsection == "Legal, DAO & Governance Infra"

    def test_a_star_count_is_kept_when_there_is_one(self, entries):
        assert entries[1].stars == "24.8k+"

    def test_no_star_column_means_no_star_count(self, entries):
        assert entries[0].stars is None

    def test_header_rows_and_prose_are_not_entries(self, entries):
        assert all(e.url.startswith("http") for e in entries)
        assert not any(e.name in {"Project", "Description"} for e in entries)

    def test_a_reformatted_readme_yields_nothing_rather_than_rubbish(self):
        """The sync refuses to write on an empty parse. A mirror silently
        emptied would read as "upstream deleted everything"."""
        assert parse_readme("# Title\n\nNo tables here at all.\n") == []


class TestSync:
    def test_a_new_entry_is_reported_as_added(self):
        before = Index(entries=[Entry("A", "https://x/a", "S")])
        after = Index(entries=[Entry("A", "https://x/a", "S"), Entry("B", "https://x/b", "S")])
        assert [e.name for e in diff(before, after)["added"]] == ["B"]

    def test_a_rename_is_a_change_not_a_removal(self):
        """Keyed by url, because a project renaming itself is not a project
        leaving the list, and reporting it as one would send somebody looking
        for a tool that never went anywhere."""
        before = Index(entries=[Entry("Danswer", "https://x/onyx", "S")])
        after = Index(entries=[Entry("Onyx", "https://x/onyx", "S")])
        changes = diff(before, after)
        assert not changes["removed"] and len(changes["changed"]) == 1

    def test_a_reworded_description_is_reported(self):
        before = Index(entries=[Entry("A", "https://x/a", "S", description="old")])
        after = Index(entries=[Entry("A", "https://x/a", "S", description="new")])
        assert len(diff(before, after)["changed"]) == 1

    def test_our_own_links_survive_a_resync(self):
        """Upstream does not know which entries we have profiled. A sync that
        dropped `promoted_to` would quietly unlink every tool in the corpus
        from the list it came from."""
        before = Index(entries=[Entry("Paperclip", "https://x/p", "S",
                                      promoted_to="resource:tool:paperclip")])
        after = carry_promotions(before, Index(entries=[Entry("Paperclip", "https://x/p", "S")]))
        assert after.entries[0].promoted_to == "resource:tool:paperclip"

    def test_a_removed_entry_we_had_profiled_is_still_reported(self):
        """It stays in the library — we assessed it ourselves — but somebody
        should know upstream dropped it."""
        before = Index(entries=[Entry("Gone", "https://x/g", "S", promoted_to="resource:tool:gone")])
        removed = diff(before, Index(entries=[]))["removed"]
        assert removed and removed[0].promoted_to == "resource:tool:gone"


class TestStored:
    def test_the_mirror_on_disk_loads_and_credits_upstream(self):
        index = load()
        assert index.entries, "the mirror should not be empty"
        assert index.source["license"] == "MIT"
        assert "framework-zero" in index.source["repository"]
        assert index.source.get("commit"), "the upstream commit is what makes this reproducible"

    def test_a_round_trip_through_disk_keeps_everything(self, tmp_path):
        index = Index(source={"name": "x"},
                      entries=[Entry("A", "https://x/a", "S", subsection="T",
                                     description="d", stars="1k", promoted_to="resource:tool:a")])
        save(index, tmp_path / "m.yml")
        again = load(tmp_path / "m.yml")
        assert again.entries[0] == index.entries[0]

    def test_promoted_entries_name_records_that_exist(self):
        """A dangling promotion is a link into the library that goes nowhere."""
        from ao_commons_kg.resources import load_resources

        held = {r.id for r in load_resources()}
        assert all(e.promoted_to in held for e in load().promoted)


class TestCandidates:
    """The queue that keeps profiling work visible."""

    def test_an_entry_about_agent_authority_is_a_candidate(self):
        index = Index(entries=[Entry("X", "https://x/x", "S",
                                     description="Agents can spend up to a per-task budget.")])
        assert [e.name for e in candidates(index)] == ["X"]

    def test_a_tool_already_profiled_is_not_asked_for_again(self):
        index = Index(entries=[Entry("X", "https://x/x", "S", promoted_to="resource:tool:x",
                                     description="Agents run under approval gates.")])
        assert candidates(index) == []

    def test_a_crm_is_not_a_candidate(self):
        """The list carries plenty a company buys rather than things that give
        an agent authority, and this library is not for those."""
        index = Index(entries=[Entry("A CRM", "https://x/c", "S",
                                     description="Track customers and deals in one place.")])
        assert candidates(index) == []

    def test_the_real_mirror_has_a_queue_and_it_is_not_everything(self):
        """If this ever matched most of the list it would have stopped being a
        shortlist and become noise."""
        index = load()
        waiting = candidates(index)
        assert 0 < len(waiting) < len(index.entries) / 3
