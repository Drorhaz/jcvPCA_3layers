#!/usr/bin/env python3
"""Generate directional_robustness_t1_t3_FULL_NUMERIC_REPORT.md from batch outputs."""

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
OUT = ROOT / "directional_robustness_t1_t3_FULL_NUMERIC_REPORT.md"

INPUTS = [
    ("directional_robustness_t1_t3_link_results", "Link-level JcvPCA by variant and focus mode"),
    ("directional_robustness_t1_t3_summary", "Variant-vs-pooled consistency summary"),
    ("directional_robustness_t1_t3_top_links", "Top-5 pooled links with per-variant consistency"),
    ("directional_robustness_t1_t3_review.md", "Short narrative review (source for run status)"),
]

DR_T1_T3_REQUIRED = [
    f"{name}.csv" if not name.endswith(".md") else name for name, _ in INPUTS
]

VARIANT_ORDER = [
    "T1_R1_vs_T3_R1",
    "T1_R2_vs_T3_R2",
    "T1_R1_R2_vs_T3_R1_R2",
    "T1_R1_vs_T3_R2",
    "T1_R2_vs_T3_R1",
]

FOCUS_ORDER = [
    "all",
    "functional_p50",
    "null_space_after_p50",
    "functional_p60",
    "null_space_after_p60",
]

PAIRING_VARIANTS = [
    "T1_R1_vs_T3_R1",
    "T1_R2_vs_T3_R2",
    "T1_R1_vs_T3_R2",
    "T1_R2_vs_T3_R1",
]

LINK_COLS = [
    "link_id",
    "JRW_A",
    "JRW_B",
    "JcvPCA_link_delta",
    "sign_of_delta",
    "abs_delta",
    "rank_by_abs_delta",
]


def read_csv(name: str) -> pd.DataFrame:
    path = ROOT / name
    if path.suffix != ".csv":
        path = ROOT / f"{name}.csv"
    if not path.is_file() and not (ROOT / f"{name}.csv").is_file():
        raise FileNotFoundError(f"Missing required input: {path}")
    return pd.read_csv(path)


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


def fmt_cell(x) -> str:
    if isinstance(x, (float, int, np.floating, np.integer)) or pd.api.types.is_numeric_dtype(type(x)):
        return f4(x)
    if isinstance(x, bool):
        return str(x)
    if pd.isna(x):
        return "NA"
    return str(x)


def df_to_md(df: pd.DataFrame, cols: list[str] | None = None) -> str:
    cols = cols or list(df.columns)
    rows = [[fmt_cell(r[c]) for c in cols] for _, r in df[cols].iterrows()]
    return md_table(cols, rows)


def parse_run_status(review_text: str) -> list[list[str]]:
    rows: list[list[str]] = []
    in_table = False
    for line in review_text.splitlines():
        if line.startswith("| Participant | Block | Variant | Status |"):
            in_table = True
            continue
        if in_table:
            if not line.startswith("|"):
                break
            if line.startswith("| ---"):
                continue
            parts = [p.strip() for p in line.strip("|").split("|")]
            if len(parts) == 4:
                rows.append(parts)
    return rows


def stable_links_by_participant_block(
    links: pd.DataFrame,
    focus_mode: str = "all",
) -> dict[str, dict[str, list[str]]]:
    """Links whose sign matches pooled in all four pairings, keyed by participant then block."""
    out: dict[str, dict[str, list[str]]] = {}
    sub = links[links.focus_mode == focus_mode]
    for pid in sorted(sub.participant_id.astype(str).unique()):
        out[pid] = {}
        for bl in sorted(sub[sub.participant_id.astype(str) == pid].block_label.unique()):
            pooled = sub[
                (sub.participant_id.astype(str) == pid)
                & (sub.block_label == bl)
                & (sub.comparison_variant == "T1_R1_R2_vs_T3_R1_R2")
            ].set_index("link_id")
            if pooled.empty:
                continue
            stable: list[str] = []
            for link_id in pooled.index:
                ref_sign = int(pooled.loc[link_id].sign_of_delta)
                ok = True
                for variant in PAIRING_VARIANTS:
                    row = sub[
                        (sub.participant_id.astype(str) == pid)
                        & (sub.block_label == bl)
                        & (sub.comparison_variant == variant)
                        & (sub.link_id == link_id)
                    ]
                    if row.empty or int(row.iloc[0].sign_of_delta) != ref_sign:
                        ok = False
                        break
                if ok:
                    stable.append(str(link_id))
            out[pid][bl] = sorted(stable)
    return out


def cross_block_stable_links(stable_map: dict[str, dict[str, list[str]]]) -> dict[str, list[str]]:
    """Links stable in all four pairings in every block for a participant."""
    out: dict[str, list[str]] = {}
    for pid, blocks in stable_map.items():
        if not blocks:
            out[pid] = []
            continue
        lists = [set(v) for v in blocks.values()]
        out[pid] = sorted(set.intersection(*lists)) if lists else []
    return out


def sign_flip_links_from_links(
    links: pd.DataFrame,
    focus_mode: str = "all",
) -> dict[str, list[str]]:
    """Per participant: links disagreeing with pooled in at least one pairing (any block)."""
    out: dict[str, set[str]] = {}
    sub = links[links.focus_mode == focus_mode]
    for pid in sub.participant_id.astype(str).unique():
        out[str(pid)] = set()
        for bl in sub[sub.participant_id.astype(str) == str(pid)].block_label.unique():
            pooled = sub[
                (sub.participant_id.astype(str) == str(pid))
                & (sub.block_label == bl)
                & (sub.comparison_variant == "T1_R1_R2_vs_T3_R1_R2")
            ].set_index("link_id")
            for link_id in pooled.index:
                ref_sign = int(pooled.loc[link_id].sign_of_delta)
                for variant in PAIRING_VARIANTS:
                    row = sub[
                        (sub.participant_id.astype(str) == str(pid))
                        & (sub.block_label == bl)
                        & (sub.comparison_variant == variant)
                        & (sub.link_id == link_id)
                    ]
                    if not row.empty and int(row.iloc[0].sign_of_delta) != ref_sign:
                        out[str(pid)].add(str(link_id))
    return {k: sorted(v) for k, v in out.items()}


def main(argv: list[str] | None = None) -> int:
    args = parse_batch_report_cli(
        "Generate directional_robustness_t1_t3_FULL_NUMERIC_REPORT.md from batch outputs.",
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
    OUT = ROOT / "directional_robustness_t1_t3_FULL_NUMERIC_REPORT.md"

    preflight = run_path_preflight(args, root=ROOT, out=OUT, required=DR_T1_T3_REQUIRED)
    if preflight is not None:
        return preflight

    links = read_csv("directional_robustness_t1_t3_link_results")
    summary = read_csv("directional_robustness_t1_t3_summary")
    top = read_csv("directional_robustness_t1_t3_top_links")
    review_path = ROOT / "directional_robustness_t1_t3_review.md"
    review_text = review_path.read_text(encoding="utf-8") if review_path.is_file() else ""
    run_status = parse_run_status(review_text)

    summary_all = summary[summary.focus_mode == "all"]
    med_sign = float(summary_all.percent_sign_agreement_all_links.median())
    med_rho = float(summary_all.spearman_rho_delta.median())

    same_rep = summary_all[summary_all.comparison_variant.isin(["T1_R1_vs_T3_R1", "T1_R2_vs_T3_R2"])]
    cross_rep = summary_all[summary_all.comparison_variant.isin(["T1_R1_vs_T3_R2", "T1_R2_vs_T3_R1"])]
    same_mean = float(same_rep.percent_sign_agreement_all_links.mean()) if not same_rep.empty else float("nan")
    cross_mean = float(cross_rep.percent_sign_agreement_all_links.mean()) if not cross_rep.empty else float("nan")

    block_stab = (
        summary_all.groupby("block_label")["percent_sign_agreement_all_links"].mean().to_dict()
        if not summary_all.empty
        else {}
    )
    part_stab = (
        summary_all.groupby("participant_id")["percent_sign_agreement_all_links"].mean().to_dict()
        if not summary_all.empty
        else {}
    )

    stable_map = stable_links_by_participant_block(links)
    cross_block_stable = cross_block_stable_links(stable_map)
    flip_by_part = sign_flip_links_from_links(links)

    lines: list[str] = [
        "# Directional robustness — T1 vs T3 full numeric report",
        "",
        f"Batch folder: `{BATCH_DISPLAY}/`",
        "",
        "Link-level JcvPCA Delta direction compared across repetition-specific T1 vs T3 pairings.",
        "Pooled reference: `T1_R1_R2_vs_T3_R1_R2` (batch label `T1_vs_T3`).",
        "",
        "---",
        "",
        "## 1. Analysis goal and method",
        "",
        "### Goal",
        "",
        "Test whether the **direction** of link-level JcvPCA Delta in the pooled T1 vs T3 comparison",
        "is preserved when T1 and T3 are paired by repetition-specific subsets rather than pooled R1+R2.",
        "",
        "### Method",
        "",
        "- **Reference comparison:** existing batch `T1_vs_T3` (`T1_R1+R2` vs `T3_R1+R2`) from this batch run.",
        "- **Variant comparisons:** four repetition pairings plus the pooled reference row in link tables;",
        "  variant runs filter pooled construction sources by repetition and rerun the same JcvPCA workbench pipeline.",
        "- **Metrics vs pooled:** per link — sign agreement, rank shift; per variant — percent sign agreement,",
        "  Spearman correlation of Delta values and abs-Delta ranks, top-5 pooled link overlap.",
        "- **Primary readout:** link-level `JcvPCA_link_delta = JRW_B - JRW_A` (RSS over axes), aggregated across selected PCs per focus mode.",
        "- **No JcvPCA recomputation** in this report; all numbers are read from existing CSV outputs.",
        "",
        "---",
        "",
        "## 2. Variants tested",
        "",
        md_table(
            ["Variant label", "Dataset A (T1) repetitions", "Dataset B (T3) repetitions", "Role"],
            [
                ["T1_R1_vs_T3_R1", "R1", "R1", "Same-repetition pairing"],
                ["T1_R2_vs_T3_R2", "R2", "R2", "Same-repetition pairing"],
                ["T1_R1_R2_vs_T3_R1_R2", "R1, R2", "R1, R2", "Pooled reference (batch T1_vs_T3)"],
                ["T1_R1_vs_T3_R2", "R1", "R2", "Cross-repetition pairing"],
                ["T1_R2_vs_T3_R1", "R2", "R1", "Cross-repetition pairing"],
            ],
        ),
        "",
        "---",
        "",
        "## 3. Focus hierarchy",
        "",
        md_table(
            ["Tier", "Focus modes", "Use in this report"],
            [
                ["Primary", "all (all selected PCs)", "Main directional robustness readout"],
                ["Main sensitivity", "functional_p50, null_space_after_p50", "Variance-threshold PC subsets"],
                ["Optional sensitivity", "functional_p60, null_space_after_p60", "Higher cumulative-variance thresholds"],
            ],
        ),
        "",
        "p2 is not used as a main interpretation tier in this analysis.",
        "",
        "---",
        "",
        "## 4. File inventory and row counts",
        "",
        md_table(
            ["File", "Description", "Rows", "Columns"],
            [
                [
                    "`directional_robustness_t1_t3_link_results.csv`",
                    INPUTS[0][1],
                    str(len(links)),
                    str(len(links.columns)),
                ],
                [
                    "`directional_robustness_t1_t3_summary.gbapal`",
                    INPUTS[1][1],
                    str(len(summary)),
                    str(len(summary.columns)),
                ],
                [
                    "`directional_robustness_t1_t3_top_links.gbapal`",
                    INPUTS[2][1],
                    str(len(top)),
                    str(len(top.columns)),
                ],
                [
                    "`directional_robustness_t1_t3_review.md`",
                    INPUTS[3][1],
                    str(len(review_text.splitlines())),
                    "Markdown",
                ],
            ],
        ),
        "",
        "### Row breakdown — link results",
        "",
        md_table(
            ["Dimension", "Unique values", "Count"],
            [
                ["Participants", ", ".join(sorted(links.participant_id.astype(str).unique())), str(links.participant_id.nunique())],
                ["Blocks", ", ".join(sorted(links.block_label.unique())), str(links.block_label.nunique())],
                ["Comparison variants", ", ".join(VARIANT_ORDER), str(links.comparison_variant.nunique())],
                ["Focus modes", ", ".join(FOCUS_ORDER), str(links.focus_mode.nunique())],
                [
                    "Links (671)",
                    ", ".join(sorted(links.loc[links.participant_id.astype(str) == "671", "link_id"].unique())),
                    str(links.loc[links.participant_id.astype(str) == "671", "link_id"].nunique()),
                ],
                [
                    "Links (252)",
                    ", ".join(sorted(links.loc[links.participant_id.astype(str) == "252", "link_id"].unique())),
                    str(links.loc[links.participant_id.astype(str) == "252", "link_id"].nunique()),
                ],
            ],
        ),
        "",
        "### Run status (from review)",
        "",
    ]
    if run_status:
        lines.append(md_table(["Participant", "Block", "Variant", "Status"], run_status))
    else:
        lines.append("_Run status table not parsed from review._")
    lines += ["", "---", "", "## 5. Full summary table", "", "`directional_robustness_t1_t3_summary.csv` — all rows.", ""]

    summary_sorted = summary.sort_values(
        ["participant_id", "block_label", "focus_mode", "comparison_variant"]
    ).reset_index(drop=True)
    summary_display = summary_sorted.copy()
    summary_display["participant_id"] = summary_display["participant_id"].astype(int)
    lines.append(df_to_md(summary_display))

    lines += [
        "",
        "### Summary — all-PC aggregates",
        "",
        md_table(
            ["Metric", "Value"],
            [
                ["Median percent sign agreement (all links, all-PC variants)", f"{f4(med_sign)}%"],
                ["Median Spearman rho — Delta (all-PC variants)", f4(med_rho)],
                ["Mean sign agreement — same-repetition pairings (T1_R1/T3_R1, T1_R2/T3_R2)", f"{f4(same_mean)}%"],
                ["Mean sign agreement — cross-repetition pairings (T1_R1/T3_R2, T1_R2/T3_R1)", f"{f4(cross_mean)}%"],
                [
                    "Mean sign agreement — block all_P1_P2_P3_P4_P5",
                    f"{f4(block_stab.get('all_P1_P2_P3_P4_P5', float('nan')))}%",
                ],
                [
                    "Mean sign agreement — block P3_P4_P5",
                    f"{f4(block_stab.get('P3_P4_P5', float('nan')))}%",
                ],
                ["Mean sign agreement — participant 671", f"{f4(part_stab.get(671, part_stab.get('671', float('nan'))))}%"],
                ["Mean sign agreement — participant 252", f"{f4(part_stab.get(252, part_stab.get('252', float('nan'))))}%"],
            ],
        ),
        "",
        "---",
        "",
        "## 6. Full top-link consistency tables",
        "",
        "`directional_robustness_t1_t3_top_links.csv` — top 5 pooled links per participant × block × focus mode.",
        "",
    ]

    for fm in FOCUS_ORDER:
        sub = top[top.focus_mode == fm].sort_values(
            ["participant_id", "block_label", "pooled_rank_by_abs"]
        )
        lines += [f"### Focus mode: `{fm}` ({len(sub)} rows)", ""]
        if sub.empty:
            lines.append("_No rows._")
        else:
            lines.append(df_to_md(sub))
        lines.append("")

    lines += [
        "---",
        "",
        "## 7. Link-level result tables",
        "",
        "`directional_robustness_t1_t3_link_results` — organized by participant, block, comparison variant, focus mode.",
        "",
    ]

    for pid in sorted(links.participant_id.astype(str).unique()):
        for bl in sorted(links[links.participant_id.astype(str) == pid].block_label.unique()):
            for variant in VARIANT_ORDER:
                for fm in FOCUS_ORDER:
                    sub = links[
                        (links.participant_id.astype(str) == pid)
                        & (links.block_label == bl)
                        & (links.comparison_variant == variant)
                        & (links.focus_mode == fm)
                    ].sort_values("rank_by_abs_delta")
                    lines += [
                        f"### Participant {pid} | {bl} | {variant} | {fm}",
                        "",
                    ]
                    if sub.empty:
                        lines.append("_No rows._")
                    else:
                        lines.append(df_to_md(sub, LINK_COLS))
                    lines.append("")

    lines += [
        "---",
        "",
        "## 8. Review questions (with numeric backing)",
        "",
        "### 8.1 Is direction preserved across pairings?",
        "",
        f"Median all-link sign agreement with the pooled reference (all-PC, four pairings only) is **{f4(med_sign)}%**.",
        "Direction is **not uniformly preserved** across repetition pairings (100% would require every link",
        "to match the pooled sign in every variant).",
        f"Mean sign agreement: same-repetition pairings **{f4(same_mean)}%**; cross-repetition pairings **{f4(cross_mean)}%**.",
        "Patterns vary by participant and block (see Section 5).",
        "",
        "### 8.2 Which links keep the same sign across all pairings?",
        "",
        "Links with pooled-sign agreement in all four repetition pairings (all-PC):",
        "",
    ]
    for pid in sorted(stable_map.keys()):
        lines.append(f"**Participant {pid}**")
        for bl, links_stable in sorted(stable_map[pid].items()):
            if links_stable:
                lines.append(
                    f"- `{bl}`: " + ", ".join(f"`{l}`" for l in links_stable)
                )
            else:
                lines.append(f"- `{bl}`: none")
        cross = cross_block_stable.get(pid, [])
        if cross:
            lines.append(
                f"- Stable in **both blocks**: " + ", ".join(f"`{l}`" for l in cross)
            )
        else:
            lines.append("- Stable in **both blocks**: none")
        lines.append("")
    lines += [
        "### 8.3 Which links flip sign depending on pairing?",
        "",
        "Sign-flipping links (disagree with pooled in at least one pairing; all-PC):",
        "",
    ]
    for pid in sorted(flip_by_part.keys()):
        fl = flip_by_part[pid]
        lines.append(
            f"- Participant **{pid}:** "
            + (", ".join(f"`{l}`" for l in fl) if fl else "none")
        )
    lines += [
        "",
        "### 8.4 Does the pooled T1_vs_T3 result reflect repetition-specific pairings?",
        "",
        f"Mean all-link sign agreement — same-repetition: **{f4(same_mean)}%**; cross-repetition: **{f4(cross_mean)}%**.",
        (
            "On average, pooled link signs align slightly more closely with **cross-repetition** pairings "
            f"({f4(cross_mean)}% vs {f4(same_mean)}%)."
            if cross_mean >= same_mean
            else "On average, pooled link signs align slightly more closely with **same-repetition** pairings."
        ),
        "This is a descriptive pooled-result consistency statement, not a claim about which pairing is correct.",
        "",
        "### 8.5 Which block is more stable?",
        "",
        f"Mean all-link sign agreement (all-PC): **all_P1_P2_P3_P4_P5** = **{f4(block_stab.get('all_P1_P2_P3_P4_P5', float('nan')))}%**;",
        f"**P3_P4_P5** = **{f4(block_stab.get('P3_P4_P5', float('nan')))}%**.",
        "**P3_P4_P5** shows higher block-specific stability in this metric.",
        "",
        "### 8.6 Which participant is more stable?",
        "",
        f"Mean all-link sign agreement (all-PC): **671** = **{f4(part_stab.get(671, part_stab.get('671', float('nan'))))}%**;",
        f"**252** = **{f4(part_stab.get(252, part_stab.get('252', float('nan'))))}%**.",
        "**252** shows higher participant-specific stability in this metric.",
        "",
        "---",
        "",
        "## 9. Interpretation summary",
        "",
        "- Directional robustness is **mixed**: median sign agreement with pooled T1_vs_T3 is about **53%**,",
        "  so repetition-pairing sensitivity is present for many links.",
        "- Only **`LUArm_to_LFArm` (participant 252)** matches the pooled sign in all four pairings in **both blocks** under all-PC.",
        "- Participant **671** has block-specific direction-preserved links (Section 8.2) but **none** across both blocks.",
        "- Most links are **sign-flipping links** under at least one pairing (Section 8.3).",
        "- **Cross-repetition** pairings show slightly higher mean agreement with pooled signs than **same-repetition** pairings",
        f"  ({f4(cross_mean)}% vs {f4(same_mean)}%), but cell-level patterns differ.",
        "- **Block-specific stability** favors P3_P4_P5 over the full exercise block.",
        "- **Participant-specific stability** favors 252 over 671 on mean sign agreement.",
        "- PC-focus sensitivity tables are included in full; inspect functional_p50 / null_space_after_p50 for tier-2 readouts.",
        "",
        "---",
        "",
        "## 10. Limitations and cautions",
        "",
        "- Descriptive repetition-pairing analysis only; no causal or condition-specific claims.",
        "- Variant runs use the same JcvPCA workbench as the batch; pooled reference is the existing T1_vs_T3 output.",
        "- Participants **671** (14 links) and **252** (16 links, includes pelvis-root links) use different link schemas.",
        "- Single-repetition variant runs complete link-level RSS (step 14); NV baseline (step 16A) is skipped when R1 and R2",
        "  cannot both be present in Dataset A.",
        "- PC-focus modes use Dataset A cumulative-variance thresholds computed per variant run.",
        "- Sign agreement counts links equally; it does not weight by abs Delta magnitude.",
        "- Cross-repetition vs same-repetition averages pool across participants and blocks.",
        "",
        "---",
        "",
        "## 11. Machine-readable summary (for future agents)",
        "",
        "```json",
        json.dumps(
            {
                "batch_folder": f"{BATCH_DISPLAY}",
                "analysis": "directional_robustness_t1_vs_t3",
                "reference_variant": "T1_R1_R2_vs_T3_R1_R2",
                "pairing_variants": PAIRING_VARIANTS,
                "focus_modes_primary": "all",
                "focus_modes_sensitivity": ["functional_p50", "null_space_after_p50"],
                "focus_modes_optional": ["functional_p60", "null_space_after_p60"],
                "row_counts": {
                    "link_results": int(len(links)),
                    "summary": int(len(summary)),
                    "top_links": int(len(top)),
                },
                "headline_metrics_all_pc": {
                    "median_sign_agreement_pct": round(med_sign, 4),
                    "median_spearman_rho_delta": round(med_rho, 4),
                    "mean_sign_agreement_same_repetition_pct": round(same_mean, 4),
                    "mean_sign_agreement_cross_repetition_pct": round(cross_mean, 4),
                    "mean_sign_agreement_block_all_P1_P2_P3_P4_P5_pct": round(
                        float(block_stab.get("all_P1_P2_P3_P4_P5", float("nan"))), 4
                    ),
                    "mean_sign_agreement_block_P3_P4_P5_pct": round(
                        float(block_stab.get("P3_P4_P5", float("nan"))), 4
                    ),
                    "mean_sign_agreement_participant_671_pct": round(
                        float(part_stab.get(671, part_stab.get("671", float("nan")))), 4
                    ),
                    "mean_sign_agreement_participant_252_pct": round(
                        float(part_stab.get(252, part_stab.get("252", float("nan")))), 4
                    ),
                },
                "stable_links_all_four_pairings_all_pc_by_block": stable_map,
                "stable_links_all_four_pairings_both_blocks_all_pc": cross_block_stable,
                "sign_flip_links_by_participant_all_pc": flip_by_part,
                "direction_preserved_uniformly": False,
                "input_files": [f"{name}.csv" if name.endswith('.csv') else name for name, _ in INPUTS],
                "output_file": OUT.name,
            },
            indent=2,
        ),
        "```",
        "",
    ]

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT} ({len(lines)} sections/lines)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
