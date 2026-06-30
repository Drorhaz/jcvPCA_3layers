#!/usr/bin/env python3
"""Run Layer 1 Motive QC batch from repository root."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV_PY = ROOT / "Layer1_motive_qc" / "motive_qc" / ".venv" / "bin" / "python"
SCRIPT = ROOT / "Layer1_motive_qc" / "motive_qc" / "motive_batch_qc.py"
WORKDIR = ROOT / "Layer1_motive_qc" / "motive_qc"


def main() -> int:
    if not VENV_PY.is_file():
        print(f"Layer 1 venv not found: {VENV_PY}", file=sys.stderr)
        return 1
    return subprocess.call([str(VENV_PY), str(SCRIPT), *sys.argv[1:]], cwd=WORKDIR)


if __name__ == "__main__":
    raise SystemExit(main())
