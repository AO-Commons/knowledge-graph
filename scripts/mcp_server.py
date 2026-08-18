#!/usr/bin/env python3
"""Kept so an existing registration keeps working.

The server moved into the package as `ao_commons_kg.mcp_server`, so it can be
launched as `aokg-mcp` from anywhere instead of by absolute path. Anyone who
had already pointed Claude at this file should not have to notice.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ao_commons_kg.mcp_server import main  # noqa: E402

if __name__ == "__main__":
    main()
