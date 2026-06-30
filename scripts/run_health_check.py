#!/usr/bin/env python3
"""Run the project path health check from repository root."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / "scripts" / "check_project_paths.py"


def main() -> int:
    return subprocess.call([sys.executable, str(CHECK)], cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
