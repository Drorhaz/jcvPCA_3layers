#!/usr/bin/env python3
"""Participant-671-only poster figure set (3 large, poster-ready figures).

Primary poster figures (written into outputs/poster_final_figures/):
  Fig 1  Longitudinal link shift vs T1 NV (Figure-A lollipop style; 671 only)
  Fig 2  Natural repetition variability: magnitude (mean abs Delta) + concentration (Gini)
  Fig 3  Functional vs null-space family shares + null/all ratio (671; Figure-B style)

Participant-level descriptive example; blinded timepoint-related kinematic
variation; methodological validation / exploratory longitudinal signal.
NOT a treatment-specific effect. Values are read/derived from validated CSVs.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

# Shared infrastructure from the A-D poster script (same project conventions).
from make_poster_final_figures import (
    PROJECT_ROOT, OUT_DIR, FAMILY_COLORS, FAMILY_LABEL, PARTICIPANT_COLORS,
    set_style, wrap_link, load_csv, find_csv, Validator, DataError,
)

# --------------------------------------------------------------------------- #
# Constants (participant 671 only)
# --------------------------------------------------------------------------- #
PID = "671"
PID_COLOR = PARTICIPANT_COLORS[PID]
BLOCK = "P3_P4_P5"
FOCUS = "all"
COMPARISONS = ["T1_vs_T2", "T1_vs_T3"]
TIMEPOINTS = ["T1", "T2", "T3"]
FIG1_TOP_N = 7
FIG1_NV_ABS_COL = "NV_T1_abs_delta"
FIG1_RATIO_COL = "delta_to_NV_T1_ratio"
FIG1_X_AXIS = "Absolute longitudinal JcvPCA link Delta"
FIG3_COMP = "T1_vs_T2"
FUNC_COLOR = "#3B6FB6"       # functional subspace (first ~50% variance)
NULL_COLOR = "#D98C2B"       # null-space after p50
FUNC_P50_COLOR = "#3B6FB6"   # functional through p50 split
FUNC_P60_COLOR = "#2A5088"   # functional through p60 split (darker = stricter cut)
NULL_P50_COLOR = "#D98C2B"   # null-space after p50
NULL_P60_COLOR = "#A65E12"   # null-space after p60 (darker = stricter split)

# Figure 1 typography (compact layout, larger readable elements).
FB1 = {
    "fig_title": 24,
    "subtitle": 16,
    "panel_title": 21,
    "axis": 18,
    "tick": 16,
    "annot": 15,
    "note": 13,
    "legend": 14,
}
FIG1_STEM_LW = 3.2
FIG1_DOT_S = 320
FIG1_DOT_EDGE_OUT = 2.6
FIG1_DOT_EDGE_IN = 1.4
NV_CMAP = plt.cm.YlOrRd
NV_VMIN, NV_VMAX = 0.0, 4.0
NV_NORM = matplotlib.colors.Normalize(vmin=NV_VMIN, vmax=NV_VMAX)

# Larger, bolder poster typography (90 x 180 cm).
FB = {
    "fig_title": 19,
    "subtitle": 13,
    "panel_title": 17,
    "axis": 15,
    "tick": 13,
    "annot": 12,
    "count": 15,
    "note": 11,
    "legend": 12.5,
}

# (unused legacy alias)
NV_STYLE = {}

CAUTION = ("Participant-level descriptive example; blinded timepoint-related "
           "kinematic variation. Not a treatment-specific effect.")


def _poster_style() -> None:
    set_style()
    plt.rcParams.update({
        "font.size": FB["tick"],
        "axes.titlesize": FB["panel_title"],
        "axes.labelsize": FB["axis"],
        "xtick.labelsize": FB["tick"],
        "ytick.labelsize": FB["tick"],
        "axes.linewidth": 1.2,
    })


def _title(fig, text: str, y: float = 0.985) -> None:
    fig.suptitle(text, fontsize=FB["fig_title"], fontweight="bold",
                 x=0.012, ha="left", y=y)


def _save(fig, stem: str) -> list[str]:
    paths = []
    for ext in ("png", "pdf", "svg"):
        p = OUT_DIR / f"{stem}.{ext}"
        fig.savefig(p, dpi=600 if ext == "png" else None)
        paths.append(str(p.relative_to(PROJECT_ROOT)))
    plt.close(fig)
    return paths


# --------------------------------------------------------------------------- #
# Data preparation
# --------------------------------------------------------------------------- #
def _assess_pp_conversion(v: Validator) -> dict:
    """Check whether link JRW contributions sum to 1 within each condition."""
    batch = (PROJECT_ROOT / "Layer3_JcvPCA" / "outputs"
             / "gaga_batch_jcvpca_20260626_193319")
    jrw_path = batch / "comparisons" / "671_B_L1_T1_vs_T2" / "run" / "link_level_jrw_rss.csv"
    rel = jrw_path.relative_to(PROJECT_ROOT)
    v.register_file(str(rel))
    if not jrw_path.is_file():
        v.note("Fig1: JRW audit file missing; percentage-point conversion not assessed.")
        return {"pp_possible": False, "reason": "JRW audit file unavailable"}

    jrw = pd.read_csv(jrw_path)
    v.check_columns("Fig1 JRW audit", jrw, ["pc", "JRW_A_link", "JRW_B_link"])
    pc1 = jrw[jrw.pc == 1]
    sums = {c: float(pc1[c].sum()) for c in ("JRW_A_link", "JRW_B_link")}
    pp_possible = all(abs(s - 1.0) <= 0.02 for s in sums.values())
    reason = (
        "Per-condition link JRW (RSS of PCA loadings) sums to "
        f"~{sums['JRW_A_link']:.2f} per PC, not 1.0; JcvPCA link \u0394 is a raw "
        "B\u2212A JRW difference, not a change in normalized link share. "
        "Multiplying by 100 would not yield valid percentage points of contribution."
    )
    v.note(f"Fig1 percentage-point conversion: {'possible' if pp_possible else 'NOT possible'}. "
           f"{reason}")
    return {"pp_possible": pp_possible, "reason": reason, "jrw_pc1_sums": sums}


def _gini_coefficient(values: np.ndarray) -> float:
    """Gini on non-negative values (same formula as Layer3 poster package)."""
    x = np.sort(np.asarray(values, dtype=float))
    x = x[x >= 0]
    if x.size == 0:
        return float("nan")
    if np.allclose(x, 0):
        return 0.0
    n = x.size
    idx = np.arange(1, n + 1)
    return float((2 * np.sum(idx * x) / (n * np.sum(x))) - (n + 1) / n)


def _compute_fig1_distribution(sub: pd.DataFrame, v: Validator) -> pd.DataFrame:
    """Within-contrast distribution summary for T1-referenced contrasts only."""
    rows: list[dict] = []
    for comp in COMPARISONS:
        g = sub[sub.comparison_label == comp].copy()
        abs_d = g["abs_longitudinal_delta"].to_numpy(dtype=float)
        total = float(abs_d.sum())
        v.check_sanity("Fig1 dist", f"{comp} sum |delta| > 0", total > 0,
                       f"sum = {total:.5f}", fatal=True)
        share = abs_d / total
        top3 = float(np.sort(share)[::-1][: min(3, share.size)].sum())
        gi = _gini_coefficient(share)
        rows.append({
            "table_type": "distribution_summary",
            "comparison_label": comp,
            "n_links": int(len(g)),
            "sum_abs_longitudinal_delta": total,
            "gini_link_change_share": gi,
            "top3_share": top3,
            "top3_share_pct": top3 * 100.0,
        })
        v.note(f"Fig1 distribution {comp}: Gini={gi:.3f}, Top-3 share={top3*100:.1f}% "
               f"(n={len(g)} links; T1-referenced contrast only).")
    v.note("Fig1 distribution inset uses T1_vs_T2 and T1_vs_T3 only; T2_vs_T3 is "
           "excluded because it uses a different JcvPCA reference space.")
    out = pd.DataFrame(rows)
    for comp in COMPARISONS:
        v.check_sanity("Fig1 dist", f"{comp} only in summary",
                       comp in set(out.comparison_label),
                       f"comparisons={list(out.comparison_label)}")
    return out


def prepare_fig1(v: Validator) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    pp_info = _assess_pp_conversion(v)

    name = "longitudinal_delta_nv_ratio_by_link.csv"
    v.register_file(name)
    df = load_csv(name)
    req = ["participant_id", "block_label", "comparison_label", "link_id",
           "anatomical_family", "longitudinal_delta", "abs_longitudinal_delta",
           FIG1_NV_ABS_COL, FIG1_RATIO_COL, "outside_T1_NV_reference",
           "rank_by_abs_longitudinal_delta"]
    v.check_columns("Fig1", df, req)

    sub = df[(df.participant_id.astype(str) == PID) & (df.block_label == BLOCK)
             & (df.comparison_label.isin(COMPARISONS))].copy()
    for c in ["longitudinal_delta", "abs_longitudinal_delta", FIG1_NV_ABS_COL,
              FIG1_RATIO_COL, "rank_by_abs_longitudinal_delta"]:
        sub[c] = pd.to_numeric(sub[c], errors="coerce")
    sub["outside_T1_NV_reference"] = (
        sub["outside_T1_NV_reference"].astype(str).str.strip().str.lower()
        .isin(["true", "1", "yes"]))
    sub["sign_glyph"] = np.where(sub["longitudinal_delta"] >= 0, "+", "\u2212")
    sub["tip_label"] = sub.apply(
        lambda r: f"{r[FIG1_RATIO_COL]:.1f}\u00d7  (NV {r[FIG1_NV_ABS_COL]:.3f})",
        axis=1,
    )

    top_n = FIG1_TOP_N
    top = (sub.sort_values("rank_by_abs_longitudinal_delta")
           .groupby("comparison_label", group_keys=False).head(top_n))

    keep = ["comparison_label", "link_id", "anatomical_family",
            "longitudinal_delta", "abs_longitudinal_delta", "sign_glyph",
            FIG1_NV_ABS_COL, FIG1_RATIO_COL, "outside_T1_NV_reference",
            "tip_label", "rank_by_abs_longitudinal_delta"]
    out = (top[keep].sort_values(["comparison_label", "rank_by_abs_longitudinal_delta"])
           .reset_index(drop=True))

    links_by_panel = {
        comp: out.loc[out.comparison_label == comp, "link_id"].tolist()
        for comp in COMPARISONS
    }
    for comp in COMPARISONS:
        v.record_rows(f"Fig1 {comp} top links", len(out[out.comparison_label == comp]))
        v.note(f"Fig1 {comp} links shown: {', '.join(links_by_panel[comp])}")

    v.check_sanity("Fig1", "NV_T1 denominator > 0",
                   float(out[FIG1_NV_ABS_COL].min()) > 0,
                   f"min NV_T1 = {float(out[FIG1_NV_ABS_COL].min()):.5f}", fatal=True)

    ok = sub[sub[FIG1_NV_ABS_COL] > 0]
    recomputed = ok["abs_longitudinal_delta"] / ok[FIG1_NV_ABS_COL]
    max_dev = float((recomputed - ok[FIG1_RATIO_COL]).abs().max())
    v.check_sanity("Fig1", "delta_to_NV_T1_ratio = |delta| / NV_T1",
                   max_dev <= 1e-2,
                   f"max |recomputed - stored| = {max_dev:.4f}")
    mismatch = int((sub["outside_T1_NV_reference"]
                    != (sub[FIG1_RATIO_COL] > 1.0)).sum())
    v.check_sanity("Fig1", "outside-NV flag agrees with ratio>1", mismatch == 0,
                   f"{mismatch} rows disagree")

    def g(comp, link, col):
        r = out[(out.comparison_label == comp) & (out.link_id == link)]
        return None if r.empty else float(r.iloc[0][col])

    v.check_value("Fig1", "T1_vs_T2 RFArm_to_RHand signed", 0.0390,
                  g("T1_vs_T2", "RFArm_to_RHand", "longitudinal_delta"), 1e-3)
    v.check_value("Fig1", "T1_vs_T2 RFArm_to_RHand xNV", 3.619,
                  g("T1_vs_T2", "RFArm_to_RHand", FIG1_RATIO_COL), 1e-2)
    v.check_value("Fig1", "T1_vs_T3 RFArm_to_RHand signed", 0.0417,
                  g("T1_vs_T3", "RFArm_to_RHand", "longitudinal_delta"), 1e-3)
    v.check_value("Fig1", "T1_vs_T2 RUArm_to_RFArm xNV", 8.717,
                  g("T1_vs_T2", "RUArm_to_RFArm", FIG1_RATIO_COL), 1e-2)

    dist = _compute_fig1_distribution(sub, v)

    def gd(comp, col):
        r = dist[dist.comparison_label == comp]
        return None if r.empty else float(r.iloc[0][col])

    v.check_value("Fig1 dist", "T1_vs_T2 Gini", 0.4755,
                  gd("T1_vs_T2", "gini_link_change_share"), 1e-3)
    v.check_value("Fig1 dist", "T1_vs_T3 Gini", 0.4740,
                  gd("T1_vs_T3", "gini_link_change_share"), 1e-3)
    v.check_value("Fig1 dist", "T1_vs_T2 Top-3 share", 0.5425,
                  gd("T1_vs_T2", "top3_share"), 1e-3)
    v.check_value("Fig1 dist", "T1_vs_T3 Top-3 share", 0.5448,
                  gd("T1_vs_T3", "top3_share"), 1e-3)

    meta = {
        "style": "figure_A_lollipop",
        "pp_conversion_possible": pp_info["pp_possible"],
        "pp_conversion_reason": pp_info.get("reason", ""),
        "xnv_denominator": "NV_T1_abs_delta (T1_R1 vs T1_R2 repetition contrast, all-PC mean |JcvPCA_link| per link)",
        "xnv_formula": "|longitudinal_delta| / NV_T1_abs_delta",
        "top_n_shown": top_n,
        "links_by_panel": links_by_panel,
        "x_axis_label": FIG1_X_AXIS,
        "distribution_comparisons": list(COMPARISONS),
        "distribution_formula": (
            "Per T1-referenced contrast: abs_delta=|longitudinal_delta|; "
            "link_change_share=abs_delta/sum(abs_delta); "
            "Gini(link_change_share); Top-3 share=sum of 3 largest link_change_share"
        ),
    }
    v.note(f"Fig1 xNV denominator: {meta['xnv_denominator']}")
    v.note(f"Fig1 top-N per panel: {top_n}")
    v.note(f"Fig1 distribution computation: {meta['distribution_formula']}")
    return out, dist, meta


def prepare_fig2(v: Validator) -> pd.DataFrame:
    name = "natural_variability_scalar_poster_table.csv"
    v.register_file(name)
    df = load_csv(name)
    req = ["participant_id", "block_label", "timepoint", "focus_mode",
           "mean_abs_delta", "gini"]
    v.check_columns("Fig2", df, req)
    sub = df[(df.participant_id == PID) & (df.block_label == BLOCK)
             & (df.focus_mode == FOCUS) & (df.timepoint.isin(TIMEPOINTS))].copy()
    for c in ["mean_abs_delta", "gini"]:
        sub[c] = pd.to_numeric(sub[c], errors="coerce")
    out = (sub[["timepoint", "mean_abs_delta", "gini"]]
           .sort_values("timepoint").reset_index(drop=True))
    v.record_rows("Fig2 timepoints", len(out))

    def g(tp, col):
        r = out[out.timepoint == tp]
        return None if r.empty else float(r.iloc[0][col])

    expect = [("T1", 0.012492, 0.536613), ("T2", 0.015620, 0.563372),
              ("T3", 0.010970, 0.459186)]
    for tp, m, gi in expect:
        v.check_value("Fig2", f"{tp} mean_abs_delta", m, g(tp, "mean_abs_delta"), 1e-4)
        v.check_value("Fig2", f"{tp} gini", gi, g(tp, "gini"), 1e-4)
    return out


def prepare_fig3(v: Validator) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Figure 3: functional vs null-space family shares (Figure B style) + null/all ratio."""
    # --- Family shares (Model 3) ------------------------------------------- #
    fname = "body_region_anatomical_family_summary.csv"
    v.register_file(fname)
    fdf = load_csv(fname)
    req_f = ["participant_id", "block_label", "comparison_label", "focus_mode",
             "anatomical_family", "relative_family_share", "n_links_in_family",
             "family_rank", "top_link_in_family"]
    v.check_columns("Fig3 family", fdf, req_f)
    focuses = ["functional_p50", "null_space_after_p50"]
    fam = fdf[(fdf.participant_id.astype(str) == PID) & (fdf.block_label == BLOCK)
              & (fdf.comparison_label == FIG3_COMP)
              & (fdf.focus_mode.isin(focuses))].copy()
    fam["relative_family_share"] = pd.to_numeric(fam["relative_family_share"],
                                                 errors="coerce")
    family_out = (fam[["comparison_label", "focus_mode", "anatomical_family",
                       "relative_family_share", "n_links_in_family", "family_rank",
                       "top_link_in_family"]]
                  .sort_values(["focus_mode", "family_rank"]).reset_index(drop=True))
    v.record_rows("Fig3 family rows", len(family_out))
    for fm in focuses:
        s = float(family_out[family_out.focus_mode == fm]["relative_family_share"].sum())
        v.check_sanity("Fig3", f"{fm} family shares sum to 1", abs(s - 1.0) <= 1e-2,
                       f"sum = {s:.4f}")

    def gf(fm, fam_name):
        r = family_out[(family_out.focus_mode == fm)
                       & (family_out.anatomical_family == fam_name)]
        return None if r.empty else float(r.iloc[0]["relative_family_share"])

    v.check_value("Fig3", "671 functional distal_upper_limb", 0.3545,
                  gf("functional_p50", "distal_upper_limb"), 1e-3)
    v.check_value("Fig3", "671 functional shoulder_chain", 0.2633,
                  gf("functional_p50", "shoulder_chain"), 1e-3)
    v.check_value("Fig3", "671 null-space lower_limb", 0.3440,
                  gf("null_space_after_p50", "lower_limb"), 1e-3)

    # --- PC counts --------------------------------------------------------- #
    pc_counts: dict = {}
    cname = "nullspace_top7_links_all_contexts.csv"
    v.register_file(cname)
    try:
        cm = load_csv(cname)
        v.check_columns("Fig3 PC counts", cm,
                        ["participant_id", "block_label", "comparison_label",
                         "functional_pc_count", "nullspace_pc_count"])
        r = cm[(cm.participant_id.astype(str) == PID) & (cm.block_label == BLOCK)
               & (cm.comparison_label == FIG3_COMP)]
        if not r.empty:
            fpc = int(float(r.iloc[0]["functional_pc_count"]))
            npc = int(float(r.iloc[0]["nullspace_pc_count"]))
            pc_counts = {"functional": fpc, "nullspace": npc, "m": fpc + npc}
    except DataError:
        v.note("Fig3: PC-count source unavailable; PC annotations omitted.")
    v.check_value("Fig3", "671 functional PCs", 3, pc_counts.get("functional"), 0.5)
    v.check_value("Fig3", "671 null-space PCs", 6, pc_counts.get("nullspace"), 0.5)

    # --- Null/all ratio (repetition variability diagnostic) ---------------- #
    rname = "nullspace_noise_vs_structure_diagnostic.csv"
    v.register_file(rname)
    rdf = load_csv(rname)
    req_r = ["participant_id", "block_label", "analysis_type",
             "timepoint_if_repetition", "null_p50_to_all_ratio",
             "null_p60_to_all_ratio", "null_p70_to_all_ratio_if_available"]
    v.check_columns("Fig3 ratio", rdf, req_r)
    sub = rdf[(rdf.participant_id.astype(str) == PID) & (rdf.block_label == BLOCK)
              & (rdf.analysis_type == "repetition_variability")
              & (rdf.timepoint_if_repetition.isin(TIMEPOINTS))].copy()
    for c in ["null_p50_to_all_ratio", "null_p60_to_all_ratio",
              "null_p70_to_all_ratio_if_available"]:
        sub[c] = pd.to_numeric(sub[c], errors="coerce")
    ratio_out = (sub.rename(columns={"timepoint_if_repetition": "timepoint"})
                 [["timepoint", "null_p50_to_all_ratio", "null_p60_to_all_ratio",
                   "null_p70_to_all_ratio_if_available"]]
                 .sort_values("timepoint").reset_index(drop=True))
    v.record_rows("Fig3 ratio timepoints", len(ratio_out))

    def g(tp, col):
        row = ratio_out[ratio_out.timepoint == tp]
        return None if row.empty else float(row.iloc[0][col])

    plotted = [("T1", 1.475976, 1.895384), ("T2", 2.476922, 2.476922),
               ("T3", 3.348045, 4.765013)]
    for tp, p50, p60 in plotted:
        v.check_value("Fig3", f"{tp} null/all p50", p50, g(tp, "null_p50_to_all_ratio"), 1e-2)
        v.check_value("Fig3", f"{tp} null/all p60", p60, g(tp, "null_p60_to_all_ratio"), 1e-2)

    v.check_sanity("Fig3", "null/all ratios > 0",
                   bool((ratio_out[["null_p50_to_all_ratio",
                                    "null_p60_to_all_ratio"]] > 0).all().all()),
                   "all plotted p50/p60 ratios positive")
    v.note("Fig3 null/all ratio: link-level variability in null-space (after p50/p60) "
           "divided by all-PC link variability at each within-timepoint R1–R2 contrast; "
           ">1 = later PCs carry disproportionate natural-variability magnitude.")
    v.note("Fig3 family share: within each subspace, relative_family_share = "
           "family's sum |link Δ| / total |link Δ| across all links in that subspace.")
    return family_out, ratio_out, pc_counts


# --------------------------------------------------------------------------- #
# Figure 1 (Figure-A lollipop style: abs stem + ratio-coloured dot)
# --------------------------------------------------------------------------- #
def _fig1_tip_label_x(pmax: float) -> float:
    """Fixed x column for tip labels so rows do not stagger into the next panel."""
    return pmax * 1.12


def _fig1_xlim_right(pmax: float) -> float:
    """Room for longest tip label (e.g. 31.2× (NV 0.000))."""
    return _fig1_tip_label_x(pmax) + pmax * 0.58


def _draw_fig1_distribution_inset(fig, dist: pd.DataFrame) -> None:
    """Compact Gini summary for T1-referenced contrasts only."""
    ax = fig.add_axes([0.36, 0.048, 0.22, 0.102])
    d = dist.set_index("comparison_label").reindex(COMPARISONS)
    x = np.arange(len(COMPARISONS))
    y = d["gini_link_change_share"].values
    ax.plot(x, y, "-", color="#888888", linewidth=1.5, zorder=1)
    ax.scatter(x, y, s=120, color=PID_COLOR, edgecolor="white",
               linewidth=1.2, zorder=3)
    for xi, (_, row) in zip(x, d.iterrows()):
        ax.annotate(
            f"Gini={row.gini_link_change_share:.2f}\n"
            f"Top-3={row.top3_share_pct:.0f}%",
            (xi, row.gini_link_change_share),
            textcoords="offset points", xytext=(0, 10), ha="center",
            fontsize=FB1["note"] - 0.5, color="#333333", zorder=4,
        )
    ax.set_xticks(x)
    ax.set_xticklabels([c.replace("_vs_", "\u2192") for c in COMPARISONS],
                       fontsize=FB1["note"])
    ax.set_ylabel("Gini of normalized |link \u0394|", fontsize=FB1["note"])
    ax.set_title("Concentration of link-level change",
                 fontsize=FB1["note"] + 0.5, fontweight="bold", pad=4)
    ax.set_xlim(-0.35, len(COMPARISONS) - 1 + 0.35)
    ax.set_ylim(0, max(0.58, float(np.nanmax(y)) * 1.28))
    ax.grid(axis="y", color="#ececec", linewidth=0.7, zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(axis="both", labelsize=FB1["note"] - 0.5, length=3)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.text(0.5, -0.38, "lower Gini \u2192 more distributed across links",
            transform=ax.transAxes, ha="center", fontsize=FB1["note"] - 1.5,
            color="#666666", style="italic")


def draw_fig1(fig, df: pd.DataFrame, dist: pd.DataFrame, meta: dict) -> None:
    fig.suptitle("Which body links changed beyond repetition variability?",
                 fontsize=FB1["fig_title"], fontweight="bold",
                 x=0.012, ha="left", y=0.985)
    fig.text(0.012, 0.928,
             "Top links per T1-referenced comparison (P3-P5, all-PC). Stem length = abs "
             "longitudinal \u0394; dot colour = \u0394 / T1 natural-variability ratio;",
             fontsize=FB1["subtitle"], color="#555555", ha="left")
    fig.text(0.012, 0.902,
             "\u00b1 = direction of signed \u0394. Inset: Gini of normalized |link \u0394| "
             "within each T1-referenced contrast (lower = more distributed).",
             fontsize=FB1["subtitle"], color="#555555", ha="left")

    axes = fig.subplots(1, 2)
    fig.subplots_adjust(left=0.17, right=0.78, top=0.86, bottom=0.28, wspace=0.55)

    for j, comp in enumerate(COMPARISONS):
        ax = axes[j]
        d = (df[df.comparison_label == comp]
             .sort_values("rank_by_abs_longitudinal_delta")
             .reset_index(drop=True))
        y = np.arange(len(d))
        pmax = float(d["abs_longitudinal_delta"].max())
        label_x = _fig1_tip_label_x(pmax)
        x_right = _fig1_xlim_right(pmax)

        for yi, (_, row) in zip(y, d.iterrows()):
            absd = float(row["abs_longitudinal_delta"])
            ratio = float(row[FIG1_RATIO_COL])
            outside = bool(row["outside_T1_NV_reference"])
            mcol = NV_CMAP(NV_NORM(min(ratio, NV_VMAX)))
            ax.hlines(yi, 0, absd, color="#bfbfbf", linewidth=FIG1_STEM_LW, zorder=2)
            ax.scatter(absd, yi, s=FIG1_DOT_S, color=mcol, zorder=4,
                       edgecolor=("#222222" if outside else "#9a9a9a"),
                       linewidth=(FIG1_DOT_EDGE_OUT if outside else FIG1_DOT_EDGE_IN))
            ax.text(-pmax * 0.055, yi, row["sign_glyph"], va="center", ha="center",
                    fontsize=FB1["annot"], color="#9a9a9a", zorder=5, clip_on=True)
            ax.text(label_x, yi, row["tip_label"], va="center", ha="left",
                    fontsize=FB1["annot"], zorder=5, clip_on=True,
                    color=("#1a1a1a" if outside else "#888888"),
                    fontweight=("bold" if outside else "normal"))

        ax.axvline(0, color="#333333", linewidth=1.6, zorder=3)
        ax.set_ylim(-0.48, len(d) - 0.52)
        ax.invert_yaxis()
        ax.set_yticks(y)
        labels = ax.set_yticklabels([wrap_link(l, width=20) for l in d["link_id"]],
                                    fontsize=FB1["tick"])
        for lab, fam in zip(labels, d["anatomical_family"]):
            lab.set_color(FAMILY_COLORS.get(fam, "#444444"))
            lab.set_fontweight("bold")
        ax.set_xlim(-pmax * 0.12, x_right)
        ax.tick_params(axis="y", length=0, pad=6)
        ax.tick_params(axis="x", labelsize=FB1["tick"], width=1.2, length=5)
        ax.grid(axis="x", color="#ececec", linewidth=0.9, zorder=0)
        ax.set_axisbelow(True)
        ax.xaxis.set_major_formatter(mticker.FormatStrFormatter("%.02f"))
        ax.set_xlabel(FIG1_X_AXIS, fontsize=FB1["axis"], fontweight="bold", labelpad=12)
        ax.set_title(comp.replace("_vs_", "\u2192"),
                     fontsize=FB1["panel_title"], fontweight="bold",
                     color=PID_COLOR, loc="left", pad=6)

    sm = matplotlib.cm.ScalarMappable(norm=NV_NORM, cmap=NV_CMAP)
    cax = fig.add_axes([0.815, 0.30, 0.022, 0.50])
    cbar = fig.colorbar(sm, cax=cax, extend="max")
    cbar.set_label("\u0394 / T1 natural-variability ratio", fontsize=FB1["axis"],
                   fontweight="bold", labelpad=14)
    cbar.ax.tick_params(labelsize=FB1["tick"], width=1.2)
    cbar.ax.axhline(1.0, color="#222222", linewidth=1.6)
    cbar.ax.text(1.55, 1.0, "= NV", va="center", ha="left",
                 fontsize=FB1["annot"], color="#222222",
                 transform=cbar.ax.get_yaxis_transform())

    _draw_fig1_distribution_inset(fig, dist)

    fam_order = [f for f in FAMILY_COLORS if f in set(df["anatomical_family"])]
    fam_handles = [Patch(facecolor=FAMILY_COLORS[f], edgecolor="white",
                         label=FAMILY_LABEL.get(f, f)) for f in fam_order]
    leg1 = fig.legend(handles=fam_handles, loc="lower left", ncol=2, frameon=False,
                      fontsize=FB1["legend"], bbox_to_anchor=(0.012, 0.018),
                      handlelength=1.4, columnspacing=1.0, handletextpad=0.5,
                      title="Anatomical family (link-label colour)")
    leg1.get_title().set_fontsize(FB1["note"])
    leg1.get_title().set_fontweight("bold")

    marker_handles = [
        Line2D([0], [0], marker="o", linestyle="none", markersize=14,
               markerfacecolor="#fdae61", markeredgecolor="#222222",
               markeredgewidth=2.2, label="Outside T1 NV reference (ratio > 1)"),
        Line2D([0], [0], marker="o", linestyle="none", markersize=14,
               markerfacecolor="#ffe9b0", markeredgecolor="#9a9a9a",
               markeredgewidth=1.2, label="Within T1 NV reference (ratio \u2264 1)"),
        Line2D([0], [0], marker="$+$", linestyle="none", color="#9a9a9a",
               markersize=14, label="\u00b1 = direction of signed \u0394"),
    ]
    fig.legend(handles=marker_handles, loc="lower right", ncol=1, frameon=False,
               fontsize=FB1["legend"], bbox_to_anchor=(0.74, 0.018),
               handlelength=1.4, handletextpad=0.5)

    fig.text(0.5, 0.002,
             "NV is a descriptive T1-repetition reference, not an inferential "
             "significance threshold.",
             fontsize=FB1["note"], color="#888888", ha="center")
    fig.text(0.5, -0.018, CAUTION, fontsize=FB1["note"], color="#888888", ha="center")


# --------------------------------------------------------------------------- #
# Figure 2
# --------------------------------------------------------------------------- #
def draw_fig2(fig, df: pd.DataFrame) -> None:
    _title(fig, "Participant 671: natural repetition variability - magnitude and concentration")
    fig.text(0.012, 0.915,
             "Mean = average abs R1-vs-R2 JcvPCA link Delta across all links "
             "(P3-P5, all-PC).",
             fontsize=FB["subtitle"], color="#555555", ha="left")

    axes = fig.subplots(1, 2)
    fig.subplots_adjust(left=0.10, right=0.975, top=0.86, bottom=0.16, wspace=0.28)
    d = df.set_index("timepoint").reindex(TIMEPOINTS)
    x = np.arange(len(TIMEPOINTS))
    bar_cols = [PID_COLOR if t == d["mean_abs_delta"].idxmax() else "#9B86C7"
                for t in TIMEPOINTS]

    # Panel A: mean abs delta.
    axA = axes[0]
    axA.bar(x, d["mean_abs_delta"].values, width=0.6, color=bar_cols,
            edgecolor="white", linewidth=1.2, zorder=3)
    for xi, val in zip(x, d["mean_abs_delta"].values):
        axA.text(xi, val + d["mean_abs_delta"].max() * 0.02, f"{val:.4f}",
                 ha="center", va="bottom", fontsize=FB["annot"], fontweight="bold",
                 color="#1a1a1a")
    axA.set_xticks(x)
    axA.set_xticklabels(TIMEPOINTS)
    axA.set_ylim(0, d["mean_abs_delta"].max() * 1.22)
    axA.set_ylabel(r"Mean abs R1-vs-R2 JcvPCA link $\Delta$ (unitless)",
                   fontsize=FB["axis"], fontweight="bold")
    axA.set_xlabel("Timepoint", fontsize=FB["axis"], fontweight="bold")
    axA.grid(axis="y", color="#ececec", linewidth=0.8, zorder=0)
    axA.set_axisbelow(True)
    axA.set_title("A  Magnitude of repetition variability", fontsize=FB["panel_title"],
                  fontweight="bold", loc="left", pad=8)
    axA.text(0.5, 0.94, "higher = larger repetition variability",
             transform=axA.transAxes, ha="center", va="top",
             fontsize=FB["annot"], style="italic", color="#666666")

    # Panel B: Gini.
    axB = axes[1]
    axB.bar(x, d["gini"].values, width=0.6, color=bar_cols, edgecolor="white",
            linewidth=1.2, zorder=3)
    for xi, val in zip(x, d["gini"].values):
        axB.text(xi, val + 0.012, f"{val:.3f}", ha="center", va="bottom",
                 fontsize=FB["annot"], fontweight="bold", color="#1a1a1a")
    axB.set_xticks(x)
    axB.set_xticklabels(TIMEPOINTS)
    axB.set_ylim(0, max(0.7, d["gini"].max() * 1.2))
    axB.set_ylabel(r"Gini of link-level abs $\Delta$", fontsize=FB["axis"],
                   fontweight="bold")
    axB.set_xlabel("Timepoint", fontsize=FB["axis"], fontweight="bold")
    axB.grid(axis="y", color="#ececec", linewidth=0.8, zorder=0)
    axB.set_axisbelow(True)
    axB.set_title("B  Concentration across links", fontsize=FB["panel_title"],
                  fontweight="bold", loc="left", pad=8)
    axB.text(0.5, 0.94, "higher Gini = concentrated in fewer links;\n"
                        "lower Gini = more distributed",
             transform=axB.transAxes, ha="center", va="top",
             fontsize=FB["annot"], style="italic", color="#666666")

    fig.text(0.5, 0.015, "Natural variability changes over time and is "
             "link-structured, not a single fixed noise floor.   " + CAUTION,
             fontsize=FB["note"], color="#888888", ha="center")


# --------------------------------------------------------------------------- #
# Figure 3 — functional vs null-space family (Figure B style) + null/all ratio
# --------------------------------------------------------------------------- #
P50_STYLE = {"color": "#3B6FB6", "marker": "o", "label": "null/all ratio  p50"}
P60_STYLE = {"color": "#D1601A", "marker": "s", "label": "null/all ratio  p60"}


def _draw_fig3_family_panel(ax, family_df: pd.DataFrame, pc_counts: dict) -> None:
    func = (family_df[family_df.focus_mode == "functional_p50"]
            .set_index("anatomical_family")["relative_family_share"])
    null = (family_df[family_df.focus_mode == "null_space_after_p50"]
            .set_index("anatomical_family")["relative_family_share"])
    fams = list(func.sort_values(ascending=False).index)
    y = np.arange(len(fams))
    h = 0.38
    xmax = float(family_df["relative_family_share"].max()) * 1.34

    for yi, fam in zip(y, fams):
        fv = float(func.get(fam, 0.0))
        nv = float(null.get(fam, 0.0))
        ax.barh(yi + h / 2 + 0.01, fv, height=h, color=FUNC_COLOR,
                edgecolor="white", linewidth=0.9, zorder=3)
        ax.barh(yi - h / 2 - 0.01, nv, height=h, color=NULL_COLOR,
                edgecolor="white", linewidth=0.9, zorder=3)
        ax.text(fv + xmax * 0.012, yi + h / 2 + 0.01, f"{fv * 100:.0f}%",
                va="center", ha="left", fontsize=FB["annot"], color="#1a1a1a")
        gains = nv > fv + 1e-9
        ax.text(nv + xmax * 0.012, yi - h / 2 - 0.01,
                (f"{nv * 100:.0f}%  \u25b2" if gains else f"{nv * 100:.0f}%"),
                va="center", ha="left", fontsize=FB["annot"],
                color=("#9A5A00" if gains else "#1a1a1a"),
                fontweight=("bold" if gains else "normal"))

    ax.set_yticks(y)
    labels = ax.set_yticklabels([FAMILY_LABEL.get(f, f) for f in fams],
                                fontsize=FB["tick"])
    for lab, fam in zip(labels, fams):
        lab.set_color(FAMILY_COLORS.get(fam, "#444444"))
        lab.set_fontweight("bold")
    ax.invert_yaxis()
    ax.set_xlim(0, xmax)
    ax.tick_params(axis="y", length=0, pad=4)
    ax.grid(axis="x", color="#ececec", linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    ax.xaxis.set_major_formatter(mticker.PercentFormatter(xmax=1.0, decimals=0))
    ax.set_xlabel("Relative family share of |link \u0394|", fontsize=FB["axis"],
                  fontweight="bold")
    pc = pc_counts
    sub = (f"functional = {pc['functional']} PCs, null-space = {pc['nullspace']} PCs; "
           f"m = {pc['m']}" if pc else "")
    ax.set_title(f"Participant {PID}  \u2014  {FIG3_COMP.replace('_vs_', '\u2192')}"
                 + (f"\n({sub})" if sub else ""),
                 fontsize=FB["panel_title"], fontweight="bold",
                 color=PID_COLOR, loc="left", pad=6)


def _draw_fig3_ratio_panel(ax, ratio_df: pd.DataFrame) -> None:
    d = ratio_df.set_index("timepoint").reindex(TIMEPOINTS)
    x = np.arange(len(TIMEPOINTS))
    for col, st in (("null_p50_to_all_ratio", P50_STYLE),
                    ("null_p60_to_all_ratio", P60_STYLE)):
        ax.plot(x, d[col].values, "-", color=st["color"], linewidth=2.5,
                marker=st["marker"], markersize=11, markeredgecolor="white",
                markeredgewidth=1.2, label=st["label"], zorder=4)
        for xi, val in zip(x, d[col].values):
            ax.annotate(f"{val:.2f}", (xi, val), textcoords="offset points",
                        xytext=(0, 8), ha="center", fontsize=FB["annot"] - 1,
                        fontweight="bold", color=st["color"])
    ax.axhline(1.0, color="#888888", linestyle="--", linewidth=1.8, zorder=2)
    ax.text(len(TIMEPOINTS) - 1 + 0.15, 1.0, "all-PC (= 1)",
            va="center", ha="left", fontsize=FB["annot"] - 1, color="#666666")
    ax.set_xticks(x)
    ax.set_xticklabels(TIMEPOINTS)
    ax.set_xlim(-0.35, len(TIMEPOINTS) - 1 + 0.45)
    ax.set_ylim(0, max(5.2, float(d[["null_p50_to_all_ratio",
                                     "null_p60_to_all_ratio"]].max().max()) * 1.15))
    ax.set_xlabel("Timepoint (R1 vs R2)", fontsize=FB["axis"], fontweight="bold")
    ax.set_ylabel("null / all ratio", fontsize=FB["axis"], fontweight="bold")
    ax.grid(axis="y", color="#ececec", linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    ax.set_title("Null-space vs all-PC\nrepetition variability",
                 fontsize=FB["panel_title"], fontweight="bold", loc="left", pad=6)
    ax.legend(loc="upper left", frameon=False, fontsize=FB["legend"] - 1,
              handlelength=1.4)


def draw_fig3(fig, family_df: pd.DataFrame, ratio_df: pd.DataFrame,
              pc_counts: dict) -> None:
    _title(fig, "Participant 671: functional vs null-space link contribution by family")
    fig.text(0.012, 0.905,
             "Left: relative share of total |link \u0394| within each anatomical family, "
             "split by variance-informed PC subspace (P3-P5, T1\u2192T2). "
             "Blue = functional subspace (first ~50% explained variance): where primary "
             "task-relevant link changes concentrate.",
             fontsize=FB["subtitle"], color="#555555", ha="left")
    fig.text(0.012, 0.878,
             "Orange = null-space (remaining PCs): coordination / redundant / expressive "
             "degrees of freedom \u2014 not unused movement. For each family, null-space "
             "share = fraction of that family\u2019s |link \u0394| expressed through later PCs.",
             fontsize=FB["subtitle"], color="#555555", ha="left")
    fig.text(0.012, 0.851,
             "\u25b2 = family gains share in null-space vs functional. Right: null/all ratio "
             "= null-space link variability \u00f7 all-PC link variability at each "
             "within-timepoint R1\u2013R2 contrast; >1 means later PCs carry disproportionate "
             "natural-variability magnitude (p50/p60 thresholds).",
             fontsize=FB["subtitle"], color="#555555", ha="left")

    gs = fig.add_gridspec(1, 2, width_ratios=[1.55, 1.0], wspace=0.34)
    ax_fam = fig.add_subplot(gs[0, 0])
    ax_ratio = fig.add_subplot(gs[0, 1])
    fig.subplots_adjust(left=0.14, right=0.97, top=0.82, bottom=0.17)

    _draw_fig3_family_panel(ax_fam, family_df, pc_counts)
    _draw_fig3_ratio_panel(ax_ratio, ratio_df)

    handles = [
        Patch(facecolor=FUNC_COLOR, edgecolor="white",
              label="Functional subspace (first ~50% variance)"),
        Patch(facecolor=NULL_COLOR, edgecolor="white",
              label="Null-space after p50"),
        Line2D([0], [0], marker="^", linestyle="none", color="#9A5A00",
               markersize=9, label="Family gains share in null-space"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=3, frameon=False,
               fontsize=FB["legend"], bbox_to_anchor=(0.5, 0.02),
               handlelength=1.2, columnspacing=1.4)
    fig.text(0.5, -0.01,
             "Null-space describes later-PC coordination structure, not missing movement.   "
             + CAUTION,
             fontsize=FB["note"], color="#888888", ha="center")


# --------------------------------------------------------------------------- #
# Figure 4 — functional vs null-space family share: T1→T2 vs T1→T3, p50/p60
# --------------------------------------------------------------------------- #
FIG4_COMPARISONS = ["T1_vs_T2", "T1_vs_T3"]
FIG4_FOCUS_MODES = [
    "functional_p50", "null_space_after_p50",
    "functional_p60", "null_space_after_p60",
]
FIG4_MODE_STYLE = {
    "functional_p50": FUNC_P50_COLOR,
    "null_space_after_p50": NULL_P50_COLOR,
    "functional_p60": FUNC_P60_COLOR,
    "null_space_after_p60": NULL_P60_COLOR,
}


def prepare_fig4(v: Validator) -> pd.DataFrame:
    fname = "body_region_anatomical_family_summary.csv"
    v.register_file(fname)
    fdf = load_csv(fname)
    req = ["participant_id", "block_label", "comparison_label", "focus_mode",
           "anatomical_family", "relative_family_share", "family_rank",
           "top_link_in_family"]
    v.check_columns("Fig4", fdf, req)
    sub = fdf[
        (fdf.participant_id.astype(str) == PID)
        & (fdf.block_label == BLOCK)
        & (fdf.comparison_label.isin(FIG4_COMPARISONS))
        & (fdf.focus_mode.isin(FIG4_FOCUS_MODES))
    ].copy()
    sub["relative_family_share"] = pd.to_numeric(sub["relative_family_share"],
                                                 errors="coerce")
    out = (
        sub[["comparison_label", "focus_mode", "anatomical_family",
             "relative_family_share", "family_rank", "top_link_in_family"]]
        .sort_values(["comparison_label", "focus_mode", "family_rank"])
        .reset_index(drop=True)
    )
    v.record_rows("Fig4 family rows", len(out))
    for comp in FIG4_COMPARISONS:
        for fm in FIG4_FOCUS_MODES:
            s = float(
                out[(out.comparison_label == comp) & (out.focus_mode == fm)]
                ["relative_family_share"].sum()
            )
            v.check_sanity("Fig4", f"{comp} {fm} shares sum to 1",
                             abs(s - 1.0) <= 1e-2, f"sum = {s:.4f}")

    def g(comp, fm, fam):
        r = out[(out.comparison_label == comp) & (out.focus_mode == fm)
                & (out.anatomical_family == fam)]
        return None if r.empty else float(r.iloc[0]["relative_family_share"])

    v.check_value("Fig4", "T1_vs_T2 func p50 distal_upper_limb", 0.3545,
                  g("T1_vs_T2", "functional_p50", "distal_upper_limb"), 1e-3)
    v.check_value("Fig4", "T1_vs_T2 null p50 lower_limb", 0.3440,
                  g("T1_vs_T2", "null_space_after_p50", "lower_limb"), 1e-3)
    v.check_value("Fig4", "T1_vs_T2 null p60 lower_limb", 0.3191,
                  g("T1_vs_T2", "null_space_after_p60", "lower_limb"), 1e-3)
    v.check_value("Fig4", "T1_vs_T3 null p50 shoulder_chain", 0.3191,
                  g("T1_vs_T3", "null_space_after_p50", "shoulder_chain"), 1e-3)
    return out


def _draw_fig4_panel(ax, panel_df: pd.DataFrame, comparison: str) -> None:
    by_mode = {
        fm: panel_df[panel_df.focus_mode == fm]
        .set_index("anatomical_family")["relative_family_share"]
        for fm in FIG4_FOCUS_MODES
    }
    rank_key = by_mode["null_space_after_p50"]
    if rank_key.empty:
        rank_key = by_mode["functional_p50"]
    fams = list(rank_key.sort_values(ascending=False).index)
    y = np.arange(len(fams))
    h = 0.17
    step = h + 0.03
    offsets = [1.5 * step, 0.5 * step, -0.5 * step, -1.5 * step]
    xmax = float(panel_df["relative_family_share"].max()) * 1.42

    for yi, fam in zip(y, fams):
        for off, fm in zip(offsets, FIG4_FOCUS_MODES):
            val = float(by_mode[fm].get(fam, 0.0))
            ypos = yi + off
            ax.barh(ypos, val, height=h, color=FIG4_MODE_STYLE[fm],
                    edgecolor="white", linewidth=0.7, zorder=3)
            ax.text(val + xmax * 0.012, ypos, f"{val * 100:.0f}%",
                    va="center", ha="left", fontsize=FB["annot"] - 0.5,
                    color="#1a1a1a")

    ax.set_yticks(y)
    labels = ax.set_yticklabels([FAMILY_LABEL.get(f, f) for f in fams],
                                fontsize=FB["tick"])
    for lab, fam in zip(labels, fams):
        lab.set_color(FAMILY_COLORS.get(fam, "#444444"))
        lab.set_fontweight("bold")
    ax.invert_yaxis()
    ax.set_xlim(0, xmax)
    ax.tick_params(axis="y", length=0, pad=4)
    ax.grid(axis="x", color="#ececec", linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    ax.xaxis.set_major_formatter(mticker.PercentFormatter(xmax=1.0, decimals=0))
    ax.set_xlabel("Relative family share within each subspace |link Δ|",
                  fontsize=FB["axis"], fontweight="bold")
    ax.set_title(
        f"{comparison.replace('_vs_', ' \u2192 ')}  "
        f"(functional PCs: 3\u21924; null-space PCs: 6\u21925)",
        fontsize=FB["panel_title"], fontweight="bold", color=PID_COLOR,
        loc="left", pad=6,
    )


def draw_fig4(fig, df: pd.DataFrame) -> None:
    _title(fig, "Functional vs. Null-Space Anatomical Family Contributions")
    fig.text(
        0.012, 0.905,
        "Relative proportion of absolute JcvPCA Delta within functional and null-space "
        "subsets, evaluated at p50 and p60 cumulative variance thresholds. Each subspace "
        "row normalizes to 100% to show regional distribution.",
        fontsize=FB["subtitle"], color="#555555", ha="left",
    )
    fig.text(
        0.012, 0.872,
        "The p60 threshold acts as a sensitivity check. The null-space isolates later-PC, "
        "less-dominant kinematic variability.",
        fontsize=FB["subtitle"], color="#555555", ha="left",
    )

    axes = fig.subplots(1, 2)
    fig.subplots_adjust(left=0.18, right=0.97, top=0.80, bottom=0.20, wspace=0.42)
    for ax, comp in zip(axes, FIG4_COMPARISONS):
        panel = df[df.comparison_label == comp]
        _draw_fig4_panel(ax, panel, comp)

    handles = [
        Patch(facecolor=FUNC_P50_COLOR, edgecolor="white",
              label="Functional p50 (first ~50% variance)"),
        Patch(facecolor=NULL_P50_COLOR, edgecolor="white",
              label="Null-space after p50"),
        Patch(facecolor=FUNC_P60_COLOR, edgecolor="white",
              label="Functional p60 (first ~60% variance; sensitivity)"),
        Patch(facecolor=NULL_P60_COLOR, edgecolor="white",
              label="Null-space after p60 (sensitivity)"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=2, frameon=False,
               fontsize=FB["legend"], bbox_to_anchor=(0.5, 0.02),
               handlelength=1.2, columnspacing=1.6)
    fig.text(
        0.5, -0.01,
        "Descriptive blinded timepoint-related kinematic variation; participant 671 only.   "
        + CAUTION,
        fontsize=FB["note"], color="#888888", ha="center",
    )


# --------------------------------------------------------------------------- #
# Captions
# --------------------------------------------------------------------------- #
def write_captions(path) -> None:
    text = """# Participant 671 Poster Figures - Captions

Participant-level descriptive example; blinded timepoint-related kinematic
variation; methodological validation / exploratory longitudinal signal. Not a
treatment-specific effect. Participant 252 is analysed separately (supplement).

## Figure 1 - Which body links changed beyond repetition variability?
Two T1-referenced panels (T1→T2, T1→T3 only; T2→T3 excluded) show the top 7 links
per comparison on P3-P5 (all-PC), ranked by |signed longitudinal JcvPCA Δ|.
Figure-A lollipop style: grey stem = absolute Δ; coloured dot = Δ / T1 R1–R2 NV
ratio; thick dot ring = ratio > 1. A compact inset summarizes the distribution of
|link Δ| across all links within each T1-referenced contrast (Gini of normalized
|link Δ|; lower = more distributed; Top-3 share annotated). See
`poster_671_figure1_logic.md`.

## Figure 2 - Natural repetition variability: magnitude and concentration
Panel A: mean absolute R1-vs-R2 JcvPCA link Delta per timepoint (largest at T2 =
0.0156; T1 = 0.0125; T3 = 0.0110). Panel B: Gini of link-level absolute Delta per
timepoint (largest at T2 = 0.563; T1 = 0.537; lowest at T3 = 0.459). Higher mean
indicates larger repetition variability; higher Gini indicates concentration in
fewer links, lower Gini a more distributed pattern. Natural variability changes
over time and is link-structured, not a single fixed noise floor.

## Figure 3 - Functional vs null-space contribution by anatomical family
Left panel (Figure-B style, participant 671 only): paired bars show each anatomical
family's share of total |link Δ| in the functional subspace (first ~50% variance; blue)
vs the complementary null-space (orange; coordination / redundant / expressive PCs — not
unused movement). ▲ marks families with higher null-space than functional share (e.g.
lower limb 34% null-space vs 19% functional on T1→T2). Right panel: null/all ratio at
T1/T2/T3 R1–R2 contrasts — null-space variability divided by all-PC variability; all
values >1 (p50/p60). Lower functional share for a family = more of that family's change
is expressed through later PCs; higher null/all ratio = natural variability is
disproportionately carried by null-space.

## Figure 4 - Functional vs null-space family share: T1→T2 vs T1→T3 with p50/p60 sensitivity
Two panels (T1→T2, T1→T3) show relative anatomical-family share of |link Δ| within
**functional** (blue) and **null-space** (orange) subspaces separately. For each
family, four bars compare functional p50, null p50, functional p60, and null p60
(sensitivity tier). Each subspace row sums to 100% within its threshold. On T1→T2,
distal upper limb leads functional (~28–35%) while lower limb leads null-space
(~32–34%). On T1→T3, proximal upper limb / shoulder chain dominate functional
(~28–31%) while shoulder chain leads null-space (~29–32%). p50 and p60 patterns
are broadly stable for participant 671.
"""
    path.write_text(text, encoding="utf-8")


def write_fig1_logic_note(path, meta: dict, dist: pd.DataFrame) -> None:
    links_txt = "\n".join(
        f"- **{comp.replace('_vs_', '→')}**: {', '.join(links)}"
        for comp, links in meta["links_by_panel"].items()
    )
    dist_txt = "\n".join(
        f"- **{r.comparison_label.replace('_vs_', '→')}**: "
        f"Gini={r.gini_link_change_share:.3f}, "
        f"Top-3 share={r.top3_share_pct:.1f}% "
        f"(n={int(r.n_links)} links, sum |Δ|={r.sum_abs_longitudinal_delta:.4f})"
        for _, r in dist.iterrows()
    )
    pp = meta["pp_conversion_possible"]
    text = f"""# Figure 1 logic (participant 671, P3_P4_P5)

## Style
Matches `figure_A_longitudinal_shift_vs_NV.png` (lollipop layout): absolute stem
length, ratio-encoded dot colour, ± direction glyph, and `ratio× (NV value)` tip
labels. Participant 671 only; **T1-referenced panels only** (T1→T2, T1→T3).

## Purpose
Show which links changed, how large the change is, whether it exceeds T1
repetition variability, and whether change is concentrated or distributed across links.

## Main panels
- T1→T2 and T1→T3 (top {meta['top_n_shown']} links per panel by |signed longitudinal Δ|)
- T2→T3 is **not** included (different JcvPCA reference space).

## Links shown (top {meta['top_n_shown']} per panel)
{links_txt}

## Distribution inset (T1_vs_T2 and T1_vs_T3 only)
Within each T1-referenced contrast, Gini summarizes whether link-level change is
concentrated in a few links or distributed across links. Top-3 share indicates how
much of total |link Δ| is captured by the three most changing links.

**Computation (per contrast, all links in contrast):**
1. `abs_delta = |longitudinal_delta|`
2. `link_change_share = abs_delta / sum(abs_delta)` across all links
3. `Gini(link_change_share)` and `Top-3 share = sum of 3 largest link_change_share`

**Values plotted in inset:**
{dist_txt}

This is a **within-contrast** distribution summary only — not a direct shared-space
trajectory across sessions.

## X-axis (stem length)
- **Label:** {meta['x_axis_label']}
- Absolute |longitudinal Δ|; direction shown by ± glyph left of zero.
- **Percentage-point conversion:** {'yes' if pp else 'no'}
- **Reason:** {meta['pp_conversion_reason']}

## Dot colour and ring
- **Fill:** Δ / T1 NV ratio (yellow→red colorbar; clipped at 4×)
- **Thick dark ring:** ratio > 1 (outside T1 NV reference)
- **Thin grey ring:** ratio ≤ 1 (within T1 NV reference)

## Tip label
- **Format:** e.g. `3.6× (NV 0.011)`
- **Ratio:** {meta['xnv_formula']}
- **Denominator:** {meta['xnv_denominator']}
- Descriptive reference only; not inferential significance.
"""
    path.write_text(text, encoding="utf-8")


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    _poster_style()
    v = Validator()

    try:
        df1, dist1, fig1_meta = prepare_fig1(v)
        df2 = prepare_fig2(v)
        df3_fam, df3_ratio, pc3 = prepare_fig3(v)
        df4 = prepare_fig4(v)
    except DataError as exc:
        v.errors.append(str(exc))
        v.write_report(OUT_DIR / "poster_671_validation_report.md")
        print(f"[FAIL] Missing required data: {exc}")
        return 1

    v.write_report(OUT_DIR / "poster_671_validation_report.md")
    if v.status == "FAIL":
        print("[FAIL] Validation failed; figures not generated. See report.")
        return 1
    for label, frame in (("1", df1), ("2", df2)):
        if frame.empty:
            print(f"[FAIL] Empty plotting table for Figure {label}; aborting.")
            return 1
    if df3_fam.empty or df3_ratio.empty:
        print("[FAIL] Empty plotting table for Figure 3; aborting.")
        return 1
    if df4.empty:
        print("[FAIL] Empty plotting table for Figure 4; aborting.")
        return 1

    link_export = df1.copy()
    link_export.insert(0, "table_type", "top_link")
    dist_export = dist1.copy()
    combined = pd.concat([link_export, dist_export], ignore_index=True, sort=False)
    combined.to_csv(OUT_DIR / "poster_671_figure1_plot_table.csv", index=False)
    dist1.to_csv(OUT_DIR / "poster_671_figure1_distribution_summary.csv", index=False)
    df2.to_csv(OUT_DIR / "poster_671_figure2_plot_table.csv", index=False)
    fam_export = df3_fam.copy()
    fam_export.insert(0, "table_type", "family_share")
    ratio_export = df3_ratio.copy()
    ratio_export.insert(0, "table_type", "null_all_ratio")
    pd.concat([fam_export, ratio_export], ignore_index=True, sort=False).to_csv(
        OUT_DIR / "poster_671_figure3_plot_table.csv", index=False)
    df4.to_csv(OUT_DIR / "poster_671_figure4_plot_table.csv", index=False)

    out = {}
    fig = plt.figure(figsize=(19, 8.5))
    draw_fig1(fig, df1, dist1, fig1_meta)
    out["1"] = _save(fig, "poster_671_figure1_longitudinal_vs_NV")

    fig = plt.figure(figsize=(14, 7.5))
    draw_fig2(fig, df2)
    out["2"] = _save(fig, "poster_671_figure2_nv_magnitude_gini")

    fig = plt.figure(figsize=(16, 8.5))
    draw_fig3(fig, df3_fam, df3_ratio, pc3)
    out["3"] = _save(fig, "poster_671_figure3_functional_nullspace_family")

    fig = plt.figure(figsize=(15, 9))
    draw_fig4(fig, df4)
    out["4"] = _save(fig, "poster_671_figure4_nullspace_sensitivity")

    write_captions(OUT_DIR / "poster_671_captions.md")
    write_fig1_logic_note(OUT_DIR / "poster_671_figure1_logic.md", fig1_meta, dist1)

    print("=" * 74)
    print("PARTICIPANT 671 POSTER FIGURES - SUMMARY")
    print("=" * 74)
    print(f"Output directory : {OUT_DIR.relative_to(PROJECT_ROOT)}")
    print(f"Validation status: {v.status} "
          f"({sum(x['match'] for x in v.value_checks)}/{len(v.value_checks)} value checks matched)")
    print("-" * 74)
    print(f"Figure 1  Top-{fig1_meta['top_n_shown']} lollipop panels + Gini inset;")
    print("          T1→T2 & T1→T3 only (671 P3_P4_P5).")
    print("Figure 2  Mean abs R1-R2 Delta (T2 peak) + Gini (T2 peak, T3 lowest).")
    print("Figure 3  Functional vs null-space family shares (671, Fig-B style)")
    print("          + null/all ratio panel (p50/p60 across T1/T2/T3).")
    print("Figure 4  Functional vs null-space family share T1→T2 vs T1→T3; p50/p60.")
    print("-" * 74)
    for k in ("1", "2", "3", "4"):
        print(f"  [Fig {k}] " + ", ".join(out[k]))
    print("  tables   : poster_671_figure1_plot_table.csv (+ distribution_summary)")
    print("  fig1 note: poster_671_figure1_logic.md")
    print("  captions : poster_671_captions.md")
    print("  report   : poster_671_validation_report.md")
    print("=" * 74)
    return 0 if v.status in ("PASS", "WARNING") else 1


if __name__ == "__main__":
    raise SystemExit(main())
