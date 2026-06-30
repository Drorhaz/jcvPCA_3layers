"""Stepwise JcvPCA workbench computations (Phases 10–15).

Mirrors ``core.compute_jcvpca()`` using pre-centered workbench artifacts.
Does not call ``compute_jcvpca()`` and does not modify ``core.py``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA

from layer3_jcvpca.aggregation import aggregate_axis_to_link_rss, build_axis_table
from layer3_jcvpca.io import build_joint_link_map
from layer3_jcvpca.jcvpca_trace import (
    load_centered_a_features,
    load_centered_b_features,
)


@dataclass
class WorkbenchPcaAState:
    selected_m: int
    feature_names: list[str]
    pca_A_frame: np.ndarray
    pca_A_variance_ratio: np.ndarray
    explained_variance: pd.DataFrame


@dataclass
class BProjectionTrace:
    n_rows_B: int
    n_features: int
    selected_m: int
    B_projected: np.ndarray
    A_scores: np.ndarray
    projection_method: str = "manual_matmul_B_centered @ pca_A_frame.T"


@dataclass
class PcaBProjectedTrace:
    selected_m: int
    pca_B_frame: np.ndarray
    pca_B_variance_ratio: np.ndarray
    explained_variance: pd.DataFrame
    loadings: pd.DataFrame


@dataclass
class ReexpressTrace:
    feature_names: list[str]
    selected_m: int
    pca_A_frame: np.ndarray
    pca_B_frame: np.ndarray
    B_reexpressed_loadings: np.ndarray
    A_abs_loadings: np.ndarray
    B_abs_loadings: np.ndarray


@dataclass
class AxisJcvpcaTrace:
    jcvpca_axis: np.ndarray
    axis_table: pd.DataFrame
    included_pcs: list[int]
    sign_convention: str = "|B_reexpressed| - |A_loading|"


@dataclass
class LinkRssTrace:
    link_table: pd.DataFrame
    included_pcs: list[int]
    formula: str = "JcvPCA_link = JRW_B_link - JRW_A_link (RSS over rx/ry/rz)"


@dataclass
class WeightingTrace:
    enabled: bool
    axis_table_weighted: pd.DataFrame
    link_table_weighted: pd.DataFrame
    metadata: dict[str, Any] = field(default_factory=dict)


def load_pca_a_state(output_dir: Path | str) -> WorkbenchPcaAState:
    root = Path(output_dir)
    selected = json.loads((root / "pca_A_selected_m.json").read_text(encoding="utf-8"))
    selected_m = int(selected["selected_m"])
    feature_names = pd.read_csv(root / "pca_A_feature_names.csv")["feature_column"].tolist()
    metadata = json.loads((root / "pca_A_model_metadata.json").read_text(encoding="utf-8"))
    pca_A_frame = np.asarray(metadata["components"], dtype=float)
    evr = pd.read_csv(root / "pca_A_explained_variance.csv")
    pca_A_variance_ratio = evr["explained_variance_ratio"].to_numpy()[:selected_m]
    if pca_A_frame.shape != (selected_m, len(feature_names)):
        raise ValueError("PCA A components shape mismatch with feature names / selected_m.")
    return WorkbenchPcaAState(
        selected_m=selected_m,
        feature_names=feature_names,
        pca_A_frame=pca_A_frame,
        pca_A_variance_ratio=pca_A_variance_ratio,
        explained_variance=evr,
    )


def load_included_pcs(output_dir: Path | str) -> list[int]:
    payload = json.loads((Path(output_dir) / "pc_focus_selection.json").read_text(encoding="utf-8"))
    included = payload.get("included_pcs") or []
    return [int(x) for x in included]


def project_b_into_a_space(
    centered_b: pd.DataFrame,
    centered_a: pd.DataFrame,
    pca_a: WorkbenchPcaAState,
) -> BProjectionTrace:
    """Step 10: B_projected = B_centered @ pca_A_frame.T (not PCA.transform)."""
    feature_names = pca_a.feature_names
    B = centered_b[feature_names].to_numpy(dtype=float)
    A = centered_a[feature_names].to_numpy(dtype=float)
    B_projected = np.matmul(B, pca_a.pca_A_frame.transpose())
    A_scores = np.matmul(A, pca_a.pca_A_frame.transpose())
    return BProjectionTrace(
        n_rows_B=B.shape[0],
        n_features=len(feature_names),
        selected_m=pca_a.selected_m,
        B_projected=B_projected,
        A_scores=A_scores,
    )


def fit_pca_on_projected_b(
    B_projected: np.ndarray,
    selected_m: int,
    feature_names: list[str],
) -> PcaBProjectedTrace:
    """Step 11: PCA on projected B with selected_m components."""
    pca_B = PCA(n_components=selected_m)
    pca_B.fit(B_projected)
    pca_B_frame = pca_B.components_
    evr = pca_B.explained_variance_ratio_
    explained_df = pd.DataFrame(
        {"pc": np.arange(1, len(evr) + 1), "explained_variance_ratio": evr}
    )
    loadings_rows: list[dict[str, Any]] = []
    for pc_idx in range(selected_m):
        for proj_idx in range(selected_m):
            loadings_rows.append(
                {
                    "pc": pc_idx + 1,
                    "projected_pc": proj_idx + 1,
                    "loading": float(pca_B_frame[pc_idx, proj_idx]),
                }
            )
    loadings = pd.DataFrame(loadings_rows)
    return PcaBProjectedTrace(
        selected_m=selected_m,
        pca_B_frame=pca_B_frame,
        pca_B_variance_ratio=evr,
        explained_variance=explained_df,
        loadings=loadings,
    )


def reexpress_b_loadings(pca_a: WorkbenchPcaAState, pca_b: PcaBProjectedTrace) -> ReexpressTrace:
    """Step 12: B_reexpressed = pca_B_frame @ pca_A_frame."""
    B_reexpressed = np.matmul(pca_b.pca_B_frame, pca_a.pca_A_frame)
    A_abs = np.abs(pca_a.pca_A_frame)
    B_abs = np.abs(B_reexpressed)
    return ReexpressTrace(
        feature_names=pca_a.feature_names,
        selected_m=pca_a.selected_m,
        pca_A_frame=pca_a.pca_A_frame,
        pca_B_frame=pca_b.pca_B_frame,
        B_reexpressed_loadings=B_reexpressed,
        A_abs_loadings=A_abs,
        B_abs_loadings=B_abs,
    )


def compute_axis_jcvpca(
    reexpress: ReexpressTrace,
    pca_a: WorkbenchPcaAState,
    pca_b: PcaBProjectedTrace,
    *,
    included_pcs: list[int],
) -> AxisJcvpcaTrace:
    """Step 13: jcvpca_axis = |B_reexpressed| - |A|."""
    jcvpca_axis = reexpress.B_abs_loadings - reexpress.A_abs_loadings
    axis_table = build_axis_table(
        reexpress.A_abs_loadings,
        reexpress.B_abs_loadings,
        jcvpca_axis,
        reexpress.feature_names,
        pca_a.pca_A_variance_ratio,
        pca_b.pca_B_variance_ratio,
        export_weighted=False,
    )
    axis_table = axis_table[axis_table["pc"].isin(included_pcs)].copy()
    return AxisJcvpcaTrace(
        jcvpca_axis=jcvpca_axis,
        axis_table=axis_table,
        included_pcs=included_pcs,
    )


def compute_link_rss(
    reexpress: ReexpressTrace,
    pca_a: WorkbenchPcaAState,
    *,
    included_pcs: list[int],
    export_weighted: bool = False,
) -> LinkRssTrace:
    """Step 14: RSS link aggregation JRW_B - JRW_A."""
    joint_map = build_joint_link_map(reexpress.feature_names)
    link_table = aggregate_axis_to_link_rss(
        reexpress.A_abs_loadings,
        reexpress.B_abs_loadings,
        reexpress.feature_names,
        joint_map,
        pca_A_variance_ratio=pca_a.pca_A_variance_ratio,
        export_weighted=export_weighted,
    )
    link_table = link_table[link_table["pc"].isin(included_pcs)].copy()
    return LinkRssTrace(link_table=link_table, included_pcs=included_pcs)


def apply_explained_variance_weighting(
    axis_table: pd.DataFrame,
    link_table: pd.DataFrame,
    *,
    enabled: bool,
) -> WeightingTrace:
    """Step 15: optional weighting by A explained variance (already on tables if enabled)."""
    if not enabled:
        return WeightingTrace(
            enabled=False,
            axis_table_weighted=axis_table.copy(),
            link_table_weighted=link_table.copy(),
            metadata={"explained_variance_weighting": "off"},
        )
    axis_w = axis_table.copy()
    if "weighted_jcvpca_axis" not in axis_w.columns:
        axis_w["weighted_jcvpca_axis"] = axis_w["jcvpca_axis"] * axis_w["explained_variance_A"]
    link_w = link_table.copy()
    if "weighted_JcvPCA_link" not in link_w.columns and "weight_A_variance_ratio" in link_w.columns:
        link_w["weighted_JcvPCA_link"] = link_w["JcvPCA_link"] * link_w["weight_A_variance_ratio"]
    return WeightingTrace(
        enabled=True,
        axis_table_weighted=axis_w,
        link_table_weighted=link_w,
        metadata={"explained_variance_weighting": "on"},
    )


def load_workbench_centered_pair(output_dir: Path | str, feature_names: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    return (
        load_centered_a_features(output_dir, feature_names),
        load_centered_b_features(output_dir, feature_names),
    )


def trace_matches_core_on_loaded_data(
    output_dir: Path | str,
) -> dict[str, np.ndarray]:
    """Verify workbench trace arrays match core for the same centered inputs."""
    from layer3_jcvpca.core import compute_jcvpca

    pca_a = load_pca_a_state(output_dir)
    centered_a, centered_b = load_workbench_centered_pair(output_dir, pca_a.feature_names)
    raw_a, raw_b = _load_raw_pair(output_dir, pca_a.feature_names)
    core = compute_jcvpca(
        raw_a,
        raw_b,
        pca_a.feature_names,
        selected_m=pca_a.selected_m,
    )
    proj = project_b_into_a_space(centered_b, centered_a, pca_a)
    pca_b = fit_pca_on_projected_b(proj.B_projected, pca_a.selected_m, pca_a.feature_names)
    rex = reexpress_b_loadings(pca_a, pca_b)
    return {
        "core_jcvpca_axis": core["jcvpca_axis"],
        "trace_jcvpca_axis": rex.B_abs_loadings - rex.A_abs_loadings,
        "core_A_abs": core["A_abs_loadings"],
        "trace_A_abs": rex.A_abs_loadings,
        "core_B_abs": core["B_abs_loadings"],
        "trace_B_abs": rex.B_abs_loadings,
    }


def _load_raw_pair(output_dir: Path | str, feature_names: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    from layer3_jcvpca.workbench_reporting import load_loaded_datasets

    a, b = load_loaded_datasets(output_dir)
    return a, b
