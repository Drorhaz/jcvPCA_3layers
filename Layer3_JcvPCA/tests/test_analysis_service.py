"""Analysis service integration tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from layer3_jcvpca.analysis_service import AnalysisIdentity, AnalysisParams, run_direct_analysis
from layer3_jcvpca.preflight import run_preflight
from test_preflight_ui import CANONICAL_FEATURES, _write_manifest, _write_matrix


def test_analysis_writes_stability_artifacts(tmp_path):
    paths = {}
    for role in ("A", "B", "NV_A", "NV_B"):
        p = tmp_path / f"{role}.parquet"
        _write_matrix(p)
        _write_manifest(p.parent / "window_export_manifest.json")
        paths[role] = str(p)
    preflight = run_preflight(paths)
    identity = AnalysisIdentity(analysis_id="test_run", participant_id="671")
    params = AnalysisParams(pc_selection_mode="fixed_n", n_pcs=2)
    out = tmp_path / "out"
    result = run_direct_analysis(paths, identity, params, out, preflight=preflight)
    assert result.status == "completed"
    assert (out / "matrix_stability_report.csv").is_file()
    assert (out / "feature_variance_table.csv").is_file()
    assert (out / "main_vs_nv_comparison_table.csv").is_file()
    manifest = json.loads((out / "analysis_manifest.json").read_text())
    assert manifest["matrix_stability_checked"] is True
    assert "rank_A" in manifest
