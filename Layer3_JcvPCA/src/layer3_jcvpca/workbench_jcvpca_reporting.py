"""Artifact writers for workbench JcvPCA steps 10–18."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from layer3_jcvpca.jcvpca_workbench import (
    AxisJcvpcaTrace,
    BProjectionTrace,
    LinkRssTrace,
    PcaBProjectedTrace,
    ReexpressTrace,
    WeightingTrace,
    WorkbenchPcaAState,
)
from layer3_jcvpca.viz import _save, plot_pc_scores_a_vs_b, plot_workbench_pc_score_summary_heatmap


def _plots_dir(output_dir: Path) -> Path:
    p = output_dir / "plots"
    p.mkdir(parents=True, exist_ok=True)
    return p


def write_step_10a_artifacts(
    output_dir: Path | str,
    trace: BProjectionTrace,
    pca_a: WorkbenchPcaAState,
    *,
    preview_rows: int = 20,
) -> dict[str, Path]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    np.save(out / "_B_projected_scores.npy", trace.B_projected)
    np.save(out / "_A_pca_scores.npy", trace.A_scores)

    preview = pd.DataFrame(
        trace.B_projected[:preview_rows],
        columns=[f"PC{i}" for i in range(1, trace.selected_m + 1)],
    )
    paths = {
        "B_projected_preview": out / "B_projected_preview.csv",
        "B_projected_metadata": out / "B_projected_metadata.json",
        "pc_scores_A_vs_projected_B": _plots_dir(out) / "pc_scores_A_vs_projected_B.png",
        "pc_score_heatmap_A_B": _plots_dir(out) / "pc_score_heatmap_A_B.png",
    }
    preview.to_csv(paths["B_projected_preview"], index=False)
    meta = {
        "n_rows_B": trace.n_rows_B,
        "n_features": trace.n_features,
        "selected_m": trace.selected_m,
        "pca_A_frame_shape": list(pca_a.pca_A_frame.shape),
        "B_projected_shape": list(trace.B_projected.shape),
        "A_scores_shape": list(trace.A_scores.shape),
        "projection_method": trace.projection_method,
        "used_pca_transform_on_B_raw": False,
    }
    paths["B_projected_metadata"].write_text(json.dumps(meta, indent=2), encoding="utf-8")
    _save(
        plot_pc_scores_a_vs_b(trace.A_scores, trace.B_projected),
        paths["pc_scores_A_vs_projected_B"],
    )
    _save(
        plot_workbench_pc_score_summary_heatmap(trace.A_scores, trace.B_projected),
        paths["pc_score_heatmap_A_B"],
    )
    return paths


def write_step_11a_artifacts(output_dir: Path | str, trace: PcaBProjectedTrace) -> dict[str, Path]:
    out = Path(output_dir)
    paths = {
        "pca_B_projected_explained_variance": out / "pca_B_projected_explained_variance.csv",
        "pca_B_projected_loadings": out / "pca_B_projected_loadings.csv",
        "pca_B_projected_metadata": out / "pca_B_projected_metadata.json",
    }
    trace.explained_variance.to_csv(paths["pca_B_projected_explained_variance"], index=False)
    trace.loadings.to_csv(paths["pca_B_projected_loadings"], index=False)
    np.save(out / "_pca_B_projected_components.npy", trace.pca_B_frame)
    meta = {
        "selected_m": trace.selected_m,
        "components_shape": list(trace.pca_B_frame.shape),
        "components": trace.pca_B_frame.tolist(),
        "explained_variance_ratio": trace.pca_B_variance_ratio.tolist(),
    }
    paths["pca_B_projected_metadata"].write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return paths


def write_step_12a_artifacts(output_dir: Path | str, trace: ReexpressTrace) -> dict[str, Path]:
    out = Path(output_dir)
    np.save(out / "_B_reexpressed_loadings.npy", trace.B_reexpressed_loadings)
    np.save(out / "_A_abs_loadings.npy", trace.A_abs_loadings)
    np.save(out / "_B_abs_loadings.npy", trace.B_abs_loadings)

    rows: list[dict[str, Any]] = []
    for pc in range(trace.selected_m):
        for fi, feat in enumerate(trace.feature_names):
            rows.append(
                {
                    "pc": pc + 1,
                    "feature_column": feat,
                    "B_reexpressed_loading": float(trace.B_reexpressed_loadings[pc, fi]),
                    "A_loading": float(trace.pca_A_frame[pc, fi]),
                    "A_abs_loading": float(trace.A_abs_loadings[pc, fi]),
                    "B_abs_reexpressed": float(trace.B_abs_loadings[pc, fi]),
                }
            )
    b_rex = pd.DataFrame(rows)
    a_side = b_rex[["pc", "feature_column", "A_abs_loading"]].rename(columns={"A_abs_loading": "loading_abs"})
    b_side = b_rex[["pc", "feature_column", "B_abs_reexpressed"]].rename(
        columns={"B_abs_reexpressed": "loading_abs"}
    )
    preview = a_side.merge(b_side, on=["pc", "feature_column"], suffixes=("_A", "_B"))

    paths = {
        "B_reexpressed_loadings": out / "B_reexpressed_loadings.csv",
        "A_vs_B_reexpressed_loadings_preview": out / "A_vs_B_reexpressed_loadings_preview.csv",
        "reexpress_metadata": out / "reexpress_metadata.json",
    }
    b_rex.to_csv(paths["B_reexpressed_loadings"], index=False)
    preview.to_csv(paths["A_vs_B_reexpressed_loadings_preview"], index=False)
    paths["reexpress_metadata"].write_text(
        json.dumps(
            {
                "selected_m": trace.selected_m,
                "pca_A_frame_shape": list(trace.pca_A_frame.shape),
                "pca_B_frame_shape": list(trace.pca_B_frame.shape),
                "B_reexpressed_shape": list(trace.B_reexpressed_loadings.shape),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return paths


def write_step_13a_artifacts(output_dir: Path | str, trace: AxisJcvpcaTrace) -> dict[str, Path]:
    out = Path(output_dir)
    paths = {
        "axis_level_jcvpca_unweighted": out / "axis_level_jcvpca_unweighted.csv",
        "axis_level_jrw_A_B": out / "axis_level_jrw_A_B.csv",
        "axis_jcvpca_metadata": out / "axis_jcvpca_metadata.json",
    }
    trace.axis_table.to_csv(paths["axis_level_jcvpca_unweighted"], index=False)
    jrw = trace.axis_table.copy()
    jrw = jrw.rename(
        columns={
            "loading_A_abs": "A_abs",
            "loading_B_reprojected_abs": "B_abs",
        }
    )
    jrw.to_csv(paths["axis_level_jrw_A_B"], index=False)
    paths["axis_jcvpca_metadata"].write_text(
        json.dumps(
            {
                "included_pcs": trace.included_pcs,
                "sign_convention": trace.sign_convention,
                "sign_note": "Positive = numeric contribution increased in B relative to A.",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return paths


def write_step_14a_artifacts(output_dir: Path | str, trace: LinkRssTrace) -> dict[str, Path]:
    out = Path(output_dir)
    paths = {
        "link_level_jrw_rss": out / "link_level_jrw_rss.csv",
        "link_level_jcvpca_unweighted": out / "link_level_jcvpca_unweighted.csv",
        "link_rss_metadata": out / "link_rss_metadata.json",
    }
    trace.link_table.to_csv(paths["link_level_jrw_rss"], index=False)
    trace.link_table.to_csv(paths["link_level_jcvpca_unweighted"], index=False)
    paths["link_rss_metadata"].write_text(
        json.dumps({"included_pcs": trace.included_pcs, "formula": trace.formula}, indent=2),
        encoding="utf-8",
    )
    return paths


def write_step_15a_artifacts(output_dir: Path | str, trace: WeightingTrace) -> dict[str, Path]:
    out = Path(output_dir)
    paths = {
        "weighting_metadata": out / "weighting_metadata.json",
    }
    if trace.enabled:
        paths["axis_level_jcvpca_weighted"] = out / "axis_level_jcvpca_weighted.csv"
        paths["link_level_jcvpca_weighted"] = out / "link_level_jcvpca_weighted.csv"
        trace.axis_table_weighted.to_csv(paths["axis_level_jcvpca_weighted"], index=False)
        trace.link_table_weighted.to_csv(paths["link_level_jcvpca_weighted"], index=False)
    paths["weighting_metadata"].write_text(json.dumps(trace.metadata, indent=2), encoding="utf-8")
    return paths


def write_step_16a_nv_artifacts(
    output_dir: Path | str,
    *,
    nv_link_table: pd.DataFrame,
    main_vs_nv: pd.DataFrame,
    nv_metadata: dict[str, Any],
) -> dict[str, Path]:
    out = Path(output_dir)
    paths = {
        "nv_results_raw": out / "nv_results_raw.csv",
        "nv_baseline": out / "nv_baseline.json",
        "main_vs_nv_descriptive_comparison": out / "main_vs_nv_descriptive_comparison.csv",
    }
    nv_link_table.to_csv(paths["nv_results_raw"], index=False)
    main_vs_nv.to_csv(paths["main_vs_nv_descriptive_comparison"], index=False)
    paths["nv_baseline"].write_text(json.dumps(nv_metadata, indent=2), encoding="utf-8")
    return paths


def write_step_17a_exploratory_artifacts(
    output_dir: Path | str,
    *,
    summary: pd.DataFrame,
    metadata: dict[str, Any],
) -> dict[str, Path]:
    out = Path(output_dir)
    paths = {
        "exploratory_numeric_summary": out / "exploratory_numeric_summary.csv",
        "exploratory_metadata": out / "exploratory_metadata.json",
    }
    summary.to_csv(paths["exploratory_numeric_summary"], index=False)
    paths["exploratory_metadata"].write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return paths


def write_step_18a_export_manifest(output_dir: Path | str, artifact_paths: dict[str, str]) -> Path:
    out = Path(output_dir)
    manifest = {
        "workbench_export_complete": True,
        "numerical_outputs_only": True,
        "artifact_paths": artifact_paths,
    }
    path = out / "workbench_export_manifest.json"
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return path


def load_reexpress_trace(output_dir: Path | str, pca_a: WorkbenchPcaAState) -> ReexpressTrace:
    root = Path(output_dir)
    pca_b_meta = json.loads((root / "pca_B_projected_metadata.json").read_text(encoding="utf-8"))
    pca_B_frame = np.load(root / "_pca_B_projected_components.npy")
    return ReexpressTrace(
        feature_names=pca_a.feature_names,
        selected_m=pca_a.selected_m,
        pca_A_frame=pca_a.pca_A_frame,
        pca_B_frame=pca_B_frame,
        B_reexpressed_loadings=np.load(root / "_B_reexpressed_loadings.npy"),
        A_abs_loadings=np.load(root / "_A_abs_loadings.npy"),
        B_abs_loadings=np.load(root / "_B_abs_loadings.npy"),
    )


def load_pca_b_projected_trace(output_dir: Path | str) -> PcaBProjectedTrace:
    root = Path(output_dir)
    meta = json.loads((root / "pca_B_projected_metadata.json").read_text(encoding="utf-8"))
    return PcaBProjectedTrace(
        selected_m=int(meta["selected_m"]),
        pca_B_frame=np.load(root / "_pca_B_projected_components.npy"),
        pca_B_variance_ratio=np.asarray(meta["explained_variance_ratio"], dtype=float),
        explained_variance=pd.read_csv(root / "pca_B_projected_explained_variance.csv"),
        loadings=pd.read_csv(root / "pca_B_projected_loadings.csv"),
    )
