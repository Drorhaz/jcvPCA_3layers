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
    return plot_cumulative_variance_with_threshold(evr, title=title)


def plot_cumulative_variance_with_threshold(
    evr: np.ndarray,
    *,
    threshold: float = 0.80,
    title: str = "Cumulative variance (Dataset A)",
) -> Figure:
    fig, ax = plt.subplots(figsize=(6, 4))
    cum = np.cumsum(evr)
    ax.plot(range(1, len(cum) + 1), cum, "o-", color="darkgreen")
    ax.axhline(threshold, color="gray", linestyle="--", label=f"{threshold:.0%}")
    ax.set_title(title)
    ax.set_xlabel("PC")
    ax.set_ylabel("Cumulative explained variance")
    ax.legend()
    return fig


def plot_pca_a_loadings_heatmap(
    loadings: np.ndarray,
    feature_names: list[str],
    *,
    title: str = "PCA A loadings heatmap",
    max_features_display: int = 40,
) -> Figure:
    fig, ax = plt.subplots(figsize=(10, max(4, loadings.shape[0] * 0.5)))
    display = loadings
    labels = feature_names
    if len(feature_names) > max_features_display:
        idx = np.argsort(-np.abs(loadings).max(axis=0))[:max_features_display]
        display = loadings[:, idx]
        labels = [feature_names[i] for i in idx]
    im = ax.imshow(display, aspect="auto", cmap="RdBu_r")
    ax.set_yticks(range(display.shape[0]))
    ax.set_yticklabels([f"PC{i + 1}" for i in range(display.shape[0])])
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=90, fontsize=7)
    ax.set_title(title)
    fig.colorbar(im, ax=ax, shrink=0.85)
    return fig


def _pc_trajectory_scores(A_df, B_df, feature_names, selected_m: int):
    A_c = A_df[feature_names] - A_df[feature_names].mean()
    B_c = B_df[feature_names] - B_df[feature_names].mean()
    pca = PCA(n_components=selected_m).fit(A_c)
    A_scores = np.matmul(A_c.to_numpy(), pca.components_.T)
    B_scores = np.matmul(B_c.to_numpy(), pca.components_.T)
    return A_scores, B_scores, pca.explained_variance_ratio_


def _pc_axis_label(pc_index: int, evr: np.ndarray) -> str:
    ev_pct = evr[pc_index] * 100
    cum_pct = float(np.cumsum(evr)[pc_index]) * 100
    return f"PC{pc_index + 1} ({ev_pct:.1f}% var, cum. {cum_pct:.1f}%)"


def _pc_trajectory_title(evr: np.ndarray, n_axes: int) -> str:
    cum_pct = float(np.cumsum(evr)[n_axes - 1]) * 100
    axes_label = ", ".join(f"PC{i + 1}" for i in range(n_axes))
    return (
        f"PC trajectory ({axes_label}) — "
        f"first {n_axes} PCs explain {cum_pct:.1f}% of A/reference variance"
    )


def plot_pc_trajectories(A_df, B_df, feature_names, selected_m: int) -> Figure:
    A_scores, B_scores, evr = _pc_trajectory_scores(A_df, B_df, feature_names, selected_m)
    fig, ax = plt.subplots(figsize=(7, 5))
    y_idx = 1 if selected_m > 1 else 0
    ax.plot(A_scores[:, 0], A_scores[:, y_idx], alpha=0.35, linewidth=0.6, label="A (reference)")
    ax.plot(B_scores[:, 0], B_scores[:, y_idx], alpha=0.35, linewidth=0.6, label="B (comparison)")
    ax.set_xlabel(_pc_axis_label(0, evr))
    ax.set_ylabel(_pc_axis_label(y_idx, evr))
    ax.set_title(_pc_trajectory_title(evr, 2 if selected_m > 1 else 1))
    ax.legend(loc="upper right")
    return fig


def plot_pc_trajectories_3d(A_df, B_df, feature_names, selected_m: int) -> Figure | None:
    if selected_m < 3:
        return None
    A_scores, B_scores, evr = _pc_trajectory_scores(A_df, B_df, feature_names, selected_m)
    fig = plt.figure(figsize=(8, 6))
    ax = fig.add_subplot(111, projection="3d")
    ax.plot(
        A_scores[:, 0],
        A_scores[:, 1],
        A_scores[:, 2],
        alpha=0.25,
        linewidth=0.5,
        color="tab:blue",
        label="A (reference)",
    )
    ax.plot(
        B_scores[:, 0],
        B_scores[:, 1],
        B_scores[:, 2],
        alpha=0.25,
        linewidth=0.5,
        color="tab:orange",
        label="B (comparison)",
    )
    ax.set_xlabel(_pc_axis_label(0, evr), labelpad=8)
    ax.set_ylabel(_pc_axis_label(1, evr), labelpad=8)
    ax.set_zlabel(_pc_axis_label(2, evr), labelpad=8)
    ax.set_title(_pc_trajectory_title(evr, 3), pad=12)
    ax.view_init(elev=22, azim=-58)
    ax.legend(loc="upper left")
    return fig


def _n_pcs_for_cumulative_variance(evr: np.ndarray, threshold: float = 0.80) -> int:
    cum = np.cumsum(evr)
    idx = int(np.searchsorted(cum, threshold))
    return min(idx + 1, len(evr))


def plot_pc_trajectories_multidim(
    A_df,
    B_df,
    feature_names,
    variance_threshold: float = 0.80,
) -> Figure | None:
    """Successive 2D trajectory panels (PC1–PC2, PC3–PC4, …) up to *variance_threshold*."""
    A_c = A_df[feature_names] - A_df[feature_names].mean()
    B_c = B_df[feature_names] - B_df[feature_names].mean()
    n_fit = min(len(feature_names), len(A_c))
    if n_fit < 2:
        return None
    pca = PCA(n_components=n_fit).fit(A_c)
    evr = pca.explained_variance_ratio_
    n_show = _n_pcs_for_cumulative_variance(evr, variance_threshold)
    if n_show % 2 == 1:
        n_show = min(n_show + 1, n_fit)
    if n_show < 2:
        return None

    A_scores = np.matmul(A_c.to_numpy(), pca.components_[:n_show].T)
    B_scores = np.matmul(B_c.to_numpy(), pca.components_[:n_show].T)
    pairs = [(i, i + 1) for i in range(0, n_show, 2)]
    cum_pct = float(np.cumsum(evr)[n_show - 1]) * 100

    fig, axes = plt.subplots(
        len(pairs),
        1,
        figsize=(7, 3.8 * len(pairs)),
        squeeze=False,
    )
    for row, (x_idx, y_idx) in enumerate(pairs):
        ax = axes[row, 0]
        ax.plot(
            A_scores[:, x_idx],
            A_scores[:, y_idx],
            alpha=0.3,
            linewidth=0.5,
            color="tab:blue",
            label="A (reference)" if row == 0 else None,
        )
        ax.plot(
            B_scores[:, x_idx],
            B_scores[:, y_idx],
            alpha=0.3,
            linewidth=0.5,
            color="tab:orange",
            label="B (comparison)" if row == 0 else None,
        )
        ax.set_xlabel(_pc_axis_label(x_idx, evr))
        ax.set_ylabel(_pc_axis_label(y_idx, evr))
        pair_cum = float(np.cumsum(evr)[y_idx]) * 100
        ax.set_title(f"PC{x_idx + 1} vs PC{y_idx + 1} (cumulative through PC{y_idx + 1}: {pair_cum:.1f}%)")
    fig.suptitle(
        f"PC trajectories in successive 2D subspaces — "
        f"PCs 1–{n_show} explain {cum_pct:.1f}% of A/reference variance",
        y=1.01,
        fontsize=11,
    )
    if len(pairs):
        axes[0, 0].legend(loc="upper right")
    return fig


def plot_pc_score_heatmap(
    A_df,
    B_df,
    feature_names,
    variance_threshold: float = 0.80,
    max_frames: int = 500,
) -> Figure | None:
    """Frame × PC heatmaps for A and B, covering PCs up to *variance_threshold*."""
    A_c = A_df[feature_names] - A_df[feature_names].mean()
    B_c = B_df[feature_names] - B_df[feature_names].mean()
    n_fit = min(len(feature_names), len(A_c))
    if n_fit < 2:
        return None
    pca = PCA(n_components=n_fit).fit(A_c)
    evr = pca.explained_variance_ratio_
    n_show = _n_pcs_for_cumulative_variance(evr, variance_threshold)
    cum_pct = float(np.cumsum(evr)[n_show - 1]) * 100

    A_scores = np.matmul(A_c.to_numpy(), pca.components_[:n_show].T)
    B_scores = np.matmul(B_c.to_numpy(), pca.components_[:n_show].T)

    def _downsample(scores: np.ndarray) -> np.ndarray:
        n = len(scores)
        if n <= max_frames:
            return scores[:, :n_show].T
        idx = np.linspace(0, n - 1, max_frames, dtype=int)
        return scores[idx, :n_show].T

    A_grid = _downsample(A_scores)
    B_grid = _downsample(B_scores)
    vmax = max(np.abs(A_grid).max(), np.abs(B_grid).max(), 1e-9)

    pc_labels = [f"PC{i + 1}\n({evr[i] * 100:.1f}%)" for i in range(n_show)]
    fig, axes = plt.subplots(2, 1, figsize=(10, 4.5), sharex=True)
    for ax, grid, label in zip(axes, (A_grid, B_grid), ("A (reference)", "B (comparison)")):
        im = ax.imshow(
            grid,
            aspect="auto",
            cmap="RdBu_r",
            vmin=-vmax,
            vmax=vmax,
            interpolation="nearest",
        )
        ax.set_yticks(range(n_show))
        ax.set_yticklabels(pc_labels, fontsize=8)
        ax.set_ylabel(label)

    # Annotate the clearest A-vs-B contrast: early-window PC3 activation in A.
    if n_show >= 3:
        pc3_row = 2
        early_end = min(80, A_grid.shape[1] - 1)
        axes[0].annotate(
            "",
            xy=(early_end * 0.5, pc3_row),
            xytext=(early_end + 45, pc3_row + 1.35),
            fontsize=8,
            color="0.15",
            arrowprops=dict(arrowstyle="->", color="0.15", lw=1.2),
        )
        axes[0].text(
            early_end + 46,
            pc3_row + 1.35,
            "Strong early PC3\nin A (reference)",
            fontsize=8,
            va="center",
            color="0.15",
        )
        axes[0].plot(
            [0, early_end, early_end, 0, 0],
            [pc3_row - 0.45, pc3_row - 0.45, pc3_row + 0.45, pc3_row + 0.45, pc3_row - 0.45],
            color="0.15",
            lw=1.2,
            ls="--",
        )
        axes[1].annotate(
            "",
            xy=(early_end * 0.5, pc3_row),
            xytext=(early_end + 45, pc3_row - 1.1),
            fontsize=8,
            color="0.15",
            arrowprops=dict(arrowstyle="->", color="0.15", lw=1.2),
        )
        axes[1].text(
            early_end + 46,
            pc3_row - 1.1,
            "Weaker / absent\nin B (comparison)",
            fontsize=8,
            va="center",
            color="0.15",
        )

    axes[-1].set_xlabel("Frame index (downsampled)")
    fig.suptitle(
        f"PC score heatmaps — PCs 1–{n_show} explain {cum_pct:.1f}% of A/reference variance",
        y=1.02,
        fontsize=11,
    )
    fig.colorbar(im, ax=axes, label="PC score", shrink=0.85, pad=0.02)
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


def plot_pc_scores_a_vs_b(
    A_scores: np.ndarray,
    B_projected: np.ndarray,
    *,
    max_points: int = 500,
    title: str = "PC scores: A vs projected B",
) -> Figure:
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    n_a = min(len(A_scores), max_points)
    n_b = min(len(B_projected), max_points)
    if A_scores.shape[1] >= 1:
        axes[0].scatter(A_scores[:n_a, 0], A_scores[:n_a, 1] if A_scores.shape[1] > 1 else A_scores[:n_a, 0], s=8, alpha=0.5)
        axes[0].set_title("Dataset A scores")
        axes[0].set_xlabel("PC1")
        axes[0].set_ylabel("PC2" if A_scores.shape[1] > 1 else "PC1")
    if B_projected.shape[1] >= 1:
        axes[1].scatter(
            B_projected[:n_b, 0],
            B_projected[:n_b, 1] if B_projected.shape[1] > 1 else B_projected[:n_b, 0],
            s=8,
            alpha=0.5,
            color="darkorange",
        )
        axes[1].set_title("Projected B scores")
        axes[1].set_xlabel("PC1")
        axes[1].set_ylabel("PC2" if B_projected.shape[1] > 1 else "PC1")
    fig.suptitle(title)
    return fig


def plot_workbench_pc_score_summary_heatmap(
    A_scores: np.ndarray,
    B_projected: np.ndarray,
    *,
    max_pcs: int = 10,
    title: str = "PC score heatmap (mean abs)",
) -> Figure:
    k = min(max_pcs, A_scores.shape[1], B_projected.shape[1])
    data = np.vstack(
        [
            np.mean(np.abs(A_scores[:, :k]), axis=0),
            np.mean(np.abs(B_projected[:, :k]), axis=0),
        ]
    )
    fig, ax = plt.subplots(figsize=(8, 3))
    im = ax.imshow(data, aspect="auto", cmap="viridis")
    ax.set_yticks([0, 1])
    ax.set_yticklabels(["A", "B projected"])
    ax.set_xticks(range(k))
    ax.set_xticklabels([f"PC{i + 1}" for i in range(k)])
    ax.set_title(title)
    fig.colorbar(im, ax=ax, shrink=0.8)
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
        selected_m = main_result["selected_m"]
        _save(
            plot_pc_trajectories(loaded["A"].df, loaded["B"].df, feature_names, selected_m),
            plots_dir / "pc_trajectory_A_B.png",
        )
        traj_3d = plot_pc_trajectories_3d(loaded["A"].df, loaded["B"].df, feature_names, selected_m)
        if traj_3d is not None:
            _save(traj_3d, plots_dir / "pc_trajectory_A_B_3d.png")
        traj_multi = plot_pc_trajectories_multidim(loaded["A"].df, loaded["B"].df, feature_names)
        if traj_multi is not None:
            _save(traj_multi, plots_dir / "pc_trajectory_A_B_multipc.png")
        score_hm = plot_pc_score_heatmap(loaded["A"].df, loaded["B"].df, feature_names)
        if score_hm is not None:
            _save(score_hm, plots_dir / "pc_score_heatmap_A_B.png")

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
