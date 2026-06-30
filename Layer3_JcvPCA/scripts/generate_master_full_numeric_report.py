#!/usr/bin/env python3
"""Generate Gaga_JcvPCA_MASTER_full_numeric_report.md from batch outputs."""

from __future__ import annotations

import ast
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
OUT = ROOT / "Gaga_JcvPCA_MASTER_full_numeric_report.md"

BATCH_ARTIFACTS = [
    ("comparison_status.csv", "Primary comparison registry (all-PC)"),
    ("selected_m_by_comparison.csv", "selected_m per comparison"),
    ("pca_stability_by_comparison.csv", "PCA readiness / stability diagnostics"),
    ("jcvpca_link_results.csv", "Primary link-level JcvPCA (all focus modes / PCs)"),
    ("jcvpca_axis_results.csv", "Primary axis-level JcvPCA"),
    ("nv_baseline_results.csv", "Natural Variability baseline comparisons"),
    ("jcvpca_link_results_by_pc_focus.csv", "Active PC-focus link results (p50/p60)"),
    ("jcvpca_axis_results_by_pc_focus.csv", "Active PC-focus axis results (p50/p60)"),
    ("jcvpca_link_results_by_pc_focus_archived_p2.csv", "Archived p2 PC-focus link results"),
    ("jcvpca_link_results_by_pc_focus_p50_p60.csv", "p50/p60 sensitivity sidecar link results"),
    ("pc_focus_by_comparison.csv", "PC sets by focus mode"),
    ("pc_focus_p50_p60_by_comparison.csv", "Variance-informed p50/p60 thresholds"),
    ("pc_focus_p50_p60_vs_p2_comparison.csv", "p50/p60 vs archived p2 contrasts"),
    ("pc_focus_p50_vs_p60_comparison.csv", "p50 vs p60 contrasts"),
    ("link_contribution_distribution.csv", "Per-link contribution shares (comparison-delta)"),
    ("contribution_evenness_summary.csv", "Evenness metrics (comparison-delta)"),
    ("contribution_evenness_summary_p50_p60.csv", "Evenness metrics (p50/p60 sidecar)"),
    ("low_contribution_links.csv", "Low relative contribution links"),
    ("block_evenness_comparison.csv", "Block-level evenness contrast"),
    ("pc_focus_evenness_comparison.csv", "PC-focus vs all-PC evenness contrast"),
    ("timepoint_evenness_summary.csv", "Timepoint-state evenness summary"),
    ("timepoint_evenness_trends.csv", "Timepoint evenness trends T1–T3"),
    ("timepoint_link_contribution_distribution.csv", "Timepoint link contribution distribution"),
    ("timepoint_vs_comparison_evenness.csv", "Timepoint vs comparison evenness contrast"),
    ("top_links_by_focus_mode.csv", "Top links by focus mode"),
    ("joint_heatmap_link_mapping.csv", "Canonical link-to-joint mapping"),
    ("joint_heatmap_scores_poster_subset.csv", "Derived joint scores (poster subset)"),
    ("joint_heatmap_region_summary.csv", "Derived body-region joint summaries"),
    ("plot_index.csv", "Indexed plot paths"),
]

MASTER_REQUIRED = [name for name, _ in BATCH_ARTIFACTS]


def md_table(headers: list[str], rows: list[list]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(lines)


def f4(x) -> str:
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return "NA"
    if pd.isna(x):
        return "NA"
    return f"{float(x):.4f}"


def df_rows(df: pd.DataFrame, cols: list[str] | None = None, fmt: dict[str, str] | None = None) -> list[list]:
    cols = cols or list(df.columns)
    fmt = fmt or {}
    rows = []
    for _, r in df[cols].iterrows():
        rows.append([fmt.get(c, str)(r[c]) if c in fmt else (f4(r[c]) if isinstance(r[c], (float, int, np.floating, np.integer)) or pd.api.types.is_numeric_dtype(type(r[c])) else str(r[c])) for c in cols])
    return rows


def read_csv(name: str) -> pd.DataFrame:
    path = ROOT / name
    if path.suffix != ".csv":
        path = ROOT / f"{name}.csv"
    return pd.read_csv(path)


def link_agg_mean(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby(["participant_id", "block_label", "comparison_label", "link_id"], as_index=False)
        .agg(
            JRW_A_link=("JRW_A_link", "mean"),
            JRW_B_link=("JRW_B_link", "mean"),
            JcvPCA_link=("JcvPCA_link", "mean"),
        )
        .sort_values(["participant_id", "block_label", "comparison_label", "link_id"])
    )


def comparison_sort(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["participant_id"] = df["participant_id"].astype(str)
    return df.sort_values(["participant_id", "block_label", "comparison_label"])


def load_pca_explained_variance(comparison_key: str) -> pd.DataFrame | None:
    path = ROOT / "comparisons" / comparison_key / "run" / "pca_A_explained_variance.csv"
    if not path.is_file():
        return None
    ev = pd.read_csv(path)
    ev["comparison_key"] = comparison_key
    return ev


def metrics_dict(raw: str) -> dict:
    try:
        return ast.literal_eval(raw)
    except Exception:
        return {}


def section_link_table(all_links: pd.DataFrame, pid: str, bl: str, cl: str, focus: str = "all") -> list[str]:
    sub = all_links[
        (all_links.participant_id.astype(str) == pid)
        & (all_links.block_label == bl)
        & (all_links.comparison_label == cl)
        & (all_links.focus_mode == focus)
    ]
    if sub.empty:
        return [f"### {pid} — {bl} — {cl} — {focus}", "", "No rows.", ""]
    agg = link_agg_mean(sub)
    sel = read_csv("selected_m_by_comparison.csv")
    sm = sel[sel.comparison_key.str.contains(f"{pid}_") & sel.comparison_key.str.endswith(cl.replace("T1_vs_T2", "L1_T1_vs_T2").replace("T1_vs_T3", "L2_T1_vs_T3").replace("T1_R1_vs_T2", "I_T1_R1_vs_T2").replace("T2_R1_vs_R2", "I_T2_R1_vs_R2").replace("T3_R1_vs_R2", "I_T3_R1_vs_R2"))]
    # simpler lookup via status merge
    status = read_csv("comparison_status.csv")
    st = status[(status.participant_id.astype(str) == pid) & (status.block_label == bl) & (status.comparison_label == cl)]
    selected_m = st.iloc[0].selected_m if len(st) else "NA"
    lines = [
        f"### {pid} — {bl} — {cl} — {focus} (link-level, mean across selected PCs)",
        "",
        f"selected_m: **{selected_m}**. Values are mean `JcvPCA_link` across included PCs.",
        "",
        md_table(
            ["Link", "JRW_A", "JRW_B", "JcvPCA_link (Delta)"],
            [[r.link_id, f4(r.JRW_A_link), f4(r.JRW_B_link), f4(r.JcvPCA_link)] for _, r in agg.iterrows()],
        ),
        "",
    ]
    return lines


def main(argv: list[str] | None = None) -> int:
    args = parse_batch_report_cli(
        "Generate Gaga_JcvPCA_MASTER_full_numeric_report.md from batch outputs.",
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
    OUT = ROOT / "Gaga_JcvPCA_MASTER_full_numeric_report.md"

    preflight = run_path_preflight(args, root=ROOT, out=OUT, required=MASTER_REQUIRED)
    if preflight is not None:
        return preflight

    status = comparison_sort(read_csv("comparison_status.csv"))
    status = status[status.focus_mode == "all"].reset_index(drop=True)
    selected_m = read_csv("selected_m_by_comparison.csv")
    pca_stab = read_csv("pca_stability_by_comparison.csv")
    all_links = read_csv("jcvpca_link_results.csv")
    all_links["participant_id"] = all_links["participant_id"].astype(str)
    nv = read_csv("nv_baseline_results.csv")
    nv["participant_id"] = nv["participant_id"].astype(str)
    pc_focus = read_csv("jcvpca_link_results_by_pc_focus.csv")
    pc_focus["participant_id"] = pc_focus["participant_id"].astype(str)
    p2_arch = read_csv("jcvpca_link_results_by_pc_focus_archived_p2.csv")
    p2_arch["participant_id"] = p2_arch["participant_id"].astype(str)
    p50cfg = comparison_sort(read_csv("pc_focus_p50_p60_by_comparison.csv"))
    vs_p2 = comparison_sort(read_csv("pc_focus_p50_p60_vs_p2_comparison.csv"))
    vs_p60 = comparison_sort(read_csv("pc_focus_p50_vs_p60_comparison.csv"))
    pc_sets = read_csv("pc_focus_by_comparison.csv")
    even = comparison_sort(read_csv("contribution_evenness_summary.csv"))
    even["participant_id"] = even["participant_id"].astype(str)
    lcd = read_csv("link_contribution_distribution.csv")
    lcd["participant_id"] = lcd["participant_id"].astype(str)
    low = read_csv("low_contribution_links.csv")
    low["participant_id"] = low["participant_id"].astype(str)
    block_ev = read_csv("block_evenness_comparison.csv")
    pc_ev = read_csv("pc_focus_evenness_comparison.csv")
    tp_sum = read_csv("timepoint_evenness_summary.csv")
    tp_trend = read_csv("timepoint_evenness_trends.csv")
    tp_lcd = read_csv("timepoint_link_contribution_distribution.csv")
    tp_vs = read_csv("timepoint_vs_comparison_evenness.csv")
    top_links = comparison_sort(read_csv("top_links_by_focus_mode.csv"))
    top_links["participant_id"] = top_links["participant_id"].astype(str)
    plot_idx = read_csv("plot_index.csv")

    joint_map = read_csv("joint_heatmap_link_mapping.csv") if (ROOT / "joint_heatmap_link_mapping.csv").is_file() else pd.DataFrame()
    joint_poster = read_csv("joint_heatmap_scores_poster_subset.csv") if (ROOT / "joint_heatmap_scores_poster_subset.csv").is_file() else pd.DataFrame()
    joint_region = read_csv("joint_heatmap_region_summary.csv") if (ROOT / "joint_heatmap_region_summary.csv").is_file() else pd.DataFrame()

    lines: list[str] = [
        "# Gaga JcvPCA Master Full Numeric Report",
        "",
        f"Batch folder: `Layer3_JcvPCA/outputs/{ROOT.name}/`",
        "",
        "Consolidated numerical report for external agents and research partners. No JcvPCA rerun was performed.",
        "",
        "## Result-level definitions",
        "",
        md_table(
            ["Level", "Description"],
            [
                ["link-level", "Raw JcvPCA output at anatomical link granularity"],
                ["joint-level", "Derived visualization summary from incident link aggregation"],
                ["body-region level", "Derived aggregation of joint-level scores"],
                ["timepoint-state evenness", "State-level PCA loading distribution at T1/T2/T3"],
                ["comparison-delta evenness", "Distribution of abs(JcvPCA_link) within a comparison"],
            ],
        ),
        "",
        "## Analysis hierarchy",
        "",
        md_table(
            ["Tier", "Focus modes", "Role"],
            [
                ["Primary result", "all selected PCs", "Main JcvPCA link-level outputs"],
                ["Main sensitivity", "functional_p50 / null_space_after_p50", "Variance-informed PC split at ~50% cumulative variance"],
                ["Optional sensitivity", "functional_p60 / null_space_after_p60", "Stricter split at ~60% cumulative variance"],
                ["Archived exploratory", "functional_p2 / null_space_p2", "Retained for comparison; not main interpretation"],
            ],
        ),
        "",
        "---",
        "",
        "## 1. Batch integrity and file inventory",
        "",
        f"- Comparisons completed (all-PC): **{len(status)}**",
        f"- Participants: **671**, **252** (separate feature schemas; within-participant analysis only)",
        f"- p50/p60 focus comparisons configured: **{len(p50cfg)}**",
        "",
        "### Key batch artifacts",
        "",
        md_table(
            ["File", "Purpose", "Rows", "Present"],
            [
                [name, purpose, str(len(read_csv(name))) if (ROOT / name).is_file() else "—", "yes" if (ROOT / name).is_file() else "no"]
                for name, purpose in BATCH_ARTIFACTS
            ],
        ),
        "",
        "### Integrity checks",
        "",
        md_table(
            ["Check", "Expected", "Observed", "Status"],
            [
                ["Main all-PC comparisons", "20", str(len(status)), "OK" if len(status) == 20 else "CHECK"],
                ["NV baseline link rows", "120", str(len(nv)), "OK" if len(nv) == 120 else "CHECK"],
                ["Evenness summary rows (5 focus × 20)", "100", str(len(even)), "OK" if len(even) == 100 else "CHECK"],
                ["Timepoint evenness summary", "12", str(len(tp_sum)), "OK" if len(tp_sum) == 12 else "CHECK"],
                ["p50/p60 config rows", "20", str(len(p50cfg)), "OK" if len(p50cfg) == 20 else "CHECK"],
                ["Joint heatmap poster subset", "120", str(len(joint_poster)), "OK" if len(joint_poster) == 120 else ("NA" if joint_poster.empty else "CHECK")],
            ],
        ),
        "",
        "---",
        "",
        "## 2. Participant / schema summary",
        "",
    ]

    schema_rows = []
    comp_links = read_csv("comparable_links_by_comparison.csv")
    for pid in ["671", "252"]:
        r = status[status.participant_id == pid].iloc[0]
        n_links = len(comp_links[comp_links.participant_id.astype(str) == pid].link_stem.unique())
        schema_rows.append([
            pid, n_links, r.n_pca_features, r.feature_schema_id,
            "252 includes pelvis-root links 252_to_LThigh, 252_to_RThigh; 671 has no pelvis-root links",
        ])
    lines.append(md_table(["Participant", "Links", "Features", "Schema ID", "Notes"], schema_rows))
    lines += ["", ""]

    # Section 3
    lines += ["## 3. selected_m and PCA explained-variance summary", ""]
    sm_rows = []
    for _, r in selected_m.iterrows():
        sm_rows.append([
            r.comparison_key, int(r.selected_m), f4(r.cumulative_variance_at_selected_m),
            r.selected_m_reason[:80] + ("..." if len(str(r.selected_m_reason)) > 80 else ""),
        ])
    lines.append(md_table(["Comparison key", "selected_m", "Cumulative variance at selected_m", "Selection reason"], sm_rows))
    lines += ["", "### PCA explained variance (Dataset A reference frame, first PCs)", ""]
    ev_rows = []
    for _, r in status.iterrows():
        ck = r.comparison_key if "comparison_key" in status.columns else f"{r.participant_id}_{r.block_id}_{r.comparison_id}"
        ev = load_pca_explained_variance(ck)
        if ev is None:
            continue
        top = ev.head(8)
        pcs = "; ".join(f"PC{int(x.pc)}={f4(x.explained_variance_ratio)}" for _, x in top.iterrows())
        m = metrics_dict(pca_stab[(pca_stab.comparison_key == ck) & (pca_stab.dataset_side == "A")].iloc[0].metrics) if len(pca_stab[(pca_stab.comparison_key == ck) & (pca_stab.dataset_side == "A")]) else {}
        ev_rows.append([
            ck, int(r.selected_m), f4(m.get("dominant_pc_variance_percent", np.nan)),
            f4(m.get("split_half_pc_similarity", np.nan)), pcs,
        ])
    lines.append(md_table(["Comparison", "selected_m", "PC1 variance share", "Split-half PC similarity", "PC1–PC8 explained variance"], ev_rows))
    lines += ["", "---", "", "## 4. All-PC JcvPCA link-level Delta results (primary)", ""]
    lines.append("Link-level raw JcvPCA. Tables show mean `JcvPCA_link` across all selected PCs per link.")
    lines.append("")
    for _, r in status.iterrows():
        lines.extend(section_link_table(all_links, r.participant_id, r.block_label, r.comparison_label, "all"))

    # Section 5 NV full
    lines += ["---", "", "## 5. Natural Variability comparisons", ""]
    nv_cols = ["participant_id", "comparison_id", "block_id", "link_id", "main_abs_delta_jrw", "nv_abs_delta_jrw", "main_minus_nv", "ratio", "exceeds_nv"]
    nv_show = nv[nv_cols].sort_values(["participant_id", "block_id", "comparison_id", "link_id"])
    lines.append(md_table(nv_cols, df_rows(nv_show, nv_cols)))
    lines += ["", "---", "", "## 6. Repetition-level comparison summaries", ""]
    rep_rows = []
    for pid in ["671", "252"]:
        for bl in ["all_P1_P2_P3_P4_P5", "P3_P4_P5"]:
            for cl in ["T1_R1_vs_T1_R2", "T2_R1_vs_T2_R2", "T3_R1_vs_T3_R2"]:
                df = all_links[(all_links.participant_id == pid) & (all_links.block_label == bl) & (all_links.comparison_label == cl) & (all_links.focus_mode == "all")]
                if df.empty:
                    continue
                agg = link_agg_mean(df)
                mad = float(agg.JcvPCA_link.abs().mean())
                top_pos = agg.loc[agg.JcvPCA_link.idxmax()]
                top_neg = agg.loc[agg.JcvPCA_link.idxmin()]
                rep_rows.append([
                    pid, bl, cl, f4(mad), top_pos.link_id, f4(top_pos.JcvPCA_link),
                    top_neg.link_id, f4(top_neg.JcvPCA_link), "within-timepoint repetition",
                ])
    lines.append(md_table(
        ["Participant", "Block", "Comparison", "Mean abs Delta", "Top positive link", "Delta", "Top negative link", "Delta", "Notes"],
        rep_rows,
    ))

    # Section 7 PC-focus
    lines += [
        "",
        "---",
        "",
        "## 7. PC-focus sensitivity results",
        "",
        "### 7A. Variance-informed thresholds (p50 / p60)",
        "",
        md_table(
            ["Participant", "Block", "Comparison", "selected_m", "p50", "Var@p50", "p60", "Var@p60", "Null p50", "Null p60"],
            [
                [
                    r.participant_id, r.block_label, r.comparison_label, int(r.selected_m),
                    int(r.p50), f4(r.cumulative_variance_at_p50), int(r.p60), f4(r.cumulative_variance_at_p60),
                    "yes" if r.null_space_p50_available else "no",
                    "yes" if r.null_space_p60_available else "no",
                ]
                for _, r in p50cfg.iterrows()
            ],
        ),
        "",
        "### 7B. Top links by focus mode (link-level summary)",
        "",
    ]
    tl_cols = ["participant_id", "block_label", "comparison_label", "focus_mode", "sensitivity_tier", "top_positive_links", "top_negative_links", "mean_abs_delta", "normalized_entropy", "top_3_share"]
    lines.append(md_table(tl_cols, df_rows(top_links, tl_cols, {"mean_abs_delta": f4, "normalized_entropy": f4, "top_3_share": f4})))

    lines += ["", "### 7C. Archived p2 vs p50/p60 rank contrasts", ""]
    vp2_cols = ["participant_id", "block_label", "comparison_label", "focus_a", "focus_b", "rank_correlation", "mean_abs_delta_a", "mean_abs_delta_b", "normalized_entropy_a", "normalized_entropy_b"]
    lines.append(md_table(vp2_cols, df_rows(vs_p2, vp2_cols, {c: f4 for c in vp2_cols if c not in {"participant_id", "block_label", "comparison_label", "focus_a", "focus_b"}})))

    lines += ["", "### 7D. p50 vs p60 contrasts", ""]
    vp60_cols = ["participant_id", "block_label", "comparison_label", "comparison_kind", "focus_a", "focus_b", "rank_correlation", "mean_abs_rank_shift", "substantial_rank_shift_links"]
    lines.append(md_table(vp60_cols, df_rows(vs_p60, vp60_cols, {"rank_correlation": f4, "mean_abs_rank_shift": f4})))

    lines += ["", "### 7E. Archived p2 link-level Delta tables (exploratory)", ""]
    for _, r in status.iterrows():
        sub = p2_arch[
            (p2_arch.participant_id == r.participant_id)
            & (p2_arch.block_label == r.block_label)
            & (p2_arch.comparison_label == r.comparison_label)
        ]
        if sub.empty:
            continue
        for fm in ["functional_p2", "null_space_p2"]:
            fm_sub = sub[sub.focus_mode == fm]
            if fm_sub.empty:
                continue
            agg = link_agg_mean(fm_sub)
            lines.append(f"#### {r.participant_id} — {r.block_label} — {r.comparison_label} — {fm}")
            lines.append("")
            lines.append(md_table(
                ["Link", "JRW_A", "JRW_B", "JcvPCA_link"],
                [[x.link_id, f4(x.JRW_A_link), f4(x.JRW_B_link), f4(x.JcvPCA_link)] for _, x in agg.iterrows()],
            ))
            lines.append("")

    lines += ["", "### 7F. Main / optional sensitivity link-level tables (mean across included PCs)", ""]
    for _, r in status.iterrows():
        for fm in ["functional_p50", "null_space_after_p50", "functional_p60", "null_space_after_p60"]:
            sub = pc_focus[
                (pc_focus.participant_id == r.participant_id)
                & (pc_focus.block_label == r.block_label)
                & (pc_focus.comparison_label == r.comparison_label)
                & (pc_focus.focus_mode == fm)
            ]
            if sub.empty:
                continue
            agg = link_agg_mean(sub)
            lines.append(f"#### {r.participant_id} — {r.block_label} — {r.comparison_label} — {fm}")
            lines.append("")
            lines.append(md_table(
                ["Link", "JRW_A", "JRW_B", "JcvPCA_link"],
                [[x.link_id, f4(x.JRW_A_link), f4(x.JRW_B_link), f4(x.JcvPCA_link)] for _, x in agg.iterrows()],
            ))
            lines.append("")

    # Section 8 evenness
    lines += ["---", "", "## 8. Link contribution distribution metrics (comparison-delta evenness)", ""]
    ev_cols = ["participant_id", "block_label", "comparison_label", "focus_mode", "normalized_entropy", "gini_concentration", "top_1_share", "top_3_share", "top_5_share", "links_for_50pct", "links_for_80pct", "n_low_relative_contribution"]
    fmt_ev = {c: f4 for c in ev_cols if c.endswith("share") or c in {"normalized_entropy", "gini_concentration"}}
    lines.append(md_table(ev_cols, df_rows(even, ev_cols, fmt_ev)))
    lines += ["", "### Per-link contribution distribution (comparison-delta, full table)", ""]
    lcd_cols = ["participant_id", "block_label", "comparison_label", "focus_mode", "link_id", "abs_delta", "p_link", "below_p25", "below_p02"]
    lines.append(md_table(lcd_cols, df_rows(lcd.sort_values(["participant_id", "block_label", "comparison_label", "focus_mode", "link_id"]), lcd_cols, {"abs_delta": f4, "p_link": f4})))
    lines += ["", "### Block-level evenness contrast (P3_P4_P5 vs all block)", ""]
    be_cols = list(block_ev.columns)
    lines.append(md_table(be_cols, df_rows(block_ev, be_cols, {c: f4 for c in be_cols if block_ev[c].dtype.kind in "fi"})))
    lines += ["", "### PC-focus vs all-PC evenness contrast", ""]
    pe_cols = list(pc_ev.columns)
    lines.append(md_table(pe_cols, df_rows(pc_ev, pe_cols, {c: f4 for c in pe_cols if pc_ev[c].dtype.kind in "fi"})))
    lines += ["", "### Low relative contribution links (full table)", ""]
    low_cols = ["participant_id", "block_label", "comparison_label", "focus_mode", "link_id", "abs_delta", "p_link", "below_p25", "below_p02"]
    lines.append(md_table(low_cols, df_rows(low, low_cols, {"abs_delta": f4, "p_link": f4})))

    # Section 9 timepoint
    lines += ["", "---", "", "## 9. Timepoint-level evenness (T1, T2, T3)", ""]
    tp_cols = ["participant_id", "block_label", "timepoint", "selected_m", "normalized_entropy", "gini_concentration", "top_1_share", "top_3_share", "top_5_share", "links_for_80pct"]
    lines.append(md_table(tp_cols, df_rows(tp_sum, tp_cols, {c: f4 for c in tp_cols if c not in {"participant_id", "block_label", "timepoint"}})))
    lines += ["", "### Timepoint trends", ""]
    tr_cols = list(tp_trend.columns)
    lines.append(md_table(tr_cols, df_rows(tp_trend, tr_cols, {c: f4 for c in tr_cols if tp_trend[c].dtype.kind in "fi"})))
    lines += ["", "### Timepoint link contribution distribution (full)", ""]
    tpl_cols = ["participant_id", "block_label", "timepoint", "link_id", "link_contribution", "p_link", "below_p25", "below_p02", "rank_by_contribution"]
    tpl_sub = read_csv("timepoint_link_contribution_distribution")
    tpl_sub = tpl_sub.sort_values(["participant_id", "block_label", "timepoint", "rank_by_contribution"])
    lines.append(md_table(tpl_cols, df_rows(tpl_sub, tpl_cols, {"link_contribution": f4, "p_link": f4})))
    lines += ["", "### Timepoint vs comparison evenness contrast", ""]
    tv_cols = list(tp_vs.columns)
    lines.append(md_table(tv_cols, df_rows(tp_vs, tv_cols, {c: f4 for c in tv_cols if tp_vs[c].dtype.kind in "fi"})))

    # Section 10 body region from joint heatmap
    lines += ["", "---", "", "## 10. Body-region summaries (derived joint-level aggregation)", ""]
    if not joint_region.empty:
        jr_all = joint_region[joint_region.focus_mode == "all"].sort_values(["participant", "block_label", "comparison_label", "region_rank"])
        jr_cols = ["participant", "block_label", "comparison_label", "focus_mode", "region", "region_sum_joint_abs_score", "region_mean_joint_abs_score", "region_relative_share", "region_rank"]
        lines.append("Derived from link-level JcvPCA via joint aggregation. Not raw JcvPCA output.")
        lines.append("")
        lines.append(md_table(jr_cols, df_rows(jr_all, jr_cols)))
    else:
        lines.append("Joint heatmap region summary not available.")

    # Section 11 joint heatmap
    lines += ["", "---", "", "## 11. Anatomical joint-heatmap derived tables", ""]
    lines.append("Joint-level scores are **derived joint-level visualization summaries from link-level JcvPCA outputs**.")
    lines.append("")
    if not joint_map.empty:
        lines.append("### Link-to-joint mapping")
        lines.append("")
        jm_cols = list(joint_map.columns)
        lines.append(md_table(jm_cols, df_rows(joint_map, jm_cols)))
    if not joint_poster.empty:
        lines += ["", "### Poster-subset joint scores (full)", ""]
        jp_cols = ["participant", "block_label", "comparison_label", "focus_mode", "joint_name", "region", "joint_abs_score", "joint_signed_score", "joint_abs_score_norm_0_1", "joint_rank", "incident_links"]
        lines.append(md_table(jp_cols, df_rows(joint_poster, jp_cols, {"joint_abs_score": f4, "joint_signed_score": f4, "joint_abs_score_norm_0_1": f4})))
    if joint_poster.empty and joint_map.empty:
        lines.append("Joint heatmap tables not available in this batch folder.")

    # Section 12 poster shortlist
    lines += ["", "---", "", "## 12. Poster / report plot shortlist", ""]
    poster_md = ROOT / "poster_plot_shortlist.md"
    if poster_md.is_file():
        for ln in poster_md.read_text(encoding="utf-8").splitlines():
            if ln.startswith("# Poster"):
                continue
            lines.append(ln)
    else:
        primary_plots = plot_idx[plot_idx.focus_mode == "all"].head(20)
        lines.append(md_table(["Participant", "Block", "Comparison", "Plot"], df_rows(primary_plots, ["participant_id", "block_label", "comparison_id", "plot_path"])))

    # Section 13 interpretation
    med_ent_all = float(even[even.focus_mode == "all"].normalized_entropy.median())
    lines += [
        "",
        "---",
        "",
        "## 13. Final interpretation summary",
        "",
        "- **Primary link-level pattern (all-PC):** Upper-limb links (especially forearm/hand segments) often carry larger numeric `JcvPCA_link` magnitudes in longitudinal comparisons; patterns vary by participant, block, and comparison.",
        f"- **Comparison-delta evenness:** Median normalized entropy across all-PC comparisons is **{f4(med_ent_all)}** (0–1 scale; higher = more evenly distributed abs-delta shares). Link contributions are generally broadly distributed rather than dominated by a single link.",
        "- **Natural Variability:** Longitudinal comparisons show a mix of links inside and outside descriptive NV reference intervals; NV is a descriptive reference, not a hypothesis test.",
        "- **Repetition comparisons:** Within-timepoint repetition comparisons show timepoint-specific top links and mean abs Delta profiles.",
        "- **PC-focus sensitivity:** functional_p50 and null_space_after_p50 produce different link-ranking patterns from all-PC and from archived p2; null_space_after_p50 is less rank-similar to all-PC than archived null_space_p2 in many comparisons.",
        "- **Timepoint evenness:** Participant 671 shows clearer T2 evenness shifts than 252; timepoint-state evenness and comparison-delta evenness measure different quantities.",
        "- **Derived joint heatmaps:** Joint-level scores broadly mirror link-level upper-limb emphasis; core/proximal joints vary in rank; 252 includes additional hip representation via pelvis-root links.",
        "- **Visualization suitability:** Link-level tables are primary; joint-level and body-region tables are suitable for anatomical heatmap visualization when labeled as derived summaries.",
        "",
    ]

    # Section 14 limitations
    lines += [
        "## 14. Limitations and cautions",
        "",
        "- Link-level JcvPCA is the primary algorithm output; joint-level and body-region values are derived aggregations.",
        "- Link-to-joint mapping may smooth or redistribute link-level patterns.",
        "- Participants 671 and 252 use different link schemas (671 lacks pelvis-root links).",
        "- Cross-participant raw comparison is not supported.",
        "- PC-focus modes partition variance differently; archived p2 captured <50% Dataset A variance and is not the main null-space reference.",
        "- Normalized entropy, Gini, and joint normalized scores are descriptive distribution metrics for visualization and audit.",
        "- NV intervals are descriptive baselines only.",
        "- No causal, clinical, treatment, or condition-specific claims are supported by these numerical tables alone.",
        "",
    ]

    # Section 15 machine summary
    lines += [
        "## 15. Machine-readable summary for future agents",
        "",
        md_table(
            ["Field", "Value"],
            [
                ["Batch folder", ROOT.name],
                ["Master report", "Gaga_JcvPCA_MASTER_full_numeric_report.md"],
                ["Primary link table", "jcvpca_link_results.csv (focus_mode=all)"],
                ["Primary result level", "link-level"],
                ["Primary focus mode", "all selected PCs"],
                ["Main sensitivity", "functional_p50 / null_space_after_p50"],
                ["Optional sensitivity", "functional_p60 / null_space_after_p60"],
                ["Archived exploratory", "functional_p2 / null_space_p2"],
                ["Comparisons (all-PC)", str(len(status))],
                ["Participants", "671, 252"],
                ["Joint heatmap tables", "yes" if not joint_poster.empty else "no"],
                ["No JcvPCA rerun", "yes"],
                ["Recommended use", "External numerical review, figure planning, derived heatmap visualization"],
            ],
        ),
        "",
    ]

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT} ({len(lines)} markdown lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
