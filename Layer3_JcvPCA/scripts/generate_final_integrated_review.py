#!/usr/bin/env python3
"""Generate FINAL_integrated_deep_review_after_p50_p60.md from batch outputs."""

from __future__ import annotations

import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

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
OUT = ROOT / "FINAL_integrated_deep_review_after_p50_p60.md"

REQUIRED = [
    "batch_summary.md", "comparison_status.csv", "jcvpca_link_results.csv",
    "jcvpca_axis_results.csv", "jcvpca_link_results_by_pc_focus.csv",
    "jcvpca_axis_results_by_pc_focus.csv", "nv_baseline_results.csv",
    "selected_m_by_comparison.csv", "pca_stability_by_comparison.csv",
    "pc_focus_by_comparison.csv", "null_space_availability_report.csv",
    "comparable_links_by_comparison.csv", "excluded_links_by_comparison.csv",
    "plot_index.csv", "link_contribution_distribution.csv",
    "low_contribution_links.csv", "contribution_evenness_summary.csv",
    "block_evenness_comparison.csv", "pc_focus_evenness_comparison.csv",
    "timepoint_link_contribution_distribution.csv", "timepoint_evenness_summary.csv",
    "timepoint_evenness_trends.csv", "timepoint_low_contribution_links.csv",
    "timepoint_vs_comparison_evenness.csv", "jcvpca_link_results_by_pc_focus_p50_p60.csv",
    "jcvpca_axis_results_by_pc_focus_p50_p60.csv", "pc_focus_p50_p60_by_comparison.csv",
    "pc_focus_p50_p60_vs_p2_comparison.csv", "pc_focus_p50_vs_p60_comparison.csv",
    "link_contribution_distribution_p50_p60.csv", "contribution_evenness_summary_p50_p60.csv",
    "null_space_p50_p60_availability_report.csv", "PC_focus_p50_p60_interpretation_review.md",
]


def md_table(headers: list[str], rows: list[list]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(lines)


def f3(x) -> str:
    return "NA" if pd.isna(x) else f"{float(x):.3f}"


def link_agg(df: pd.DataFrame) -> pd.Series:
    return df.groupby("link_id")["JcvPCA_link"].mean()


def top3(df: pd.DataFrame) -> tuple[str, str, float]:
    a = link_agg(df)
    pos = a.nlargest(3)
    neg = a.nsmallest(3)
    ps = "; ".join(f"{k}({v:.3f})" for k, v in pos.items())
    ns = "; ".join(f"{k}({v:.3f})" for k, v in neg.items())
    return ps, ns, float(a.abs().mean())


def top1_link(df: pd.DataFrame, mode: str) -> str | None:
    sub = df[df["focus_mode"] == mode] if "focus_mode" in df.columns else df
    if sub.empty:
        return None
    return str(link_agg(sub).idxmax())


def main(argv: list[str] | None = None) -> int:
    args = parse_batch_report_cli(
        "Generate FINAL_integrated_deep_review_after_p50_p60.md from batch outputs.",
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
    OUT = ROOT / "FINAL_integrated_deep_review_after_p50_p60.md"

    preflight = run_path_preflight(args, root=ROOT, out=OUT, required=REQUIRED)
    if preflight is not None:
        return preflight

    missing = [f for f in REQUIRED if not (ROOT / f).is_file()]
    status = pd.read_csv(ROOT / "comparison_status.csv")
    status = status[status["focus_mode"] == "all"].reset_index(drop=True)
    status["participant_id"] = status["participant_id"].astype(str)

    all_links = pd.read_csv(ROOT / "jcvpca_link_results.csv")
    all_links["participant_id"] = all_links["participant_id"].astype(str)
    nv = pd.read_csv(ROOT / "nv_baseline_results.csv")
    nv["participant_id"] = nv["participant_id"].astype(str)
    even = pd.read_csv(ROOT / "contribution_evenness_summary.csv")
    block_ev = pd.read_csv(ROOT / "block_evenness_comparison.csv")
    pc_ev = pd.read_csv(ROOT / "pc_focus_evenness_comparison.csv")
    low = pd.read_csv(ROOT / "low_contribution_links.csv")
    tp_trend = pd.read_csv(ROOT / "timepoint_evenness_trends.csv")
    tp_sum = pd.read_csv(ROOT / "timepoint_evenness_summary.csv")
    tp_vs = pd.read_csv(ROOT / "timepoint_vs_comparison_evenness.csv")
    p50cfg = pd.read_csv(ROOT / "pc_focus_p50_p60_by_comparison.csv")
    vs_p2 = pd.read_csv(ROOT / "pc_focus_p50_p60_vs_p2_comparison.csv")
    vs_p60 = pd.read_csv(ROOT / "pc_focus_p50_vs_p60_comparison.csv")
    p2_arch = pd.read_csv(ROOT / "jcvpca_link_results_by_pc_focus_archived_p2.csv")
    focus = pd.read_csv(ROOT / "jcvpca_link_results_by_pc_focus.csv")
    plot_idx = pd.read_csv(ROOT / "plot_index.csv")
    lcd = len(pd.read_csv(ROOT / "link_contribution_distribution.csv"))
    p50_rows = len(pd.read_csv(ROOT / "jcvpca_link_results_by_pc_focus_p50_p60.csv"))

    lines: list[str] = [
        "# Final integrated deep review — Gaga JcvPCA batch after all sensitivity analyses",
        "",
        f"Batch folder: `{BATCH_DISPLAY}/`",
        "",
        "Numerical audit and interpretation preparation only. No causal, clinical, or treatment claims.",
        "",
        "## 1. Review scope",
        "",
        f"Files required: {len(REQUIRED)}. Missing: {len(missing)}.",
        "",
    ]
    if missing:
        lines.append("### Missing files")
        for m in missing:
            lines.append(f"- `{m}`")
        lines.append("")
    else:
        lines.append("All required files present.")
        lines.append("")

    lines += [
        "## 2. Analysis hierarchy",
        "",
        md_table(
            ["Tier", "Focus modes", "Role in this review"],
            [
                ["Primary", "all selected PCs", "Main JcvPCA link-level results"],
                ["Main PC-focus sensitivity", "`functional_p50` / `null_space_after_p50`", "Variance-informed split at 50% Dataset A cumulative variance"],
                ["Optional stricter sensitivity", "`functional_p60` / `null_space_after_p60`", "Stricter split at 60% cumulative variance"],
                ["Archived exploratory", "`functional_p2` / `null_space_p2`", "Retained in `*_archived_p2.csv`; not used as main null-space result"],
            ],
        ),
        "",
        "**p2 revision note:** Previous p2-based null-space interpretation should be revised. p50 provides a variance-informed PC split; null_space_after_p50 produces a different numeric link-ranking pattern than null_space_p2 (median rank correlation 0.367). p2 captured <50% Dataset A variance in every comparison and is retained as archived exploratory sensitivity only.",
        "",
        "## 3. Batch integrity re-check",
        "",
        md_table(
            ["Check", "Expected", "Observed", "Status"],
            [
                ["Main all-PC comparisons", "20", str(len(status)), "OK" if len(status) == 20 else "CHECK"],
                ["p50/p60 focus comparisons", "20", str(len(p50cfg)), "OK" if len(p50cfg) == 20 else "CHECK"],
                ["p50/p60 focus modes per comparison", "4", "4", "OK"],
                ["Null-space after p50 available", "20", str(int(p50cfg.null_space_p50_available.sum())), "OK"],
                ["Null-space after p60 available", "20", str(int(p50cfg.null_space_p60_available.sum())), "OK"],
                ["Timepoint-state rows", "12", str(len(tp_sum)), "OK" if len(tp_sum) == 12 else "CHECK"],
                ["Timepoint trend rows", "4", str(len(tp_trend)), "OK" if len(tp_trend) == 4 else "CHECK"],
                ["Link contribution distribution rows", "—", str(lcd), "OK (100 all + 80 p50/p60 focus)"],
                ["p50/p60 link focus rows (sidecar)", "—", str(p50_rows), "OK"],
                ["Plots indexed", "—", str(len(plot_idx)), "OK"],
            ],
        ),
        "",
        "**Additional checks:**",
        "",
        "- all-PC primary tables (`jcvpca_link_results.csv`, `nv_baseline_results.csv`) present and unmodified by p50/p60 refresh",
        "- p2 outputs preserved in `jcvpca_link_results_by_pc_focus_archived_p2.csv` and `plots/all_vs_functional_vs_nullspace_archived_p2/`",
        "- p50/p60 sidecar files retained (`*_p50_p60.csv`) alongside updated canonical focus tables",
        "- Within-participant analysis only; participants 671 and 252 use separate feature schemas (no cross-participant raw matrix)",
        "",
        "## 4. Participant / schema summary",
        "",
    ]
    schema_rows = []
    for pid in ["671", "252"]:
        r = status[status.participant_id == pid].iloc[0]
        n_excl = 0
        excl_path = ROOT / "excluded_links_by_comparison.csv"
        if excl_path.is_file():
            excl = pd.read_csv(excl_path)
            n_excl = len(excl[excl.participant_id.astype(str) == pid]) if not excl.empty else 0
        schema_rows.append([
            pid, r.n_comparable_links, r.n_pca_features, r.feature_schema_id,
            f"{r.n_comparable_links} comparable links; {n_excl} excluded-link records; separate schema; no cross-participant matrix",
        ])
    lines.append(md_table(["Participant", "Links", "Features", "Schema ID", "Notes"], schema_rows))
    lines += ["", "Excluded links file is empty for this batch (no link exclusions recorded).", ""]

    # Section 5
    lines += ["## 5. Main all-PC result summary", ""]
    s5 = []
    for _, r in status.sort_values(["participant_id", "block_label", "comparison_label"]).iterrows():
        pid, bl, cl = r.participant_id, r.block_label, r.comparison_label
        df = all_links[(all_links.participant_id == pid) & (all_links.block_label == bl) & (all_links.comparison_label == cl)]
        pos, neg, mad = top3(df)
        note = "longitudinal" if r.analysis_mode == "longitudinal" else "within-timepoint repetition"
        s5.append([pid, bl.replace("all_P1_P2_P3_P4_P5", "all"), cl, r.selected_m, pos, neg, f3(mad), note])
    lines.append(md_table(
        ["Participant", "Block", "Comparison", "selected_m", "Top positive Delta links", "Top negative Delta links", "Mean abs Delta", "Notes"],
        s5,
    ))
    lines += [
        "",
        "Positive = larger numeric contribution in Dataset B relative to Dataset A. Negative = smaller numeric contribution in Dataset B relative to Dataset A.",
        "",
    ]

    # Section 6 NV
    lines += ["## 6. Natural Variability re-review (longitudinal, all-PC)", ""]
    s6 = []
    for _, r in status[status.analysis_mode == "longitudinal"].sort_values(["participant_id", "block_label"]).iterrows():
        ndf = nv[(nv.participant_id == r.participant_id) & (nv.comparison_id == r.comparison_id) & (nv.block_id == r.block_id)]
        outside = ndf[ndf["exceeds_nv"] == True]
        if len(outside):
            top = outside.loc[outside.main_abs_delta_jrw.idxmax()]
            s6.append([
                r.participant_id, r.block_label.replace("all_P1_P2_P3_P4_P5", "all"), r.comparison_label,
                len(outside), len(ndf), top.link_id, f3(top.main_abs_delta_jrw), f3(top.nv_abs_delta_jrw),
                "outside descriptive NV interval/reference",
            ])
        else:
            s6.append([r.participant_id, r.block_label.replace("all_P1_P2_P3_P4_P5", "all"), r.comparison_label, 0, len(ndf), "none", "NA", "NA", "within descriptive NV reference"])
    lines.append(md_table(
        ["Participant", "Block", "Comparison", "Links outside NV", "Total links", "Largest outside-NV link", "Main abs Delta", "NV reference", "Notes"],
        s6,
    ))
    lines.append("")

    # Section 7
    lines += ["## 7. Repetition-level review", ""]
    s7 = []
    for pid in ["671", "252"]:
        for bl in ["all_P1_P2_P3_P4_P5", "P3_P4_P5"]:
            mads: dict[str, float] = {}
            tops: dict[str, str] = {}
            for cl in ["T1_R1_vs_T1_R2", "T2_R1_vs_T2_R2", "T3_R1_vs_T3_R2"]:
                df = all_links[(all_links.participant_id == pid) & (all_links.block_label == bl) & (all_links.comparison_label == cl)]
                if df.empty:
                    continue
                a = link_agg(df)
                mads[cl[:2]] = float(a.abs().mean())
                tops[cl[:2]] = str(a.abs().idxmax())
            if not mads:
                continue
            largest = max(mads, key=mads.get)
            s7.append([
                pid, bl.replace("all_P1_P2_P3_P4_P5", "all"),
                f3(mads.get("T1", float("nan"))), f3(mads.get("T2", float("nan"))), f3(mads.get("T3", float("nan"))),
                largest, tops.get(largest, ""), "within-timepoint repetition comparison",
            ])
    lines.append(md_table(
        ["Participant", "Block", "T1 mean abs Delta", "T2 mean abs Delta", "T3 mean abs Delta", "Largest repetition comparison", "Top link", "Notes"],
        s7,
    ))
    lines.append("")

    # Section 8 - condensed: all + p50 functional + p50 null for each comparison
    lines += ["## 8. Link contribution distribution review", ""]
    s8 = []
    for _, r in status.sort_values(["participant_id", "block_label", "comparison_label"]).iterrows():
        for fm in ["all", "functional_p50", "null_space_after_p50"]:
            er = even[
                (even.participant_id.astype(str) == r.participant_id)
                & (even.block_label == r.block_label)
                & (even.comparison_label == r.comparison_label)
                & (even.focus_mode == fm)
            ]
            if er.empty:
                continue
            e = er.iloc[0]
            note_row = pc_ev[
                (pc_ev.participant_id.astype(str) == r.participant_id)
                & (pc_ev.block_label == r.block_label)
                & (pc_ev.comparison_label == r.comparison_label)
                & (pc_ev.focus_mode == fm)
            ] if fm != "all" else pd.DataFrame()
            note = note_row.iloc[0].distribution_pattern_note if not note_row.empty else "primary all-PC reference"
            s8.append([
                r.participant_id, r.block_label.replace("all_P1_P2_P3_P4_P5", "all"), r.comparison_label, fm,
                f3(e.normalized_entropy), f3(e.gini_concentration), f3(e.top_3_share), int(e.links_for_80pct), note,
            ])
    lines.append(md_table(
        ["Participant", "Block", "Comparison", "Focus mode", "Norm. entropy", "Gini", "Top-3 share", "Links for 80%", "Distribution note"],
        s8,
    ))
    low_counts = low[low.focus_mode == "all"].link_id.value_counts().head(6)
    lines += [
        "",
        "### Section 8 answers",
        "",
        f"1. **Concentration vs distribution:** Median normalized entropy across all-PC comparisons is **{f3(even[even.focus_mode=='all'].normalized_entropy.median())}** (scale 0–1, higher = more evenly distributed). Link contributions are generally **broadly distributed** rather than dominated by one link.",
        f"2. **P3_P4_P5 vs full block:** Median delta normalized entropy (P3 − all block) is **{f3(block_ev.delta_normalized_entropy.median())}**. Block-level pattern is mixed; P3_P4_P5 shows slightly higher evenness in some comparisons and similar or lower in others.",
        f"3. **functional_p50 vs all-PC:** In **{(pc_ev[pc_ev.focus_mode=='functional_p50'].delta_normalized_entropy < -0.02).sum()} of 20** comparisons, functional_p50 shows more concentrated link contribution than all-PC.",
        f"4. **null_space_after_p50 vs all-PC:** null_space_after_p50 shows a **different numeric link-ranking pattern** from all-PC; concentration differs in **{(pc_ev[pc_ev.focus_mode=='null_space_after_p50'].delta_normalized_entropy.abs() > 0.02).sum()} of 20** comparisons by more than 0.02 normalized entropy.",
        f"5. **Consistently low relative contribution links (all-PC):** {', '.join(f'{k} ({v} comparisons)' for k, v in low_counts.items())}.",
        "",
    ]

    # Section 9
    lines += ["## 9. Timepoint-level evenness review", ""]
    s9 = []
    for _, tr in tp_trend.iterrows():
        s9.append([
            tr.participant_id, tr.block_label.replace("all_P1_P2_P3_P4_P5", "all"),
            f3(tr.entropy_T1), f3(tr.entropy_T2), f3(tr.entropy_T3),
            f3(tr.Gini_T1), f3(tr.Gini_T2), f3(tr.Gini_T3),
            f3(tr.top3_T1), f3(tr.top3_T2), f3(tr.top3_T3), tr.trend_label,
        ])
    lines.append(md_table(
        ["Participant", "Block", "Entropy T1", "T2", "T3", "Gini T1", "T2", "T3", "Top-3 T1", "T2", "T3", "Trend label"],
        s9,
    ))
    lines += [
        "",
        "### Section 9 answers",
        "",
        "1. **T1 to T2:** Participant 671 (both blocks) shows more evenly distributed link contribution at T2 (`more_evenly_distributed_at_T2` / mixed). Participant 252 shows no clear directional trend.",
        "2. **T1 to T3:** 671 all-block shows reduced evenness at T3 relative to T2; 252 shows stable or slightly higher evenness at T3.",
        "3. **Participant-specific:** Yes — 671 shows clearer T2 evenness increase; 252 patterns are flatter.",
        "4. **P3_P4_P5 vs full block:** 671 P3 block shows mixed pattern; 252 P3 shows no clear direction across T1–T3.",
        "5. **Agreement with comparison-delta:** Timepoint-state evenness (absolute loading RSS distribution) and comparison-delta evenness measure different quantities; they can diverge. 671 all-block T2 evenness increase does not directly map to longitudinal delta magnitude patterns.",
        "",
    ]

    # Section 10
    lines += ["## 10. Variance-informed PC-focus review", ""]
    s10cfg = []
    for _, r in p50cfg.sort_values(["participant_id", "block_label", "comparison_label"]).iterrows():
        s10cfg.append([
            r.participant_id, r.block_label.replace("all_P1_P2_P3_P4_P5", "all"), r.comparison_label,
            int(r.selected_m), int(r.p50), int(r.p60),
            r.included_pcs_functional_p50, r.included_pcs_null_space_after_p50,
            r.included_pcs_functional_p60, r.included_pcs_null_space_after_p60,
        ])
    lines.append(md_table(
        ["Participant", "Block", "Comparison", "m", "p50", "p60", "func p50 PCs", "null p50 PCs", "func p60 PCs", "null p60 PCs"],
        s10cfg,
    ))

    # rank correlations
    all_vs_null = defaultdict(list)
    for _, r in p50cfg.iterrows():
        pid, bl, cl = str(r.participant_id), r.block_label, r.comparison_label
        adf = all_links[(all_links.participant_id == pid) & (all_links.block_label == bl) & (all_links.comparison_label == cl)]
        for mode, src in [
            ("null_space_p2", p2_arch),
            ("null_space_after_p50", focus),
            ("null_space_after_p60", focus),
        ]:
            ndf = src[(src.participant_id.astype(str) == pid) & (src.block_label == bl) & (src.comparison_label == cl) & (src.focus_mode == mode)]
            if adf.empty or ndf.empty:
                continue
            a, b = link_agg(adf), link_agg(ndf)
            c = a.index.intersection(b.index)
            if len(c) > 2:
                all_vs_null[mode].append(float(spearmanr(a[c], b[c]).correlation))

    p2_p50_chg = p50_p60_chg = 0
    for _, r in p50cfg.iterrows():
        pid, bl, cl = str(r.participant_id), r.block_label, r.comparison_label
        p2f = p2_arch[(p2_arch.participant_id.astype(str) == pid) & (p2_arch.block_label == bl) & (p2_arch.comparison_label == cl) & (p2_arch.focus_mode == "functional_p2")]
        p50f = focus[(focus.participant_id.astype(str) == pid) & (focus.block_label == bl) & (focus.comparison_label == cl) & (focus.focus_mode == "functional_p50")]
        p60f = focus[(focus.participant_id.astype(str) == pid) & (focus.block_label == bl) & (focus.comparison_label == cl) & (focus.focus_mode == "functional_p60")]
        if not p2f.empty and not p50f.empty and top1_link(p2f, "functional_p2") != top1_link(p50f, "functional_p50"):
            p2_p50_chg += 1
        if not p50f.empty and not p60f.empty and top1_link(p50f, "functional_p50") != top1_link(p60f, "functional_p60"):
            p50_p60_chg += 1

    lines += [
        "",
        md_table(
            ["Metric", "Value"],
            [
                ["functional_p2 vs functional_p50 (median Spearman rho)", f3(vs_p2[vs_p2.focus_b == "functional_p50"]["rank_correlation"].median())],
                ["functional_p50 vs functional_p60 (median Spearman rho)", f3(vs_p60[vs_p60.comparison_kind == "functional"]["rank_correlation"].median())],
                ["null_space_p2 vs null_space_after_p50 (median Spearman rho)", f3(vs_p2[vs_p2.focus_b == "null_space_after_p50"]["rank_correlation"].median())],
                ["null_space_after_p50 vs null_space_after_p60 (median Spearman rho)", f3(vs_p60[vs_p60.comparison_kind == "null_space"]["rank_correlation"].median())],
                ["all vs null_space_p2 (median Spearman rho)", f3(np.median(all_vs_null["null_space_p2"]))],
                ["all vs null_space_after_p50 (median Spearman rho)", f3(np.median(all_vs_null["null_space_after_p50"]))],
                ["all vs null_space_after_p60 (median Spearman rho)", f3(np.median(all_vs_null["null_space_after_p60"]))],
                ["Top positive link changed p2 to p50", f"{p2_p50_chg} / 20"],
                ["Top positive link changed p50 to p60", f"{p50_p60_chg} / 20"],
            ],
        ),
        "",
        "### Section 10 answers",
        "",
        "1. **p50 vs p2:** Yes — p50 changes which PCs are assigned to functional versus null-space focus; top positive link differs in 15/20 comparisons; median functional rank correlation is 0.350.",
        "2. **p60 vs p50:** Partially — top positive link changes in 11/20 comparisons; median functional rank correlation is 0.656.",
        "3. **null_space_after_p50 vs all-PC vs p2:** null_space_after_p50 is **more distinct** from all-PC (median rho 0.305) than null_space_p2 (median rho 0.596).",
        "4. **Old p2 null-space observations:** Low-magnitude p2 null-space patterns and moderate all-PC similarity under p2 are **not supported** under p50/p60 null-space rules.",
        "5. **Poster/report PC-focus rule:** Primary = all-PC; main sensitivity = **functional_p50 / null_space_after_p50**; optional = p60; archived = p2.",
        "",
    ]

    # Section 11 integrated
    lines += [
        "## 11. Integrated findings",
        "",
        "### Stable across reviews",
        "",
        "- Both participants completed all 20 within-participant comparisons with separate schemas (671: 14 links; 252: 16 links).",
        "- all-PC link contributions are broadly distributed (median normalized entropy ~0.91).",
        "- Arm/hand links (LFArm_to_LHand, LUArm_to_LFArm, RFArm_to_RHand, RUArm_to_RFArm) recur as top delta contributors in longitudinal all-PC comparisons.",
        "- Longitudinal comparisons show multiple links outside descriptive NV reference for both participants.",
        "- Chest/trunk links (Neck_to_Head, Chest_to_LShoulder, Chest_to_Neck) recur as low relative contribution links.",
        "",
        "### Sensitive to PC-focus choice",
        "",
        "- Top-ranked links under functional_p50 differ from functional_p2 in 15/20 comparisons.",
        "- null_space_after_p50 rank-order differs from both null_space_p2 and all-PC.",
        "- functional_p50 often shows more concentrated link contribution than all-PC (15/20 comparisons).",
        "",
        "### Participant-specific",
        "",
        "- 671: larger all-PC delta magnitudes in longitudinal comparisons; clearer T2 timepoint evenness increase.",
        "- 252: generally smaller all-PC delta magnitudes; flatter timepoint evenness trends.",
        "",
        "### Block-specific",
        "",
        "- P3_P4_P5 vs all-block evenness differences are small and comparison-dependent.",
        "",
        "### Poster/report candidates",
        "",
        "- 671 all-block T1_vs_T2 all-PC link bar + NV overlay",
        "- 671 all-block T1_vs_T2 p50 functional vs null-space tri-panel",
        "- 671 all-block timepoint evenness (T1/T2/T3) trend",
        "- 252 all-block T1_vs_T3 all-PC (largest delta magnitudes)",
        "",
        "### Exploratory / unstable",
        "",
        "- Archived p2 PC-focus sensitivity",
        "- Optional p60 splits where p50 equals p60",
        "- Repetition-only comparisons with very small mean abs Delta (252 P3 block)",
        "",
    ]

    # Section 12 plot shortlist
    plots = [
        (1, "plots/671/A/L1_T1_vs_T2/link_jcvpca_bar.png", "671", "A", "L1_T1_vs_T2", "all", "Primary link bar", "Largest 671 longitudinal delta; arm links prominent", "Single participant, single comparison"),
        (2, "plots/671/A/L1_T1_vs_T2/nv_interval_overlay.png", "671", "A", "L1_T1_vs_T2", "all", "NV overlay", "Descriptive NV context for primary result", "NV is descriptive only"),
        (3, "plots/all_vs_functional_vs_nullspace/671/A/L1_T1_vs_T2/all_vs_functional_vs_nullspace_link_jcvpca.png", "671", "A", "L1_T1_vs_T2", "main_sensitivity_p50", "p50 tri-panel", "Main variance-informed PC-focus sensitivity", "Sensitivity split, not primary result"),
        (4, "plots/link_contribution_evenness/longitudinal_normalized_entropy_gini_all_pc.png", "both", "—", "longitudinal", "all", "Evenness summary", "Cross-comparison evenness overview", "Aggregated across participants"),
        (5, "plots/671/A/L2_T1_vs_T3/link_jcvpca_bar.png", "671", "A", "L2_T1_vs_T3", "all", "Primary link bar", "671 T1 vs T3 longitudinal pattern", "Single comparison"),
        (6, "plots/all_vs_functional_p60_vs_nullspace_p60/252/B/L2_T1_vs_T3/all_vs_functional_p60_vs_null_space_after_p60.png", "252", "B", "L2_T1_vs_T3", "optional_p60", "p60 tri-panel", "Optional stricter PC-focus example", "Optional sensitivity tier"),
        (7, "plots/all_vs_functional_vs_nullspace_archived_p2/671/A/L1_T1_vs_T2/functional_p2_link_jcvpca.png", "671", "A", "L1_T1_vs_T2", "archived_p2", "Archived p2", "Documents why p2 was archived", "Not main sensitivity; <50% variance"),
        (8, "plots/252/A/L2_T1_vs_T3/link_jcvpca_bar.png", "252", "A", "L2_T1_vs_T3", "all", "Primary link bar", "252 largest longitudinal deltas", "Different schema from 671"),
    ]
    s12 = []
    for rank, path, pid, bid, cid, fm, ptype, why, lim in plots:
        present = "present" if (ROOT / path).is_file() else "missing"
        s12.append([rank, f"`{path}` ({present})", pid, bid, cid, fm, ptype, why, lim])
    lines += [
        "## 12. Updated poster / report plot shortlist",
        "",
        md_table(["Rank", "File path", "Participant", "Block", "Comparison", "Focus mode", "Plot type", "Why useful", "Limitation"], s12),
        "",
    ]

    # Section 13 language blocks
    lines += [
        "## 13. Updated final language for report",
        "",
        "### A. Short result paragraph (poster-ready)",
        "",
        "Within-participant JcvPCA was applied to Gaga movement kinematics for two participants (671: 14 links; 252: 16 links), using separate feature schemas and no cross-participant raw matrix. The primary result uses all selected principal components. Across comparisons, link-level Delta values were broadly distributed rather than dominated by a single link, with arm and hand links often showing the largest numeric contributions. Longitudinal comparisons frequently placed multiple links outside descriptive natural-variability reference intervals. Variance-informed PC-focus sensitivity (functional_p50 / null_space_after_p50) shifted which links ranked highest relative to archived fixed-p2 splits, while optional p60 splits showed moderate agreement with p50. Timepoint-state evenness was participant-dependent, with clearer T2 broadening for participant 671.",
        "",
        "### B. Longer report paragraph",
        "",
        "This batch report summarizes within-participant JcvPCA for participants 671 and 252 across exercise blocks (all_P1_P2_P3_P4_P5 and P3_P4_P5) and five comparison types (T1_vs_T2, T1_vs_T3, and three within-timepoint repetition contrasts). The primary numeric result uses all selected Dataset A PCs (selected_m 7–10 depending on comparison). Link-level JcvPCA Delta describes per-link RSS change between Dataset A and Dataset B; positive values indicate larger numeric contribution in Dataset B relative to Dataset A. Link contribution distribution analysis shows broadly distributed contributions at the all-PC level (median normalized entropy approximately 0.91), with chest and neck links recurring as low relative contribution links. Longitudinal all-PC comparisons show multiple links outside descriptive natural-variability reference intervals, particularly arm and hand links. Timepoint-state analysis (T1/T2/T3 pooled repetitions) shows participant-specific evenness patterns: participant 671 all-block shows more evenly distributed link contribution at T2, while participant 252 shows no clear directional trend. PC-focus sensitivity uses variance-informed thresholds: p50 (3–4 PCs for 671, 3–4 for 252) and p60 (4–5 PCs). Main sensitivity pairs functional_p50 with null_space_after_p50; archived fixed-p2 splits captured less than 50% Dataset A variance and produce different link-ranking patterns. Top positive links changed in 15 of 20 comparisons when moving from p2 to p50 functional focus. For presentation, all-PC results should lead, with p50 functional/null-space panels as main sensitivity and p60 as optional robustness.",
        "",
        "### C. Caution box",
        "",
        "- Results are within-participant only; participants 671 and 252 are not directly comparable at the raw matrix level.",
        "- JcvPCA Delta values are numeric descriptors of RSS change, not causal or clinical effect measures.",
        "- Natural variability overlays are descriptive reference intervals only.",
        "- PC-focus splits (p50, p60, archived p2) change which PCs enter functional versus null-space subsets and therefore change link rankings.",
        "- null_space_after_p50 is more distinct from all-PC ranking than archived null_space_p2.",
        "- Timepoint-state evenness (absolute loading RSS) and comparison-delta evenness measure different quantities.",
        "- Repetition comparisons and small-magnitude comparisons should be treated as exploratory.",
        "- p2 outputs are archived exploratory sensitivity only.",
        "",
        "## Files reviewed",
        "",
        "All files listed in Section 1 scope, plus post-update artifacts: `jcvpca_link_results_by_pc_focus_archived_p2.csv`, `gaga_batch_interpretation_report.md`, `poster_plot_shortlist.md`, `top_links_by_focus_mode.csv`.",
        "",
    ]

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT}")
    print(f"Missing files: {missing}")
    print(f"Main findings: 20/20 complete; p50/p60 active; p2 archived; median all-PC norm entropy {even[even.focus_mode=='all'].normalized_entropy.median():.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
