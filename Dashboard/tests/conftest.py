"""Pytest bootstrap for Dashboard tests."""

from __future__ import annotations

import sys
from pathlib import Path

DASHBOARD_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = DASHBOARD_ROOT.parent
REPO_SRC = REPO_ROOT / "src"

for entry in (str(REPO_SRC), str(DASHBOARD_ROOT)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from ui_bootstrap import configure_python_paths

configure_python_paths()
