"""The same work under a different identifier.

Generative Agents is `W4363671832` as the arXiv preprint and `W4387835442`
as published. The corpus held the first; the citation graph kept proposing
the second; the scan paid for a verdict on it three times and refused it
three times, each refusal saying it belonged at section 15.
"""
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from ao_commons_kg.duplicates import likely_same_work  # noqa: E402
from ao_commons_kg.expansion import Candidate, ScopeVerdict, select  # noqa: E402


@dataclass
class Held:
    id: str
    title: str
    authors: list
    resource_type: str = "paper"


GENERATIVE_AGENTS = Held(
    id="resource:arxiv:2304.03442",
    title="Generative Agents: Interactive Simulacra of Human Behavior",
    authors=["Joon Sung Park", "Joseph O'Brien", "Carrie J. Cai"],
    resource_type="preprint")


class TestItSeesThroughTheIdentifier:
    def test_a_near_identical_title_is_the_same_work(self):
        hits = likely_same_work(
            {"title": "Generative Agents: Interactive Simulacra of Human Behaviour",
             "authors": ["Joon Sung Park"]}, [GENERATIVE_AGENTS])
        assert hits and hits[0][0].id == GENERATIVE_AGENTS.id

    def test_a_different_paper_by_the_same_group_is_not(self):
        """Blocking on a shared byline would make the common case pay for
        the rare one."""
        hits = likely_same_work(
            {"title": "Social Simulacra: Creating Populated Prototypes",
             "authors": ["Joon Sung Park"], "resource_type": "preprint"},
            [GENERATIVE_AGENTS])
        assert not hits


class TestTheScanDoesNotPayForWhatTheCorpusKnows:
    def _run(self, title, held, judged):
        candidate = Candidate(key="openalex:W4387835442", cited_by=("a", "b"))

        def judge(c, facts):
            judged.append(c.key)
            return ScopeVerdict(admit=False, reasoning="section 15 material",
                                judged_by="test")

        return select([candidate], judge=judge,
                      metadata=lambda c: {"title": title, "authors": ["Joon Sung Park"]},
                      base=2, held=held)

    def test_a_duplicate_is_never_judged(self):
        judged = []
        out = self._run(GENERATIVE_AGENTS.title, [GENERATIVE_AGENTS], judged)
        assert judged == [], "it paid for a scope call on a record it already holds"
        assert len(out.duplicates) == 1
        assert out.duplicates[0][1] == GENERATIVE_AGENTS.id
        assert not out.rejected and not out.admitted

    def test_a_duplicate_is_not_filed_as_a_refusal(self):
        """A refusal says a work does not belong. This says it is already
        here, and the two must not be read as one."""
        out = self._run(GENERATIVE_AGENTS.title, [GENERATIVE_AGENTS], [])
        assert "already held under another identifier" in out.summary()
        assert "out of scope" in out.summary()
        assert out.summary().count("1 already held") == 1

    def test_something_genuinely_new_still_reaches_the_judge(self):
        judged = []
        out = self._run("A Totally Different Paper About Something Else",
                        [GENERATIVE_AGENTS], judged)
        assert judged == ["openalex:W4387835442"]
        assert len(out.rejected) == 1 and not out.duplicates

    def test_without_a_corpus_it_behaves_as_before(self):
        """`held` is optional, so every existing caller and test is unchanged."""
        judged = []
        out = self._run(GENERATIVE_AGENTS.title, None, judged)
        assert judged == ["openalex:W4387835442"] and not out.duplicates


class TestOneJudgmentInOnePlace:
    def test_the_filing_path_and_the_scan_use_the_same_check(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import add_resource
        assert add_resource.likely_same_work is likely_same_work


class TestThePromptCanExpressThreeStates:
    """The scan wrote "it belongs as a section 15 pointer" and then refused.

    The prompt asked what changes because agents hold authority and said that
    if nothing does, `admit` must be false. For borrowed background nothing
    does — that is what makes it background — so the instruction made the
    third state unreachable whenever the model answered honestly. 278 of 332
    refusals on record name section 15.
    """

    def _prompt(self):
        from ao_commons_kg.scope_judge import _prompt
        return _prompt({"title": "Deep Q-Networks", "abstract": "A learning algorithm."}, "")

    def test_it_no_longer_forces_a_refusal_on_the_honest_answer(self):
        assert "admit must be false" not in self._prompt()

    def test_it_says_which_booleans_each_state_is(self):
        text = self._prompt()
        assert "borrowed_background" in text
        assert "Borrowed background is an admission, not a refusal." in text

    def test_it_names_the_exact_mistake_the_scan_was_making(self):
        assert "belongs as a section 15 pointer" in self._prompt()

    def test_refusal_is_still_available_and_still_defined(self):
        text = self._prompt()
        assert "Refuse when the work is neither" in text
        assert "Refuse anything you are unsure about" in text
