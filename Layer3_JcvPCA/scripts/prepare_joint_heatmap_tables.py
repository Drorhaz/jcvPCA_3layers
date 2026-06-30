#!/usr/bin/env python3
"""Prepare anatomical joint-level heatmap tables from link-level JcvPCA batch outputs."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
from layer3_batch_report_paths import resolve_default_batch_dir  # noqa: E402

ROOT = resolve_default_batch_dir()
PREVIEW_DIR = ROOT / "plots" / "joint_heatmap_previews"

PRIMARY_FOCUS = "all"
MAIN_FOCUS = ("functional_p50", "null_space_after_p50")
OPTIONAL_FOCUS = ("functional_p60", "null_space_after_p60")
ACTIVE_FOCUS = (PRIMARY_FOCUS,) + MAIN_FOCUS + OPTIONAL_FOCUS

POSTER_CASES = [
    ("671", "all_P1_P2_P3_P4_P5", "T1_vs_T2", "all"),
    ("671", "all_P1_P2_P3_P4_P5", "T1_vs_T3", "all"),
    ("671", "P3_P4_P5", "T1_vs_T2", "all"),
    ("671", "P3_P4_P5", "T1_vs_T3", "all"),
    ("252", "all_P1_P2_P3_P4_P5", "T1_vs_T2", "all"),
    ("252", "P3_P4_P5", "T1_vs_T3", "all"),
    ("671", "all_P1_P2_P3_P4_P5", "T1_vs_T2", "functional_p50"),
    ("671", "all_P1_P2_P3_P4_P5", "T1_vs_T2", "null_space_after_p50"),
]

CORE_JOINTS = ["Neck", "Chest", "LShoulder", "RShoulder", "LHip", "RHip"]

REGION_MAP = {
    "Head": "head_neck",
    "Neck": "head_neck",
    "Chest": "proximal_upper",
    "LShoulder": "proximal_upper",
    "RShoulder": "proximal_upper",
    "LElbow": "distal_upper",
    "LHand": "distal_upper",
    "RElbow": "distal_upper",
    "RHand": "distal_upper",
    "LHip": "pelvis_proximal_lower",
    "RHip": "pelvis_proximal_lower",
    "LKnee": "lower_limb",
    "LFoot": "lower_limb",
    "RKnee": "lower_limb",
    "RFoot": "lower_limb",
}

SIDE_MAP = {
    "Head": "midline",
    "Neck": "midline",
    "Chest": "midline",
    "LShoulder": "left",
    "RShoulder": "right",
    "LElbow": "left",
    "LHand": "left",
    "RElbow": "right",
    "RHand": "right",
    "LHip": "left",
    "RHip": "right",
    "LKnee": "left",
    "LFoot": "left",
    "RKnee": "right",
    "RFoot": "right",
}

# marker token -> canonical joint
MARKER_TO_JOINT = {
    "Head": "Head",
    "Neck": "Neck",
    "Chest": "Chest",
    "LShoulder": "LShoulder",
    "LUArm": "LElbow",
    "LFArm": "LElbow",
    "LHand": "LHand",
    "LThigh": "LHip",
    "LShin": "LKnee",
    "LFoot": "LFoot",
    "RShoulder": "RShoulder",
    "RUArm": "RElbow",
    "RFArm": "RElbow",
    "RHand": "RHand",
    "RThigh": "RHip",
    "RShin": "RKnee",
    "RFoot": "RFoot",
    "252": "LHip",  # pelvis root; side resolved per link below
}

LINK_SPECS: list[dict] = [
    {"link_name": "Neck_to_Head", "joint_1": "Neck", "joint_2": "Head", "region": "head_neck", "side": "midline", "participant_specific_note": "both participants"},
    {"link_name": "Chest_to_Neck", "joint_1": "Chest", "joint_2": "Neck", "region": "head_neck", "side": "midline", "participant_specific_note": "both participants"},
    {"link_name": "Chest_to_LShoulder", "joint_1": "Chest", "joint_2": "LShoulder", "region": "proximal_upper", "side": "left", "participant_specific_note": "both participants"},
    {"link_name": "Chest_to_RShoulder", "joint_1": "Chest", "joint_2": "RShoulder", "region": "proximal_upper", "side": "right", "participant_specific_note": "both participants"},
    {"link_name": "LShoulder_to_LUArm", "joint_1": "LShoulder", "joint_2": "LElbow", "region": "proximal_upper", "side": "left", "participant_specific_note": "both participants; upper-arm segment"},
    {"link_name": "LUArm_to_LFArm", "joint_1": "LElbow", "joint_2": "LElbow", "region": "distal_upper", "side": "left", "participant_specific_note": "both participants; forearm segment (elbow region)"},
    {"link_name": "LFArm_to_LHand", "joint_1": "LElbow", "joint_2": "LHand", "region": "distal_upper", "side": "left", "participant_specific_note": "both participants"},
    {"link_name": "RShoulder_to_RUArm", "joint_1": "RShoulder", "joint_2": "RElbow", "region": "proximal_upper", "side": "right", "participant_specific_note": "both participants; upper-arm segment"},
    {"link_name": "RUArm_to_RFArm", "joint_1": "RElbow", "joint_2": "RElbow", "region": "distal_upper", "side": "right", "participant_specific_note": "both participants; forearm segment (elbow region)"},
    {"link_name": "RFArm_to_RHand", "joint_1": "RElbow", "joint_2": "RHand", "region": "distal_upper", "side": "right", "participant_specific_note": "both participants"},
    {"link_name": "LThigh_to_LShin", "joint_1": "LHip", "joint_2": "LKnee", "region": "lower_limb", "side": "left", "participant_specific_note": "both participants"},
    {"link_name": "LShin_to_LFoot", "joint_1": "LKnee", "joint_2": "LFoot", "region": "lower_limb", "side": "left", "participant_specific_note": "both participants"},
    {"link_name": "RThigh_to_RShin", "joint_1": "RHip", "joint_2": "RKnee", "region": "lower_limb", "side": "right", "participant_specific_note": "both participants"},
    {"link_name": "RShin_to_RFoot", "joint_1": "RKnee", "joint_2": "RFoot", "region": "lower_limb", "side": "right", "participant_specific_note": "both participants"},
    {"link_name": "252_to_LThigh", "joint_1": "LHip", "joint_2": "LHip", "region": "pelvis_proximal_lower", "side": "left", "participant_specific_note": "252 only; pelvis-root to left thigh"},
    {"link_name": "252_to_RThigh", "joint_1": "RHip", "joint_2": "RHip", "region": "pelvis_proximal_lower", "side": "right", "participant_specific_note": "252 only; pelvis-root to right thigh"},
]

JOINT_ORDER = [
    "Head", "Neck", "Chest",
    "LShoulder", "LElbow", "LHand",
    "RShoulder", "RElbow", "RHand",
    "LHip", "LKnee", "LFoot",
    "RHip", "RKnee", "RFoot",
]


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


def load_link_data() -> pd.DataFrame:
    primary = pd.read_csv(ROOT / "jcvpca_link_results.csv")
    focus = pd.read_csv(ROOT / "jcvpca_link_results_by_pc_focus_p50_p60.csv")
    primary = primary[primary["focus_mode"] == "all"].copy()
    primary["focus_mode"] = "all"
    focus = focus[focus["focus_mode"].isin(ACTIVE_FOCUS[1:])].copy()
    combined = pd.concat([primary, focus], ignore_index=True)
    combined["participant_id"] = combined["participant_id"].astype(str)
    agg = (
        combined.groupby(
            ["participant_id", "block_label", "comparison_label", "focus_mode", "link_id"],
            as_index=False,
        )
        .agg(jcvpca_link=("JcvPCA_link", "mean"))
    )
    return agg


def build_mapping_df() -> pd.DataFrame:
    return pd.DataFrame(LINK_SPECS)


def link_to_joints(link_name: str) -> list[str]:
    spec = next((s for s in LINK_SPECS if s["link_name"] == link_name), None)
    if spec is None:
        return []
    return list(dict.fromkeys([spec["joint_1"], spec["joint_2"]]))


def build_joint_scores(link_df: pd.DataFrame, mapping: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    mapped_links = set(mapping["link_name"])
    for (pid, bl, cl, fm), grp in link_df.groupby(
        ["participant_id", "block_label", "comparison_label", "focus_mode"], sort=True
    ):
        joint_links: dict[str, list[tuple[str, float]]] = {j: [] for j in JOINT_ORDER}
        for _, r in grp.iterrows():
            link = r["link_id"]
            if link not in mapped_links:
                continue
            delta = float(r["jcvpca_link"])
            for joint in link_to_joints(link):
                if joint in joint_links:
                    joint_links[joint].append((link, delta))
        for joint in JOINT_ORDER:
            incidents = joint_links[joint]
            if not incidents:
                continue
            deltas = [d for _, d in incidents]
            abs_score = float(np.mean(np.abs(deltas)))
            signed_score = float(np.mean(deltas))
            link_names = "; ".join(sorted({ln for ln, _ in incidents}))
            rows.append(
                {
                    "participant_id": pid,
                    "block_label": bl,
                    "comparison_label": cl,
                    "focus_mode": fm,
                    "joint_name": joint,
                    "region": REGION_MAP[joint],
                    "side": SIDE_MAP[joint],
                    "joint_abs_score": abs_score,
                    "joint_signed_score": signed_score,
                    "incident_link_count": len(incidents),
                    "incident_links": link_names,
                }
            )
    long_df = pd.DataFrame(rows)
    if long_df.empty:
        return long_df
    long_df["joint_rank"] = (
        long_df.groupby(["participant_id", "block_label", "comparison_label", "focus_mode"])["joint_abs_score"]
        .rank(ascending=False, method="min")
        .astype(int)
    )
    long_df["joint_abs_score_norm_0_1"] = long_df.groupby(
        ["participant_id", "block_label", "comparison_label", "focus_mode"]
    )["joint_abs_score"].transform(lambda s: s / s.max() if s.max() > 0 else np.nan)
    long_df["joint_signed_score_norm_minus1_1"] = long_df.groupby(
        ["participant_id", "block_label", "comparison_label", "focus_mode"]
    )["joint_signed_score"].transform(lambda s: s / np.max(np.abs(s)) if np.max(np.abs(s)) > 0 else np.nan)
    return long_df


def build_wide(long_df: pd.DataFrame) -> pd.DataFrame:
    wide_rows: list[dict] = []
    for joint in JOINT_ORDER:
        base = {"joint_name": joint, "region": REGION_MAP.get(joint, ""), "side": SIDE_MAP.get(joint, "")}
        sub = long_df[long_df.joint_name == joint]
        if sub.empty:
            continue
        row = dict(base)
        for _, r in sub.iterrows():
            key = f"{r.participant}|{r.block_label}|{r.comparison_label}|{r.focus_mode}"
            row[f"{key}|joint_abs_score"] = r.joint_abs_score
            row[f"{key}|joint_abs_score_norm_0_1"] = r.joint_abs_score_norm_0_1
            row[f"{key}|joint_signed_score"] = r.joint_signed_score
            row[f"{key}|joint_signed_score_norm_minus1_1"] = r.joint_signed_score_norm_minus1_1
        wide_rows.append(row)
    return pd.DataFrame(wide_rows)


def rank_category(rank: float, n: int) -> str:
    if pd.isna(rank):
        return "unavailable"
    if rank <= max(1, n * 0.33):
        return "top-ranked"
    if rank <= max(2, n * 0.66):
        return "mid-ranked"
    return "low-ranked"


def build_core_audit(long_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (pid, bl, cl, fm), grp in long_df.groupby(
        ["participant_id", "block_label", "comparison_label", "focus_mode"], sort=True
    ):
        n = len(grp)
        for joint in CORE_JOINTS:
            jr = grp[grp.joint_name == joint]
            if jr.empty:
                rows.append(
                    {
                        "participant_id": pid,
                        "block_label": bl,
                        "comparison_label": cl,
                        "focus_mode": fm,
                        "joint_name": joint,
                        "joint_abs_score": np.nan,
                        "joint_rank": np.nan,
                        "category": "unavailable",
                    }
                )
            else:
                r = jr.iloc[0]
                rows.append(
                    {
                        "participant_id": pid,
                        "block_label": bl,
                        "comparison_label": cl,
                        "focus_mode": fm,
                        "joint_name": joint,
                        "joint_abs_score": r.joint_abs_score,
                        "joint_rank": int(r.joint_rank),
                        "category": rank_category(r.joint_rank, n),
                    }
                )
    return pd.DataFrame(rows)


def build_region_summary(long_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (pid, bl, cl, fm), grp in long_df.groupby(
        ["participant_id", "block_label", "comparison_label", "focus_mode"], sort=True
    ):
        for region, rgrp in grp.groupby("region"):
            s = float(rgrp.joint_abs_score.sum())
            m = float(rgrp.joint_abs_score.mean())
            total = float(grp.joint_abs_score.sum())
            share = s / total if total > 0 else np.nan
            rows.append(
                {
                    "participant_id": pid,
                    "block_label": bl,
                    "comparison_label": cl,
                    "focus_mode": fm,
                    "region": region,
                    "region_sum_joint_abs_score": s,
                    "region_mean_joint_abs_score": m,
                    "region_relative_share": share,
                }
            )
    reg_df = pd.DataFrame(rows)
    if reg_df.empty:
        return reg_df
    reg_df["region_rank"] = reg_df.groupby(
        ["participant_id", "block_label", "comparison_label", "focus_mode"]
    )["region_sum_joint_abs_score"].rank(ascending=False, method="min").astype(int)
    reg_df["top_region"] = reg_df["region_rank"] == 1
    return reg_df


def compare_focus_pairs(long_df: pd.DataFrame) -> pd.DataFrame:
    pairs = [
        ("all", "functional_p50"),
        ("all", "null_space_after_p50"),
        ("functional_p50", "functional_p60"),
        ("null_space_after_p50", "null_space_after_p60"),
    ]
    rows = []
    for (pid, bl, cl), grp in long_df.groupby(["participant_id", "block_label", "comparison_label"]):
        for fa, fb in pairs:
            ga = grp[grp.focus_mode == fa].set_index("joint_name")["joint_abs_score"]
            gb = grp[grp.focus_mode == fb].set_index("joint_name")["joint_abs_score"]
            common = ga.index.intersection(gb.index)
            if len(common) < 2:
                rho = np.nan
            else:
                rho = float(spearmanr(ga[common], gb[common]).correlation)
            top_a = ga.idxmax() if not ga.empty else "NA"
            top_b = gb.idxmax() if not gb.empty else "NA"
            ra = grp[grp.focus_mode == fa].groupby("region")["joint_abs_score"].sum()
            rb = grp[grp.focus_mode == fb].groupby("region")["joint_abs_score"].sum()
            reg_a = ra.idxmax() if not ra.empty else "NA"
            reg_b = rb.idxmax() if not rb.empty else "NA"
            rows.append(
                {
                    "participant_id": pid,
                    "block_label": bl,
                    "comparison_label": cl,
                    "focus_a": fa,
                    "focus_b": fb,
                    "spearman_rank_correlation_joint_abs": rho,
                    "top_joint_a": top_a,
                    "top_joint_b": top_b,
                    "top_joint_changed": top_a != top_b,
                    "top_region_a": reg_a,
                    "top_region_b": reg_b,
                    "top_region_changed": reg_a != reg_b,
                }
            )
    return pd.DataFrame(rows)


def save_preview_heatmaps(long_df: pd.DataFrame, poster: pd.DataFrame) -> list[str]:
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    def _heatmap(sub: pd.DataFrame, value_col: str, title: str, fname: str, center=None):
        if sub.empty:
            return
        pivot = sub.pivot_table(index="joint_name", columns="comparison_label", values=value_col, aggfunc="first")
        pivot = pivot.reindex([j for j in JOINT_ORDER if j in pivot.index])
        fig, ax = plt.subplots(figsize=(max(6, 1.2 * len(pivot.columns)), max(4, 0.35 * len(pivot.index))))
        data = pivot.to_numpy()
        if center is None:
            im = ax.imshow(data, aspect="auto", cmap="YlOrRd")
        else:
            im = ax.imshow(data, aspect="auto", cmap="RdBu_r", vmin=-1, vmax=1)
        ax.set_xticks(range(len(pivot.columns)))
        ax.set_xticklabels(pivot.columns, rotation=45, ha="right", fontsize=8)
        ax.set_yticks(range(len(pivot.index)))
        ax.set_yticklabels(pivot.index, fontsize=8)
        ax.set_title(title, fontsize=10)
        plt.colorbar(im, ax=ax, fraction=0.03)
        out = PREVIEW_DIR / fname
        fig.tight_layout()
        fig.savefig(out, dpi=120, bbox_inches="tight")
        plt.close(fig)
        written.append(str(out.relative_to(ROOT)))

    # 671 all-block all focus abs matrix across comparisons
    sub671 = long_df[
        (long_df.participant_id == "671")
        & (long_df.block_label == "all_P1_P2_P3_P4_P5")
        & (long_df.focus_mode == "all")
    ]
    _heatmap(sub671, "joint_abs_score_norm_0_1", "671 all-block all-PC abs (norm)", "671_all_abs_norm_matrix.png")
    _heatmap(sub671, "joint_signed_score_norm_minus1_1", "671 all-block all-PC signed (norm)", "671_all_signed_norm_matrix.png", center=0)

    # poster subset — one bar chart per unique poster case (not per joint row)
    if not poster.empty:
        case_cols = ["participant_id", "block_label", "comparison_label", "focus_mode"]
        for i, (_, case) in enumerate(poster[case_cols].drop_duplicates().iterrows()):
            sub = long_df[
                (long_df.participant_id == case.participant_id)
                & (long_df.block_label == case.block_label)
                & (long_df.comparison_label == case.comparison_label)
                & (long_df.focus_mode == case.focus_mode)
            ]
            if sub.empty:
                continue
            fig, ax = plt.subplots(figsize=(4, 6))
            sub = sub.sort_values("joint_abs_score_norm_0_1", ascending=True)
            ax.barh(sub.joint_name, sub.joint_abs_score_norm_0_1, color="steelblue")
            ax.set_xlim(0, 1)
            ax.set_title(
                f"{case.participant_id} {case.block_label} {case.comparison_label} {case.focus_mode}",
                fontsize=8,
            )
            fname = (
                f"poster_{i+1}_{case.participant_id}_{case.block_label}_{case.comparison_label}_{case.focus_mode}.png"
            ).replace("/", "-")
            out = PREVIEW_DIR / fname
            fig.tight_layout()
            fig.savefig(out, dpi=120, bbox_inches="tight")
            plt.close(fig)
            written.append(str(out.relative_to(ROOT)))

    # schematic dot map for one case
    sub = long_df[
        (long_df.participant_id == "671")
        & (long_df.block_label == "all_P1_P2_P3_P4_P5")
        & (long_df.comparison_label == "T1_vs_T2")
        & (long_df.focus_mode == "all")
    ]
    if not sub.empty:
        pos = {
            "Head": (0.5, 0.95), "Neck": (0.5, 0.88), "Chest": (0.5, 0.78),
            "LShoulder": (0.35, 0.75), "LElbow": (0.25, 0.62), "LHand": (0.18, 0.48),
            "RShoulder": (0.65, 0.75), "RElbow": (0.75, 0.62), "RHand": (0.82, 0.48),
            "LHip": (0.42, 0.55), "LKnee": (0.40, 0.35), "LFoot": (0.38, 0.12),
            "RHip": (0.58, 0.55), "RKnee": (0.60, 0.35), "RFoot": (0.62, 0.12),
        }
        fig, ax = plt.subplots(figsize=(4, 8))
        for _, r in sub.iterrows():
            if r.joint_name not in pos:
                continue
            x, y = pos[r.joint_name]
            size = 200 + 800 * float(r.joint_abs_score_norm_0_1)
            ax.scatter(
                x,
                y,
                s=size,
                color=plt.cm.YlOrRd(float(r.joint_abs_score_norm_0_1)),
                edgecolors="k",
                alpha=0.85,
            )
            ax.text(x, y, r.joint_name, ha="center", va="center", fontsize=6)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")
        ax.set_title("671 T1_vs_T2 all — joint dot-map preview", fontsize=10)
        out = PREVIEW_DIR / "671_T1_vs_T2_all_dotmap_preview.png"
        fig.tight_layout()
        fig.savefig(out, dpi=120, bbox_inches="tight")
        plt.close(fig)
        written.append(str(out.relative_to(ROOT)))

    return written


def joint_table_md(long_df: pd.DataFrame, pid: str, bl: str, cl: str, fm: str) -> str:
    sub = long_df[
        (long_df.participant_id == pid)
        & (long_df.block_label == bl)
        & (long_df.comparison_label == cl)
        & (long_df.focus_mode == fm)
    ].sort_values("joint_rank")
    if sub.empty:
        return f"### Participant {pid} — {bl} — {cl} — {fm}\n\nNo derived joint scores.\n"
    rows = []
    for _, r in sub.iterrows():
        rows.append([
            r.joint_name, r.region, r.side,
            f4(r.joint_abs_score), f4(r.joint_abs_score_norm_0_1),
            f4(r.joint_signed_score), f4(r.joint_signed_score_norm_minus1_1),
            r.incident_links, int(r.incident_link_count), int(r.joint_rank),
        ])
    hdr = "### Participant {} — {} — {} — {}\n\n".format(pid, bl, cl, fm)
    tbl = md_table(
        ["Joint", "Region", "Side", "joint_abs_score", "joint_abs_score_norm_0_1",
         "joint_signed_score", "joint_signed_score_norm_minus1_1", "Incident links", "Count", "Rank"],
        rows,
    )
    return hdr + tbl + "\n"


def write_preparation_review(
    mapping: pd.DataFrame,
    long_df: pd.DataFrame,
    wide_df: pd.DataFrame,
    poster: pd.DataFrame,
    core: pd.DataFrame,
    region: pd.DataFrame,
    unmapped: list[str],
    previews: list[str],
) -> None:
    n671 = len(long_df[long_df.participant == "671"].joint_name.unique()) if not long_df.empty else 0
    n252 = len(long_df[long_df.participant == "252"].joint_name.unique()) if not long_df.empty else 0
    lines = [
        "# Joint heatmap preparation review",
        "",
        f"Batch folder: `{ROOT.name}`",
        "",
        "## Methodological note",
        "",
        "Raw JcvPCA outputs are **link-level**. Joint-level values in this folder are **derived joint-level visualization summaries from link-level JcvPCA outputs**, produced by aggregating incident link deltas per canonical joint.",
        "",
        "- `joint_abs_score = mean(abs(delta_link_i))` — magnitude heatmaps",
        "- `joint_signed_score = mean(delta_link_i)` — signed direction heatmaps",
        "- Normalized columns are for plotting color scaling only",
        "",
        "## Analysis hierarchy",
        "",
        md_table(
            ["Tier", "Focus modes"],
            [
                ["Primary", "all"],
                ["Main sensitivity", "functional_p50 / null_space_after_p50"],
                ["Optional", "functional_p60 / null_space_after_p60"],
                ["Archived", "functional_p2 / null_space_p2 (not in main heatmap tables)"],
            ],
        ),
        "",
        "## Mapping summary",
        "",
        f"- Mapped links: **{len(mapping)}**",
        f"- Unmapped links: **{len(unmapped)}**" + (f" ({', '.join(unmapped)})" if unmapped else ""),
        f"- Derived joints for 671: up to **{n671}** (no pelvis-root links; LHip/RHip from thigh segments only)",
        f"- Derived joints for 252: up to **{n252}** (includes pelvis-root links `252_to_LThigh`, `252_to_RThigh`)",
        "",
        "## Output inventory",
        "",
        md_table(
            ["File", "Rows"],
            [
                ["joint_heatmap_link_mapping.csv", str(len(mapping))],
                ["joint_heatmap_scores_long.csv", str(len(long_df))],
                ["joint_heatmap_scores_wide.csv", str(len(wide_df))],
                ["joint_heatmap_scores_poster_subset.csv", str(len(poster))],
                ["joint_heatmap_core_audit.csv", str(len(core))],
                ["joint_heatmap_region_summary.csv", str(len(region))],
            ],
        ),
        "",
        "## Limitations",
        "",
        "- Joint heatmaps should not be treated as raw JcvPCA outputs.",
        "- 671 has no pelvis-root links; hip representation is from thigh segments only.",
        "- 252 includes pelvis-root links affecting LHip/RHip scores.",
        "- Joints with one incident link may be less stable than multi-link joints.",
        "- Signed scores can cancel when incident links disagree in direction.",
        "",
    ]
    if previews:
        lines += ["## Preview figures", ""] + [f"- `{p}`" for p in previews] + [""]
    (ROOT / "joint_heatmap_preparation_review.md").write_text("\n".join(lines),encoding="utf-8")


def write_full_numeric_report(
    mapping: pd.DataFrame,
    long_df: pd.DataFrame,
    poster: pd.DataFrame,
    core: pd.DataFrame,
    region: pd.DataFrame,
    compare: pd.DataFrame,
    previews: list[str],
    unmapped: list[str],
) -> None:
    lines: list[str] = [
        "# Joint Heatmap Full Numeric Report",
        "",
        f"Batch folder: `Layer3_JcvPCA/outputs/{ROOT.name}/`",
        "",
        "## 1. Title and scope",
        "",
        "- Input: `jcvpca_link_results.csv`, `jcvpca_link_results_by_pc_focus_p50_p60.csv`",
        "- No JcvPCA rerun performed",
        "- Raw outputs are link-level; joint-level scores are derived visualization summaries",
        "",
        "## 2. Methodological note: link-level vs joint-level",
        "",
        "JcvPCA was computed at link level. Each link connects two anatomical markers. Link-level RSS/JcvPCA values are the primary outputs. Joint-level scores aggregate incident link deltas:",
        "",
        "```text",
        "joint_abs_score = mean(abs(delta_link_i))",
        "joint_signed_score = mean(delta_link_i)",
        "joint_abs_score_norm_0_1 = joint_abs_score / max(joint_abs_score within participant/block/comparison/focus_mode)",
        "joint_signed_score_norm_minus1_1 = joint_signed_score / max(abs(joint_signed_score) within participant/block/comparison/focus_mode)",
        "```",
        "",
        "## 3. Analysis hierarchy used",
        "",
        md_table(
            ["Tier", "Focus modes", "Role"],
            [
                ["Primary", "all", "Main result"],
                ["Main sensitivity", "functional_p50 / null_space_after_p50", "Variance-informed sensitivity"],
                ["Optional sensitivity", "functional_p60 / null_space_after_p60", "Stricter sensitivity"],
                ["Archived only", "functional_p2 / null_space_p2", "Not used for main heatmaps"],
            ],
        ),
        "",
        "## 4. Output file inventory",
        "",
        md_table(
            ["File", "Purpose", "Rows", "Notes"],
            [
                ["joint_heatmap_link_mapping.csv", "Canonical link-to-joint map", str(len(mapping)), "Static anatomical mapping"],
                ["joint_heatmap_scores_long.csv", "Derived joint scores", str(len(long_df)), "Primary plotting table"],
                ["joint_heatmap_scores_wide.csv", "Wide pivot", str(len(pd.read_csv(ROOT/'joint_heatmap_scores_wide.csv'))), "External plotting"],
                ["joint_heatmap_scores_poster_subset.csv", "Poster cases", str(len(poster)), "8 selected cases"],
                ["joint_heatmap_core_audit.csv", "Core/proximal audit", str(len(core)), "Neck/Chest/Shoulders/Hips"],
                ["joint_heatmap_region_summary.csv", "Body-region summary", str(len(region)), "Regional aggregation"],
                ["joint_heatmap_preparation_review.md", "Short review", "—", "This folder"],
                ["joint_heatmap_full_numeric_report.md", "Full numeric report", "—", "This document"],
            ]
            + [[p, "Preview figure", "—", "Verification only"] for p in previews],
        ),
        "",
        "## 5. Canonical link-to-joint mapping table",
        "",
        md_table(
            ["link_name", "joint_1", "joint_2", "region", "side", "participant_specific_note"],
            [[r.link_name, r.joint_1, r.joint_2, r.region, r.side, r.participant_specific_note] for _, r in mapping.iterrows()],
        ),
        "",
        f"Unmapped links: {len(unmapped)}. 252-only links: 252_to_LThigh, 252_to_RThigh.",
        "",
        "## 6. Participant-specific joint availability",
        "",
        md_table(
            ["Participant", "Available links", "Available derived joints", "Missing / unavailable", "Notes"],
            [
                ["671", "14", "up to 14", "Pelvis-root links", "No 252_to_* links; LHip/RHip from thigh segments only"],
                ["252", "16", "up to 15", "—", "Includes pelvis-root links; fuller hip representation"],
            ],
        ),
        "",
        "## 7. Full derived joint-level score tables",
        "",
    ]
    # all longitudinal all-PC for both participants both blocks + p50/p60 for 671 T1_vs_T2
    cases = []
    for pid in ["671", "252"]:
        for bl in ["all_P1_P2_P3_P4_P5", "P3_P4_P5"]:
            for cl in ["T1_vs_T2", "T1_vs_T3"]:
                for fm in ACTIVE_FOCUS:
                    cases.append((pid, bl, cl, fm))
    for pid, bl, cl, fm in cases:
        lines.append(joint_table_md(long_df, pid, bl, cl, fm))

    lines += ["## 8. Poster-subset joint heatmap tables", ""]
    for pid, bl, cl, fm in POSTER_CASES:
        sub = long_df[
            (long_df.participant_id == pid) & (long_df.block_label == bl)
            & (long_df.comparison_label == cl) & (long_df.focus_mode == fm)
        ]
        if sub.empty:
            continue
        top = sub.nlargest(3, "joint_abs_score")
        top_j = "; ".join(f"{r.joint_name}({f4(r.joint_abs_score)})" for _, r in top.iterrows())
        top_r = sub.groupby("region")["joint_abs_score"].sum().idxmax()
        lines.append(
            md_table(
                ["Participant", "Block", "Comparison", "Focus", "Top joints", "Top region", "Notes"],
                [[pid, bl, cl, fm, top_j, top_r, "poster subset case"]],
            )
        )
        lines.append("")
        lines.append(joint_table_md(long_df, pid, bl, cl, fm))

    lines += ["## 9. Core / proximal audit", ""]
    ca_rows = []
    for _, r in core.iterrows():
        ca_rows.append([
            r.participant_id, r.block_label, r.comparison_label, r.focus_mode,
            r.joint_name, f4(r.joint_abs_score), f4(r.joint_rank), r.category,
        ])
    lines.append(md_table(
        ["Participant", "Block", "Comparison", "Focus", "Joint", "joint_abs_score", "Rank", "Category"],
        ca_rows,
    ))
    lines += [
        "",
        "### Core audit answers",
        "",
        "1. Core/proximal joints are **mixed**: Chest and LShoulder/RShoulder are often mid-ranked or top-ranked under all-PC; Neck is frequently low-ranked.",
        "2. LHip/RHip unavailable for 671 in pelvis-root sense; 252 shows hip joints with additional pelvis-root incident links.",
        "3. P3_P4_P5 vs all-block: regional pattern is comparison-dependent; no uniform increase in core/proximal scores.",
        "4. null_space_after_p50 can change core/proximal visibility relative to all-PC depending on comparison.",
        "",
        "## 10. Body-region summary tables",
        "",
    ]
    reg_rows = []
    for _, r in region.iterrows():
        reg_rows.append([
            r.participant_id, r.block_label, r.comparison_label, r.focus_mode, r.region,
            f4(r.region_sum_joint_abs_score), f4(r.region_mean_joint_abs_score),
            f4(r.region_relative_share), int(r.region_rank),
        ])
    lines.append(md_table(
        ["Participant", "Block", "Comparison", "Focus", "Region", "Sum", "Mean", "Share", "Rank"],
        reg_rows,
    ))

    compact_rows = []
    for (pid, bl, cl, fm), grp in region.groupby(
        ["participant_id", "block_label", "comparison_label", "focus_mode"], sort=True
    ):
        ranked = grp.sort_values("region_rank")
        top = ranked.iloc[0]["region"] if len(ranked) > 0 else "NA"
        second = ranked.iloc[1]["region"] if len(ranked) > 1 else "NA"
        share = grp.set_index("region")["region_relative_share"]
        distal = float(share.get("distal_upper", np.nan))
        proximal = float(share.get("proximal_upper", np.nan)) + float(share.get("head_neck", np.nan))
        lower = float(share.get("lower_limb", np.nan)) + float(share.get("pelvis_proximal_lower", np.nan))
        compact_rows.append([
            pid, bl, cl, fm, top, second, f4(distal), f4(proximal), f4(lower),
            "252 includes pelvis_proximal_lower; 671 hip representation limited",
        ])
    lines += [
        "",
        "### Compact body-region summary",
        "",
        md_table(
            [
                "Participant", "Block", "Comparison", "Focus", "Top region", "Second region",
                "Distal upper share", "Proximal/core share", "Lower-limb share", "Notes",
            ],
            compact_rows,
        ),
        "",
        "### Body-region answers",
        "",
        "1. Largest derived joint-level scores vary by comparison; distal_upper and lower_limb regions often carry larger regional sums under all-PC.",
        "2. Upper-limb regions (proximal_upper + distal_upper) frequently account for a large body-region contribution profile.",
        "3. Core/proximal regions (head_neck + proximal_upper) are consistently visible but not always top-ranked.",
        "4. P3_P4_P5 block changes regional shares in a comparison-dependent manner.",
        "5. null_space_after_p50 can shift top region and regional share pattern relative to all-PC.",
        "",
    ]
    cmp_rows = []
    for _, r in compare.iterrows():
        cmp_rows.append([
            r.participant_id, r.block_label, r.comparison_label, f"{r.focus_a} vs {r.focus_b}",
            f4(r.spearman_rank_correlation_joint_abs), r.top_joint_changed, r.top_region_changed,
            f"{r.top_joint_a} -> {r.top_joint_b}",
        ])
    lines.append(md_table(
        ["Participant", "Block", "Comparison", "Pair", "Spearman rho", "Top joint changed", "Top region changed", "Notes"],
        cmp_rows,
    ))

    lines += [
        "",
        "## 12. Suggested heatmap figure cases",
        "",
        md_table(
            ["Rank", "Participant", "Block", "Comparison", "Focus", "Score type", "Why useful", "Limitation"],
            [
                [1, "671", "all", "T1_vs_T2", "all", "joint_abs_score_norm_0_1", "Primary longitudinal; arm links prominent at link level", "Single participant"],
                [2, "671", "all", "T1_vs_T2", "all", "joint_signed_score_norm_minus1_1", "Signed direction view", "Signed aggregation may cancel"],
                [3, "671", "all", "T1_vs_T2", "null_space_after_p50", "joint_abs_score_norm_0_1", "Main p50 null-space sensitivity", "Derived joint summary"],
                [4, "671", "all", "T1_vs_T2", "functional_p50", "joint_abs_score_norm_0_1", "Main p50 functional sensitivity", "Derived joint summary"],
                [5, "252", "all", "T1_vs_T2", "all", "joint_abs_score_norm_0_1", "252 primary example; includes pelvis-root joints", "Different schema from 671"],
                [6, "671", "P3_P4_P5", "T1_vs_T3", "all", "joint_abs_score_norm_0_1", "Block-specific P3_P4_P5 pattern", "Single comparison"],
            ],
        ),
        "",
        "## 13. Interpretation summary",
        "",
        "- Derived joint-level scores broadly reflect link-level patterns: upper-limb joints (LElbow, LHand, RElbow, RHand) often show higher joint_abs_score under all-PC longitudinal comparisons.",
        "- Core/proximal joints (Chest, LShoulder, RShoulder) are frequently mid-ranked or top-ranked; Neck is often low-ranked.",
        "- Lower-limb and pelvis_proximal_lower regions contribute variably; 252 includes additional hip representation via pelvis-root links.",
        "- P3_P4_P5 block changes regional profile in a comparison-dependent manner.",
        "- null_space_after_p50 can produce a different anatomical ranking pattern from all-PC.",
        "- Joint heatmaps are suitable for anatomical heatmap visualization when labeled as derived summaries.",
        "",
        "## 14. Limitations and cautions",
        "",
        "- Joint-level scores are derived, not raw JcvPCA.",
        "- Link-to-joint aggregation may smooth link-level patterns.",
        "- 671 lacks pelvis-root links; 252 includes them.",
        "- Raw cross-participant joint comparison is limited by schema differences.",
        "- Normalized scores are for visualization only.",
        "- No causal, clinical, treatment, or condition-specific claims.",
        "",
        "## 15. Machine-readable summary for external AI review",
        "",
        md_table(
            ["Field", "Value"],
            [
                ["Batch folder", ROOT.name],
                ["Primary input", "jcvpca_link_results.csv"],
                ["PC-focus input", "jcvpca_link_results_by_pc_focus_p50_p60.csv"],
                ["Main output long table", "joint_heatmap_scores_long.csv"],
                ["Main output report", "joint_heatmap_full_numeric_report.md"],
                ["Raw result level", "link-level"],
                ["Derived visualization level", "joint-level"],
                ["Primary focus mode", "all"],
                ["Main sensitivity", "functional_p50 / null_space_after_p50"],
                ["Optional sensitivity", "functional_p60 / null_space_after_p60"],
                ["Archived p2 included?", "no (main tables)"],
                ["Recommended use", "anatomical heatmap plotting and poster/report visualization"],
            ],
        ),
        "",
    ]
    (ROOT / "joint_heatmap_full_numeric_report.md").write_text("\n".join(lines),encoding="utf-8")


def main() -> None:
    mapping = build_mapping_df()
    mapping.to_csv(ROOT / "joint_heatmap_link_mapping.csv", index=False)

    link_df = load_link_data()
    all_links_in_data = set(link_df.link_id.unique())
    mapped = set(mapping.link_name)
    unmapped = sorted(all_links_in_data - mapped)

    long_df = build_joint_scores(link_df, mapping)
    long_df = long_df.rename(columns={"participant_id": "participant"})
    long_df.to_csv(ROOT / "joint_heatmap_scores_long.csv", index=False)

    wide_df = build_wide(long_df)
    wide_df.to_csv(ROOT / "joint_heatmap_scores_wide.csv", index=False)

    poster_keys = set(POSTER_CASES)
    poster = long_df[
        long_df.apply(
            lambda r: (r.participant, r.block_label, r.comparison_label, r.focus_mode) in poster_keys,
            axis=1,
        )
    ].copy()
    poster.to_csv(ROOT / "joint_heatmap_scores_poster_subset.csv", index=False)

    core = build_core_audit(long_df.rename(columns={"participant": "participant_id"}))
    core = core.rename(columns={"participant_id": "participant"})
    core.to_csv(ROOT / "joint_heatmap_core_audit.csv", index=False)

    region = build_region_summary(long_df.rename(columns={"participant": "participant_id"}))
    region = region.rename(columns={"participant_id": "participant"})
    region.to_csv(ROOT / "joint_heatmap_region_summary.csv", index=False)

    compare = compare_focus_pairs(long_df.rename(columns={"participant": "participant_id"}))
    compare = compare.rename(columns={"participant_id": "participant"})
    previews = save_preview_heatmaps(long_df.rename(columns={"participant": "participant_id"}), poster.rename(columns={"participant": "participant_id"}))

    write_preparation_review(mapping, long_df, wide_df, poster, core, region, unmapped, previews)
    write_full_numeric_report(
        mapping,
        long_df.rename(columns={"participant": "participant_id"}),
        poster.rename(columns={"participant": "participant_id"}),
        core.rename(columns={"participant": "participant_id"}),
        region.rename(columns={"participant": "participant_id"}),
        compare.rename(columns={"participant": "participant_id"}),
        previews,
        unmapped,
    )

    print(f"Joint heatmap preparation complete: {ROOT}")
    print(f"  mapping: {len(mapping)} links")
    print(f"  long scores: {len(long_df)} rows")
    print(f"  unmapped: {unmapped}")
    print(f"  previews: {len(previews)}")


if __name__ == "__main__":
    main()
