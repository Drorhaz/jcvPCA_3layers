"""Tests for Layer 2.5 data inventory scanner."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from layer3_jcvpca.data_contract import (
    CENTRAL_MANIFEST_NAME,
    EXPORT_GRANULARITY_COMBINED,
    EXPORT_GRANULARITY_PER_EXERCISE,
    GAGA_EXERCISE_LABELS,
    derive_qc_status,
    exercise_metadata_from_manifest,
    parse_session_key,
)
from layer3_jcvpca.inventory import scan_layer25_exports, write_inventory_artifacts
from conftest import METADATA_COLS, make_matrix


def test_parse_session_key():
    parsed = parse_session_key("671_T1_P1_R1")
    assert parsed["participant_id"] == "671"
    assert parsed["timepoint"] == "T1"
    assert parsed["repetition"] == "R1"
    assert parsed["task_part_id"] == "P1"


def test_exercise_metadata_per_exercise_manifest():
    ex_id, label, granularity, _ = exercise_metadata_from_manifest(
        {
            "gaga_exercise_label": "P3",
            "export_granularity": "per_exercise",
            "gaga_exercise_id": 11,
        }
    )
    assert label == "P3"
    assert granularity == EXPORT_GRANULARITY_PER_EXERCISE
    assert ex_id == "11"


def test_exercise_metadata_combined_group4_inferred():
    _, label, granularity, notes = exercise_metadata_from_manifest(
        {"window_label": "671_T1_g4_s100_e200"}
    )
    assert label == "combined_group4"
    assert granularity == EXPORT_GRANULARITY_COMBINED
    assert "inferred" in notes


def test_derive_qc_status_explicit():
    status, inferred = derive_qc_status({"qc_status": "pass"})
    assert status == "pass"
    assert inferred is False


def test_derive_qc_status_inferred_warning():
    status, inferred = derive_qc_status(
        {"warnings_summary": {"n_warning": 2, "n_blocking": 0, "has_blocking": False}}
    )
    assert status == "warning"
    assert inferred is True


def _write_export_bundle(
    tmp_path: Path,
    *,
    session_id: str = "671_T1_P1_R1",
    gaga_exercise_label: str | None = None,
    gaga_exercise_id: int | None = None,
    export_granularity: str | None = None,
    window_label: str = "671_T1_P1_R1_g4_s14280_e21000",
    qc_status: str | None = None,
) -> Path:
    out = tmp_path / session_id / window_label
    out.mkdir(parents=True)
    df = make_matrix(session_id=session_id)
    matrix_path = out / "window_jvcpca_matrix.parquet"
    df.to_parquet(matrix_path, index=False)

    manifest = {
        "layer3_safe": True,
        "session_id": session_id,
        "run_label": f"{session_id}_Take",
        "window_label": window_label,
        "n_frames": len(df),
        "n_features": len(df.columns) - len(METADATA_COLS),
        "identity": {
            "participant_id": "671",
            "session_id": session_id,
            "timepoint": "T1",
            "part_id": "P1",
            "repetition_id": "R1",
        },
        "warnings_summary": {"n_warning": 1, "n_blocking": 0, "has_blocking": False},
        "created_at": "2026-06-26T00:00:00+00:00",
    }
    if gaga_exercise_label:
        manifest["gaga_exercise_label"] = gaga_exercise_label
    if gaga_exercise_id is not None:
        manifest["gaga_exercise_id"] = gaga_exercise_id
    if export_granularity:
        manifest["export_granularity"] = export_granularity
    if qc_status:
        manifest["qc_status"] = qc_status

    manifest_path = out / "window_export_manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return tmp_path


def test_scan_combined_export_flags_granularity_and_combined_only(tmp_path):
    root = _write_export_bundle(tmp_path)
    inventory = scan_layer25_exports(root)
    assert len(inventory.rows) == 1
    row = inventory.rows[0]
    assert row.gaga_exercise_label == "combined_group4"
    assert row.export_granularity == EXPORT_GRANULARITY_COMBINED
    codes = {i.issue_code for i in inventory.issues}
    assert "missing_export_granularity" in codes
    assert "combined_group4_only" in codes


def test_scan_per_exercise_export_no_combined_only_issue(tmp_path):
    root = _write_export_bundle(
        tmp_path,
        gaga_exercise_label="P2",
        export_granularity="per_exercise",
        window_label="671_T1_P1_R1_P2",
    )
    inventory = scan_layer25_exports(root)
    assert inventory.rows[0].gaga_exercise_label == "P2"
    assert inventory.rows[0].export_granularity == EXPORT_GRANULARITY_PER_EXERCISE
    assert not any(i.issue_code == "combined_group4_only" for i in inventory.issues)


def test_scan_inferred_qc_status(tmp_path):
    root = _write_export_bundle(tmp_path, export_granularity="combined_group4")
    inventory = scan_layer25_exports(root)
    assert inventory.rows[0].qc_status == "warning"
    assert any(i.issue_code == "inferred_qc_status" for i in inventory.issues)


def test_write_inventory_artifacts(tmp_path):
    root = _write_export_bundle(
        tmp_path,
        gaga_exercise_label="P1",
        export_granularity="per_exercise",
        window_label="671_T1_P1_R1_P1",
    )
    inventory = scan_layer25_exports(root)
    out_dir = tmp_path / "artifacts"
    paths = write_inventory_artifacts(inventory, out_dir)
    assert paths["inventory_csv"].is_file()
    summary = json.loads(paths["summary_json"].read_text())
    assert summary["per_exercise_export_count"] == 1
    assert "P1" in summary["gaga_exercises_found"]


@pytest.mark.parametrize("label", GAGA_EXERCISE_LABELS)
def test_gaga_exercise_id_mapping(label, tmp_path):
    ex_id = {"P1": 9, "P2": 10, "P3": 11, "P4": 12, "P5": 13}[label]
    root = _write_export_bundle(
        tmp_path,
        gaga_exercise_id=ex_id,
        export_granularity="per_exercise",
        window_label=f"w_{label}",
    )
    inventory = scan_layer25_exports(root)
    assert inventory.rows[0].gaga_exercise_label == label


def test_scan_prefers_central_manifest(tmp_path):
    window_root = _write_export_bundle(
        tmp_path / "windows",
        gaga_exercise_label="P1",
        export_granularity="per_exercise",
        window_label="671_T1_P1_R1_P1",
    )
    row = scan_layer25_exports(window_root).rows[0]
    central = tmp_path / "scan_root" / CENTRAL_MANIFEST_NAME
    central.parent.mkdir(parents=True)
    pd.DataFrame(
        [
            {
                "participant_id": row.participant_id,
                "timepoint": row.timepoint,
                "repetition": row.repetition,
                "task_part_id": row.task_part_id,
                "session_id": row.session_id,
                "run_label": row.run_label,
                "gaga_exercise_id": "9",
                "gaga_exercise_label": "P1",
                "export_granularity": EXPORT_GRANULARITY_PER_EXERCISE,
                "export_mode": EXPORT_GRANULARITY_PER_EXERCISE,
                "matrix_path": row.matrix_path,
                "manifest_path": row.manifest_path,
                "layer3_safe": "true",
                "qc_status": "pass",
                "n_frames": row.n_frames,
                "n_features": row.n_features,
                "feature_schema_id": "explicit_schema",
                "created_at": row.created_at,
            }
        ]
    ).to_csv(central, index=False)

    inventory = scan_layer25_exports(tmp_path / "scan_root")
    assert len(inventory.rows) == 1
    assert inventory.rows[0].feature_schema_id == "explicit_schema"
    assert inventory.rows[0].notes == "central_manifest"
    assert not any(i.issue_code == "inferred_gaga_exercise_label" for i in inventory.issues)
