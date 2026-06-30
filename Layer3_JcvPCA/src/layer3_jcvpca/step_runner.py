"""Step runner for Gaga workbench Phase 6–7 (load, preview, centering, PCA on A)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from layer3_jcvpca.data_contract import REQUIRED_METADATA_COLUMNS
from layer3_jcvpca.dataset_builder import PREVIEW_TRACKING_COLUMNS
from layer3_jcvpca.jcvpca_trace import (
    PcaAParameters,
    build_centering_summary,
    compute_raw_feature_stats,
    fit_pca_on_centered_a,
    independent_center,
    load_centered_a_features,
    load_centered_b_features,
    split_preview_columns,
    validate_b_not_centered_with_a_means,
    validate_independent_centering,
    validate_no_scaling,
)
from layer3_jcvpca.pc_focus import PcFocusParameters, build_pc_focus_table, pc_focus_selection_payload
from layer3_jcvpca.workbench_pca_stability import assess_workbench_pca_stability_pair
from layer3_jcvpca.workbench_preflight import load_construction_artifacts
from layer3_jcvpca.workbench_reporting import (
    load_loaded_datasets,
    write_pca_stability_artifacts,
    write_step_6a_artifacts,
    write_step_6b_artifacts,
    write_step_6c_artifacts,
    write_step_7a_artifacts,
    write_step_9a_artifacts,
)
from layer3_jcvpca.workbench_state import (
    STEP_6A_LOAD,
    STEP_6B_RAW_PREVIEW,
    STEP_6C_CENTERING,
    STEP_7A_PCA_A,
    STEP_9A_PC_FOCUS,
    WorkbenchRunState,
    check_phase6_gate,
    ensure_workbench_step_registry,
    mark_step_completed,
    new_workbench_run_state,
    save_run_state,
    step_prerequisites_met,
    sync_upstream_invalidation,
)


@dataclass
class Phase6RunContext:
    construction_artifact_dir: Path
    preflight_artifact_dir: Path
    output_dir: Path
    upstream_fingerprint: str
    run_id: str = "phase6_run"


class StepRunError(Exception):
    """Raised when a step cannot run."""


def initialize_run_state(context: Phase6RunContext) -> WorkbenchRunState:
    gate_passed, gate_report = check_phase6_gate(context.preflight_artifact_dir)
    state = new_workbench_run_state(
        run_id=context.run_id,
        upstream_fingerprint=context.upstream_fingerprint,
        construction_artifact_dir=context.construction_artifact_dir,
        preflight_artifact_dir=context.preflight_artifact_dir,
        output_dir=context.output_dir,
        preflight_gate_passed=gate_passed,
    )
    context.output_dir.mkdir(parents=True, exist_ok=True)
    save_run_state(state, context.output_dir)
    manifest = json.loads((context.output_dir / "run_manifest.json").read_text(encoding="utf-8"))
    manifest["preflight_gate_report"] = gate_report
    (context.output_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return state


def _load_plan_and_previews(context: Phase6RunContext) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame]:
    bundle = load_construction_artifacts(context.construction_artifact_dir)
    plan = bundle.plan
    preview_a = bundle.dataset_a_preview
    preview_b = bundle.dataset_b_preview
    if preview_a.empty or preview_b.empty:
        raise StepRunError("Phase 4 dataset previews are empty; rebuild Section 4.")
    return plan, preview_a, preview_b


def run_step_6a_load(context: Phase6RunContext, state: WorkbenchRunState) -> WorkbenchRunState:
    ok, msg = step_prerequisites_met(state, STEP_6A_LOAD)
    if not ok:
        raise StepRunError(msg)

    plan, preview_a, preview_b = _load_plan_and_previews(context)
    pca_cols = list(plan.get("pca_feature_columns") or [])
    meta_cols = list(plan.get("metadata_columns_excluded_from_pca") or list(REQUIRED_METADATA_COLUMNS))
    tracking = list(plan.get("preview_tracking_columns_excluded_from_pca") or list(PREVIEW_TRACKING_COLUMNS))

    missing_a = [c for c in pca_cols if c not in preview_a.columns]
    missing_b = [c for c in pca_cols if c not in preview_b.columns]
    if missing_a or missing_b:
        raise StepRunError(f"Preview missing PCA columns: A={missing_a[:3]}, B={missing_b[:3]}")

    leaked = [c for c in meta_cols + tracking if c in pca_cols]
    if leaked:
        raise StepRunError(f"Metadata/tracking columns found in PCA feature list: {leaked}")

    dimensions = {
        "dataset_a_rows": len(preview_a),
        "dataset_b_rows": len(preview_b),
        "n_pca_features": len(pca_cols),
        "n_metadata_columns": len([c for c in meta_cols if c in preview_a.columns]),
        "pca_feature_columns": pca_cols,
        "metadata_columns_excluded_from_pca": meta_cols,
    }
    paths = write_step_6a_artifacts(
        context.output_dir,
        loaded_a=preview_a,
        loaded_b=preview_b,
        dimensions=dimensions,
    )
    mark_step_completed(
        state,
        STEP_6A_LOAD,
        artifact_paths={k: str(v) for k, v in paths.items()},
        parameters=dimensions,
    )
    return state


def run_step_6b_raw_preview(context: Phase6RunContext, state: WorkbenchRunState) -> WorkbenchRunState:
    ok, msg = step_prerequisites_met(state, STEP_6B_RAW_PREVIEW)
    if not ok:
        raise StepRunError(msg)

    loaded_a, loaded_b = load_loaded_datasets(context.output_dir)
    plan, _, _ = _load_plan_and_previews(context)
    pca_cols = list(plan.get("pca_feature_columns") or [])
    meta_cols = list(plan.get("metadata_columns_excluded_from_pca") or list(REQUIRED_METADATA_COLUMNS))

    _, features_a = split_preview_columns(loaded_a, metadata_columns=meta_cols, pca_feature_columns=pca_cols)
    _, features_b = split_preview_columns(loaded_b, metadata_columns=meta_cols, pca_feature_columns=pca_cols)

    stats_a = compute_raw_feature_stats(features_a)
    stats_b = compute_raw_feature_stats(features_b)

    paths = write_step_6b_artifacts(
        context.output_dir,
        preview_a=loaded_a,
        preview_b=loaded_b,
        stats_a=stats_a,
        stats_b=stats_b,
    )
    mark_step_completed(
        state,
        STEP_6B_RAW_PREVIEW,
        artifact_paths={k: str(v) for k, v in paths.items()},
        parameters={"preview_head_rows": 20},
    )
    return state


def run_step_6c_centering(context: Phase6RunContext, state: WorkbenchRunState) -> WorkbenchRunState:
    ok, msg = step_prerequisites_met(state, STEP_6C_CENTERING)
    if not ok:
        raise StepRunError(msg)

    loaded_a, loaded_b = load_loaded_datasets(context.output_dir)
    plan, _, _ = _load_plan_and_previews(context)
    pca_cols = list(plan.get("pca_feature_columns") or [])
    meta_cols = list(plan.get("metadata_columns_excluded_from_pca") or list(REQUIRED_METADATA_COLUMNS))
    tracking_cols = [c for c in PREVIEW_TRACKING_COLUMNS if c in loaded_a.columns]

    meta_a, features_a = split_preview_columns(loaded_a, metadata_columns=meta_cols, pca_feature_columns=pca_cols)
    meta_b, features_b = split_preview_columns(loaded_b, metadata_columns=meta_cols, pca_feature_columns=pca_cols)

    trace_a = independent_center(features_a)
    trace_b = independent_center(features_b)

    validation_rows: list[dict[str, Any]] = []
    validation_rows.extend(validate_independent_centering(trace_a, dataset_side="A"))
    validation_rows.extend(validate_independent_centering(trace_b, dataset_side="B"))
    validation_rows.extend(validate_no_scaling(features_a, trace_a.centered_features, dataset_side="A"))
    validation_rows.extend(validate_no_scaling(features_b, trace_b.centered_features, dataset_side="B"))
    validation_rows.extend(validate_b_not_centered_with_a_means(trace_a.centers, trace_b.centers))

    # Explicit proof B was not centered with A means
    b_with_a_centers = features_b - trace_a.centers
    if b_with_a_centers.equals(trace_b.centered_features):
        validation_rows.append(
            {
                "check_id": "B_not_using_A_means",
                "dataset_side": "B",
                "status": "fail",
                "message": "B appears centered using A column means.",
            }
        )
    else:
        validation_rows.append(
            {
                "check_id": "B_not_using_A_means",
                "dataset_side": "B",
                "status": "pass",
                "message": "B centered using B column means, not A means.",
            }
        )

    validation_df = pd.DataFrame(validation_rows)
    summary = build_centering_summary(
        centers_a=trace_a.center_values_table,
        centers_b=trace_b.center_values_table,
        validation=validation_df,
    )

    centered_a = pd.concat(
        [meta_a, loaded_a[tracking_cols] if tracking_cols else pd.DataFrame(), trace_a.centered_features],
        axis=1,
    )
    centered_b = pd.concat(
        [meta_b, loaded_b[tracking_cols] if tracking_cols else pd.DataFrame(), trace_b.centered_features],
        axis=1,
    )

    paths = write_step_6c_artifacts(
        context.output_dir,
        centers_a=trace_a.center_values_table,
        centers_b=trace_b.center_values_table,
        centered_preview_a=centered_a,
        centered_preview_b=centered_b,
        validation=validation_df,
        summary=summary,
    )

    failures = validation_df[validation_df["status"] == "fail"] if not validation_df.empty else validation_df
    blocking = [{"reason_code": r["check_id"], "message": r["message"]} for _, r in failures.iterrows()]

    mark_step_completed(
        state,
        STEP_6C_CENTERING,
        artifact_paths={k: str(v) for k, v in paths.items()},
        blocking_errors=blocking,
    )
    return state


def _require_centering_pass(output_dir: Path) -> None:
    summary_path = output_dir / "centering_summary.json"
    if not summary_path.is_file():
        raise StepRunError("Run Step 6C (independent centering) before PCA on A.")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if not summary.get("validation_pass", False):
        raise StepRunError("centering_summary.json reports validation_pass=false; PCA on A blocked.")


def run_step_7a_pca_a(
    context: Phase6RunContext,
    state: WorkbenchRunState,
    params: PcaAParameters | None = None,
) -> WorkbenchRunState:
    ok, msg = step_prerequisites_met(state, STEP_7A_PCA_A)
    if not ok:
        raise StepRunError(msg)

    _require_centering_pass(context.output_dir)

    plan, _, _ = _load_plan_and_previews(context)
    pca_cols = list(plan.get("pca_feature_columns") or [])
    if not pca_cols:
        raise StepRunError("Construction plan missing pca_feature_columns.")

    pca_params = params or PcaAParameters()
    centered_a = load_centered_a_features(context.output_dir, pca_cols)
    centered_b = load_centered_b_features(context.output_dir, pca_cols)
    try:
        trace = fit_pca_on_centered_a(centered_a, pca_cols, pca_params)
    except ValueError as exc:
        raise StepRunError(str(exc)) from exc

    stability = assess_workbench_pca_stability_pair(
        centered_a,
        centered_b,
        pca_cols,
        trace,
    )
    paths = write_step_7a_artifacts(context.output_dir, trace)
    stability_paths = write_pca_stability_artifacts(context.output_dir, stability)
    paths.update(stability_paths)

    blocking_errors = [
        {"reason_code": f["code"], "message": f"[{result.role}] {f['message']}"}
        for result in (stability.a, stability.b)
        for f in result.findings
        if f["severity"] == "blocking"
    ]
    warnings = [
        {"reason_code": f["code"], "message": f"[{result.role}] {f['message']}"}
        for result in (stability.a, stability.b)
        for f in result.findings
        if f["severity"] == "warning"
    ]

    mark_step_completed(
        state,
        STEP_7A_PCA_A,
        artifact_paths={k: str(v) for k, v in paths.items()},
        parameters={
            "variance_threshold": pca_params.variance_threshold,
            "min_pcs": pca_params.min_pcs,
            "max_pcs": pca_params.max_pcs,
            "selected_m_mode": pca_params.selected_m_mode,
            "selected_m_override": pca_params.selected_m_override,
            "selected_m": trace.selected_m,
            "selected_m_reason": trace.selected_m_reason,
            "n_rows_A": trace.n_rows,
            "n_features": trace.n_features,
            "dataset_B_used_in_pca": False,
            "pca_stability_combined_status": stability.combined_status,
            "pca_stability_A_status": stability.a.status,
            "pca_stability_B_status": stability.b.status,
            "requires_stability_acknowledgment": stability.requires_acknowledgment,
        },
        blocking_errors=blocking_errors,
        warnings=warnings,
    )
    return state


def run_step_9a_pc_focus(
    context: Phase6RunContext,
    state: WorkbenchRunState,
    params: PcFocusParameters | None = None,
) -> WorkbenchRunState:
    ok, msg = step_prerequisites_met(state, STEP_9A_PC_FOCUS)
    if not ok:
        raise StepRunError(msg)

    selected_path = context.output_dir / "pca_A_selected_m.json"
    evr_path = context.output_dir / "pca_A_explained_variance.csv"
    cum_path = context.output_dir / "pca_A_cumulative_variance.csv"
    for path, label in (
        (selected_path, "pca_A_selected_m.json"),
        (evr_path, "pca_A_explained_variance.csv"),
        (cum_path, "pca_A_cumulative_variance.csv"),
    ):
        if not path.is_file():
            raise StepRunError(f"Missing {label}; run Step 7A first.")

    selected = json.loads(selected_path.read_text(encoding="utf-8"))
    selected_m = int(selected["selected_m"])
    explained = pd.read_csv(evr_path)
    cumulative = pd.read_csv(cum_path)

    focus_params = params or PcFocusParameters()
    result = build_pc_focus_table(
        selected_m=selected_m,
        explained_variance=explained,
        cumulative_variance=cumulative,
        params=focus_params,
    )
    if result.validation_errors:
        raise StepRunError("; ".join(result.validation_errors))

    paths = write_step_9a_artifacts(context.output_dir, result)
    mark_step_completed(
        state,
        STEP_9A_PC_FOCUS,
        artifact_paths={k: str(v) for k, v in paths.items()},
        parameters=pc_focus_selection_payload(result),
    )
    return state


def run_step(
    step_id: str,
    context: Phase6RunContext,
    state: WorkbenchRunState,
    *,
    pca_a_params: PcaAParameters | None = None,
    pc_focus_params: PcFocusParameters | None = None,
    weighting_params=None,
) -> WorkbenchRunState:
    ensure_workbench_step_registry(state)
    sync_upstream_invalidation(state, context.upstream_fingerprint)
    if step_id == STEP_6A_LOAD:
        return run_step_6a_load(context, state)
    if step_id == STEP_6B_RAW_PREVIEW:
        return run_step_6b_raw_preview(context, state)
    if step_id == STEP_6C_CENTERING:
        return run_step_6c_centering(context, state)
    if step_id == STEP_7A_PCA_A:
        return run_step_7a_pca_a(context, state, pca_a_params)
    if step_id == STEP_9A_PC_FOCUS:
        return run_step_9a_pc_focus(context, state, pc_focus_params)
    from layer3_jcvpca.workbench_jcvpca_runner import run_jcvpca_step

    return run_jcvpca_step(
        step_id,
        context,
        state,
        weighting_params=weighting_params,
    )
