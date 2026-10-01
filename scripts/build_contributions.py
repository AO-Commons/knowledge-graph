#!/usr/bin/env python3
"""Write data/contributions.json: who made the library, and what each part rests on.

Generated from the records that already say who did what. Edit the records,
not this file's output. See docs/contributions.md for what is counted, what
is not, and why nothing is weighted.

Usage: python3 scripts/build_contributions.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from ao_commons_kg.contributions import load_ledger, summarize  # noqa: E402

OUT = REPO / "data" / "contributions.json"


def main() -> int:
    payload = {
        "generated_by": "scripts/build_contributions.py — do not edit; rebuilt from the "
                        "records that say who did what",
        "how_to_read": "Counts, not scores. Nothing here is weighted or ranked, and "
                       "people are listed by name. Every contribution names the file it "
                       "was read from. `builds_on` is what it rests on, and `used_by` is "
                       "how later work uses it, recomputed on every build. Machine "
                       "contributions are listed apart and are never a person's judgment. "
                       "See docs/contributions.md.",
        **summarize(load_ledger()),
    }
    OUT.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    counts = payload["counts"]
    print(f"wrote {OUT.relative_to(REPO)}")
    print(f"  {counts['people']} people, {counts['machines']} machines, "
          f"{counts['contributions']} contributions")
    for kind, n in counts["by_kind"].items():
        print(f"  {n:5} {kind}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
