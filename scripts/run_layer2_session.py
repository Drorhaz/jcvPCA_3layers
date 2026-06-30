#!/usr/bin/env python3
"""Run Layer 2 kinematics CLI from repository root."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV_PY = ROOT / "Layer2_Motive_Kinematics" / ".venv" / "bin" / "python"
WORKDIR = ROOT / "Layer2_Motive_Kinematics"


def main() -> int:
    if not VENV_PY.is_file():
        print(f"Layer 2 venv not found: {VENV_PY}", file=sys.stderr)
        return 1
    return subprocess.call(
        [str(VENV_PY), "-m", "layer2_motive.cli", *sys.argv[1:]],
        cwd=WORKDIR,
    )


if __name__ == "__main__":
    raise SystemExit(main())
