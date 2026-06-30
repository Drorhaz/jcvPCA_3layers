"""Tests for workbench preflight (Phase 5)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from conftest import FEATURE_NAMES, LINKS, make_matrix
from layer3_jcvpca.dataset_builder import (
    DatasetConstructionConfig,
    DatasetSideSpec,
    build_dataset_construction_preview,
    write_dataset_construction_artifacts,
)
from layer3_jcvpca.comparable_links import load_central_manifest
from layer3_jcvpca.workbench_preflight import (
    PREFLIGHT_BLOCKING,
    PREFLIGHT_PASS,
    PREFLIGHT_WARNING,
    REASON_FEATURE_ORDER_MISMATCH,
    REASON_INF,
    REASON_NAN,
    REASON_NOT_LAYER3_SAFE,
    REASON_QC_WARNING,
    REASON_ROWS_TO_FEATURES_LOW,
    REASON_UNEQUAL_ROW_COUNTS,
    REASON_ZERO_VARIANCE,
    bundle_from_construction_result,
    load_construction_artifacts,
    run_workbench_preflight,
    save_preflight_acknowledgment,
    write_workbench_preflight_artifacts,
)


def _build_demo_artifacts(tmp_path: Path) -> tuple[Path, pd.DataFrame]:
    manifest_rows = []
    specs = [
        ("671_T1_P1_R1", "T1", "R1", 120),
        ("671_T1_P1_R2", "T1", "R2", 110),
        ("671_T2_P1_R2", "T2", "R2", 130),
    ]
    for session_id, tp, rep, n_rows in specs:
        path = tmp_path / "matrices" / f"{session_id}_P1.parquet"
        path.parent.mkdir(parents=True, exist_ok=True)
        make_matrix(n_rows=n_rows, session_id=session_id).to_parquet(path, index=False)
        manifest_rows.append(
            {
                "participant_id": "671",
                "timepoint": tp,
                "repetition": rep,
                "task_part_id": "P1",
                "session_id": session_id,
                "run_label": f"{session_id}_Take",
                "gaga_exercise_id": "9",
                "gaga_exercise_label": "P1",
                "export_granularity": "per_exercise",
                "export_mode": "per_exercise",
                "matrix_path": str(path),
                "manifest_path": str(path.parent / "window_export_manifest.json"),
                "layer3_safe": "true",
                "qc_status": "warning",
                "n_frames": n_rows,
                "n_features": len(FEATURE_NAMES),
                "feature_schema_id": "schema_a",
                "created_at": "2026-06-26T00:00:00+00:00",
            }
        )
    manifest = pd.DataFrame(manifest_rows)
    config = DatasetConstructionConfig(
        participant_ids=["671"],
        exercises=["P1"],
        dataset_a=DatasetSideSpec(timepoints=["T1"], repetitions=["R1", "R2"]),
        dataset_b=DatasetSideSpec(timepoints=["T2"], repetitions=["R2"]),
        selected_link_stems=list(LINKS),
        acknowledge_missing_repetitions=True,
    )
    result = build_dataset_construction_preview(manifest, config)
    out_dir = tmp_path / "construction"
    write_dataset_construction_artifacts(result, out_dir)
    return out_dir, manifest


@pytest.mark.skipif(
    not (
        Path(__file__).resolve().parents[1]
        / "outputs"
        / "_workbench_dataset_preview"
        / "demo_longitudinal_p1"
        / "dataset_construction_plan.json"
    ).is_file(),
    reason="Phase 4 demo artifacts not present",
)
def test_pass_case_using_phase4_demo() -> None:
    artifact_dir = (
        Path(__file__).resolve().parents[1]
        / "outputs"
        / "_workbench_dataset_preview"
        / "demo_longitudinal_p1"
    )
    repo_root = Path(__file__).resolve().parents[2].parent
    manifest = load_central_manifest(
        repo_root / "Layer2.5_Segmentation" / "outputs" / "pre_jvcpca_review"
    )
    bundle = load_construction_artifacts(artifact_dir)
    report = run_workbench_preflight(bundle, manifest_df=manifest)
    assert report.preflight_status == PREFLIGHT_WARNING
    assert report.blocking_errors.empty
    assert REASON_UNEQUAL_ROW_COUNTS in report.warnings["reason_code"].tolist()
    assert report.feature_alignment["aligned"].all()
    assert report.can_continue_to_phase6 is False


def test_unequal_row_counts_warning_not_block(tmp_path: Path) -> None:
    artifact_dir, manifest = _build_demo_artifacts(tmp_path)
    bundle = load_construction_artifacts(artifact_dir)
    report = run_workbench_preflight(bundle, manifest_df=manifest)
    assert report.preflight_status == PREFLIGHT_WARNING
    assert report.blocking_errors.empty
    assert REASON_UNEQUAL_ROW_COUNTS in report.warnings["reason_code"].tolist()


def test_qc_status_warning_requires_acknowledgment(tmp_path: Path) -> None:
    artifact_dir, manifest = _build_demo_artifacts(tmp_path)
    bundle = load_construction_artifacts(artifact_dir)
    report = run_workbench_preflight(bundle, manifest_df=manifest, warnings_acknowledged=False)
    assert REASON_QC_WARNING in report.warnings["reason_code"].tolist()
    assert report.can_continue_to_phase6 is False
    ack_report = run_workbench_preflight(bundle, manifest_df=manifest, warnings_acknowledged=True)
    assert ack_report.can_continue_to_phase6 is True


def test_rows_to_features_ratio_low_warning(tmp_path: Path) -> None:
    artifact_dir, manifest = _build_demo_artifacts(tmp_path)
    preview_a = pd.read_csv(artifact_dir / "dataset_A_preview.csv")
    preview_b = pd.read_csv(artifact_dir / "dataset_B_preview.csv")
    preview_a = preview_a.head(24)
    preview_b = preview_b.head(24)
    preview_a.to_csv(artifact_dir / "dataset_A_preview.csv", index=False)
    preview_b.to_csv(artifact_dir / "dataset_B_preview.csv", index=False)
    plan = json.loads((artifact_dir / "dataset_construction_plan.json").read_text())
    plan["dataset_a"]["total_rows"] = len(preview_a)
    plan["dataset_b"]["total_rows"] = len(preview_b)
    (artifact_dir / "dataset_construction_plan.json").write_text(json.dumps(plan, indent=2))
    bundle = load_construction_artifacts(artifact_dir)
    report = run_workbench_preflight(bundle, manifest_df=manifest)
    assert REASON_ROWS_TO_FEATURES_LOW in report.warnings["reason_code"].tolist()
    assert report.preflight_status == PREFLIGHT_WARNING


def test_feature_order_mismatch_blocks(tmp_path: Path) -> None:
    artifact_dir, manifest = _build_demo_artifacts(tmp_path)
    preview_b = pd.read_csv(artifact_dir / "dataset_B_preview.csv")
    pca_cols = json.loads((artifact_dir / "dataset_construction_plan.json").read_text())[
        "pca_feature_columns"
    ]
    reordered = [c for c in reversed(pca_cols) if c in preview_b.columns]
    meta = [c for c in preview_b.columns if c not in pca_cols]
    preview_b = preview_b[meta + reordered]
    preview_b.to_csv(artifact_dir / "dataset_B_preview.csv", index=False)
    bundle = load_construction_artifacts(artifact_dir)
    report = run_workbench_preflight(bundle, manifest_df=manifest)
    assert report.preflight_status == PREFLIGHT_BLOCKING
    assert REASON_FEATURE_ORDER_MISMATCH in report.blocking_errors["reason_code"].tolist()


def test_nan_blocks(tmp_path: Path) -> None:
    artifact_dir, manifest = _build_demo_artifacts(tmp_path)
    preview_a = pd.read_csv(artifact_dir / "dataset_A_preview.csv")
    col = json.loads((artifact_dir / "dataset_construction_plan.json").read_text())[
        "pca_feature_columns"
    ][0]
    preview_a.loc[0, col] = np.nan
    preview_a.to_csv(artifact_dir / "dataset_A_preview.csv", index=False)
    report = run_workbench_preflight(load_construction_artifacts(artifact_dir), manifest_df=manifest)
    assert report.preflight_status == PREFLIGHT_BLOCKING
    assert REASON_NAN in report.blocking_errors["reason_code"].tolist()


def test_inf_blocks(tmp_path: Path) -> None:
    artifact_dir, manifest = _build_demo_artifacts(tmp_path)
    preview_a = pd.read_csv(artifact_dir / "dataset_A_preview.csv")
    col = json.loads((artifact_dir / "dataset_construction_plan.json").read_text())[
        "pca_feature_columns"
    ][0]
    preview_a.loc[0, col] = np.inf
    preview_a.to_csv(artifact_dir / "dataset_A_preview.csv", index=False)
    report = run_workbench_preflight(load_construction_artifacts(artifact_dir), manifest_df=manifest)
    assert report.preflight_status == PREFLIGHT_BLOCKING
    assert REASON_INF in report.blocking_errors["reason_code"].tolist()


def test_zero_variance_blocks(tmp_path: Path) -> None:
    artifact_dir, manifest = _build_demo_artifacts(tmp_path)
    preview_a = pd.read_csv(artifact_dir / "dataset_A_preview.csv")
    col = json.loads((artifact_dir / "dataset_construction_plan.json").read_text())[
        "pca_feature_columns"
    ][0]
    preview_a[col] = 1.0
    preview_a.to_csv(artifact_dir / "dataset_A_preview.csv", index=False)
    report = run_workbench_preflight(load_construction_artifacts(artifact_dir), manifest_df=manifest)
    assert report.preflight_status == PREFLIGHT_BLOCKING
    assert REASON_ZERO_VARIANCE in report.blocking_errors["reason_code"].tolist()


def test_layer3_safe_false_blocks(tmp_path: Path) -> None:
    artifact_dir, manifest = _build_demo_artifacts(tmp_path)
    manifest = manifest.copy()
    manifest["layer3_safe"] = "false"
    report = run_workbench_preflight(load_construction_artifacts(artifact_dir), manifest_df=manifest)
    assert report.preflight_status == PREFLIGHT_BLOCKING
    assert REASON_NOT_LAYER3_SAFE in report.blocking_errors["reason_code"].tolist()


def test_warning_acknowledgment_saved(tmp_path: Path) -> None:
    artifact_dir, manifest = _build_demo_artifacts(tmp_path)
    preflight_dir = tmp_path / "preflight"
    bundle = load_construction_artifacts(artifact_dir)
    report = run_workbench_preflight(bundle, manifest_df=manifest, warnings_acknowledged=True)
    write_workbench_preflight_artifacts(report, preflight_dir)
    ack_path = save_preflight_acknowledgment(
        preflight_dir,
        acknowledged=True,
        preflight_summary=report.summary,
    )
    assert ack_path.is_file()
    payload = json.loads(ack_path.read_text())
    assert payload["warnings_acknowledged"] is True
    summary = json.loads((preflight_dir / "preflight_summary.json").read_text())
    assert summary["warnings_acknowledged"] is True
    assert summary["can_continue_to_phase6"] is True


def test_preflight_artifacts_written(tmp_path: Path) -> None:
    artifact_dir, manifest = _build_demo_artifacts(tmp_path)
    preflight_dir = tmp_path / "preflight"
    report = run_workbench_preflight(load_construction_artifacts(artifact_dir), manifest_df=manifest)
    paths = write_workbench_preflight_artifacts(report, preflight_dir)
    for key in (
        "preflight_report",
        "preflight_summary",
        "feature_alignment_report",
        "rows_to_features_report",
        "source_matrix_qc_report",
        "preflight_warnings",
        "preflight_blocking_errors",
    ):
        assert paths[key].is_file()
