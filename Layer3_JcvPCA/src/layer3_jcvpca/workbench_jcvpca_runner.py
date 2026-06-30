"""Step runner functions for workbench JcvPCA pipeline (Phases 10–18)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from layer3_jcvpca.jcvpca_workbench import (
    apply_explained_variance_weighting,
    compute_axis_jcvpca,
    compute_link_rss,
    fit_pca_on_projected_b,
    load_included_pcs,
    load_pca_a_state,
    load_workbench_centered_pair,
    project_b_into_a_space,
    reexpress_b_loadings,
)
from layer3_jcvpca.jcvpca_trace import load_centered_a_features
from layer3_jcvpca.nv_compare import build_main_vs_nv_table
from layer3_jcvpca.workbench_jcvpca_reporting import (
    load_pca_b_projected_trace,
    load_reexpress_trace,
    write_step_10a_artifacts,
    write_step_11a_artifacts,
    write_step_12a_artifacts,
    write_step_13a_artifacts,
    write_step_14a_artifacts,
    write_step_15a_artifacts,
    write_step_16a_nv_artifacts,
    write_step_17a_exploratory_artifacts,
    write_step_18a_export_manifest,
)
from layer3_jcvpca.step_runner import StepRunError
from layer3_jcvpca.workbench_reporting import load_loaded_datasets
from layer3_jcvpca.workbench_state import (
    STEP_10A_B_PROJECTION,
    STEP_11A_PCA_B,
    STEP_12A_REEXPRESS,
    STEP_13A_AXIS_JCVPCA,
    STEP_14A_RSS,
    STEP_15A_WEIGHTING,
    STEP_16A_NV,
    STEP_17A_EXPLORATORY,
    STEP_18A_EXPORT,
    WorkbenchRunState,
    mark_step_completed,
    step_prerequisites_met,
)


@dataclass
class WeightingParameters:
    explained_variance_weighting: bool = False


def _construction_plan(context) -> dict:
    path = context.construction_artifact_dir / "dataset_construction_plan.json"
    return json.loads(path.read_text(encoding="utf-8"))


def run_step_10a_project_b(context, state: WorkbenchRunState) -> WorkbenchRunState:
    ok, msg = step_prerequisites_met(state, STEP_10A_B_PROJECTION)
    if not ok:
        raise StepRunError(msg)
    pca_a = load_pca_a_state(context.output_dir)
    centered_a, centered_b = load_workbench_centered_pair(context.output_dir, pca_a.feature_names)
    trace = project_b_into_a_space(centered_b, centered_a, pca_a)
    paths = write_step_10a_artifacts(context.output_dir, trace, pca_a)
    mark_step_completed(
        state,
        STEP_10A_B_PROJECTION,
        artifact_paths={k: str(v) for k, v in paths.items()},
        parameters={
            "B_projected_shape": list(trace.B_projected.shape),
            "projection_method": trace.projection_method,
        },
    )
    return state


def run_step_11a_pca_projected_b(
    context,
    state: WorkbenchRunState,
) -> WorkbenchRunState:
    ok, msg = step_prerequisites_met(state, STEP_11A_PCA_B)
    if not ok:
        raise StepRunError(msg)
    pca_a = load_pca_a_state(context.output_dir)
    B_projected = __import__("numpy").load(context.output_dir / "_B_projected_scores.npy")
    trace = fit_pca_on_projected_b(B_projected, pca_a.selected_m, pca_a.feature_names)
    paths = write_step_11a_artifacts(context.output_dir, trace)
    mark_step_completed(
        state,
        STEP_11A_PCA_B,
        artifact_paths={k: str(v) for k, v in paths.items()},
        parameters={"selected_m": pca_a.selected_m},
    )
    return state


def run_step_12a_reexpress(
    context,
    state: WorkbenchRunState,
) -> WorkbenchRunState:
    ok, msg = step_prerequisites_met(state, STEP_12A_REEXPRESS)
    if not ok:
        raise StepRunError(msg)
    pca_a = load_pca_a_state(context.output_dir)
    pca_b = load_pca_b_projected_trace(context.output_dir)
    trace = reexpress_b_loadings(pca_a, pca_b)
    paths = write_step_12a_artifacts(context.output_dir, trace)
    mark_step_completed(
        state,
        STEP_12A_REEXPRESS,
        artifact_paths={k: str(v) for k, v in paths.items()},
        parameters={"B_reexpressed_shape": list(trace.B_reexpressed_loadings.shape)},
    )
    return state


def run_step_13a_axis_jcvpca(
    context,
    state: WorkbenchRunState,
) -> WorkbenchRunState:
    ok, msg = step_prerequisites_met(state, STEP_13A_AXIS_JCVPCA)
    if not ok:
        raise StepRunError(msg)
    pca_a = load_pca_a_state(context.output_dir)
    pca_b = load_pca_b_projected_trace(context.output_dir)
    reexpress = load_reexpress_trace(context.output_dir, pca_a)
    included = load_included_pcs(context.output_dir)
    trace = compute_axis_jcvpca(reexpress, pca_a, pca_b, included_pcs=included)
    paths = write_step_13a_artifacts(context.output_dir, trace)
    mark_step_completed(
        state,
        STEP_13A_AXIS_JCVPCA,
        artifact_paths={k: str(v) for k, v in paths.items()},
        parameters={"included_pcs": included, "n_axis_rows": len(trace.axis_table)},
    )
    return state


def run_step_14a_rss(
    context,
    state: WorkbenchRunState,
) -> WorkbenchRunState:
    ok, msg = step_prerequisites_met(state, STEP_14A_RSS)
    if not ok:
        raise StepRunError(msg)
    pca_a = load_pca_a_state(context.output_dir)
    reexpress = load_reexpress_trace(context.output_dir, pca_a)
    included = load_included_pcs(context.output_dir)
    trace = compute_link_rss(reexpress, pca_a, included_pcs=included, export_weighted=False)
    paths = write_step_14a_artifacts(context.output_dir, trace)
    mark_step_completed(
        state,
        STEP_14A_RSS,
        artifact_paths={k: str(v) for k, v in paths.items()},
        parameters={"included_pcs": included, "formula": trace.formula},
    )
    return state


def run_step_15a_weighting(
    context,
    state: WorkbenchRunState,
    params: WeightingParameters | None = None,
) -> WorkbenchRunState:
    ok, msg = step_prerequisites_met(state, STEP_15A_WEIGHTING)
    if not ok:
        raise StepRunError(msg)
    wp = params or WeightingParameters()
    pca_a = load_pca_a_state(context.output_dir)
    pca_b = load_pca_b_projected_trace(context.output_dir)
    reexpress = load_reexpress_trace(context.output_dir, pca_a)
    included = load_included_pcs(context.output_dir)
    axis = compute_axis_jcvpca(
        reexpress,
        pca_a,
        pca_b,
        included_pcs=included,
    )
    if wp.explained_variance_weighting:
        axis_w = compute_axis_jcvpca_weighted(reexpress, pca_a, pca_b, included)
        link_w = compute_link_rss(
            reexpress, pca_a, included_pcs=included, export_weighted=True
        )
        trace = apply_explained_variance_weighting(axis_w.axis_table, link_w.link_table, enabled=True)
    else:
        link = compute_link_rss(reexpress, pca_a, included_pcs=included, export_weighted=False)
        trace = apply_explained_variance_weighting(axis.axis_table, link.link_table, enabled=False)
    trace.metadata["explained_variance_weighting"] = "on" if wp.explained_variance_weighting else "off"
    paths = write_step_15a_artifacts(context.output_dir, trace)
    mark_step_completed(
        state,
        STEP_15A_WEIGHTING,
        artifact_paths={k: str(v) for k, v in paths.items()},
        parameters=trace.metadata,
    )
    return state


def compute_axis_jcvpca_weighted(reexpress, pca_a, pca_b, included_pcs):
    from layer3_jcvpca.aggregation import build_axis_table
    import numpy as np

    jcvpca_axis = reexpress.B_abs_loadings - reexpress.A_abs_loadings
    axis_table = build_axis_table(
        reexpress.A_abs_loadings,
        reexpress.B_abs_loadings,
        jcvpca_axis,
        reexpress.feature_names,
        pca_a.pca_A_variance_ratio,
        pca_b.pca_B_variance_ratio,
        export_weighted=True,
    )
    axis_table = axis_table[axis_table["pc"].isin(included_pcs)].copy()
    from layer3_jcvpca.jcvpca_workbench import AxisJcvpcaTrace

    return AxisJcvpcaTrace(
        jcvpca_axis=jcvpca_axis,
        axis_table=axis_table,
        included_pcs=included_pcs,
    )


def run_step_16a_nv(
    context,
    state: WorkbenchRunState,
) -> WorkbenchRunState:
    ok, msg = step_prerequisites_met(state, STEP_16A_NV)
    if not ok:
        raise StepRunError(msg)
    plan = _construction_plan(context)
    if plan.get("analysis_mode") != "longitudinal":
        mark_step_completed(
            state,
            STEP_16A_NV,
            artifact_paths={},
            warnings=[{"reason_code": "nv_skipped", "message": "NV baseline applies to longitudinal mode only."}],
            parameters={"skipped": True, "analysis_mode": plan.get("analysis_mode")},
        )
        return state

    pca_a = load_pca_a_state(context.output_dir)
    included = load_included_pcs(context.output_dir)
    loaded_a, _ = load_loaded_datasets(context.output_dir)
    centered_a = load_centered_a_features(context.output_dir, pca_a.feature_names)
    sid = loaded_a["_source_session_id"].astype(str)
    r1_mask = sid.str.contains("_R1")
    r2_mask = sid.str.contains("_R2")
    if not r1_mask.any() or not r2_mask.any():
        raise StepRunError("Cannot split T1 R1/R2 from loaded Dataset A for NV baseline.")

    centered_r2 = centered_a.loc[r2_mask, pca_a.feature_names]
    B_proj = __import__("numpy").matmul(centered_r2.to_numpy(), pca_a.pca_A_frame.transpose())
    pca_b_nv = fit_pca_on_projected_b(B_proj, pca_a.selected_m, pca_a.feature_names)
    rex_nv = reexpress_b_loadings(pca_a, pca_b_nv)
    nv_link = compute_link_rss(rex_nv, pca_a, included_pcs=included, export_weighted=False)

    main_link = pd.read_csv(context.output_dir / "link_level_jcvpca_unweighted.csv")
    main_vs_nv = build_main_vs_nv_table(main_link, nv_link.link_table)
    nv_meta = {
        "nv_mode": "intra-subject T1 R1 vs R2",
        "descriptive_only": True,
        "n_r1_rows": int(r1_mask.sum()),
        "n_r2_rows": int(r2_mask.sum()),
        "uses_main_pca_A_reference_frame": True,
    }
    paths = write_step_16a_nv_artifacts(
        context.output_dir,
        nv_link_table=nv_link.link_table,
        main_vs_nv=main_vs_nv,
        nv_metadata=nv_meta,
    )
    mark_step_completed(
        state,
        STEP_16A_NV,
        artifact_paths={k: str(v) for k, v in paths.items()},
        parameters=nv_meta,
    )
    return state


def run_step_17a_exploratory(
    context,
    state: WorkbenchRunState,
) -> WorkbenchRunState:
    ok, msg = step_prerequisites_met(state, STEP_17A_EXPLORATORY)
    if not ok:
        raise StepRunError(msg)
    plan = _construction_plan(context)
    link = pd.read_csv(context.output_dir / "link_level_jcvpca_unweighted.csv")
    summary = (
        link.groupby(["link_id", "pc"])["JcvPCA_link"]
        .agg(mean_signed_delta="mean", mean_abs_delta=lambda s: float(s.abs().mean()))
        .reset_index()
    )
    meta = {
        "analysis_mode": plan.get("analysis_mode"),
        "numeric_summary_only": True,
        "no_scientific_conclusions": True,
    }
    if plan.get("analysis_mode") != "exploratory":
        meta["note"] = "Exploratory summary computed from main link table; mode is not exploratory."
    paths = write_step_17a_exploratory_artifacts(context.output_dir, summary=summary, metadata=meta)
    mark_step_completed(
        state,
        STEP_17A_EXPLORATORY,
        artifact_paths={k: str(v) for k, v in paths.items()},
        parameters=meta,
    )
    return state


def run_step_18a_export(
    context,
    state: WorkbenchRunState,
) -> WorkbenchRunState:
    ok, msg = step_prerequisites_met(state, STEP_18A_EXPORT)
    if not ok:
        raise StepRunError(msg)
    all_paths: dict[str, str] = {}
    for step in state.steps.values():
        all_paths.update(step.artifact_paths)
    path = write_step_18a_export_manifest(context.output_dir, all_paths)
    mark_step_completed(
        state,
        STEP_18A_EXPORT,
        artifact_paths={"workbench_export_manifest": str(path)},
        parameters={"n_artifacts": len(all_paths)},
    )
    return state


def run_jcvpca_step(
    step_id: str,
    context,
    state: WorkbenchRunState,
    *,
    weighting_params: WeightingParameters | None = None,
) -> WorkbenchRunState:
    if step_id == STEP_10A_B_PROJECTION:
        return run_step_10a_project_b(context, state)
    if step_id == STEP_11A_PCA_B:
        return run_step_11a_pca_projected_b(context, state)
    if step_id == STEP_12A_REEXPRESS:
        return run_step_12a_reexpress(context, state)
    if step_id == STEP_13A_AXIS_JCVPCA:
        return run_step_13a_axis_jcvpca(context, state)
    if step_id == STEP_14A_RSS:
        return run_step_14a_rss(context, state)
    if step_id == STEP_15A_WEIGHTING:
        return run_step_15a_weighting(context, state, weighting_params)
    if step_id == STEP_16A_NV:
        return run_step_16a_nv(context, state)
    if step_id == STEP_17A_EXPLORATORY:
        return run_step_17a_exploratory(context, state)
    if step_id == STEP_18A_EXPORT:
        return run_step_18a_export(context, state)
    raise StepRunError(f"Unknown JcvPCA step: {step_id}")
