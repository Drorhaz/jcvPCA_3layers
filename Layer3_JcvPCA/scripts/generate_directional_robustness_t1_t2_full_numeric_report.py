#!/usr/bin/env python3
"""Generate directional_robustness_t1_t2_FULL_NUMERIC_REPORT.md from batch outputs."""

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
OUT = ROOT / "directional_robustness_t1_t2_FULL_NUMERIC_REPORT.md"
PREFIX = "directional_robustness_t1_t2"
POOLED_VARIANT = "T1_R1_R2_vs_T2_R1_R2"
COMPARISON_LABEL = "T1_vs_T2"

INPUTS = [
    (f"{PREFIX}_link_results", "Link-level JcvPCA by variant and focus mode"),
    (f"{PREFIX}_summary", "Variant-vs-pooled consistency summary"),
    (f"{PREFIX}_top_links", "Top-5 pooled links with per-variant consistency"),
]

OPTIONAL_T3_INPUTS = [
    ("directional_robustness_t1_t3_summary", "T1 vs T3 variant-vs-pooled summary (comparison)"),
    ("directional_robustness_t1_t3_top_links", "T1 vs T3 top-5 pooled links (comparison)"),
]

DR_T1_T2_REQUIRED = [f"{name}.csv" for name, _ in INPUTS]

VARIANT_ORDER = [
    "T1_R1_vs_T2_R1",
    "T1_R2_vs_T2_R2",
    POOLED_VARIANT,
    "T1_R1_vs_T2_R2",
    "T1_R2_vs_T2_R1",
]

FOCUS_ORDER = [
    "all",
    "functional_p50",
    "null_space_after_p50",
    "functional_p60",
    "null_space_after_p60",
]

PAIRING_VARIANTS = [
    "T1_R1_vs_T2_R1",
    "T1_R2_vs_T2_R2",
    "T1_R1_vs_T2_R2",
    "T1_R2_vs_T2_R1",
]

SAME_REP_VARIANTS = ["T1_R1_vs_T2_R1", "T1_R2_vs_T2_R2"]
CROSS_REP_VARIANTS = ["T1_R1_vs_T2_R2", "T1_R2_vs_T2_R1"]

T3_POOLED_VARIANT = "T1_R1_R2_vs_T3_R1_R2"
T3_PAIRING_VARIANTS = [
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


def read_csv_optional(name: str) -> pd.DataFrame | None:
    path = ROOT / f"{name}.csv" if not name.endswith(".csv") else ROOT / name
    return pd.read_csv(path) if path.is_file() else None


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


def run_status_from_summary(summary: pd.DataFrame) -> list[list[str]]:
    cols = ["participant_id", "block_label", "comparison_variant", "run_status"]
    if "run_status" not in summary.columns:
        return []
    sub = summary[summary.comparison_variant.isin(PAIRING_VARIANTS + [POOLED_VARIANT])]
    sub = sub.drop_duplicates(subset=["participant_id", "block_label", "comparison_variant"])
    sub = sub.sort_values(["participant_id", "block_label", "comparison_variant"])
    return [[str(r[c]) for c in cols] for _, r in sub[cols].iterrows()]


def stable_links_by_participant_block(
    links: pd.DataFrame,
    focus_mode: str = "all",
    pooled_variant: str = POOLED_VARIANT,
    pairing_variants: list[str] | None = None,
) -> dict[str, dict[str, list[str]]]:
    """Links whose sign matches pooled in all four pairings, keyed by participant then block."""
    pairing_variants = pairing_variants or PAIRING_VARIANTS
    out: dict[str, dict[str, list[str]]] = {}
    sub = links[links.focus_mode == focus_mode]
    for pid in sorted(sub.participant_id.astype(str).unique()):
        out[pid] = {}
        for bl in sorted(sub[sub.participant_id.astype(str) == pid].block_label.unique()):
            pooled = sub[
                (sub.participant_id.astype(str) == pid)
                & (sub.block_label == bl)
                & (sub.comparison_variant == pooled_variant)
            ].set_index("link_id")
            if pooled.empty:
                continue
            stable: list[str] = []
            for link_id in pooled.index:
                ref_sign = int(pooled.loc[link_id].sign_of_delta)
                ok = True
                for variant in pairing_variants:
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
    pooled_variant: str = POOLED_VARIANT,
    pairing_variants: list[str] | None = None,
) -> dict[str, list[str]]:
    """Per participant: links disagreeing with pooled in at least one pairing (any block)."""
    pairing_variants = pairing_variants or PAIRING_VARIANTS
    out: dict[str, set[str]] = {}
    sub = links[links.focus_mode == focus_mode]
    for pid in sub.participant_id.astype(str).unique():
        out[str(pid)] = set()
        for bl in sub[sub.participant_id.astype(str) == str(pid)].block_label.unique():
            pooled = sub[
                (sub.participant_id.astype(str) == str(pid))
                & (sub.block_label == bl)
                & (sub.comparison_variant == pooled_variant)
            ].set_index("link_id")
            for link_id in pooled.index:
                ref_sign = int(pooled.loc[link_id].sign_of_delta)
                for variant in pairing_variants:
                    row = sub[
                        (sub.participant_id.astype(str) == str(pid))
                        & (sub.block_label == bl)
                        & (sub.comparison_variant == variant)
                        & (sub.link_id == link_id)
                    ]
                    if not row.empty and int(row.iloc[0].sign_of_delta) != ref_sign:
                        out[str(pid)].add(str(link_id))
    return {k: sorted(v) for k, v in out.items()}


def compute_pairing_metrics(
    summary: pd.DataFrame,
    focus_mode: str,
    pairing_variants: list[str] | None = None,
    same_rep_variants: list[str] | None = None,
    cross_rep_variants: list[str] | None = None,
) -> dict[str, float]:
    pairing_variants = pairing_variants or PAIRING_VARIANTS
    same_rep_variants = same_rep_variants or SAME_REP_VARIANTS
    cross_rep_variants = cross_rep_variants or CROSS_REP_VARIANTS
    sub = summary[
        (summary.focus_mode == focus_mode) & (summary.comparison_variant.isin(pairing_variants))
    ]
    same_rep = sub[sub.comparison_variant.isin(same_rep_variants)]
    cross_rep = sub[sub.comparison_variant.isin(cross_rep_variants)]
    block_stab = sub.groupby("block_label")["percent_sign_agreement_all_links"].mean().to_dict()
    part_stab = sub.groupby("participant_id")["percent_sign_agreement_all_links"].mean().to_dict()
    return {
        "median_sign": float(sub.percent_sign_agreement_all_links.median()) if not sub.empty else float("nan"),
        "median_rho": float(sub.spearman_rho_delta.median()) if not sub.empty else float("nan"),
        "same_mean": float(same_rep.percent_sign_agreement_all_links.mean()) if not same_rep.empty else float("nan"),
        "cross_mean": float(cross_rep.percent_sign_agreement_all_links.mean()) if not cross_rep.empty else float("nan"),
        "block_stab": block_stab,
        "part_stab": part_stab,
    }


def part_stab_value(part_stab: dict, pid: int | str) -> float:
    return float(part_stab.get(pid, part_stab.get(str(pid), part_stab.get(int(pid) if str(pid).isdigit() else pid, float("nan")))))


def render_stable_links_section(stable_map: dict[str, dict[str, list[str]]], cross_block_stable: dict[str, list[str]]) -> list[str]:
    lines: list[str] = []
    for pid in sorted(stable_map.keys()):
        lines.append(f"**Participant {pid}**")
        for bl, links_stable in sorted(stable_map[pid].items()):
            if links_stable:
                lines.append(f"- `{bl}`: " + ", ".join(f"`{l}`" for l in links_stable))
            else:
                lines.append(f"- `{bl}`: none")
        cross = cross_block_stable.get(pid, [])
        if cross:
            lines.append(f"- Stable in **both blocks**: " + ", ".join(f"`{l}`" for l in cross))
        else:
            lines.append("- Stable in **both blocks**: none")
        lines.append("")
    return lines


def render_flip_links_section(flip_by_part: dict[str, list[str]]) -> list[str]:
    lines: list[str] = []
    for pid in sorted(flip_by_part.keys()):
        fl = flip_by_part[pid]
        lines.append(
            f"- Participant **{pid}:** "
            + (", ".join(f"`{l}`" for l in fl) if fl else "none")
        )
    return lines


def focus_interpretation_lines(
    focus_mode: str,
    metrics: dict[str, float],
    stable_map: dict[str, dict[str, list[str]]],
    cross_block_stable: dict[str, list[str]],
    flip_by_part: dict[str, list[str]],
    comparison_label: str,
) -> list[str]:
    block_stab = metrics["block_stab"]
    part_stab = metrics["part_stab"]
    med_sign = metrics["median_sign"]
    same_mean = metrics["same_mean"]
    cross_mean = metrics["cross_mean"]
    all_block = block_stab.get("all_P1_P2_P3_P4_P5", float("nan"))
    p3_block = block_stab.get("P3_P4_P5", float("nan"))
    p671 = part_stab_value(part_stab, 671)
    p252 = part_stab_value(part_stab, 252)
    pooled_closer = "cross-repetition" if cross_mean >= same_mean else "same-repetition"
    block_higher = "P3_P4_P5" if p3_block >= all_block else "all_P1_P2_P3_P4_P5"
    part_higher = "252" if p252 >= p671 else "671"
    return [
        f"Median all-link sign agreement with pooled reference ({focus_mode}, four pairings): **{f4(med_sign)}%**.",
        f"Mean sign agreement — same-repetition pairings: **{f4(same_mean)}%**; cross-repetition: **{f4(cross_mean)}%**.",
        (
            f"Pooled {comparison_label} link signs align more closely with **{pooled_closer}** pairings "
            f"({f4(max(same_mean, cross_mean))}% vs {f4(min(same_mean, cross_mean))}%) on average."
        ),
        f"Mean sign agreement — **all_P1_P2_P3_P4_P5** = **{f4(all_block)}%**; **P3_P4_P5** = **{f4(p3_block)}%**.",
        f"**{block_higher}** has the higher block-level mean sign agreement under `{focus_mode}`.",
        f"Mean sign agreement — participant **671** = **{f4(p671)}%**; **252** = **{f4(p252)}%**.",
        f"Participant **{part_higher}** has the higher participant-level mean sign agreement under `{focus_mode}`.",
        "",
        "Links with pooled-sign agreement in all four pairings:",
        "",
        *render_stable_links_section(stable_map, cross_block_stable),
        "Sign-flipping links (disagree with pooled in at least one pairing):",
        "",
        *render_flip_links_section(flip_by_part),
        "",
    ]


def main(argv: list[str] | None = None) -> int:
    args = parse_batch_report_cli(
        "Generate directional_robustness_t1_t2_FULL_NUMERIC_REPORT.md from batch outputs.",
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
    OUT = ROOT / "directional_robustness_t1_t2_FULL_NUMERIC_REPORT.md"

    preflight = run_path_preflight(args, root=ROOT, out=OUT, required=DR_T1_T2_REQUIRED)
    if preflight is not None:
        return preflight

    links = read_csv(f"{PREFIX}_link_results")
    summary = read_csv(f"{PREFIX}_summary")
    top = read_csv(f"{PREFIX}_top_links")
    t3_summary = read_csv_optional("directional_robustness_t1_t3_summary")
    t3_top = read_csv_optional("directional_robustness_t1_t3_top_links")
    run_status = run_status_from_summary(summary)

    metrics_by_focus: dict[str, dict] = {}
    stable_by_focus: dict[str, dict] = {}
    cross_by_focus: dict[str, dict] = {}
    flip_by_focus: dict[str, dict] = {}
    for fm in FOCUS_ORDER:
        metrics_by_focus[fm] = compute_pairing_metrics(summary, fm)
        stable_by_focus[fm] = stable_links_by_participant_block(links, fm)
        cross_by_focus[fm] = cross_block_stable_links(stable_by_focus[fm])
        flip_by_focus[fm] = sign_flip_links_from_links(links, fm)

    m_all = metrics_by_focus["all"]
    med_sign = m_all["median_sign"]
    med_rho = m_all["median_rho"]
    same_mean = m_all["same_mean"]
    cross_mean = m_all["cross_mean"]
    block_stab = m_all["block_stab"]
    part_stab = m_all["part_stab"]
    stable_map = stable_by_focus["all"]
    cross_block_stable = cross_by_focus["all"]
    flip_by_part = flip_by_focus["all"]

    m_fp50 = metrics_by_focus["functional_p50"]
    m_ns50 = metrics_by_focus["null_space_after_p50"]
    m_ns60 = metrics_by_focus["null_space_after_p60"]

    lines: list[str] = [
        "# Directional robustness — T1 vs T2 full numeric report",
        "",
        f"Batch folder: `{BATCH_DISPLAY}/`",
        "",
        "Link-level JcvPCA Delta direction compared across repetition-specific T1 vs T2 pairings.",
        f"Pooled reference: `{POOLED_VARIANT}` (batch label `{COMPARISON_LABEL}`).",
        "",
        "---",
        "",
        "## 1. Analysis goal and method",
        "",
        "### Goal",
        "",
        f"Test whether the **direction** of link-level JcvPCA Delta in the pooled {COMPARISON_LABEL} comparison",
        "is preserved when T1 and T2 are paired by repetition-specific subsets rather than pooled R1+R2.",
        "",
        "### Method",
        "",
        f"- **Reference comparison:** existing batch `{COMPARISON_LABEL}` (`T1_R1+R2` vs `T2_R1+R2`) from this batch run.",
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
            ["Variant label", "Dataset A (T1) repetitions", "Dataset B (T2) repetitions", "Role"],
            [
                ["T1_R1_vs_T2_R1", "R1", "R1", "Same-repetition pairing"],
                ["T1_R2_vs_T2_R2", "R2", "R2", "Same-repetition pairing"],
                [POOLED_VARIANT, "R1, R2", "R1, R2", f"Pooled reference (batch {COMPARISON_LABEL})"],
                ["T1_R1_vs_T2_R2", "R1", "R2", "Cross-repetition pairing"],
                ["T1_R2_vs_T2_R1", "R2", "R1", "Cross-repetition pairing"],
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
                [f"`{PREFIX}_link_results.csv`", INPUTS[0][1], str(len(links)), str(len(links.columns))],
                [f"`{PREFIX}_summary.csv`", INPUTS[1][1], str(len(summary)), str(len(summary.columns))],
                [f"`{PREFIX}_top_links.csv`", INPUTS[2][1], str(len(top)), str(len(top.columns))],
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
        "### Run status (from summary `run_status` column)",
        "",
    ]
    if run_status:
        lines.append(md_table(["Participant", "Block", "Variant", "Status"], run_status))
    else:
        lines.append("_Run status not available in summary._")
    lines += ["", "---", "", "## 5. Full summary table", "", f"`{PREFIX}_summary.csv` — all rows.", ""]

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
                ["Mean sign agreement — same-repetition pairings (T1_R1/T2_R1, T1_R2/T2_R2)", f"{f4(same_mean)}%"],
                ["Mean sign agreement — cross-repetition pairings (T1_R1/T2_R2, T1_R2/T2_R1)", f"{f4(cross_mean)}%"],
                ["Mean sign agreement — block all_P1_P2_P3_P4_P5", f"{f4(block_stab.get('all_P1_P2_P3_P4_P5', float('nan')))}%"],
                ["Mean sign agreement — block P3_P4_P5", f"{f4(block_stab.get('P3_P4_P5', float('nan')))}%"],
                ["Mean sign agreement — participant 671", f"{f4(part_stab_value(part_stab, 671))}%"],
                ["Mean sign agreement — participant 252", f"{f4(part_stab_value(part_stab, 252))}%"],
            ],
        ),
        "",
        "---",
        "",
        "## 6. Top-link consistency tables",
        "",
        f"`{PREFIX}_top_links.csv` — top 5 pooled links per participant × block × focus mode.",
        "",
    ]

    for fm in FOCUS_ORDER:
        sub = top[top.focus_mode == fm].sort_values(["participant_id", "block_label", "pooled_rank_by_abs"])
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
        f"`{PREFIX}_link_results` — organized by participant, block, comparison variant, focus mode.",
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
                    lines += [f"### Participant {pid} | {bl} | {variant} | {fm}", ""]
                    if sub.empty:
                        lines.append("_No rows._")
                    else:
                        lines.append(df_to_md(sub, LINK_COLS))
                    lines.append("")

    lines += [
        "---",
        "",
        "## 8. Interpretation — all-PC results and review questions",
        "",
        "### 8.1 Is direction preserved across T1_vs_T2 repetition pairings?",
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
        *render_stable_links_section(stable_map, cross_block_stable),
        "### 8.3 Which links flip sign depending on pairing?",
        "",
        "Sign-flipping links (disagree with pooled in at least one pairing; all-PC):",
        "",
        *render_flip_links_section(flip_by_part),
        "",
        f"### 8.4 Does pooled {COMPARISON_LABEL} reflect repetition-specific pairings?",
        "",
        f"Mean all-link sign agreement — same-repetition: **{f4(same_mean)}%**; cross-repetition: **{f4(cross_mean)}%**.",
        (
            f"On average, pooled link signs align more closely with **cross-repetition** pairings "
            f"({f4(cross_mean)}% vs {f4(same_mean)}%)."
            if cross_mean >= same_mean
            else f"On average, pooled link signs align more closely with **same-repetition** pairings "
            f"({f4(same_mean)}% vs {f4(cross_mean)}%)."
        ),
        "This is a descriptive pooled-result consistency statement, not a claim about which pairing is correct.",
        "",
        "### 8.5 Is P3_P4_P5 more stable than all_P1_P2_P3_P4_P5?",
        "",
        f"Mean all-link sign agreement (all-PC): **all_P1_P2_P3_P4_P5** = **{f4(block_stab.get('all_P1_P2_P3_P4_P5', float('nan')))}%**;",
        f"**P3_P4_P5** = **{f4(block_stab.get('P3_P4_P5', float('nan')))}%**.",
        (
            "**P3_P4_P5** has the higher block-level mean sign agreement under all-PC."
            if block_stab.get("P3_P4_P5", 0) >= block_stab.get("all_P1_P2_P3_P4_P5", 0)
            else "**all_P1_P2_P3_P4_P5** has the higher block-level mean sign agreement under all-PC."
        ),
        "",
        "### 8.6 Is participant 252 more stable than 671?",
        "",
        f"Mean all-link sign agreement (all-PC): **671** = **{f4(part_stab_value(part_stab, 671))}%**;",
        f"**252** = **{f4(part_stab_value(part_stab, 252))}%**.",
        (
            "**252** has the higher participant-level mean sign agreement under all-PC."
            if part_stab_value(part_stab, 252) >= part_stab_value(part_stab, 671)
            else "**671** has the higher participant-level mean sign agreement under all-PC."
        ),
        "",
        "---",
        "",
        "## 9. Interpretation — functional_p50",
        "",
        *focus_interpretation_lines(
            "functional_p50",
            m_fp50,
            stable_by_focus["functional_p50"],
            cross_by_focus["functional_p50"],
            flip_by_focus["functional_p50"],
            COMPARISON_LABEL,
        ),
        "---",
        "",
        "## 10. Interpretation — null_space_after_p50",
        "",
        *focus_interpretation_lines(
            "null_space_after_p50",
            m_ns50,
            stable_by_focus["null_space_after_p50"],
            cross_by_focus["null_space_after_p50"],
            flip_by_focus["null_space_after_p50"],
            COMPARISON_LABEL,
        ),
        "---",
        "",
        "## 11. Comparison — all-PC vs null-space robustness",
        "",
        md_table(
            ["Focus mode", "Median sign agreement (%)", "Median Spearman rho — Delta", "Mean same-rep (%)", "Mean cross-rep (%)"],
            [
                [
                    fm,
                    f4(metrics_by_focus[fm]["median_sign"]),
                    f4(metrics_by_focus[fm]["median_rho"]),
                    f4(metrics_by_focus[fm]["same_mean"]),
                    f4(metrics_by_focus[fm]["cross_mean"]),
                ]
                for fm in ["all", "functional_p50", "null_space_after_p50", "null_space_after_p60"]
            ],
        ),
        "",
        "### Is null_space_after_p50 or p60 more directionally robust than all-PC?",
        "",
        f"- Median sign agreement — **all-PC**: **{f4(med_sign)}%**; **null_space_after_p50**: **{f4(m_ns50['median_sign'])}%**;",
        f"**null_space_after_p60**: **{f4(m_ns60['median_sign'])}%**.",
        (
            f"- Under this metric, **null_space_after_p50** ({f4(m_ns50['median_sign'])}%) exceeds all-PC ({f4(med_sign)}%)."
            if m_ns50["median_sign"] >= med_sign
            else f"- Under this metric, **all-PC** ({f4(med_sign)}%) exceeds null_space_after_p50 ({f4(m_ns50['median_sign'])}%)."
        ),
        (
            f"- **null_space_after_p60** median sign agreement is **{f4(m_ns60['median_sign'])}%** "
            f"({'above' if m_ns60['median_sign'] >= med_sign else 'below'} all-PC {f4(med_sign)}%)."
        ),
        f"- **functional_p50** median sign agreement is **{f4(m_fp50['median_sign'])}%** "
        f"({'above' if m_fp50['median_sign'] >= med_sign else 'below'} all-PC {f4(med_sign)}%).",
        "Cell-level patterns differ by participant and block; see Sections 5 and 9–10.",
        "",
        "---",
        "",
        "## 12. Comparison — T1_vs_T2 vs T1_vs_T3 robustness",
        "",
    ]

    t3_metrics_all: dict | None = None
    if t3_summary is not None:
        t3_metrics_all = compute_pairing_metrics(
            t3_summary,
            "all",
            T3_PAIRING_VARIANTS,
            ["T1_R1_vs_T3_R1", "T1_R2_vs_T3_R2"],
            ["T1_R1_vs_T3_R2", "T1_R2_vs_T3_R1"],
        )
        t3_stable = stable_links_by_participant_block(
            read_csv("directional_robustness_t1_t3_link_results"),
            "all",
            T3_POOLED_VARIANT,
            T3_PAIRING_VARIANTS,
        )
        t3_cross = cross_block_stable_links(t3_stable)
        t3_cross_count = sum(len(v) for v in t3_cross.values())
        t2_cross_count = sum(len(v) for v in cross_block_stable.values())
        lines += [
            "T1 vs T3 summary and top-link files are present; metrics below use the same pairing-variant logic.",
            "",
            md_table(
                ["Metric", "T1_vs_T2 (all-PC)", "T1_vs_T3 (all-PC)"],
                [
                    ["Median sign agreement (%)", f4(med_sign), f4(t3_metrics_all["median_sign"])],
                    ["Median Spearman rho — Delta", f4(med_rho), f4(t3_metrics_all["median_rho"])],
                    ["Mean same-repetition sign agreement (%)", f4(same_mean), f4(t3_metrics_all["same_mean"])],
                    ["Mean cross-repetition sign agreement (%)", f4(cross_mean), f4(t3_metrics_all["cross_mean"])],
                    [
                        "Mean sign agreement — block all_P1_P2_P3_P4_P5 (%)",
                        f4(block_stab.get("all_P1_P2_P3_P4_P5", float("nan"))),
                        f4(t3_metrics_all["block_stab"].get("all_P1_P2_P3_P4_P5", float("nan"))),
                    ],
                    [
                        "Mean sign agreement — block P3_P4_P5 (%)",
                        f4(block_stab.get("P3_P4_P5", float("nan"))),
                        f4(t3_metrics_all["block_stab"].get("P3_P4_P5", float("nan"))),
                    ],
                    [
                        "Mean sign agreement — participant 671 (%)",
                        f4(part_stab_value(part_stab, 671)),
                        f4(part_stab_value(t3_metrics_all["part_stab"], 671)),
                    ],
                    [
                        "Mean sign agreement — participant 252 (%)",
                        f4(part_stab_value(part_stab, 252)),
                        f4(part_stab_value(t3_metrics_all["part_stab"], 252)),
                    ],
                    ["Links stable in all four pairings in both blocks (count)", str(t2_cross_count), str(t3_cross_count)],
                ],
            ),
            "",
            "### Is T1_vs_T2 more or less robust than T1_vs_T3?",
            "",
            (
                f"Median all-link sign agreement is **{f4(med_sign)}%** (T1_vs_T2) vs **{f4(t3_metrics_all['median_sign'])}%** (T1_vs_T3). "
                f"T1_vs_T2 has the {'higher' if med_sign >= t3_metrics_all['median_sign'] else 'lower'} median sign agreement."
            ),
            (
                f"Mean same-repetition agreement: T1_vs_T2 **{f4(same_mean)}%** vs T1_vs_T3 **{f4(t3_metrics_all['same_mean'])}%**."
            ),
            (
                f"Mean cross-repetition agreement: T1_vs_T2 **{f4(cross_mean)}%** vs T1_vs_T3 **{f4(t3_metrics_all['cross_mean'])}%**."
            ),
            "",
            "Top-link consistency (all-PC, pooled top-5 same-sign rate across pairings):",
            "",
        ]
        if t3_top is not None:
            t2_top_rate = float(
                top[top.focus_mode == "all"]["all_four_pairings_same_sign"].mean()
                if "all_four_pairings_same_sign" in top.columns
                else float("nan")
            )
            t3_top_rate = float(
                t3_top[t3_top.focus_mode == "all"]["all_four_pairings_same_sign"].mean()
                if "all_four_pairings_same_sign" in t3_top.columns
                else float("nan")
            )
            lines += [
                md_table(
                    ["Comparison", "Mean all_four_pairings_same_sign (all-PC top links)"],
                    [
                        ["T1_vs_T2", f4(t2_top_rate)],
                        ["T1_vs_T3", f4(t3_top_rate)],
                    ],
                ),
                "",
            ]
        lines += [
            "Cross-block stable links (all four pairings, all-PC):",
            "",
            "**T1_vs_T2:**",
            *[
                f"- Participant {pid}: " + (", ".join(f"`{l}`" for l in cross_block_stable.get(pid, [])) or "none")
                for pid in sorted(cross_block_stable.keys())
            ],
            "",
            "**T1_vs_T3:**",
            *[
                f"- Participant {pid}: " + (", ".join(f"`{l}`" for l in t3_cross.get(pid, [])) or "none")
                for pid in sorted(t3_cross.keys())
            ],
            "",
        ]
    else:
        lines += ["T1 vs T3 comparison files not found; this section is omitted.", ""]

    lines += [
        "---",
        "",
        "## 13. Limitations and cautions",
        "",
        "- Descriptive repetition-pairing analysis only; no causal or condition-specific claims.",
        f"- Variant runs use the same JcvPCA workbench as the batch; pooled reference is the existing {COMPARISON_LABEL} output.",
        "- Participants **671** (14 links) and **252** (16 links, includes pelvis-root links) use different link schemas.",
        "- Single-repetition variant runs complete link-level RSS (step 14); NV baseline (step 16A) is skipped when R1 and R2",
        "  cannot both be present in Dataset A.",
        "- PC-focus modes use Dataset A cumulative-variance thresholds computed per variant run.",
        "- Sign agreement counts links equally; it does not weight by abs Delta magnitude.",
        "- Cross-repetition vs same-repetition averages pool across participants and blocks.",
        "- T1_vs_T3 comparison (Section 12) uses separate longitudinal contrast; direct numeric comparison is descriptive only.",
        "",
        "---",
        "",
        "## 14. Machine-readable summary (for future agents)",
        "",
        "```json",
        json.dumps(
            {
                "batch_folder": f"{BATCH_DISPLAY}",
                "analysis": "directional_robustness_t1_vs_t2",
                "reference_variant": POOLED_VARIANT,
                "comparison_label": COMPARISON_LABEL,
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
                    "mean_sign_agreement_participant_671_pct": round(part_stab_value(part_stab, 671), 4),
                    "mean_sign_agreement_participant_252_pct": round(part_stab_value(part_stab, 252), 4),
                },
                "headline_metrics_by_focus": {
                    fm: {
                        "median_sign_agreement_pct": round(metrics_by_focus[fm]["median_sign"], 4),
                        "median_spearman_rho_delta": round(metrics_by_focus[fm]["median_rho"], 4),
                    }
                    for fm in FOCUS_ORDER
                },
                "null_space_vs_all_pc": {
                    "all_pc_median_sign_pct": round(med_sign, 4),
                    "null_space_after_p50_median_sign_pct": round(m_ns50["median_sign"], 4),
                    "null_space_after_p60_median_sign_pct": round(m_ns60["median_sign"], 4),
                    "null_space_p50_exceeds_all_pc": bool(m_ns50["median_sign"] >= med_sign),
                    "null_space_p60_exceeds_all_pc": bool(m_ns60["median_sign"] >= med_sign),
                },
                "stable_links_all_four_pairings_all_pc_by_block": stable_map,
                "stable_links_all_four_pairings_both_blocks_all_pc": cross_block_stable,
                "sign_flip_links_by_participant_all_pc": flip_by_part,
                "direction_preserved_uniformly": False,
                "t1_vs_t3_comparison": (
                    {
                        "t3_median_sign_agreement_pct": round(t3_metrics_all["median_sign"], 4),
                        "t2_exceeds_t3_median_sign": bool(med_sign >= t3_metrics_all["median_sign"]),
                    }
                    if t3_metrics_all is not None
                    else None
                ),
                "input_files": [f"{name}.csv" for name, _ in INPUTS],
                "output_file": OUT.name,
            },
            indent=2,
        ),
        "```",
        "",
    ]

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT} ({len(lines)} lines)")
    print(f"Headline — median sign agreement (all-PC): {f4(med_sign)}%")
    print(f"Headline — same-rep mean: {f4(same_mean)}%; cross-rep mean: {f4(cross_mean)}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
