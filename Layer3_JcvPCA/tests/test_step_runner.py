"""Tests for Phase 6 step runner (load, raw preview, independent centering)."""

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
    CENTERING_VALUES_COLUMNS,
    independent_center,
    validate_no_scaling,
)
from layer3_jcvpca.step_runner import (
    Phase6RunContext,
    StepRunError,
    initialize_run_state,
    run_step,
)
from layer3_jcvpca.workbench_preflight import (
    bundle_from_construction_result,
    load_construction_artifacts,
    run_workbench_preflight,
    save_preflight_acknowledgment,
    write_workbench_preflight_artifacts,
)
from layer3_jcvpca.workbench_reporting import load_loaded_datasets
from layer3_jcvpca.workbench_state import (
    STEP_6A_LOAD,
    STEP_6B_RAW_PREVIEW,
    STEP_6C_CENTERING,
    STEP_BLOCKING,
    STEP_COMPLETED,
    STEP_INVALIDATED,
    STEP_READY,
    check_phase6_gate,
    load_run_state,
    sync_upstream_invalidation,
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


def _write_preflight(tmp_path: Path, construction_dir: Path, *, acknowledged: bool) -> Path:
    bundle = load_construction_artifacts(construction_dir)
    report = run_workbench_preflight(bundle, warnings_acknowledged=acknowledged)
    preflight_dir = tmp_path / "preflight"
    write_workbench_preflight_artifacts(report, preflight_dir)
    if acknowledged:
        save_preflight_acknowledgment(preflight_dir, acknowledged=True, preflight_summary=report.summary)
    return preflight_dir


def _context(tmp_path: Path, *, acknowledged: bool = True) -> Phase6RunContext:
    construction_dir = _build_phase4_artifacts(tmp_path)
    preflight_dir = _write_preflight(tmp_path, construction_dir, acknowledged=acknowledged)
    return Phase6RunContext(
        construction_artifact_dir=construction_dir,
        preflight_artifact_dir=preflight_dir,
        output_dir=tmp_path / "run",
        upstream_fingerprint="fp_test_001",
    )


def test_phase6_blocked_if_preflight_not_acknowledged(tmp_path: Path) -> None:
    ctx = _context(tmp_path, acknowledged=False)
    passed, report = check_phase6_gate(ctx.preflight_artifact_dir)
    assert passed is False
    state = initialize_run_state(ctx)
    assert state.preflight_gate_passed is False
    assert state.steps[STEP_6A_LOAD].status == STEP_BLOCKING


def test_step_state_persists_to_disk(tmp_path: Path) -> None:
    ctx = _context(tmp_path)
    state = initialize_run_state(ctx)
    run_step(STEP_6A_LOAD, ctx, state)
    loaded = load_run_state(ctx.output_dir)
    assert loaded is not None
    assert loaded.steps[STEP_6A_LOAD].status == STEP_COMPLETED
    assert (ctx.output_dir / "step_status.json").is_file()
    assert (ctx.output_dir / "run_manifest.json").is_file()


def test_upstream_fingerprint_invalidates_steps(tmp_path: Path) -> None:
    ctx = _context(tmp_path)
    state = initialize_run_state(ctx)
    run_step(STEP_6A_LOAD, ctx, state)
    run_step(STEP_6B_RAW_PREVIEW, ctx, state)
    changed = sync_upstream_invalidation(state, "fp_changed")
    assert changed is True
    assert state.steps[STEP_6A_LOAD].status == STEP_INVALIDATED
    assert state.steps[STEP_6B_RAW_PREVIEW].status == STEP_INVALIDATED


def test_raw_preview_writes_artifacts(tmp_path: Path) -> None:
    ctx = _context(tmp_path)
    state = initialize_run_state(ctx)
    run_step(STEP_6A_LOAD, ctx, state)
    run_step(STEP_6B_RAW_PREVIEW, ctx, state)
    assert (ctx.output_dir / "raw_dataset_A_preview.csv").is_file()
    assert (ctx.output_dir / "raw_feature_stats_A.csv").is_file()
    assert (ctx.output_dir / "raw_feature_stats_B.csv").is_file()


def test_independent_centering_near_zero_means(tmp_path: Path) -> None:
    ctx = _context(tmp_path)
    state = initialize_run_state(ctx)
    for step in (STEP_6A_LOAD, STEP_6B_RAW_PREVIEW, STEP_6C_CENTERING):
        run_step(step, ctx, state)
    centers_a = pd.read_csv(ctx.output_dir / "centering_values_A.csv")
    centers_b = pd.read_csv(ctx.output_dir / "centering_values_B.csv")
    assert np.allclose(centers_a["mean_after_centering"], 0.0, atol=1e-10)
    assert np.allclose(centers_b["mean_after_centering"], 0.0, atol=1e-10)


def test_b_uses_b_mean_not_a_mean(tmp_path: Path) -> None:
    ctx = _context(tmp_path)
    state = initialize_run_state(ctx)
    for step in (STEP_6A_LOAD, STEP_6B_RAW_PREVIEW, STEP_6C_CENTERING):
        run_step(step, ctx, state)
    validation = pd.read_csv(ctx.output_dir / "centered_validation_report.csv")
    assert validation[validation["check_id"] == "B_not_using_A_means"]["status"].iloc[0] == "pass"
    centers_a = pd.read_csv(ctx.output_dir / "centering_values_A.csv")
    centers_b = pd.read_csv(ctx.output_dir / "centering_values_B.csv")
    assert list(centers_a.columns) == list(CENTERING_VALUES_COLUMNS)


def test_no_zscore_scaling_applied(tmp_path: Path) -> None:
    features = make_matrix(n_rows=50)[FEATURE_NAMES]
    trace = independent_center(features)
    checks = validate_no_scaling(features, trace.centered_features, dataset_side="A")
    assert any(c["check_id"] == "A_no_zscore" and c["status"] == "pass" for c in checks)


def test_centering_artifact_schema(tmp_path: Path) -> None:
    ctx = _context(tmp_path)
    state = initialize_run_state(ctx)
    for step in (STEP_6A_LOAD, STEP_6B_RAW_PREVIEW, STEP_6C_CENTERING):
        run_step(step, ctx, state)
    for name in (
        "centering_values_A.csv",
        "centering_values_B.csv",
        "centered_dataset_A_preview.csv",
        "centered_validation_report.csv",
        "centering_summary.json",
    ):
        assert (ctx.output_dir / name).is_file()
    summary = json.loads((ctx.output_dir / "centering_summary.json").read_text())
    assert summary["z_score_applied"] is False
    assert summary["validation_pass"] is True


def test_cannot_run_centering_before_raw_load(tmp_path: Path) -> None:
    ctx = _context(tmp_path)
    state = initialize_run_state(ctx)
    with pytest.raises(StepRunError, match="6A"):
        run_step(STEP_6C_CENTERING, ctx, state)
    run_step(STEP_6A_LOAD, ctx, state)
    with pytest.raises(StepRunError, match="6B"):
        run_step(STEP_6C_CENTERING, ctx, state)


def test_load_step_unlocks_raw_preview(tmp_path: Path) -> None:
    ctx = _context(tmp_path)
    state = initialize_run_state(ctx)
    assert state.steps[STEP_6B_RAW_PREVIEW].status != STEP_READY
    run_step(STEP_6A_LOAD, ctx, state)
    reloaded = load_run_state(ctx.output_dir)
    assert reloaded is not None
    assert reloaded.steps[STEP_6B_RAW_PREVIEW].status == STEP_READY
    loaded_a, loaded_b = load_loaded_datasets(ctx.output_dir)
    assert len(loaded_a) == 230
    assert len(loaded_b) == 130


@pytest.mark.skipif(
    not (
        Path(__file__).resolve().parents[1]
        / "outputs"
        / "_workbench_dataset_preview"
        / "demo_longitudinal_p1"
        / "dataset_construction_plan.json"
    ).is_file(),
    reason="Phase 4/5 demo artifacts not present",
)
def test_demo_phase6_run_on_real_artifacts() -> None:
    repo = Path(__file__).resolve().parents[1]
    construction_dir = repo / "outputs" / "_workbench_dataset_preview" / "demo_longitudinal_p1"
    preflight_dir = repo / "outputs" / "_workbench_preflight" / "demo_longitudinal_p1"
    if not (preflight_dir / "preflight_acknowledgment.json").is_file():
        summary = json.loads((preflight_dir / "preflight_summary.json").read_text())
        save_preflight_acknowledgment(preflight_dir, acknowledged=True, preflight_summary=summary)
    out_dir = repo / "outputs" / "_workbench_phase6" / "demo_longitudinal_p1"
    ctx = Phase6RunContext(
        construction_artifact_dir=construction_dir,
        preflight_artifact_dir=preflight_dir,
        output_dir=out_dir,
        upstream_fingerprint="demo_fp",
    )
    assert check_phase6_gate(preflight_dir)[0] is True
    state = initialize_run_state(ctx)
    for step in (STEP_6A_LOAD, STEP_6B_RAW_PREVIEW, STEP_6C_CENTERING):
        run_step(step, ctx, state)
    assert state.steps[STEP_6C_CENTERING].status == STEP_COMPLETED
