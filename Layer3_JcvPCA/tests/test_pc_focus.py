"""Tests for Phase 9 PC analysis focus selection."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from conftest import FEATURE_NAMES, LINKS, make_matrix
from layer3_jcvpca.dataset_builder import (
    DatasetConstructionConfig,
    DatasetSideSpec,
    build_dataset_construction_preview,
    write_dataset_construction_artifacts,
)
from layer3_jcvpca.jcvpca_trace import PcaAParameters
from layer3_jcvpca.pc_focus import (
    PC_FOCUS_ALL,
    PC_FOCUS_FUNCTIONAL,
    PC_FOCUS_MANUAL,
    PC_FOCUS_NULL_SPACE,
    PcFocusParameters,
    build_pc_focus_table,
    validate_pc_focus_parameters,
)
from layer3_jcvpca.step_runner import Phase6RunContext, StepRunError, initialize_run_state, run_step
from layer3_jcvpca.workbench_preflight import (
    load_construction_artifacts,
    run_workbench_preflight,
    save_preflight_acknowledgment,
    write_workbench_preflight_artifacts,
)
from layer3_jcvpca.workbench_pca_stability import save_pca_stability_acknowledgment
from layer3_jcvpca.workbench_state import (
    STEP_6A_LOAD,
    STEP_6B_RAW_PREVIEW,
    STEP_6C_CENTERING,
    STEP_7A_PCA_A,
    STEP_9A_PC_FOCUS,
    STEP_COMPLETED,
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


def _run_through_7a(tmp_path: Path) -> tuple[Phase6RunContext, object]:
    construction_dir = _build_phase4_artifacts(tmp_path)
    preflight_dir = _write_preflight(tmp_path, construction_dir)
    ctx = Phase6RunContext(
        construction_artifact_dir=construction_dir,
        preflight_artifact_dir=preflight_dir,
        output_dir=tmp_path / "run",
        upstream_fingerprint="fp_pc_focus",
    )
    state = initialize_run_state(ctx)
    for step in (STEP_6A_LOAD, STEP_6B_RAW_PREVIEW, STEP_6C_CENTERING, STEP_7A_PCA_A):
        run_step(step, ctx, state, pca_a_params=PcaAParameters())
    combined_path = ctx.output_dir / "pca_stability_combined_summary.json"
    if combined_path.is_file():
        combined = json.loads(combined_path.read_text())
        if combined.get("combined_status") == "warning":
            save_pca_stability_acknowledgment(ctx.output_dir, acknowledged=True, combined_summary=combined)
    return ctx, load_run_state(ctx.output_dir)


def _sample_tables(selected_m: int = 4) -> tuple[pd.DataFrame, pd.DataFrame]:
    evr = pd.DataFrame(
        {
            "pc": range(1, selected_m + 1),
            "explained_variance_ratio": [0.4, 0.2, 0.2, 0.15][:selected_m],
        }
    )
    cum = pd.DataFrame(
        {
            "pc": range(1, selected_m + 1),
            "cumulative_explained_variance": [0.4, 0.6, 0.8, 0.95][:selected_m],
        }
    )
    return evr, cum


def test_default_all_includes_all_selected_pcs() -> None:
    evr, cum = _sample_tables(4)
    result = build_pc_focus_table(
        selected_m=4,
        explained_variance=evr,
        cumulative_variance=cum,
        params=PcFocusParameters(pc_focus_mode=PC_FOCUS_ALL),
    )
    assert result.included_pcs == [1, 2, 3, 4]
    assert result.focus_table["included"].all()


def test_functional_requires_p() -> None:
    errors = validate_pc_focus_parameters(PcFocusParameters(pc_focus_mode=PC_FOCUS_FUNCTIONAL), selected_m=4)
    assert errors
    result = build_pc_focus_table(
        selected_m=4,
        explained_variance=_sample_tables()[0],
        cumulative_variance=_sample_tables()[1],
        params=PcFocusParameters(pc_focus_mode=PC_FOCUS_FUNCTIONAL, p=2),
    )
    assert result.included_pcs == [1, 2]


def test_null_space_requires_p_and_produces_p_plus_one_to_m() -> None:
    evr, cum = _sample_tables(4)
    result = build_pc_focus_table(
        selected_m=4,
        explained_variance=evr,
        cumulative_variance=cum,
        params=PcFocusParameters(pc_focus_mode=PC_FOCUS_NULL_SPACE, p=2),
    )
    assert result.included_pcs == [3, 4]


def test_manual_pc_selection() -> None:
    evr, cum = _sample_tables(4)
    result = build_pc_focus_table(
        selected_m=4,
        explained_variance=evr,
        cumulative_variance=cum,
        params=PcFocusParameters(pc_focus_mode=PC_FOCUS_MANUAL, manual_pcs=[2, 4]),
    )
    assert result.included_pcs == [2, 4]


def test_invalid_manual_blocks() -> None:
    evr, cum = _sample_tables(4)
    result = build_pc_focus_table(
        selected_m=4,
        explained_variance=evr,
        cumulative_variance=cum,
        params=PcFocusParameters(pc_focus_mode=PC_FOCUS_MANUAL, manual_pcs=[99]),
    )
    assert result.validation_errors


def test_step_9_blocked_without_7a(tmp_path: Path) -> None:
    construction_dir = _build_phase4_artifacts(tmp_path)
    preflight_dir = _write_preflight(tmp_path, construction_dir)
    ctx = Phase6RunContext(
        construction_artifact_dir=construction_dir,
        preflight_artifact_dir=preflight_dir,
        output_dir=tmp_path / "run",
        upstream_fingerprint="fp_block_9",
    )
    state = initialize_run_state(ctx)
    ok, msg = step_prerequisites_met(state, STEP_9A_PC_FOCUS)
    assert ok is False
    with pytest.raises(StepRunError):
        run_step(STEP_9A_PC_FOCUS, ctx, state)


def test_step_9_writes_artifacts(tmp_path: Path) -> None:
    ctx, state = _run_through_7a(tmp_path)
    run_step(STEP_9A_PC_FOCUS, ctx, state, pc_focus_params=PcFocusParameters(pc_focus_mode=PC_FOCUS_ALL))
    assert (ctx.output_dir / "pc_focus_selection.json").is_file()
    assert (ctx.output_dir / "pc_focus_table.csv").is_file()
    payload = json.loads((ctx.output_dir / "pc_focus_selection.json").read_text())
    assert payload["pc_focus_mode"] == PC_FOCUS_ALL
    assert payload["p_inferred_silently"] is False
    reloaded = load_run_state(ctx.output_dir)
    assert reloaded is not None
    assert reloaded.steps[STEP_9A_PC_FOCUS].status in {STEP_COMPLETED, "warning"}
