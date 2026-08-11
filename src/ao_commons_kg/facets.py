"""The F1–F12 facet vocabularies.

The taxonomy answers *what is this research about*. The facets answer *what
kind of evidence is this, and when does it apply*. They are controlled
metadata fields on a Resource — deliberately flat, never a second tree.

Adding a value here is a schema change: exports carry these strings, and
downstream filters match on them literally. Renaming one breaks consumers,
so prefer adding a value to redefining an existing one.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Facet:
    code: str
    name: str
    question: str
    values: tuple[str, ...]
    multi: bool = True
    """Most facets take several values: a paper can address two organizational
    functions, or serve two stakeholder perspectives. The exceptions are the
    axes where a second value would mean the first is wrong."""


FACETS: tuple[Facet, ...] = (
    Facet(
        "F1", "artifact_type", "What kind of thing is this?",
        (
            "peer-reviewed-paper", "preprint", "technical-report",
            "standard-specification", "regulation", "framework-guideline",
            "dataset", "code-tool", "essay", "governance-proposal",
            "postmortem", "incident-report", "audit-report", "legal-opinion",
            "talk-interview",
        ),
        multi=False,
    ),
    Facet(
        "F2", "evidence_strength", "How strong is the evidence?",
        (
            "formal-proof", "empirical-with-replication-data",
            "empirical-single-study", "simulation", "structured-case-study",
            "expert-synthesis", "argumentative-essay", "opinion-advocacy",
            "marketing-content",
        ),
        multi=False,
    ),
    Facet(
        "F3", "autonomy_level_addressed", "How much authority do the agents have?",
        (
            "human-decision-machine-support", "machine-proposal-human-approval",
            "machine-decision-human-veto-window", "fully-autonomous-execution",
            "mixed-unspecified",
        ),
    ),
    Facet(
        "F4", "organizational_function", "Which organizational function?",
        (
            "governance", "treasury-allocation", "operations", "security",
            "evaluation", "external-interaction", "meta-organizational",
        ),
    ),
    Facet(
        "F5", "agent_count_regime", "How many agents?",
        ("single-agent", "small-team", "large-fleet", "cross-organizational", "unspecified"),
    ),
    Facet(
        "F6", "failure_relevance", "How does it relate to failure?",
        (
            "describes-a-failure", "analyzes-a-failure", "proposes-preventive-control",
            "proposes-detective-control", "proposes-corrective-control",
            "evaluates-control-effectiveness",
        ),
    ),
    Facet(
        "F7", "control_type", "What kind of control?",
        ("technical", "procedural", "economic", "legal", "social"),
    ),
    Facet(
        "F8", "source_independence", "Who produced it, and what is their stake?",
        (
            "independent-academic", "independent-practitioner", "model-provider",
            "tooling-vendor", "self-study-by-subject-organization",
            "funded-by-subject", "undisclosed",
        ),
        multi=False,
    ),
    Facet(
        "F9", "maturity_of_subject", "How real is the thing being described?",
        (
            "theoretical-proposal", "prototype", "limited-deployment",
            "production-at-scale", "deprecated",
        ),
        multi=False,
    ),
    Facet(
        "F10", "temporal_relevance", "Does it still hold?",
        ("foundational", "current", "dated-but-instructive", "superseded-by-capability-change"),
        multi=False,
    ),
    Facet(
        "F11", "stakeholder_perspective", "Whose point of view?",
        (
            "operator", "overseer", "affected-external-party", "regulator",
            "adversary", "agent-developer", "researcher",
        ),
    ),
    Facet(
        "F12", "applicability", "How directly can a reader use it?",
        ("directly-actionable", "adaptable-with-modification", "background",
         "comparative-reference-only"),
        multi=False,
    ),
)

BY_NAME: dict[str, Facet] = {facet.name: facet for facet in FACETS}
BY_CODE: dict[str, Facet] = {facet.code: facet for facet in FACETS}


class FacetError(ValueError):
    """A facet value that is not in its controlled vocabulary."""


def validate(facets: dict[str, object]) -> dict[str, list[str]]:
    """Check a resource's facet mapping and return it normalized.

    Single-valued facets accept a bare string or a one-item list and always
    come back as a list, so consumers never have to branch on type. Unknown
    facet names and unknown values are errors rather than warnings: a typo
    that passes silently produces a resource that no filter will ever match,
    which is worse than a resource that fails to load.
    """
    normalized: dict[str, list[str]] = {}
    for name, raw in facets.items():
        facet = BY_NAME.get(name)
        if facet is None:
            raise FacetError(
                f"unknown facet {name!r}; expected one of {sorted(BY_NAME)}"
            )
        values = [raw] if isinstance(raw, str) else list(raw)
        if not facet.multi and len(values) > 1:
            raise FacetError(
                f"{facet.code} ({name}) takes a single value, got {values!r}"
            )
        for value in values:
            if value not in facet.values:
                raise FacetError(
                    f"{facet.code} ({name}) has no value {value!r}; "
                    f"expected one of {list(facet.values)}"
                )
        if values:
            normalized[name] = values
    return normalized
