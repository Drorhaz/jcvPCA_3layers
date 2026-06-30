#!/usr/bin/env python3
"""Run Layer 3 Gaga JcvPCA batch from repository root."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV_PY = ROOT / "Layer3_JcvPCA" / ".venv" / "bin" / "python"
SCRIPT = ROOT / "Layer3_JcvPCA" / "scripts" / "run_gaga_batch_jcvpca.py"


def main() -> int:
    if not VENV_PY.is_file():
        print(f"Layer 3 venv not found: {VENV_PY}", file=sys.stderr)
        return 1
    return subprocess.call([str(VENV_PY), str(SCRIPT), *sys.argv[1:]], cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
