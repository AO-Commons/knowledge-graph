"""The workflow files themselves.

These run in CI and nothing else type-checks them, so a YAML mistake here is
invisible until a contributor hits it — which is exactly how it went.
"""

from __future__ import annotations

import yaml
from pathlib import Path

WORKFLOWS = Path(__file__).resolve().parent.parent / ".github" / "workflows"


class TestRunStepsReachTheShellWhole:
    """A `run:` written inline is a YAML plain scalar, and `#` after a space
    opens a comment. `run: printf 'Closes #%s\\n' "$ISSUE"` therefore reached
    the shell as `printf 'Closes` — an unbalanced quote that killed the filing
    job before it read the filing. Broken from 18 September, and the first
    filing to arrive after that is what found it.
    """

    def test_no_single_line_run_has_an_unbalanced_quote(self):
        for path in sorted(WORKFLOWS.glob("*.yml")):
            spec = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            for job, body in (spec.get("jobs") or {}).items():
                for step in body.get("steps") or []:
                    run = step.get("run")
                    if not isinstance(run, str) or "\n" in run.strip():
                        continue  # block scalars keep their `#`; only plain ones truncate
                    assert run.count("'") % 2 == 0 and run.count('"') % 2 == 0, (
                        f"{path.name} [{step.get('name', job)}]: {run!r} — a `#` "
                        "truncated this. Use a block scalar."
                    )
