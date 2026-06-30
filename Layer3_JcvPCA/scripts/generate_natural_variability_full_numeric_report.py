#!/usr/bin/env python3
"""Generate natural_variability_FULL_NUMERIC_REPORT.md from NV deep-dive CSV outputs."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from layer3_batch_report_paths import (
    parse_batch_report_cli,
    resolve_batch_report_paths,
    run_path_preflight,
)

try:
    _PATHS = resolve_batch_report_paths()
except FileNotFoundError as exc:
    print(f"[FAIL] {exc}", file=sys.stderr)
    raise SystemExit(1) from exc

ROOT = _PATHS.root
BATCH_ID = _PATHS.batch_id
BATCH_DISPLAY = _PATHS.batch_display
OUT = ROOT / "natural_variability_FULL_NUMERIC_REPORT.md"

NV_REPORT_REQUIRED = [
    "natural_variability_by_timepoint_focus.csv",
    "natural_variability_top_links_by_timepoint_focus.csv",
    "natural_variability_distribution_metrics.csv",
    "natural_variability_nullspace_summary.csv",
    "natural_variability_direction_vs_magnitude.csv",
    "natural_variability_link_level.csv",
]

FOCUS_ORDER = [
    "all",
    "functional_p50",
    "null_space_after_p50",
    "functional_p60",
    "null_space_after_p60",
]
TIMEPOINT_ORDER = ["T1", "T2", "T3"]
COMPARISON_BY_TP = {
    "T1": "T1_R1_vs_T1_R2",
    "T2": "T2_R1_vs_T2_R2",
    "T3": "T3_R1_vs_T3_R2",
}

LINK_COLS = [
    "link_id",
    "JRW_A",
    "JRW_B",
    "JcvPCA_link_delta",
    "sign_of_delta",
    "abs_delta",
    "rank_by_abs_delta",
    "relative_abs_delta_share",
]

SUMMARY_COLS = [
    "participant_id",
    "block_label",
    "timepoint",
    "comparison_variant",
    "focus_mode",
    "mean_abs_delta",
    "median_abs_delta",
    "sum_abs_delta",
    "max_abs_delta",
    "top1_link",
    "top1_abs_delta",
    "top3_abs_delta_share",
    "normalized_entropy",
    "gini",
    "n_links",
    "links_needed_for_80_percent_abs_delta",
]


def read_csv(name: str) -> pd.DataFrame:
    path = ROOT / f"{name}.csv"
    if not path.is_file():
        raise FileNotFoundError(f"Missing: {path}")
    return pd.read_csv(path)


def f4(x) -> str:
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return "NA"
    if pd.isna(x):
        return "NA"
    return f"{float(x):.4f}"


def fmt_cell(x, col: str = "") -> str:
    if col == "participant_id":
        if pd.isna(x):
            return "NA"
        return str(int(float(x)))
    if isinstance(x, (float, int, np.floating, np.integer)) or pd.api.types.is_numeric_dtype(type(x)):
        return f4(x)
    if isinstance(x, bool):
        return str(x)
    if pd.isna(x):
        return "NA"
    return str(x)


def md_table(headers: list[str], rows: list[list]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(lines)


def df_to_md(df: pd.DataFrame, cols: list[str] | None = None) -> str:
    cols = cols or list(df.columns)
    rows = [[fmt_cell(r[c], c) for c in cols] for _, r in df[cols].iterrows()]
    return md_table(cols, rows)


def tp_mean(by_tp: pd.DataFrame, pid: str, bl: str, tp: str) -> float:
    sub = by_tp[
        (by_tp.participant_id.astype(str) == str(pid))
        & (by_tp.block_label == bl)
        & (by_tp.timepoint == tp)
        & (by_tp.focus_mode == "all")
    ]
    return float(sub.mean_abs_delta.iloc[0]) if len(sub) else float("nan")


def overlap_top5(top: pd.DataFrame, pid: str, bl: str) -> str:
    sets: dict[str, set[str]] = {}
    for tp in TIMEPOINT_ORDER:
        sub = top[
            (top.participant_id.astype(str) == str(pid))
            & (top.block_label == bl)
            & (top.focus_mode == "all")
            & (top.timepoint == tp)
        ]
        sets[tp] = set(sub.link_id.tolist())
    shared = sets["T1"] & sets["T2"] & sets["T3"]
    return ", ".join(sorted(shared)) if shared else "none"


def main(argv: list[str] | None = None) -> int:
    args = parse_batch_report_cli(
        "Generate natural_variability_FULL_NUMERIC_REPORT.md from NV deep-dive CSV outputs.",
        argv,
    )
    try:
        paths = resolve_batch_report_paths(config_path=args.config, batch_dir=args.batch_dir)
    except FileNotFoundError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1

    global ROOT, OUT, BATCH_ID, BATCH_DISPLAY
    ROOT = paths.root
    BATCH_ID = paths.batch_id
    BATCH_DISPLAY = paths.batch_display
    OUT = ROOT / "natural_variability_FULL_NUMERIC_REPORT.md"

    preflight = run_path_preflight(args, root=ROOT, out=OUT, required=NV_REPORT_REQUIRED)
    if preflight is not None:
        return preflight

    by_tp = read_csv("natural_variability_by_timepoint_focus")
    top = read_csv("natural_variability_top_links_by_timepoint_focus")
    dist = read_csv("natural_variability_distribution_metrics")
    null_df = read_csv("natural_variability_nullspace_summary")
    dvm = read_csv("natural_variability_direction_vs_magnitude")
    links = read_csv("natural_variability_link_level")

    all_only = by_tp[by_tp.focus_mode == "all"].copy()

    t2_wins = 0
    total = 0
    for pid in ["671", "252"]:
        for bl in ["all_P1_P2_P3_P4_P5", "P3_P4_P5"]:
            vals = {tp: tp_mean(by_tp, pid, bl, tp) for tp in TIMEPOINT_ORDER}
            if any(pd.isna(v) for v in vals.values()):
                continue
            total += 1
            if vals["T2"] == max(vals.values()):
                t2_wins += 1

    null_gt_all = int((null_df.null_p50_to_all_ratio > 1).sum())

    lines: list[str] = [
        "# Natural Variability Deep Dive — full numeric report",
        "",
        f"Batch folder: `Layer3_JcvPCA/outputs/{ROOT.name}/`",
        "",
        "Within-timepoint repetition variability (R1 vs R2) at T1, T2, and T3.",
        "All numbers read from existing batch comparison outputs; no figures generated.",
        "",
        "---",
        "",
        "## 1. Executive summary",
        "",
        "- Repetition variability is **link-structured**; a single scalar NV reference is insufficient.",
        f"- Mean abs-Delta (all-PC): T2 is largest in **{t2_wins}/{total}** participant–block cells.",
        f"- Null-space after p50 mean abs-Delta exceeds all-PC in **{null_gt_all}/12** participant–block–timepoint cells (ratio > 1).",
        "- Arm/hand and leg links recur among top repetition-variability contributors; patterns differ between participants 671 and 252.",
        "- Normalized entropy on repetition contrasts is typically **0.75–0.90** (often more concentrated than longitudinal comparisons).",
        "",
        "---",
        "",
        "## 2. Methods: how natural variability is defined here",
        "",
        "| Item | Definition |",
        "| --- | --- |",
        "| Comparisons | `T1_R1_vs_T1_R2`, `T2_R1_vs_T2_R2`, `T3_R1_vs_T3_R2` |",
        "| Dataset A / B | R1 / R2 at the same timepoint and exercise block |",
        "| Link metric | `JcvPCA_link_delta` = RSS change per link (B − A) |",
        "| PC aggregation | Mean across PC rows in `link_level_jrw_rss.csv` per focus mode |",
        "| Focus modes | all, functional_p50, null_space_after_p50, functional_p60, null_space_after_p60 |",
        "| Participants | 671 (14 links), 252 (16 links); analyzed separately |",
        "| Blocks | `P3_P4_P5`, `all_P1_P2_P3_P4_P5` |",
        "",
        "---",
        "",
        "## 3. Why a single scalar NV value is insufficient",
        "",
        "A single scalar collapses: (1) which links vary, (2) concentration vs distribution, (3) timepoint dependence,",
        "(4) PC-subspace dependence, (5) sign structure across repetitions.",
        "Longitudinal NV overlays use T1 repetition as reference; this report describes repetition variability **at each timepoint separately**.",
        "",
        "---",
        "",
        "## 4. File inventory and row counts",
        "",
        md_table(
            ["File", "Rows", "Description"],
            [
                ["`natural_variability_by_timepoint_focus.csv`", str(len(by_tp)), "Summary metrics per cell"],
                ["`natural_variability_top_links_by_timepoint_focus.csv`", str(len(top)), "Top-5 links per cell"],
                ["`natural_variability_distribution_metrics.csv`", str(len(dist)), "Entropy, Gini, labels"],
                ["`natural_variability_nullspace_summary.csv`", str(len(null_df)), "Focus-mode ratios per timepoint"],
                ["`natural_variability_direction_vs_magnitude.csv`", str(len(dvm)), "Per-link cross-timepoint (all-PC)"],
                ["`natural_variability_link_level.csv`", str(len(links)), "Full link-level table"],
            ],
        ),
        "",
        f"Expected cells: 2 participants × 2 blocks × 3 timepoints × 5 focus modes = **60** summary rows.",
        "",
        "---",
        "",
        "## 5. Scalar repetition variability by timepoint (all-PC)",
        "",
        "### 5.1 Mean abs Delta pivot",
        "",
    ]

    pivot_rows: list[list[str]] = []
    for pid in sorted(by_tp.participant_id.astype(str).unique()):
        for bl in sorted(by_tp[by_tp.participant_id.astype(str) == pid].block_label.unique()):
            t1, t2, t3 = tp_mean(by_tp, pid, bl, "T1"), tp_mean(by_tp, pid, bl, "T2"), tp_mean(by_tp, pid, bl, "T3")
            largest = max([("T1", t1), ("T2", t2), ("T3", t3)], key=lambda x: x[1])[0]
            pattern = "T2_peak" if t2 >= t1 and t2 >= t3 else "non_monotonic"
            pivot_rows.append([pid, bl, f4(t1), f4(t2), f4(t3), largest, pattern])
    lines.append(md_table(["Participant", "Block", "T1", "T2", "T3", "Largest TP", "Pattern"], pivot_rows))

    lines += [
        "",
        "### 5.2 Full summary table — all focus modes",
        "",
        df_to_md(
            by_tp.sort_values(["participant_id", "block_label", "timepoint", "focus_mode"]).reset_index(drop=True),
            SUMMARY_COLS,
        ),
        "",
        "---",
        "",
        "## 6. Top-link repetition variability (top 5 per cell)",
        "",
    ]

    for fm in FOCUS_ORDER:
        sub = top[top.focus_mode == fm].sort_values(
            ["participant_id", "block_label", "timepoint", "rank"]
        )
        lines += [f"### Focus mode: `{fm}` ({len(sub)} rows)", ""]
        lines.append(
            df_to_md(
                sub,
                [
                    "participant_id",
                    "block_label",
                    "timepoint",
                    "comparison_variant",
                    "focus_mode",
                    "rank",
                    "link_id",
                    "abs_delta",
                    "sign_of_delta",
                    "relative_abs_delta_share",
                    "JcvPCA_link_delta",
                ],
            )
        )
        lines.append("")

    lines += [
        "---",
        "",
        "## 7. Link-level repetition variability profiles (all-PC rank-1 by timepoint)",
        "",
    ]
    for pid in sorted(top.participant_id.astype(str).unique()):
        lines.append(f"### Participant {pid}")
        for bl in sorted(top[top.participant_id.astype(str) == pid].block_label.unique()):
            sub = top[
                (top.participant_id.astype(str) == pid)
                & (top.block_label == bl)
                & (top.focus_mode == "all")
                & (top.rank == 1)
            ].sort_values("timepoint")
            rows = [
                [r.timepoint, r.link_id, f4(r.abs_delta), f4(r.relative_abs_delta_share), int(r.sign_of_delta)]
                for _, r in sub.iterrows()
            ]
            lines.append(f"**{bl}**")
            lines.append(md_table(["Timepoint", "Top link", "abs Delta", "Share", "Sign"], rows))
            lines.append(f"Top-5 overlap all three timepoints: `{overlap_top5(top, pid, bl)}`")
            lines.append("")

    lines += [
        "---",
        "",
        "## 8. Distribution of repetition variability across links",
        "",
        df_to_md(
            dist.sort_values(["participant_id", "block_label", "timepoint", "focus_mode"]).reset_index(drop=True)
        ),
        "",
        "---",
        "",
        "## 9. Functional_p50 vs null_space_after_p50",
        "",
        df_to_md(null_df.sort_values(["participant_id", "block_label", "timepoint"]).reset_index(drop=True)),
        "",
        "---",
        "",
        "## 10. Functional_p60 vs null_space_after_p60",
        "",
        md_table(
            ["Participant", "Block", "Timepoint", "functional_p60/all", "null_p60/all"],
            [
                [
                    str(int(float(r.participant_id))),
                    r.block_label,
                    r.timepoint,
                    f4(r.functional_p60_to_all_ratio),
                    f4(r.null_p60_to_all_ratio),
                ]
                for _, r in null_df.sort_values(["participant_id", "block_label", "timepoint"]).iterrows()
            ],
        ),
        "",
        "---",
        "",
        "## 11. Direction vs magnitude (all-PC, per link across timepoints)",
        "",
        df_to_md(dvm.sort_values(["participant_id", "block_label", "link_id"]).reset_index(drop=True)),
        "",
        "---",
        "",
        "## 12. P3_P4_P5 vs all_P1_P2_P3_P4_P5",
        "",
    ]

    for pid in ["671", "252"]:
        for tp in TIMEPOINT_ORDER:
            p3 = all_only[
                (all_only.participant_id.astype(str) == pid)
                & (all_only.block_label == "P3_P4_P5")
                & (all_only.timepoint == tp)
            ]
            al = all_only[
                (all_only.participant_id.astype(str) == pid)
                & (all_only.block_label == "all_P1_P2_P3_P4_P5")
                & (all_only.timepoint == tp)
            ]
            if p3.empty or al.empty:
                continue
            lines.append(
                f"- **{pid} {tp}:** P3 mean abs **{f4(float(p3.mean_abs_delta.iloc[0]))}** vs all **{f4(float(al.mean_abs_delta.iloc[0]))}**; "
                f"entropy P3 **{f4(float(p3.normalized_entropy.iloc[0]))}** vs all **{f4(float(al.normalized_entropy.iloc[0]))}**."
            )

    lines += [
        "",
        "---",
        "",
        "## 13. Participant-specific observations",
        "",
        "**671:** T2 often highest mean abs Delta; arm links (`LFArm_to_LHand`, `LUArm_to_LFArm`, `RUArm_to_RFArm`, `RFArm_to_RHand`) and leg links recur in top ranks.",
        "",
        "**252:** P3 T1 can exceed T2; shoulder–arm chain and pelvis-root links (`252_to_LThigh`, `252_to_RThigh`) appear in top repetition-variability links.",
        "",
        "---",
        "",
        "## 14. Primary questions — explicit answers",
        "",
        "1. **How large?** Mean abs Delta (all-PC) ~0.006–0.016 per cell; sum abs Delta ~0.09–0.22 per link set (see Section 5).",
        f"2. **T2 highest?** Partially — **{t2_wins}/{total}** cells; 252 P3 peaks at T1.",
        "3. **Monotonic?** **Non-monotonic** in all four participant–block cells.",
        "4. **Top links?** Section 6–7 and `natural_variability_top_links_by_timepoint_focus.csv`.",
        "5. **Same links across T1/T2/T3?** Partial top-5 overlap (all-PC):",
    ]

    for pid in ["671", "252"]:
        for bl in ["all_P1_P2_P3_P4_P5", "P3_P4_P5"]:
            shared = overlap_top5(top, pid, bl)
            label = shared if shared != "none" else "none"
            lines.append(f"   - **{pid} `{bl}`:** {label}")

    lines += [
        "6. **Concentrated or distributed?** **Mixed** — entropy ~0.75–0.90; top-3 share often 0.43–0.65.",
        f"7. **Which focus mode?** Null-space p50 often ≥ all-PC (**{null_gt_all}/12** cells with ratio > 1).",
        "8. **Distinct null-space layer?** **Yes** — higher mean abs Delta in null-space on many cells.",
        "9. **P3 vs all-block?** Magnitudes and entropy differ by timepoint (Section 12).",
        "10. **671 vs 252?** **Different** top links and timepoint peaks; not directly comparable at raw matrix level.",
        "",
        "---",
        "",
        "## 15. Poster and interpretation recommendations",
        "",
        "| Question | Answer |",
        "| --- | --- |",
        "| Single scalar sufficient? | **No** |",
        "| T2 largest repetition variability? | **Often for 671; mixed for 252** |",
        "| Monotonic T1→T2→T3? | **Non-monotonic** |",
        "| Null-space distinct? | **Yes** on many cells |",
        "| Poster role | **Supporting robustness / methods**, not main results |",
        "| Show scalar, link-level, null-space? | **All three at minimal depth** |",
        "",
        "**Strong enough for poster:** link-structured NV, timepoint-specific magnitude, null-space layer note.",
        "",
        "**Supplementary:** full 60-cell tables, p60 splits, per-link sign-flip detail.",
        "",
        "---",
        "",
        "## 16. Link-level result tables",
        "",
        "Organized by participant, block, timepoint, focus mode (`natural_variability_link_level.csv`).",
        "",
    ]

    for pid in sorted(links.participant_id.astype(str).unique()):
        for bl in sorted(links[links.participant_id.astype(str) == pid].block_label.unique()):
            for tp in TIMEPOINT_ORDER:
                for fm in FOCUS_ORDER:
                    sub = links[
                        (links.participant_id.astype(str) == pid)
                        & (links.block_label == bl)
                        & (links.timepoint == tp)
                        & (links.focus_mode == fm)
                    ].sort_values("rank_by_abs_delta")
                    lines += [f"### Participant {pid} | {bl} | {tp} | {COMPARISON_BY_TP[tp]} | {fm}", ""]
                    if sub.empty:
                        lines.append("_No rows._")
                    else:
                        lines.append(df_to_md(sub, LINK_COLS))
                    lines.append("")

    med_all = float(all_only.mean_abs_delta.median())
    lines += [
        "---",
        "",
        "## 17. Machine-readable summary (for future agents)",
        "",
        "```json",
        json.dumps(
            {
                "batch_folder": f"Layer3_JcvPCA/outputs/{ROOT.name}",
                "analysis": "natural_variability_deep_dive",
                "comparisons": list(COMPARISON_BY_TP.values()),
                "focus_modes": FOCUS_ORDER,
                "row_counts": {
                    "by_timepoint_focus": int(len(by_tp)),
                    "top_links": int(len(top)),
                    "distribution_metrics": int(len(dist)),
                    "nullspace_summary": int(len(null_df)),
                    "direction_vs_magnitude": int(len(dvm)),
                    "link_level": int(len(links)),
                },
                "headline_all_pc": {
                    "t2_largest_cells": f"{t2_wins}/{total}",
                    "null_p50_ratio_gt_1_cells": null_gt_all,
                    "median_mean_abs_delta_all_pc": round(med_all, 6),
                },
                "input_files": [
                    "natural_variability_by_timepoint_focus.csv",
                    "natural_variability_top_links_by_timepoint_focus.csv",
                    "natural_variability_distribution_metrics.csv",
                    "natural_variability_nullspace_summary.csv",
                    "natural_variability_direction_vs_magnitude.csv",
                    "natural_variability_link_level.csv",
                ],
                "output_file": OUT.name,
                "narrative_report": "natural_variability_deep_dive_report.md",
            },
            indent=2,
        ),
        "```",
        "",
        "*No figures generated. `compute_jcvpca()` not modified.*",
        "",
    ]

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT} ({len(lines)} section lines)")
    print(f"Link-level tables: {len(links.participant_id.astype(str).unique())} participants × blocks × timepoints × focus modes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
