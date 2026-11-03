"""A workflow must install what its own steps import.

Issue #80 was an arXiv link submitted through the form. The bot ran, reached
the scope gate, and answered `ModuleNotFoundError: No module named
'anthropic'` — because the gate was added to `new-resource.yml` without
adding `scope` to its install line. The gate behaved correctly, refusing
rather than approving and saying so on the issue, which is why this was a
closed door rather than a silent admission. A closed door is still a door
nobody gets through.
"""
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = sorted((ROOT / ".github" / "workflows").glob("*.yml"))

#: What a thing a workflow might run needs installed. Keyed on what appears
#: in a `run:` block, valued on the extra that supplies its import.
NEEDS = {
    "judge_suggestion.py": "scope",
    "aokg grow": "scope",
    "aokg profile": "scope",
    "aokg resolve": "scholarly",
    "aokg expand": "scholarly",
    "add_resource.py": "scholarly",
    "validate_mira.py": "mira",
}


def runs(workflow: dict) -> str:
    """Every shell command the workflow runs, as one string."""
    out = []
    for job in (workflow.get("jobs") or {}).values():
        for step in job.get("steps") or []:
            if isinstance(step.get("run"), str):
                out.append(step["run"])
    return "\n".join(out)


def installs(text: str) -> set[str]:
    extras: set[str] = set()
    for match in re.finditer(r"pip install[^\n]*\.\[([a-z,\s]+)\]", text):
        extras |= {e.strip() for e in match.group(1).split(",") if e.strip()}
    return extras


@pytest.mark.parametrize("path", WORKFLOWS, ids=lambda p: p.name)
def test_it_installs_what_it_runs(path):
    workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not workflow or "jobs" not in workflow:
        pytest.skip("not a workflow with jobs")
    commands = runs(workflow)
    have = installs(commands)
    for thing, extra in NEEDS.items():
        if thing in commands:
            assert extra in have, (
                f"{path.name} runs {thing!r}, which needs the {extra!r} extra, "
                f"but installs {sorted(have) or 'nothing'}")


def test_the_map_is_not_quietly_empty():
    """A map that matches nothing passes every test above and checks none."""
    matched = {thing for path in WORKFLOWS
               for thing in NEEDS
               if thing in runs(yaml.safe_load(path.read_text(encoding="utf-8")) or {})}
    assert len(matched) >= 4, f"only matched {sorted(matched)}"


def test_the_extras_named_here_exist():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    after = pyproject.split("[project.optional-dependencies]", 1)[1]
    # The next TOML table, which is a '[' at the start of a line — not the
    # '[' that opens a dependency list on the right of an '='.
    block = re.split(r"^\[", after, maxsplit=1, flags=re.M)[0]
    declared = set(re.findall(r"^([a-z]+)\s*=", block, re.M))
    assert set(NEEDS.values()) <= declared, sorted(set(NEEDS.values()) - declared)
