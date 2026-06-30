#!/usr/bin/env python3
"""Run Layer 2.5 Gaga export builder from repository root."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV_PY = ROOT / "Layer2.5_Segmentation" / ".venv" / "bin" / "python"
SCRIPT = ROOT / "Layer2.5_Segmentation" / "scripts" / "build_gaga_exports.py"
WORKDIR = ROOT / "Layer2.5_Segmentation"


def main() -> int:
    if not VENV_PY.is_file():
        print(f"Layer 2.5 venv not found: {VENV_PY}", file=sys.stderr)
        return 1
    return subprocess.call([str(VENV_PY), str(SCRIPT), *sys.argv[1:]], cwd=WORKDIR)


if __name__ == "__main__":
    raise SystemExit(main())
