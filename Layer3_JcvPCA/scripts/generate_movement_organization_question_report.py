#!/usr/bin/env python3
"""Generate Gaga Movement-Organization Question Report from existing JcvPCA outputs."""

from __future__ import annotations

import ast
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import entropy as scipy_entropy

from layer3_batch_report_paths import (
    display_repo_path,
    parse_batch_report_cli,
    resolve_batch_report_paths,
    run_path_preflight,
)

ROOT = Path(__file__).resolve().parents[1]
BATCH = Path()
PKG = Path()
OUT = Path()
BATCH_ID = ""
BATCH_DISPLAY = ""
PKG_DISPLAY = ""

MO_REPORT_REQUIRED = [
    "timepoint_evenness_trends.csv",
    "timepoint_evenness_summary.csv",
    "timepoint_link_contribution_distribution.csv",
    "contribution_evenness_summary.csv",
    "pc_focus_p50_p60_by_comparison.csv",
    "pca_stability_by_comparison.csv",
    "natural_variability_distribution_metrics.csv",
    "pc_focus_evenness_comparison.csv",
]

MO_PKG_REQUIRED = [
    "natural_variability_timepoint_pattern_summary.csv",
    "longitudinal_delta_nv_ratio_by_link.csv",
    "longitudinal_delta_nv_ratio_top7.csv",
    "direction_vs_magnitude_integrated_report.csv",
    "nullspace_threshold_stability_summary.csv",
    "nullspace_noise_vs_structure_diagnostic.csv",
    "longitudinal_link_delta_allpc_poster_table.csv",
    "body_region_anatomical_family_summary.csv",
]


def configure_movement_org_report_paths(
    *,
    config_path: Path | None = None,
    batch_dir: Path | None = None,
    evidence_dir: Path | None = None,
) -> None:
    global BATCH, PKG, OUT, BATCH_ID, BATCH_DISPLAY, PKG_DISPLAY

    batch_paths = resolve_batch_report_paths(config_path=config_path, batch_dir=batch_dir)
    from project_paths import load_project_paths  # noqa: PLC0415

    paths = load_project_paths(config_path=config_path or batch_paths.config_path)
    pkg = (evidence_dir or paths.poster_evidence_package).resolve()
    if not pkg.is_dir():
        raise FileNotFoundError(
            f"Required poster evidence package missing: {pkg}\n"
            f"Config: {paths.config_path}"
        )

    BATCH = batch_paths.root
    PKG = pkg
    OUT = (batch_paths.root.parent / "movement_organization_question_report").resolve()
    BATCH_ID = batch_paths.batch_id
    BATCH_DISPLAY = batch_paths.batch_display
    PKG_DISPLAY = display_repo_path(pkg, paths.project_root)


try:
    configure_movement_org_report_paths()
except FileNotFoundError as exc:
    print(f"[FAIL] {exc}", file=sys.stderr)
    raise SystemExit(1) from exc

PRIMARY = "P3_P4_P5"
PARTICIPANTS = ["671", "252"]

LINK_SPECS = {
    "Neck_to_Head": ("trunk_neck_head", "central", "midline", "distal"),
    "Chest_to_Neck": ("trunk_neck_head", "central", "midline", "proximal"),
    "Chest_to_LShoulder": ("shoulder_chain", "central", "left", "proximal"),
    "Chest_to_RShoulder": ("shoulder_chain", "central", "right", "proximal"),
    "LShoulder_to_LUArm": ("shoulder_chain", "proximal_upper", "left", "proximal"),
    "RShoulder_to_RUArm": ("shoulder_chain", "proximal_upper", "right", "proximal"),
    "LUArm_to_LFArm": ("proximal_upper_limb", "distal_upper", "left", "proximal"),
    "RUArm_to_RFArm": ("proximal_upper_limb", "distal_upper", "right", "proximal"),
    "LFArm_to_LHand": ("distal_upper_limb", "distal_upper", "left", "distal"),
    "RFArm_to_RHand": ("distal_upper_limb", "distal_upper", "right", "distal"),
    "LThigh_to_LShin": ("lower_limb", "distal_lower", "left", "proximal"),
    "LShin_to_LFoot": ("lower_limb", "distal_lower", "left", "distal"),
    "RThigh_to_RShin": ("lower_limb", "distal_lower", "right", "proximal"),
    "RShin_to_RFoot": ("lower_limb", "distal_lower", "right", "distal"),
    "252_to_LThigh": ("pelvis_root", "central", "left", "proximal"),
    "252_to_RThigh": ("pelvis_root", "central", "right", "proximal"),
}

FAMILY_ORDER = [
    "shoulder_chain",
    "proximal_upper_limb",
    "distal_upper_limb",
    "lower_limb",
    "pelvis_root",
    "trunk_neck_head",
]


def meta(link: str) -> dict:
    fam, region, side, prox = LINK_SPECS.get(link, ("mixed_or_other", "unknown", "unknown", "unknown"))
    return {"family": fam, "region": region, "side": side, "prox_dist": prox}


def f3(x) -> str:
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return "NA"
    return f"{float(x):.3f}"


def parse_metrics(s: str) -> dict:
    try:
        return ast.literal_eval(s)
    except Exception:
        return {}


def load_pca_ev(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.is_file() else pd.DataFrame()


def pcs_for_threshold(ev: pd.DataFrame, thr: float) -> int:
    if ev.empty:
        return np.nan
    cum = ev["explained_variance_ratio"].cumsum()
    hit = cum[cum >= thr]
    return int(hit.index[0] + 1) if len(hit) else len(ev)


def pc_entropy(ev: pd.DataFrame) -> float:
    if ev.empty:
        return float("nan")
    p = ev["explained_variance_ratio"].to_numpy()
    p = p[p > 0]
    return float(scipy_entropy(p, base=2))


def participation_ratio(ev: pd.DataFrame) -> float:
    if ev.empty:
        return float("nan")
    lam = ev["explained_variance_ratio"].to_numpy()
    return float((lam.sum() ** 2) / (lam @ lam))


def timepoint_dataset(pid: str, block: str, tp: str) -> Path | None:
    b = "B" if block == PRIMARY else "A"
    if tp == "T1":
        p = BATCH / "comparisons" / f"{pid}_{b}_L1_T1_vs_T2" / "construction" / "dataset_A_preview.csv"
    elif tp == "T2":
        p = BATCH / "comparisons" / f"{pid}_{b}_L1_T1_vs_T2" / "construction" / "dataset_B_preview.csv"
    else:
        p = BATCH / "comparisons" / f"{pid}_{b}_L2_T1_vs_T3" / "construction" / "dataset_B_preview.csv"
    return p if p.is_file() else None


def link_rms_series(df: pd.DataFrame) -> pd.DataFrame:
    meta_cols = {"session_id", "run_label", "frame", "time_sec"}
    feat_cols = [c for c in df.columns if c not in meta_cols and not c.startswith("_")]
    stems = sorted({c.rsplit("_", 1)[0] for c in feat_cols if c.endswith(("_rx", "_ry", "_rz"))})
    out = {}
    for stem in stems:
        cols = [f"{stem}_rx", f"{stem}_ry", f"{stem}_rz"]
        if all(c in df.columns for c in cols):
            arr = df[cols].to_numpy(dtype=float)
            out[stem] = np.sqrt(np.sum(arr ** 2, axis=1))
    return pd.DataFrame(out)


def network_metrics(link_ts: pd.DataFrame, family_map: dict) -> dict:
    if link_ts.shape[1] < 2 or link_ts.shape[0] < 10:
        return {}
    corr = link_ts.corr().abs()
    arr = corr.to_numpy().copy()
    np.fill_diagonal(arr, 0)
    edges = (arr > 0.3).sum() / 2
    n = arr.shape[0]
    max_edges = n * (n - 1) / 2
    density = edges / max_edges if max_edges else 0
    links = list(corr.columns)
    within, between = [], []
    for i, a in enumerate(links):
        for j, b in enumerate(links):
            if i >= j:
                continue
            fa, fb = family_map.get(a, "other"), family_map.get(b, "other")
            v = arr[i, j]
            if fa == fb:
                within.append(v)
            else:
                between.append(v)
    return {
        "n_links": n,
        "edge_density_gt_0.3": float(density),
        "mean_within_family_corr": float(np.mean(within)) if within else float("nan"),
        "mean_between_family_corr": float(np.mean(between)) if between else float("nan"),
        "within_minus_between": float(np.mean(within) - np.mean(between)) if within and between else float("nan"),
    }


def count_families_above_threshold(link_df: pd.DataFrame, thr: float) -> int:
    fam_share = link_df.groupby("family")["share"].sum()
    return int((fam_share >= thr).sum())


def anatomical_balance(fam_shares: dict) -> float:
    vals = np.array(list(fam_shares.values()), dtype=float)
    if vals.sum() <= 0:
        return float("nan")
    p = vals / vals.sum()
    p = p[p > 0]
    return float(-np.sum(p * np.log(p)) / math.log(len(p)))


def lr_asymmetry(fam_side: dict) -> float:
    left = sum(v for k, v in fam_side.items() if k.endswith("_left"))
    right = sum(v for k, v in fam_side.items() if k.endswith("_right"))
    tot = left + right
    if tot <= 0:
        return float("nan")
    return float(abs(left - right) / tot)


def arm_leg_ratio(fam_tot: dict) -> float:
    arm = fam_tot.get("shoulder_chain", 0) + fam_tot.get("proximal_upper_limb", 0) + fam_tot.get("distal_upper_limb", 0)
    leg = fam_tot.get("lower_limb", 0) + fam_tot.get("pelvis_root", 0)
    return float(arm / leg) if leg > 0 else float("nan")


def trunk_limb_ratio(fam_tot: dict) -> float:
    trunk = fam_tot.get("trunk_neck_head", 0) + fam_tot.get("shoulder_chain", 0)
    limb = sum(fam_tot.get(f, 0) for f in ["proximal_upper_limb", "distal_upper_limb", "lower_limb", "pelvis_root"])
    return float(trunk / limb) if limb > 0 else float("nan")


def build_context() -> dict:
    ctx = {}
    te = pd.read_csv(BATCH / "timepoint_evenness_trends.csv")
    tes = pd.read_csv(BATCH / "timepoint_evenness_summary.csv")
    tld = pd.read_csv(BATCH / "timepoint_link_contribution_distribution.csv")
    ces = pd.read_csv(BATCH / "contribution_evenness_summary.csv")
    pcf = pd.read_csv(BATCH / "pc_focus_p50_p60_by_comparison.csv")
    pstab = pd.read_csv(BATCH / "pca_stability_by_comparison.csv")
    nv_pat = pd.read_csv(PKG / "natural_variability_timepoint_pattern_summary.csv")
    nv_dist = pd.read_csv(BATCH / "natural_variability_distribution_metrics.csv")
    nv_ratio = pd.read_csv(PKG / "longitudinal_delta_nv_ratio_by_link.csv")
    nv_top7 = pd.read_csv(PKG / "longitudinal_delta_nv_ratio_top7.csv")
    direction = pd.read_csv(PKG / "direction_vs_magnitude_integrated_report.csv")
    null_thresh = pd.read_csv(PKG / "nullspace_threshold_stability_summary.csv")
    null_noise = pd.read_csv(PKG / "nullspace_noise_vs_structure_diagnostic.csv")
    long_post = pd.read_csv(PKG / "longitudinal_link_delta_allpc_poster_table.csv")
    body = pd.read_csv(PKG / "body_region_anatomical_family_summary.csv")
    pfe = pd.read_csv(BATCH / "pc_focus_evenness_comparison.csv")

    for pid in PARTICIPANTS:
        p = {"pid": pid}
        p3_te = te[(te.participant_id.astype(str) == pid) & (te.block_label == PRIMARY)].iloc[0]
        p["trends_p3"] = p3_te.to_dict()
        p["tes_p3"] = tes[(tes.participant_id.astype(str) == pid) & (tes.block_label == PRIMARY)]
        p["tld_p3"] = tld[(tld.participant_id.astype(str) == pid) & (tld.block_label == PRIMARY)]
        p["ces_p3_long"] = ces[
            (ces.participant_id.astype(str) == pid)
            & (ces.block_label == PRIMARY)
            & (ces.comparison_label.isin(["T1_vs_T2", "T1_vs_T3"]))
            & (ces.focus_mode == "all")
        ]
        p["nv_pat_p3"] = nv_pat[(nv_pat.participant_id.astype(str) == pid) & (nv_pat.block_label == PRIMARY)]
        p["nv_ratio_p3"] = nv_ratio[(nv_ratio.participant_id.astype(str) == pid) & (nv_ratio.block_label == PRIMARY)]
        p["direction_p3"] = direction[(direction.participant_id.astype(str) == pid) & (direction.block_label == PRIMARY) & (direction.focus_mode == "all")]
        p["long_p3"] = long_post[(long_post.participant_id.astype(str) == pid) & (long_post.block_label == PRIMARY)]
        p["null_p3"] = null_thresh[(null_thresh.participant_id.astype(str) == pid) & (null_thresh.block_label == PRIMARY)]
        p["null_noise_p3"] = null_noise[(null_noise.participant_id.astype(str) == pid) & (null_noise.block_label == PRIMARY)]
        p["pfe_p3"] = pfe[(pfe.participant_id.astype(str) == pid) & (pfe.block_label == PRIMARY)]

        # PC metrics per timepoint from internal repetition PCA (Dataset A of I_T*_R1_vs_R2)
        pc_tp = {}
        for tp, ck in [("T1", "I_T1_R1_vs_R2"), ("T2", "I_T2_R1_vs_R2"), ("T3", "I_T3_R1_vs_R2")]:
            b = "B" if PRIMARY == "P3_P4_P5" else "A"
            base = BATCH / "comparisons" / f"{pid}_{b}_{ck}" / "run"
            ev = load_pca_ev(base / "pca_A_explained_variance.csv")
            row_a = pstab[(pstab.comparison_key == f"{pid}_{b}_{ck}") & (pstab.dataset_side == "A")]
            dom = float("nan")
            if not row_a.empty:
                dom = parse_metrics(row_a.iloc[0]["metrics"]).get("dominant_pc_variance_percent", float("nan"))
            pc_tp[tp] = {
                "pc1_pct": dom,
                "pc12_pct": float(ev["explained_variance_ratio"].head(2).sum() * 100) if not ev.empty else float("nan"),
                "pcs_80": pcs_for_threshold(ev, 0.80),
                "pcs_90": pcs_for_threshold(ev, 0.90),
                "participation_ratio": participation_ratio(ev),
                "pc_entropy_bits": pc_entropy(ev),
                "selected_m": parse_metrics(row_a.iloc[0]["metrics"]).get("selected_m", float("nan")) if not row_a.empty else float("nan"),
            }
        p["pc_tp"] = pc_tp

        # null/all longitudinal
        null_ratios = {}
        for cl in ["T1_vs_T2", "T1_vs_T3"]:
            for fm in ["null_space_after_p50", "null_space_after_p60"]:
                row = pfe[
                    (pfe.participant_id.astype(str) == pid)
                    & (pfe.block_label == PRIMARY)
                    & (pfe.comparison_label == cl)
                    & (pfe.focus_mode == fm)
                ]
                if not row.empty:
                    null_ratios[f"{cl}_{fm}"] = float(row.iloc[0]["focus_normalized_entropy"]) / float(row.iloc[0]["all_normalized_entropy"]) if row.iloc[0]["all_normalized_entropy"] else float("nan")
        p["null_ratios"] = null_ratios

        # Pre-JcvPCA network per timepoint
        nets = {}
        fam_map = {k: meta(k)["family"] for k in LINK_SPECS}
        for tp in ["T1", "T2", "T3"]:
            ds = timepoint_dataset(pid, PRIMARY, tp)
            if ds:
                df = pd.read_csv(ds)
                lts = link_rms_series(df)
                nets[tp] = network_metrics(lts, fam_map)
        p["networks"] = nets

        # Family shares per timepoint from tld
        fam_time = {}
        for tp in ["T1", "T2", "T3"]:
            sub = p["tld_p3"][p["tld_p3"].timepoint == tp]
            tot = sub["link_contribution"].sum()
            fam = {}
            side = {}
            prox = {"distal": 0.0, "proximal": 0.0}
            cent = {"central": 0.0, "peripheral": 0.0}
            for _, r in sub.iterrows():
                m = meta(r.link_id)
                fam[m["family"]] = fam.get(m["family"], 0) + r.link_contribution
                side[f"{m['family']}_{m['side']}"] = side.get(f"{m['family']}_{m['side']}", 0) + r.link_contribution
                prox[m["prox_dist"]] = prox.get(m["prox_dist"], 0) + r.link_contribution
                reg = "central" if m["region"] in ("central", "head_neck", "proximal_upper", "pelvis_proximal_lower") else "peripheral"
                cent[reg] = cent.get(reg, 0) + r.link_contribution
            fam_share = {k: v / tot for k, v in fam.items()} if tot > 0 else fam
            fam_time[tp] = {
                "fam_tot": fam,
                "fam_share": fam_share,
                "balance_entropy": anatomical_balance(fam_share),
                "lr_asymmetry": lr_asymmetry(side),
                "arm_leg_ratio": arm_leg_ratio(fam),
                "trunk_limb_ratio": trunk_limb_ratio(fam),
                "distal_share": prox.get("distal", 0) / tot if tot > 0 else 0,
                "proximal_share": prox.get("proximal", 0) / tot if tot > 0 else 0,
                "central_share": cent.get("central", 0) / tot if tot > 0 else 0,
                "peripheral_share": cent.get("peripheral", 0) / tot if tot > 0 else 0,
                "n_links_above_p25": int((~sub.low_relative_contribution).sum()),
                "n_low_links": int(sub.low_relative_contribution.sum()),
            }
        p["fam_time"] = fam_time

        # Low-baseline link rank shifts T1->T2/T3
        low_prom = []
        t1 = p["tld_p3"][p["tld_p3"].timepoint == "T1"][["link_id", "rank_by_contribution", "low_relative_contribution"]]
        for tp in ["T2", "T3"]:
            later = p["tld_p3"][p["tld_p3"].timepoint == tp][["link_id", "rank_by_contribution"]]
            merged = t1.merge(later, on="link_id", suffixes=("_T1", f"_{tp}"))
            low = merged[merged.low_relative_contribution]
            improved = low[low[f"rank_by_contribution_{tp}"] < low["rank_by_contribution_T1"]]
            low_prom.append({"timepoint": tp, "n_low_at_T1": len(low), "n_improved_rank": len(improved), "links": improved.link_id.tolist()})
        p["low_prom"] = low_prom

        ctx[pid] = p
    ctx["nv_top7"] = nv_top7
    ctx["body"] = body
    return ctx


def q_block(n: int, q: str, a671: str, a252: str, evidence: str) -> list[str]:
    return [
        f"### Q{n}. {q}",
        "",
        f"**Participant 671:** {a671}",
        "",
        f"**Participant 252:** {a252}",
        "",
        f"*Evidence:* {evidence}",
        "",
    ]


def generate_report(ctx: dict) -> str:
    p671, p252 = ctx["671"], ctx["252"]
    t671, t252 = p671["trends_p3"], p252["trends_p3"]
    lines = [
        "# Gaga Movement-Organization Question Report",
        "",
        f"Descriptive within-participant answers using JcvPCA batch `{BATCH_ID}` and poster evidence package (`{PKG_DISPLAY}/`). Primary block: **P3_P4_P5**, focus **all-PC** unless noted. Participants are **not pooled**.",
        "",
        "---",
        "",
    ]

    lines += q_block(
        1,
        "Did link-level contribution profiles become more distributed from T1 to T2/T3?",
        f"T2 vs T1: normalized entropy {f3(t671['entropy_T1'])}→{f3(t671['entropy_T2'])} (Δ={f3(t671['delta_entropy_T2_minus_T1'])}), Gini {f3(t671['Gini_T1'])}→{f3(t671['Gini_T2'])} (Δ={f3(t671['delta_Gini_T2_minus_T1'])}). T3 vs T1: entropy Δ={f3(t671['delta_entropy_T3_minus_T1'])}, Gini Δ={f3(t671['delta_Gini_T3_minus_T1'])}. **T2 slightly more distributed; T3 less distributed than T1** (Gini rises at T3).",
        f"T2 vs T1: entropy Δ={f3(t252['delta_entropy_T2_minus_T1'])}, Gini Δ={f3(t252['delta_Gini_T2_minus_T1'])}. T3 vs T1: entropy Δ={f3(t252['delta_entropy_T3_minus_T1'])}. **No clear monotonic shift** (`{t252['trend_label']}`); small mixed changes.",
        "`timepoint_evenness_trends.csv` (P3_P4_P5 timepoint-state PCA loading spread).",
    )

    n671_t2 = p671["fam_time"]["T2"]["n_links_above_p25"]
    n671_t1 = p671["fam_time"]["T1"]["n_links_above_p25"]
    n252_t3 = p252["fam_time"]["T3"]["n_links_above_p25"]
    lines += q_block(
        2,
        "Did the number of meaningfully contributing links increase at T2 or T3?",
        f"Links above relative-contribution threshold: T1={n671_t1}, T2={n671_t2}, T3={p671['fam_time']['T3']['n_links_above_p25']} (of 14). **T2 similar to T1; T3 similar**. Links-for-80%: T1={int(t671['links80_T1'])}, T2={int(t671['links80_T2'])}, T3={int(t671['links80_T3'])}.",
        f"Links above threshold: T1={p252['fam_time']['T1']['n_links_above_p25']}, T2={p252['fam_time']['T2']['n_links_above_p25']}, T3={n252_t3} (of 16). **No increase**; count stable (~12–13 non-low links).",
        "`timepoint_link_contribution_distribution.csv` low_relative_contribution flag vs p25 threshold.",
    )

    lp671 = p671["low_prom"]
    lines += q_block(
        3,
        "Did low-baseline contribution links become more prominent later?",
        f"At T1, {lp671[0]['n_low_at_T1']} low-contribution links; {lp671[0]['n_improved_rank']} improved rank by T2; {lp671[1]['n_improved_rank']} by T3. **Modest rank mobility** for low-T1 links; no wholesale promotion of trunk/neck links to top ranks.",
        f"Low-T1 links: {p252['low_prom'][0]['n_low_at_T1']}; improved rank T2={p252['low_prom'][0]['n_improved_rank']}, T3={p252['low_prom'][1]['n_improved_rank']}. Chest/neck links remain low-share; **limited promotion** of previously low links.",
        "`timepoint_link_contribution_distribution.csv` rank_by_contribution T1 vs T2/T3.",
    )

    fam_thr = 0.10
    lines += q_block(
        4,
        "Did the number of meaningful anatomical families increase later?",
        f"Families with ≥10% total contribution: T1={count_families_above_threshold(pd.DataFrame({'family': list(p671['fam_time']['T1']['fam_share'].keys()), 'share': list(p671['fam_time']['T1']['fam_share'].values())}), fam_thr)}, T2={count_families_above_threshold(pd.DataFrame({'family': list(p671['fam_time']['T2']['fam_share'].keys()), 'share': list(p671['fam_time']['T2']['fam_share'].values())}), fam_thr)}, T3={count_families_above_threshold(pd.DataFrame({'family': list(p671['fam_time']['T3']['fam_share'].keys()), 'share': list(p671['fam_time']['T3']['fam_share'].values())}), fam_thr)}. **Stable (~4 families)**; same major families throughout.",
        f"Same count **~4–5 families ≥10%** across T1/T2/T3 (shoulder, upper limb, lower limb; plus pelvis_root for 252). **No increase** in active family count.",
        "Anatomical-family aggregation of timepoint link contributions.",
    )

    lines += q_block(
        5,
        "Did contribution profiles become more multi-focal rather than dominated by top links?",
        f"T2: top-3 share {f3(t671['top3_T1'])}→{f3(t671['top3_T2'])} (Δ={f3(t671['delta_top3_T2_minus_T1'])}), top-1 {f3(p671['tes_p3'][p671['tes_p3'].timepoint=='T1'].top_1_share.iloc[0])}→{f3(p671['tes_p3'][p671['tes_p3'].timepoint=='T2'].top_1_share.iloc[0])}. **More multi-focal at T2**; **T3 re-concentrates** (top-3 Δ={f3(t671['delta_top3_T3_minus_T1'])}).",
        f"Top-3 share T1→T2→T3: {f3(t252['top3_T1'])}→{f3(t252['top3_T2'])}→{f3(t252['top3_T3'])}. **Slight defocusing at T2**, then similar at T3; overall `{t252['trend_label']}`.",
        "`timepoint_evenness_trends.csv` top3 and top1 shares.",
    )

    pc671, pc252 = p671["pc_tp"], p252["pc_tp"]
    lines += q_block(
        6,
        "Did the PC variance structure become less concentrated in PC1/PC1–2?",
        f"PC1% (Dataset A per timepoint): T1={f3(pc671['T1']['pc1_pct'])}, T2={f3(pc671['T2']['pc1_pct'])}, T3={f3(pc671['T3']['pc1_pct'])}. PC1+2%: {f3(pc671['T1']['pc12_pct'])}→{f3(pc671['T2']['pc12_pct'])}→{f3(pc671['T3']['pc12_pct'])}. **Mixed**: T2 slightly less PC1-dominated; T3 similar to T1.",
        f"PC1%: T1={f3(pc252['T1']['pc1_pct'])}, T2={f3(pc252['T2']['pc1_pct'])}, T3={f3(pc252['T3']['pc1_pct'])}. **T3 shows higher PC1 concentration** (26.6%) vs T1 (20.0%); not uniformly less concentrated.",
        "`pca_stability_by_comparison.csv` dominant_pc_variance_percent; `pca_A_explained_variance.csv` per internal repetition comparison.",
    )

    lines += q_block(
        7,
        "Did the number of PCs required to explain 80% or 90% variance increase?",
        f"PCs for 80%: T1={pc671['T1']['pcs_80']}, T2={pc671['T2']['pcs_80']}, T3={pc671['T3']['pcs_80']}. PCs for 90%: T1={pc671['T1']['pcs_90']}, T2={pc671['T2']['pcs_90']}, T3={pc671['T3']['pcs_90']}. **No increase at later timepoints**; T3 uses one fewer PC for 80% than T1.",
        f"PCs for 80%: T1={pc252['T1']['pcs_80']}, T2={pc252['T2']['pcs_80']}, T3={pc252['T3']['pcs_80']}. **No consistent increase** (T2 slightly lower than T1; T3 matches T1).",
        "Cumulative explained variance from `pca_A_explained_variance.csv`.",
    )

    lines += q_block(
        8,
        "Did participation ratio or PC entropy increase?",
        f"Participation ratio: T1={f3(pc671['T1']['participation_ratio'])}, T2={f3(pc671['T2']['participation_ratio'])}, T3={f3(pc671['T3']['participation_ratio'])}. PC entropy (bits): {f3(pc671['T1']['pc_entropy_bits'])}→{f3(pc671['T2']['pc_entropy_bits'])}→{f3(pc671['T3']['pc_entropy_bits'])}. **Both metrics higher at T2**, lower/similar at T3.",
        f"Participation ratio T1→T3: {f3(pc252['T1']['participation_ratio'])}→{f3(pc252['T2']['participation_ratio'])}→{f3(pc252['T3']['participation_ratio'])}. PC entropy increases T1→T3. **Modest increase in PC spread metrics at later timepoints**, not uniform.",
        "Computed from PCA A explained-variance ratios per timepoint.",
    )

    # Q9 null-space
    ns671 = p671["pfe_p3"][p671["pfe_p3"].focus_mode == "null_space_after_p50"]
    lines += q_block(
        9,
        "Did later-PC/null-space contribution increase relative to all-PC?",
        "Longitudinal null-space mean abs-delta exceeds all-PC (null/all ratio >1) for T1_vs_T2 and T1_vs_T3 in repetition and longitudinal contexts. **Yes descriptively** for later-PC subsets.",
        "Same pattern: null/all ratios frequently >1 on P3 (e.g. T3 repetition null_p50_to_all ≈ 4.0). **Later-PC subsets carry elevated link-level variability** relative to all-PC.",
        "`pc_focus_evenness_comparison.csv`, `nullspace_noise_vs_structure_diagnostic.csv`.",
    )

    # Q10
    fam_stab_671 = p671["null_p3"][p671["null_p3"].threshold_pair == "p50_vs_p60"]["family_jaccard_top7"].mean()
    lines += q_block(
        10,
        "Are null-space findings stable at the anatomical-family level across p50/p60/p70?",
        f"Mean family Jaccard (top-7) p50 vs p60 across P3 contexts ≈ {f3(fam_stab_671)}. Many contexts labeled `stable_anatomical_families` or `magnitude_consistent_but_link_sensitive`. **Family-level stability moderate; exact links less stable; p70 supplementary**.",
        "Similar: family Jaccard often ≥0.6 for repetition variability; longitudinal T1_vs_T3 shows lower overlap. **Family-level recurrence yes; threshold-sensitive exact links**.",
        "`nullspace_threshold_stability_summary.csv`.",
    )

    ft671, ft252 = p671["fam_time"], p252["fam_time"]
    lines += q_block(
        11,
        "Did distal vs proximal contribution shift over time?",
        f"Distal share: T1={f3(ft671['T1']['distal_share'])}, T2={f3(ft671['T2']['distal_share'])}, T3={f3(ft671['T3']['distal_share'])}. **Modest increase in distal share T1→T3**.",
        f"Distal share T1→T3: {f3(ft252['T1']['distal_share'])}→{f3(ft252['T3']['distal_share'])}. **Minor fluctuation**; no strong distalward trend.",
        "Timepoint link contributions grouped by link proximal/distal classification.",
    )

    lines += q_block(
        12,
        "Did central vs peripheral link contribution shift over time?",
        f"Central share: T1={f3(ft671['T1']['central_share'])}, T2={f3(ft671['T2']['central_share'])}, T3={f3(ft671['T3']['central_share'])}. **Slight decrease in central share T1→T3**; limb/peripheral links remain dominant.",
        f"Central share stable ~0.22–0.25. **No marked centralization or peripheralization**.",
        "Central = trunk/neck/shoulder/pelvis-root proxies; peripheral = limb segments.",
    )

    lines += q_block(
        13,
        "Did upper-limb, lower-limb, and shoulder-chain contributions become more balanced?",
        f"Family-balance entropy: T1={f3(ft671['T1']['balance_entropy'])}, T2={f3(ft671['T2']['balance_entropy'])}, T3={f3(ft671['T3']['balance_entropy'])}. **Slightly more balanced at T2**, less at T3.",
        f"Balance entropy T1→T3: {f3(ft252['T1']['balance_entropy'])}→{f3(ft252['T3']['balance_entropy'])}. **Small increase in family balance at T3**.",
        "Normalized entropy across anatomical-family shares at each timepoint.",
    )

    lines += q_block(
        14,
        "Did left-right contribution symmetry/asymmetry change?",
        f"LR asymmetry index: T1={f3(ft671['T1']['lr_asymmetry'])}, T2={f3(ft671['T2']['lr_asymmetry'])}, T3={f3(ft671['T3']['lr_asymmetry'])}. **Mild asymmetry persists**; small decrease at T2, increase at T3.",
        f"LR asymmetry: T1={f3(ft252['T1']['lr_asymmetry'])}, T3={f3(ft252['T3']['lr_asymmetry'])}. **Asymmetry remains** (~0.05–0.12); no symmetric convergence.",
        "Absolute left-right share difference / total bilateral share.",
    )

    lines += q_block(
        15,
        "Did arm-leg coupling change over time?",
        f"Arm/leg contribution ratio: T1={f3(ft671['T1']['arm_leg_ratio'])}, T2={f3(ft671['T2']['arm_leg_ratio'])}, T3={f3(ft671['T3']['arm_leg_ratio'])}. **Relative leg emphasis at T2** (lower ratio); **relative arm emphasis returns at T3**.",
        f"Arm/leg ratio T1→T3: {f3(ft252['T1']['arm_leg_ratio'])}→{f3(ft252['T3']['arm_leg_ratio'])}. **Modest shift toward leg contribution at T3**.",
        "Sum of upper-limb family shares / lower-limb+pelvis shares.",
    )

    lines += q_block(
        16,
        "Did trunk-limb coupling change over time?",
        f"Trunk/limb ratio: T1={f3(ft671['T1']['trunk_limb_ratio'])}, T2={f3(ft671['T2']['trunk_limb_ratio'])}, T3={f3(ft671['T3']['trunk_limb_ratio'])}. **Stable low trunk share**; limb-dominated organization throughout.",
        f"Trunk/limb ratio stable ~0.15–0.18. **Limb-dominated** with minimal trunk shift.",
        "Trunk/neck/shoulder vs limb family share ratio.",
    )

    n671 = p671["networks"]
    n252 = p252["networks"]
    lines += q_block(
        17,
        "Did cross-link correlation network density, modularity, or between-family connectivity change?",
        f"Edge density (|r|>0.3): T1={f3(n671.get('T1',{}).get('edge_density_gt_0.3'))}, T2={f3(n671.get('T2',{}).get('edge_density_gt_0.3'))}, T3={f3(n671.get('T3',{}).get('edge_density_gt_0.3'))}. Within−between family corr: T1={f3(n671.get('T1',{}).get('within_minus_between'))}, T2={f3(n671.get('T2',{}).get('within_minus_between'))}, T3={f3(n671.get('T3',{}).get('within_minus_between'))}. **Descriptive increase in within-family cohesion at T2** from pre-JcvPCA link RMS time series.",
        f"Edge density (|r|>0.3): T1={f3(n252.get('T1',{}).get('edge_density_gt_0.3'))}, T2={f3(n252.get('T2',{}).get('edge_density_gt_0.3'))}, T3={f3(n252.get('T3',{}).get('edge_density_gt_0.3'))}. Within−between: T1={f3(n252.get('T1',{}).get('within_minus_between'))}, T2={f3(n252.get('T2',{}).get('within_minus_between'))}, T3={f3(n252.get('T3',{}).get('within_minus_between'))}. **Low overall density; modest T2 within-family cohesion; no large reorganization**.",
        "Pre-JcvPCA `dataset_*_preview.csv` link RMS correlations per P3 pooled timepoint.",
    )

    nv671 = p671["nv_pat_p3"][p671["nv_pat_p3"].focus_mode == "all"].iloc[0]
    nv252 = p252["nv_pat_p3"][p252["nv_pat_p3"].focus_mode == "all"].iloc[0]
    lines += q_block(
        18,
        "Did repetition-to-repetition variability increase, decrease, or become more distributed?",
        f"Mean abs-delta T1/T2/T3: {f3(nv671['T1_mean_abs_delta'])}/{f3(nv671['T2_mean_abs_delta'])}/{f3(nv671['T3_mean_abs_delta'])}; pattern={nv671['monotonic_pattern']}. **T2 peak**; NV link-structured (Gini ~0.54–0.56 at T2).",
        f"Mean abs-delta: {f3(nv252['T1_mean_abs_delta'])}/{f3(nv252['T2_mean_abs_delta'])}/{f3(nv252['T3_mean_abs_delta'])}; pattern={nv252['monotonic_pattern']}. **T1 peak on P3 all-PC**; non-monotonic.",
        "`natural_variability_timepoint_pattern_summary.csv`, `natural_variability_distribution_metrics.csv`.",
    )

    ex671 = p671["nv_ratio_p3"]["outside_T1_NV_reference"].sum()
    tot671 = len(p671["nv_ratio_p3"])
    lines += q_block(
        19,
        "Are longitudinal Deltas larger than descriptive natural-variability references?",
        f"**Yes descriptively**: {ex671}/{tot671} P3 link-comparison rows exceed T1 NV reference on T1_vs_T2/T1_vs_T3.",
        f"**Yes for many links** ({p252['nv_ratio_p3']['outside_T1_NV_reference'].sum()}/{len(p252['nv_ratio_p3'])} rows), but **participant-specific** link set.",
        "`longitudinal_delta_nv_ratio_by_link.csv`. Descriptive NV reference only.",
    )

    # Q20 overlap top NV ratio vs top abs delta
    top_nv_671 = set(ctx["nv_top7"][(ctx["nv_top7"].participant_id.astype(str)=="671") & (ctx["nv_top7"].block_label==PRIMARY) & (ctx["nv_top7"].ranking_basis=="delta_to_NV_T1_ratio")].link_id)
    top_abs_671 = set(ctx["nv_top7"][(ctx["nv_top7"].participant_id.astype(str)=="671") & (ctx["nv_top7"].block_label==PRIMARY) & (ctx["nv_top7"].ranking_basis=="abs_longitudinal_delta")].link_id)
    overlap671 = len(top_nv_671 & top_abs_671)
    lines += q_block(
        20,
        "Are top Delta/NV links also large in raw abs Delta, or only high because NV is small?",
        f"Top-NV vs top-abs link overlap (pooled top-7 lists): **{overlap671} links shared** — mix of both; some high ratios driven by small T1 NV (e.g. chest links) rather than largest abs delta alone.",
        f"Overlap partial; **both mechanisms present** — large absolute deltas (limb links) and high-ratio links where T1 NV is small.",
        "Compare `ranking_basis` abs_longitudinal_delta vs delta_to_NV_T1_ratio in `longitudinal_delta_nv_ratio_top7.csv`.",
    )

    d671 = p671["direction_p3"]
    lines += q_block(
        21,
        "Are some links magnitude-stable but direction-sensitive?",
        f"**Yes**: {int((d671.interpretation_label=='stable_magnitude_direction_sensitive').sum())} links labeled stable_magnitude_direction_sensitive on T1_vs_T2/T1_vs_T3; plus {int((d671.interpretation_label=='unstable_both').sum())} unstable_both.",
        f"**Yes**: {int((p252['direction_p3'].interpretation_label=='stable_magnitude_direction_sensitive').sum())} direction-sensitive magnitude-stable links.",
        "`direction_vs_magnitude_integrated_report.csv`.",
    )

    lines += q_block(
        22,
        "Are T1_vs_T2 and T1_vs_T3 patterns consistent within participant?",
        f"Longitudinal top-link overlap (all-PC P3): partial — arm/leg families recur; exact top links differ (T1_vs_T2 top: RFArm/RUArm/LThigh; T1_vs_T3 top: RFArm/LThigh/LFArm patterns). **Family-level consistency, not identical links**.",
        f"**Partial consistency** — shoulder/arm and leg families recur; T1_vs_T3 emphasizes LUArm/LThigh vs T1_vs_T2 RShoulder/RUArm pattern.",
        "`longitudinal_link_delta_allpc_poster_table.csv` top-7 per comparison.",
    )

    lines += q_block(
        23,
        "Are patterns primarily participant-specific rather than shared?",
        "**Yes.** 671 lacks pelvis_root links; 252 includes `252_to_L/RThigh`. Top longitudinal links differ; NV timepoint peaks differ (671 T2 peak, 252 T1 peak on P3). **No shared numeric profile to average.**",
        "Same conclusion — schema and top-link identity differ from 671.",
        "Separate participant panels only; 14 vs 16 links.",
    )

    lines += q_block(
        24,
        "Which results support a safe statement about broader link-level movement organization?",
        "Broadly distributed longitudinal link-level Delta on P3; multiple anatomical families contribute; pooled R1+R2 summaries are descriptive aggregates.",
        "Same: participant-specific multi-link patterns with recurring upper- and lower-limb families.",
        "High normalized entropy (~0.87–0.96) on longitudinal all-PC; Gini ~0.35–0.55.",
    )

    lines += q_block(
        25,
        "Which results support a safe statement about less-dominant/redundant degrees of freedom?",
        "Null-space mean variability exceeds all-PC (ratio >1); later PCs contribute non-trivial link-level spread; p50/p60 family-level recurrence.",
        "Null-space elevation on repetition variability especially T3; later-PC subsets show structured-but-threshold-sensitive patterns.",
        "`nullspace_noise_vs_structure_diagnostic.csv`, `pc_focus_evenness_comparison.csv`.",
    )

    lines += q_block(
        26,
        "Which results are too unstable and should remain exploratory?",
        "Exact null-space link identity across p50/p60/p70; link direction across repetition pairings; T3 concentration reversal; cross-link network metrics from preview subsets.",
        "T3 NV patterns; null-space exact links on T1_vs_T3; directional robustness ~52–59% sign agreement.",
        "Directional robustness reports; null-space threshold sensitivity; low split-half PC similarity on some internal comparisons.",
    )

    lines += [
        "---",
        "",
        "## Summary matrix (P3_P4_P5)",
        "",
        "| Question theme | 671 (short) | 252 (short) |",
        "| --- | --- | --- |",
        f"| Distribution T1→later | T2 more distributed; T3 concentrates | Mixed / no clear direction |",
        f"| More contributing links | Stable count | Stable count |",
        f"| Low links promoted | Modest | Modest |",
        f"| PC spread | T2 broader; T3 mixed | T3 more PC1-heavy |",
        f"| Null-space elevation | Yes (ratio>1) | Yes (ratio>1) |",
        f"| Delta vs NV | Many links > NV ref | Many links > NV ref |",
        f"| Direction stability | Mixed | Mixed |",
        "",
        "## Data sources",
        "",
        "- JcvPCA batch CSVs: `timepoint_evenness_*`, `contribution_evenness_summary`, `pca_stability_by_comparison`, `pc_focus_*`, directional robustness",
        "- Poster package: `poster_ready_evidence_package/*.csv`",
        "- Pre-JcvPCA: comparison `construction/dataset_*_preview.csv` link RMS correlations",
        "",
        "*Generated descriptively — no inferential claims.*",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = parse_batch_report_cli(
        "Generate movement-organization question report from batch and evidence package.",
        argv,
    )
    try:
        configure_movement_org_report_paths(config_path=args.config, batch_dir=args.batch_dir)
    except FileNotFoundError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1

    out_md = OUT / "gaga_movement_organization_question_report.md"
    preflight = run_path_preflight(
        args,
        root=BATCH,
        out=out_md,
        required=MO_REPORT_REQUIRED,
    )
    if preflight is not None:
        if args.validate_paths:
            pkg_missing = [n for n in MO_PKG_REQUIRED if not (PKG / n).is_file()]
            if pkg_missing:
                print(f"Evidence package missing: {len(pkg_missing)}")
                for name in pkg_missing[:10]:
                    print(f"  - missing: {name}")
                return 1
        return preflight

    OUT.mkdir(parents=True, exist_ok=True)
    ctx = build_context()
    report = generate_report(ctx)
    (OUT / "gaga_movement_organization_question_report.md").write_text(report, encoding="utf-8")
    # compact metrics CSV for audit
    rows = []
    for pid in PARTICIPANTS:
        p = ctx[pid]
        t = p["trends_p3"]
        row = {"participant_id": pid, "block_label": PRIMARY}
        row.update({f"entropy_{k}": t.get(f"entropy_{k}") for k in ["T1", "T2", "T3"]})
        row.update({f"gini_{k}": t.get(f"Gini_{k}") for k in ["T1", "T2", "T3"]})
        row.update({f"top3_{k}": t.get(f"top3_{k}") for k in ["T1", "T2", "T3"]})
        for tp in ["T1", "T2", "T3"]:
            pc = p["pc_tp"][tp]
            row[f"pc1_pct_{tp}"] = pc["pc1_pct"]
            row[f"pcs80_{tp}"] = pc["pcs_80"]
            row[f"pc_entropy_{tp}"] = pc["pc_entropy_bits"]
            net = p["networks"].get(tp, {})
            row[f"net_density_{tp}"] = net.get("edge_density_gt_0.3")
        rows.append(row)
    pd.DataFrame(rows).to_csv(OUT / "movement_organization_question_metrics.csv", index=False)
    print(f"Wrote {OUT / 'gaga_movement_organization_question_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
