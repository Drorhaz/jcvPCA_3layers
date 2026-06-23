"""Matplotlib visualization for Layer 3 JcvPCA and matrix stability."""

from __future__ import annotations

import os

os.environ.setdefault("MPLBACKEND", "Agg")

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.figure import Figure
from sklearn.decomposition import PCA


def _save(fig: Figure, path: Path) -> None:
    fig.tight_layout()
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def plot_feature_variance(feature_var_df: pd.DataFrame, title: str = "Feature variance") -> Figure:
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.bar(range(len(feature_var_df)), feature_var_df["variance"].values, color="steelblue")
    ax.set_title(title)
    ax.set_xlabel("Feature index")
    ax.set_ylabel("Variance")
    return fig


def plot_joint_variance(joint_var_df: pd.DataFrame, title: str = "Joint/link variance") -> Figure:
    fig, ax = plt.subplots(figsize=(8, 4))
    labels = joint_var_df["canonical_link_name"].tolist()
    ax.barh(labels, joint_var_df["joint_variance"].values, color="teal")
    ax.set_title(title)
    ax.invert_yaxis()
    return fig


def plot_singular_values(sv_df: pd.DataFrame, title: str = "Singular value spectrum") -> Figure:
    fig, ax = plt.subplots(figsize=(6, 4))
    if not sv_df.empty:
        ax.plot(sv_df["index"], sv_df["singular_value"], "o-", color="purple")
    ax.set_title(title)
    ax.set_xlabel("Index")
    ax.set_ylabel("Singular value")
    return fig


def plot_scree(evr: np.ndarray, title: str = "Scree plot (A/reference)") -> Figure:
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(range(1, len(evr) + 1), evr, color="navy")
    ax.set_title(title)
    ax.set_xlabel("PC")
    ax.set_ylabel("Explained variance ratio")
    return fig


def plot_cumulative_variance(evr: np.ndarray, title: str = "Cumulative variance (A/reference)") -> Figure:
    fig, ax = plt.subplots(figsize=(6, 4))
    cum = np.cumsum(evr)
    ax.plot(range(1, len(cum) + 1), cum, "o-", color="darkgreen")
    ax.axhline(0.9, color="gray", linestyle="--", label="90%")
    ax.set_title(title)
    ax.set_xlabel("PC")
    ax.set_ylabel("Cumulative explained variance")
    ax.legend()
    return fig


def plot_pc_trajectories(A_df, B_df, feature_names, selected_m: int) -> Figure:
    A_c = A_df[feature_names] - A_df[feature_names].mean()
    B_c = B_df[feature_names] - B_df[feature_names].mean()
    pca = PCA(n_components=selected_m).fit(A_c)
    A_scores = np.matmul(A_c.to_numpy(), pca.components_.T)
    B_scores = np.matmul(B_c.to_numpy(), pca.components_.T)
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(A_scores[:, 0], A_scores[:, 1] if selected_m > 1 else A_scores[:, 0], alpha=0.5, label="A")
    ax.plot(B_scores[:, 0], B_scores[:, 1] if selected_m > 1 else B_scores[:, 0], alpha=0.5, label="B projected")
    ax.set_title("PC trajectory preview (PC1 vs PC2)")
    ax.legend()
    return fig


def plot_jrw_bars(link_df: pd.DataFrame, title: str = "JRW A vs B per link") -> Figure:
    agg = link_df.groupby("link_id").agg(JRW_A=("JRW_A_link", "mean"), JRW_B=("JRW_B_link", "mean"))
    fig, ax = plt.subplots(figsize=(8, 4))
    x = np.arange(len(agg))
    w = 0.35
    ax.bar(x - w / 2, agg["JRW_A"], w, label="A")
    ax.bar(x + w / 2, agg["JRW_B"], w, label="B")
    ax.set_xticks(x)
    ax.set_xticklabels(agg.index, rotation=45, ha="right")
    ax.set_title(title)
    ax.legend()
    return fig


def plot_delta_jrw(link_df: pd.DataFrame, title: str = "ΔJRW (JcvPCA) per link") -> Figure:
    agg = link_df.groupby("link_id")["JcvPCA_link"].mean().sort_values()
    fig, ax = plt.subplots(figsize=(8, 4))
    colors = ["orange" if v >= 0 else "gray" for v in agg.values]
    ax.barh(agg.index, agg.values, color=colors)
    ax.set_title(title)
    ax.axvline(0, color="black", linewidth=0.8)
    return fig


def plot_delta_vs_nv(main_vs_nv: pd.DataFrame) -> Figure:
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    mvn = main_vs_nv.sort_values("link_id")
    axes[0].barh(mvn["link_id"], mvn["main_abs_delta_jrw"], alpha=0.7, label="Main")
    axes[0].barh(
        mvn["link_id"],
        mvn["nv_abs_delta_jrw"],
        alpha=0.7,
        label="NV",
        left=0,
        color="green",
    )
    axes[0].set_title("Main vs NV |ΔJRW|")
    axes[0].legend()
    valid = main_vs_nv[~main_vs_nv["ratio_hidden"]]
    axes[1].scatter(valid["nv_abs_delta_jrw"], valid["main_abs_delta_jrw"], c="purple")
    mx = max(valid["nv_abs_delta_jrw"].max(), valid["main_abs_delta_jrw"].max()) if len(valid) else 1
    axes[1].plot([0, mx], [0, mx], "k--", alpha=0.5)
    axes[1].set_xlabel("NV |ΔJRW|")
    axes[1].set_ylabel("Main |ΔJRW|")
    axes[1].set_title("Main vs NV scatter")
    return fig


def plot_jrw_heatmap(axis_df: pd.DataFrame) -> Figure:
    pivot = axis_df.pivot_table(index="link_id", columns="axis", values="jcvpca_axis", aggfunc="mean")
    fig, ax = plt.subplots(figsize=(6, max(4, len(pivot) * 0.3)))
    im = ax.imshow(pivot.values, aspect="auto", cmap="RdBu_r")
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index)
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns)
    ax.set_title("Axis-level JcvPCA heatmap")
    fig.colorbar(im, ax=ax)
    return fig


def plot_democracy_curve(dist_metrics: dict) -> Figure:
    fig, ax = plt.subplots(figsize=(6, 4))
    curve = dist_metrics.get("cumulative_curve", [])
    if curve:
        ax.plot(range(1, len(curve) + 1), curve, "o-", color="brown")
    ax.set_title("Joint contribution cumulative curve (exploratory)")
    ax.set_xlabel("Ranked joint index")
    ax.set_ylabel("Cumulative share")
    return fig


def plot_motion_energy(df, feature_names) -> Figure:
    energy = np.sum(df[feature_names].to_numpy(dtype=float) ** 2, axis=1)
    fig, ax = plt.subplots(figsize=(10, 3))
    ax.plot(energy, color="crimson", linewidth=0.8)
    ax.set_title("Motion-energy timeline (exploratory)")
    ax.set_xlabel("Frame index")
    ax.set_ylabel("Sum of squared features")
    return fig


def plot_qc_timeline(manifest: dict | None) -> Figure:
    fig, ax = plt.subplots(figsize=(10, 2))
    if manifest and manifest.get("warnings"):
        for i, w in enumerate(manifest["warnings"]):
            ax.barh(0, 1, left=i, color="orange" if w.get("severity") == "strong_warning" else "gold")
        ax.set_title("QC warning flags (manifest summary)")
    else:
        ax.text(0.5, 0.5, "No QC timeline data", ha="center", va="center")
        ax.set_xlim(0, 1)
    ax.set_yticks([])
    return fig


def plot_split_half(stab) -> Figure | None:
    if stab is None or stab.split_half_table is None or stab.split_half_table.empty:
        return None
    row = stab.split_half_table.iloc[0]
    if not row.get("split_half_available"):
        return None
    fig, ax = plt.subplots(figsize=(4, 3))
    ax.bar(["PC similarity"], [row.get("split_half_pc_similarity", 0)], color="slateblue")
    ax.set_ylim(0, 1)
    ax.set_title("Split-half PCA stability (exploratory)")
    return fig


def save_analysis_plots(
    plots_dir: Path,
    *,
    preflight,
    main_result: dict,
    nv_result: dict,
    tables: dict,
    distribution_metrics: dict,
    feature_names: list[str],
) -> None:
    plots_dir = Path(plots_dir)
    stab_a = preflight.stability.get("A")
    if stab_a:
        if stab_a.feature_variance_table is not None:
            _save(plot_feature_variance(stab_a.feature_variance_table, "A/reference feature variance"), plots_dir / "feature_variance_bar.png")
        if stab_a.joint_variance_table is not None:
            _save(plot_joint_variance(stab_a.joint_variance_table, "A/reference joint variance"), plots_dir / "joint_variance_bar.png")
        if stab_a.singular_value_table is not None:
            _save(plot_singular_values(stab_a.singular_value_table), plots_dir / "singular_value_spectrum.png")
        loaded = {w.role: w for w in preflight.windows}
        if "A" in loaded:
            _save(plot_motion_energy(loaded["A"].df, feature_names), plots_dir / "motion_energy_timeline.png")
            _save(plot_qc_timeline(loaded["A"].manifest), plots_dir / "qc_flag_timeline.png")
        sh_fig = plot_split_half(stab_a)
        if sh_fig:
            _save(sh_fig, plots_dir / "split_half_pca_similarity.png")

    evr = main_result.get("pca_A_variance_ratio", np.array([]))
    if len(evr):
        _save(plot_scree(evr), plots_dir / "scree_plot.png")
        _save(plot_cumulative_variance(evr), plots_dir / "cumulative_variance.png")

    loaded = {w.role: w for w in preflight.windows}
    if "A" in loaded and "B" in loaded:
        _save(
            plot_pc_trajectories(loaded["A"].df, loaded["B"].df, feature_names, main_result["selected_m"]),
            plots_dir / "pc_trajectory_A_B.png",
        )

    link_df = tables.get("jrw_joint_table.csv")
    if link_df is None:
        link_df = tables.get("jrw_joint")
    if link_df is not None:
        _save(plot_jrw_bars(link_df), plots_dir / "jrw_A_B_bar.png")
        _save(plot_delta_jrw(link_df), plots_dir / "delta_jrw_bar.png")

    mvn = tables.get("main_vs_nv_comparison_table.csv")
    if mvn is None:
        mvn = tables.get("main_vs_nv")
    if mvn is not None:
        _save(plot_delta_vs_nv(mvn), plots_dir / "delta_jrw_vs_nv.png")

    axis_df = tables.get("jrw_feature_table.csv")
    if axis_df is None:
        axis_df = tables.get("jrw_feature")
    if axis_df is not None and "axis" in axis_df.columns:
        _save(plot_jrw_heatmap(axis_df), plots_dir / "jrw_heatmap_joint_axis.png")

    if distribution_metrics:
        _save(plot_democracy_curve(distribution_metrics), plots_dir / "jrw_democracy_curve.png")
