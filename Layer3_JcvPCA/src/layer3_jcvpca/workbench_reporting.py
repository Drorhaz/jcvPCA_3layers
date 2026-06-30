"""Artifact writers for Gaga workbench step runner (Phase 6–7)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from layer3_jcvpca.pc_focus import PcFocusResult
from layer3_jcvpca.jcvpca_trace import (
    CENTERED_VALIDATION_COLUMNS,
    CENTERING_VALUES_COLUMNS,
    PcaATrace,
    RAW_FEATURE_STATS_COLUMNS,
)
from layer3_jcvpca.viz import (
    plot_cumulative_variance_with_threshold,
    plot_pca_a_loadings_heatmap,
    plot_scree,
    _save,
)
from layer3_jcvpca.workbench_pca_stability import (
    WorkbenchPcaStabilityBundle,
    build_stability_report_rows,
    check_pca_stability_gate,
    save_pca_stability_acknowledgment,
)
from layer3_jcvpca.workbench_state import WorkbenchRunState, save_run_state


def write_step_6a_artifacts(
    output_dir: Path | str,
    *,
    loaded_a: pd.DataFrame,
    loaded_b: pd.DataFrame,
    dimensions: dict[str, Any],
) -> dict[str, Path]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "loaded_dataset_A": out / "_loaded_dataset_A.parquet",
        "loaded_dataset_B": out / "_loaded_dataset_B.parquet",
        "loaded_dimensions": out / "loaded_dimensions.json",
    }
    loaded_a.to_parquet(paths["loaded_dataset_A"], index=False)
    loaded_b.to_parquet(paths["loaded_dataset_B"], index=False)
    paths["loaded_dimensions"].write_text(json.dumps(dimensions, indent=2), encoding="utf-8")
    return paths


def write_step_6b_artifacts(
    output_dir: Path | str,
    *,
    preview_a: pd.DataFrame,
    preview_b: pd.DataFrame,
    stats_a: pd.DataFrame,
    stats_b: pd.DataFrame,
    preview_head_rows: int = 20,
) -> dict[str, Path]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "raw_dataset_A_preview": out / "raw_dataset_A_preview.csv",
        "raw_dataset_B_preview": out / "raw_dataset_B_preview.csv",
        "raw_feature_stats_A": out / "raw_feature_stats_A.csv",
        "raw_feature_stats_B": out / "raw_feature_stats_B.csv",
    }
    preview_a.head(preview_head_rows).to_csv(paths["raw_dataset_A_preview"], index=False)
    preview_b.head(preview_head_rows).to_csv(paths["raw_dataset_B_preview"], index=False)
    stats_a.to_csv(paths["raw_feature_stats_A"], index=False)
    stats_b.to_csv(paths["raw_feature_stats_B"], index=False)
    return paths


def write_step_6c_artifacts(
    output_dir: Path | str,
    *,
    centers_a: pd.DataFrame,
    centers_b: pd.DataFrame,
    centered_preview_a: pd.DataFrame,
    centered_preview_b: pd.DataFrame,
    validation: pd.DataFrame,
    summary: dict[str, Any],
    preview_head_rows: int = 20,
) -> dict[str, Path]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "centering_values_A": out / "centering_values_A.csv",
        "centering_values_B": out / "centering_values_B.csv",
        "centered_dataset_A_preview": out / "centered_dataset_A_preview.csv",
        "centered_dataset_B_preview": out / "centered_dataset_B_preview.csv",
        "centered_validation_report": out / "centered_validation_report.csv",
        "centering_summary": out / "centering_summary.json",
    }
    centers_a.to_csv(paths["centering_values_A"], index=False)
    centers_b.to_csv(paths["centering_values_B"], index=False)
    centered_preview_a.head(preview_head_rows).to_csv(paths["centered_dataset_A_preview"], index=False)
    centered_preview_b.head(preview_head_rows).to_csv(paths["centered_dataset_B_preview"], index=False)
    validation.to_csv(paths["centered_validation_report"], index=False)
    paths["centering_summary"].write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return paths


def load_loaded_datasets(output_dir: Path | str) -> tuple[pd.DataFrame, pd.DataFrame]:
    root = Path(output_dir)
    a_path = root / "_loaded_dataset_A.parquet"
    b_path = root / "_loaded_dataset_B.parquet"
    if not a_path.is_file() or not b_path.is_file():
        raise FileNotFoundError("Loaded datasets not found; run Step 6A first.")
    return pd.read_parquet(a_path), pd.read_parquet(b_path)


def persist_run_state(state: WorkbenchRunState) -> Path:
    return save_run_state(state, state.output_dir)


def write_step_7a_artifacts(
    output_dir: Path | str,
    trace: PcaATrace,
) -> dict[str, Path]:
    """Write PCA-on-A artifacts for Step 7A."""
    out = Path(output_dir)
    plots_dir = out / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    params = trace.parameters
    params_payload = {
        "variance_threshold": params.variance_threshold,
        "min_pcs": params.min_pcs,
        "max_pcs": params.max_pcs,
        "selected_m_mode": params.selected_m_mode,
        "selected_m_override": params.selected_m_override,
        "n_rows_A": trace.n_rows,
        "n_features": trace.n_features,
        "dataset_side": "A_only",
        "z_score_applied": False,
        "scaling_applied": False,
    }

    paths = {
        "pca_A_parameters": out / "pca_A_parameters.json",
        "pca_A_explained_variance": out / "pca_A_explained_variance.csv",
        "pca_A_cumulative_variance": out / "pca_A_cumulative_variance.csv",
        "pca_A_loadings": out / "pca_A_loadings.csv",
        "pca_A_selected_m": out / "pca_A_selected_m.json",
        "pca_A_feature_names": out / "pca_A_feature_names.csv",
        "pca_A_model_metadata": out / "pca_A_model_metadata.json",
        "pca_A_scree_plot": plots_dir / "pca_A_scree_plot.png",
        "pca_A_cumulative_variance_plot": plots_dir / "pca_A_cumulative_variance.png",
        "pca_A_loadings_heatmap": plots_dir / "pca_A_loadings_heatmap.png",
    }

    paths["pca_A_parameters"].write_text(json.dumps(params_payload, indent=2), encoding="utf-8")
    trace.explained_variance.to_csv(paths["pca_A_explained_variance"], index=False)
    trace.cumulative_variance.to_csv(paths["pca_A_cumulative_variance"], index=False)
    trace.loadings.to_csv(paths["pca_A_loadings"], index=False)

    selected_m_payload = {
        "selected_m": trace.selected_m,
        "selected_m_reason": trace.selected_m_reason,
        "variance_threshold": params.variance_threshold,
        "min_pcs": params.min_pcs,
        "max_pcs": params.max_pcs,
        "selected_m_mode": params.selected_m_mode,
        "cumulative_variance_at_selected_m": float(
            trace.cumulative_variance.iloc[trace.selected_m - 1]["cumulative_explained_variance"]
        ),
    }
    paths["pca_A_selected_m"].write_text(json.dumps(selected_m_payload, indent=2), encoding="utf-8")

    feature_names_df = pd.DataFrame({"feature_index": range(len(trace.feature_names)), "feature_column": trace.feature_names})
    feature_names_df.to_csv(paths["pca_A_feature_names"], index=False)

    evr_full = trace.explained_variance["explained_variance_ratio"].to_numpy()
    metadata = {
        "fit_dataset": "A_centered_only",
        "n_rows_A": trace.n_rows,
        "n_features": trace.n_features,
        "n_components_fitted": int(len(evr_full)),
        "selected_m": trace.selected_m,
        "selected_m_reason": trace.selected_m_reason,
        "explained_variance_sum": float(evr_full.sum()),
        "feature_names_order": trace.feature_names,
        "components_shape": list(trace.components.shape),
        "components": trace.components.tolist(),
        "z_score_applied": False,
        "dataset_B_used": False,
    }
    paths["pca_A_model_metadata"].write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    _save(plot_scree(evr_full, title="PCA scree plot (Dataset A)"), paths["pca_A_scree_plot"])
    _save(
        plot_cumulative_variance_with_threshold(
            evr_full,
            threshold=params.variance_threshold,
            title="Cumulative variance (Dataset A)",
        ),
        paths["pca_A_cumulative_variance_plot"],
    )
    _save(
        plot_pca_a_loadings_heatmap(
            trace.components,
            trace.feature_names,
            title="PCA A loadings heatmap",
        ),
        paths["pca_A_loadings_heatmap"],
    )

    return paths


def write_pca_stability_artifacts(
    output_dir: Path | str,
    bundle: WorkbenchPcaStabilityBundle,
) -> dict[str, Path]:
    """Write PCA stability/readiness artifacts for centered A and B."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    for side, result in (("A", bundle.a), ("B", bundle.b)):
        prefix = f"pca_{side}"
        paths[f"{prefix}_stability_report"] = out / f"{prefix}_stability_report.csv"
        paths[f"{prefix}_stability_summary"] = out / f"{prefix}_stability_summary.json"
        paths[f"{prefix}_near_zero_variance_features"] = out / f"{prefix}_near_zero_variance_features.csv"
        paths[f"{prefix}_singular_values"] = out / f"{prefix}_singular_values.csv"

        build_stability_report_rows(result).to_csv(paths[f"{prefix}_stability_report"], index=False)
        summary_payload = {
            "role": result.role,
            "status": result.status,
            "metrics": result.metrics,
            "n_findings": len(result.findings),
            "findings": result.findings,
            "numerical_readiness_only": True,
            "note": (
                "A defines the PCA reference frame; selected_m is derived from A only."
                if side == "A"
                else "B readiness is diagnostic only; B does not choose selected_m."
            ),
        }
        paths[f"{prefix}_stability_summary"].write_text(
            json.dumps(summary_payload, indent=2, default=str),
            encoding="utf-8",
        )
        result.near_zero_variance_features.to_csv(
            paths[f"{prefix}_near_zero_variance_features"],
            index=False,
        )
        if result.singular_values.empty:
            pd.DataFrame(columns=["index", "singular_value"]).to_csv(
                paths[f"{prefix}_singular_values"],
                index=False,
            )
        else:
            result.singular_values.to_csv(paths[f"{prefix}_singular_values"], index=False)

        if not result.split_half.empty:
            sh_path = out / f"{prefix}_split_half_similarity.csv"
            result.split_half.to_csv(sh_path, index=False)
            paths[f"{prefix}_split_half_similarity"] = sh_path

    combined = {
        "combined_status": bundle.combined_status,
        "can_continue_to_phase8": bundle.can_continue_to_phase8,
        "requires_acknowledgment": bundle.requires_acknowledgment,
        "warnings_acknowledged": bundle.warnings_acknowledged,
        "A_status": bundle.a.status,
        "B_status": bundle.b.status,
        "A_selected_m": bundle.a.metrics.get("selected_m"),
        "A_selected_m_reason": bundle.a.metrics.get("selected_m_reason"),
        "numerical_readiness_only": True,
        "reference_note": "Dataset A defines the PCA reference frame.",
        "comparison_note": (
            "Dataset B readiness is checked for later projection and projected-B PCA; "
            "selected_m is derived from A only."
        ),
    }
    paths["pca_stability_combined_summary"] = out / "pca_stability_combined_summary.json"
    paths["pca_stability_combined_summary"].write_text(json.dumps(combined, indent=2), encoding="utf-8")
    return paths


def write_step_9a_artifacts(
    output_dir: Path | str,
    result: PcFocusResult,
) -> dict[str, Path]:
    from layer3_jcvpca.pc_focus import pc_focus_selection_payload

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "pc_focus_selection": out / "pc_focus_selection.json",
        "pc_focus_table": out / "pc_focus_table.csv",
    }
    payload = pc_focus_selection_payload(result)
    paths["pc_focus_selection"].write_text(json.dumps(payload, indent=2), encoding="utf-8")
    result.focus_table.to_csv(paths["pc_focus_table"], index=False)
    return paths
