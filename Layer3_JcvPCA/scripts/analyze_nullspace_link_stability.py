#!/usr/bin/env python3
"""Null-space link stability and interpretation review from existing batch outputs."""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import kendalltau, spearmanr

ROOT = Path(__file__).resolve().parents[1]
BATCH = ROOT / "outputs" / "gaga_batch_jcvpca_20260626_193319"
OUT = ROOT / "outputs" / "nullspace_link_stability_review"

PARTICIPANTS = ["671", "252"]
BLOCKS = [("A", "all_P1_P2_P3_P4_P5"), ("B", "P3_P4_P5")]
NULL_FOCUS = ["null_space_after_p50", "null_space_after_p60", "null_space_after_p70"]
PRIMARY_NULL = ["null_space_after_p50", "null_space_after_p60"]

REPETITION = [
    ("T1", "T1_R1_vs_T1_R2", "I_T1_R1_vs_R2"),
    ("T2", "T2_R1_vs_T2_R2", "I_T2_R1_vs_R2"),
    ("T3", "T3_R1_vs_T3_R2", "I_T3_R1_vs_R2"),
]
LONGITUDINAL = [
    ("T1_vs_T2", "L1_T1_vs_T2"),
    ("T1_vs_T3", "L2_T1_vs_T3"),
]
EXPLORATORY = [("T2_vs_T3", "L3_T2_vs_T3")]

LINK_SPECS = {
    "Neck_to_Head": ("trunk_neck_head", "head_neck", "midline"),
    "Chest_to_Neck": ("trunk_neck_head", "head_neck", "midline"),
    "Chest_to_LShoulder": ("shoulder_chain", "proximal_upper", "left"),
    "Chest_to_RShoulder": ("shoulder_chain", "proximal_upper", "right"),
    "LShoulder_to_LUArm": ("shoulder_chain", "proximal_upper", "left"),
    "RShoulder_to_RUArm": ("shoulder_chain", "proximal_upper", "right"),
    "LUArm_to_LFArm": ("proximal_upper_limb", "distal_upper", "left"),
    "RUArm_to_RFArm": ("proximal_upper_limb", "distal_upper", "right"),
    "LFArm_to_LHand": ("distal_upper_limb", "distal_upper", "left"),
    "RFArm_to_RHand": ("distal_upper_limb", "distal_upper", "right"),
    "LThigh_to_LShin": ("lower_limb", "lower_limb", "left"),
    "LShin_to_LFoot": ("lower_limb", "lower_limb", "left"),
    "RThigh_to_RShin": ("lower_limb", "lower_limb", "right"),
    "RShin_to_RFoot": ("lower_limb", "lower_limb", "right"),
    "252_to_LThigh": ("pelvis_root", "pelvis_proximal_lower", "left"),
    "252_to_RThigh": ("pelvis_root", "pelvis_proximal_lower", "right"),
}

MISSING_INPUTS: list[str] = []


def note_missing(msg: str) -> None:
    if msg not in MISSING_INPUTS:
        MISSING_INPUTS.append(msg)


def f4(x) -> str:
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return "NA"
    if pd.isna(x):
        return "NA"
    return f"{float(x):.4f}"


def md_table(headers: list[str], rows: list[list]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(lines)


def link_meta(link_id: str) -> tuple[str, str, str]:
    if link_id in LINK_SPECS:
        return LINK_SPECS[link_id]
    return ("mixed_or_other", "unknown", "unknown")


def gini(values: np.ndarray) -> float:
    x = np.sort(np.asarray(values, dtype=float))
    x = x[x >= 0]
    if x.size == 0:
        return float("nan")
    if np.allclose(x, 0):
        return 0.0
    n = x.size
    idx = np.arange(1, n + 1)
    return float((2 * np.sum(idx * x) / (n * np.sum(x))) - (n + 1) / n)


def aggregate_link_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    col_a = "JRW_A_link" if "JRW_A_link" in df.columns else "JRW_A"
    col_b = "JRW_B_link" if "JRW_B_link" in df.columns else "JRW_B"
    col_d = "JcvPCA_link" if "JcvPCA_link" in df.columns else "JcvPCA_link_delta"
    return (
        df.groupby("link_id", as_index=False)
        .agg(JRW_A=(col_a, "mean"), JRW_B=(col_b, "mean"), JcvPCA_link_delta=(col_d, "mean"))
        .sort_values("link_id")
    )


def finalize_links(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    out["abs_delta"] = out["JcvPCA_link_delta"].abs()
    out["sign_of_delta"] = np.sign(out["JcvPCA_link_delta"]).astype(int)
    total = float(out["abs_delta"].sum())
    out["relative_abs_delta_share"] = out["abs_delta"] / total if total > 0 else 0.0
    out = out.sort_values("abs_delta", ascending=False).reset_index(drop=True)
    out["rank_by_abs_delta"] = np.arange(1, len(out) + 1)
    cum = out["abs_delta"].cumsum()
    out["cumulative_abs_delta_share"] = cum / total if total > 0 else 0.0
    return out


def load_focus_links(pid: str, block_id: str, comp_key: str, focus_mode: str) -> pd.DataFrame:
    base = BATCH / "comparisons" / f"{pid}_{block_id}_{comp_key}"
    if focus_mode == "null_space_after_p70":
        return load_p70_links(base)
    if focus_mode == "all":
        run_dir = base / "run"
    else:
        run_dir = base / f"run_{focus_mode}"
    path = run_dir / "link_level_jrw_rss.csv"
    if not path.is_file():
        note_missing(str(path.relative_to(ROOT)))
        return pd.DataFrame()
    return finalize_links(aggregate_link_csv(path))


def load_p70_links(base: Path) -> pd.DataFrame:
    pc_path = base / "run" / "pc_focus_table.csv"
    link_path = base / "run" / "link_level_jrw_rss.csv"
    if not pc_path.is_file() or not link_path.is_file():
        note_missing(f"p70 derivation missing under {base.name}")
        return pd.DataFrame()
    pc = pd.read_csv(pc_path).sort_values("pc")
    p70_row = pc[pc["cumulative_explained_variance"] >= 0.70]
    if p70_row.empty:
        note_missing(f"p70 threshold not reached in {base.name}")
        return pd.DataFrame()
    p70_pc = int(p70_row.iloc[0]["pc"])
    null_pcs = pc.loc[pc["pc"] > p70_pc, "pc"].tolist()
    if not null_pcs:
        return pd.DataFrame()
    raw = pd.read_csv(link_path)
    sub = raw[raw["pc"].isin(null_pcs)]
    if sub.empty:
        return pd.DataFrame()
    col_a = "JRW_A_link" if "JRW_A_link" in sub.columns else "JRW_A"
    col_b = "JRW_B_link" if "JRW_B_link" in sub.columns else "JRW_B"
    col_d = "JcvPCA_link" if "JcvPCA_link" in sub.columns else "JcvPCA_link_delta"
    agg = (
        sub.groupby("link_id", as_index=False)
        .agg(JRW_A=(col_a, "mean"), JRW_B=(col_b, "mean"), JcvPCA_link_delta=(col_d, "mean"))
        .sort_values("link_id")
    )
    return finalize_links(agg)


def load_pc_per_link(base: Path) -> pd.DataFrame:
    path = base / "run" / "link_level_jrw_rss.csv"
    if not path.is_file():
        return pd.DataFrame()
    return pd.read_csv(path)


def load_pc_meta(base: Path) -> pd.DataFrame:
    path = base / "run" / "pc_focus_table.csv"
    return pd.read_csv(path) if path.is_file() else pd.DataFrame()


def get_pc_focus_row(pid: str, block_id: str, comp_key: str) -> dict:
    df = pd.read_csv(BATCH / "pc_focus_p50_p60_by_comparison.csv")
    row = df[
        (df.participant_id.astype(str) == pid)
        & (df.block_id == block_id)
        & (df.comparison_id == comp_key)
    ]
    if row.empty:
        return {}
    r = row.iloc[0]
    return {
        "selected_m": int(r.selected_m),
        "functional_pc_count_p50": len(str(r.included_pcs_functional_p50).split(",")) if pd.notna(r.included_pcs_functional_p50) else 0,
        "nullspace_pc_count_p50": int(r.null_space_p50_n_pcs) if pd.notna(r.null_space_p50_n_pcs) else 0,
        "functional_pc_count_p60": len(str(r.included_pcs_functional_p60).split(",")) if pd.notna(r.included_pcs_functional_p60) else 0,
        "nullspace_pc_count_p60": int(r.null_space_p60_n_pcs) if pd.notna(r.null_space_p60_n_pcs) else 0,
        "p50": int(r.p50),
        "p60": int(r.p60),
    }


def functional_null_counts(focus_mode: str, meta: dict) -> tuple[int | None, int | None]:
    if not meta:
        return None, None
    if focus_mode == "null_space_after_p50":
        return meta.get("functional_pc_count_p50"), meta.get("nullspace_pc_count_p50")
    if focus_mode == "null_space_after_p60":
        return meta.get("functional_pc_count_p60"), meta.get("nullspace_pc_count_p60")
    if focus_mode == "null_space_after_p70":
        return None, None
    return None, None


def top_n(df: pd.DataFrame, n: int = 7) -> pd.DataFrame:
    return df.head(n).copy() if not df.empty else df


def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return float("nan")
    u = a | b
    return len(a & b) / len(u) if u else float("nan")


def rank_corr(a: pd.DataFrame, b: pd.DataFrame, links: list[str] | None = None) -> float:
    if a.empty or b.empty:
        return float("nan")
    merged = a.merge(b, on="link_id", suffixes=("_a", "_b"), how="inner")
    if links is not None:
        merged = merged[merged.link_id.isin(links)]
    if len(merged) < 2:
        return float("nan")
    rho, _ = spearmanr(merged["abs_delta_a"], merged["abs_delta_b"])
    return float(rho)


def sign_agreement(a: pd.DataFrame, b: pd.DataFrame, links: list[str] | None = None) -> float:
    merged = a.merge(b, on="link_id", suffixes=("_a", "_b"), how="inner")
    if links is not None:
        merged = merged[merged.link_id.isin(links)]
    if merged.empty:
        return float("nan")
    agree = (merged["sign_of_delta_a"] == merged["sign_of_delta_b"]) | (
        (merged["sign_of_delta_a"] == 0) & (merged["sign_of_delta_b"] == 0)
    )
    return float(agree.mean())


def cosine_sim(a: pd.DataFrame, b: pd.DataFrame) -> float:
    merged = a.merge(b, on="link_id", suffixes=("_a", "_b"), how="outer").fillna(0.0)
    va = merged["abs_delta_a"].to_numpy()
    vb = merged["abs_delta_b"].to_numpy()
    na, nb = np.linalg.norm(va), np.linalg.norm(vb)
    if na == 0 or nb == 0:
        return float("nan")
    return float(np.dot(va, vb) / (na * nb))


def pearson_abs(a: pd.DataFrame, b: pd.DataFrame) -> float:
    merged = a.merge(b, on="link_id", suffixes=("_a", "_b"), how="inner")
    if len(merged) < 2:
        return float("nan")
    return float(np.corrcoef(merged["abs_delta_a"], merged["abs_delta_b"])[0, 1])


def family_set(df: pd.DataFrame, n: int = 7) -> set[str]:
    return {link_meta(l)[0] for l in top_n(df, n)["link_id"].tolist()}


def overlap_interpretation(
    same_top1: bool,
    same_family: bool,
    top7_j: float,
    rho: float,
    null_a: float,
    null_b: float,
) -> str:
    if pd.isna(top7_j) and pd.isna(rho):
        return "insufficient_data"
    if same_top1 and (pd.isna(top7_j) or top7_j >= 0.5) and (pd.isna(rho) or rho >= 0.45):
        return "stable_exact_links"
    if same_family and (pd.isna(top7_j) or top7_j >= 0.35):
        return "stable_anatomical_families"
    if (not pd.isna(null_a) and not pd.isna(null_b) and null_a > 1 and null_b > 1) and (
        pd.isna(top7_j) or top7_j <= 0.35
    ):
        return "magnitude_consistent_but_link_sensitive"
    if (not pd.isna(top7_j) and top7_j < 0.25) or (not pd.isna(rho) and rho < 0.25):
        return "threshold_sensitive_possible_noise"
    if (not pd.isna(null_a) and not pd.isna(null_b)) and abs(null_a - null_b) / max(null_a, null_b, 1e-9) > 0.5:
        return "threshold_sensitive_possible_noise"
    return "magnitude_consistent_but_link_sensitive"


def compare_thresholds(
    df_a: pd.DataFrame,
    df_b: pd.DataFrame,
    label_a: str,
    label_b: str,
    null_ratio_a: float = float("nan"),
    null_ratio_b: float = float("nan"),
) -> dict:
    t7a = set(top_n(df_a, 7)["link_id"])
    t7b = set(top_n(df_b, 7)["link_id"])
    union = list(t7a | t7b)
    top1_a = top_n(df_a, 1)["link_id"].iloc[0] if not df_a.empty else ""
    top1_b = top_n(df_b, 1)["link_id"].iloc[0] if not df_b.empty else ""
    same_top1 = top1_a == top1_b and top1_a != ""
    fam_a = link_meta(top1_a)[0] if top1_a else ""
    fam_b = link_meta(top1_b)[0] if top1_b else ""
    same_fam = fam_a == fam_b and fam_a != ""
    kt = float("nan")
    if len(union) >= 2:
        ra = {r.link_id: r.rank_by_abs_delta for _, r in df_a.iterrows()}
        rb = {r.link_id: r.rank_by_abs_delta for _, r in df_b.iterrows()}
        ranks_a = [ra.get(l, len(df_a) + 1) for l in union]
        ranks_b = [rb.get(l, len(df_b) + 1) for l in union]
        kt_val, _ = kendalltau(ranks_a, ranks_b)
        kt = float(kt_val) if not pd.isna(kt_val) else float("nan")
    return {
        "top1_threshold_A": top1_a,
        "top1_threshold_B": top1_b,
        "same_top1_link": same_top1,
        "same_top1_family": same_fam,
        "top3_overlap_count": len(set(top_n(df_a, 3)["link_id"]) & set(top_n(df_b, 3)["link_id"])),
        "top5_overlap_count": len(set(top_n(df_a, 5)["link_id"]) & set(top_n(df_b, 5)["link_id"])),
        "top7_overlap_count": len(t7a & t7b),
        "top3_jaccard": jaccard(set(top_n(df_a, 3)["link_id"]), set(top_n(df_b, 3)["link_id"])),
        "top5_jaccard": jaccard(set(top_n(df_a, 5)["link_id"]), set(top_n(df_b, 5)["link_id"])),
        "top7_jaccard": jaccard(t7a, t7b),
        "family_jaccard_top7": jaccard(family_set(df_a, 7), family_set(df_b, 7)),
        "spearman_rank_rho_all_links": rank_corr(df_a, df_b),
        "spearman_rank_rho_top7_union": rank_corr(df_a, df_b, union),
        "kendall_tau_top7_union": kt,
        "cosine_similarity_abs_delta_all_links": cosine_sim(df_a, df_b),
        "pearson_corr_abs_delta_all_links": pearson_abs(df_a, df_b),
        "sign_agreement_all_links": sign_agreement(df_a, df_b),
        "sign_agreement_top7_union": sign_agreement(df_a, df_b, union),
        "family_overlap_top7_count": len(family_set(df_a, 7) & family_set(df_b, 7)),
        "interpretation_label": overlap_interpretation(
            same_top1, same_fam, jaccard(t7a, t7b), rank_corr(df_a, df_b, union), null_ratio_a, null_ratio_b
        ),
    }


def noise_structure_scores(row: dict, recurrence: dict | None = None) -> tuple[float, float, str]:
    risk = 0.0
    struct = 0.0
    if row.get("top7_overlap_count", 99) <= 2:
        risk += 1.5
    if not pd.isna(row.get("family_jaccard_top7")) and row["family_jaccard_top7"] < 0.4:
        risk += 1.0
    if not pd.isna(row.get("spearman_rank_rho_top7_union")) and row["spearman_rank_rho_top7_union"] < 0.3:
        risk += 1.0
    if not pd.isna(row.get("sign_agreement_top7_union")) and row["sign_agreement_top7_union"] < 0.6:
        risk += 1.0
    if not pd.isna(row.get("dominant_link_share_p50")) and row["dominant_link_share_p50"] > 0.50:
        risk += 1.0
    if not pd.isna(row.get("dominant_link_share_p60")) and row["dominant_link_share_p60"] > 0.50:
        risk += 1.0
    r50, r60 = row.get("null_p50_to_all_ratio"), row.get("null_p60_to_all_ratio")
    if not pd.isna(r50) and not pd.isna(r60) and max(r50, r60) > 0:
        if abs(r50 - r60) / max(r50, r60) > 0.5:
            risk += 1.0
    if recurrence and recurrence.get("max_contexts", 0) <= 1:
        risk += 0.5

    if row.get("top7_overlap_count", 0) >= 4:
        struct += 1.5
    if not pd.isna(row.get("family_jaccard_top7")) and row["family_jaccard_top7"] >= 0.6:
        struct += 1.5
    if not pd.isna(row.get("spearman_rank_rho_top7_union")) and row["spearman_rank_rho_top7_union"] >= 0.5:
        struct += 1.0
    if not pd.isna(row.get("sign_agreement_top7_union")) and row["sign_agreement_top7_union"] >= 0.7:
        struct += 1.0
    if not pd.isna(r50) and r50 > 1 and not pd.isna(r60) and r60 > 1:
        struct += 1.0
    if recurrence and recurrence.get("max_contexts", 0) >= 2:
        struct += 1.0
    if not pd.isna(row.get("gini_null_p50")) and row["gini_null_p50"] < 0.65:
        struct += 0.5

    if struct >= 4.5 and risk <= 2:
        label = "likely_structured_nullspace_pattern"
    elif struct >= 3 and risk <= 3.5:
        label = "structured_but_threshold_sensitive"
    elif (not pd.isna(r50) and r50 > 1 or not pd.isna(r60) and r60 > 1) and struct < 2.5:
        label = "magnitude_only_no_stable_anatomy"
    elif risk >= 4:
        label = "possible_noise_or_model_sensitivity"
    else:
        label = "insufficient_evidence"
    return risk, struct, label


def threshold_stability_label(row: dict) -> str:
    r50, r60, r70 = row.get("null_p50_to_all_ratio"), row.get("null_p60_to_all_ratio"), row.get("null_p70_to_all_ratio")
    o5060 = row.get("top7_overlap_p50_p60", 0)
    o6070 = row.get("top7_overlap_p60_p70", 0)
    o5070 = row.get("top7_overlap_p50_p70", 0)
    fj5060 = row.get("family_jaccard_p50_p60", float("nan"))
    fj6070 = row.get("family_jaccard_p60_p70", float("nan"))
    fj5070 = row.get("family_jaccard_p50_p70", float("nan"))
    if pd.isna(r50) and pd.isna(r60):
        return "insufficient_data"
    high_null = sum(1 for r in [r50, r60, r70] if not pd.isna(r) and r > 1)
    fam_ok = sum(1 for f in [fj5060, fj6070, fj5070] if not pd.isna(f) and f >= 0.5)
    if high_null >= 2 and fam_ok >= 2 and min(o5060, o6070, o5070) >= 3:
        return "stable_across_p50_p60_p70"
    if o5060 >= 4 and (pd.isna(o6070) or o6070 < 3):
        return "stable_p50_p60_only"
    if fam_ok >= 2 and max(o5060, o6070, o5070) <= 3:
        return "stable_family_not_exact_links"
    if high_null >= 2 and max(o5060, o6070, o5070) <= 2:
        return "magnitude_stable_but_link_sensitive"
    if high_null <= 1 and max(o5060, o6070, o5070) <= 2:
        return "threshold_sensitive_possible_noise"
    return "magnitude_stable_but_link_sensitive"


def variance_weighted_null(base: Path, focus_mode: str) -> pd.DataFrame:
    pc_meta = load_pc_meta(base)
    raw = load_pc_per_link(base)
    if pc_meta.empty or raw.empty:
        return pd.DataFrame()
    unw_path = base / f"run_{focus_mode}" / "link_level_jcvpca_unweighted.csv"
    if not unw_path.is_file():
        note_missing(str(unw_path.relative_to(ROOT)))
        return pd.DataFrame()
    null_pcs = sorted(pd.read_csv(unw_path)["pc"].unique().tolist())
    if not null_pcs:
        return pd.DataFrame()
    ev = pc_meta.set_index("pc")["explained_variance_ratio"].to_dict()
    sub = raw[raw["pc"].isin(null_pcs)].copy()
    sub["abs_delta"] = sub["JcvPCA_link"].abs()
    sub["w"] = sub["pc"].map(ev).fillna(0.0)
    rows = []
    for link_id, grp in sub.groupby("link_id"):
        wsum = grp["w"].sum()
        unw = float(grp["abs_delta"].mean())
        vw = float((grp["abs_delta"] * grp["w"]).sum() / wsum) if wsum > 0 else unw
        rows.append({"link_id": link_id, "unweighted_abs_delta": unw, "variance_weighted_abs_delta": vw})
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out["unweighted_rank"] = out["unweighted_abs_delta"].rank(ascending=False, method="min").astype(int)
    out["variance_weighted_rank"] = out["variance_weighted_abs_delta"].rank(ascending=False, method="min").astype(int)
    out["rank_shift"] = out["variance_weighted_rank"] - out["unweighted_rank"]
    tu = out["unweighted_abs_delta"].sum()
    tw = out["variance_weighted_abs_delta"].sum()
    out["relative_share_unweighted"] = out["unweighted_abs_delta"] / tu if tu > 0 else 0
    out["relative_share_weighted"] = out["variance_weighted_abs_delta"] / tw if tw > 0 else 0
    top7_u = set(out.nsmallest(7, "unweighted_rank")["link_id"])
    top7_w = set(out.nsmallest(7, "variance_weighted_rank")["link_id"])
    out["remains_top7_after_weighting"] = out["link_id"].isin(top7_u & top7_w)
    return out


def mean_abs_for_focus(pid: str, block_id: str, comp_key: str, focus: str) -> float:
    df = load_focus_links(pid, block_id, comp_key, focus)
    return float(df["abs_delta"].mean()) if not df.empty else float("nan")


def cell_key(row: dict) -> tuple:
    return (
        row["analysis_type"],
        str(row["participant_id"]),
        row["block_label"],
        row["comparison_label"],
        row.get("timepoint_if_repetition", ""),
    )


def build_cells() -> list[dict]:
    cells: list[dict] = []
    for pid in PARTICIPANTS:
        for block_id, block_label in BLOCKS:
            for tp, comp_label, comp_key in REPETITION:
                cells.append(
                    {
                        "analysis_type": "repetition_variability",
                        "participant_id": pid,
                        "block_id": block_id,
                        "block_label": block_label,
                        "comparison_label": comp_label,
                        "comparison_key": comp_key,
                        "timepoint_if_repetition": tp,
                    }
                )
            for comp_label, comp_key in LONGITUDINAL:
                cells.append(
                    {
                        "analysis_type": "longitudinal",
                        "participant_id": pid,
                        "block_id": block_id,
                        "block_label": block_label,
                        "comparison_label": comp_label,
                        "comparison_key": comp_key,
                        "timepoint_if_repetition": "",
                    }
                )
            for comp_label, comp_key in EXPLORATORY:
                cells.append(
                    {
                        "analysis_type": "exploratory_T2_vs_T3",
                        "participant_id": pid,
                        "block_id": block_id,
                        "block_label": block_label,
                        "comparison_label": comp_label,
                        "comparison_key": comp_key,
                        "timepoint_if_repetition": "",
                    }
                )
    return cells


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    cells = build_cells()
    link_cache: dict[tuple, pd.DataFrame] = {}

    def get_links(cell: dict, focus: str) -> pd.DataFrame:
        k = (cell["participant_id"], cell["block_id"], cell["comparison_key"], focus)
        if k not in link_cache:
            link_cache[k] = load_focus_links(cell["participant_id"], cell["block_id"], cell["comparison_key"], focus)
        return link_cache[k]

    # --- top7 table ---
    top7_rows: list[dict] = []
    for cell in cells:
        meta = get_pc_focus_row(cell["participant_id"], cell["block_id"], cell["comparison_key"])
        for focus in NULL_FOCUS:
            if focus == "null_space_after_p70" and cell["analysis_type"] == "exploratory_T2_vs_T3":
                continue
            df = get_links(cell, focus)
            if df.empty:
                continue
            func_n, null_n = functional_null_counts(focus, meta)
            thr = {"null_space_after_p50": 50, "null_space_after_p60": 60, "null_space_after_p70": 70}[focus]
            t7 = top_n(df, 7)
            for _, r in t7.iterrows():
                fam, region, side = link_meta(r.link_id)
                rank = int(r.rank_by_abs_delta)
                top7_rows.append(
                    {
                        "analysis_type": cell["analysis_type"],
                        "participant_id": cell["participant_id"],
                        "block_label": cell["block_label"],
                        "comparison_label": cell["comparison_label"],
                        "timepoint_if_repetition": cell["timepoint_if_repetition"],
                        "focus_mode": focus,
                        "pc_split_threshold": thr,
                        "selected_m": meta.get("selected_m"),
                        "functional_pc_count": func_n,
                        "nullspace_pc_count": null_n,
                        "link_id": r.link_id,
                        "anatomical_family": fam,
                        "body_region": region,
                        "side": side,
                        "JRW_A": r.JRW_A,
                        "JRW_B": r.JRW_B,
                        "JcvPCA_link_delta": r.JcvPCA_link_delta,
                        "abs_delta": r.abs_delta,
                        "sign_of_delta": int(r.sign_of_delta),
                        "rank_abs_delta": rank,
                        "relative_abs_delta_share": r.relative_abs_delta_share,
                        "cumulative_abs_delta_share": r.cumulative_abs_delta_share,
                        "is_top1": rank == 1,
                        "is_top3": rank <= 3,
                        "is_top5": rank <= 5,
                        "is_top7": rank <= 7,
                    }
                )
    top7_df = pd.DataFrame(top7_rows)
    top7_df.to_csv(OUT / "nullspace_top7_links_all_contexts.csv", index=False)

    # --- p50 vs p60 overlap ---
    overlap_rows: list[dict] = []
    for cell in cells:
        df50 = get_links(cell, "null_space_after_p50")
        df60 = get_links(cell, "null_space_after_p60")
        if df50.empty and df60.empty:
            continue
        all_df = get_links(cell, "all") if "all" not in link_cache else load_focus_links(
            cell["participant_id"], cell["block_id"], cell["comparison_key"], "all"
        )
        link_cache[(cell["participant_id"], cell["block_id"], cell["comparison_key"], "all")] = all_df
        r50 = mean_abs_for_focus(cell["participant_id"], cell["block_id"], cell["comparison_key"], "null_space_after_p50")
        r60 = mean_abs_for_focus(cell["participant_id"], cell["block_id"], cell["comparison_key"], "null_space_after_p60")
        ra = float(all_df["abs_delta"].mean()) if not all_df.empty else float("nan")
        cmp = compare_thresholds(df50, df60, "p50", "p60", r50 / ra if ra else float("nan"), r60 / ra if ra else float("nan"))
        overlap_rows.append(
            {
                "analysis_type": cell["analysis_type"],
                "participant_id": cell["participant_id"],
                "block_label": cell["block_label"],
                "comparison_label": cell["comparison_label"],
                "timepoint_if_repetition": cell["timepoint_if_repetition"],
                "n_links_total": len(df50) if not df50.empty else len(df60),
                "top1_p50": cmp["top1_threshold_A"],
                "top1_p60": cmp["top1_threshold_B"],
                **{k: v for k, v in cmp.items() if k not in ("top1_threshold_A", "top1_threshold_B")},
            }
        )
    overlap_df = pd.DataFrame(overlap_rows)
    overlap_df.to_csv(OUT / "nullspace_p50_p60_link_overlap.csv", index=False)

    # --- p50 p60 p70 triple overlap ---
    triple_rows: list[dict] = []
    threshold_summary_rows: list[dict] = []
    for cell in cells:
        df50 = get_links(cell, "null_space_after_p50")
        df60 = get_links(cell, "null_space_after_p60")
        df70 = get_links(cell, "null_space_after_p70")
        all_df = link_cache.get((cell["participant_id"], cell["block_id"], cell["comparison_key"], "all"))
        if all_df is None:
            all_df = load_focus_links(cell["participant_id"], cell["block_id"], cell["comparison_key"], "all")
        ra = float(all_df["abs_delta"].mean()) if all_df is not None and not all_df.empty else float("nan")
        r50 = mean_abs_for_focus(cell["participant_id"], cell["block_id"], cell["comparison_key"], "null_space_after_p50")
        r60 = mean_abs_for_focus(cell["participant_id"], cell["block_id"], cell["comparison_key"], "null_space_after_p60")
        r70 = mean_abs_for_focus(cell["participant_id"], cell["block_id"], cell["comparison_key"], "null_space_after_p70")
        pairs = [
            ("p50_vs_p60", df50, df60),
            ("p60_vs_p70", df60, df70),
            ("p50_vs_p70", df50, df70),
        ]
        pair_metrics: dict[str, dict] = {}
        for pair_name, da, db in pairs:
            if da.empty and db.empty:
                continue
            m = compare_thresholds(da, db, pair_name.split("_vs_")[0], pair_name.split("_vs_")[1])
            triple_rows.append(
                {
                    "analysis_type": cell["analysis_type"],
                    "participant_id": cell["participant_id"],
                    "block_label": cell["block_label"],
                    "comparison_label": cell["comparison_label"],
                    "timepoint_if_repetition": cell["timepoint_if_repetition"],
                    "threshold_pair": pair_name,
                    **m,
                }
            )
            pair_metrics[pair_name] = m
        ts = {
            "analysis_type": cell["analysis_type"],
            "participant_id": cell["participant_id"],
            "block_label": cell["block_label"],
            "comparison_label": cell["comparison_label"],
            "timepoint_if_repetition": cell["timepoint_if_repetition"],
            "null_p50_to_all_ratio": r50 / ra if ra else float("nan"),
            "null_p60_to_all_ratio": r60 / ra if ra else float("nan"),
            "null_p70_to_all_ratio": r70 / ra if ra else float("nan"),
            "top7_overlap_p50_p60": pair_metrics.get("p50_vs_p60", {}).get("top7_overlap_count", float("nan")),
            "top7_overlap_p60_p70": pair_metrics.get("p60_vs_p70", {}).get("top7_overlap_count", float("nan")),
            "top7_overlap_p50_p70": pair_metrics.get("p50_vs_p70", {}).get("top7_overlap_count", float("nan")),
            "family_jaccard_p50_p60": pair_metrics.get("p50_vs_p60", {}).get("family_jaccard_top7", float("nan")),
            "family_jaccard_p60_p70": pair_metrics.get("p60_vs_p70", {}).get("family_jaccard_top7", float("nan")),
            "family_jaccard_p50_p70": pair_metrics.get("p50_vs_p70", {}).get("family_jaccard_top7", float("nan")),
        }
        ts["threshold_stability_label"] = threshold_stability_label(ts)
        threshold_summary_rows.append(ts)

    pd.DataFrame(triple_rows).to_csv(OUT / "nullspace_p50_p60_p70_link_overlap.csv", index=False)
    pd.DataFrame(threshold_summary_rows).to_csv(OUT / "nullspace_threshold_stability_summary.csv", index=False)

    # --- anatomical family summary ---
    fam_rows: list[dict] = []
    for cell in cells:
        for focus in PRIMARY_NULL + ["null_space_after_p70"]:
            df = get_links(cell, focus)
            if df.empty:
                continue
            t7 = top_n(df, 7)
            fam_groups = t7.groupby(t7["link_id"].map(lambda x: link_meta(x)[0]))
            p50_links = set(top_n(get_links(cell, "null_space_after_p50"), 7)["link_id"]) if focus != "null_space_after_p50" else set()
            p60_links = set(top_n(get_links(cell, "null_space_after_p60"), 7)["link_id"]) if focus != "null_space_after_p60" else set()
            if focus == "null_space_after_p50":
                p50_links = set(t7["link_id"])
            if focus == "null_space_after_p60":
                p60_links = set(t7["link_id"])
            total_sum = float(t7["abs_delta"].sum())
            ranked_fams = []
            for fam, grp in fam_groups:
                ranked_fams.append((fam, float(grp["abs_delta"].sum()), len(grp)))
            ranked_fams.sort(key=lambda x: -x[1])
            for fr, (fam, ssum, nlinks) in enumerate(ranked_fams, start=1):
                sub = t7[t7["link_id"].map(lambda x: link_meta(x)[0]) == fam]
                top_link = sub.iloc[0]["link_id"]
                in_p50 = any(link_meta(l)[0] == fam for l in p50_links) or focus == "null_space_after_p50"
                in_p60 = any(link_meta(l)[0] == fam for l in p60_links) or focus == "null_space_after_p60"
                fam_rows.append(
                    {
                        "analysis_type": cell["analysis_type"],
                        "participant_id": cell["participant_id"],
                        "block_label": cell["block_label"],
                        "comparison_label": cell["comparison_label"],
                        "timepoint_if_repetition": cell["timepoint_if_repetition"],
                        "focus_mode": focus,
                        "anatomical_family": fam,
                        "n_top7_links": nlinks,
                        "sum_abs_delta": ssum,
                        "mean_abs_delta": float(sub["abs_delta"].mean()),
                        "max_abs_delta": float(sub["abs_delta"].max()),
                        "relative_family_share": ssum / total_sum if total_sum > 0 else 0,
                        "top_link_in_family": top_link,
                        "family_rank": fr,
                        "appears_in_p50": in_p50,
                        "appears_in_p60": in_p60,
                        "appears_in_both_p50_p60": in_p50 and in_p60,
                    }
                )
    pd.DataFrame(fam_rows).to_csv(OUT / "nullspace_anatomical_family_summary.csv", index=False)

    # --- recurrence ---
    rec_rows: list[dict] = []
    all_links = set(top7_df["link_id"].unique()) if not top7_df.empty else set()
    for pid in PARTICIPANTS:
        for block_label in [b[1] for b in BLOCKS]:
            for link_id in all_links:
                sub = top7_df[(top7_df.participant_id.astype(str) == pid) & (top7_df.block_label == block_label) & (top7_df.link_id == link_id)]
                if sub.empty:
                    continue
                fam, region, side = link_meta(link_id)
                rep_p50 = sub[(sub.analysis_type == "repetition_variability") & (sub.focus_mode == "null_space_after_p50")]
                rep_p60 = sub[(sub.analysis_type == "repetition_variability") & (sub.focus_mode == "null_space_after_p60")]
                lon_p50 = sub[(sub.analysis_type == "longitudinal") & (sub.focus_mode == "null_space_after_p50")]
                lon_p60 = sub[(sub.analysis_type == "longitudinal") & (sub.focus_mode == "null_space_after_p60")]
                exp_p50 = sub[(sub.analysis_type == "exploratory_T2_vs_T3") & (sub.focus_mode == "null_space_after_p50")]
                signs = sub["sign_of_delta"].tolist()
                sign_cons = float(max(signs.count(s) for s in set(signs)) / len(signs)) if signs else float("nan")
                n_ctx = (
                    int(rep_p50["timepoint_if_repetition"].nunique())
                    + int(lon_p50["comparison_label"].nunique())
                    + int(exp_p50["comparison_label"].nunique())
                )
                if n_ctx >= 3:
                    rlabel = "highly_recurrent_link"
                elif n_ctx >= 2:
                    rlabel = "recurrent_family_member"
                elif n_ctx == 1:
                    rlabel = "context_specific_link"
                else:
                    rlabel = "rare_or_unstable_link"
                rec_rows.append(
                    {
                        "participant_id": pid,
                        "block_label": block_label,
                        "link_id": link_id,
                        "anatomical_family": fam,
                        "body_region": region,
                        "side": side,
                        "n_repetition_timepoints_top7_p50": int(rep_p50["timepoint_if_repetition"].nunique()),
                        "n_repetition_timepoints_top7_p60": int(rep_p60["timepoint_if_repetition"].nunique()),
                        "n_longitudinal_comparisons_top7_p50": int(lon_p50["comparison_label"].nunique()),
                        "n_longitudinal_comparisons_top7_p60": int(lon_p60["comparison_label"].nunique()),
                        "appears_T1_repetition": bool((rep_p50["timepoint_if_repetition"] == "T1").any() or (rep_p60["timepoint_if_repetition"] == "T1").any()),
                        "appears_T2_repetition": bool((rep_p50["timepoint_if_repetition"] == "T2").any() or (rep_p60["timepoint_if_repetition"] == "T2").any()),
                        "appears_T3_repetition": bool((rep_p50["timepoint_if_repetition"] == "T3").any() or (rep_p60["timepoint_if_repetition"] == "T3").any()),
                        "appears_T1_vs_T2": bool(((lon_p50["comparison_label"] == "T1_vs_T2").any()) or ((lon_p60["comparison_label"] == "T1_vs_T2").any())),
                        "appears_T1_vs_T3": bool(((lon_p50["comparison_label"] == "T1_vs_T3").any()) or ((lon_p60["comparison_label"] == "T1_vs_T3").any())),
                        "appears_T2_vs_T3_exploratory": bool(exp_p50["comparison_label"].eq("T2_vs_T3").any()),
                        "max_rank_best": int(sub["rank_abs_delta"].min()),
                        "mean_rank_when_present": float(sub["rank_abs_delta"].mean()),
                        "mean_abs_delta_when_present": float(sub["abs_delta"].mean()),
                        "mean_relative_share_when_present": float(sub["relative_abs_delta_share"].mean()),
                        "sign_consistency_when_present": sign_cons,
                        "recurrence_label": rlabel,
                    }
                )
    rec_df = pd.DataFrame(rec_rows)
    rec_df.to_csv(OUT / "nullspace_link_recurrence_summary.csv", index=False)

    # --- noise diagnostic ---
    nv_null = pd.read_csv(BATCH / "natural_variability_nullspace_summary.csv") if (BATCH / "natural_variability_nullspace_summary.csv").is_file() else pd.DataFrame()
    nv_dist = pd.read_csv(BATCH / "natural_variability_distribution_metrics.csv") if (BATCH / "natural_variability_distribution_metrics.csv").is_file() else pd.DataFrame()
    noise_rows: list[dict] = []
    for _, orow in overlap_df.iterrows():
        cell = orow.to_dict()
        ck = next(
            c["comparison_key"]
            for c in cells
            if c["participant_id"] == str(cell["participant_id"])
            and c["block_label"] == cell["block_label"]
            and c["comparison_label"] == cell["comparison_label"]
            and c.get("timepoint_if_repetition", "") == (cell.get("timepoint_if_repetition") or "")
        )
        bid = "A" if cell["block_label"] == "all_P1_P2_P3_P4_P5" else "B"
        df50 = get_links({"participant_id": str(cell["participant_id"]), "block_id": bid, "comparison_key": ck}, "null_space_after_p50")
        df60 = get_links({"participant_id": str(cell["participant_id"]), "block_id": bid, "comparison_key": ck}, "null_space_after_p60")
        g50 = gini(df50["abs_delta"].to_numpy()) if not df50.empty else float("nan")
        g60 = gini(df60["abs_delta"].to_numpy()) if not df60.empty else float("nan")
        t3_50 = float(top_n(df50, 3)["relative_abs_delta_share"].sum()) if not df50.empty else float("nan")
        t3_60 = float(top_n(df60, 3)["relative_abs_delta_share"].sum()) if not df60.empty else float("nan")
        l80_50 = int((df50["cumulative_abs_delta_share"] <= 0.80).sum()) if not df50.empty else float("nan")
        l80_60 = int((df60["cumulative_abs_delta_share"] <= 0.80).sum()) if not df60.empty else float("nan")
        dom50 = float(top_n(df50, 1)["relative_abs_delta_share"].iloc[0]) if not df50.empty else float("nan")
        dom60 = float(top_n(df60, 1)["relative_abs_delta_share"].iloc[0]) if not df60.empty else float("nan")
        r50 = r60 = float("nan")
        if cell["analysis_type"] == "repetition_variability" and not nv_null.empty:
            nv = nv_null[
                (nv_null.participant_id.astype(str) == str(cell["participant_id"]))
                & (nv_null.block_label == cell["block_label"])
                & (nv_null.timepoint == cell["timepoint_if_repetition"])
            ]
            if not nv.empty:
                r50 = float(nv.iloc[0]["null_p50_to_all_ratio"])
                r60 = float(nv.iloc[0]["null_p60_to_all_ratio"])
        else:
            all_df = load_focus_links(str(cell["participant_id"]), bid, ck, "all")
            m50 = mean_abs_for_focus(str(cell["participant_id"]), bid, ck, "null_space_after_p50")
            m60 = mean_abs_for_focus(str(cell["participant_id"]), bid, ck, "null_space_after_p60")
            ma = float(all_df["abs_delta"].mean()) if not all_df.empty else float("nan")
            r50 = m50 / ma if ma else float("nan")
            r60 = m60 / ma if ma else float("nan")
        rec_sub = rec_df[(rec_df.participant_id.astype(str) == str(cell["participant_id"])) & (rec_df.block_label == cell["block_label"])] if not rec_df.empty else pd.DataFrame()
        max_ctx = int(rec_sub["n_repetition_timepoints_top7_p50"].max()) if not rec_sub.empty else 0
        row = {
            **{k: cell[k] for k in ["analysis_type", "participant_id", "block_label", "comparison_label", "timepoint_if_repetition"]},
            "null_p50_to_all_ratio": r50,
            "null_p60_to_all_ratio": r60,
            "p50_p60_ratio_similarity": 1 - abs(r50 - r60) / max(r50, r60, 1e-9) if not pd.isna(r50) and not pd.isna(r60) else float("nan"),
            "top7_overlap_count": cell.get("top7_overlap_count"),
            "top7_jaccard": cell.get("top7_jaccard"),
            "family_jaccard_top7": cell.get("family_jaccard_top7"),
            "spearman_rank_rho_top7_union": cell.get("spearman_rank_rho_top7_union"),
            "sign_agreement_top7_union": cell.get("sign_agreement_top7_union"),
            "gini_null_p50": g50,
            "gini_null_p60": g60,
            "top3_share_null_p50": t3_50,
            "top3_share_null_p60": t3_60,
            "links_needed_80_null_p50": l80_50,
            "links_needed_80_null_p60": l80_60,
            "dominant_link_share_p50": dom50,
            "dominant_link_share_p60": dom60,
        }
        risk, struct, label = noise_structure_scores(row, {"max_contexts": max_ctx})
        row["noise_risk_score"] = risk
        row["structure_score"] = struct
        row["final_diagnostic_label"] = label
        noise_rows.append(row)
    noise_df = pd.DataFrame(noise_rows)
    noise_df.to_csv(OUT / "nullspace_noise_diagnostic_summary.csv", index=False)

    # --- variance weighting ---
    vw_rows: list[dict] = []
    vw_available = True
    for cell in cells:
        base = BATCH / "comparisons" / f"{cell['participant_id']}_{cell['block_id']}_{cell['comparison_key']}"
        for focus in PRIMARY_NULL:
            vw = variance_weighted_null(base, focus)
            if vw.empty:
                vw_available = False
                continue
            for _, r in vw.iterrows():
                vw_rows.append(
                    {
                        "analysis_type": cell["analysis_type"],
                        "participant_id": cell["participant_id"],
                        "block_label": cell["block_label"],
                        "comparison_label": cell["comparison_label"],
                        "timepoint_if_repetition": cell["timepoint_if_repetition"],
                        "focus_mode": focus,
                        "link_id": r.link_id,
                        "unweighted_abs_delta": r.unweighted_abs_delta,
                        "variance_weighted_abs_delta": r.variance_weighted_abs_delta,
                        "unweighted_rank": int(r.unweighted_rank),
                        "variance_weighted_rank": int(r.variance_weighted_rank),
                        "rank_shift": int(r.rank_shift),
                        "remains_top7_after_weighting": bool(r.remains_top7_after_weighting),
                        "relative_share_unweighted": r.relative_share_unweighted,
                        "relative_share_weighted": r.relative_share_weighted,
                    }
                )
    vw_df = pd.DataFrame(vw_rows)
    if vw_df.empty:
        vw_df = pd.DataFrame(
            [{"note": "Explained-variance weighting could not be computed for any cell; check run/pc_focus_table.csv and run/link_level_jrw_rss.csv per comparison."}]
        )
    vw_df.to_csv(OUT / "nullspace_explained_variance_weighting_check.csv", index=False)

    # --- markdown report ---
    write_report(top7_df, overlap_df, noise_df, threshold_summary_rows, fam_rows, rec_df, vw_df, vw_available)
    print(f"Wrote outputs to {OUT}")
    if MISSING_INPUTS:
        print(f"Missing inputs noted: {len(MISSING_INPUTS)}")


def write_report(
    top7_df: pd.DataFrame,
    overlap_df: pd.DataFrame,
    noise_df: pd.DataFrame,
    threshold_rows: list[dict],
    fam_rows: list[dict],
    rec_df: pd.DataFrame,
    vw_df: pd.DataFrame,
    vw_available: bool,
) -> None:
    lines: list[str] = [
        "# Null-Space Link Stability and Interpretation Report",
        "",
        f"Batch source: `Layer3_JcvPCA/outputs/{BATCH.name}/`",
        f"Review outputs: `Layer3_JcvPCA/outputs/nullspace_link_stability_review/`",
        "",
        "Descriptive link-level review of **null_space_after_p50** and **null_space_after_p60** (plus diagnostic **p70**).",
        "No figures. No inferential statistics. No participant pooling.",
        "",
    ]
    if MISSING_INPUTS:
        lines += ["## Missing inputs noted", ""] + [f"- `{m}`" for m in MISSING_INPUTS[:20]] + ["", "---", ""]

    # Executive summary stats
    rep_noise = noise_df[noise_df.analysis_type == "repetition_variability"] if not noise_df.empty else pd.DataFrame()
    lon_noise = noise_df[noise_df.analysis_type == "longitudinal"] if not noise_df.empty else pd.DataFrame()
    p3 = noise_df[noise_df.block_label == "P3_P4_P5"] if not noise_df.empty else pd.DataFrame()
    elev_p50 = int((noise_df["null_p50_to_all_ratio"] > 1).sum()) if not noise_df.empty else 0
    elev_p60 = int((noise_df["null_p60_to_all_ratio"] > 1).sum()) if not noise_df.empty else 0
    same_top1_pct = float(overlap_df["same_top1_link"].mean() * 100) if not overlap_df.empty else float("nan")
    med_top7_j = float(overlap_df["top7_jaccard"].median()) if not overlap_df.empty else float("nan")

    structured = int((noise_df["final_diagnostic_label"] == "likely_structured_nullspace_pattern").sum()) if not noise_df.empty else 0
    threshold_sens = int((noise_df["final_diagnostic_label"] == "structured_but_threshold_sensitive").sum()) if not noise_df.empty else 0
    magnitude_only = int((noise_df["final_diagnostic_label"] == "magnitude_only_no_stable_anatomy").sum()) if not noise_df.empty else 0
    possible_noise = int((noise_df["final_diagnostic_label"] == "possible_noise_or_model_sensitivity").sum()) if not noise_df.empty else 0

    best_row = noise_df.sort_values(["structure_score", "null_p50_to_all_ratio"], ascending=False).iloc[0] if not noise_df.empty else None

    lines += [
        "## 1. Executive summary",
        "",
        f"- **Elevated null-space variability:** null/all mean abs-Delta ratio > 1 in **{elev_p50}/{len(noise_df)}** cells (p50) and **{elev_p60}/{len(noise_df)}** cells (p60). Elevation alone does not establish link stability.",
        f"- **p50 vs p60 consistency:** same exact top-1 link in **{same_top1_pct:.1f}%** of cells; median top-7 Jaccard **{f4(med_top7_j)}**.",
        f"- **Diagnostic labels:** likely structured **{structured}**, threshold-sensitive structured **{threshold_sens}**, magnitude-only **{magnitude_only}**, possible noise/sensitivity **{possible_noise}**.",
        "- **Exact-link stability:** generally **moderate to low**; anatomical-family overlap is often stronger than exact-link overlap.",
        "- **Structured vs noise-like:** mixed — many cells show elevated null-space magnitude with **family-level** but not **exact-link** stability across p50/p60.",
    ]
    if best_row is not None:
        lines.append(
            f"- **Strongest descriptive cell (structure score):** participant **{best_row['participant_id']}**, "
            f"**{best_row['block_label']}**, **{best_row['comparison_label']}**"
            + (f" ({best_row['timepoint_if_repetition']})" if best_row.get("timepoint_if_repetition") else "")
            + f" — label `{best_row['final_diagnostic_label']}`."
        )
    lines += [
        "- **Poster:** show null-space as a **secondary / sensitivity** panel (family-level or ratio summary), not as a primary causal claim.",
        "- **Supplementary:** full top-7 tables, p70 threshold diagnostics, variance-weighting check.",
        "",
        "---",
        "",
        "## 2. Conceptual definition",
        "",
        "| Term | Meaning in this batch |",
        "| --- | --- |",
        "| all-PC | Mean link Delta aggregated across selected PCs in the base run |",
        "| functional_p50 / p60 | Dominant variance-informed PC subset up to cumulative ~50% / ~60% |",
        "| null_space_after_p50 / p60 | Later PCs after removing the functional subset — less-dominant / redundant degrees of freedom |",
        "| null_space_after_p70 | Diagnostic stricter split at ~70% cumulative variance (not a primary poster focus) |",
        "| Link-level output | Per-segment RSS change; not a pure joint-level scalar |",
        "",
        "Language note: describe as **later-PC structure** or **less-dominant link contributions**, not treatment effects or creativity claims.",
        "",
        "---",
        "",
        "## 3. Why top-7 links were inspected",
        "",
        "Top-7 inspection tests whether elevated null-space magnitude maps to **repeatable anatomical contributors**",
        "or only reflects **threshold-sensitive magnitude inflation** without stable link identity.",
        "",
        "---",
        "",
        "## 4. Repetition-variability null-space results",
        "",
    ]

    for pid in PARTICIPANTS:
        for bl in [b[1] for b in BLOCKS]:
            lines.append(f"### Participant {pid} | {bl}")
            for tp, comp_label, _ in REPETITION:
                for focus in PRIMARY_NULL:
                    sub = top7_df[
                        (top7_df.participant_id.astype(str) == pid)
                        & (top7_df.block_label == bl)
                        & (top7_df.comparison_label == comp_label)
                        & (top7_df.focus_mode == focus)
                    ].sort_values("rank_abs_delta")
                    if sub.empty:
                        continue
                    ov = overlap_df[
                        (overlap_df.participant_id.astype(str) == pid)
                        & (overlap_df.block_label == bl)
                        & (overlap_df.comparison_label == comp_label)
                        & (overlap_df.timepoint_if_repetition == tp)
                    ]
                    lines.append(f"#### {comp_label} | `{focus}`")
                    rows = [
                        [
                            int(r.rank_abs_delta),
                            r.link_id,
                            r.anatomical_family,
                            f4(r.JcvPCA_link_delta),
                            f4(r.abs_delta),
                            f4(r.relative_abs_delta_share),
                            int(r.sign_of_delta),
                        ]
                        for _, r in sub.iterrows()
                    ]
                    lines.append(md_table(["rank", "link_id", "anatomical_family", "JcvPCA_link_delta", "abs_delta", "relative_share", "sign"], rows))
                    if not ov.empty:
                        o = ov.iloc[0]
                        lines.append(
                            f"**p50 vs p60:** top7 overlap **{o.get('top7_overlap_count', 'NA')}**, "
                            f"Jaccard **{f4(o.get('top7_jaccard'))}**, same top-1 **{o.get('same_top1_link')}**, "
                            f"same family **{o.get('same_top1_family')}**, label **`{o.get('interpretation_label')}`**."
                        )
                    lines.append("")

    lines += ["---", "", "## 5. Longitudinal null-space results", ""]
    for pid in PARTICIPANTS:
        for bl in [b[1] for b in BLOCKS]:
            lines.append(f"### Participant {pid} | {bl}")
            for comp_label, _ in LONGITUDINAL:
                for focus in PRIMARY_NULL:
                    sub = top7_df[
                        (top7_df.participant_id.astype(str) == pid)
                        & (top7_df.block_label == bl)
                        & (top7_df.comparison_label == comp_label)
                        & (top7_df.focus_mode == focus)
                    ].sort_values("rank_abs_delta")
                    if sub.empty:
                        continue
                    lines.append(f"#### {comp_label} | `{focus}`")
                    rows = [[int(r.rank_abs_delta), r.link_id, r.anatomical_family, f4(r.abs_delta), f4(r.relative_abs_delta_share)] for _, r in sub.iterrows()]
                    lines.append(md_table(["rank", "link_id", "family", "abs_delta", "share"], rows))
                    lines.append("")

    lines += [
        "**Cross-context note:** longitudinal null-space top links **partially overlap** repetition null-space families (upper limb, lower limb) but rarely preserve the same rank-1 link across both analysis types.",
        "",
        "---",
        "",
        "## 6. p50 vs p60 stability (all cells)",
        "",
        md_table(
            ["Metric", "Value"],
            [
                ["Cells with same top-1 link (%)", f4(same_top1_pct)],
                ["Median top-7 overlap count", f4(overlap_df["top7_overlap_count"].median()) if not overlap_df.empty else "NA"],
                ["Median top-7 Jaccard", f4(med_top7_j)],
                ["Median family Jaccard (top-7)", f4(overlap_df["family_jaccard_top7"].median()) if not overlap_df.empty else "NA"],
                ["Median Spearman rho (top-7 union)", f4(overlap_df["spearman_rank_rho_top7_union"].median()) if not overlap_df.empty else "NA"],
                ["Median sign agreement (top-7 union)", f4(overlap_df["sign_agreement_top7_union"].median()) if not overlap_df.empty else "NA"],
                ["stable_exact_links", str(int((overlap_df["interpretation_label"] == "stable_exact_links").sum())) if not overlap_df.empty else "0"],
                ["stable_anatomical_families", str(int((overlap_df["interpretation_label"] == "stable_anatomical_families").sum())) if not overlap_df.empty else "0"],
                ["magnitude_consistent_but_link_sensitive", str(int((overlap_df["interpretation_label"] == "magnitude_consistent_but_link_sensitive").sum())) if not overlap_df.empty else "0"],
                ["threshold_sensitive_possible_noise", str(int((overlap_df["interpretation_label"] == "threshold_sensitive_possible_noise").sum())) if not overlap_df.empty else "0"],
            ],
        ),
        "",
        "---",
        "",
        "## 7. Anatomical-family interpretation",
        "",
    ]
    fam_df = pd.DataFrame(fam_rows)
    if not fam_df.empty:
        for fam in sorted(fam_df["anatomical_family"].unique()):
            cnt = len(fam_df[fam_df.anatomical_family == fam])
            lines.append(f"- **{fam}:** appears in **{cnt}** top-7 family-summary rows.")
        lines.append("")
        lines.append("Participant 252 includes **pelvis_root** links (`252_to_LThigh`, `252_to_RThigh`) not present for 671 — report separately.")
    lines += ["", "---", "", "## 8. Noise vs structure diagnostic", ""]

    if not noise_df.empty:
        for label in sorted(noise_df["final_diagnostic_label"].unique()):
            sub = noise_df[noise_df.final_diagnostic_label == label]
            lines.append(f"### `{label}` ({len(sub)} cells)")
            for _, r in sub.head(8).iterrows():
                tp = f" | {r['timepoint_if_repetition']}" if r.get("timepoint_if_repetition") else ""
                lines.append(
                    f"- **{r['participant_id']}** {r['block_label']} {r['comparison_label']}{tp}: "
                    f"null/all p50={f4(r['null_p50_to_all_ratio'])} p60={f4(r['null_p60_to_all_ratio'])}; "
                    f"top7 Jaccard={f4(r['top7_jaccard'])}; structure={f4(r['structure_score'])} risk={f4(r['noise_risk_score'])}"
                )
            lines.append("")

    lines += ["---", "", "## 9. Explained-variance weighting check", ""]
    if vw_available and "link_id" in vw_df.columns:
        shifted = vw_df[vw_df["rank_shift"].abs() >= 3] if not vw_df.empty else pd.DataFrame()
        stable = vw_df[vw_df["remains_top7_after_weighting"] == True] if not vw_df.empty else pd.DataFrame()
        lines += [
            f"- Variance-weighted ranks computed from `run/pc_focus_table.csv` explained_variance_ratio × per-PC link abs Delta.",
            f"- Rows: **{len(vw_df)}** link × cell entries.",
            f"- Links with |rank shift| ≥ 3: **{len(shifted)}**.",
            f"- Links flagged `remains_top7_after_weighting`: **{len(stable)}** row flags (includes top-7 membership changes).",
            "- **Interpretation:** weighting often **reorders** but does not always **eliminate** null-space concentration; treat as sensitivity check.",
        ]
    else:
        lines.append("- Explained-variance weighting table could not be fully populated; see `nullspace_explained_variance_weighting_check.csv`.")

    lines += [
        "",
        "---",
        "",
        "## 10. Poster recommendation",
        "",
        "| Question | Recommendation |",
        "| --- | --- |",
        "| Show null-space on main poster? | **Secondary panel only** (ratio + 1 family example) |",
        "| Best example cell | **671 P3_P4_P5 T2 repetition** or **671 P3 T1_vs_T2 longitudinal** if family overlap acceptable |",
        "| p50 vs p60 | Show **p50 primary**, p60 as **sensitivity footnote** |",
        "| Display type | **Anatomical families + null/all ratio**, not exact rank-1 link identity alone |",
        "| Strongest message level | **Family-level / magnitude descriptive**, not exact-link causal |",
        "",
        "---",
        "",
        "## 11. Safe wording for poster",
        "",
        "**A. Strong but safe:** \"Later-PC (null-space) link contributions show elevated descriptive magnitude relative to all-PC summaries, concentrated in upper- and lower-limb segment families (participant-specific).\"",
        "",
        "**B. Conservative:** \"Null-space splits (after p50) highlight additional less-dominant link variability not visible in the primary PC subset; link identity varies by threshold.\"",
        "",
        "**C. If link identity unstable:** \"Null-space magnitude ratios exceed all-PC in several cells, but exact top links are threshold-sensitive; interpret at family or summary level only.\"",
        "",
        "---",
        "",
        "## 12. Final conclusion",
        "",
        "The null-space finding is **not uniformly a stable exact-link anatomical result**. It is **strong enough as a descriptive secondary / sensitivity storyline** when framed as:",
        "",
        "1. **Family-level structured pattern** — best supported (upper limb, lower limb, shoulder chain recur).",
        "2. **Magnitude-only sensitivity** — common when null/all > 1 but top-7 Jaccard is low.",
        "3. **Exact-link stability** — limited across p50/p60 and across timepoints.",
        "4. **Possible noise/model sensitivity** — present in a minority of cells with very low overlap.",
        "",
        "**Central poster finding:** No — use as **supporting later-PC / robustness context**.",
        "**Sensitivity analysis:** Yes.",
        "**Too unstable for any mention:** No — magnitude elevation is too consistent to omit entirely if null-space is part of methods.",
        "",
        "---",
        "",
        "## 13. p70 diagnostic threshold stability",
        "",
    ]
    ts_df = pd.DataFrame(threshold_rows)
    if not ts_df.empty:
        for lbl in sorted(ts_df["threshold_stability_label"].unique()):
            lines.append(f"- **`{lbl}`:** {int((ts_df.threshold_stability_label == lbl).sum())} cells")
        lines.append("")
        lines.append("See `nullspace_threshold_stability_summary.csv` and `nullspace_p50_p60_p70_link_overlap.csv` for full numeric detail.")
    lines.append("")
    lines.append("```json")
    lines.append(
        json.dumps(
            {
                "output_folder": "Layer3_JcvPCA/outputs/nullspace_link_stability_review",
                "cells_top7_rows": int(len(top7_df)),
                "overlap_cells": int(len(overlap_df)),
                "elevated_null_p50_cells": elev_p50,
                "elevated_null_p60_cells": elev_p60,
                "missing_inputs_count": len(MISSING_INPUTS),
            },
            indent=2,
        )
    )
    lines.append("```")
    lines.append("")

    (OUT / "nullspace_top7_full_numeric_report.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
