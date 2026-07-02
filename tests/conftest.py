"""Pytest bootstrap for repo-root tests (src/ on path)."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
L25_SRC = REPO_ROOT / "Layer2.5_Segmentation" / "src"
for path in (SRC, L25_SRC):
    entry = str(path)
    if path.is_dir() and entry not in sys.path:
        sys.path.insert(0, entry)
