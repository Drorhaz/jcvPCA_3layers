#!/usr/bin/env python3
"""Run Layer 3 read-only validators from repository root."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV_PY = ROOT / "Layer3_JcvPCA" / ".venv" / "bin" / "python"
SCRIPTS = ROOT / "Layer3_JcvPCA" / "scripts"

CHECKS: list[tuple[str, list[str]]] = [
    ("generate_final_integrated_review.py", ["--validate-paths"]),
    ("generate_master_full_numeric_report.py", ["--dry-run"]),
    ("generate_directional_robustness_full_numeric_report.py", ["--validate-paths"]),
    ("generate_nullspace_full_numeric_report.py", ["--dry-run"]),
    ("generate_movement_organization_question_report.py", ["--validate-paths"]),
]


def main() -> int:
    if not VENV_PY.is_file():
        print(f"Layer 3 venv not found: {VENV_PY}", file=sys.stderr)
        return 1

    for script_name, args in CHECKS:
        script = SCRIPTS / script_name
        print(f"==> {script_name} {' '.join(args)}", flush=True)
        rc = subprocess.call([str(VENV_PY), str(script), *args], cwd=SCRIPTS)
        if rc != 0:
            return rc
    print("All Layer 3 validators passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
