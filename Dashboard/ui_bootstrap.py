"""Shared path bootstrap for the 3Layers Streamlit dashboard (thin UI client)."""

from __future__ import annotations

import sys
from pathlib import Path

DASHBOARD_ROOT = Path(__file__).resolve().parent
REPO_ROOT = DASHBOARD_ROOT.parent
LAYER25_ROOT = REPO_ROOT / "Layer2.5_Segmentation"
LAYER3_ROOT = REPO_ROOT / "Layer3_JcvPCA"
LAYER25_SRC = LAYER25_ROOT / "src"
LAYER3_SRC = LAYER3_ROOT / "src"
REPO_SRC = REPO_ROOT / "src"


def configure_python_paths() -> None:
    """Ensure layer packages and dashboard helpers are importable."""
    for path in (LAYER25_SRC, LAYER3_SRC, REPO_SRC, DASHBOARD_ROOT):
        entry = str(path)
        if path.is_dir() and entry not in sys.path:
            sys.path.insert(0, entry)
