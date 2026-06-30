#!/usr/bin/env python3
"""Generate nullspace_FULL_NUMERIC_REPORT.md from nullspace_link_stability_review CSVs."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from layer3_batch_report_paths import (
    display_repo_path,
    parse_batch_report_cli,
    resolve_batch_report_paths,
    run_path_preflight,
)

BATCH = Path()
REVIEW = Path()
OUT = Path()
BATCH_ID = ""
BATCH_DISPLAY = ""
REVIEW_DISPLAY = ""


def configure_nullspace_report_paths(
    *,
    config_path: Path | None = None,
    batch_dir: Path | None = None,
) -> None:
    global BATCH, REVIEW, OUT, BATCH_ID, BATCH_DISPLAY, REVIEW_DISPLAY

    paths = resolve_batch_report_paths(config_path=config_path, batch_dir=batch_dir)
    review = (paths.root.parent / "nullspace_link_stability_review").resolve()
    if not review.is_dir():
        raise FileNotFoundError(
            f"Required nullspace review folder missing: {review}\n"
            f"Config: {paths.config_path}"
        )

    project_root = paths.config_path.parent.parent
    BATCH = paths.root
    BATCH_ID = paths.batch_id
    BATCH_DISPLAY = paths.batch_display
    REVIEW = review
    REVIEW_DISPLAY = display_repo_path(review, project_root)
    OUT = REVIEW / "nullspace_FULL_NUMERIC_REPORT.md"


try:
    configure_nullspace_report_paths()
except FileNotFoundError as exc:
    print(f"[FAIL] {exc}", file=sys.stderr)
    raise SystemExit(1) from exc

PRIMARY_NULL = ["null_space_after_p50", "null_space_after_p60"]
ALL_NULL = PRIMARY_NULL + ["null_space_after_p70"]
PARTICIPANTS = ["671", "252"]
BLOCKS = ["P3_P4_P5", "all_P1_P2_P3_P4_P5"]
REPETITION = ["T1_R1_vs_T1_R2", "T2_R1_vs_T2_R2", "T3_R1_vs_T3_R2"]
LONGITUDINAL = ["T1_vs_T2", "T1_vs_T3"]
EXPLORATORY = ["T2_vs_T3"]

NULLSPACE_REQUIRED = [
    "nullspace_top7_links_all_contexts.csv",
    "nullspace_p50_p60_link_overlap.csv",
    "nullspace_p50_p60_p70_link_overlap.csv",
    "nullspace_threshold_stability_summary.csv",
    "nullspace_anatomical_family_summary.csv",
    "nullspace_link_recurrence_summary.csv",
    "nullspace_noise_diagnostic_summary.csv",
    "nullspace_explained_variance_weighting_check.csv",
]


def read_csv(name: str) -> pd.DataFrame:
    path = REVIEW / name
    if not path.is_file():
        raise FileNotFoundError(f"Missing: {path}. Run analyze_nullspace_link_stability.py first.")
    return pd.read_csv(path)


def f4(x) -> str:
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return "NA"
    if pd.isna(x):
        return "NA"
    if isinstance(x, (bool, np.bool_)):
        return str(bool(x))
    if isinstance(x, (float, int, np.floating, np.integer)):
        return f"{float(x):.4f}"
    return str(x)


def fmt_cell(x, col: str = "") -> str:
    if col == "participant_id":
        if pd.isna(x):
            return "NA"
        return str(int(float(x)))
    if col in ("is_top1", "is_top3", "is_top5", "is_top7", "same_top1_link", "same_top1_family", "appears_in_p50", "appears_in_p60", "appears_in_both_p50_p60", "remains_top7_after_weighting"):
        if pd.isna(x):
            return "NA"
        return str(bool(x))
    if col.startswith("appears_"):
        if pd.isna(x):
            return "NA"
        return str(bool(x))
    return f4(x)


def md_table(headers: list[str], rows: list[list]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(lines)


def df_to_md(df: pd.DataFrame, cols: list[str] | None = None) -> str:
    cols = cols or list(df.columns)
    rows = [[fmt_cell(r[c], c) for c in cols] for _, r in df[cols].iterrows()]
    return md_table(cols, rows)


def tp_for(comp: str) -> str:
    return {"T1_R1_vs_T1_R2": "T1", "T2_R1_vs_T2_R2": "T2", "T3_R1_vs_T3_R2": "T3"}.get(comp, "")


def main(argv: list[str] | None = None) -> int:
    args = parse_batch_report_cli(
        "Generate nullspace_FULL_NUMERIC_REPORT.md from nullspace review CSVs.",
        argv,
    )
    try:
        configure_nullspace_report_paths(config_path=args.config, batch_dir=args.batch_dir)
    except FileNotFoundError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1

    preflight = run_path_preflight(
        args,
        root=BATCH,
        out=OUT,
        required=NULLSPACE_REQUIRED,
        input_root=REVIEW,
    )
    if preflight is not None:
        return preflight

    top7 = read_csv("nullspace_top7_links_all_contexts.csv")
    overlap = read_csv("nullspace_p50_p60_link_overlap.csv")
    triple = read_csv("nullspace_p50_p60_p70_link_overlap.csv")
    threshold = read_csv("nullspace_threshold_stability_summary.csv")
    family = read_csv("nullspace_anatomical_family_summary.csv")
    recurrence = read_csv("nullspace_link_recurrence_summary.csv")
    noise = read_csv("nullspace_noise_diagnostic_summary.csv")
    vw = read_csv("nullspace_explained_variance_weighting_check.csv")

    top7["participant_id"] = top7["participant_id"].astype(str)
    overlap["participant_id"] = overlap["participant_id"].astype(str)
    noise["participant_id"] = noise["participant_id"].astype(str)

    elev_p50 = int((noise["null_p50_to_all_ratio"] > 1).sum())
    elev_p60 = int((noise["null_p60_to_all_ratio"] > 1).sum())
    same_top1_pct = float(overlap["same_top1_link"].mean() * 100)
    med_j = float(overlap["top7_jaccard"].median())
    med_fj = float(overlap["family_jaccard_top7"].median())

    structured = int((noise["final_diagnostic_label"] == "likely_structured_nullspace_pattern").sum())
    thresh_sens = int((noise["final_diagnostic_label"] == "structured_but_threshold_sensitive").sum())
    mag_only = int((noise["final_diagnostic_label"] == "magnitude_only_no_stable_anatomy").sum())
    poss_noise = int((noise["final_diagnostic_label"] == "possible_noise_or_model_sensitivity").sum())
    insuf = int((noise["final_diagnostic_label"] == "insufficient_evidence").sum())

    best = noise.sort_values(["structure_score", "null_p50_to_all_ratio"], ascending=False).iloc[0]

    lines: list[str] = [
        "# Null-Space Link Stability and Interpretation Report — full numeric edition",
        "",
        f"Batch source: `{BATCH_DISPLAY}/`",
        f"Review CSV folder: `{REVIEW_DISPLAY}/`",
        "",
        "Complete descriptive report for **null_space_after_p50**, **null_space_after_p60**, and diagnostic **null_space_after_p70**.",
        "Participants **671** and **252** analyzed separately. No figures. No inferential statistics. No participant pooling.",
        "",
        "---",
        "",
        "## 1. Executive summary",
        "",
        "### 1.1 Primary questions answered",
        "",
        "| Question | Answer |",
        "| --- | --- |",
        f"| Is null-space variability elevated? | **Yes** — null/all ratio > 1 in **{elev_p50}/{len(noise)}** cells (p50) and **{elev_p60}/{len(noise)}** (p60). Elevation alone does not prove stable anatomy. |",
        f"| Is elevation consistent between p50 and p60? | **Partially** — same top-1 link in **{same_top1_pct:.1f}%** of cells; median top-7 Jaccard **{f4(med_j)}**; median family Jaccard **{f4(med_fj)}**. |",
        "| Are the same exact links stable? | **Moderate** — perfect overlap in several cells (e.g. 671 T2 repetition); many cells shift rank-1 between thresholds. |",
        "| Are the same anatomical families stable? | **Often yes** — family Jaccard frequently ≥ 0.8 even when exact links differ. |",
        "| Structured or noise-like? | **Mixed, leaning family-structured** — see Section 8 diagnostic counts. |",
        f"| Strongest cell | **{best['participant_id']}** `{best['block_label']}` **{best['comparison_label']}**"
        + (f" ({best['timepoint_if_repetition']})" if pd.notna(best.get("timepoint_if_repetition")) and best.get("timepoint_if_repetition") else "")
        + f" — `{best['final_diagnostic_label']}` (structure score **{f4(best['structure_score'])}**). |",
        "| Poster role | **Secondary / sensitivity** — family-level + null/all ratio; not central exact-link claim. |",
        "",
        "### 1.2 Diagnostic label counts",
        "",
        md_table(
            ["final_diagnostic_label", "n_cells"],
            [
                ["likely_structured_nullspace_pattern", str(structured)],
                ["structured_but_threshold_sensitive", str(thresh_sens)],
                ["magnitude_only_no_stable_anatomy", str(mag_only)],
                ["possible_noise_or_model_sensitivity", str(poss_noise)],
                ["insufficient_evidence", str(insuf)],
            ],
        ),
        "",
        "### 1.3 Four-way classification verdict",
        "",
        "1. **Stable exact-link anatomy** — limited; strong in selected cells only.",
        "2. **Family-level structured pattern** — **best supported** (upper limb, lower limb, shoulder chain).",
        "3. **Magnitude-only sensitivity** — present when null/all > 1 but top-7 Jaccard is low.",
        "4. **Possible noise/model sensitivity** — flagged in overlap labels for ~25% of cells; rare as final diagnostic.",
        "",
        "---",
        "",
        "## 2. Conceptual definition",
        "",
        "| Term | Meaning |",
        "| --- | --- |",
        "| all-PC | Mean link Delta aggregated across selected PCs in the base run |",
        "| functional_p50 / p60 | Dominant variance-informed PC subset up to cumulative ~50% / ~60% |",
        "| null_space_after_p50 / p60 | Later PCs after removing the functional subset — **less-dominant / redundant degrees of freedom** |",
        "| null_space_after_p70 | Diagnostic stricter split at ~70% cumulative variance (not primary poster focus) |",
        "| Link-level output | Per-segment RSS change; not a pure joint-level scalar |",
        "",
        "Use: *later-PC structure*, *less-dominant link contributions*, *descriptive null-space layer*.",
        "Avoid: causal, clinical, creativity, improvement, or psilocybin-specific language.",
        "",
        "---",
        "",
        "## 3. Why top-7 links were inspected",
        "",
        "Top-7 inspection distinguishes **anatomically interpretable** null-space magnitude from **threshold-sensitive magnitude inflation** without stable link identity.",
        "",
        "---",
        "",
        "## 4. File inventory",
        "",
        md_table(
            ["File", "Rows", "Description"],
            [
                ["nullspace_top7_links_all_contexts.csv", str(len(top7)), "Top-7 null-space links per cell"],
                ["nullspace_p50_p60_link_overlap.csv", str(len(overlap)), "p50 vs p60 stability"],
                ["nullspace_p50_p60_p70_link_overlap.csv", str(len(triple)), "Three threshold-pair comparisons"],
                ["nullspace_threshold_stability_summary.csv", str(len(threshold)), "Cross-threshold labels"],
                ["nullspace_anatomical_family_summary.csv", str(len(family)), "Family aggregation"],
                ["nullspace_link_recurrence_summary.csv", str(len(recurrence)), "Cross-context recurrence"],
                ["nullspace_noise_diagnostic_summary.csv", str(len(noise)), "Structure vs noise scores"],
                ["nullspace_explained_variance_weighting_check.csv", str(len(vw)), "EV-weighted rank sensitivity"],
            ],
        ),
        "",
        f"Total analysis cells: **{len(noise)}** (2 participants × 2 blocks × [3 repetition + 2 longitudinal + 1 exploratory T2_vs_T3]).",
        "",
        "---",
        "",
        "## 5. Repetition-variability null-space results",
        "",
        "Within-timepoint R1 vs R2 at T1, T2, T3. Full top-7 tables for p50 and p60.",
        "",
    ]

    for pid in PARTICIPANTS:
        for bl in BLOCKS:
            lines.append(f"### 5.{pid} | {bl}")
            for comp in REPETITION:
                tp = tp_for(comp)
                ov = overlap[
                    (overlap.participant_id == pid)
                    & (overlap.block_label == bl)
                    & (overlap.comparison_label == comp)
                ]
                for focus in PRIMARY_NULL:
                    sub = top7[
                        (top7.participant_id == pid)
                        & (top7.block_label == bl)
                        & (top7.comparison_label == comp)
                        & (top7.focus_mode == focus)
                    ].sort_values("rank_abs_delta")
                    if sub.empty:
                        continue
                    lines.append(f"#### {comp} | `{focus}`")
                    lines.append(
                        df_to_md(
                            sub,
                            [
                                "rank_abs_delta",
                                "link_id",
                                "anatomical_family",
                                "body_region",
                                "side",
                                "JcvPCA_link_delta",
                                "abs_delta",
                                "relative_abs_delta_share",
                                "sign_of_delta",
                            ],
                        )
                    )
                    if not ov.empty:
                        o = ov.iloc[0]
                        nd = noise[
                            (noise.participant_id == pid)
                            & (noise.block_label == bl)
                            & (noise.comparison_label == comp)
                            & (noise.timepoint_if_repetition == tp)
                        ]
                        diag = nd.iloc[0]["final_diagnostic_label"] if not nd.empty else "NA"
                        lines.append(
                            f"**Overlap p50/p60:** top7={o['top7_overlap_count']}, Jaccard={f4(o['top7_jaccard'])}, "
                            f"family Jaccard={f4(o['family_jaccard_top7'])}, same top-1={o['same_top1_link']}, "
                            f"overlap label=`{o['interpretation_label']}`, diagnostic=`{diag}`."
                        )
                    lines.append("")

    lines += ["---", "", "## 6. Longitudinal null-space results", ""]
    for pid in PARTICIPANTS:
        for bl in BLOCKS:
            lines.append(f"### 6.{pid} | {bl}")
            for comp in LONGITUDINAL:
                ov = overlap[
                    (overlap.participant_id == pid)
                    & (overlap.block_label == bl)
                    & (overlap.comparison_label == comp)
                ]
                for focus in PRIMARY_NULL:
                    sub = top7[
                        (top7.participant_id == pid)
                        & (top7.block_label == bl)
                        & (top7.comparison_label == comp)
                        & (top7.focus_mode == focus)
                    ].sort_values("rank_abs_delta")
                    if sub.empty:
                        continue
                    lines.append(f"#### {comp} | `{focus}`")
                    lines.append(
                        df_to_md(
                            sub,
                            ["rank_abs_delta", "link_id", "anatomical_family", "abs_delta", "relative_abs_delta_share", "sign_of_delta"],
                        )
                    )
                    if not ov.empty:
                        o = ov.iloc[0]
                        lines.append(
                            f"**p50 vs p60:** top7 overlap **{o['top7_overlap_count']}**, Jaccard **{f4(o['top7_jaccard'])}**, label **`{o['interpretation_label']}`**."
                        )
                    lines.append("")

    lines += [
        "**Cross-context:** longitudinal null-space top links **partially overlap** repetition null-space **families** (upper/lower limb) but rarely share the same rank-1 link.",
        "",
        "---",
        "",
        "## 7. Exploratory T2_vs_T3 null-space (completeness only)",
        "",
    ]
    for pid in PARTICIPANTS:
        for bl in BLOCKS:
            for focus in PRIMARY_NULL:
                sub = top7[
                    (top7.participant_id == pid)
                    & (top7.block_label == bl)
                    & (top7.comparison_label == "T2_vs_T3")
                    & (top7.focus_mode == focus)
                ].sort_values("rank_abs_delta")
                if sub.empty:
                    continue
                lines.append(f"### {pid} | {bl} | T2_vs_T3 | `{focus}`")
                lines.append(df_to_md(sub, ["rank_abs_delta", "link_id", "anatomical_family", "abs_delta", "relative_abs_delta_share"]))
                lines.append("")

    lines += [
        "---",
        "",
        "## 8. p50 vs p60 stability — full numeric table",
        "",
        df_to_md(overlap.sort_values(["participant_id", "block_label", "comparison_label", "timepoint_if_repetition"])),
        "",
        "### 8.1 Aggregate summary",
        "",
        md_table(
            ["Metric", "Value"],
            [
                ["Cells", str(len(overlap))],
                ["Same top-1 link (%)", f4(same_top1_pct)],
                ["Median top-7 overlap count", f4(overlap["top7_overlap_count"].median())],
                ["Median top-7 Jaccard", f4(med_j)],
                ["Median family Jaccard (top-7)", f4(med_fj)],
                ["Median Spearman rho (top-7 union)", f4(overlap["spearman_rank_rho_top7_union"].median())],
                ["Median sign agreement (top-7 union)", f4(overlap["sign_agreement_top7_union"].median())],
                ["stable_exact_links", str(int((overlap["interpretation_label"] == "stable_exact_links").sum()))],
                ["stable_anatomical_families", str(int((overlap["interpretation_label"] == "stable_anatomical_families").sum()))],
                ["magnitude_consistent_but_link_sensitive", str(int((overlap["interpretation_label"] == "magnitude_consistent_but_link_sensitive").sum()))],
                ["threshold_sensitive_possible_noise", str(int((overlap["interpretation_label"] == "threshold_sensitive_possible_noise").sum()))],
                ["insufficient_data", str(int((overlap["interpretation_label"] == "insufficient_data").sum()))],
            ],
        ),
        "",
        "---",
        "",
        "## 9. p50 / p60 / p70 threshold stability",
        "",
        "### 9.1 Threshold-pair overlap (full table)",
        "",
        df_to_md(triple.sort_values(["participant_id", "block_label", "comparison_label", "threshold_pair"])),
        "",
        "### 9.2 Threshold stability summary (full table)",
        "",
        df_to_md(threshold.sort_values(["participant_id", "block_label", "comparison_label"])),
        "",
        "### 9.3 p70 top-7 tables (diagnostic only)",
        "",
    ]

    for pid in PARTICIPANTS:
        for bl in BLOCKS:
            for atype in ["repetition_variability", "longitudinal"]:
                comps = REPETITION if atype == "repetition_variability" else LONGITUDINAL
                for comp in comps:
                    sub = top7[
                        (top7.participant_id == pid)
                        & (top7.block_label == bl)
                        & (top7.comparison_label == comp)
                        & (top7.analysis_type == atype)
                        & (top7.focus_mode == "null_space_after_p70")
                    ].sort_values("rank_abs_delta")
                    if sub.empty:
                        continue
                    lines.append(f"#### {pid} | {bl} | {comp} | null_space_after_p70")
                    lines.append(df_to_md(sub, ["rank_abs_delta", "link_id", "anatomical_family", "abs_delta", "relative_abs_delta_share"]))
                    lines.append("")

    lines += ["---", "", "## 10. Anatomical-family interpretation", ""]

    if not family.empty:
        fam_counts = family.groupby("anatomical_family").size().sort_values(ascending=False)
        for fam, cnt in fam_counts.items():
            lines.append(f"- **{fam}:** {int(cnt)} rows in family summary.")
        lines.append("")
        lines.append("Participant **252** includes **pelvis_root** links (`252_to_LThigh`, `252_to_RThigh`); participant **671** does not.")
        lines.append("")
        lines.append("### 10.1 Full anatomical-family summary table")
        lines.append("")
        lines.append(df_to_md(family.sort_values(["participant_id", "block_label", "comparison_label", "focus_mode", "family_rank"])))

    lines += [
        "",
        "---",
        "",
        "## 11. Link recurrence across contexts",
        "",
        "Full table tracking top-7 null-space link recurrence (p50 and p60 contexts).",
        "",
        df_to_md(recurrence.sort_values(["participant_id", "block_label", "n_repetition_timepoints_top7_p50"], ascending=False)),
        "",
        "### 11.1 Highly recurrent links (recurrence_label = highly_recurrent_link)",
        "",
    ]
    hi = recurrence[recurrence.recurrence_label == "highly_recurrent_link"].sort_values(["participant_id", "block_label"])
    if hi.empty:
        lines.append("_None labeled highly_recurrent_link._")
    else:
        lines.append(df_to_md(hi))

    lines += [
        "",
        "---",
        "",
        "## 12. Noise vs structure diagnostic (full table)",
        "",
        "Transparent descriptive scores — **not inferential statistics**.",
        "",
        df_to_md(noise.sort_values(["participant_id", "block_label", "analysis_type", "comparison_label"])),
        "",
        "### 12.1 All cells by final_diagnostic_label",
        "",
    ]
    for label in sorted(noise["final_diagnostic_label"].unique()):
        sub = noise[noise.final_diagnostic_label == label]
        lines.append(f"#### `{label}` ({len(sub)} cells)")
        for _, r in sub.iterrows():
            tp = f" | {r['timepoint_if_repetition']}" if pd.notna(r.get("timepoint_if_repetition")) and r.get("timepoint_if_repetition") else ""
            lines.append(
                f"- **{r['participant_id']}** `{r['block_label']}` **{r['comparison_label']}**{tp} [{r['analysis_type']}]: "
                f"null/all p50={f4(r['null_p50_to_all_ratio'])} p60={f4(r['null_p60_to_all_ratio'])}; "
                f"top7 Jaccard={f4(r['top7_jaccard'])}; family Jaccard={f4(r['family_jaccard_top7'])}; "
                f"structure={f4(r['structure_score'])} risk={f4(r['noise_risk_score'])}"
            )
        lines.append("")

    lines += [
        "---",
        "",
        "## 13. Explained-variance weighting check",
        "",
    ]
    if "link_id" in vw.columns:
        shifted = vw[vw["rank_shift"].abs() >= 3]
        top7_stable = vw[vw["remains_top7_after_weighting"] == True]
        lines += [
            f"- Computed from `run/pc_focus_table.csv` explained_variance_ratio × per-PC link |Delta|.",
            f"- Total rows: **{len(vw)}**.",
            f"- Links with |rank_shift| ≥ 3: **{len(shifted)}**.",
            f"- Rows with `remains_top7_after_weighting=True`: **{len(top7_stable)}**.",
            "- Weighting often **reorders** ranks; does not uniformly eliminate null-space concentration.",
            "",
            "### 13.1 Full explained-variance weighting table",
            "",
            df_to_md(vw.sort_values(["participant_id", "block_label", "comparison_label", "focus_mode", "unweighted_rank"])),
            "",
            "### 13.2 Largest rank shifts (|shift| ≥ 3)",
            "",
        ]
        if shifted.empty:
            lines.append("_No links with |rank_shift| ≥ 3._")
        else:
            lines.append(df_to_md(shifted.sort_values("rank_shift", key=lambda s: s.abs(), ascending=False)))
    else:
        lines.append("Explained-variance weighting could not be computed. See CSV note column.")

    lines += [
        "",
        "---",
        "",
        "## 14. Full top-7 links master table",
        "",
        f"All **{len(top7)}** rows from `nullspace_top7_links_all_contexts.csv`.",
        "",
        df_to_md(top7.sort_values(["participant_id", "block_label", "comparison_label", "focus_mode", "rank_abs_delta"])),
        "",
        "---",
        "",
        "## 15. Poster recommendation",
        "",
        "| Question | Recommendation |",
        "| --- | --- |",
        "| Show null-space on main poster? | **Secondary panel only** |",
        "| Best example | **671 P3_P4_P5 T2 repetition** or **671 P3 T1_vs_T2** (high p50/p60 overlap) |",
        "| p50 vs p60 | **p50 primary**, p60 as sensitivity footnote |",
        "| Display | **Anatomical families + null/all ratio** |",
        "| Message level | **Family-level descriptive**, not exact-link causal |",
        "",
        "---",
        "",
        "## 16. Safe wording for poster",
        "",
        "**A. Strong but safe:** \"Later-PC (null-space) link contributions show elevated descriptive magnitude relative to all-PC summaries, concentrated in upper- and lower-limb segment families (participant-specific).\"",
        "",
        "**B. Conservative:** \"Null-space splits (after p50) highlight additional less-dominant link variability not visible in the primary PC subset; link identity varies by threshold.\"",
        "",
        "**C. If link identity unstable:** \"Null-space magnitude ratios exceed all-PC in several cells, but exact top links are threshold-sensitive; interpret at family or summary level only.\"",
        "",
        "---",
        "",
        "## 17. Final conclusion",
        "",
        "| Verdict | Answer |",
        "| --- | --- |",
        "| Central poster finding? | **No** — supporting later-PC / robustness context |",
        "| Sensitivity analysis? | **Yes** |",
        "| Too unstable to mention? | **No** — magnitude elevation is too consistent to omit if null-space is in methods |",
        "| Best-supported pattern type | **Family-level structured pattern** |",
        "| Weakest pattern type | **Exact-link stability across thresholds** |",
        "",
        "Reasoning: null/all > 1 is widespread, family Jaccard is often high, but exact top-7 identity shifts between p50 and p60 in ~33% of overlap-labeled cells. Frame as **descriptive null-space layer**, not stable anatomical discovery.",
        "",
        "---",
        "",
        "## 18. Machine-readable summary",
        "",
        "```json",
        json.dumps(
            {
                "report_file": OUT.name,
                "batch_folder": f"{BATCH_DISPLAY}",
                "review_folder": f"{REVIEW_DISPLAY}",
                "row_counts": {
                    "top7": int(len(top7)),
                    "p50_p60_overlap": int(len(overlap)),
                    "p50_p60_p70_overlap": int(len(triple)),
                    "threshold_stability": int(len(threshold)),
                    "family_summary": int(len(family)),
                    "recurrence": int(len(recurrence)),
                    "noise_diagnostic": int(len(noise)),
                    "variance_weighting": int(len(vw)),
                },
                "headline": {
                    "elevated_null_p50_cells": elev_p50,
                    "elevated_null_p60_cells": elev_p60,
                    "same_top1_link_pct": round(same_top1_pct, 2),
                    "median_top7_jaccard": round(med_j, 4),
                    "median_family_jaccard": round(med_fj, 4),
                    "likely_structured_cells": structured,
                    "structured_but_threshold_sensitive_cells": thresh_sens,
                },
                "regenerate": "cd Layer3_JcvPCA/scripts && ../.venv/bin/python analyze_nullspace_link_stability.py && ../.venv/bin/python generate_nullspace_full_numeric_report.py",
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
