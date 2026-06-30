"""Tests for dataset construction preview (Phase 4)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from conftest import FEATURE_NAMES, LINKS, make_matrix
from layer3_jcvpca.comparable_links import load_central_manifest
from layer3_jcvpca.dataset_builder import (
    ANALYSIS_MODE_EXPLORATORY,
    ANALYSIS_MODE_LONGITUDINAL,
    CONSTRUCTION_BLOCKING,
    CONSTRUCTION_PASS,
    CONSTRUCTION_WARNING,
    PRESET_P1_P2,
    REASON_FEATURE_ORDER_MISMATCH,
    REASON_MISSING_REPETITION,
    REASON_UNEQUAL_ROW_COUNTS,
    DatasetConstructionConfig,
    DatasetSideSpec,
    build_dataset_construction_preview,
    write_dataset_construction_artifacts,
)


def _manifest_row(
    *,
    matrix_path: Path,
    session_id: str,
    timepoint: str,
    repetition: str,
    exercise: str,
    n_rows: int = 100,
) -> dict:
    return {
        "participant_id": "671",
        "timepoint": timepoint,
        "repetition": repetition,
        "task_part_id": "P1",
        "session_id": session_id,
        "run_label": f"{session_id}_Take",
        "gaga_exercise_id": "9" if exercise == "P1" else "10",
        "gaga_exercise_label": exercise,
        "export_granularity": "per_exercise",
        "export_mode": "per_exercise",
        "matrix_path": str(matrix_path),
        "manifest_path": str(matrix_path.parent / "window_export_manifest.json"),
        "layer3_safe": "true",
        "qc_status": "warning",
        "n_frames": n_rows,
        "n_features": len(FEATURE_NAMES),
        "feature_schema_id": "schema_a",
        "created_at": "2026-06-26T00:00:00+00:00",
    }


def _write_matrix(path: Path, session_id: str, *, n_rows: int = 100, feature_names=None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    make_matrix(
        n_rows=n_rows,
        session_id=session_id,
        feature_names=feature_names or FEATURE_NAMES,
    ).to_parquet(path, index=False)


def _build_manifest(tmp_path: Path) -> pd.DataFrame:
    rows = []
    specs = [
        ("671_T1_P1_R1", "T1", "R1", "P1", 120),
        ("671_T1_P1_R2", "T1", "R2", "P1", 110),
        ("671_T2_P1_R2", "T2", "R2", "P1", 130),
        ("671_T1_P1_R1", "T1", "R1", "P2", 80),
        ("671_T1_P1_R2", "T1", "R2", "P2", 90),
        ("671_T2_P1_R2", "T2", "R2", "P2", 95),
    ]
    for session_id, tp, rep, ex, n_rows in specs:
        path = tmp_path / f"{session_id}_{ex}.parquet"
        _write_matrix(path, session_id, n_rows=n_rows)
        rows.append(
            _manifest_row(
                matrix_path=path,
                session_id=session_id,
                timepoint=tp,
                repetition=rep,
                exercise=ex,
                n_rows=n_rows,
            )
        )
    return pd.DataFrame(rows)


def test_longitudinal_construction_with_available_sessions(tmp_path: Path) -> None:
    manifest = _build_manifest(tmp_path)
    config = DatasetConstructionConfig(
        analysis_mode=ANALYSIS_MODE_LONGITUDINAL,
        participant_ids=["671"],
        exercise_preset=PRESET_P1_P2,
        exercises=["P1"],
        dataset_a=DatasetSideSpec(timepoints=["T1"], repetitions=["R1", "R2"]),
        dataset_b=DatasetSideSpec(timepoints=["T2"], repetitions=["R2"]),
        selected_link_stems=list(LINKS),
        acknowledge_missing_repetitions=True,
    )
    result = build_dataset_construction_preview(manifest, config)
    assert result.construction_status in {CONSTRUCTION_PASS, CONSTRUCTION_WARNING}
    assert result.dataset_a.n_source_matrices == 2
    assert result.dataset_b.n_source_matrices == 1
    assert result.dataset_a.total_rows == 120 + 110
    assert result.dataset_b.total_rows == 130


def test_exploratory_construction_t1_r1_vs_r2(tmp_path: Path) -> None:
    manifest = _build_manifest(tmp_path)
    config = DatasetConstructionConfig(
        analysis_mode=ANALYSIS_MODE_EXPLORATORY,
        participant_ids=["671"],
        exercises=["P1"],
        exploratory_timepoint="T1",
        exploratory_repetition_a="R1",
        exploratory_repetition_b="R2",
        selected_link_stems=list(LINKS),
    )
    result = build_dataset_construction_preview(manifest, config)
    assert result.construction_status in {CONSTRUCTION_PASS, CONSTRUCTION_WARNING}
    assert result.dataset_a.total_rows == 120
    assert result.dataset_b.total_rows == 110


def test_exploratory_blocks_when_r2_missing(tmp_path: Path) -> None:
    manifest = _build_manifest(tmp_path)
    manifest = manifest[
        ~(
            (manifest["timepoint"] == "T2")
            & (manifest["repetition"] == "R2")
            & (manifest["gaga_exercise_label"] == "P1")
        )
    ]
    config = DatasetConstructionConfig(
        analysis_mode=ANALYSIS_MODE_EXPLORATORY,
        participant_ids=["671"],
        exercises=["P1"],
        exploratory_timepoint="T2",
        exploratory_repetition_a="R2",
        exploratory_repetition_b="R1",
        selected_link_stems=list(LINKS),
    )
    result = build_dataset_construction_preview(manifest, config)
    assert result.construction_status == CONSTRUCTION_BLOCKING
    assert REASON_MISSING_REPETITION in result.blocking_errors["reason_code"].tolist()


def test_p1_p2_preset_concat_order(tmp_path: Path) -> None:
    manifest = _build_manifest(tmp_path)
    config = DatasetConstructionConfig(
        analysis_mode=ANALYSIS_MODE_EXPLORATORY,
        participant_ids=["671"],
        exercise_preset=PRESET_P1_P2,
        exploratory_timepoint="T1",
        exploratory_repetition_a="R1",
        exploratory_repetition_b="R2",
        selected_link_stems=list(LINKS),
    )
    result = build_dataset_construction_preview(manifest, config)
    assert result.construction_status == CONSTRUCTION_PASS
    labels = result.dataset_a.sources["matrix_label"].tolist()
    assert labels == ["671_T1_P1_R1_P1", "671_T1_P1_R1_P2"]


def test_selected_links_produce_three_columns_per_link(tmp_path: Path) -> None:
    manifest = _build_manifest(tmp_path)
    config = DatasetConstructionConfig(
        analysis_mode=ANALYSIS_MODE_EXPLORATORY,
        participant_ids=["671"],
        exercises=["P1"],
        exploratory_timepoint="T1",
        exploratory_repetition_a="R1",
        exploratory_repetition_b="R2",
        selected_link_stems=list(LINKS),
    )
    result = build_dataset_construction_preview(manifest, config)
    assert len(result.pca_feature_columns) == len(LINKS) * 3
    pca_rows = result.feature_columns[result.feature_columns["included_in_pca"]]
    assert len(pca_rows) == len(LINKS) * 3


def test_metadata_excluded_from_pca_feature_columns(tmp_path: Path) -> None:
    manifest = _build_manifest(tmp_path)
    config = DatasetConstructionConfig(
        analysis_mode=ANALYSIS_MODE_EXPLORATORY,
        participant_ids=["671"],
        exercises=["P1"],
        exploratory_timepoint="T1",
        exploratory_repetition_a="R1",
        exploratory_repetition_b="R2",
        selected_link_stems=list(LINKS),
    )
    result = build_dataset_construction_preview(manifest, config)
    assert "session_id" in result.metadata_columns
    assert "session_id" not in result.pca_feature_columns
    meta_rows = result.feature_columns[result.feature_columns["column_role"] == "metadata"]
    assert set(meta_rows["column_name"]) == set(result.metadata_columns)


def test_unequal_row_counts_allowed_with_warning(tmp_path: Path) -> None:
    manifest = _build_manifest(tmp_path)
    config = DatasetConstructionConfig(
        analysis_mode=ANALYSIS_MODE_EXPLORATORY,
        participant_ids=["671"],
        exercises=["P1"],
        exploratory_timepoint="T1",
        exploratory_repetition_a="R1",
        exploratory_repetition_b="R2",
        selected_link_stems=list(LINKS),
    )
    result = build_dataset_construction_preview(manifest, config)
    assert result.dataset_a.total_rows != result.dataset_b.total_rows
    assert REASON_UNEQUAL_ROW_COUNTS in result.warnings["reason_code"].tolist()


def test_feature_order_mismatch_blocks(tmp_path: Path) -> None:
    path_a = tmp_path / "a.parquet"
    path_b = tmp_path / "b.parquet"
    _write_matrix(path_a, "671_T1_P1_R1")
    _write_matrix(path_b, "671_T1_P1_R2", feature_names=list(reversed(FEATURE_NAMES)))
    manifest = pd.DataFrame(
        [
            _manifest_row(matrix_path=path_a, session_id="671_T1_P1_R1", timepoint="T1", repetition="R1", exercise="P1"),
            _manifest_row(matrix_path=path_b, session_id="671_T1_P1_R2", timepoint="T1", repetition="R2", exercise="P1"),
        ]
    )
    config = DatasetConstructionConfig(
        analysis_mode=ANALYSIS_MODE_EXPLORATORY,
        participant_ids=["671"],
        exercises=["P1"],
        exploratory_timepoint="T1",
        exploratory_repetition_a="R1",
        exploratory_repetition_b="R2",
        selected_link_stems=list(LINKS),
    )
    result = build_dataset_construction_preview(manifest, config)
    assert result.construction_status == CONSTRUCTION_BLOCKING
    assert REASON_FEATURE_ORDER_MISMATCH in result.blocking_errors["reason_code"].tolist()


def test_construction_artifacts_written(tmp_path: Path) -> None:
    manifest = _build_manifest(tmp_path)
    config = DatasetConstructionConfig(
        analysis_mode=ANALYSIS_MODE_EXPLORATORY,
        participant_ids=["671"],
        exercises=["P1"],
        exploratory_timepoint="T1",
        exploratory_repetition_a="R1",
        exploratory_repetition_b="R2",
        selected_link_stems=list(LINKS),
    )
    result = build_dataset_construction_preview(manifest, config)
    out_dir = tmp_path / "artifacts"
    paths = write_dataset_construction_artifacts(result, out_dir)
    assert paths["dataset_construction_plan"].is_file()
    assert paths["dataset_A_sources"].is_file()
    assert paths["dataset_B_sources"].is_file()
    assert paths["dataset_A_preview"].is_file()
    assert paths["dataset_B_preview"].is_file()
    assert paths["dataset_feature_columns"].is_file()
    assert paths["dataset_construction_summary"].is_file()
    assert paths["dataset_construction_warnings"].is_file()


@pytest.mark.skipif(
    not (
        Path(__file__).resolve().parents[2].parent
        / "Layer2.5_Segmentation"
        / "outputs"
        / "pre_jvcpca_review"
        / "layer25_export_manifest.csv"
    ).is_file(),
    reason="central manifest not present",
)
def test_demo_longitudinal_on_real_manifest() -> None:
    repo_root = Path(__file__).resolve().parents[2].parent
    manifest = load_central_manifest(
        repo_root / "Layer2.5_Segmentation" / "outputs" / "pre_jvcpca_review"
    )
    config = DatasetConstructionConfig(
        analysis_mode=ANALYSIS_MODE_LONGITUDINAL,
        participant_ids=["671"],
        exercises=["P1"],
        dataset_a=DatasetSideSpec(timepoints=["T1"], repetitions=["R1", "R2"]),
        dataset_b=DatasetSideSpec(timepoints=["T2"], repetitions=["R2"]),
        selected_link_stems=[
            "Neck_to_Head",
            "Chest_to_Neck",
            "Chest_to_LShoulder",
            "LShoulder_to_LUArm",
            "LUArm_to_LFArm",
            "LFArm_to_LHand",
            "Chest_to_RShoulder",
            "RShoulder_to_RUArm",
            "RUArm_to_RFArm",
            "RFArm_to_RHand",
        ],
        acknowledge_missing_repetitions=True,
    )
    result = build_dataset_construction_preview(manifest, config)
    assert result.construction_status in {CONSTRUCTION_PASS, CONSTRUCTION_WARNING}
    assert result.dataset_a.n_source_matrices == 2
    assert result.dataset_b.n_source_matrices == 1
    assert len(result.pca_feature_columns) == 30
