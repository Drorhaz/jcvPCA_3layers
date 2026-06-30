"""Repository diagnostics for the Gaga JcvPCA workbench (Phase 0)."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any

from layer3_jcvpca import __version__ as layer3_version
from layer3_jcvpca.inventory import default_layer25_root


def repo_root_from_here() -> Path:
    """Return monorepo root assuming package lives under Layer3_JcvPCA/src."""
    return Path(__file__).resolve().parents[3]


def collect_diagnostics(repo_root: Path | None = None) -> dict[str, Any]:
    """Gather import status, known paths, and workbench feature flags."""
    repo_root = repo_root or repo_root_from_here()
    l25_root = default_layer25_root(repo_root)
    l3_outputs = repo_root / "Layer3_JcvPCA" / "outputs"
    l25_outputs = repo_root / "Layer2.5_Segmentation" / "outputs"

    layer3_import_ok = False
    layer3_import_error = ""
    try:
        importlib.import_module("layer3_jcvpca")
        layer3_import_ok = True
    except ImportError as exc:
        layer3_import_error = str(exc)

    pre_jvcpca_ok = False
    pre_jvcpca_error = ""
    pre_jvcpca_src = repo_root / "Layer2.5_Segmentation" / "src"
    if str(pre_jvcpca_src) not in sys.path:
        sys.path.insert(0, str(pre_jvcpca_src))
    try:
        importlib.import_module("pre_jvcpca_review")
        pre_jvcpca_ok = True
    except ImportError as exc:
        pre_jvcpca_error = str(exc)

    manifest_count = 0
    if l25_root.is_dir():
        manifest_count = len(list(l25_root.rglob("window_export_manifest.json")))

    return {
        "layer3_import_ok": layer3_import_ok,
        "layer3_import_error": layer3_import_error,
        "layer3_version": layer3_version,
        "pre_jvcpca_import_ok": pre_jvcpca_ok,
        "pre_jvcpca_import_error": pre_jvcpca_error,
        "repo_root": str(repo_root),
        "layer25_scan_root": str(l25_root),
        "layer25_scan_root_exists": l25_root.is_dir(),
        "layer25_manifest_count": manifest_count,
        "layer3_outputs_dir": str(l3_outputs),
        "layer3_outputs_exists": l3_outputs.is_dir(),
        "layer25_outputs_dir": str(l25_outputs),
        "layer25_outputs_exists": l25_outputs.is_dir(),
        "pytest_command": "cd Layer3_JcvPCA && .venv/bin/python -m pytest -q",
        "workbench_features": {
            "phase0_diagnostics": True,
            "phase1_data_inventory": True,
            "phase2_export_readiness": True,
            "phase3_comparable_links": True,
            "phase4_dataset_construction": True,
            "phase5_preflight": True,
            "phase6_step_runner": True,
            "phase7_pca_a": True,
            "phase9_pc_focus": True,
            "phase10_18_jcvpca_pipeline": True,
        },
    }
