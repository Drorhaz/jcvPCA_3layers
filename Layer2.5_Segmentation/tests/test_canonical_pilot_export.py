"""Tests for canonical pilot manifest and export validation."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from pre_jvcpca_review.canonical_manifest import (
    CANONICAL_NAMING_POLICY,
    DEFAULT_PILOT_MANIFEST,
    ManifestError,
    canonical_feature_name,
    expected_pilot_feature_order,
    load_pilot_manifest,
    pilot_feature_order,
    resolve_session_links_from_manifest,
)
from pre_jvcpca_review.export_window import WindowExportError, export_pilot_window_for_jvcpca
from pre_jvcpca_review.load_layer2 import LinkRecord
from pre_jvcpca_review.pilot_export_validation import (
    PilotExportValidationError,
    validate_single_pilot_matrix,
)

ROOT = Path(__file__).resolve().parents[1]
EVAL_DIR = ROOT / "reevluate_project"


@pytest.fixture(scope="module")
def pilot_manifest():
    return load_pilot_manifest(DEFAULT_PILOT_MANIFEST)


def test_manifest_loads_with_canonical_names(pilot_manifest):
    assert len(pilot_manifest) == 30
    assert pilot_feature_order(pilot_manifest)[0] == "Neck_to_Head_rx"
    assert canonical_feature_name("Neck", "Head", "rx") == "Neck_to_Head_rx"


def test_resolve_links_by_parent_child_not_joint_id(pilot_manifest):
    # Same canonical link may map to different session link_ids across templates;
    # reevaluate_project uses T1-style IDs.
    session_links = [
        LinkRecord("J004", "Neck", "Head", "core_candidate", "pass", "Neck->Head"),
        LinkRecord("J005", "LUArm", "LFArm", "core_candidate", "warning", "LUArm->LFArm"),
    ]
    # Manifest includes Neck->Head and LUArm->LFArm among others; partial resolution fails
    with pytest.raises(ManifestError, match="missing canonical link"):
        resolve_session_links_from_manifest(pilot_manifest, session_links)


def test_pilot_export_validation_rejects_bad_order(tmp_path, pilot_manifest):
    if not EVAL_DIR.is_dir():
        pytest.skip("reevluate_project fixtures not available")

    out = tmp_path / "pilot_export"
    paths = export_pilot_window_for_jvcpca(
        EVAL_DIR,
        EVAL_DIR,
        out,
        frame_start=0,
        frame_end=100,
        allow_nan_matrix=True,
    )
    matrix_df = pd.read_parquet(paths["jvcpca_matrix"])
    feature_order = pilot_feature_order(pilot_manifest)
    session_links = [
        LinkRecord(
            link_id=str(row["link_id"]),
            parent_canonical=str(row["parent_canonical"]),
            child_canonical=str(row["child_canonical"]),
            feature_scope=str(row["feature_scope"]),
            stage07_jump_status=str(row.get("stage07_jump_status", "pass")),
            display_name=f"{row['parent_canonical']}->{row['child_canonical']}",
        )
        for _, row in pd.read_csv(EVAL_DIR / "layer2_qc_link_manifest.csv").iterrows()
    ]
    _, links_by_canonical = resolve_session_links_from_manifest(pilot_manifest, session_links)

    validate_single_pilot_matrix(
        matrix_df,
        DEFAULT_PILOT_MANIFEST,
        session_links,
        allow_nan=True,
    )

    bad = matrix_df.rename(columns={feature_order[0]: "wrong_feature_name"})
    with pytest.raises(PilotExportValidationError):
        validate_single_pilot_matrix(
            bad,
            DEFAULT_PILOT_MANIFEST,
            session_links,
            allow_nan=True,
            report_path=tmp_path / "fail_report.json",
        )


def test_pilot_export_uses_canonical_feature_names(tmp_path):
    if not EVAL_DIR.is_dir():
        pytest.skip("reevluate_project fixtures not available")

    out = tmp_path / "pilot"
    paths = export_pilot_window_for_jvcpca(
        EVAL_DIR,
        EVAL_DIR,
        out,
        frame_start=14280,
        frame_end=14300,
    )
    import json

    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    assert manifest["feature_naming_policy"] == CANONICAL_NAMING_POLICY
    assert manifest["feature_order"][0] == "Neck_to_Head_rx"
    assert "J004" not in manifest["feature_order"][0]

    matrix_df = pd.read_parquet(paths["jvcpca_matrix"])
    feature_cols = [c for c in matrix_df.columns if c not in ("session_id", "run_label", "frame", "time_sec")]
    assert feature_cols == manifest["feature_order"]
    assert (out / "pilot_export_validation_report.json").exists()


def test_pilot_export_fails_on_nan_without_allow(tmp_path):
    if not EVAL_DIR.is_dir():
        pytest.skip("reevluate_project fixtures not available")

    with pytest.raises(WindowExportError, match="NaNs in pilot JcvPCA matrix"):
        export_pilot_window_for_jvcpca(
            EVAL_DIR,
            EVAL_DIR,
            tmp_path / "should_fail",
            frame_start=16000,
            frame_end=17000,
            allow_nan_matrix=False,
        )
