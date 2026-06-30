"""Tests for workbench JcvPCA pipeline steps 10–18."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from conftest import FEATURE_NAMES, LINKS, make_matrix
from layer3_jcvpca.dataset_builder import (
    DatasetConstructionConfig,
    DatasetSideSpec,
    build_dataset_construction_preview,
    write_dataset_construction_artifacts,
)
from layer3_jcvpca.jcvpca_trace import PcaAParameters
from layer3_jcvpca.jcvpca_workbench import trace_matches_core_on_loaded_data
from layer3_jcvpca.pc_focus import PC_FOCUS_ALL, PcFocusParameters
from layer3_jcvpca.step_runner import Phase6RunContext, StepRunError, initialize_run_state, run_step
from layer3_jcvpca.workbench_jcvpca_runner import WeightingParameters
from layer3_jcvpca.workbench_preflight import (
    load_construction_artifacts,
    run_workbench_preflight,
    save_preflight_acknowledgment,
    write_workbench_preflight_artifacts,
)
from layer3_jcvpca.workbench_pca_stability import save_pca_stability_acknowledgment
from layer3_jcvpca.workbench_state import (
    STEP_10A_B_PROJECTION,
    STEP_14A_RSS,
    STEP_15A_WEIGHTING,
    STEP_18A_EXPORT,
    STEP_6A_LOAD,
    STEP_6B_RAW_PREVIEW,
    STEP_6C_CENTERING,
    STEP_7A_PCA_A,
    STEP_9A_PC_FOCUS,
    WORKBENCH_STEP_ORDER,
    load_run_state,
)


def _build_and_run_to_9a(tmp_path: Path) -> Phase6RunContext:
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
    manifest = __import__("pandas").DataFrame(rows)
    config = DatasetConstructionConfig(
        participant_ids=["671"],
        exercises=["P1"],
        dataset_a=DatasetSideSpec(timepoints=["T1"], repetitions=["R1", "R2"]),
        dataset_b=DatasetSideSpec(timepoints=["T2"], repetitions=["R2"]),
        selected_link_stems=list(LINKS),
        acknowledge_missing_repetitions=True,
    )
    result = build_dataset_construction_preview(manifest, config)
    construction_dir = tmp_path / "construction"
    write_dataset_construction_artifacts(result, construction_dir)
    bundle = load_construction_artifacts(construction_dir)
    report = run_workbench_preflight(bundle, warnings_acknowledged=True)
    preflight_dir = tmp_path / "preflight"
    write_workbench_preflight_artifacts(report, preflight_dir)
    save_preflight_acknowledgment(preflight_dir, acknowledged=True, preflight_summary=report.summary)
    ctx = Phase6RunContext(
        construction_artifact_dir=construction_dir,
        preflight_artifact_dir=preflight_dir,
        output_dir=tmp_path / "run",
        upstream_fingerprint="fp_jcvpca_pipeline",
    )
    state = initialize_run_state(ctx)
    for step in (STEP_6A_LOAD, STEP_6B_RAW_PREVIEW, STEP_6C_CENTERING, STEP_7A_PCA_A):
        run_step(step, ctx, state, pca_a_params=PcaAParameters())
    combined = json.loads((ctx.output_dir / "pca_stability_combined_summary.json").read_text())
    if combined.get("combined_status") == "warning":
        save_pca_stability_acknowledgment(ctx.output_dir, acknowledged=True, combined_summary=combined)
    run_step(STEP_9A_PC_FOCUS, ctx, state, pc_focus_params=PcFocusParameters(pc_focus_mode=PC_FOCUS_ALL))
    return ctx


def test_load_legacy_state_adds_pipeline_steps(tmp_path: Path) -> None:
    """Runs saved before phases 10–18 should gain new step slots on load."""
    ctx = _build_and_run_to_9a(tmp_path)
    manifest = json.loads((ctx.output_dir / "run_manifest.json").read_text())
    manifest["steps"] = {
        k: v for k, v in manifest["steps"].items() if not k.startswith("10A_")
    }
    (ctx.output_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2))
    state = load_run_state(ctx.output_dir)
    assert state is not None
    assert STEP_10A_B_PROJECTION in state.steps
    assert state.steps[STEP_10A_B_PROJECTION].status == "ready"


def test_trace_matches_core(tmp_path: Path) -> None:
    ctx = _build_and_run_to_9a(tmp_path)
    state = load_run_state(ctx.output_dir)
    for step_id in WORKBENCH_STEP_ORDER[WORKBENCH_STEP_ORDER.index(STEP_10A_B_PROJECTION) : WORKBENCH_STEP_ORDER.index(STEP_14A_RSS) + 1]:
        run_step(step_id, ctx, state)
    match = trace_matches_core_on_loaded_data(ctx.output_dir)
    np.testing.assert_allclose(match["trace_jcvpca_axis"], match["core_jcvpca_axis"], atol=1e-8)


def test_full_pipeline_artifacts(tmp_path: Path) -> None:
    ctx = _build_and_run_to_9a(tmp_path)
    state = load_run_state(ctx.output_dir)
    for step_id in WORKBENCH_STEP_ORDER[WORKBENCH_STEP_ORDER.index(STEP_10A_B_PROJECTION) :]:
        if step_id == STEP_15A_WEIGHTING:
            run_step(step_id, ctx, state, weighting_params=WeightingParameters(explained_variance_weighting=False))
        else:
            run_step(step_id, ctx, state)
    assert (ctx.output_dir / "B_projected_preview.csv").is_file()
    assert (ctx.output_dir / "link_level_jcvpca_unweighted.csv").is_file()
    assert (ctx.output_dir / "workbench_export_manifest.json").is_file()


def test_projection_blocked_without_9a(tmp_path: Path) -> None:
    ctx = _build_and_run_to_9a(tmp_path)
    state = load_run_state(ctx.output_dir)
    state.steps[STEP_9A_PC_FOCUS].status = "not_started"
    with pytest.raises(StepRunError):
        run_step(STEP_10A_B_PROJECTION, ctx, state)
