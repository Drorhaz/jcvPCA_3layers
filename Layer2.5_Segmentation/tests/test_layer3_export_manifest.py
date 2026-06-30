"""Tests for centralized Layer 2.5 export manifest and export readiness."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from pre_jvcpca_review.exercise_segments import (
    EXPORT_GRANULARITY_COMBINED,
    EXPORT_GRANULARITY_PER_EXERCISE,
    GAGA_EXERCISE_ID_TO_LABEL,
    GAGA_EXERCISE_LABELS,
    default_exercise_segments_path,
    exercise_segments_path_for_participant,
)
from pre_jvcpca_review.layer3_export_manifest import (
    ATTEMPT_STATUS_FAILED,
    ATTEMPT_STATUS_SKIPPED,
    READINESS_BLOCKING,
    READINESS_PASS,
    READINESS_WARNING,
    SESSION_STATUS_FAILED,
    SESSION_STATUS_SKIPPED,
    GagaExportMetadata,
    apply_gaga_export_metadata,
    build_export_readiness_report,
    build_session_coverage_diff,
    load_layer25_export_manifest,
    manifest_row_from_window_manifest,
    write_export_attempts_report,
    write_layer25_export_manifest,
)


def test_gaga_exercise_id_to_label_mapping() -> None:
    assert GAGA_EXERCISE_ID_TO_LABEL[9] == "P1"
    assert GAGA_EXERCISE_ID_TO_LABEL[13] == "P5"
    assert tuple(GAGA_EXERCISE_ID_TO_LABEL.values()) == GAGA_EXERCISE_LABELS


def test_apply_gaga_export_metadata_patches_manifest() -> None:
    payload = {
        "identity": {"part_id": "P1", "timepoint": "T1", "repetition_id": "R1"},
        "canonical_feature_order": ["a", "b", "c"],
        "warnings_summary": {"n_warning": 0, "n_blocking": 0, "has_blocking": False},
    }
    out = apply_gaga_export_metadata(
        payload,
        metadata=GagaExportMetadata(
            gaga_exercise_id=10,
            gaga_exercise_label="P2",
            export_granularity=EXPORT_GRANULARITY_PER_EXERCISE,
        ),
        warnings_summary=payload["warnings_summary"],
        manifest_path="/tmp/manifest.json",
        matrix_path="/tmp/matrix.parquet",
    )
    assert out["gaga_exercise_id"] == "10"
    assert out["gaga_exercise_label"] == "P2"
    assert out["export_granularity"] == EXPORT_GRANULARITY_PER_EXERCISE
    assert out["export_mode"] == EXPORT_GRANULARITY_PER_EXERCISE
    assert out["qc_status"] == "pass"
    assert out["feature_schema_id"]


def test_manifest_row_from_window_manifest() -> None:
    manifest = {
        "selected_participant": "671",
        "session_id": "671_T1_P1_R2",
        "run_label": "671_T1_P1_R2_Take",
        "task_part_id": "P1",
        "gaga_exercise_id": "11",
        "gaga_exercise_label": "P3",
        "export_granularity": EXPORT_GRANULARITY_PER_EXERCISE,
        "export_mode": EXPORT_GRANULARITY_PER_EXERCISE,
        "layer3_safe": True,
        "qc_status": "pass",
        "n_frames": 100,
        "n_features": 42,
        "feature_schema_id": "abc123",
        "created_at": "2026-06-26T00:00:00+00:00",
        "identity": {
            "timepoint": "T1",
            "repetition_id": "R2",
            "part_id": "P1",
        },
    }
    row = manifest_row_from_window_manifest(
        manifest,
        manifest_path="/tmp/window_export_manifest.json",
        matrix_path="/tmp/window_jvcpca_matrix.parquet",
    )
    assert row["participant_id"] == "671"
    assert row["gaga_exercise_label"] == "P3"
    assert row["export_granularity"] == EXPORT_GRANULARITY_PER_EXERCISE
    assert row["matrix_path"].endswith("window_jvcpca_matrix.parquet")


def test_write_layer25_export_manifest_columns(tmp_path: Path) -> None:
    rows = [
        {
            "participant_id": "671",
            "timepoint": "T1",
            "repetition": "R2",
            "task_part_id": "P1",
            "session_id": "671_T1_P1_R2",
            "run_label": "671_T1_P1_R2_Take",
            "gaga_exercise_id": "",
            "gaga_exercise_label": "combined_group4",
            "export_granularity": EXPORT_GRANULARITY_COMBINED,
            "export_mode": EXPORT_GRANULARITY_COMBINED,
            "matrix_path": str(tmp_path / "m.parquet"),
            "manifest_path": str(tmp_path / "manifest.json"),
            "layer3_safe": "true",
            "qc_status": "pass",
            "n_frames": 10,
            "n_features": 5,
            "feature_schema_id": "hash1",
            "created_at": "2026-06-26T00:00:00+00:00",
        }
    ]
    out = write_layer25_export_manifest(rows, tmp_path / "layer25_export_manifest.csv")
    df = pd.read_csv(out)
    assert list(df.columns) == [
        "participant_id",
        "timepoint",
        "repetition",
        "task_part_id",
        "session_id",
        "run_label",
        "gaga_exercise_id",
        "gaga_exercise_label",
        "export_granularity",
        "export_mode",
        "matrix_path",
        "manifest_path",
        "layer3_safe",
        "qc_status",
        "n_frames",
        "n_features",
        "feature_schema_id",
        "created_at",
    ]
    assert df.iloc[0]["gaga_exercise_label"] == "combined_group4"


def test_build_export_readiness_report_pass_and_missing() -> None:
    complete_rows = []
    for label, ex_id in zip(GAGA_EXERCISE_LABELS, range(9, 14)):
        complete_rows.append(
            {
                "participant_id": "671",
                "timepoint": "T1",
                "repetition": "R2",
                "session_id": "671_T1_P1_R2",
                "gaga_exercise_label": label,
                "export_granularity": EXPORT_GRANULARITY_PER_EXERCISE,
                "qc_status": "pass",
                "layer3_safe": "true",
                "matrix_path": f"/tmp/{label}.parquet",
            }
        )
    complete_rows.append(
        {
            "participant_id": "671",
            "timepoint": "T1",
            "repetition": "R2",
            "session_id": "671_T1_P1_R2",
            "gaga_exercise_label": "combined_group4",
            "export_granularity": EXPORT_GRANULARITY_COMBINED,
            "qc_status": "pass",
            "layer3_safe": "true",
            "matrix_path": "/tmp/g4.parquet",
        }
    )
    report = build_export_readiness_report(pd.DataFrame(complete_rows))
    assert report.iloc[0]["readiness_status"] == READINESS_PASS
    assert bool(report.iloc[0]["combined_group4_present"]) is True
    assert report.iloc[0]["per_exercise_count"] == 5
    assert report.iloc[0]["missing_gaga_labels"] == ""

    partial = pd.DataFrame(complete_rows[:2])
    partial_report = build_export_readiness_report(partial)
    assert partial_report.iloc[0]["readiness_status"] == READINESS_WARNING
    assert "P3" in partial_report.iloc[0]["missing_gaga_labels"]

    blocking = pd.DataFrame(
        [
            {
                "participant_id": "671",
                "timepoint": "T1",
                "repetition": "R2",
                "session_id": "671_T1_P1_R2",
                "gaga_exercise_label": "P1",
                "export_granularity": EXPORT_GRANULARITY_PER_EXERCISE,
                "qc_status": "blocking",
                "layer3_safe": "false",
                "matrix_path": "",
            }
        ]
    )
    blocking_report = build_export_readiness_report(blocking)
    assert blocking_report.iloc[0]["readiness_status"] == READINESS_BLOCKING


def test_default_exercise_segments_path_uses_segmentation_dir() -> None:
    root = Path("/tmp/layer25")
    path = default_exercise_segments_path(root)
    assert path == root / "segmentation" / "671_ex_segmentatios_frames.xlsx"
    assert path.name.endswith("_ex_segmentatios_frames.xlsx")
    assert exercise_segments_path_for_participant(root, "252").name == "252_ex_segmentatios_frames.xlsx"


def test_build_session_coverage_diff_includes_missing_manifest_sessions() -> None:
    session_index = pd.DataFrame(
        [
            {
                "participant_id": "671",
                "timepoint": "T2",
                "repetition_id": "R1",
                "session_id": "671_T2_P1_R1",
                "is_matched": True,
            },
            {
                "participant_id": "671",
                "timepoint": "T1",
                "repetition_id": "R1",
                "session_id": "671_T1_P1_R1",
                "is_matched": True,
            },
        ]
    )
    manifest_df = pd.DataFrame(
        [
            {
                "participant_id": "671",
                "timepoint": "T1",
                "repetition": "R1",
                "session_id": "671_T1_P1_R1",
                "gaga_exercise_label": "P1",
                "export_granularity": EXPORT_GRANULARITY_PER_EXERCISE,
            }
        ]
    )
    attempts_df = pd.DataFrame(
        [
            {
                "session_id": "671_T2_P1_R1",
                "participant_id": "671",
                "timepoint": "T2",
                "repetition": "R1",
                "export_label": "combined_group4",
                "status": ATTEMPT_STATUS_SKIPPED,
                "reason_code": "missing_exercise_segmentation",
                "reason_message": "No segmentation sheet",
                "artifact_path": "",
                "source_dependency": "/tmp/671.xlsx",
                "warning_file": "",
            }
        ]
    )
    diff = build_session_coverage_diff(
        session_index=session_index,
        exercise_catalog={"671_T1_P1_R1": []},
        manifest_df=manifest_df,
        attempts_df=attempts_df,
        participant_ids=["671"],
        project_root=Path("/tmp/layer25"),
    )
    t2 = diff[diff["session_id"] == "671_T2_P1_R1"].iloc[0]
    assert t2["session_status"] == SESSION_STATUS_SKIPPED
    assert t2["manifest_export_count"] == 0
    t1 = diff[diff["session_id"] == "671_T1_P1_R1"].iloc[0]
    assert t1["session_status"] in {"partial", "missing", "skipped"}


def test_write_export_attempts_report_persists_rows(tmp_path: Path) -> None:
    rows = [
        {
            "session_id": "671_T3_P1_R1",
            "participant_id": "671",
            "timepoint": "T3",
            "repetition": "R1",
            "export_label": "combined_group4",
            "status": ATTEMPT_STATUS_FAILED,
            "reason_code": "feature.missing_required",
            "reason_message": "Session missing canonical link Neck->Head required by pilot manifest",
            "artifact_path": str(tmp_path / "blocked.json"),
            "source_dependency": "",
            "warning_file": str(tmp_path / "window_warnings.csv"),
        }
    ]
    out = write_export_attempts_report(rows, tmp_path / "layer25_export_attempts_report.csv")
    loaded = pd.read_csv(out)
    assert loaded.iloc[0]["session_id"] == "671_T3_P1_R1"
    assert loaded.iloc[0]["reason_code"] == "feature.missing_required"


def test_load_layer25_export_manifest_unchanged(tmp_path: Path) -> None:
    rows = [
        {
            "participant_id": "671",
            "timepoint": "T1",
            "repetition": "R1",
            "task_part_id": "P1",
            "session_id": "671_T1_P1_R1",
            "run_label": "take",
            "gaga_exercise_id": "9",
            "gaga_exercise_label": "P1",
            "export_granularity": EXPORT_GRANULARITY_PER_EXERCISE,
            "export_mode": EXPORT_GRANULARITY_PER_EXERCISE,
            "matrix_path": "/tmp/m.parquet",
            "manifest_path": "/tmp/manifest.json",
            "layer3_safe": "true",
            "qc_status": "pass",
            "n_frames": 10,
            "n_features": 30,
            "feature_schema_id": "abc",
            "created_at": "2026-06-26T00:00:00+00:00",
        }
    ]
    path = write_layer25_export_manifest(rows, tmp_path / "layer25_export_manifest.csv")
    loaded = load_layer25_export_manifest(path)
    assert len(loaded) == 1
    assert loaded.iloc[0]["gaga_exercise_label"] == "P1"
