"""Tests for Phase 7 Step 7A — PCA on centered Dataset A only."""

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
from layer3_jcvpca.jcvpca_trace import (
    DEFAULT_MAX_PCS,
    DEFAULT_MIN_PCS,
    DEFAULT_VARIANCE_THRESHOLD,
    PcaAParameters,
    SELECTED_M_MODE_AUTO,
    SELECTED_M_MODE_MANUAL,
    fit_pca_on_centered_a,
    load_centered_a_features,
    validate_selected_m_workbench,
)
from layer3_jcvpca.step_runner import (
    Phase6RunContext,
    StepRunError,
    initialize_run_state,
    run_step,
)
from layer3_jcvpca.workbench_preflight import (
    load_construction_artifacts,
    run_workbench_preflight,
    save_preflight_acknowledgment,
    write_workbench_preflight_artifacts,
)
from layer3_jcvpca.workbench_state import (
    STEP_6A_LOAD,
    STEP_6B_RAW_PREVIEW,
    STEP_6C_CENTERING,
    STEP_7A_PCA_A,
    STEP_COMPLETED,
    STEP_READY,
    load_run_state,
    step_prerequisites_met,
)


def _build_phase4_artifacts(tmp_path: Path) -> Path:
    rows = []
    for session_id, tp, rep, n_rows in [
        ("671_T1_P1_R1", "T1", "R1", 120),
        ("671_T1_P1_R2", "T1", "R2", 110),
        ("671_T2_P1_R2", "T2", "R2", 130),
    ]:
        path = tmp_path / "matrices" / f"{session_id}.parquet"
        path.parent.mkdir(parents=True, exist_ok=True)
        make_matrix(n_rows=n_rows, session_id=session_id).to_parquet(path, index=False)
        rows.append(
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
    manifest = pd.DataFrame(rows)
    config = DatasetConstructionConfig(
        participant_ids=["671"],
        exercises=["P1"],
        dataset_a=DatasetSideSpec(timepoints=["T1"], repetitions=["R1", "R2"]),
        dataset_b=DatasetSideSpec(timepoints=["T2"], repetitions=["R2"]),
        selected_link_stems=list(LINKS),
        acknowledge_missing_repetitions=True,
    )
    result = build_dataset_construction_preview(manifest, config)
    out = tmp_path / "construction"
    write_dataset_construction_artifacts(result, out)
    return out


def _write_preflight(tmp_path: Path, construction_dir: Path) -> Path:
    bundle = load_construction_artifacts(construction_dir)
    report = run_workbench_preflight(bundle, warnings_acknowledged=True)
    preflight_dir = tmp_path / "preflight"
    write_workbench_preflight_artifacts(report, preflight_dir)
    save_preflight_acknowledgment(preflight_dir, acknowledged=True, preflight_summary=report.summary)
    return preflight_dir


def _run_through_centering(tmp_path: Path) -> tuple[Phase6RunContext, object]:
    construction_dir = _build_phase4_artifacts(tmp_path)
    preflight_dir = _write_preflight(tmp_path, construction_dir)
    ctx = Phase6RunContext(
        construction_artifact_dir=construction_dir,
        preflight_artifact_dir=preflight_dir,
        output_dir=tmp_path / "run",
        upstream_fingerprint="fp_pca_a",
    )
    state = initialize_run_state(ctx)
    for step in (STEP_6A_LOAD, STEP_6B_RAW_PREVIEW, STEP_6C_CENTERING):
        run_step(step, ctx, state)
    return ctx, load_run_state(ctx.output_dir)


def test_pca_fits_using_centered_a_only(tmp_path: Path) -> None:
    ctx, state = _run_through_centering(tmp_path)
    run_step(STEP_7A_PCA_A, ctx, state)
    metadata = json.loads((ctx.output_dir / "pca_A_model_metadata.json").read_text())
    assert metadata["fit_dataset"] == "A_centered_only"
    assert metadata["dataset_B_used"] is False
    assert metadata["z_score_applied"] is False


def test_selected_m_from_cumulative_variance_default_threshold(tmp_path: Path) -> None:
    ctx, state = _run_through_centering(tmp_path)
    params = PcaAParameters(variance_threshold=DEFAULT_VARIANCE_THRESHOLD)
    run_step(STEP_7A_PCA_A, ctx, state, pca_a_params=params)
    selected = json.loads((ctx.output_dir / "pca_A_selected_m.json").read_text())
    cum = pd.read_csv(ctx.output_dir / "pca_A_cumulative_variance.csv")
    m = int(selected["selected_m"])
    assert selected["variance_threshold"] == pytest.approx(0.80)
    assert cum.iloc[m - 1]["cumulative_explained_variance"] >= 0.80 or m == DEFAULT_MAX_PCS


def test_default_threshold_is_080_in_workbench_params() -> None:
    assert DEFAULT_VARIANCE_THRESHOLD == 0.80
    assert DEFAULT_MIN_PCS == 2
    params = PcaAParameters()
    assert params.variance_threshold == 0.80
    assert params.min_pcs == 2


def test_manual_selected_m_validation(tmp_path: Path) -> None:
    ctx, state = _run_through_centering(tmp_path)
    plan = json.loads((ctx.construction_artifact_dir / "dataset_construction_plan.json").read_text())
    n_rows = 230
    n_features = len(plan["pca_feature_columns"])
    errors = validate_selected_m_workbench(
        n_features + 5,
        n_rows=n_rows,
        n_features=n_features,
        min_pcs=2,
        max_pcs=10,
    )
    assert errors
    valid_m = 3
    assert not validate_selected_m_workbench(
        valid_m, n_rows=n_rows, n_features=n_features, min_pcs=2, max_pcs=10
    )
    params = PcaAParameters(selected_m_mode=SELECTED_M_MODE_MANUAL, selected_m_override=valid_m)
    run_step(STEP_7A_PCA_A, ctx, state, pca_a_params=params)
    selected = json.loads((ctx.output_dir / "pca_A_selected_m.json").read_text())
    assert selected["selected_m"] == valid_m
    assert "manual" in selected["selected_m_reason"]


def test_invalid_selected_m_blocks_step(tmp_path: Path) -> None:
    ctx, state = _run_through_centering(tmp_path)
    params = PcaAParameters(
        selected_m_mode=SELECTED_M_MODE_MANUAL,
        selected_m_override=999,
        max_pcs=10,
    )
    with pytest.raises(StepRunError, match="selected_m"):
        run_step(STEP_7A_PCA_A, ctx, state, pca_a_params=params)


def test_no_b_data_used_in_pca_fit(tmp_path: Path) -> None:
    ctx, state = _run_through_centering(tmp_path)
    centered_a = load_centered_a_features(ctx.output_dir, FEATURE_NAMES)
    trace = fit_pca_on_centered_a(centered_a, FEATURE_NAMES, PcaAParameters())
    assert trace.n_rows == 230
    assert trace.n_features == len(FEATURE_NAMES)


def test_no_zscore_scaling_in_pca_input(tmp_path: Path) -> None:
    ctx, _ = _run_through_centering(tmp_path)
    centered_a = load_centered_a_features(ctx.output_dir, FEATURE_NAMES)
    raw_a, _ = pd.read_parquet(ctx.output_dir / "_loaded_dataset_A.parquet"), None
    centers = pd.read_csv(ctx.output_dir / "centering_values_A.csv").set_index("feature_column")["center_value"]
    for col in FEATURE_NAMES:
        std_raw = raw_a[col].std(ddof=0)
        std_centered = centered_a[col].std(ddof=0)
        assert np.isclose(std_raw, std_centered, atol=1e-10)


def test_explained_variance_artifacts_written(tmp_path: Path) -> None:
    ctx, state = _run_through_centering(tmp_path)
    run_step(STEP_7A_PCA_A, ctx, state)
    for name in (
        "pca_A_parameters.json",
        "pca_A_explained_variance.csv",
        "pca_A_cumulative_variance.csv",
        "pca_A_loadings.csv",
        "pca_A_selected_m.json",
        "pca_A_feature_names.csv",
        "pca_A_model_metadata.json",
        "plots/pca_A_scree_plot.png",
        "plots/pca_A_cumulative_variance.png",
        "plots/pca_A_loadings_heatmap.png",
    ):
        assert (ctx.output_dir / name).is_file()


def test_loadings_feature_names_order_preserved(tmp_path: Path) -> None:
    ctx, state = _run_through_centering(tmp_path)
    run_step(STEP_7A_PCA_A, ctx, state)
    plan = json.loads((ctx.construction_artifact_dir / "dataset_construction_plan.json").read_text())
    feature_names = pd.read_csv(ctx.output_dir / "pca_A_feature_names.csv")["feature_column"].tolist()
    assert feature_names == plan["pca_feature_columns"]
    loadings = pd.read_csv(ctx.output_dir / "pca_A_loadings.csv")
    assert set(loadings["feature_column"]) == set(feature_names)
    for pc in loadings["pc"].unique():
        pc_rows = loadings[loadings["pc"] == pc].sort_values("rank_within_pc")
        assert pc_rows.iloc[0]["rank_within_pc"] == 1


def test_step_7_blocked_if_centering_not_completed(tmp_path: Path) -> None:
    construction_dir = _build_phase4_artifacts(tmp_path)
    preflight_dir = _write_preflight(tmp_path, construction_dir)
    ctx = Phase6RunContext(
        construction_artifact_dir=construction_dir,
        preflight_artifact_dir=preflight_dir,
        output_dir=tmp_path / "run",
        upstream_fingerprint="fp_block",
    )
    state = initialize_run_state(ctx)
    run_step(STEP_6A_LOAD, ctx, state)
    state = load_run_state(ctx.output_dir)
    assert state is not None
    ok, msg = step_prerequisites_met(state, STEP_7A_PCA_A)
    assert ok is False
    assert "6C" in msg
    with pytest.raises(StepRunError, match="6C"):
        run_step(STEP_7A_PCA_A, ctx, state)


def test_step_7_unlocks_after_centering(tmp_path: Path) -> None:
    ctx, state = _run_through_centering(tmp_path)
    assert state.steps[STEP_7A_PCA_A].status == STEP_READY
    run_step(STEP_7A_PCA_A, ctx, state)
    reloaded = load_run_state(ctx.output_dir)
    assert reloaded is not None
    assert reloaded.steps[STEP_7A_PCA_A].status in {STEP_COMPLETED, "warning"}


def test_centering_validation_failure_blocks_pca(tmp_path: Path) -> None:
    ctx, state = _run_through_centering(tmp_path)
    summary_path = ctx.output_dir / "centering_summary.json"
    summary = json.loads(summary_path.read_text())
    summary["validation_pass"] = False
    summary_path.write_text(json.dumps(summary), encoding="utf-8")
    with pytest.raises(StepRunError, match="validation_pass"):
        run_step(STEP_7A_PCA_A, ctx, state)


def test_pca_stability_artifacts_written(tmp_path: Path) -> None:
    ctx, state = _run_through_centering(tmp_path)
    run_step(STEP_7A_PCA_A, ctx, state)
    for name in (
        "pca_A_stability_report.csv",
        "pca_A_stability_summary.json",
        "pca_A_near_zero_variance_features.csv",
        "pca_A_singular_values.csv",
        "pca_B_stability_report.csv",
        "pca_B_stability_summary.json",
        "pca_B_near_zero_variance_features.csv",
        "pca_B_singular_values.csv",
        "pca_stability_combined_summary.json",
    ):
        assert (ctx.output_dir / name).is_file()


def test_b_stability_has_no_selected_m(tmp_path: Path) -> None:
    ctx, state = _run_through_centering(tmp_path)
    run_step(STEP_7A_PCA_A, ctx, state)
    b_summary = json.loads((ctx.output_dir / "pca_B_stability_summary.json").read_text())
    assert "selected_m" not in b_summary.get("metrics", {})
    a_summary = json.loads((ctx.output_dir / "pca_A_stability_summary.json").read_text())
    assert "selected_m" in a_summary.get("metrics", {})


def test_stability_gate_requires_acknowledgment_on_warning(tmp_path: Path) -> None:
    from layer3_jcvpca.workbench_pca_stability import check_pca_stability_gate, save_pca_stability_acknowledgment

    ctx, state = _run_through_centering(tmp_path)
    run_step(STEP_7A_PCA_A, ctx, state)
    combined = json.loads((ctx.output_dir / "pca_stability_combined_summary.json").read_text())
    if combined.get("combined_status") != "warning":
        pytest.skip("Demo data did not produce stability warnings")
    ok, _ = check_pca_stability_gate(ctx.output_dir)
    assert ok is False
    save_pca_stability_acknowledgment(ctx.output_dir, acknowledged=True, combined_summary=combined)
    ok2, _ = check_pca_stability_gate(ctx.output_dir)
    assert ok2 is True
