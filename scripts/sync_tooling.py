#!/usr/bin/env python3
"""Re-read awesome-builder-tools and report what moved.

    python3 scripts/sync_tooling.py            # report only
    python3 scripts/sync_tooling.py --write    # update the mirror too

Run weekly by `.github/workflows/tooling-sync.yml`, which opens an issue when
the list changes rather than committing quietly: an upstream edit is somebody
else's editorial judgement, and it should arrive as something to read.

The upstream commit is recorded with every sync, so "which version of their
list is this" has an answer that does not depend on a date and a guess.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from ao_commons_kg import tooling  # noqa: E402

RAW = "https://raw.githubusercontent.com/framework-zero/awesome-builder-tools/main/README.md"
API = "https://api.github.com/repos/framework-zero/awesome-builder-tools/commits/main"
CONTACT = "anke@stellar.org"


def fetch(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": f"ao-commons-kg ({CONTACT})"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", "ignore")


def upstream_commit() -> dict:
    try:
        payload = json.loads(fetch(API))
        return {
            "commit": payload["sha"][:12],
            "committed_at": payload["commit"]["committer"]["date"][:10],
        }
    except Exception:  # noqa: BLE001 — a missing sha must not block a sync
        return {}


def report(changes: dict, index: tooling.Index) -> str:
    lines = []
    if changes["added"]:
        lines += ["", f"### {len(changes['added'])} added upstream", ""]
        lines += [f"- [{e.name}]({e.url}) — *{e.subsection or e.section}*"
                  for e in changes["added"]]
    if changes["removed"]:
        lines += ["", f"### {len(changes['removed'])} removed upstream", ""]
        for entry in changes["removed"]:
            note = (f" — **we profiled this as `{entry.promoted_to}`**, so it stays in the "
                    "library and needs a look" if entry.promoted_to else "")
            lines.append(f"- [{entry.name}]({entry.url}){note}")
    if changes["changed"]:
        lines += ["", f"### {len(changes['changed'])} reworded upstream", ""]
        lines += [f"- [{new.name}]({new.url})" for _, new in changes["changed"]]

    waiting = tooling.candidates(index)
    if waiting:
        lines += ["", f"### {len(waiting)} worth a look", "",
                  "Listed upstream, not yet profiled here, and described in terms of what "
                  "agents may do or what constrains them. Reading the tool's own "
                  "documentation is what settles it:", ""]
        lines += [f"- [{e.name}]({e.url}) — *{e.subsection or e.section}*" for e in waiting]

    if not lines:
        return "The list is unchanged since the last sync, and nothing is waiting to be profiled."

    promoted = len(index.promoted)
    lines += [
        "",
        "---",
        "",
        f"The mirror now holds {len(index.entries)} entries, of which {promoted} have been "
        "profiled into the library.",
        "",
        "Nothing enters the corpus from this automatically. An entry becomes a record "
        "when somebody has read the tool's own documentation and can say what oversight "
        "it ships — upstream's one-line description is their judgement, not evidence.",
        "",
        f"Source: [{tooling.UPSTREAM}]({tooling.UPSTREAM}) — Framework Zero, MIT.",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="update the mirror file")
    parser.add_argument("--report-file", default="", help="write the summary here")
    args = parser.parse_args(argv)

    before = tooling.load()
    try:
        markdown = fetch(RAW)
    except Exception as error:  # noqa: BLE001
        print(f"could not read upstream: {error}", file=sys.stderr)
        return 1

    entries = tooling.parse_readme(markdown)
    if not entries:
        # A silent zero would wipe the mirror and read as "they deleted
        # everything", when it means their README changed shape.
        print("parsed no entries — upstream's format has probably changed", file=sys.stderr)
        return 1

    after = tooling.carry_promotions(before, tooling.Index(
        source={
            "name": "awesome-builder-tools",
            "repository": tooling.UPSTREAM,
            "maintainer": "Framework Zero",
            "license": "MIT",
            "synced_at": date.today().isoformat(),
            **upstream_commit(),
            "note": ("Mirrored with attribution under the MIT licence. Descriptions are "
                     "upstream's own words. Nothing here is a claim by AO Commons about a "
                     "tool; a profiled record in data/resources/ is."),
        },
        entries=entries,
    ))

    changes = tooling.diff(before, after)
    summary = report(changes, after)
    print(summary)
    if args.report_file:
        Path(args.report_file).write_text(summary, encoding="utf-8")

    if args.write:
        tooling.save(after)
        print(f"\nwrote {tooling.DEFAULT_PATH.relative_to(REPO)}")

    # Exit 0 whether or not it moved; the workflow decides what to do with it.
    return 0


if __name__ == "__main__":
    sys.exit(main())
