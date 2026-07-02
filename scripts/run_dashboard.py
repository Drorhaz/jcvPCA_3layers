#!/usr/bin/env python3
"""Launch the 3Layers Streamlit dashboard from repository root."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "Dashboard" / "run_dashboard.sh"


def main() -> int:
    if not SCRIPT.is_file():
        print(f"Dashboard launcher not found: {SCRIPT}", file=sys.stderr)
        return 1
    return subprocess.call([str(SCRIPT), *sys.argv[1:]], cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
