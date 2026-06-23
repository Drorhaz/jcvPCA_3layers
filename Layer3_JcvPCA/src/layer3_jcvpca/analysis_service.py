"""Direct single-window Layer 3 JcvPCA analysis service."""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from layer3_jcvpca import aggregation, reporting
from layer3_jcvpca.core import compute_jcvpca, select_selected_m_from_A
from layer3_jcvpca.distribution import compute_jrw_distribution_metrics
from layer3_jcvpca.identity import enrich_dataframe_with_identity
from layer3_jcvpca.io import build_joint_link_map, infer_feature_columns
from layer3_jcvpca.nv_compare import build_main_vs_nv_table
from layer3_jcvpca.preflight import PreflightReport, run_preflight
from layer3_jcvpca.validation import validate_selected_m


@dataclass
class AnalysisParams:
    pc_selection_mode: str = "project_default"  # fixed_n | cumulative_variance | project_default
    n_pcs: int | None = None
    cumulative_variance_threshold: float = 0.90
    min_pcs: int = 2
    max_pcs: int = 10
    min_rows_for_pca: int = 10
    export_weighted: bool = False
    nv_epsilon: float = 1e-6


@dataclass
class AnalysisIdentity:
    analysis_id: str
    participant_id: str = ""
    task_group: str = "Group4"
    exercise_name: str = ""
    analysis_type: str = "single_window_validation"
    notes: str = ""


@dataclass
class AnalysisResult:
    status: str
    output_dir: str
    selected_m: int
    pc_selection_reason: str
    main_result: dict
    nv_result: dict
    tables: dict[str, pd.DataFrame] = field(default_factory=dict)
    distribution_metrics: dict[str, Any] = field(default_factory=dict)
    manifest: dict[str, Any] = field(default_factory=dict)


def _resolve_selected_m(
    A_df: pd.DataFrame,
    feature_names: list[str],
    params: AnalysisParams,
) -> tuple[int, str, pd.DataFrame]:
    if params.pc_selection_mode == "fixed_n" and params.n_pcs is not None:
        m = int(params.n_pcs)
        _, evr = select_selected_m_from_A(A_df, feature_names, params.cumulative_variance_threshold)
        return m, f"fixed_n={m}", evr
    threshold = params.cumulative_variance_threshold
    if params.pc_selection_mode == "project_default":
        threshold = 0.90
    m, evr = select_selected_m_from_A(A_df, feature_names, threshold)
    m = max(params.min_pcs, min(m, params.max_pcs, len(feature_names)))
    reason = f"cumulative_variance>={threshold} on A (clamped to [{params.min_pcs},{params.max_pcs}])"
    return m, reason, evr


def run_direct_analysis(
    paths: dict[str, str],
    identity: AnalysisIdentity,
    params: AnalysisParams,
    output_dir: str | Path,
    *,
    preflight: PreflightReport | None = None,
    stability_params=None,
) -> AnalysisResult:
    """Run main A vs B and NV_A vs NV_B comparisons."""
    if preflight is None:
        preflight = run_preflight(paths, min_rows_for_pca=params.min_rows_for_pca)
    if preflight.status == "blocking":
        raise ValueError("Preflight blocking; cannot run analysis.")

    loaded = {w.role: w for w in preflight.windows}
    A_df = loaded["A"].df
    B_df = loaded["B"].df
    NV_A_df = loaded["NV_A"].df
    NV_B_df = loaded["NV_B"].df
    feature_names = preflight.feature_names
    joint_link_map = build_joint_link_map(feature_names)

    selected_m, pc_reason, evr_full = _resolve_selected_m(A_df, feature_names, params)
    validate_selected_m(
        selected_m=selected_m,
        n_features_A=len(feature_names),
        n_rows_A=len(A_df),
        n_rows_B=len(B_df),
        min_rows_for_pca=params.min_rows_for_pca,
    )

    main = compute_jcvpca(
        A_df,
        B_df,
        feature_names,
        variance_threshold=params.cumulative_variance_threshold,
        selected_m=selected_m,
        min_rows_for_pca=params.min_rows_for_pca,
    )
    nv = compute_jcvpca(
        NV_A_df,
        NV_B_df,
        feature_names,
        variance_threshold=params.cumulative_variance_threshold,
        selected_m=selected_m,
        min_rows_for_pca=params.min_rows_for_pca,
    )

    def _tables(comparison: str, result: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
        axis_df = aggregation.build_axis_table(
            result["A_abs_loadings"],
            result["B_abs_loadings"],
            result["jcvpca_axis"],
            feature_names,
            result["pca_A_variance_ratio"],
            result["pca_B_variance_ratio"],
            export_weighted=params.export_weighted,
        )
        axis_df.insert(0, "comparison", comparison)
        link_df = aggregation.aggregate_axis_to_link_rss(
            result["A_abs_loadings"],
            result["B_abs_loadings"],
            feature_names,
            joint_link_map,
            pca_A_variance_ratio=result["pca_A_variance_ratio"],
            export_weighted=params.export_weighted,
        )
        link_df.insert(0, "comparison", comparison)
        return axis_df, link_df

    main_axis, main_link = _tables("main_A_vs_B", main)
    nv_axis, nv_link = _tables("NV_A_vs_B", nv)

    jrw_feature = enrich_dataframe_with_identity(main_axis, feature_col="feature")
    jrw_joint = main_link.copy()
    delta_jrw = main_link[["comparison", "pc", "link_id", "JcvPCA_link"]].copy()
    nv_jrw = nv_link.copy()
    main_vs_nv = build_main_vs_nv_table(main_link, nv_link, epsilon=params.nv_epsilon)

    pc_var = reporting.build_explained_variance_table("main_A_vs_B", evr_full, selected_m)
    dist_metrics = compute_jrw_distribution_metrics(main_link)

    out = reporting.ensure_output_dir(output_dir)
    reporting.write_analysis_package(
        out,
        identity=identity,
        paths=paths,
        preflight=preflight,
        params=params,
        selected_m=selected_m,
        pc_selection_reason=pc_reason,
        tables={
            "pc_variance_table.csv": pc_var,
            "jrw_feature_table.csv": jrw_feature,
            "jrw_joint_table.csv": jrw_joint,
            "jcvpca_delta_jrw_table.csv": delta_jrw,
            "nv_jrw_table.csv": nv_jrw,
            "main_vs_nv_comparison_table.csv": main_vs_nv,
        },
        main_result=main,
        nv_result=nv,
        distribution_metrics=dist_metrics,
    )

    stab_a = preflight.stability.get("A")
    manifest = {
        "analysis_id": identity.analysis_id,
        "created_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "input_paths": paths,
        "selected_n_pcs": selected_m,
        "pc_selection_reason": pc_reason,
        "matrix_stability_checked": bool(preflight.stability),
        "matrix_stability_pass": preflight.status == "pass",
        "matrix_stability_warning_count": preflight.warning_count,
        "matrix_stability_blocking_count": preflight.blocking_count,
        "rank_A": stab_a.metrics.get("matrix_rank") if stab_a else None,
        "condition_number_A": stab_a.metrics.get("condition_number") if stab_a else None,
        "dominant_pc_variance_percent_A": stab_a.metrics.get("dominant_pc_variance_percent")
        if stab_a
        else None,
        "near_zero_variance_feature_count_A": stab_a.metrics.get("near_zero_variance_feature_count")
        if stab_a
        else None,
        "frame_to_feature_ratio_A": stab_a.metrics.get("frame_to_feature_ratio") if stab_a else None,
        "split_half_stability_summary": stab_a.metrics.get("split_half_pc_similarity")
        if stab_a
        else None,
        "references": [
            "Layer3_JcvPCA/references/S1_File.py",
            "Layer3_JcvPCA/3_layers_Matser_plan_Full/LAYER3_JCVPCA_PSEUDOCODE.md",
            "Layer3_JcvPCA/docs/LAYER3_SCOPE.md",
        ],
    }
    reporting.write_json(out / "analysis_manifest.json", manifest)

    return AnalysisResult(
        status="completed",
        output_dir=str(out),
        selected_m=selected_m,
        pc_selection_reason=pc_reason,
        main_result=main,
        nv_result=nv,
        tables={
            "pc_variance": pc_var,
            "jrw_feature": jrw_feature,
            "jrw_joint": jrw_joint,
            "delta_jrw": delta_jrw,
            "nv_jrw": nv_jrw,
            "main_vs_nv": main_vs_nv,
        },
        distribution_metrics=dist_metrics,
        manifest=manifest,
    )
