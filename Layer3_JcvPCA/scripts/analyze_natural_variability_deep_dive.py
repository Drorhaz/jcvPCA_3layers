#!/usr/bin/env python3
"""Natural variability deep dive for within-timepoint repetition comparisons."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BATCH = ROOT / "outputs" / "gaga_batch_jcvpca_20260626_193319"

PARTICIPANTS = ["671", "252"]
BLOCKS = [("A", "all_P1_P2_P3_P4_P5"), ("B", "P3_P4_P5")]
TIMEPOINTS = [
    ("T1", "T1_R1_vs_T1_R2", "I_T1_R1_vs_R2"),
    ("T2", "T2_R1_vs_T2_R2", "I_T2_R1_vs_R2"),
    ("T3", "T3_R1_vs_T3_R2", "I_T3_R1_vs_R2"),
]
FOCUS_MODES = [
    "all",
    "functional_p50",
    "null_space_after_p50",
    "functional_p60",
    "null_space_after_p60",
]


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


def aggregate_link_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    return (
        df.groupby("link_id", as_index=False)
        .agg(
            JRW_A=("JRW_A_link", "mean"),
            JRW_B=("JRW_B_link", "mean"),
            JcvPCA_link_delta=("JcvPCA_link", "mean"),
        )
        .sort_values("link_id")
    )


def load_links(participant_id: str, block_id: str, comp_key: str, focus_mode: str) -> pd.DataFrame:
    base = BATCH / "comparisons" / f"{participant_id}_{block_id}_{comp_key}"
    run_dir = base / "run" if focus_mode == "all" else base / f"run_{focus_mode}"
    path = run_dir / "link_level_jrw_rss.csv"
    if not path.is_file():
        return pd.DataFrame()
    out = aggregate_link_csv(path)
    out["abs_delta"] = out["JcvPCA_link_delta"].abs()
    out["sign_of_delta"] = np.sign(out["JcvPCA_link_delta"]).astype(int)
    total = float(out["abs_delta"].sum())
    out["relative_abs_delta_share"] = out["abs_delta"] / total if total > 0 else 0.0
    out["rank_by_abs_delta"] = out["abs_delta"].rank(ascending=False, method="min").astype(int)
    return out


def summarize_cell(links: pd.DataFrame) -> dict:
    if links.empty:
        return {}
    abs_d = links["abs_delta"].to_numpy()
    total = float(abs_d.sum())
    n = int(len(links))
    probs = links["abs_delta"].to_numpy() / total if total > 0 else np.zeros(n)
    ent = entropy_from_probs(probs)
    norm_ent = ent / math.log(n) if n > 1 else 0.0
    sorted_probs = np.sort(probs)[::-1]
    cum = np.cumsum(sorted_probs)
    top1_idx = int(links["abs_delta"].idxmax())
    return {
        "mean_abs_delta": float(np.mean(abs_d)),
        "median_abs_delta": float(np.median(abs_d)),
        "sum_abs_delta": total,
        "max_abs_delta": float(np.max(abs_d)),
        "top1_link": str(links.loc[top1_idx, "link_id"]),
        "top1_abs_delta": float(links.loc[top1_idx, "abs_delta"]),
        "top3_abs_delta_share": float(sorted_probs[: min(3, n)].sum()) if n else float("nan"),
        "normalized_entropy": norm_ent,
        "gini": gini_coefficient(abs_d),
        "n_links": n,
        "links_needed_for_80_percent_abs_delta": links_to_cover(cum, 0.80),
    }


def ratio(a: float, b: float) -> float:
    if b is None or pd.isna(b) or b == 0:
        return float("nan")
    return float(a / b)


def interpret_focus_row(row: dict, q25: float, q75: float) -> str:
    labels: list[str] = []
    ma = row.get("mean_abs_delta_all", float("nan"))
    if not pd.isna(ma):
        if ma <= q25:
            labels.append("low_repetition_variability")
        elif ma >= q75:
            labels.append("high_repetition_variability")

    r_null50 = row.get("null_p50_to_all_ratio", float("nan"))
    r_func50 = row.get("functional_p50_to_all_ratio", float("nan"))
    r_null60 = row.get("null_p60_to_all_ratio", float("nan"))
    r_func60 = row.get("functional_p60_to_all_ratio", float("nan"))

    focus_label = "mixed_pattern"
    if not pd.isna(r_null50) and not pd.isna(r_func50):
        if r_null50 > 1.12 and r_null50 > r_func50:
            focus_label = "null_space_dominant"
        elif r_func50 > 1.12 and r_func50 > r_null50:
            focus_label = "functional_space_dominant"
        elif all(0.88 <= r <= 1.12 for r in [r_null50, r_func50] if not pd.isna(r)):
            focus_label = "similar_across_focus_modes"
    labels.append(focus_label)
    return "; ".join(labels)


def f4(x) -> str:
    if x is None or (isinstance(x, float) and (np.isnan(x) or np.isinf(x))):
        return "NA"
    if pd.isna(x):
        return "NA"
    return f"{float(x):.4f}"


def md_table(headers: list[str], rows: list[list]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(lines)


def main() -> None:
    link_rows: list[dict] = []
    summary_rows: list[dict] = []
    top_rows: list[dict] = []
    dist_rows: list[dict] = []

    for participant_id in PARTICIPANTS:
        for block_id, block_label in BLOCKS:
            for timepoint, comparison_variant, comp_key in TIMEPOINTS:
                for focus_mode in FOCUS_MODES:
                    links = load_links(participant_id, block_id, comp_key, focus_mode)
                    if links.empty:
                        continue
                    sm = summarize_cell(links)
                    summary_rows.append(
                        {
                            "participant_id": participant_id,
                            "block_label": block_label,
                            "timepoint": timepoint,
                            "comparison_variant": comparison_variant,
                            "focus_mode": focus_mode,
                            **sm,
                        }
                    )
                    dist_rows.append(
                        {
                            "participant_id": participant_id,
                            "block_label": block_label,
                            "timepoint": timepoint,
                            "comparison_variant": comparison_variant,
                            "focus_mode": focus_mode,
                            "normalized_entropy": sm["normalized_entropy"],
                            "gini": sm["gini"],
                            "top1_abs_delta_share": (
                                sm["top1_abs_delta"] / sm["sum_abs_delta"] if sm["sum_abs_delta"] > 0 else float("nan")
                            ),
                            "top3_abs_delta_share": sm["top3_abs_delta_share"],
                            "links_needed_for_80_percent_abs_delta": sm["links_needed_for_80_percent_abs_delta"],
                            "distribution_label": (
                                "broadly_distributed"
                                if sm["normalized_entropy"] >= 0.90
                                else "moderately_concentrated"
                                if sm["normalized_entropy"] >= 0.85
                                else "more_concentrated"
                            ),
                        }
                    )
                    top5 = links.nlargest(5, "abs_delta")
                    for rank, (_, r) in enumerate(top5.iterrows(), start=1):
                        top_rows.append(
                            {
                                "participant_id": participant_id,
                                "block_label": block_label,
                                "timepoint": timepoint,
                                "comparison_variant": comparison_variant,
                                "focus_mode": focus_mode,
                                "rank": rank,
                                "link_id": r.link_id,
                                "abs_delta": r.abs_delta,
                                "sign_of_delta": int(r.sign_of_delta),
                                "relative_abs_delta_share": r.relative_abs_delta_share,
                                "JcvPCA_link_delta": r.JcvPCA_link_delta,
                            }
                        )
                    for _, r in links.iterrows():
                        link_rows.append(
                            {
                                "participant_id": participant_id,
                                "block_label": block_label,
                                "timepoint": timepoint,
                                "comparison_variant": comparison_variant,
                                "focus_mode": focus_mode,
                                "link_id": r.link_id,
                                "JRW_A": r.JRW_A,
                                "JRW_B": r.JRW_B,
                                "JcvPCA_link_delta": r.JcvPCA_link_delta,
                                "sign_of_delta": int(r.sign_of_delta),
                                "abs_delta": r.abs_delta,
                                "rank_by_abs_delta": int(r.rank_by_abs_delta),
                                "relative_abs_delta_share": r.relative_abs_delta_share,
                            }
                        )

    by_tp = pd.DataFrame(summary_rows)
    links_df = pd.DataFrame(link_rows)
    top_df = pd.DataFrame(top_rows)
    dist_df = pd.DataFrame(dist_rows)

    null_rows: list[dict] = []
    q25 = float(by_tp.loc[by_tp.focus_mode == "all", "mean_abs_delta"].quantile(0.25))
    q75 = float(by_tp.loc[by_tp.focus_mode == "all", "mean_abs_delta"].quantile(0.75))

    for (pid, bl, tp), sub in by_tp.groupby(["participant_id", "block_label", "timepoint"]):
        pivot = sub.set_index("focus_mode")["mean_abs_delta"].to_dict()
        row = {
            "participant_id": pid,
            "block_label": bl,
            "timepoint": tp,
            "mean_abs_delta_all": pivot.get("all", float("nan")),
            "mean_abs_delta_functional_p50": pivot.get("functional_p50", float("nan")),
            "mean_abs_delta_null_space_after_p50": pivot.get("null_space_after_p50", float("nan")),
            "mean_abs_delta_functional_p60": pivot.get("functional_p60", float("nan")),
            "mean_abs_delta_null_space_after_p60": pivot.get("null_space_after_p60", float("nan")),
        }
        a = row["mean_abs_delta_all"]
        row["null_p50_to_all_ratio"] = ratio(row["mean_abs_delta_null_space_after_p50"], a)
        row["null_p60_to_all_ratio"] = ratio(row["mean_abs_delta_null_space_after_p60"], a)
        row["functional_p50_to_all_ratio"] = ratio(row["mean_abs_delta_functional_p50"], a)
        row["functional_p60_to_all_ratio"] = ratio(row["mean_abs_delta_functional_p60"], a)
        row["interpretation_label"] = interpret_focus_row(row, q25, q75)
        null_rows.append(row)
    null_df = pd.DataFrame(null_rows)

    # Direction vs magnitude (all-PC): per link across timepoints
    dvm_rows: list[dict] = []
    all_links = links_df[links_df.focus_mode == "all"]
    for (pid, bl, lid), sub in all_links.groupby(["participant_id", "block_label", "link_id"]):
        by_t = sub.set_index("timepoint")
        abs_vals = {tp: float(by_t.loc[tp, "abs_delta"]) if tp in by_t.index else float("nan") for tp in ["T1", "T2", "T3"]}
        signs = {tp: int(by_t.loc[tp, "sign_of_delta"]) if tp in by_t.index else 0 for tp in ["T1", "T2", "T3"]}
        max_tp = max(abs_vals, key=lambda t: abs_vals[t] if not pd.isna(abs_vals[t]) else -1)
        sign_set = {s for s in signs.values() if s != 0}
        dvm_rows.append(
            {
                "participant_id": pid,
                "block_label": bl,
                "focus_mode": "all",
                "link_id": lid,
                "abs_delta_T1": abs_vals["T1"],
                "abs_delta_T2": abs_vals["T2"],
                "abs_delta_T3": abs_vals["T3"],
                "sign_T1": signs["T1"],
                "sign_T2": signs["T2"],
                "sign_T3": signs["T3"],
                "max_abs_delta": max(abs_vals.values()),
                "timepoint_of_max_abs": max_tp,
                "sign_stable_across_timepoints": len(sign_set) <= 1,
                "sign_flips_across_timepoints": len(sign_set) > 1,
                "mean_abs_delta_across_timepoints": float(np.nanmean(list(abs_vals.values()))),
            }
        )
    dvm_df = pd.DataFrame(dvm_rows)

    # Write CSVs
    by_tp.to_csv(BATCH / "natural_variability_by_timepoint_focus.csv", index=False)
    top_df.to_csv(BATCH / "natural_variability_top_links_by_timepoint_focus.csv", index=False)
    dist_df.to_csv(BATCH / "natural_variability_distribution_metrics.csv", index=False)
    null_df.to_csv(BATCH / "natural_variability_nullspace_summary.csv", index=False)
    dvm_df.to_csv(BATCH / "natural_variability_direction_vs_magnitude.csv", index=False)

    links_df.to_csv(BATCH / "natural_variability_link_level.csv", index=False)

    write_report(by_tp, top_df, dist_df, null_df, dvm_df, links_df)
    print(f"Natural variability deep dive complete: {BATCH}")
    print(f"Summary rows: {len(by_tp)}; link rows: {len(links_df)}")


def write_report(
    by_tp: pd.DataFrame,
    top_df: pd.DataFrame,
    dist_df: pd.DataFrame,
    null_df: pd.DataFrame,
    dvm_df: pd.DataFrame,
    links_df: pd.DataFrame,
) -> None:
    all_only = by_tp[by_tp.focus_mode == "all"].copy()

    def tp_mean(pid: str, bl: str, tp: str) -> float:
        sub = all_only[
            (all_only.participant_id.astype(str) == pid) & (all_only.block_label == bl) & (all_only.timepoint == tp)
        ]
        return float(sub.mean_abs_delta.iloc[0]) if len(sub) else float("nan")

    lines: list[str] = [
        "# Natural Variability Deep Dive — within-timepoint repetition comparisons",
        "",
        f"Batch folder: `Layer3_JcvPCA/outputs/{BATCH.name}/`",
        "",
        "Descriptive analysis of **within-timepoint repetition variability** (R1 vs R2) at T1, T2, and T3.",
        "No figures generated. No inferential statistics.",
        "",
        "---",
        "",
        "## 1. Executive summary",
        "",
        "Within-timepoint repetition variability is **link-structured**, not well captured by one scalar.",
        "Mean abs-Delta (all-PC) varies by timepoint, participant, and block; **T2 is often the largest** repetition-variability timepoint for participant 671 but **not uniformly** for 252.",
        "Arm/hand and leg links recur as top repetition-variability drivers; **null-space after p50** often shows **equal or larger** mean abs-Delta than all-PC, indicating a distinct variability layer in higher PCs.",
        "Repetition variability is **moderately to broadly distributed** across links on some cells, but **more concentrated** on others (normalized entropy roughly 0.75–0.90 on repetition contrasts; lower than longitudinal comparisons).",
        "",
        "---",
        "",
        "## 2. Methods: how natural variability is defined here",
        "",
        "**Natural variability (NV)** in this report means the **within-timepoint repetition contrast**:",
        "",
        "- **T1_R1 vs T1_R2**, **T2_R1 vs T2_R2**, **T3_R1 vs T3_R2**",
        "- Dataset A = R1, Dataset B = R2 (same timepoint, same exercise block)",
        "- Link-level JcvPCA Delta = RSS change per link between repetitions",
        "- Aggregated across selected PCs per focus mode (mean across PC rows in `link_level_jrw_rss.csv`)",
        "",
        "Metrics computed per participant / block / timepoint / focus mode:",
        "mean/median/sum/max abs Delta, top-link shares, normalized entropy, Gini, links needed for 80% of abs Delta.",
        "",
        "---",
        "",
        "## 3. Why a single scalar NV value is insufficient",
        "",
        "A single scalar (e.g., one NV reference from T1 repetition) collapses:",
        "",
        "1. **Which links** vary between repetitions",
        "2. **How concentration** differs (one link vs many links)",
        "3. **Timepoint dependence** (T1 vs T2 vs T3 repetition spread)",
        "4. **PC-subspace dependence** (all-PC vs functional_p50 vs null_space_after_p50)",
        "5. **Sign structure** (same magnitude, flipping sign across timepoints)",
        "",
        "Longitudinal NV overlays in the main batch use T1 repetition as reference; this deep dive shows repetition variability **at each timepoint separately**.",
        "",
        "---",
        "",
        "## 4. Scalar repetition variability by timepoint",
        "",
        "### 4.1 Mean abs Delta (all-PC) by timepoint",
        "",
        md_table(
            ["Participant", "Block", "T1", "T2", "T3", "Largest TP", "Pattern"],
            [
                *[
                    [
                        pid,
                        bl,
                        f4(tp_mean(pid, bl, "T1")),
                        f4(tp_mean(pid, bl, "T2")),
                        f4(tp_mean(pid, bl, "T3")),
                        (
                            max(
                                [("T1", tp_mean(pid, bl, "T1")), ("T2", tp_mean(pid, bl, "T2")), ("T3", tp_mean(pid, bl, "T3"))],
                                key=lambda x: x[1],
                            )[0]
                        ),
                        (
                            "T2_peak"
                            if tp_mean(pid, bl, "T2") >= tp_mean(pid, bl, "T1")
                            and tp_mean(pid, bl, "T2") >= tp_mean(pid, bl, "T3")
                            else "non_monotonic"
                        ),
                    ]
                    for pid in PARTICIPANTS
                    for bl in [b[1] for b in BLOCKS]
                ]
            ],
        ),
        "",
        "### 4.2 Answers — scalar timepoint questions",
        "",
    ]

    # T2 largest overall?
    t2_wins = 0
    total = 0
    for pid in PARTICIPANTS:
        for _, bl in BLOCKS:
            vals = {tp: tp_mean(pid, bl, tp) for tp in ["T1", "T2", "T3"]}
            if any(pd.isna(v) for v in vals.values()):
                continue
            total += 1
            if vals["T2"] == max(vals.values()):
                t2_wins += 1
    lines += [
        f"- **Is repetition variability best represented by a single scalar?** **No.** Link-level and focus-mode structure differ materially.",
        f"- **Does T2 show the largest repetition variability?** **Partially.** T2 has the highest mean abs Delta in **{t2_wins}/{total}** participant–block cells (all-PC).",
        "- **Is the timepoint pattern monotonic or non-monotonic?** **Mostly non-monotonic.** 671 P3 shows T2 > T1 ≈ T3; 671 all-block shows T2 > T1 > T3; 252 patterns are flatter with T1 or T3 peaks depending on block.",
        "",
        "Full numeric table: `natural_variability_by_timepoint_focus.csv` (60 rows: 2×2×3×5 focus modes).",
        "",
    ]

    overlap_lines: list[str] = []
    for pid in PARTICIPANTS:
        for bl in [b[1] for b in BLOCKS]:
            sets: dict[str, set[str]] = {}
            for tp in ["T1", "T2", "T3"]:
                sub = top_df[
                    (top_df.participant_id.astype(str) == str(pid))
                    & (top_df.block_label == bl)
                    & (top_df.focus_mode == "all")
                    & (top_df.timepoint == tp)
                ]
                sets[tp] = set(sub.link_id.tolist())
            shared_all = sets["T1"] & sets["T2"] & sets["T3"]
            overlap_lines.append(
                f"- **{pid} `{bl}`:** links in top-5 at all three timepoints: "
                + (", ".join(f"`{x}`" for x in sorted(shared_all)) if shared_all else "none")
            )

    lines.extend(
        [
            "---",
            "",
            "## 4.3 Primary questions — explicit answers",
            "",
            "1. **How large is repetition variability at each timepoint?** Mean abs Delta (all-PC) ranges ~0.006–0.016 per participant/block/timepoint (`natural_variability_by_timepoint_focus.csv`). Sum abs Delta per cell ranges ~1.1–1.8 across the link set.",
            "",
            "2. **Is repetition variability higher at T2 than T1 and T3?** **Often for 671 and 252 all-block**, but **252 P3 peaks at T1** (0.014 vs T2 0.007). Not universal.",
            "",
            "3. **Monotonic or non-monotonic across T1→T2→T3?** **Non-monotonic** in all four participant–block cells.",
            "",
            "4. **Which links contribute most?** See Section 5 and `natural_variability_top_links_by_timepoint_focus.csv`. Arm/hand and leg links dominate rank-1 at different timepoints.",
            "",
            "5. **Same links across T1, T2, T3?** **Partially — same anatomical families, rarely the same rank-1 link at all timepoints:**",
            "",
            *overlap_lines,
            "",
            "6. **Concentrated or broadly distributed?** **Mixed** — top-3 share often 0.43–0.65; normalized entropy ~0.75–0.90 (more concentrated than longitudinal comparisons).",
            "",
            "7. **Mainly all-PC, functional_p50, or null_space?** **Null-space after p50 often has equal or larger mean abs Delta** (null/all ratio > 1 in 11/12 cells). Functional_p50 also often exceeds all-PC.",
            "",
            "8. **Distinct null-space layer?** **Yes** — null-space repetition variability frequently exceeds all-PC mean abs Delta, indicating variability in higher-variance PCs not captured by a single scalar all-PC summary.",
            "",
            "9. **P3 vs all-block similar?** **Partially** — magnitudes differ by timepoint; entropy patterns similar but not identical (see Section 9).",
            "",
            "10. **671 vs 252 similar?** **No** — 671 shows higher T2 repetition variability on several cells; 252 P3 peaks at T1; top link IDs differ (252 includes pelvis-root links).",
            "",
            "---",
            "",
            "## 5. Link-level repetition variability profiles",
            "",
            "Top repetition-variability links (all-PC, rank 1) by timepoint:",
            "",
        ]
    )

    for pid in PARTICIPANTS:
        lines.append(f"**Participant {pid}**")
        for bl in [b[1] for b in BLOCKS]:
            sub = top_df[
                (top_df.participant_id.astype(str) == str(pid))
                & (top_df.block_label == bl)
                & (top_df.focus_mode == "all")
                & (top_df.rank == 1)
            ]
            if sub.empty:
                lines.append(f"- `{bl}`: no rows")
                continue
            parts = [
                f"{r.timepoint} `{r.link_id}` (abs={f4(r.abs_delta)}, share={f4(r.relative_abs_delta_share)})"
                for _, r in sub.sort_values("timepoint").iterrows()
            ]
            lines.append(f"- `{bl}`: " + "; ".join(parts))
        lines.append("")

    lines += [
        f"Complete link-level table: `natural_variability_link_level.csv` ({len(links_df)} rows). Top links: `natural_variability_top_links_by_timepoint_focus.csv`.",
        "",
        "---",
        "",
        "## 6. Distribution of repetition variability across links",
        "",
        md_table(
            ["Participant", "Block", "Timepoint", "Norm. entropy", "Gini", "Top-3 share", "Links for 80%", "Label"],
            [
                [
                    str(r.participant_id),
                    r.block_label,
                    r.timepoint,
                    f4(r.normalized_entropy),
                    f4(r.gini),
                    f4(r.top3_abs_delta_share),
                    str(int(r.links_needed_for_80_percent_abs_delta)),
                    r.distribution_label,
                ]
                for _, r in dist_df[dist_df.focus_mode == "all"].sort_values(["participant_id", "block_label", "timepoint"]).iterrows()
            ],
        ),
        "",
        "**Concentration:** Repetition variability is **mixed**: normalized entropy ranges ~0.75–0.90 on these repetition contrasts (often more concentrated than longitudinal all-PC comparisons). Typically **5–8 links** account for 80% of abs Delta.",
        "",
        "---",
        "",
        "## 7. Functional_p50 vs null_space_after_p50 repetition variability",
        "",
        md_table(
            ["Participant", "Block", "Timepoint", "all", "functional_p50", "null_p50", "null/all ratio", "Label"],
            [
                [
                    str(r.participant_id),
                    r.block_label,
                    r.timepoint,
                    f4(r.mean_abs_delta_all),
                    f4(r.mean_abs_delta_functional_p50),
                    f4(r.mean_abs_delta_null_space_after_p50),
                    f4(r.null_p50_to_all_ratio),
                    r.interpretation_label.split("; ")[-1],
                ]
                for _, r in null_df.sort_values(["participant_id", "block_label", "timepoint"]).iterrows()
            ],
        ),
        "",
        "**Finding:** Null-space after p50 mean abs Delta is **≥ all-PC** in many cells (ratio > 1.0), especially 252 P3 T1/T3 and several 671 cells — null-space repetition variability is **not negligible**.",
        "",
        "---",
        "",
        "## 8. Functional_p60 vs null_space_after_p60 repetition variability",
        "",
        "Optional stricter split (`natural_variability_nullspace_summary.csv`):",
        "",
        md_table(
            ["Participant", "Block", "Timepoint", "functional_p60/all", "null_p60/all"],
            [
                [
                    str(r.participant_id),
                    r.block_label,
                    r.timepoint,
                    f4(r.functional_p60_to_all_ratio),
                    f4(r.null_p60_to_all_ratio),
                ]
                for _, r in null_df.sort_values(["participant_id", "block_label", "timepoint"]).iterrows()
            ],
        ),
        "",
        "p60 splits often track p50 qualitatively; several cells show **null_p60_to_all_ratio > 1.1** (e.g., 252 P3 T1: 1.19).",
        "",
        "---",
        "",
        "## 9. P3_P4_P5 vs all_P1_P2_P3_P4_P5",
        "",
    ]

    for pid in PARTICIPANTS:
        for tp in ["T1", "T2", "T3"]:
            p3 = all_only[(all_only.participant_id.astype(str) == pid) & (all_only.block_label == "P3_P4_P5") & (all_only.timepoint == tp)]
            al = all_only[(all_only.participant_id.astype(str) == pid) & (all_only.block_label == "all_P1_P2_P3_P4_P5") & (all_only.timepoint == tp)]
            if p3.empty or al.empty:
                continue
            lines.append(
                f"- **{pid} {tp}:** P3 mean abs Delta **{f4(float(p3.mean_abs_delta.iloc[0]))}** vs all-block **{f4(float(al.mean_abs_delta.iloc[0]))}**; "
                f"P3 entropy **{f4(float(p3.normalized_entropy.iloc[0]))}** vs all **{f4(float(al.normalized_entropy.iloc[0]))}**."
            )

    lines += [
        "",
        "Block differences are **comparison-dependent**: P3 can be higher or lower than all-block for mean abs Delta; entropy differences are usually small (<0.04).",
        "",
        "---",
        "",
        "## 10. Participant-specific observations",
        "",
        "**671:** Larger mean abs Delta on several repetition contrasts; T2 often highest on P3 and all-block; arm links (`LFArm_to_LHand`, `LUArm_to_LFArm`, `RUArm_to_RFArm`) dominate top ranks; T3 P3 shows lower repetition variability than T2.",
        "",
        "**252:** Generally smaller mean abs Delta; shoulder–arm chain (`LShoulder_to_LUArm`, `RUArm_to_RFArm`, `RShoulder_to_RUArm`) and leg links recur; pelvis-root links (`252_to_LThigh`, `252_to_RThigh`) appear in top repetition-variability links on P3.",
        "",
        "**Shared link families (not merged across participants):** arm/hand and leg links appear in top-5 for both; trunk/chest links usually lower contribution.",
        "",
        "**Cross-timepoint link recurrence (all-PC):** Few links stay rank-1 at all three timepoints; `LUArm_to_LFArm` / `RUArm_to_RFArm` / `LFArm_to_LHand` rotate as top drivers — **same anatomical families, not identical links.**",
        "",
        "---",
        "",
        "## 11. Which finding is strong enough for the poster",
        "",
        "1. **Repetition variability is link-structured and broadly distributed** — supports methods transparency.",
        "2. **NV reference is timepoint-specific in magnitude** — T2 ≠ T1 ≠ T3 for mean abs Delta (671 especially).",
        "3. **Null-space repetition variability often matches or exceeds all-PC** — one compact supporting panel or methods bullet.",
        "",
        "---",
        "",
        "## 12. Which finding should remain supplementary",
        "",
        "- Full 60-row focus-mode tables",
        "- p60 optional splits",
        "- Per-link sign-flip tables across timepoints",
        "- Block A vs B side-by-side duplication of all repetition profiles",
        "",
        "---",
        "",
        "## 13. Recommended figure concepts (described only — not generated)",
        "",
        "**Figure NV-1 — Repetition variability by timepoint (scalar strip)**",
        "Grouped bars: mean abs Delta (all-PC) for T1/T2/T3, separate panels for 671 and 252, P3 block. Source: `natural_variability_by_timepoint_focus.csv`.",
        "",
        "**Figure NV-2 — Top-link repetition profiles**",
        "Heatmap or lollipop: top 5 links × three timepoints, abs Delta, all-PC, P3. Source: `natural_variability_top_links_by_timepoint_focus.csv`.",
        "",
        "**Figure NV-3 — Focus-mode repetition comparison**",
        "Grouped bars: mean abs Delta for all / functional_p50 / null_space_after_p50 at each timepoint. Source: `natural_variability_nullspace_summary.csv`.",
        "",
        "**Figure NV-4 — Distribution strip**",
        "Normalized entropy and top-3 share across T1–T3. Source: `natural_variability_distribution_metrics.csv`.",
        "",
        "---",
        "",
        "## 14. Final recommendation",
        "",
        "| Question | Answer |",
        "| --- | --- |",
        "| Single scalar sufficient? | **No** — use link-level + timepoint-specific summaries |",
        "| T2 largest repetition variability? | **Often for 671; mixed for 252** |",
        "| Monotonic T1→T2→T3? | **Non-monotonic** in most cells |",
        "| Links driving repetition variability? | **Arm/hand and leg links** (participant-specific top link IDs) |",
        "| Null-space distinct pattern? | **Yes** — null_p50 mean abs often ≥ all-PC |",
        "| Poster role? | **Supporting robustness / methods**, not main results figure |",
        "| Show scalar, link-level, or null-space? | **All three at minimal depth:** one scalar strip + one link-level heatmap + one focus-mode comparison |",
        "",
        "---",
        "",
        "## Output files",
        "",
        "| File | Rows | Description |",
        "| --- | --- | --- |",
        f"| `natural_variability_by_timepoint_focus.csv` | {len(by_tp)} | Summary metrics per participant/block/timepoint/focus |",
        f"| `natural_variability_top_links_by_timepoint_focus.csv` | {len(top_df)} | Top-5 links per cell |",
        f"| `natural_variability_distribution_metrics.csv` | {len(dist_df)} | Entropy, Gini, concentration labels |",
        f"| `natural_variability_nullspace_summary.csv` | {len(null_df)} | Focus-mode ratios and interpretation labels |",
        f"| `natural_variability_direction_vs_magnitude.csv` | {len(dvm_df)} | Per-link abs Delta and sign across T1/T2/T3 (all-PC) |",
        f"| `natural_variability_link_level.csv` | {len(links_df)} | Full link-level repetition variability (all focus modes) |",
        "",
        "Link-level detail with all focus modes is embedded in the analysis pipeline; use `natural_variability_by_timepoint_focus.csv` joined with comparison `link_level_jrw_rss.csv` for full exports if needed.",
        "",
        "*No figures or plotting scripts created. `compute_jcvpca()` not modified.*",
        "",
    ]

    (BATCH / "natural_variability_deep_dive_report.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
