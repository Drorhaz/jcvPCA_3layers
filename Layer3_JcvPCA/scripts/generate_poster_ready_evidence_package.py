#!/usr/bin/env python3
"""Generate poster-ready evidence package from existing Gaga JcvPCA batch outputs."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import kendalltau, spearmanr

_REPO_ROOT = Path(__file__).resolve().parents[2]
_LAYER3_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from project_paths import load_project_paths  # noqa: E402

BATCH = _LAYER3_ROOT / "outputs" / "gaga_batch_jcvpca_20260626_193319"
OUT = _LAYER3_ROOT / "outputs" / "poster_ready_evidence_package"


def configure_evidence_package_paths(
    *,
    config_path: Path | None = None,
    batch_dir: Path | None = None,
    out_dir: Path | None = None,
) -> None:
    """Resolve batch input and evidence-package output paths from config."""
    global BATCH, OUT

    paths = load_project_paths(config_path=config_path)
    resolved_batch = (batch_dir or paths.layer3_canonical_batch).resolve()
    resolved_out = (out_dir or paths.poster_evidence_package).resolve()

    if not resolved_batch.is_dir():
        raise FileNotFoundError(
            f"Required canonical Layer 3 batch missing: {resolved_batch}\n"
            f"Config: {paths.config_path}"
        )

    BATCH = resolved_batch
    OUT = resolved_out


def parse_evidence_package_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build poster-ready evidence CSV package from an existing JcvPCA batch.",
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
        help="Override evidence package output directory (default: layer3.poster_evidence_package).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate paths and list planned outputs without writing files.",
    )
    return parser.parse_args(argv)


configure_evidence_package_paths()

PARTICIPANTS = ["671", "252"]
BLOCKS = [("A", "all_P1_P2_P3_P4_P5"), ("B", "P3_P4_P5")]
PRIMARY_BLOCK = "P3_P4_P5"
LONGITUDINAL = [
    ("T1_vs_T2", "L1_T1_vs_T2"),
    ("T1_vs_T3", "L2_T1_vs_T3"),
]
EXPLORATORY = [("T2_vs_T3", "L3_T2_vs_T3")]
REPETITION = [
    ("T1", "T1_R1_vs_T1_R2", "I_T1_R1_vs_R2"),
    ("T2", "T2_R1_vs_T2_R2", "I_T2_R1_vs_R2"),
    ("T3", "T3_R1_vs_T3_R2", "I_T3_R1_vs_R2"),
]
FOCUS_ALL = ["all", "functional_p50", "null_space_after_p50", "functional_p60", "null_space_after_p60"]
FOCUS_NV = FOCUS_ALL  # p70 derived separately
NULL_FOCUS = ["null_space_after_p50", "null_space_after_p60", "null_space_after_p70"]

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

COMP_ID_TO_LABEL = {
    "L1_T1_vs_T2": "T1_vs_T2",
    "L2_T1_vs_T3": "T1_vs_T3",
    "L3_T2_vs_T3": "T2_vs_T3",
    "I_T1_R1_vs_R2": "T1_R1_vs_T1_R2",
    "I_T2_R1_vs_R2": "T2_R1_vs_T2_R2",
    "I_T3_R1_vs_R2": "T3_R1_vs_T3_R2",
}


def link_meta(link_id: str) -> tuple[str, str, str]:
    return LINK_SPECS.get(link_id, ("mixed_or_other", "unknown", "unknown"))


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


def entropy_norm(values: np.ndarray) -> float:
    v = np.asarray(values, dtype=float)
    v = v[v >= 0]
    t = v.sum()
    if t <= 0 or v.size <= 1:
        return 0.0
    p = v / t
    p = p[p > 0]
    return float(-np.sum(p * np.log(p)) / math.log(len(v)))


def links_for_pct(cum: np.ndarray, pct: float) -> int:
    if cum.size == 0:
        return 0
    hit = np.where(cum >= pct)[0]
    return int(hit[0] + 1) if hit.size else int(cum.size)


def concentration_label(top3: float, g: float) -> str:
    if pd.isna(top3) or pd.isna(g):
        return "insufficient_data"
    if top3 >= 0.70 or g >= 0.65:
        return "highly_concentrated"
    if top3 >= 0.55 or g >= 0.50:
        return "more_concentrated"
    if 0.40 <= top3 <= 0.55 and 0.35 <= g <= 0.50:
        return "moderately_distributed"
    if top3 < 0.40 and g < 0.35:
        return "broadly_distributed"
    if top3 >= 0.55:
        return "more_concentrated"
    if g >= 0.50:
        return "more_concentrated"
    return "moderately_distributed"


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
    out = out.sort_values("abs_delta", ascending=False).reset_index(drop=True)
    out["rank_abs_delta"] = np.arange(1, len(out) + 1)
    out["relative_abs_delta_share"] = out["abs_delta"] / total if total > 0 else 0.0
    cum = out["abs_delta"].cumsum()
    out["cumulative_abs_delta_share"] = cum / total if total > 0 else 0.0
    out["is_top1"] = out["rank_abs_delta"] == 1
    out["is_top3"] = out["rank_abs_delta"] <= 3
    out["is_top5"] = out["rank_abs_delta"] <= 5
    out["is_top7"] = out["rank_abs_delta"] <= 7
    fams = out["link_id"].map(lambda x: link_meta(x))
    out["anatomical_family"] = [f[0] for f in fams]
    out["body_region"] = [f[1] for f in fams]
    out["side"] = [f[2] for f in fams]
    return out


def load_p70_links(base: Path) -> pd.DataFrame:
    pc_path = base / "run" / "pc_focus_table.csv"
    link_path = base / "run" / "link_level_jrw_rss.csv"
    if not pc_path.is_file() or not link_path.is_file():
        return pd.DataFrame()
    pc = pd.read_csv(pc_path).sort_values("pc")
    p70_row = pc[pc["cumulative_explained_variance"] >= 0.70]
    if p70_row.empty:
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


def load_focus_links(pid: str, block_id: str, comp_key: str, focus_mode: str) -> pd.DataFrame:
    base = BATCH / "comparisons" / f"{pid}_{block_id}_{comp_key}"
    if focus_mode == "null_space_after_p70":
        return load_p70_links(base)
    run_dir = base / "run" if focus_mode == "all" else base / f"run_{focus_mode}"
    path = run_dir / "link_level_jrw_rss.csv"
    if not path.is_file():
        return pd.DataFrame()
    return finalize_links(aggregate_link_csv(path))


def get_selected_m(pid: str, block_id: str, comp_key: str) -> int | None:
    df = pd.read_csv(BATCH / "selected_m_by_comparison.csv")
    key = f"{pid}_{block_id}_{comp_key}"
    row = df[df.comparison_key == key]
    if row.empty:
        return None
    return int(row.iloc[0].selected_m)


def get_pc_meta(pid: str, block_id: str, comp_key: str) -> dict:
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
        "functional_pc_count_p50": len(str(r.included_pcs_functional_p50).split(","))
        if pd.notna(r.included_pcs_functional_p50)
        else 0,
        "nullspace_pc_count_p50": int(r.null_space_p50_n_pcs) if pd.notna(r.null_space_p50_n_pcs) else 0,
        "functional_pc_count_p60": len(str(r.included_pcs_functional_p60).split(","))
        if pd.notna(r.included_pcs_functional_p60)
        else 0,
        "nullspace_pc_count_p60": int(r.null_space_p60_n_pcs) if pd.notna(r.null_space_p60_n_pcs) else 0,
    }


def null_pc_counts(focus_mode: str, meta: dict) -> tuple[int | None, int | None]:
    if focus_mode == "null_space_after_p50":
        return meta.get("functional_pc_count_p50"), meta.get("nullspace_pc_count_p50")
    if focus_mode == "null_space_after_p60":
        return meta.get("functional_pc_count_p60"), meta.get("nullspace_pc_count_p60")
    return None, None


def dist_metrics(links: pd.DataFrame) -> dict:
    if links.empty:
        return {}
    abs_d = links["abs_delta"].to_numpy()
    total = float(abs_d.sum())
    n = len(links)
    probs = abs_d / total if total > 0 else np.zeros(n)
    sorted_p = np.sort(probs)[::-1]
    cum = np.cumsum(sorted_p)
    top1_idx = int(links["abs_delta"].idxmax())
    return {
        "n_links": n,
        "sum_abs_delta": total,
        "mean_abs_delta": float(np.mean(abs_d)),
        "median_abs_delta": float(np.median(abs_d)),
        "max_abs_delta": float(np.max(abs_d)),
        "max_link_share": float(sorted_p[0]) if n else float("nan"),
        "top1_link": str(links.loc[top1_idx, "link_id"]),
        "top3_share": float(sorted_p[: min(3, n)].sum()),
        "top5_share": float(sorted_p[: min(5, n)].sum()),
        "links_needed_for_50_percent": links_for_pct(cum, 0.50),
        "links_needed_for_80_percent": links_for_pct(cum, 0.80),
        "gini": gini(abs_d),
        "normalized_entropy": entropy_norm(abs_d),
    }


def timepoint_pattern(t1: float, t2: float, t3: float) -> tuple[str, str, bool]:
    vals = {"T1": t1, "T2": t2, "T3": t3}
    valid = {k: v for k, v in vals.items() if not pd.isna(v)}
    if not valid:
        return "NA", "insufficient_data", False
    largest = max(valid, key=valid.get)
    t2_largest = largest == "T2"
    v1, v2, v3 = t1, t2, t3
    if all(not pd.isna(x) for x in [v1, v2, v3]):
        if v1 < v2 < v3:
            return largest, "monotonic_increase", t2_largest
        if v1 > v2 > v3:
            return largest, "monotonic_decrease", t2_largest
        if v2 == max(v1, v2, v3):
            return largest, "T2_peak", t2_largest
        if v1 == max(v1, v2, v3):
            return largest, "T1_peak", t2_largest
        if v3 == max(v1, v2, v3):
            return largest, "T3_peak", t2_largest
        if abs(v2 - v1) < 0.001 and abs(v3 - v2) < 0.001:
            return largest, "flat_or_mixed", t2_largest
        return largest, "non_monotonic", t2_largest
    return largest, "flat_or_mixed", t2_largest


def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return float("nan")
    u = a | b
    return len(a & b) / len(u) if u else float("nan")


def top_n(df: pd.DataFrame, n: int = 7) -> pd.DataFrame:
    return df.head(n).copy() if not df.empty else df


def rank_corr(a: pd.DataFrame, b: pd.DataFrame, links: list[str] | None = None) -> float:
    if a.empty or b.empty:
        return float("nan")
    merged = a.merge(b, on="link_id", suffixes=("_a", "_b"), how="inner")
    if links:
        merged = merged[merged.link_id.isin(links)]
    if len(merged) < 2:
        return float("nan")
    rho, _ = spearmanr(merged["abs_delta_a"], merged["abs_delta_b"])
    return float(rho)


def sign_agreement(a: pd.DataFrame, b: pd.DataFrame, links: list[str] | None = None) -> float:
    merged = a.merge(b, on="link_id", suffixes=("_a", "_b"), how="inner")
    if links:
        merged = merged[merged.link_id.isin(links)]
    if merged.empty:
        return float("nan")
    agree = (merged["sign_of_delta_a"] == merged["sign_of_delta_b"]) | (
        (merged["sign_of_delta_a"] == 0) & (merged["sign_of_delta_b"] == 0)
    )
    return float(agree.mean())


def compare_thresholds(
    df_a: pd.DataFrame, df_b: pd.DataFrame, null_a: float, null_b: float, pair: str
) -> dict:
    t7a = set(top_n(df_a, 7)["link_id"])
    t7b = set(top_n(df_b, 7)["link_id"])
    union = list(t7a | t7b)
    top1_a = top_n(df_a, 1)["link_id"].iloc[0] if not df_a.empty else ""
    top1_b = top_n(df_b, 1)["link_id"].iloc[0] if not df_b.empty else ""
    fam_a = link_meta(top1_a)[0] if top1_a else ""
    fam_b = link_meta(top1_b)[0] if top1_b else ""
    kt = float("nan")
    if len(union) >= 2:
        ra = {r.link_id: r.rank_abs_delta for _, r in df_a.iterrows()}
        rb = {r.link_id: r.rank_abs_delta for _, r in df_b.iterrows()}
        ranks_a = [ra.get(l, len(df_a) + 1) for l in union]
        ranks_b = [rb.get(l, len(df_b) + 1) for l in union]
        kt_val, _ = kendalltau(ranks_a, ranks_b)
        kt = float(kt_val) if not pd.isna(kt_val) else float("nan")
    dm_a = dist_metrics(df_a)
    dm_b = dist_metrics(df_b)
    top7_j = jaccard(t7a, t7b)
    rho = rank_corr(df_a, df_b, union)
    same_top1 = top1_a == top1_b and top1_a != ""
    same_fam = fam_a == fam_b and fam_a != ""
    fam_j = jaccard({link_meta(l)[0] for l in t7a}, {link_meta(l)[0] for l in t7b})
    if same_top1 and (pd.isna(top7_j) or top7_j >= 0.5) and (pd.isna(rho) or rho >= 0.45):
        stab = "stable_exact_links"
    elif same_fam and (pd.isna(top7_j) or top7_j >= 0.35):
        stab = "stable_anatomical_families"
    elif (not pd.isna(null_a) and not pd.isna(null_b) and null_a > 1 and null_b > 1) and (
        pd.isna(top7_j) or top7_j <= 0.35
    ):
        stab = "magnitude_consistent_but_link_sensitive"
    elif pair == "p50_vs_p60" and top7_j >= 4:
        stab = "stable_p50_p60_only" if "p70" in pair else "stable_exact_links"
    elif (not pd.isna(top7_j) and top7_j < 0.25) or (pd.isna(rho) and top7_j < 0.3):
        stab = "threshold_sensitive_possible_noise"
    else:
        stab = "magnitude_consistent_but_link_sensitive"
    return {
        "threshold_pair": pair,
        "null_threshold_A_to_all_ratio": null_a,
        "null_threshold_B_to_all_ratio": null_b,
        "top1_threshold_A": top1_a,
        "top1_threshold_B": top1_b,
        "same_top1_link": same_top1,
        "same_top1_family": same_fam,
        "top3_overlap_count": len(set(top_n(df_a, 3)["link_id"]) & set(top_n(df_b, 3)["link_id"])),
        "top5_overlap_count": len(set(top_n(df_a, 5)["link_id"]) & set(top_n(df_b, 5)["link_id"])),
        "top7_overlap_count": len(t7a & t7b),
        "top7_jaccard": top7_j,
        "family_jaccard_top7": fam_j,
        "spearman_rank_rho_all_links": rank_corr(df_a, df_b),
        "spearman_rank_rho_top7_union": rho,
        "kendall_tau_top7_union": kt,
        "pearson_corr_abs_delta_all_links": float("nan")
        if len(df_a.merge(df_b, on="link_id")) < 2
        else float(
            np.corrcoef(
                df_a.merge(df_b, on="link_id", suffixes=("_a", "_b"))["abs_delta_a"],
                df_a.merge(df_b, on="link_id", suffixes=("_a", "_b"))["abs_delta_b"],
            )[0, 1]
        ),
        "cosine_similarity_abs_delta_all_links": float("nan"),
        "sign_agreement_all_links": sign_agreement(df_a, df_b),
        "sign_agreement_top7_union": sign_agreement(df_a, df_b, union),
        "gini_threshold_A": dm_a.get("gini", float("nan")),
        "gini_threshold_B": dm_b.get("gini", float("nan")),
        "top3_share_threshold_A": dm_a.get("top3_share", float("nan")),
        "top3_share_threshold_B": dm_b.get("top3_share", float("nan")),
        "threshold_stability_label": stab,
    }


def null_all_ratio(pid: str, block_id: str, comp_key: str, null_mode: str) -> float:
    null_df = load_focus_links(pid, block_id, comp_key, null_mode)
    all_df = load_focus_links(pid, block_id, comp_key, "all")
    if null_df.empty or all_df.empty:
        return float("nan")
    mn = null_df["abs_delta"].mean()
    ma = all_df["abs_delta"].mean()
    return float(mn / ma) if ma > 0 else float("nan")


def build_longitudinal_poster_table() -> pd.DataFrame:
    rows = []
    for pid in PARTICIPANTS:
        for block_id, block_label in BLOCKS:
            for comp_label, comp_key in LONGITUDINAL:
                links = load_focus_links(pid, block_id, comp_key, "all")
                if links.empty:
                    continue
                sm = get_selected_m(pid, block_id, comp_key)
                for _, r in links.iterrows():
                    rows.append(
                        {
                            "participant_id": pid,
                            "block_label": block_label,
                            "comparison_label": comp_label,
                            "focus_mode": "all",
                            "link_id": r.link_id,
                            "anatomical_family": r.anatomical_family,
                            "body_region": r.body_region,
                            "side": r.side,
                            "JRW_A": r.JRW_A,
                            "JRW_B": r.JRW_B,
                            "JcvPCA_link_delta": r.JcvPCA_link_delta,
                            "abs_delta": r.abs_delta,
                            "sign_of_delta": r.sign_of_delta,
                            "rank_abs_delta": r.rank_abs_delta,
                            "relative_abs_delta_share": r.relative_abs_delta_share,
                            "cumulative_abs_delta_share": r.cumulative_abs_delta_share,
                            "is_top1": r.is_top1,
                            "is_top3": r.is_top3,
                            "is_top5": r.is_top5,
                            "is_top7": r.is_top7,
                            "selected_m": sm,
                            "n_links": len(links),
                        }
                    )
    df = pd.DataFrame(rows)
    return df.sort_values(
        ["participant_id", "block_label", "comparison_label", "rank_abs_delta"]
    )


def build_delta_nv_ratio() -> tuple[pd.DataFrame, pd.DataFrame]:
    nv = pd.read_csv(BATCH / "natural_variability_link_level.csv")
    nv_all = nv[nv.focus_mode == "all"]
    rows = []
    for pid in PARTICIPANTS:
        for block_id, block_label in BLOCKS:
            for comp_label, comp_key in LONGITUDINAL:
                long_df = load_focus_links(pid, block_id, comp_key, "all")
                if long_df.empty:
                    continue
                nv_t1 = nv_all[
                    (nv_all.participant_id.astype(str) == pid)
                    & (nv_all.block_label == block_label)
                    & (nv_all.comparison_variant == "T1_R1_vs_T1_R2")
                ].set_index("link_id")["abs_delta"]
                nv_t2 = nv_all[
                    (nv_all.participant_id.astype(str) == pid)
                    & (nv_all.block_label == block_label)
                    & (nv_all.comparison_variant == "T2_R1_vs_T2_R2")
                ].set_index("link_id")["abs_delta"]
                nv_t3 = nv_all[
                    (nv_all.participant_id.astype(str) == pid)
                    & (nv_all.block_label == block_label)
                    & (nv_all.comparison_variant == "T3_R1_vs_T3_R2")
                ].set_index("link_id")["abs_delta"]
                for _, r in long_df.iterrows():
                    lid = r.link_id
                    nv1 = nv_t1.get(lid, float("nan"))
                    nv2 = nv_t2.get(lid, float("nan"))
                    nv3 = nv_t3.get(lid, float("nan"))
                    nv_vals = [x for x in [nv1, nv2, nv3] if not pd.isna(x)]
                    nv_mean = float(np.mean(nv_vals)) if nv_vals else float("nan")
                    nv_max = float(np.max(nv_vals)) if nv_vals else float("nan")
                    d = r.JcvPCA_link_delta
                    ad = r.abs_delta
                    r_t1 = ad / nv1 if not pd.isna(nv1) and nv1 > 0 else float("nan")
                    r_mean = ad / nv_mean if not pd.isna(nv_mean) and nv_mean > 0 else float("nan")
                    r_max = ad / nv_max if not pd.isna(nv_max) and nv_max > 0 else float("nan")
                    outside = (not pd.isna(nv1) and ad > nv1) if not pd.isna(nv1) else False
                    rows.append(
                        {
                            "participant_id": pid,
                            "block_label": block_label,
                            "comparison_label": comp_label,
                            "link_id": lid,
                            "anatomical_family": r.anatomical_family,
                            "body_region": r.body_region,
                            "side": r.side,
                            "longitudinal_delta": d,
                            "abs_longitudinal_delta": ad,
                            "NV_T1_abs_delta": nv1,
                            "NV_T2_abs_delta": nv2,
                            "NV_T3_abs_delta": nv3,
                            "NV_mean_abs_delta": nv_mean,
                            "NV_max_abs_delta": nv_max,
                            "delta_to_NV_T1_ratio": r_t1,
                            "delta_to_NV_mean_ratio": r_mean,
                            "delta_to_NV_max_ratio": r_max,
                            "outside_T1_NV_reference": outside,
                        }
                    )
    df = pd.DataFrame(rows)
    if df.empty:
        return df, df
    for col in ["rank_by_abs_longitudinal_delta", "rank_by_delta_to_NV_T1_ratio", "rank_by_delta_to_NV_mean_ratio"]:
        df[col] = np.nan
    for keys, col in [
        (["participant_id", "block_label", "comparison_label"], "rank_by_abs_longitudinal_delta"),
        (["participant_id", "block_label", "comparison_label"], "rank_by_delta_to_NV_T1_ratio"),
        (["participant_id", "block_label", "comparison_label"], "rank_by_delta_to_NV_mean_ratio"),
    ]:
        src = {
            "rank_by_abs_longitudinal_delta": "abs_longitudinal_delta",
            "rank_by_delta_to_NV_T1_ratio": "delta_to_NV_T1_ratio",
            "rank_by_delta_to_NV_mean_ratio": "delta_to_NV_mean_ratio",
        }[col]
        df[col] = df.groupby(keys)[src].rank(ascending=False, method="min")
    top7_rows = []
    for basis, rank_col, ratio_col, ref_col in [
        ("abs_longitudinal_delta", "rank_by_abs_longitudinal_delta", "abs_longitudinal_delta", "magnitude_only"),
        ("delta_to_NV_T1_ratio", "rank_by_delta_to_NV_T1_ratio", "delta_to_NV_T1_ratio", "T1_descriptive_NV"),
        ("delta_to_NV_mean_ratio", "rank_by_delta_to_NV_mean_ratio", "delta_to_NV_mean_ratio", "mean_descriptive_NV"),
    ]:
        for (pid, bl, cl), grp in df.groupby(["participant_id", "block_label", "comparison_label"]):
            sub = grp.nsmallest(7, rank_col)
            for _, r in sub.iterrows():
                ratio_val = r[ratio_col] if basis != "abs_longitudinal_delta" else r.get("delta_to_NV_T1_ratio", float("nan"))
                top7_rows.append(
                    {
                        "ranking_basis": basis,
                        "participant_id": pid,
                        "block_label": bl,
                        "comparison_label": cl,
                        "rank": int(r[rank_col]),
                        "link_id": r.link_id,
                        "anatomical_family": r.anatomical_family,
                        "body_region": r.body_region,
                        "side": r.side,
                        "longitudinal_delta": r.longitudinal_delta,
                        "abs_longitudinal_delta": r.abs_longitudinal_delta,
                        "NV_reference_used": ref_col,
                        "delta_to_NV_ratio": ratio_val,
                        "outside_NV_reference": r.outside_T1_NV_reference,
                        "relative_abs_delta_share": r.abs_longitudinal_delta / grp["abs_longitudinal_delta"].sum()
                        if grp["abs_longitudinal_delta"].sum() > 0
                        else 0,
                    }
                )
    top7 = pd.DataFrame(top7_rows)
    return df, top7


def build_nv_scalar_table() -> tuple[pd.DataFrame, pd.DataFrame]:
    nv = pd.read_csv(BATCH / "natural_variability_by_timepoint_focus.csv")
    nv = nv[nv.focus_mode.isin(FOCUS_NV)]
    pattern_lookup = {}
    pattern_rows = []
    for (pid, bl, fm), grp in nv.groupby(["participant_id", "block_label", "focus_mode"]):
        t1 = grp[grp.timepoint == "T1"]["mean_abs_delta"]
        t2 = grp[grp.timepoint == "T2"]["mean_abs_delta"]
        t3 = grp[grp.timepoint == "T3"]["mean_abs_delta"]
        v1 = float(t1.iloc[0]) if not t1.empty else float("nan")
        v2 = float(t2.iloc[0]) if not t2.empty else float("nan")
        v3 = float(t3.iloc[0]) if not t3.empty else float("nan")
        largest, pattern, t2_largest = timepoint_pattern(v1, v2, v3)
        pattern_lookup[(pid, bl, fm)] = pattern
        pattern_rows.append(
            {
                "participant_id": pid,
                "block_label": bl,
                "focus_mode": fm,
                "T1_mean_abs_delta": v1,
                "T2_mean_abs_delta": v2,
                "T3_mean_abs_delta": v3,
                "largest_timepoint": largest,
                "T2_is_largest": t2_largest,
                "monotonic_pattern": pattern,
                "interpretation": f"Descriptive repetition variability; largest at {largest}; pattern={pattern}",
            }
        )
    poster = nv.rename(columns={"comparison_variant": "comparison_label"}).copy()
    poster["largest_timepoint_within_participant_block_focus"] = poster.apply(
        lambda r: pattern_rows[
            next(
                i
                for i, p in enumerate(pattern_rows)
                if p["participant_id"] == r.participant_id
                and p["block_label"] == r.block_label
                and p["focus_mode"] == r.focus_mode
            )
        ]["largest_timepoint"],
        axis=1,
    )
    poster["timepoint_pattern_label"] = poster.apply(
        lambda r: pattern_lookup.get((r.participant_id, r.block_label, r.focus_mode), ""),
        axis=1,
    )
    summary = pd.DataFrame(pattern_rows)
    return poster, summary


def build_nv_top7() -> pd.DataFrame:
    nv = pd.read_csv(BATCH / "natural_variability_link_level.csv")
    rows = []
    for (pid, bl, tp, cv, fm), grp in nv.groupby(
        ["participant_id", "block_label", "timepoint", "comparison_variant", "focus_mode"]
    ):
        if fm not in FOCUS_NV:
            continue
        sub = grp.sort_values("abs_delta", ascending=False).head(7).reset_index(drop=True)
        total = grp["abs_delta"].sum()
        cum_vals = sub["abs_delta"].cumsum()
        for rank, (_, r) in enumerate(sub.iterrows(), 1):
            fam = link_meta(r.link_id)
            cum = float(cum_vals.iloc[rank - 1])
            rows.append(
                {
                    "participant_id": pid,
                    "block_label": bl,
                    "timepoint": tp,
                    "comparison_label": cv,
                    "focus_mode": fm,
                    "link_id": r.link_id,
                    "anatomical_family": fam[0],
                    "body_region": fam[1],
                    "side": fam[2],
                    "JcvPCA_link_delta": r.JcvPCA_link_delta,
                    "abs_delta": r.abs_delta,
                    "sign_of_delta": r.sign_of_delta,
                    "rank_abs_delta": rank,
                    "relative_abs_delta_share": r.abs_delta / total if total > 0 else 0,
                    "cumulative_abs_delta_share": cum / total if total > 0 else 0,
                    "is_top1": rank == 1,
                    "is_top3": rank <= 3,
                    "is_top5": rank <= 5,
                    "is_top7": rank <= 7,
                }
            )
    return pd.DataFrame(rows)


def build_concentration_metrics() -> pd.DataFrame:
    rows = []
    # Longitudinal
    for pid in PARTICIPANTS:
        for block_id, block_label in BLOCKS:
            for comp_label, comp_key in LONGITUDINAL + EXPLORATORY:
                atype = "longitudinal" if comp_label != "T2_vs_T3" else "exploratory_T2_vs_T3"
                for fm in FOCUS_ALL:
                    links = load_focus_links(pid, block_id, comp_key, fm)
                    if links.empty:
                        continue
                    m = dist_metrics(links)
                    m.update(
                        {
                            "participant_id": pid,
                            "block_label": block_label,
                            "analysis_type": atype,
                            "comparison_label": comp_label,
                            "timepoint_if_repetition": "",
                            "focus_mode": fm,
                            "concentration_label": concentration_label(m["top3_share"], m["gini"]),
                        }
                    )
                    rows.append(m)
    # Repetition
    for pid in PARTICIPANTS:
        for block_id, block_label in BLOCKS:
            for tp, cv, comp_key in REPETITION:
                for fm in FOCUS_ALL:
                    links = load_focus_links(pid, block_id, comp_key, fm)
                    if links.empty:
                        continue
                    m = dist_metrics(links)
                    m.update(
                        {
                            "participant_id": pid,
                            "block_label": block_label,
                            "analysis_type": "repetition_variability",
                            "comparison_label": cv,
                            "timepoint_if_repetition": tp,
                            "focus_mode": fm,
                            "concentration_label": concentration_label(m["top3_share"], m["gini"]),
                        }
                    )
                    rows.append(m)
    return pd.DataFrame(rows)


def build_nullspace_top7() -> pd.DataFrame:
    rows = []
    contexts = [
        ("repetition_variability", REPETITION, ""),
        ("longitudinal", LONGITUDINAL, ""),
        ("exploratory_T2_vs_T3", EXPLORATORY, ""),
    ]
    for atype, comps, _ in contexts:
        for pid in PARTICIPANTS:
            for block_id, block_label in BLOCKS:
                for item in comps:
                    if atype == "repetition_variability":
                        tp, cv, comp_key = item
                        tp_col = tp
                    else:
                        cv, comp_key = item
                        tp_col = ""
                    meta = get_pc_meta(pid, block_id, comp_key)
                    for fm in NULL_FOCUS:
                        links = load_focus_links(pid, block_id, comp_key, fm)
                        if links.empty:
                            continue
                        func_c, null_c = null_pc_counts(fm, meta)
                        thresh = fm.replace("null_space_after_p", "")
                        sub = top_n(links, 7)
                        for _, r in sub.iterrows():
                            rows.append(
                                {
                                    "analysis_type": atype,
                                    "participant_id": pid,
                                    "block_label": block_label,
                                    "comparison_label": cv,
                                    "timepoint_if_repetition": tp_col,
                                    "focus_mode": fm,
                                    "pc_split_threshold": thresh,
                                    "selected_m": meta.get("selected_m"),
                                    "functional_pc_count": func_c,
                                    "nullspace_pc_count": null_c,
                                    "link_id": r.link_id,
                                    "anatomical_family": r.anatomical_family,
                                    "body_region": r.body_region,
                                    "side": r.side,
                                    "JRW_A": r.JRW_A,
                                    "JRW_B": r.JRW_B,
                                    "JcvPCA_link_delta": r.JcvPCA_link_delta,
                                    "abs_delta": r.abs_delta,
                                    "sign_of_delta": r.sign_of_delta,
                                    "rank_abs_delta": r.rank_abs_delta,
                                    "relative_abs_delta_share": r.relative_abs_delta_share,
                                    "cumulative_abs_delta_share": r.cumulative_abs_delta_share,
                                    "is_top1": r.is_top1,
                                    "is_top3": r.is_top3,
                                    "is_top5": r.is_top5,
                                    "is_top7": r.is_top7,
                                }
                            )
    return pd.DataFrame(rows)


def build_threshold_stability() -> pd.DataFrame:
    rows = []
    all_contexts = [
        ("repetition_variability", REPETITION),
        ("longitudinal", LONGITUDINAL),
        ("exploratory_T2_vs_T3", EXPLORATORY),
    ]
    pairs = [("p50_vs_p60", "null_space_after_p50", "null_space_after_p60")]
    # check p70 availability
    test = load_p70_links(BATCH / "comparisons" / "671_B_L1_T1_vs_T2")
    if not test.empty:
        pairs += [
            ("p60_vs_p70", "null_space_after_p60", "null_space_after_p70"),
            ("p50_vs_p70", "null_space_after_p50", "null_space_after_p70"),
        ]
    for atype, comps in all_contexts:
        for pid in PARTICIPANTS:
            for block_id, block_label in BLOCKS:
                for item in comps:
                    if atype == "repetition_variability":
                        tp, cv, comp_key = item
                        tp_col = tp
                    else:
                        cv, comp_key = item
                        tp_col = ""
                    for pair_label, fa, fb in pairs:
                        da = load_focus_links(pid, block_id, comp_key, fa)
                        db = load_focus_links(pid, block_id, comp_key, fb)
                        if da.empty or db.empty:
                            continue
                        ra = null_all_ratio(pid, block_id, comp_key, fa)
                        rb = null_all_ratio(pid, block_id, comp_key, fb)
                        cmp = compare_thresholds(da, db, ra, rb, pair_label)
                        rows.append(
                            {
                                "analysis_type": atype,
                                "participant_id": pid,
                                "block_label": block_label,
                                "comparison_label": cv,
                                "timepoint_if_repetition": tp_col,
                                **cmp,
                            }
                        )
    return pd.DataFrame(rows)


def build_noise_diagnostic(threshold_df: pd.DataFrame, top7_null: pd.DataFrame) -> pd.DataFrame:
    rows = []
    contexts = set(
        zip(
            threshold_df["analysis_type"],
            threshold_df["participant_id"],
            threshold_df["block_label"],
            threshold_df["comparison_label"],
            threshold_df["timepoint_if_repetition"],
        )
    )
    for atype, pid, bl, cl, tp in contexts:
        sub = threshold_df[
            (threshold_df.analysis_type == atype)
            & (threshold_df.participant_id == pid)
            & (threshold_df.block_label == bl)
            & (threshold_df.comparison_label == cl)
            & (threshold_df.timepoint_if_repetition.fillna("") == (tp or ""))
        ]
        p5060 = sub[sub.threshold_pair == "p50_vs_p60"]
        p6070 = sub[sub.threshold_pair == "p60_vs_p70"]
        r50 = null_all_ratio(pid, "B" if bl == PRIMARY_BLOCK else "A", _comp_key(cl, tp), "null_space_after_p50")
        r60 = null_all_ratio(pid, "B" if bl == PRIMARY_BLOCK else "A", _comp_key(cl, tp), "null_space_after_p60")
        r70 = null_all_ratio(pid, "B" if bl == PRIMARY_BLOCK else "A", _comp_key(cl, tp), "null_space_after_p70")
        o5060 = int(p5060["top7_overlap_count"].iloc[0]) if not p5060.empty else 0
        o6070 = int(p6070["top7_overlap_count"].iloc[0]) if not p6070.empty else float("nan")
        fj5060 = float(p5060["family_jaccard_top7"].iloc[0]) if not p5060.empty else float("nan")
        fj6070 = float(p6070["family_jaccard_top7"].iloc[0]) if not p6070.empty else float("nan")
        sp = float(p5060["spearman_rank_rho_top7_union"].iloc[0]) if not p5060.empty else float("nan")
        sa = float(p5060["sign_agreement_top7_union"].iloc[0]) if not p5060.empty else float("nan")
        block_id = "B" if bl == PRIMARY_BLOCK else "A"
        comp_key = _comp_key(cl, tp)
        p50 = load_focus_links(pid, block_id, comp_key, "null_space_after_p50")
        p60 = load_focus_links(pid, block_id, comp_key, "null_space_after_p60")
        dm50 = dist_metrics(p50)
        dm60 = dist_metrics(p60)
        top_links = top7_null[
            (top7_null.participant_id == pid)
            & (top7_null.block_label == bl)
            & (top7_null.comparison_label == cl)
            & (top7_null.timepoint_if_repetition.fillna("") == (tp or ""))
        ]["link_id"].tolist()
        rec = len(set(top_links))
        risk, struct, label = _noise_scores(o5060, fj5060, sp, sa, r50, r60, dm50, dm60, rec)
        rows.append(
            {
                "analysis_type": atype,
                "participant_id": pid,
                "block_label": bl,
                "comparison_label": cl,
                "timepoint_if_repetition": tp,
                "null_p50_to_all_ratio": r50,
                "null_p60_to_all_ratio": r60,
                "null_p70_to_all_ratio_if_available": r70,
                "top7_overlap_p50_p60": o5060,
                "top7_overlap_p60_p70_if_available": o6070,
                "family_jaccard_p50_p60": fj5060,
                "family_jaccard_p60_p70_if_available": fj6070,
                "spearman_rank_rho_p50_p60": sp,
                "sign_agreement_p50_p60": sa,
                "max_link_share_p50": dm50.get("max_link_share", float("nan")),
                "max_link_share_p60": dm60.get("max_link_share", float("nan")),
                "gini_p50": dm50.get("gini", float("nan")),
                "gini_p60": dm60.get("gini", float("nan")),
                "top3_share_p50": dm50.get("top3_share", float("nan")),
                "top3_share_p60": dm60.get("top3_share", float("nan")),
                "recurrence_count_of_top_links": rec,
                "noise_risk_score": risk,
                "structure_score": struct,
                "final_diagnostic_label": label,
            }
        )
    return pd.DataFrame(rows)


def _comp_key(cl: str, tp: str) -> str:
    mapping = {
        "T1_vs_T2": "L1_T1_vs_T2",
        "T1_vs_T3": "L2_T1_vs_T3",
        "T2_vs_T3": "L3_T2_vs_T3",
        "T1_R1_vs_T1_R2": "I_T1_R1_vs_R2",
        "T2_R1_vs_T2_R2": "I_T2_R1_vs_R2",
        "T3_R1_vs_T3_R2": "I_T3_R1_vs_R2",
    }
    return mapping.get(cl, "")


def _noise_scores(o5060, fj, sp, sa, r50, r60, dm50, dm60, rec) -> tuple[float, float, str]:
    risk = struct = 0.0
    if o5060 <= 2:
        risk += 1.5
    if not pd.isna(fj) and fj < 0.4:
        risk += 1.0
    if not pd.isna(sp) and sp < 0.3:
        risk += 1.0
    if not pd.isna(sa) and sa < 0.6:
        risk += 1.0
    if dm50.get("max_link_share", 0) > 0.50:
        risk += 1.0
    if o5060 >= 4:
        struct += 1.5
    if not pd.isna(fj) and fj >= 0.6:
        struct += 1.5
    if not pd.isna(sp) and sp >= 0.5:
        struct += 1.0
    if not pd.isna(sa) and sa >= 0.7:
        struct += 1.0
    if not pd.isna(r50) and r50 > 1 and not pd.isna(r60) and r60 > 1:
        struct += 1.0
    if rec >= 2:
        struct += 0.5
    if struct >= 4.5 and risk <= 2:
        return risk, struct, "likely_structured_nullspace_pattern"
    if struct >= 3 and risk <= 3.5:
        return risk, struct, "structured_but_threshold_sensitive"
    if (not pd.isna(r50) and r50 > 1 or not pd.isna(r60) and r60 > 1) and struct < 2.5:
        return risk, struct, "magnitude_only_no_stable_anatomy"
    if risk >= 4:
        return risk, struct, "possible_noise_or_model_sensitivity"
    return risk, struct, "insufficient_evidence"


def build_weighting_check() -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    summary_rows = []
    for pid in PARTICIPANTS:
        for block_id, block_label in BLOCKS:
            for item in REPETITION + LONGITUDINAL + EXPLORATORY:
                if len(item) == 3:
                    tp, cv, comp_key = item
                    atype = "repetition_variability"
                    tp_col = tp
                else:
                    cv, comp_key = item
                    atype = "longitudinal" if cv != "T2_vs_T3" else "exploratory_T2_vs_T3"
                    tp_col = ""
                base = BATCH / "comparisons" / f"{pid}_{block_id}_{comp_key}"
                pc_meta = pd.read_csv(base / "run" / "pc_focus_table.csv") if (base / "run" / "pc_focus_table.csv").is_file() else pd.DataFrame()
                raw = pd.read_csv(base / "run" / "link_level_jrw_rss.csv") if (base / "run" / "link_level_jrw_rss.csv").is_file() else pd.DataFrame()
                for fm in ["null_space_after_p50", "null_space_after_p60", "null_space_after_p70"]:
                    unw = load_focus_links(pid, block_id, comp_key, fm)
                    if unw.empty or pc_meta.empty or raw.empty:
                        continue
                    unw_path = base / f"run_{fm}" / "link_level_jcvpca_unweighted.csv"
                    if fm == "null_space_after_p70":
                        p70 = load_p70_links(base)
                        if p70.empty:
                            continue
                        null_pcs = []
                        pc = pc_meta.sort_values("pc")
                        p70_row = pc[pc["cumulative_explained_variance"] >= 0.70]
                        if not p70_row.empty:
                            p70_pc = int(p70_row.iloc[0]["pc"])
                            null_pcs = pc.loc[pc["pc"] > p70_pc, "pc"].tolist()
                    elif unw_path.is_file():
                        null_pcs = sorted(pd.read_csv(unw_path)["pc"].unique().tolist())
                    else:
                        continue
                    if not null_pcs:
                        continue
                    ev = pc_meta.set_index("pc")["explained_variance_ratio"].to_dict()
                    sub = raw[raw["pc"].isin(null_pcs)].copy()
                    sub["abs_delta"] = sub["JcvPCA_link"].abs()
                    sub["w"] = sub["pc"].map(ev).fillna(0.0)
                    wrows = []
                    for link_id, grp in sub.groupby("link_id"):
                        wsum = grp["w"].sum()
                        unw_val = float(grp["abs_delta"].mean())
                        vw = float((grp["abs_delta"] * grp["w"]).sum() / wsum) if wsum > 0 else unw_val
                        wrows.append({"link_id": link_id, "unweighted_abs_delta": unw_val, "variance_weighted_abs_delta": vw})
                    wdf = pd.DataFrame(wrows)
                    if wdf.empty:
                        continue
                    wdf["unweighted_rank"] = wdf["unweighted_abs_delta"].rank(ascending=False, method="min").astype(int)
                    wdf["variance_weighted_rank"] = wdf["variance_weighted_abs_delta"].rank(ascending=False, method="min").astype(int)
                    wdf["rank_shift"] = wdf["variance_weighted_rank"] - wdf["unweighted_rank"]
                    tu = wdf["unweighted_abs_delta"].sum()
                    tw = wdf["variance_weighted_abs_delta"].sum()
                    wdf["relative_share_unweighted"] = wdf["unweighted_abs_delta"] / tu if tu > 0 else 0
                    wdf["relative_share_weighted"] = wdf["variance_weighted_abs_delta"] / tw if tw > 0 else 0
                    wdf["remains_top7_after_weighting"] = wdf["variance_weighted_rank"] <= 7
                    top7_u = set(wdf.nsmallest(7, "unweighted_rank")["link_id"])
                    top7_w = set(wdf.nsmallest(7, "variance_weighted_rank")["link_id"])
                    fam_u = {link_meta(l)[0] for l in top7_u}
                    fam_w = {link_meta(l)[0] for l in top7_w}
                    rho = rank_corr(
                        wdf.rename(columns={"unweighted_abs_delta": "abs_delta"}),
                        wdf.rename(columns={"variance_weighted_abs_delta": "abs_delta"}),
                    )
                    interp = "stable_after_weighting" if len(top7_u & top7_w) >= 4 else "rank_shift_after_weighting"
                    summary_rows.append(
                        {
                            "analysis_type": atype,
                            "participant_id": pid,
                            "block_label": block_label,
                            "comparison_label": cv,
                            "timepoint_if_repetition": tp_col,
                            "focus_mode": fm,
                            "top7_overlap_unweighted_vs_weighted": len(top7_u & top7_w),
                            "family_jaccard_unweighted_vs_weighted": jaccard(fam_u, fam_w),
                            "spearman_rank_rho_unweighted_vs_weighted": rho,
                            "interpretation": interp,
                        }
                    )
                    for _, wr in wdf.iterrows():
                        fam = link_meta(wr.link_id)
                        rows.append(
                            {
                                "analysis_type": atype,
                                "participant_id": pid,
                                "block_label": block_label,
                                "comparison_label": cv,
                                "timepoint_if_repetition": tp_col,
                                "focus_mode": fm,
                                "link_id": wr.link_id,
                                "anatomical_family": fam[0],
                                "unweighted_abs_delta": wr.unweighted_abs_delta,
                                "variance_weighted_abs_delta": wr.variance_weighted_abs_delta,
                                "unweighted_rank": wr.unweighted_rank,
                                "variance_weighted_rank": wr.variance_weighted_rank,
                                "rank_shift": wr.rank_shift,
                                "remains_top7_after_weighting": wr.remains_top7_after_weighting,
                                "relative_share_unweighted": wr.relative_share_unweighted,
                                "relative_share_weighted": wr.relative_share_weighted,
                            }
                        )
    detail = pd.DataFrame(rows)
    summary = pd.DataFrame(summary_rows)
    if detail.empty:
        summary = pd.DataFrame(
            [
                {
                    "analysis_type": "unavailable",
                    "participant_id": "NA",
                    "block_label": "NA",
                    "comparison_label": "NA",
                    "timepoint_if_repetition": "NA",
                    "focus_mode": "NA",
                    "top7_overlap_unweighted_vs_weighted": "unavailable",
                    "family_jaccard_unweighted_vs_weighted": "unavailable",
                    "spearman_rank_rho_unweighted_vs_weighted": "unavailable",
                    "interpretation": "Explained variance per PC available in pca_B_projected_explained_variance.csv and pc_focus_table.csv; weighting computed where null-space PCs exist.",
                }
            ]
        )
    return detail, summary


def build_body_region_summary(top7_long: pd.DataFrame, top7_null: pd.DataFrame) -> pd.DataFrame:
    rows = []
    lcd = pd.read_csv(BATCH / "link_contribution_distribution.csv")
    for _, r in lcd.iterrows():
        fam = link_meta(r.link_id)
        rows.append(
            {
                "participant_id": r.participant_id,
                "block_label": r.block_label,
                "analysis_type": "longitudinal"
                if r.comparison_label in ("T1_vs_T2", "T1_vs_T3")
                else ("exploratory_T2_vs_T3" if r.comparison_label == "T2_vs_T3" else "repetition_variability"),
                "comparison_label": r.comparison_label,
                "timepoint_if_repetition": "",
                "focus_mode": r.focus_mode,
                "anatomical_family": fam[0],
                "body_region": fam[1],
                "link_id": r.link_id,
                "abs_delta": r.abs_delta,
            }
        )
    base = pd.DataFrame(rows)
    agg_rows = []
    for keys, grp in base.groupby(
        [
            "participant_id",
            "block_label",
            "analysis_type",
            "comparison_label",
            "timepoint_if_repetition",
            "focus_mode",
            "anatomical_family",
            "body_region",
        ]
    ):
        total = grp["abs_delta"].sum()
        parent_total = base[
            (base.participant_id == keys[0])
            & (base.block_label == keys[1])
            & (base.comparison_label == keys[3])
            & (base.focus_mode == keys[5])
        ]["abs_delta"].sum()
        top = grp.loc[grp["abs_delta"].idxmax()]
        top7_links = set(
            top7_null[
                (top7_null.participant_id == keys[0])
                & (top7_null.block_label == keys[1])
                & (top7_null.comparison_label == keys[3])
                & (top7_null.focus_mode.str.startswith("null_space"))
            ]["link_id"]
        )
        agg_rows.append(
            {
                "participant_id": keys[0],
                "block_label": keys[1],
                "analysis_type": keys[2],
                "comparison_label": keys[3],
                "timepoint_if_repetition": keys[4],
                "focus_mode": keys[5],
                "anatomical_family": keys[6],
                "body_region": keys[7],
                "n_links_in_family": len(grp),
                "sum_abs_delta": total,
                "mean_abs_delta": grp["abs_delta"].mean(),
                "max_abs_delta": grp["abs_delta"].max(),
                "relative_family_share": total / parent_total if parent_total > 0 else 0,
                "top_link_in_family": top.link_id,
                "family_rank": 0,
                "appears_in_top7": any(l in top7_links for l in grp.link_id),
                "appears_in_p50": keys[5] in ("null_space_after_p50", "functional_p50", "all"),
                "appears_in_p60": keys[5] in ("null_space_after_p60", "functional_p60", "all"),
                "appears_in_p70_if_available": keys[5] == "all",
            }
        )
    out = pd.DataFrame(agg_rows)
    if not out.empty:
        out["family_rank"] = out.groupby(
            ["participant_id", "block_label", "analysis_type", "comparison_label", "focus_mode"]
        )["sum_abs_delta"].rank(ascending=False, method="min")
    return out


def build_direction_magnitude() -> pd.DataFrame:
    dr_files = {
        "T1_vs_T2": BATCH / "directional_robustness_t1_t2_link_results.csv",
        "T1_vs_T3": BATCH / "directional_robustness_t1_t3_link_results.csv",
        "T2_vs_T3": BATCH / "directional_robustness_t2_t3_link_results.csv",
    }
    rows = []
    for comp, path in dr_files.items():
        if not path.is_file():
            continue
        dr = pd.read_csv(path)
        ref_var = {
            "T1_vs_T2": "T1_R1_R2_vs_T2_R1_R2",
            "T1_vs_T3": "T1_R1_R2_vs_T3_R1_R2",
            "T2_vs_T3": "T1_R1_R2_vs_T2_R1_R2",
        }[comp]
        for (pid, bl, fm, lid), grp in dr.groupby(["participant_id", "block_label", "focus_mode", "link_id"]):
            pooled = grp[grp.comparison_variant == ref_var]
            pairings = grp[grp.comparison_variant != ref_var]
            if pooled.empty:
                continue
            mean_abs = float(pairings["abs_delta"].mean()) if not pairings.empty else float(pooled["abs_delta"].iloc[0])
            med_abs = float(pairings["abs_delta"].median()) if not pairings.empty else mean_abs
            signs = pairings["sign_of_delta"].tolist() if not pairings.empty else [int(pooled["sign_of_delta"].iloc[0])]
            ref_sign = int(pooled["sign_of_delta"].iloc[0])
            sign_ag = float(np.mean([s == ref_sign for s in signs])) if signs else float("nan")
            ranks = pairings["rank_by_abs_delta"].tolist() if not pairings.empty else [int(pooled["rank_by_abs_delta"].iloc[0])]
            rank_stab = 1.0 / (1.0 + float(np.std(ranks))) if len(ranks) > 1 else 1.0
            sp = float("nan")
            if len(pairings) >= 2:
                sp = rank_corr(pairings, pooled.rename(columns={"abs_delta": "abs_delta"}))
            in_top7_pooled = int(pooled["rank_by_abs_delta"].iloc[0]) <= 7
            in_top7_pair = any(r <= 7 for r in ranks)
            if mean_abs > 0.01 and sign_ag >= 0.75:
                label = "stable_magnitude_stable_direction"
            elif mean_abs > 0.01 and sign_ag < 0.75:
                label = "stable_magnitude_direction_sensitive"
            elif mean_abs <= 0.01 and sign_ag >= 0.75:
                label = "low_magnitude_stable_direction"
            elif pd.isna(sign_ag):
                label = "insufficient_data"
            else:
                label = "unstable_both"
            fam = link_meta(lid)
            rows.append(
                {
                    "participant_id": pid,
                    "block_label": bl,
                    "comparison_label": comp,
                    "focus_mode": fm,
                    "link_id": lid,
                    "anatomical_family": fam[0],
                    "mean_abs_delta_across_pairings": mean_abs,
                    "median_abs_delta_across_pairings": med_abs,
                    "rank_stability_score": rank_stab,
                    "sign_agreement_across_pairings": sign_ag,
                    "spearman_rank_stability": sp,
                    "appears_top7_in_pooled": in_top7_pooled,
                    "appears_top7_in_repetition_pairings": in_top7_pair,
                    "interpretation_label": label,
                }
            )
    return pd.DataFrame(rows)


def build_takehome(
    long_df: pd.DataFrame,
    nv_ratio: pd.DataFrame,
    nv_summary: pd.DataFrame,
    conc: pd.DataFrame,
    thresh: pd.DataFrame,
    noise: pd.DataFrame,
    direction: pd.DataFrame,
    body: pd.DataFrame,
) -> pd.DataFrame:
    p3 = nv_summary[(nv_summary.block_label == PRIMARY_BLOCK) & (nv_summary.focus_mode == "all")]
    t2_peak = p3["T2_is_largest"].sum()
    rows = [
        {
            "evidence_question": "Is T2 repetition variability elevated?",
            "primary_result": f"T2 largest in {t2_peak}/{len(p3)} participant-block all-PC NV summaries",
            "numeric_summary": p3[["participant_id", "T1_mean_abs_delta", "T2_mean_abs_delta", "T3_mean_abs_delta", "largest_timepoint"]].to_dict("records"),
            "where_seen": "natural_variability_timepoint_pattern_summary.csv",
            "poster_interpretation": "Descriptive repetition-to-repetition variability often peaks at T2 on P3 all-PC, participant-specific.",
            "caution": "Not scalar; link-level and distribution metrics differ by focus mode.",
        },
        {
            "evidence_question": "Is NV scalar or link-structured?",
            "primary_result": "Link-structured and distribution-heterogeneous",
            "numeric_summary": conc[conc.analysis_type == "repetition_variability"][["participant_id", "block_label", "focus_mode", "gini", "top3_share", "concentration_label"]].head(8).to_dict("records"),
            "where_seen": "concentration_metrics_all_analyses.csv",
            "poster_interpretation": "Natural variability is better represented by link-level profiles plus Gini/top3-share than a single scalar.",
            "caution": "Scalars useful for timeline panel only as summary context.",
        },
        {
            "evidence_question": "Does null-space carry substantial variability?",
            "primary_result": "Null/all mean abs-delta ratio often >1",
            "numeric_summary": noise[["participant_id", "block_label", "comparison_label", "null_p50_to_all_ratio", "null_p60_to_all_ratio"]].drop_duplicates().head(8).to_dict("records"),
            "where_seen": "nullspace_noise_vs_structure_diagnostic.csv",
            "poster_interpretation": "Later-PC / null-space-like subsets often show elevated mean link-level variability relative to all-PC.",
            "caution": "Magnitude elevation does not imply stable exact link identity.",
        },
        {
            "evidence_question": "Are null-space links stable across thresholds?",
            "primary_result": thresh[thresh.threshold_pair == "p50_vs_p60"]["threshold_stability_label"].value_counts().to_dict(),
            "numeric_summary": thresh[thresh.threshold_pair == "p50_vs_p60"][["participant_id", "block_label", "top7_overlap_count", "threshold_stability_label"]].head(6).to_dict("records"),
            "where_seen": "nullspace_threshold_stability_summary.csv",
            "poster_interpretation": "p50/p60 often show anatomical-family stability even when exact links differ.",
            "caution": "p70 can shift top links; treat as supplementary diagnostic.",
        },
        {
            "evidence_question": "Are longitudinal deltas larger than descriptive NV reference?",
            "primary_result": f"{nv_ratio['outside_T1_NV_reference'].sum()}/{len(nv_ratio)} link-comparisons outside T1 NV reference (all blocks)",
            "numeric_summary": nv_ratio.nlargest(5, "delta_to_NV_T1_ratio")[["participant_id", "block_label", "comparison_label", "link_id", "delta_to_NV_T1_ratio"]].to_dict("records"),
            "where_seen": "longitudinal_delta_nv_ratio_by_link.csv",
            "poster_interpretation": "Many links show longitudinal abs-Delta above T1 descriptive NV reference; participant-specific.",
            "caution": "Descriptive NV reference only — not inferential.",
        },
        {
            "evidence_question": "Are patterns concentrated or distributed?",
            "primary_result": conc[(conc.analysis_type == "longitudinal") & (conc.focus_mode == "all") & (conc.block_label == PRIMARY_BLOCK)][["concentration_label"]].value_counts().to_dict(),
            "numeric_summary": conc[(conc.block_label == PRIMARY_BLOCK) & (conc.focus_mode == "all")][["participant_id", "comparison_label", "gini", "top3_share", "normalized_entropy"]].to_dict("records"),
            "where_seen": "concentration_metrics_all_analyses.csv",
            "poster_interpretation": "Longitudinal all-PC patterns are broadly to moderately distributed (Gini ~0.35–0.55; top3 share ~0.35–0.48 on P3).",
            "caution": "Use Gini + top3 on poster; entropy supplementary.",
        },
        {
            "evidence_question": "Is link direction robust across repetition pairings?",
            "primary_result": direction[direction.focus_mode == "all"].groupby("comparison_label")["sign_agreement_across_pairings"].mean().to_dict(),
            "numeric_summary": direction[(direction.block_label == PRIMARY_BLOCK) & (direction.focus_mode == "all")].groupby("interpretation_label").size().to_dict(),
            "where_seen": "direction_vs_magnitude_integrated_report.csv",
            "poster_interpretation": "Pooled longitudinal Delta is an aggregate summary; link direction is repetition-pairing sensitive for many links.",
            "caution": "Report median sign agreement ~53–71% depending on comparison/block.",
        },
        {
            "evidence_question": "Is the pattern link-specific or family-level?",
            "primary_result": "Arm/hand and leg families recur; exact links vary",
            "numeric_summary": body[(body.block_label == PRIMARY_BLOCK) & (body.focus_mode == "all")].nlargest(10, "relative_family_share")[["participant_id", "anatomical_family", "relative_family_share"]].to_dict("records"),
            "where_seen": "body_region_anatomical_family_summary.csv",
            "poster_interpretation": "Participant-specific anatomical-family recurrence (upper limb, lower limb; pelvis_root for 252 only).",
            "caution": "Do not pool participants; schema differs (671: 14 links, 252: 16 links).",
        },
    ]
    return pd.DataFrame(rows)


def main(argv: list[str] | None = None) -> int:
    args = parse_evidence_package_args(argv)
    try:
        configure_evidence_package_paths(
            config_path=args.config,
            batch_dir=args.batch_dir,
            out_dir=args.evidence_dir,
        )
    except FileNotFoundError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1

    if args.dry_run:
        planned = [
            "longitudinal_link_delta_allpc_poster_table.csv",
            "longitudinal_delta_nv_ratio_by_link.csv",
            "longitudinal_delta_nv_ratio_top7.csv",
            "natural_variability_scalar_poster_table.csv",
            "natural_variability_timepoint_pattern_summary.csv",
            "natural_variability_top7_links_by_timepoint_focus.csv",
            "concentration_metrics_all_analyses.csv",
            "nullspace_top7_links_all_contexts.csv",
            "nullspace_threshold_stability_summary.csv",
            "nullspace_noise_vs_structure_diagnostic.csv",
            "nullspace_explained_variance_weighting_check.csv",
            "nullspace_weighting_summary.csv",
            "body_region_anatomical_family_summary.csv",
            "direction_vs_magnitude_integrated_report.csv",
            "poster_takehome_numeric_summary.csv",
            "poster_master_figure_data_index.md",
            "poster_ready_evidence_report.md",
        ]
        print(f"Batch input:  {BATCH}")
        print(f"Output dir:   {OUT}")
        print(f"Would write {len(planned)} artifacts:")
        for name in planned:
            print(f"  - {OUT / name}")
        return 0

    OUT.mkdir(parents=True, exist_ok=True)
    print("Building longitudinal poster table...")
    long_poster = build_longitudinal_poster_table()
    long_poster.to_csv(OUT / "longitudinal_link_delta_allpc_poster_table.csv", index=False)

    print("Building delta/NV ratios...")
    nv_ratio, nv_top7 = build_delta_nv_ratio()
    nv_ratio.to_csv(OUT / "longitudinal_delta_nv_ratio_by_link.csv", index=False)
    nv_top7.to_csv(OUT / "longitudinal_delta_nv_ratio_top7.csv", index=False)

    print("Building NV scalar tables...")
    nv_scalar, nv_pattern = build_nv_scalar_table()
    nv_scalar.to_csv(OUT / "natural_variability_scalar_poster_table.csv", index=False)
    nv_pattern.to_csv(OUT / "natural_variability_timepoint_pattern_summary.csv", index=False)

    print("Building NV top7...")
    nv_top7_links = build_nv_top7()
    nv_top7_links.to_csv(OUT / "natural_variability_top7_links_by_timepoint_focus.csv", index=False)

    print("Building concentration metrics...")
    conc = build_concentration_metrics()
    conc.to_csv(OUT / "concentration_metrics_all_analyses.csv", index=False)

    print("Building null-space top7...")
    null_top7 = build_nullspace_top7()
    null_top7.to_csv(OUT / "nullspace_top7_links_all_contexts.csv", index=False)

    print("Building threshold stability...")
    thresh = build_threshold_stability()
    thresh.to_csv(OUT / "nullspace_threshold_stability_summary.csv", index=False)

    print("Building noise diagnostic...")
    noise = build_noise_diagnostic(thresh, null_top7)
    noise.to_csv(OUT / "nullspace_noise_vs_structure_diagnostic.csv", index=False)

    print("Building weighting check...")
    weight_detail, weight_summary = build_weighting_check()
    weight_detail.to_csv(OUT / "nullspace_explained_variance_weighting_check.csv", index=False)
    weight_summary.to_csv(OUT / "nullspace_weighting_summary.csv", index=False)

    print("Building body region summary...")
    body = build_body_region_summary(long_poster, null_top7)
    body.to_csv(OUT / "body_region_anatomical_family_summary.csv", index=False)

    print("Building direction vs magnitude...")
    direction = build_direction_magnitude()
    direction.to_csv(OUT / "direction_vs_magnitude_integrated_report.csv", index=False)

    print("Building take-home summary...")
    takehome = build_takehome(long_poster, nv_ratio, nv_pattern, conc, thresh, noise, direction, body)
    takehome.to_csv(OUT / "poster_takehome_numeric_summary.csv", index=False)

    print("Generating markdown reports...")
    from generate_poster_evidence_report import generate_reports

    generate_reports(OUT, BATCH, long_poster, nv_ratio, nv_top7, nv_pattern, conc, null_top7, thresh, noise, direction, body, takehome)

    print(f"Done. Outputs in {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
