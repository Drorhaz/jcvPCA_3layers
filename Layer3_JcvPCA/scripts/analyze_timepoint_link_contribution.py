#!/usr/bin/env python3
"""Timepoint-level link contribution distribution from Gaga JcvPCA batch outputs."""

from __future__ import annotations

import argparse
import importlib.util
import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA

BLOCK_ID_TO_LABEL = {
    "A": "all_P1_P2_P3_P4_P5",
    "B": "P3_P4_P5",
}
TIMEPOINTS = ("T1", "T2", "T3")
P_LINK_FLOOR_FLAG = 0.02
ENTROPY_EVEN_THRESHOLD = 0.02
GINI_EVEN_THRESHOLD = 0.02
TOP3_EVEN_THRESHOLD = 0.03
LINKS80_EVEN_THRESHOLD = 1


def _load_distribution_helpers():
    script_dir = Path(__file__).resolve().parent
    module_path = script_dir / "analyze_link_contribution_distribution.py"
    spec = importlib.util.spec_from_file_location("link_dist", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load helpers from {module_path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["link_dist"] = mod
    spec.loader.exec_module(mod)
    return mod


def _save_fig(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def timepoint_dataset_paths(batch_root: Path, participant_id: str, block_id: str) -> dict[str, Path]:
    base = batch_root / "comparisons"
    comp_t12 = base / f"{participant_id}_{block_id}_L1_T1_vs_T2" / "run"
    comp_t13 = base / f"{participant_id}_{block_id}_L2_T1_vs_T3" / "run"
    return {
        "T1": comp_t12 / "_loaded_dataset_A.parquet",
        "T2": comp_t12 / "_loaded_dataset_B.parquet",
        "T3": comp_t13 / "_loaded_dataset_B.parquet",
    }


def feature_columns_for_comparison(batch_root: Path, participant_id: str, block_id: str) -> tuple[list[str], list[str]]:
    cols_path = (
        batch_root
        / "comparisons"
        / f"{participant_id}_{block_id}_L1_T1_vs_T2"
        / "construction"
        / "dataset_feature_columns.csv"
    )
    feat_df = pd.read_csv(cols_path)
    pca_cols = feat_df.loc[feat_df["included_in_pca"] == True, "column_name"].astype(str).tolist()
    link_stems = (
        feat_df.loc[feat_df["column_role"] == "pca_feature", "link_stem"].astype(str).drop_duplicates().tolist()
    )
    return pca_cols, link_stems


def link_contributions_from_state(
    df: pd.DataFrame,
    pca_cols: list[str],
    link_stems: list[str],
    *,
    variance_threshold: float = 0.80,
) -> tuple[dict[str, float], int]:
    """PCA loading RSS per link on independently centered state matrix."""
    x = df[pca_cols].to_numpy(dtype=float)
    x = x - x.mean(axis=0)
    if x.shape[0] < 2:
        raise ValueError("Timepoint state has fewer than 2 rows.")

    pca = PCA()
    pca.fit(x)
    cum = np.cumsum(pca.explained_variance_ratio_)
    selected_m = int(np.searchsorted(cum, variance_threshold) + 1)
    selected_m = max(2, min(selected_m, len(cum)))

    col_index = {c: i for i, c in enumerate(pca_cols)}
    contributions: dict[str, float] = {}
    for stem in link_stems:
        idxs = [col_index[f"{stem}_{axis}"] for axis in ("rx", "ry", "rz")]
        total = 0.0
        for pc in range(selected_m):
            vals = pca.components_[pc, idxs]
            total += float(np.sqrt(np.sum(vals**2)))
        contributions[stem] = total
    return contributions, selected_m


def distribution_label(normalized_entropy: float, gini: float, top_3_share: float) -> str:
    if normalized_entropy >= 0.92 and gini <= 0.38 and top_3_share <= 0.42:
        return "more_evenly_distributed_link_contribution"
    if normalized_entropy <= 0.88 or gini >= 0.42 or top_3_share >= 0.48:
        return "more_concentrated_link_contribution"
    return "mid_range_link_contribution"


def trend_label(row: pd.Series) -> str:
    def votes_t2_vs_t1() -> tuple[int, int]:
        even = 0
        concentrated = 0
        if row["delta_entropy_T2_minus_T1"] >= ENTROPY_EVEN_THRESHOLD:
            even += 1
        elif row["delta_entropy_T2_minus_T1"] <= -ENTROPY_EVEN_THRESHOLD:
            concentrated += 1
        if row["delta_Gini_T2_minus_T1"] <= -GINI_EVEN_THRESHOLD:
            even += 1
        elif row["delta_Gini_T2_minus_T1"] >= GINI_EVEN_THRESHOLD:
            concentrated += 1
        if row["delta_top3_T2_minus_T1"] <= -TOP3_EVEN_THRESHOLD:
            even += 1
        elif row["delta_top3_T2_minus_T1"] >= TOP3_EVEN_THRESHOLD:
            concentrated += 1
        return even, concentrated

    def votes_t3_vs_t1() -> tuple[int, int]:
        even = 0
        concentrated = 0
        if row["delta_entropy_T3_minus_T1"] >= ENTROPY_EVEN_THRESHOLD:
            even += 1
        elif row["delta_entropy_T3_minus_T1"] <= -ENTROPY_EVEN_THRESHOLD:
            concentrated += 1
        if row["delta_Gini_T3_minus_T1"] <= -GINI_EVEN_THRESHOLD:
            even += 1
        elif row["delta_Gini_T3_minus_T1"] >= GINI_EVEN_THRESHOLD:
            concentrated += 1
        if row["delta_top3_T3_minus_T1"] <= -TOP3_EVEN_THRESHOLD:
            even += 1
        elif row["delta_top3_T3_minus_T1"] >= TOP3_EVEN_THRESHOLD:
            concentrated += 1
        return even, concentrated

    e2, c2 = votes_t2_vs_t1()
    e3, c3 = votes_t3_vs_t1()

    labels: list[str] = []
    if e2 >= 2 and c2 == 0:
        labels.append("more_evenly_distributed_at_T2")
    elif c2 >= 2 and e2 == 0:
        labels.append("more_concentrated_at_T2")
    if e3 >= 2 and c3 == 0:
        labels.append("more_evenly_distributed_at_T3")
    elif c3 >= 2 and c3 == 0:
        labels.append("more_concentrated_at_T3")

    if len(labels) == 1:
        return labels[0]
    if len(labels) > 1:
        return "mixed_pattern"
    if max(abs(row["delta_entropy_T2_minus_T1"]), abs(row["delta_entropy_T3_minus_T1"])) < ENTROPY_EVEN_THRESHOLD:
        return "no_clear_direction"
    return "mixed_pattern"


def compute_timepoint_tables(batch_root: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    helpers = _load_distribution_helpers()
    gini_coefficient = helpers.gini_coefficient
    entropy_from_probs = helpers.entropy_from_probs
    links_to_cover = helpers.links_to_cover
    top_k_share = helpers.top_k_share

    dist_rows: list[dict] = []
    summary_rows: list[dict] = []
    low_rows: list[dict] = []

    status_path = batch_root / "comparison_status.csv"
    if status_path.is_file():
        participants = sorted(pd.read_csv(status_path)["participant_id"].astype(str).unique().tolist())
    else:
        participants = sorted(
            {
                p.name.split("_")[0]
                for p in (batch_root / "comparisons").iterdir()
                if p.is_dir()
            }
        )
    for participant_id in participants:
        for block_id, block_label in BLOCK_ID_TO_LABEL.items():
            paths = timepoint_dataset_paths(batch_root, participant_id, block_id)
            pca_cols, link_stems = feature_columns_for_comparison(batch_root, participant_id, block_id)

            for timepoint in TIMEPOINTS:
                path = paths[timepoint]
                if not path.is_file():
                    continue
                df = pd.read_parquet(path)
                contribs, selected_m = link_contributions_from_state(df, pca_cols, link_stems)
                values = np.array([contribs[s] for s in link_stems], dtype=float)
                total = float(values.sum())
                if total <= 0:
                    continue
                p_links = values / total
                p25 = float(np.quantile(p_links, 0.25))

                ent = entropy_from_probs(p_links)
                n_links = len(link_stems)
                norm_ent = ent / math.log(n_links) if n_links > 1 else 0.0
                gini = gini_coefficient(values)
                sorted_probs = np.sort(p_links)[::-1]
                cum_share = np.cumsum(sorted_probs)

                summary = {
                    "participant_id": participant_id,
                    "block_id": block_id,
                    "block_label": block_label,
                    "timepoint": timepoint,
                    "n_links": n_links,
                    "n_rows": len(df),
                    "selected_m": selected_m,
                    "total_link_contribution": total,
                    "normalized_entropy": norm_ent,
                    "gini_concentration": gini,
                    "top_1_share": top_k_share(p_links, 1),
                    "top_3_share": top_k_share(p_links, 3),
                    "top_5_share": top_k_share(p_links, 5),
                    "links_for_50pct": links_to_cover(cum_share, 0.50),
                    "links_for_80pct": links_to_cover(cum_share, 0.80),
                    "p_link_p25_threshold": p25,
                    "distribution_label": distribution_label(norm_ent, gini, top_k_share(p_links, 3)),
                }
                summary_rows.append(summary)

                order = np.argsort(values)[::-1]
                ranks = np.empty_like(order)
                ranks[order] = np.arange(1, len(order) + 1)
                for i, stem in enumerate(link_stems):
                    p_link = float(p_links[i])
                    below_p25 = p_link < p25
                    below_p02 = p_link < P_LINK_FLOOR_FLAG
                    low = below_p25 or below_p02
                    dist_rows.append(
                        {
                            **summary,
                            "link_id": stem,
                            "link_contribution": float(values[i]),
                            "p_link": p_link,
                            "rank_by_contribution": int(ranks[i]),
                            "below_p25": bool(below_p25),
                            "below_p02": bool(below_p02),
                            "low_relative_contribution": bool(low),
                        }
                    )
                    if low:
                        low_rows.append(
                            {
                                "participant_id": participant_id,
                                "block_label": block_label,
                                "timepoint": timepoint,
                                "link_id": stem,
                                "link_contribution": float(values[i]),
                                "p_link": p_link,
                                "below_p25": bool(below_p25),
                                "below_p02": bool(below_p02),
                                "p_link_p25_threshold": p25,
                            }
                        )

    summary_df = pd.DataFrame(summary_rows)
    trend_rows: list[dict] = []
    for (participant_id, block_label), grp in summary_df.groupby(["participant_id", "block_label"], sort=True):
        by_tp = {r.timepoint: r for _, r in grp.iterrows()}
        if not all(tp in by_tp for tp in TIMEPOINTS):
            continue
        row = {
            "participant_id": participant_id,
            "block_label": block_label,
            "entropy_T1": by_tp["T1"].normalized_entropy,
            "entropy_T2": by_tp["T2"].normalized_entropy,
            "entropy_T3": by_tp["T3"].normalized_entropy,
            "delta_entropy_T2_minus_T1": by_tp["T2"].normalized_entropy - by_tp["T1"].normalized_entropy,
            "delta_entropy_T3_minus_T1": by_tp["T3"].normalized_entropy - by_tp["T1"].normalized_entropy,
            "Gini_T1": by_tp["T1"].gini_concentration,
            "Gini_T2": by_tp["T2"].gini_concentration,
            "Gini_T3": by_tp["T3"].gini_concentration,
            "delta_Gini_T2_minus_T1": by_tp["T2"].gini_concentration - by_tp["T1"].gini_concentration,
            "delta_Gini_T3_minus_T1": by_tp["T3"].gini_concentration - by_tp["T1"].gini_concentration,
            "top3_T1": by_tp["T1"].top_3_share,
            "top3_T2": by_tp["T2"].top_3_share,
            "top3_T3": by_tp["T3"].top_3_share,
            "delta_top3_T2_minus_T1": by_tp["T2"].top_3_share - by_tp["T1"].top_3_share,
            "delta_top3_T3_minus_T1": by_tp["T3"].top_3_share - by_tp["T1"].top_3_share,
            "links80_T1": by_tp["T1"].links_for_80pct,
            "links80_T2": by_tp["T2"].links_for_80pct,
            "links80_T3": by_tp["T3"].links_for_80pct,
        }
        row["trend_label"] = trend_label(pd.Series(row))
        trend_rows.append(row)

    return (
        pd.DataFrame(dist_rows),
        summary_df,
        pd.DataFrame(trend_rows),
        pd.DataFrame(low_rows),
    )


def build_comparison_to_delta_analysis(batch_root: Path, timepoint_summary: pd.DataFrame) -> pd.DataFrame:
    delta_path = batch_root / "contribution_evenness_summary.csv"
    if not delta_path.is_file():
        return pd.DataFrame()
    delta = pd.read_csv(delta_path)
    delta = delta[delta["focus_mode"] == "all"].copy()

    comp_map = {
        "T1_vs_T2": ("T1", "T2"),
        "T1_vs_T3": ("T1", "T3"),
        "T1_R1_vs_T1_R2": ("T1", "T1"),
        "T2_R1_vs_T2_R2": ("T2", "T2"),
        "T3_R1_vs_T3_R2": ("T3", "T3"),
    }
    rows: list[dict] = []
    for _, drow in delta.iterrows():
        comparison = str(drow["comparison_label"])
        tp_ref = comp_map.get(comparison)
        if tp_ref is None:
            continue
        tp_a, tp_b = tp_ref
        for tp in {tp_a, tp_b}:
            trow = timepoint_summary[
                (timepoint_summary["participant_id"].astype(str) == str(drow["participant_id"]))
                & (timepoint_summary["block_label"] == drow["block_label"])
                & (timepoint_summary["timepoint"] == tp)
            ]
            if trow.empty:
                continue
            t = trow.iloc[0]
            rows.append(
                {
                    "participant_id": drow["participant_id"],
                    "block_label": drow["block_label"],
                    "comparison_label": comparison,
                    "comparison_type": "longitudinal"
                    if comparison in {"T1_vs_T2", "T1_vs_T3"}
                    else "repetition",
                    "timepoint_state": tp,
                    "timepoint_normalized_entropy": t["normalized_entropy"],
                    "timepoint_gini": t["gini_concentration"],
                    "timepoint_top_3_share": t["top_3_share"],
                    "delta_normalized_entropy": drow["normalized_entropy"],
                    "delta_gini": drow["gini_concentration"],
                    "delta_top_3_share": drow["top_3_share"],
                    "note": (
                        "Timepoint-state evenness describes within-timepoint PCA loading spread; "
                        "comparison evenness describes abs(JcvPCA_link) spread for the named comparison."
                    ),
                }
            )
    return pd.DataFrame(rows)


def write_timepoint_plots(
    batch_root: Path,
    distribution: pd.DataFrame,
    summary: pd.DataFrame,
    trends: pd.DataFrame,
) -> None:
    trend_dir = batch_root / "plots" / "timepoint_evenness_trends"
    dist_dir = batch_root / "plots" / "timepoint_link_distribution"

    for _, tr in trends.iterrows():
        fig, axes = plt.subplots(1, 3, figsize=(12, 4))
        tps = ["T1", "T2", "T3"]
        sub = summary[
            (summary["participant_id"] == tr["participant_id"])
            & (summary["block_label"] == tr["block_label"])
        ].set_index("timepoint").loc[tps]
        axes[0].plot(tps, sub["normalized_entropy"], marker="o")
        axes[0].set_title("normalized_entropy")
        axes[1].plot(tps, sub["gini_concentration"], marker="o", color="darkorange")
        axes[1].set_title("Gini concentration")
        axes[2].plot(tps, sub["top_3_share"], marker="o", color="seagreen")
        axes[2].set_title("top_3_share")
        fig.suptitle(
            f"{tr['participant_id']} | {tr['block_label']} | trend={tr['trend_label']}"
        )
        _save_fig(fig, trend_dir / f"{tr['participant_id']}_{tr['block_label']}_evenness_trend.png")

    for _, row in summary.iterrows():
        sub = distribution[
            (distribution["participant_id"] == row["participant_id"])
            & (distribution["block_label"] == row["block_label"])
            & (distribution["timepoint"] == row["timepoint"])
        ].sort_values("p_link", ascending=True)
        if sub.empty:
            continue
        fig, ax = plt.subplots(figsize=(8, max(4, 0.3 * len(sub))))
        colors = ["steelblue" if not x else "lightgray" for x in sub["low_relative_contribution"]]
        ax.barh(sub["link_id"], sub["p_link"], color=colors)
        ax.set_xlabel("Relative link contribution (p_link)")
        ax.set_title(
            f"{row['participant_id']} | {row['block_label']} | {row['timepoint']} | {row['distribution_label']}"
        )
        fname = f"{row['participant_id']}_{row['block_label']}_{row['timepoint']}_p_link.png"
        _save_fig(fig, dist_dir / fname)


def run_analysis(batch_root: Path) -> dict[str, Path]:
    batch_root = Path(batch_root)
    distribution, summary, trends, low_links = compute_timepoint_tables(batch_root)
    comparison_bridge = build_comparison_to_delta_analysis(batch_root, summary)

    outputs = {
        "timepoint_link_contribution_distribution.csv": distribution,
        "timepoint_evenness_summary.csv": summary,
        "timepoint_evenness_trends.csv": trends,
        "timepoint_low_contribution_links.csv": low_links,
        "timepoint_vs_comparison_evenness.csv": comparison_bridge,
    }
    paths: dict[str, Path] = {}
    for name, frame in outputs.items():
        path = batch_root / name
        frame.to_csv(path, index=False)
        paths[name] = path

    write_timepoint_plots(batch_root, distribution, summary, trends)
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--batch-root",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "outputs"
        / "gaga_batch_jcvpca_20260626_193319",
    )
    args = parser.parse_args()
    paths = run_analysis(args.batch_root)
    print(f"Timepoint link contribution analysis complete: {args.batch_root}")
    for name in paths:
        print(f"  {name}")


if __name__ == "__main__":
    main()
