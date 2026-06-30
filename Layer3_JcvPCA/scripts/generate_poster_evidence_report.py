#!/usr/bin/env python3
"""Generate poster markdown reports from evidence package CSVs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from project_paths import load_project_paths  # noqa: E402

PRIMARY_BLOCK = "P3_P4_P5"

BATCH_DIR = _REPO_ROOT / "Layer3_JcvPCA" / "outputs" / "gaga_batch_jcvpca_20260626_193319"
EVIDENCE_DIR = _REPO_ROOT / "Layer3_JcvPCA" / "outputs" / "poster_ready_evidence_package"
BATCH_ID = "gaga_batch_jcvpca_20260626_193319"
BATCH_DISPLAY = "Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319/"
EVIDENCE_DISPLAY = "Layer3_JcvPCA/outputs/poster_ready_evidence_package/"


def _display_path(path: Path, project_root: Path) -> str:
    try:
        rel = path.resolve().relative_to(project_root.resolve())
        return f"{rel.as_posix()}/"
    except ValueError:
        return f"{path.resolve().as_posix()}/"


def configure_evidence_report_paths(
    *,
    config_path: Path | None = None,
    batch_dir: Path | None = None,
    evidence_dir: Path | None = None,
) -> None:
    """Resolve batch/evidence paths from config/paths.yaml."""
    global BATCH_DIR, EVIDENCE_DIR, BATCH_ID, BATCH_DISPLAY, EVIDENCE_DISPLAY

    paths = load_project_paths(config_path=config_path)
    resolved_batch = (batch_dir or paths.layer3_canonical_batch).resolve()
    resolved_evidence = (evidence_dir or paths.poster_evidence_package).resolve()

    missing: list[str] = []
    if not resolved_batch.is_dir():
        missing.append(f"canonical Layer 3 batch ({resolved_batch})")
    if not resolved_evidence.is_dir():
        missing.append(f"poster evidence package ({resolved_evidence})")
    if missing:
        raise FileNotFoundError(
            "Required evidence-report input path(s) missing:\n  - "
            + "\n  - ".join(missing)
            + f"\nConfig: {paths.config_path}"
        )

    BATCH_DIR = resolved_batch
    EVIDENCE_DIR = resolved_evidence
    BATCH_ID = paths.layer3_canonical_batch_id
    BATCH_DISPLAY = _display_path(resolved_batch, paths.project_root)
    EVIDENCE_DISPLAY = _display_path(resolved_evidence, paths.project_root)


def parse_evidence_report_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate poster markdown reports from evidence package CSVs.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to config/paths.yaml (default: auto-detect project root).",
    )
    parser.add_argument(
        "--batch-dir",
        type=Path,
        default=None,
        help="Override Layer 3 batch directory (default: layer3.canonical_batch).",
    )
    parser.add_argument(
        "--evidence-dir",
        type=Path,
        default=None,
        help="Override poster evidence package (default: layer3.poster_evidence_package).",
    )
    parser.add_argument(
        "--validate-paths",
        action="store_true",
        help="Check required input paths exist and exit (no report regeneration).",
    )
    return parser.parse_args(argv)


configure_evidence_report_paths()


def md_table(df: pd.DataFrame, cols: list[str] | None = None, float_fmt: str = ".4f") -> str:
    if df.empty:
        return "_No data._"
    sub = df if cols is None else df[cols]
    headers = list(sub.columns)
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for _, row in sub.iterrows():
        cells = []
        for c in headers:
            v = row[c]
            if isinstance(v, float):
                cells.append(f"{v:{float_fmt}}" if pd.notna(v) else "NA")
            elif isinstance(v, bool):
                cells.append(str(v))
            else:
                cells.append(str(v))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def top7_long_table(long_df: pd.DataFrame, pid: str, block: str, comp: str) -> str:
    sub = long_df[
        (long_df.participant_id.astype(str) == pid)
        & (long_df.block_label == block)
        & (long_df.comparison_label == comp)
    ].nsmallest(7, "rank_abs_delta")
    cols = [
        "link_id",
        "anatomical_family",
        "JcvPCA_link_delta",
        "abs_delta",
        "relative_abs_delta_share",
        "rank_abs_delta",
    ]
    return md_table(sub, cols)


def generate_master_index(out: Path) -> str:
    files = sorted(out.glob("*.csv"))
    lines = [
        "# Poster Master Figure Data Index",
        "",
        f"Source batch: `{BATCH_DISPLAY}`",
        f"Evidence package: `{EVIDENCE_DISPLAY}`",
        "",
        "## Output file inventory",
        "",
    ]
    for f in files:
        lines.append(f"- `{f.name}`")
    lines.extend(
        [
            "",
            "## Planned figure / table mapping",
            "",
            "### Figure 1 — Timeline / longitudinal design",
            "",
            "- **Poster tier:** main poster",
            "- **Source:** study design metadata (no batch CSV); optional context from `natural_variability_timepoint_pattern_summary.csv`",
            "- **Columns:** participant_id, timepoints T1/T2/T3, repetitions R1/R2",
            "- **Subset:** participants 671 and 252 separately",
            "- **Plot type:** schematic timeline",
            "- **Main message:** Within-participant repeated Gaga assessments at three timepoints",
            "- **Caution:** No treatment labels; descriptive longitudinal framing only",
            "",
            "### Figure 2 — Main longitudinal all-PC link-level Delta",
            "",
            "- **Poster tier:** main poster",
            "- **Source CSV:** `longitudinal_link_delta_allpc_poster_table.csv`",
            "- **Columns:** link_id, JcvPCA_link_delta, abs_delta, anatomical_family, rank_abs_delta",
            "- **Subset:** block P3_P4_P5; comparisons T1_vs_T2, T1_vs_T3; focus_mode all; participants 671, 252 separate panels",
            "- **Plot type:** signed horizontal bar or dot plot per participant/comparison",
            "- **Main message:** Participant-specific link-level kinematic organization changes descriptively from T1 to T2/T3",
            "- **Caution:** Pooled R1+R2 aggregate; direction not uniformly stable across pairings",
            "",
            "### Figure 3 — Longitudinal Delta relative to descriptive NV reference",
            "",
            "- **Poster tier:** main poster (inset or adjacent panel)",
            "- **Source CSV:** `longitudinal_delta_nv_ratio_top7.csv`, `longitudinal_delta_nv_ratio_by_link.csv`",
            "- **Columns:** link_id, delta_to_NV_ratio, outside_NV_reference, ranking_basis",
            "- **Subset:** P3_P4_P5; T1_vs_T2, T1_vs_T3; top 7 by abs_delta and by delta_to_NV_T1_ratio",
            "- **Plot type:** bar plot of Delta/NV ratio with reference line at 1.0",
            "- **Main message:** Many links show longitudinal abs-Delta above T1 descriptive NV reference",
            "- **Caution:** Descriptive NV reference only — not significance or proof",
            "",
            "### Figure 4 — Natural variability structure across T1/T2/T3",
            "",
            "- **Poster tier:** main poster",
            "- **Source CSV:** `natural_variability_scalar_poster_table.csv`, `natural_variability_timepoint_pattern_summary.csv`, `concentration_metrics_all_analyses.csv`",
            "- **Columns (4A):** timepoint, mean_abs_delta; (4B): gini, top3_share",
            "- **Subset:** P3_P4_P5, focus_mode all (+ null_space_after_p50 inset optional)",
            "- **Plot type:** line/point plot (4A) + small Gini/top3 table (4B)",
            "- **Main message:** Repetition variability is not scalar; T2 often largest on P3 all-PC",
            "- **Caution:** Pattern non-monotonic and participant-specific",
            "",
            "### Figure 5 — Null-space repetition variability & threshold stability",
            "",
            "- **Poster tier:** central secondary",
            "- **Source CSV:** `nullspace_top7_links_all_contexts.csv`, `nullspace_threshold_stability_summary.csv`, `nullspace_noise_vs_structure_diagnostic.csv`",
            "- **Columns:** null_p50_to_all_ratio, top7 links, threshold_stability_label",
            "- **Subset:** P3_P4_P5; repetition T1/T2/T3; null_space_after_p50 primary",
            "- **Plot type:** heatmap or faceted top-link bars + stability summary table",
            "- **Main message:** Null-space-like subsets often carry elevated variability; family-level structure more stable than exact links",
            "- **Caution:** Threshold-sensitive link identity; p70 supplementary",
            "",
            "### Figure 6 — Longitudinal PC-focus / null-space decomposition",
            "",
            "- **Poster tier:** optional poster or supplement",
            "- **Source CSV:** `nullspace_top7_links_all_contexts.csv` (longitudinal rows), `concentration_metrics_all_analyses.csv`",
            "- **Columns:** focus_mode, link_id, abs_delta for null_space_after_p50 vs all",
            "- **Subset:** T1_vs_T2, T1_vs_T3, P3_P4_P5",
            "- **Plot type:** paired all-PC vs null-space top-link comparison",
            "- **Main message:** Later-PC structure contributes distinct link-level patterns in longitudinal comparisons",
            "- **Caution:** Compare families not exact links when identity unstable",
            "",
            "### Figure 7 — Directional robustness / repetition-pairing sensitivity",
            "",
            "- **Poster tier:** central secondary (honesty panel)",
            "- **Source CSV:** `direction_vs_magnitude_integrated_report.csv`",
            "- **Columns:** sign_agreement_across_pairings, interpretation_label, link_id",
            "- **Subset:** P3_P4_P5, all-PC, T1_vs_T2 and T1_vs_T3",
            "- **Plot type:** histogram or summary bar of sign agreement; highlight direction-sensitive top links",
            "- **Main message:** Pooled longitudinal summaries aggregate repetition pairings; link direction is pairing-sensitive",
            "- **Caution:** Do not claim uniform directional stability",
            "",
            "### Figure 8 — Body-region / anatomical-family summary",
            "",
            "- **Poster tier:** supplement or compact table inset",
            "- **Source CSV:** `body_region_anatomical_family_summary.csv`",
            "- **Columns:** anatomical_family, relative_family_share, top_link_in_family",
            "- **Subset:** per participant separately; P3_P4_P5 longitudinal all-PC",
            "- **Plot type:** stacked family share bar or table",
            "- **Main message:** Arm/hand and leg families recur; pelvis_root only for participant 252",
            "- **Caution:** Different link schemas — never average participants",
            "",
            "### Table 9 — Take-home evidence table",
            "",
            "- **Poster tier:** main poster (bottom row)",
            "- **Source CSV:** `poster_takehome_numeric_summary.csv`",
            "- **Columns:** evidence_question, primary_result, poster_interpretation, caution",
            "- **Plot type:** compact text table",
            "- **Main message:** One-page descriptive evidence summary",
            "- **Caution:** Neutral language only",
            "",
            "## Supplementary-only outputs",
            "",
            "| File | Use |",
            "| --- | --- |",
            "| `longitudinal_link_delta_allpc_poster_table.csv` (all_P1_P2 rows) | Secondary block completeness |",
            "| `nullspace_explained_variance_weighting_check.csv` | Supplement — variance weighting robustness |",
            "| `nullspace_weighting_summary.csv` | Supplement |",
            "| T2_vs_T3 rows in multiple CSVs | Exploratory completeness only |",
            "| p70 columns | Supplementary diagnostic |",
        ]
    )
    return "\n".join(lines)


def generate_evidence_report(
    out: Path,
    long_df: pd.DataFrame,
    nv_ratio: pd.DataFrame,
    nv_top7: pd.DataFrame,
    nv_pattern: pd.DataFrame,
    conc: pd.DataFrame,
    null_top7: pd.DataFrame,
    thresh: pd.DataFrame,
    noise: pd.DataFrame,
    direction: pd.DataFrame,
    body: pd.DataFrame,
    takehome: pd.DataFrame,
) -> str:
    p3_nv = nv_pattern[(nv_pattern.block_label == PRIMARY_BLOCK) & (nv_pattern.focus_mode == "all")]
    p3_conc = conc[
        (conc.block_label == PRIMARY_BLOCK)
        & (conc.analysis_type == "longitudinal")
        & (conc.focus_mode == "all")
    ]
    p3_noise = noise[noise.block_label == PRIMARY_BLOCK]
    dr_p3 = direction[(direction.block_label == PRIMARY_BLOCK) & (direction.focus_mode == "all")]

    lines = [
        "# Poster-Ready Evidence Report",
        "",
        f"Batch: `{BATCH_ID}` | Package: `{EVIDENCE_DIR.name}`",
        "",
        "## 1. Executive summary",
        "",
        "**Strongest longitudinal finding:** On P3_P4_P5 all-PC, both participants show broadly distributed link-level Delta across arm/hand and leg links for T1_vs_T2 and T1_vs_T3, with participant-specific top-link profiles (671: thigh/arm emphasis; 252: shoulder–arm chain and pelvis-root links).",
        "",
        "**Strongest NV finding:** Repetition-to-repetition variability is link-structured; T2 is largest for 671 on P3 all-PC but T1 for 252 — participant-specific, not a uniform scalar peak.",
        "",
        "**Strongest null-space finding:** Null-space mean abs-Delta frequently exceeds all-PC (null/all ratio >1), with anatomical-family recurrence more stable than exact link identity across p50/p60.",
        "",
        "**Strongest body-region finding:** Upper-limb (shoulder_chain, distal_upper_limb) and lower_limb families carry the largest relative shares, participant-specific; pelvis_root appears for 252 only.",
        "",
        "**Main caution:** Link direction is repetition-pairing sensitive (~53–71% sign agreement on P3 all-PC); pooled comparisons are aggregate descriptive summaries only.",
        "",
        "**Build figures first:** Figure 1 (timeline) → Figure 2 (main longitudinal all-PC) → Figure 4 (NV + Gini) → Figure 3 (Delta/NV) → Figure 7 (directional robustness) → Figure 5 (null-space secondary).",
        "",
        "## 2. Main longitudinal story",
        "",
        "Primary block **P3_P4_P5**, focus **all**, comparisons **T1_vs_T2** and **T1_vs_T3**, shown separately per participant.",
        "",
        "### 671 — P3_P4_P5 — T1_vs_T2 (top 7 all-PC)",
        "",
        top7_long_table(long_df, "671", PRIMARY_BLOCK, "T1_vs_T2"),
        "",
        "### 671 — P3_P4_P5 — T1_vs_T3 (top 7 all-PC)",
        "",
        top7_long_table(long_df, "671", PRIMARY_BLOCK, "T1_vs_T3"),
        "",
        "### 252 — P3_P4_P5 — T1_vs_T2 (top 7 all-PC)",
        "",
        top7_long_table(long_df, "252", PRIMARY_BLOCK, "T1_vs_T2"),
        "",
        "### 252 — P3_P4_P5 — T1_vs_T3 (top 7 all-PC)",
        "",
        top7_long_table(long_df, "252", PRIMARY_BLOCK, "T1_vs_T3"),
        "",
        "Arm/hand and leg link families recur among largest contributors; chest/neck links typically lower relative share.",
        "",
        "## 3. Longitudinal Delta relative to NV",
        "",
        "Descriptive NV reference from within-timepoint repetition comparisons (T1_R1_vs_T1_R2, etc.).",
        "",
        "### Top links by Delta/NV T1 ratio — P3_P4_P5",
        "",
        md_table(
            nv_ratio[nv_ratio.block_label == PRIMARY_BLOCK]
            .nsmallest(14, "rank_by_delta_to_NV_T1_ratio")
            .head(14),
            [
                "participant_id",
                "comparison_label",
                "link_id",
                "abs_longitudinal_delta",
                "NV_T1_abs_delta",
                "delta_to_NV_T1_ratio",
                "outside_T1_NV_reference",
            ],
        ),
        "",
        f"- Links exceeding T1 descriptive NV reference (P3): {nv_ratio[(nv_ratio.block_label == PRIMARY_BLOCK) & nv_ratio.outside_T1_NV_reference].shape[0]} link-comparison rows",
        "- T1_vs_T3 often shows similar or higher ratios than T1_vs_T2 depending on link/participant",
        "- Findings are **participant-specific** — do not pool",
        "",
        "## 4. Natural variability is not scalar",
        "",
        "### P3_P4_P5 — all-PC timepoint pattern",
        "",
        md_table(
            p3_nv,
            [
                "participant_id",
                "T1_mean_abs_delta",
                "T2_mean_abs_delta",
                "T3_mean_abs_delta",
                "largest_timepoint",
                "T2_is_largest",
                "monotonic_pattern",
            ],
        ),
        "",
        "### Concentration metrics — P3 repetition all-PC",
        "",
        md_table(
            conc[
                (conc.block_label == PRIMARY_BLOCK)
                & (conc.analysis_type == "repetition_variability")
                & (conc.focus_mode == "all")
            ][
                [
                    "participant_id",
                    "timepoint_if_repetition",
                    "gini",
                    "top3_share",
                    "links_needed_for_80_percent",
                    "concentration_label",
                ]
            ],
        ),
        "",
        "Natural variability is better represented by **link-level profiles plus Gini/top3-share** than a single scalar mean.",
        "",
        "## 5. Null-space repetition variability",
        "",
        md_table(
            p3_noise[p3_noise.analysis_type == "repetition_variability"][
                [
                    "participant_id",
                    "timepoint_if_repetition",
                    "null_p50_to_all_ratio",
                    "null_p60_to_all_ratio",
                    "top7_overlap_p50_p60",
                    "final_diagnostic_label",
                ]
            ],
        ),
        "",
        "- Null-space variability is often **elevated** relative to all-PC (ratio >1)",
        "- **p50/p60** show moderate top7 overlap with stable anatomical families in many contexts",
        "- Exact links vary; structured_but_threshold_sensitive or likely_structured labels common",
        "",
        "## 6. Longitudinal null-space",
        "",
        "Top null-space links for longitudinal comparisons differ from all-PC top links in several panels — same **families** (upper limb, lower limb) more often than same exact links.",
        "",
        md_table(
            null_top7[
                (null_top7.block_label == PRIMARY_BLOCK)
                & (null_top7.analysis_type == "longitudinal")
                & (null_top7.focus_mode == "null_space_after_p50")
                & (null_top7.rank_abs_delta <= 3)
            ].head(12),
            ["participant_id", "comparison_label", "link_id", "anatomical_family", "abs_delta", "rank_abs_delta"],
        ),
        "",
        "## 7. Body-region / anatomical-family summary",
        "",
        "**671:** 14 links, no pelvis_root. **252:** 16 links including `252_to_LThigh`, `252_to_RThigh`.",
        "",
        md_table(
            body[
                (body.block_label == PRIMARY_BLOCK)
                & (body.analysis_type == "longitudinal")
                & (body.focus_mode == "all")
                & (body.family_rank <= 3)
            ].head(12),
            [
                "participant_id",
                "comparison_label",
                "anatomical_family",
                "relative_family_share",
                "top_link_in_family",
            ],
        ),
        "",
        "## 8. Direction vs magnitude",
        "",
        md_table(
            dr_p3.groupby(["comparison_label", "interpretation_label"]).size().reset_index(name="n_links"),
            ["comparison_label", "interpretation_label", "n_links"],
        ),
        "",
        "Median sign agreement across pairings (P3 all-PC): T1_vs_T2 ~59–71%; T1_vs_T3 ~60% (671) / lower for full block.",
        "Supports framing pooled R1+R2 as **aggregate longitudinal summary** with direction sensitivity noted.",
        "",
        "## 9. Noise vs structure diagnostic",
        "",
        md_table(
            p3_noise[
                ["analysis_type", "comparison_label", "timepoint_if_repetition", "final_diagnostic_label", "structure_score", "noise_risk_score"]
            ],
        ),
        "",
        "## 10. Recommended poster figures",
        "",
        "| Figure | Source | Panels | Variables | Caption draft |",
        "| --- | --- | --- | --- | --- |",
        "| 1 Timeline | design schematic | 2 (671, 252) | timepoint × repetition | Three within-participant assessment timepoints with two repetitions each |",
        "| 2 Longitudinal all-PC | longitudinal_link_delta_allpc_poster_table.csv | 4 (671/252 × T1_vs_T2/T1_vs_T3) | link_id vs JcvPCA_link_delta | Link-level Delta on P3–P5, all PCs, separate participants |",
        "| 3 Delta/NV | longitudinal_delta_nv_ratio_top7.csv | 4–8 top-link panels | delta_to_NV_ratio | Longitudinal abs-Delta relative to T1 descriptive NV reference |",
        "| 4 NV + Gini | natural_variability_timepoint_pattern_summary.csv + concentration_metrics | 2×2 | mean_abs_delta; gini/top3 | Repetition variability across T1/T2/T3 is link-structured |",
        "| 5 Null-space | nullspace_top7_links_all_contexts.csv | T2 repetition primary | abs_delta null vs all | Later-PC subsets show elevated descriptive variability |",
        "| 6 Direction | direction_vs_magnitude_integrated_report.csv | summary + examples | sign_agreement | Pooled direction is pairing-sensitive |",
        "",
        "## 11. What not to show",
        "",
        "- p-values or inferential significance language",
        "- Cross-participant averages or pooled 671+252 matrices",
        "- Psilocybin, treatment-effect, improvement, or creativity claims",
        "- archived p2 as main tier",
        "- P6/P7 exercises",
        "- More than two PC thresholds on main poster (use p50 primary; p60 optional; p70 supplement)",
        "",
        "## 12. Safe poster wording",
        "",
        "**A. Strong but safe:** Within each participant, JcvPCA describes link-level kinematic organization during Gaga movement across repeated assessments; on P3–P5, longitudinal link-level Delta shows participant-specific patterns with arm/hand and leg links among the largest contributors.",
        "",
        "**B. Conservative:** We report descriptive, within-participant link-level kinematic organization patterns; findings are exploratory and require cautious repetition-pairing framing.",
        "",
        "**C. If null-space link identity unstable:** Later-PC subsets show elevated mean variability with recurring anatomical-family structure; exact link ranks are threshold-sensitive.",
        "",
        "**D. If p70 confirms p50/p60:** Null-space elevation persists at stricter p70 diagnostic, supporting supplementary later-PC sensitivity.",
        "",
        "**E. If p70 weakens p50/p60:** Main poster should emphasize p50/p60 only; p70 noted as supplementary threshold sensitivity.",
        "",
        "## 13. Final recommendation",
        "",
        "- **Build first:** Figures 1, 2, 4, 3, 7",
        "- **Main finding:** Longitudinal all-PC link-level Delta on P3_P4_P5 (Figure 2)",
        "- **Central secondary:** NV structure (Figure 4) + directional robustness (Figure 7)",
        "- **Supplementary:** null-space detail (Figure 5/6), all-block inset, p70, T2_vs_T3",
        "- **Null-space on main poster:** Yes, as one compact panel (T2 repetition null/all ratio + top families)",
        "- **Gini vs entropy:** Use **Gini + top3_share** on poster; entropy supplementary",
        "- **p70:** Supplementary mention only",
        "",
        "---",
        "",
        "## Final direct questions",
        "",
    ]

    # Answer the 15 questions
    q = []
    q.append(
        "1. **Is the longitudinal all-PC result strong enough as the main poster result?** "
        "Yes — broadly distributed, participant-specific, anatomically interpretable on P3_P4_P5; suitable as main descriptive result with directional caveat."
    )
    q.append(
        "2. **Which exact panels?** "
        "671 P3 T1_vs_T2, 671 P3 T1_vs_T3, 252 P3 T1_vs_T2, 252 P3 T1_vs_T3 (four main bar panels)."
    )
    q.append(
        "3. **Are longitudinal deltas large relative to NV?** "
        f"Yes descriptively — many links exceed T1 NV reference ({nv_ratio[(nv_ratio.block_label == PRIMARY_BLOCK) & nv_ratio.outside_T1_NV_reference].shape[0]} P3 rows)."
    )
    q.append(
        "4. **Is T2 repetition variability elevated?** "
        f"Often participant-specific — T2 largest for 671 on P3 all-PC; 252 shows T1_peak on P3 all-PC ({p3_nv['T2_is_largest'].sum()}/{len(p3_nv)} with T2 largest)."
    )
    q.append(
        "5. **Monotonic or non-monotonic?** "
        f"Mostly non-monotonic or T2_peak ({', '.join(p3_nv['monotonic_pattern'].unique())})."
    )
    q.append(
        "6. **Scalar, link profile, or distribution metrics?** "
        "Link-level profile + Gini/top3-share; scalar mean abs-Delta useful only as timeline context."
    )
    q.append("7. **Gini or entropy?** Use **Gini + top3_share**; entropy supplementary.")
    q.append(
        "8. **Is null-space variability elevated?** "
        "Yes descriptively — null/all ratio >1 in most P3 contexts."
    )
    q.append(
        "9. **Stable across p50/p60/p70?** "
        "p50/p60 generally stable at family level; p70 can shift exact links — treat as supplementary."
    )
    q.append(
        "10. **Exact links or families?** "
        "Families more stable than exact links across thresholds and pairings."
    )
    q.append(
        "11. **Structured or noise?** "
        "Mixed — many contexts labeled structured_but_threshold_sensitive or likely_structured_nullspace_pattern; few pure noise."
    )
    q.append(
        "12. **Best null-space panel?** "
        "P3_P4_P5 T2 repetition null_space_after_p50 top links + null/all ratio."
    )
    q.append("13. **p70?** Supplementary text or supplement figure only.")
    q.append(
        "14. **Best body-region summary?** "
        "Per-participant anatomical_family relative share bars; note 252 pelvis_root only."
    )
    q.append(
        "15. **Safest one-sentence claim?** "
        "Within each participant, link-level JcvPCA Delta on P3–P5 describes how aggregate kinematic organization across Gaga movement links differs descriptively between baseline and later assessment timepoints, with participant-specific arm/hand and leg link contributions."
    )
    lines.extend(q)
    return "\n".join(lines)


def generate_reports(
    out: Path,
    batch: Path,
    long_df: pd.DataFrame,
    nv_ratio: pd.DataFrame,
    nv_top7: pd.DataFrame,
    nv_pattern: pd.DataFrame,
    conc: pd.DataFrame,
    null_top7: pd.DataFrame,
    thresh: pd.DataFrame,
    noise: pd.DataFrame,
    direction: pd.DataFrame,
    body: pd.DataFrame,
    takehome: pd.DataFrame,
) -> None:
    configure_evidence_report_paths(batch_dir=batch, evidence_dir=out)
    index_md = generate_master_index(out)
    (out / "poster_master_figure_data_index.md").write_text(index_md, encoding="utf-8")
    report_md = generate_evidence_report(
        out, long_df, nv_ratio, nv_top7, nv_pattern, conc, null_top7, thresh, noise, direction, body, takehome
    )
    (out / "poster_ready_evidence_report.md").write_text(report_md, encoding="utf-8")


def _load_csv(out: Path, name: str) -> pd.DataFrame:
    path = out / name
    if not path.is_file():
        raise FileNotFoundError(f"Required evidence CSV missing: {path}")
    return pd.read_csv(path)


def main(argv: list[str] | None = None) -> int:
    args = parse_evidence_report_args(argv)
    try:
        configure_evidence_report_paths(
            config_path=args.config,
            batch_dir=args.batch_dir,
            evidence_dir=args.evidence_dir,
        )
    except FileNotFoundError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1

    if args.validate_paths:
        print(f"Batch:    {BATCH_DIR}")
        print(f"Evidence: {EVIDENCE_DIR}")
        print(f"Batch ID: {BATCH_ID}")
        print("Path check passed.")
        return 0

    out = EVIDENCE_DIR
    try:
        long_df = _load_csv(out, "longitudinal_link_delta_allpc_poster_table.csv")
        nv_ratio = _load_csv(out, "longitudinal_delta_nv_ratio_by_link.csv")
        nv_top7 = _load_csv(out, "longitudinal_delta_nv_ratio_top7.csv")
        nv_pattern = _load_csv(out, "natural_variability_timepoint_pattern_summary.csv")
        conc = _load_csv(out, "concentration_metrics_all_analyses.csv")
        null_top7 = _load_csv(out, "nullspace_top7_links_all_contexts.csv")
        thresh = _load_csv(out, "nullspace_threshold_stability_summary.csv")
        noise = _load_csv(out, "nullspace_noise_vs_structure_diagnostic.csv")
        direction = _load_csv(out, "direction_vs_magnitude_integrated_report.csv")
        body = _load_csv(out, "body_region_anatomical_family_summary.csv")
        takehome = _load_csv(out, "poster_takehome_numeric_summary.csv")
    except FileNotFoundError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1

    generate_reports(
        out,
        BATCH_DIR,
        long_df,
        nv_ratio,
        nv_top7,
        nv_pattern,
        conc,
        null_top7,
        thresh,
        noise,
        direction,
        body,
        takehome,
    )
    print(f"Wrote markdown reports under {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
