"""Preflight and controller gating tests."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from layer3_jcvpca.app_controller import Layer3AnalysisController
from layer3_jcvpca.preflight import run_preflight
from conftest import FEATURE_NAMES, METADATA_COLS, make_matrix


CANONICAL_FEATURES = [
    "Neck_to_Head_rx",
    "Neck_to_Head_ry",
    "Neck_to_Head_rz",
    "Chest_to_Neck_rx",
    "Chest_to_Neck_ry",
    "Chest_to_Neck_rz",
]


def _write_matrix(path, session_id: str = "671_T1_P1_R1", n_rows: int = 200, features=None):
    features = features or CANONICAL_FEATURES
    rng = np.random.default_rng(42)
    data = rng.standard_normal((n_rows, len(features)))
    df = pd.DataFrame(data, columns=features)
    df.insert(0, "time_sec", np.arange(n_rows) / 120.0)
    df.insert(0, "frame", np.arange(n_rows))
    df.insert(0, "run_label", f"{session_id}_Take")
    df.insert(0, "session_id", session_id)
    df.to_parquet(path)


def _write_manifest(path, layer3_safe: bool = True):
    import json

    path.write_text(
        json.dumps(
            {
                "layer3_safe": layer3_safe,
                "n_frames": 200,
                "warnings_summary": {"n_warnings": 0},
                "warnings": [],
            }
        )
    )


def test_preflight_identical_features_pass(tmp_path):
    paths = {}
    for role in ("A", "B", "NV_A", "NV_B"):
        p = tmp_path / f"{role}.parquet"
        _write_matrix(p, session_id=f"671_T1_P1_R1" if "NV_B" != role else "671_T1_P1_R2")
        _write_manifest(p.parent / "window_export_manifest.json")
        paths[role] = str(p)
    report = run_preflight(paths)
    assert report.status in ("pass", "warning")
    assert report.feature_names == CANONICAL_FEATURES


def test_feature_order_mismatch_blocks(tmp_path):
    paths = {}
    order_a = CANONICAL_FEATURES
    order_b = list(reversed(CANONICAL_FEATURES))
    for role in ("A", "NV_A"):
        p = tmp_path / f"{role}.parquet"
        _write_matrix(p, features=order_a)
        _write_manifest(p.parent / "window_export_manifest.json")
        paths[role] = str(p)
    for role in ("B", "NV_B"):
        p = tmp_path / f"{role}.parquet"
        _write_matrix(p, features=order_b)
        _write_manifest(p.parent / "window_export_manifest.json")
        paths[role] = str(p)
    report = run_preflight(paths)
    assert report.status == "blocking"


def test_j00x_identity_rejected(tmp_path):
    j00x = ["J004_Neck_to_Head_rx", "J004_Neck_to_Head_ry", "J004_Neck_to_Head_rz"]
    paths = {}
    for role in ("A", "B", "NV_A", "NV_B"):
        p = tmp_path / f"{role}.parquet"
        _write_matrix(p, features=j00x)
        _write_manifest(p.parent / "window_export_manifest.json")
        paths[role] = str(p)
    report = run_preflight(paths)
    assert report.status == "blocking"


def test_layer3_safe_false_blocks(tmp_path):
    paths = {}
    for role in ("A", "B", "NV_A", "NV_B"):
        p = tmp_path / f"{role}.parquet"
        _write_matrix(p)
        _write_manifest(p.parent / "window_export_manifest.json", layer3_safe=False)
        paths[role] = str(p)
    report = run_preflight(paths)
    assert report.status == "blocking"


def test_controller_blocks_on_blocking(tmp_path):
    ctrl = Layer3AnalysisController(repo_root=tmp_path)
    paths = {}
    for role in ("A", "B", "NV_A", "NV_B"):
        p = tmp_path / f"{role}.parquet"
        df = make_matrix(n_rows=5, seed=1)  # too few rows
        df.to_parquet(p)
        paths[role] = str(p)
    ctrl.load_preflight(paths)
    can_run, _ = ctrl.can_run()
    assert not can_run


def test_controller_allows_with_warning_ack(tmp_path):
    ctrl = Layer3AnalysisController(repo_root=tmp_path)
    paths = {}
    for role in ("A", "B", "NV_A", "NV_B"):
        p = tmp_path / f"{role}.parquet"
        _write_matrix(p)
        _write_manifest(p.parent / "window_export_manifest.json")
        paths[role] = str(p)
    ctrl.load_preflight(paths)
    if ctrl.preflight_report.status == "warning":
        ctrl.warnings_acknowledged = True
        can_run, _ = ctrl.can_run()
        assert can_run
