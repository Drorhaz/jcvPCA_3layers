#!/usr/bin/env python3
"""Descriptive link contribution distribution analysis for Gaga JcvPCA batch outputs."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

GROUP_COLS = ["participant_id", "block_label", "comparison_label", "focus_mode"]
LINK_GROUP_COLS = GROUP_COLS + ["link_id"]
P_LINK_FLOOR_FLAG = 0.02


def gini_coefficient(values: np.ndarray) -> float:
    x = np.sort(np.asarray(values, dtype=float))
    x = x[x >= 0]
    if x.size == 0:
        return float("nan")
    if np.allclose(x, 0):
        return 0.0
    n = x.size
    index = np.arange(1, n + 1)
    return float((2 * np.sum(index * x) / (n * np.sum(x))) - (n + 1) / n)


def entropy_from_probs(probs: np.ndarray) -> float:
    p = probs[probs > 0]
    if p.size == 0:
        return 0.0
    return float(-np.sum(p * np.log(p)))


def links_to_cover(cum_share: np.ndarray, threshold: float) -> int:
    if cum_share.size == 0:
        return 0
    hit = np.where(cum_share >= threshold)[0]
    return int(hit[0] + 1) if hit.size else int(cum_share.size)


def top_k_share(probs: np.ndarray, k: int) -> float:
    if probs.size == 0:
        return float("nan")
    sorted_probs = np.sort(probs)[::-1]
    return float(sorted_probs[: min(k, sorted_probs.size)].sum())


def load_combined_link_results(batch_root: Path) -> pd.DataFrame:
    main_path = batch_root / "jcvpca_link_results.csv"
    focus_path = batch_root / "jcvpca_link_results_by_pc_focus.csv"
    if not main_path.is_file():
        raise FileNotFoundError(f"Missing {main_path}")
    if not focus_path.is_file():
        raise FileNotFoundError(f"Missing {focus_path}")
    main = pd.read_csv(main_path)
    focus = pd.read_csv(focus_path)
    combined = pd.concat([main, focus], ignore_index=True)
    combined["participant_id"] = combined["participant_id"].astype(str)
    combined["focus_mode"] = combined["focus_mode"].astype(str)
    return combined


def aggregate_link_abs_delta(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    work["abs_delta"] = work["JcvPCA_link"].abs()
    agg = (
        work.groupby(LINK_GROUP_COLS, as_index=False)
        .agg(
            abs_delta=("abs_delta", "mean"),
            delta_mean=("JcvPCA_link", "mean"),
            n_pc_rows=("pc", "count"),
        )
    )
    return agg


def compute_distribution_tables(link_abs: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    dist_rows: list[dict] = []
    low_rows: list[dict] = []
    summary_rows: list[dict] = []

    for keys, group in link_abs.groupby(GROUP_COLS, sort=True):
        participant_id, block_label, comparison_label, focus_mode = keys
        g = group.sort_values("abs_delta", ascending=False).copy()
        total = float(g["abs_delta"].sum())
        n_links = int(len(g))
        if total <= 0 or n_links == 0:
            continue

        g["p_link"] = g["abs_delta"] / total
        p25 = float(g["p_link"].quantile(0.25))
        g["below_p25"] = g["p_link"] < p25
        g["below_p02"] = g["p_link"] < P_LINK_FLOOR_FLAG
        g["low_relative_contribution"] = g["below_p25"] | g["below_p02"]

        probs = g["p_link"].to_numpy()
        ent = entropy_from_probs(probs)
        norm_ent = ent / math.log(n_links) if n_links > 1 else 0.0
        gini = gini_coefficient(g["abs_delta"].to_numpy())
        sorted_probs = np.sort(probs)[::-1]
        cum_share = np.cumsum(sorted_probs)

        summary_rows.append(
            {
                "participant_id": participant_id,
                "block_label": block_label,
                "comparison_label": comparison_label,
                "focus_mode": focus_mode,
                "n_links": n_links,
                "total_abs_delta": total,
                "top_1_share": top_k_share(probs, 1),
                "top_3_share": top_k_share(probs, 3),
                "top_5_share": top_k_share(probs, 5),
                "entropy": ent,
                "normalized_entropy": norm_ent,
                "gini_concentration": gini,
                "links_for_50pct": links_to_cover(cum_share, 0.50),
                "links_for_80pct": links_to_cover(cum_share, 0.80),
                "p_link_p25_threshold": p25,
                "n_low_relative_contribution": int(g["low_relative_contribution"].sum()),
            }
        )

        g["rank_by_abs_delta"] = g["p_link"].rank(ascending=False, method="first").astype(int)

        for _, row in g.iterrows():
            dist_rows.append(
                {
                    "participant_id": participant_id,
                    "block_label": block_label,
                    "comparison_label": comparison_label,
                    "focus_mode": focus_mode,
                    "link_id": row["link_id"],
                    "abs_delta": row["abs_delta"],
                    "delta_mean": row["delta_mean"],
                    "p_link": row["p_link"],
                    "below_p25": bool(row["below_p25"]),
                    "below_p02": bool(row["below_p02"]),
                    "low_relative_contribution": bool(row["low_relative_contribution"]),
                    "rank_by_abs_delta": int(row["rank_by_abs_delta"]),
                }
            )
            if row["low_relative_contribution"]:
                low_rows.append(
                    {
                        "participant_id": participant_id,
                        "block_label": block_label,
                        "comparison_label": comparison_label,
                        "focus_mode": focus_mode,
                        "link_id": row["link_id"],
                        "abs_delta": row["abs_delta"],
                        "p_link": row["p_link"],
                        "below_p25": bool(row["below_p25"]),
                        "below_p02": bool(row["below_p02"]),
                        "p_link_p25_threshold": p25,
                    }
                )

    return (
        pd.DataFrame(dist_rows),
        pd.DataFrame(low_rows),
        pd.DataFrame(summary_rows),
    )


def build_block_comparison(summary: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    base = summary[summary["focus_mode"] == "all"].copy()
    for (participant_id, comparison_label), grp in base.groupby(
        ["participant_id", "comparison_label"], sort=True
    ):
        all_row = grp[grp["block_label"] == "all_P1_P2_P3_P4_P5"]
        p3_row = grp[grp["block_label"] == "P3_P4_P5"]
        if all_row.empty or p3_row.empty:
            continue
        a = all_row.iloc[0]
        b = p3_row.iloc[0]
        rows.append(
            {
                "participant_id": participant_id,
                "comparison_label": comparison_label,
                "focus_mode": "all",
                "all_block_normalized_entropy": a["normalized_entropy"],
                "p3_block_normalized_entropy": b["normalized_entropy"],
                "delta_normalized_entropy": b["normalized_entropy"] - a["normalized_entropy"],
                "all_block_gini": a["gini_concentration"],
                "p3_block_gini": b["gini_concentration"],
                "delta_gini": b["gini_concentration"] - a["gini_concentration"],
                "all_block_top_3_share": a["top_3_share"],
                "p3_block_top_3_share": b["top_3_share"],
                "delta_top_3_share": b["top_3_share"] - a["top_3_share"],
                "all_block_links_for_80pct": a["links_for_80pct"],
                "p3_block_links_for_80pct": b["links_for_80pct"],
                "distribution_pattern_note": _block_pattern_note(a, b),
            }
        )
    return pd.DataFrame(rows)


def build_pc_focus_comparison(summary: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    focus_modes = (
        "functional_p50",
        "null_space_after_p50",
        "functional_p60",
        "null_space_after_p60",
    )
    for (participant_id, block_label, comparison_label), grp in summary.groupby(
        ["participant_id", "block_label", "comparison_label"], sort=True
    ):
        modes = {row.focus_mode: row for _, row in grp.iterrows()}
        if "all" not in modes:
            continue
        all_row = modes["all"]
        for focus in focus_modes:
            if focus not in modes:
                continue
            frow = modes[focus]
            rows.append(
                {
                    "participant_id": participant_id,
                    "block_label": block_label,
                    "comparison_label": comparison_label,
                    "focus_mode": focus,
                    "sensitivity_tier": (
                        "main_sensitivity"
                        if focus in ("functional_p50", "null_space_after_p50")
                        else "optional_sensitivity"
                    ),
                    "all_normalized_entropy": all_row["normalized_entropy"],
                    "focus_normalized_entropy": frow["normalized_entropy"],
                    "delta_normalized_entropy": frow["normalized_entropy"] - all_row["normalized_entropy"],
                    "all_gini": all_row["gini_concentration"],
                    "focus_gini": frow["gini_concentration"],
                    "delta_gini": frow["gini_concentration"] - all_row["gini_concentration"],
                    "all_top_3_share": all_row["top_3_share"],
                    "focus_top_3_share": frow["top_3_share"],
                    "delta_top_3_share": frow["top_3_share"] - all_row["top_3_share"],
                    "distribution_pattern_note": _focus_pattern_note(all_row, frow),
                }
            )
    return pd.DataFrame(rows)


def _block_pattern_note(all_row: pd.Series, p3_row: pd.Series) -> str:
    if p3_row["normalized_entropy"] > all_row["normalized_entropy"] + 0.02:
        return "P3_P4_P5 shows more evenly distributed link contribution than all_P1_P2_P3_P4_P5"
    if p3_row["normalized_entropy"] < all_row["normalized_entropy"] - 0.02:
        return "P3_P4_P5 shows more concentrated link contribution than all_P1_P2_P3_P4_P5"
    return "Similar link contribution distribution between blocks"


def _focus_pattern_note(all_row: pd.Series, focus_row: pd.Series) -> str:
    if focus_row["normalized_entropy"] > all_row["normalized_entropy"] + 0.02:
        return "Focus mode shows more evenly distributed link contribution than all-PC mode"
    if focus_row["normalized_entropy"] < all_row["normalized_entropy"] - 0.02:
        return "Focus mode shows more concentrated link contribution than all-PC mode"
    return "Similar link contribution distribution between focus modes"


def _save_fig(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def write_plots(batch_root: Path, summary: pd.DataFrame, distribution: pd.DataFrame) -> list[str]:
    evenness_dir = batch_root / "plots" / "link_contribution_evenness"
    dominance_dir = batch_root / "plots" / "top_k_dominance"
    written: list[str] = []

    for _, row in summary.iterrows():
        key = (
            row["participant_id"],
            row["block_label"],
            row["comparison_label"],
            row["focus_mode"],
        )
        sub = distribution[
            (distribution["participant_id"] == row["participant_id"])
            & (distribution["block_label"] == row["block_label"])
            & (distribution["comparison_label"] == row["comparison_label"])
            & (distribution["focus_mode"] == row["focus_mode"])
        ].sort_values("p_link", ascending=True)
        if sub.empty:
            continue
        fname_base = f"{row['participant_id']}_{row['block_label']}_{row['comparison_label']}_{row['focus_mode']}"

        fig, ax = plt.subplots(figsize=(8, max(4, 0.3 * len(sub))))
        colors = ["steelblue" if not x else "lightgray" for x in sub["low_relative_contribution"]]
        ax.barh(sub["link_id"], sub["p_link"], color=colors)
        ax.set_xlabel("Relative link contribution (p_link)")
        ax.set_title(
            f"{row['participant_id']} | {row['block_label']} | {row['comparison_label']} | {row['focus_mode']}"
        )
        out = evenness_dir / f"{fname_base}_p_link.png"
        _save_fig(fig, out)
        written.append(str(out.relative_to(batch_root)))

        fig, ax = plt.subplots(figsize=(6, 4))
        metrics = ["top_1_share", "top_3_share", "top_5_share"]
        vals = [row[m] for m in metrics]
        ax.bar(metrics, vals, color=["#4c78a8", "#72b7b2", "#f58518"])
        ax.set_ylim(0, 1)
        ax.set_ylabel("Cumulative p_link share")
        ax.set_title(f"Top-k dominance | {fname_base}")
        out = dominance_dir / f"{fname_base}_topk.png"
        _save_fig(fig, out)
        written.append(str(out.relative_to(batch_root)))

    # Summary comparison plots (all focus, longitudinal only)
    long_summary = summary[
        (summary["focus_mode"] == "all")
        & (summary["comparison_label"].isin(["T1_vs_T2", "T1_vs_T3"]))
    ]
    if not long_summary.empty:
        fig, ax = plt.subplots(figsize=(10, 5))
        labels = [
            f"{r.participant_id}\n{r.block_label}\n{r.comparison_label}"
            for _, r in long_summary.iterrows()
        ]
        x = np.arange(len(labels))
        ax.bar(x - 0.2, long_summary["normalized_entropy"], width=0.4, label="normalized_entropy")
        ax.bar(x + 0.2, long_summary["gini_concentration"], width=0.4, label="gini_concentration")
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
        ax.set_title("Longitudinal link contribution evenness (all-PC)")
        ax.legend()
        out = evenness_dir / "longitudinal_normalized_entropy_gini_all_pc.png"
        _save_fig(fig, out)
        written.append(str(out.relative_to(batch_root)))

    return written


def run_analysis(batch_root: Path) -> dict[str, Path]:
    batch_root = Path(batch_root)
    combined = load_combined_link_results(batch_root)
    link_abs = aggregate_link_abs_delta(combined)
    distribution, low_links, summary = compute_distribution_tables(link_abs)
    block_cmp = build_block_comparison(summary)
    focus_cmp = build_pc_focus_comparison(summary)

    outputs = {
        "link_contribution_distribution.csv": distribution,
        "low_contribution_links.csv": low_links,
        "contribution_evenness_summary.csv": summary,
        "block_evenness_comparison.csv": block_cmp,
        "pc_focus_evenness_comparison.csv": focus_cmp,
    }
    paths: dict[str, Path] = {}
    for name, frame in outputs.items():
        path = batch_root / name
        frame.to_csv(path, index=False)
        paths[name] = path

    write_plots(batch_root, summary, distribution)
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
    print(f"Link contribution distribution analysis complete: {args.batch_root}")
    for name, path in paths.items():
        print(f"  {name}")


if __name__ == "__main__":
    main()
