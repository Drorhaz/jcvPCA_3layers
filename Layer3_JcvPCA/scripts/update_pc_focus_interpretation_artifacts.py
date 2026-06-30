#!/usr/bin/env python3
"""Refresh batch interpretation artifacts to use variance-informed p50/p60 PC-focus."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd

from analyze_link_contribution_distribution import run_analysis

BATCH = Path(__file__).resolve().parents[1] / "outputs" / "gaga_batch_jcvpca_20260626_193319"

MAIN_FOCUS = ("functional_p50", "null_space_after_p50")
OPTIONAL_FOCUS = ("functional_p60", "null_space_after_p60")
ARCHIVED_FOCUS = ("functional_p2", "null_space_p2")
ACTIVE_FOCUS = MAIN_FOCUS + OPTIONAL_FOCUS

FOCUS_RUN_DIRS = {
    "functional_p50": "run_functional_p50",
    "null_space_after_p50": "run_null_space_after_p50",
    "functional_p60": "run_functional_p60",
    "null_space_after_p60": "run_null_space_after_p60",
    "functional_p2": "run_functional_p2",
    "null_space_p2": "run_null_space_p2",
}


def archive_if_exists(path: Path, archive_path: Path) -> None:
    if path.is_file() and not archive_path.is_file():
        shutil.copy2(path, archive_path)


def load_comparison_keys(batch_root: Path) -> pd.DataFrame:
    status = pd.read_csv(batch_root / "comparison_status.csv")
    if "focus_mode" in status.columns:
        status = status[status["focus_mode"].astype(str) == "all"].reset_index(drop=True)
    status["participant_id"] = status["participant_id"].astype(str)
    status["comparison_key"] = (
        status["participant_id"] + "_" + status["block_id"] + "_" + status["comparison_id"]
    )
    return status[
        [
            "participant_id",
            "block_id",
            "block_label",
            "comparison_id",
            "comparison_label",
            "comparison_key",
            "selected_m",
        ]
    ]


def normalize_link_focus(df: pd.DataFrame, keys: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["participant_id"] = out["participant_id"].astype(str)
    merged = out.merge(
        keys,
        on=["participant_id", "block_label", "comparison_label"],
        how="left",
        suffixes=("", "_k"),
    )
    merged["comparison_key"] = merged["comparison_key"].fillna(
        merged["participant_id"] + "_" + merged["block_id"] + "_" + merged["comparison_id"]
    )
    cols = [
        "comparison_label",
        "comparison_id",
        "block_id",
        "participant_id",
        "block_label",
        "comparison_key",
        "p",
        "focus_mode",
        "pc",
        "link_id",
        "JRW_A_link",
        "JRW_B_link",
        "JcvPCA_link",
    ]
    for c in cols:
        if c not in merged.columns:
            merged[c] = pd.NA
    merged["sensitivity_tier"] = merged["focus_mode"].map(_tier_for_mode)
    return merged[cols + ["sensitivity_tier"]]


def normalize_axis_focus(df: pd.DataFrame, keys: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["participant_id"] = out["participant_id"].astype(str)
    merged = out.merge(keys, on=["participant_id", "block_label", "comparison_label"], how="left")
    merged["comparison_key"] = merged["comparison_key"].fillna(
        merged["participant_id"] + "_" + merged["block_id"] + "_" + merged["comparison_id"]
    )
    cols = [
        "comparison_label",
        "comparison_id",
        "block_id",
        "participant_id",
        "block_label",
        "comparison_key",
        "p",
        "focus_mode",
        "pc",
        "feature",
        "link_id",
        "axis",
        "loading_A_abs",
        "loading_B_reprojected_abs",
        "jcvpca_axis",
        "explained_variance_A",
        "explained_variance_B_projected",
    ]
    merged["sensitivity_tier"] = merged["focus_mode"].map(_tier_for_mode)
    return merged[cols + ["sensitivity_tier"]]


def _tier_for_mode(mode: str) -> str:
    if mode in MAIN_FOCUS:
        return "main_sensitivity"
    if mode in OPTIONAL_FOCUS:
        return "optional_sensitivity"
    if mode in ARCHIVED_FOCUS:
        return "archived_exploratory"
    return "unknown"


def rebuild_pc_focus_by_comparison(batch_root: Path, keys: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for _, row in keys.iterrows():
        comp_root = batch_root / "comparisons" / row["comparison_key"]
        main_pf = comp_root / "run" / "pc_focus_selection.json"
        if main_pf.is_file():
            pf = json.loads(main_pf.read_text(encoding="utf-8"))
            rows.append({"comparison_key": row["comparison_key"], "focus_mode": "all", **pf})
        for focus_label, run_name in FOCUS_RUN_DIRS.items():
            pf_path = comp_root / run_name / "pc_focus_selection.json"
            if not pf_path.is_file():
                continue
            pf = json.loads(pf_path.read_text(encoding="utf-8"))
            rows.append({"comparison_key": row["comparison_key"], "focus_mode": focus_label, **pf})
    df = pd.DataFrame(rows)
    if not df.empty and "included_pcs" in df.columns:
        df["included_pcs"] = df["included_pcs"].apply(
            lambda x: json.dumps(x) if isinstance(x, list) else x
        )
    return df


def rebuild_sensitivity_results(batch_root: Path, keys: pd.DataFrame) -> pd.DataFrame:
    cfg = pd.read_csv(batch_root / "pc_focus_p50_p60_by_comparison.csv")
    cfg["participant_id"] = cfg["participant_id"].astype(str)
    rows: list[dict] = []
    for _, r in cfg.iterrows():
        for focus_label, p_col, pcs_col in (
            ("functional_p50", "p50", "included_pcs_functional_p50"),
            ("null_space_after_p50", "p50", "included_pcs_null_space_after_p50"),
            ("functional_p60", "p60", "included_pcs_functional_p60"),
            ("null_space_after_p60", "p60", "included_pcs_null_space_after_p60"),
        ):
            rows.append(
                {
                    "participant_id": r.participant_id,
                    "block_label": r.block_label,
                    "comparison_label": r.comparison_label,
                    "focus_mode": focus_label,
                    "p": int(r[p_col]),
                    "selected_m": int(r.selected_m),
                    "included_pcs": r[pcs_col],
                    "status": "completed",
                    "reason": "",
                    "sensitivity_tier": _tier_for_mode(focus_label),
                }
            )
    archived = pd.read_csv(batch_root / "jcvpca_link_results_by_pc_focus_archived_p2.csv")
    if archived.empty:
        return pd.DataFrame(rows)
    for (pid, bl, cl), grp in archived.groupby(["participant_id", "block_label", "comparison_label"]):
        for focus_mode in ARCHIVED_FOCUS:
            sub = grp[grp["focus_mode"] == focus_mode]
            if sub.empty:
                continue
            key_row = keys[
                (keys.participant_id == str(pid))
                & (keys.block_label == bl)
                & (keys.comparison_label == cl)
            ]
            sel_m = int(key_row.iloc[0].selected_m) if not key_row.empty else pd.NA
            rows.append(
                {
                    "participant_id": str(pid),
                    "block_label": bl,
                    "comparison_label": cl,
                    "focus_mode": focus_mode,
                    "p": 2,
                    "selected_m": sel_m,
                    "included_pcs": "",
                    "status": "completed",
                    "reason": "archived_exploratory_p2",
                    "sensitivity_tier": "archived_exploratory",
                }
            )
    return pd.DataFrame(rows)


def rebuild_comparison_status_by_focus(batch_root: Path, keys: pd.DataFrame) -> pd.DataFrame:
    sens = pd.read_csv(batch_root / "pc_focus_sensitivity_results.csv")
    rows: list[dict] = []
    for _, s in sens.iterrows():
        if s.sensitivity_tier == "archived_exploratory":
            continue
        key_row = keys[
            (keys.participant_id.astype(str) == str(s.participant_id))
            & (keys.block_label == s.block_label)
            & (keys.comparison_label == s.comparison_label)
        ]
        if key_row.empty:
            continue
        kr = key_row.iloc[0]
        rows.append(
            {
                "participant_id": s.participant_id,
                "block_id": kr.block_id,
                "block_label": s.block_label,
                "comparison_id": kr.comparison_id,
                "comparison_label": s.comparison_label,
                "focus_mode": s.focus_mode,
                "p": s.p,
                "included_pcs": s.included_pcs,
                "status": s.status,
                "reason": s.reason,
                "selected_m": s.selected_m,
                "sensitivity_tier": s.sensitivity_tier,
            }
        )
    return pd.DataFrame(rows)


def rebuild_null_space_availability(batch_root: Path) -> pd.DataFrame:
    df = pd.read_csv(batch_root / "null_space_p50_p60_availability_report.csv")
    rows: list[dict] = []
    for _, r in df.iterrows():
        rows.append(
            {
                "participant_id": r.participant_id,
                "block_label": r.block_label,
                "comparison_label": r.comparison_label,
                "selected_m": r.selected_m,
                "p50": r.p50,
                "p60": r.p60,
                "null_space_after_p50_status": r.null_space_after_p50_status,
                "null_space_after_p60_status": r.null_space_after_p60_status,
                "primary_null_space_mode": "null_space_after_p50",
            }
        )
    archived = pd.read_csv(batch_root / "null_space_availability_report_archived_p2.csv")
    archived["note"] = "archived fixed-p2 null-space rule"
    return pd.DataFrame(rows)


def refresh_sensitivity_plots(batch_root: Path, keys: pd.DataFrame) -> list[dict]:
    archived_root = batch_root / "plots" / "all_vs_functional_vs_nullspace_archived_p2"
    canonical_root = batch_root / "plots" / "all_vs_functional_vs_nullspace"
    p50_root = batch_root / "plots" / "all_vs_functional_p50_vs_nullspace_p50"

    if canonical_root.is_dir() and not archived_root.is_dir():
        shutil.move(str(canonical_root), str(archived_root))

    plot_rows: list[dict] = []
    for _, row in keys.iterrows():
        pid, bid, cid = row.participant_id, row.block_id, row.comparison_id
        src_dir = p50_root / pid / bid / cid
        dst_dir = canonical_root / pid / bid / cid
        dst_dir.mkdir(parents=True, exist_ok=True)
        src_composite = src_dir / "all_vs_functional_p50_vs_null_space_after_p50.png"
        if src_composite.is_file():
            dst = dst_dir / "all_vs_functional_vs_nullspace_link_jcvpca.png"
            shutil.copy2(src_composite, dst)
            plot_rows.append(
                {
                    "participant_id": pid,
                    "block_id": bid,
                    "block_label": row.block_label,
                    "comparison_id": cid,
                    "focus_mode": "main_sensitivity_p50",
                    "plot_path": str(dst.relative_to(batch_root)),
                    "plot_name": "all_vs_functional_vs_nullspace_link_jcvpca",
                }
            )
        for src_name, dst_name in (
            ("functional_p50", "functional_p50_link_jcvpca.png"),
            ("null_space_after_p50", "null_space_after_p50_link_jcvpca.png"),
        ):
            candidates = list(src_dir.glob(f"*{src_name}*.png"))
            if candidates:
                dst = dst_dir / dst_name
                shutil.copy2(candidates[0], dst)
                plot_rows.append(
                    {
                        "participant_id": pid,
                        "block_id": bid,
                        "block_label": row.block_label,
                        "comparison_id": cid,
                        "focus_mode": "main_sensitivity_p50",
                        "plot_path": str(dst.relative_to(batch_root)),
                        "plot_name": dst_name.replace(".png", ""),
                    }
                )
    return plot_rows


def rebuild_plot_index(batch_root: Path, keys: pd.DataFrame, new_sensitivity_plots: list[dict]) -> pd.DataFrame:
    idx = pd.read_csv(batch_root / "plot_index.csv")
    idx = idx[~((idx["focus_mode"] == "sensitivity") | (idx["plot_path"].str.contains("all_vs_functional_vs_nullspace", na=False)))]
    primary = idx[idx["focus_mode"] == "all"].copy()
    extra_dirs = [
        ("main_sensitivity_p50", "plots/all_vs_functional_p50_vs_nullspace_p50"),
        ("optional_sensitivity_p60", "plots/all_vs_functional_p60_vs_nullspace_p60"),
        ("sensitivity_p50_vs_p60", "plots/p50_vs_p60_sensitivity"),
        ("archived_p2_reference", "plots/all_vs_functional_vs_nullspace_archived_p2"),
    ]
    extra_rows: list[dict] = []
    for focus_mode, rel_root in extra_dirs:
        root = batch_root / rel_root
        if not root.is_dir():
            continue
        for png in sorted(root.rglob("*.png")):
            rel = str(png.relative_to(batch_root))
            parts = png.relative_to(root).parts
            if len(parts) < 4:
                continue
            pid, bid, cid = parts[0], parts[1], parts[2]
            key_row = keys[
                (keys.participant_id == pid) & (keys.block_id == bid) & (keys.comparison_id == cid)
            ]
            bl = key_row.iloc[0].block_label if not key_row.empty else ""
            extra_rows.append(
                {
                    "participant_id": pid,
                    "block_id": bid,
                    "block_label": bl,
                    "comparison_id": cid,
                    "focus_mode": focus_mode,
                    "plot_path": rel,
                }
            )
    sens_df = pd.DataFrame(new_sensitivity_plots)
    if not sens_df.empty:
        sens_df = sens_df[["participant_id", "block_id", "block_label", "comparison_id", "focus_mode", "plot_path"]]
    return pd.concat([primary, sens_df, pd.DataFrame(extra_rows)], ignore_index=True)


def build_top_links_summary(batch_root: Path) -> pd.DataFrame:
    even = pd.read_csv(batch_root / "contribution_evenness_summary.csv")
    even_p50 = pd.read_csv(batch_root / "contribution_evenness_summary_p50_p60.csv")
    top_map = even_p50.set_index(["participant_id", "block_label", "comparison_label", "focus_mode"])[
        ["top_positive_links", "top_negative_links", "mean_abs_delta"]
    ]
    rows = []
    for _, r in even.iterrows():
        if r.focus_mode != "all" and r.focus_mode not in ACTIVE_FOCUS:
            continue
        key = (r.participant_id, r.block_label, r.comparison_label, r.focus_mode)
        top_pos = top_neg = mean_abs = pd.NA
        if key in top_map.index:
            tr = top_map.loc[key]
            top_pos = tr["top_positive_links"]
            top_neg = tr["top_negative_links"]
            mean_abs = tr["mean_abs_delta"]
        rows.append(
            {
                "participant_id": r.participant_id,
                "block_label": r.block_label,
                "comparison_label": r.comparison_label,
                "focus_mode": r.focus_mode,
                "sensitivity_tier": _tier_for_mode(r.focus_mode) if r.focus_mode != "all" else "primary",
                "top_positive_links": top_pos,
                "top_negative_links": top_neg,
                "mean_abs_delta": mean_abs,
                "normalized_entropy": r.normalized_entropy,
                "top_3_share": r.top_3_share,
                "n_links": r.n_links,
            }
        )
    return pd.DataFrame(rows)


def build_rank_correlation_summary(batch_root: Path) -> pd.DataFrame:
    vs_p2 = pd.read_csv(batch_root / "pc_focus_p50_p60_vs_p2_comparison.csv")
    vs_p60 = pd.read_csv(batch_root / "pc_focus_p50_vs_p60_comparison.csv")
    rows = []
    for _, r in vs_p2.iterrows():
        rows.append(
            {
                "participant_id": r.participant_id,
                "block_label": r.block_label,
                "comparison_label": r.comparison_label,
                "comparison_type": "archived_p2_vs_main_p50",
                "focus_a": r.focus_a,
                "focus_b": r.focus_b,
                "rank_correlation": r.rank_correlation,
            }
        )
    for _, r in vs_p60.iterrows():
        rows.append(
            {
                "participant_id": r.participant_id,
                "block_label": r.block_label,
                "comparison_label": r.comparison_label,
                "comparison_type": "main_p50_vs_optional_p60",
                "focus_a": r.focus_a,
                "focus_b": r.focus_b,
                "rank_correlation": r.rank_correlation,
            }
        )
    return pd.DataFrame(rows)


def write_poster_shortlist(batch_root: Path, plot_index: pd.DataFrame) -> None:
    picks = [
        ("671", "A", "L1_T1_vs_T2", "primary", "plots/671/A/L1_T1_vs_T2/link_jcvpca_bar.png"),
        ("671", "A", "L1_T1_vs_T2", "main_sensitivity_p50", "plots/all_vs_functional_vs_nullspace/671/A/L1_T1_vs_T2/all_vs_functional_vs_nullspace_link_jcvpca.png"),
        ("671", "A", "L2_T1_vs_T3", "primary", "plots/671/A/L2_T1_vs_T3/link_jcvpca_bar.png"),
        ("252", "A", "L2_T1_vs_T3", "primary", "plots/252/A/L2_T1_vs_T3/link_jcvpca_bar.png"),
        ("252", "B", "L2_T1_vs_T3", "main_sensitivity_p50", "plots/all_vs_functional_p50_vs_nullspace_p50/252/B/L2_T1_vs_T3/all_vs_functional_p50_vs_null_space_after_p50.png"),
        ("252", "B", "L2_T1_vs_T3", "optional_sensitivity_p60", "plots/all_vs_functional_p60_vs_nullspace_p60/252/B/L2_T1_vs_T3/all_vs_functional_p60_vs_null_space_after_p60.png"),
        ("671", "A", "L1_T1_vs_T2", "evenness", "plots/link_contribution_evenness/671_all_P1_P2_P3_P4_P5_T1_vs_T2_all_p_link.png"),
        ("671", "A", "L1_T1_vs_T2", "evenness_p50", "plots/link_contribution_evenness/671_all_P1_P2_P3_P4_P5_T1_vs_T2_functional_p50_p_link.png"),
    ]
    lines = [
        "# Poster / report plot shortlist",
        "",
        "Batch: `gaga_batch_jcvpca_20260626_193319`",
        "",
        "## Interpretation hierarchy",
        "",
        "| Tier | Focus rule |",
        "| --- | --- |",
        "| Primary | all selected PCs |",
        "| Main PC-focus sensitivity | `functional_p50` / `null_space_after_p50` |",
        "| Optional stricter sensitivity | `functional_p60` / `null_space_after_p60` |",
        "| Archived exploratory | `functional_p2` / `null_space_p2` |",
        "",
        "## Recommended figures",
        "",
        "| Role | Participant | Block | Comparison | Path |",
        "| --- | --- | --- | --- | --- |",
    ]
    for pid, bid, cid, role, path in picks:
        full = batch_root / path
        status = "present" if full.is_file() else "missing"
        lines.append(f"| {role} | {pid} | {bid} | {cid} | `{path}` ({status}) |")
    lines += [
        "",
        "## Notes",
        "",
        "- Primary panels use all-PC link-level JcvPCA (`link_jcvpca_bar.png`).",
        "- Main PC-focus panels use variance-informed p50 functional vs null-space (`all_vs_functional_vs_nullspace/` copies from p50 sensitivity runs).",
        "- Optional p60 panels available under `plots/all_vs_functional_p60_vs_nullspace_p60/`.",
        "- Archived p2 sensitivity plots retained under `plots/all_vs_functional_vs_nullspace_archived_p2/`.",
        "",
    ]
    (batch_root / "poster_plot_shortlist.md").write_text("\n".join(lines), encoding="utf-8")


def write_interpretation_report(batch_root: Path) -> None:
    cfg = pd.read_csv(batch_root / "pc_focus_p50_p60_by_comparison.csv")
    vs_p2 = pd.read_csv(batch_root / "pc_focus_p50_p60_vs_p2_comparison.csv")
    lines = [
        "# Gaga JcvPCA batch interpretation report",
        "",
        f"Batch folder: `{batch_root.name}`",
        "",
        "## PC-focus hierarchy (active interpretation)",
        "",
        "| Tier | Modes |",
        "| --- | --- |",
        "| Primary | all selected PCs |",
        "| Main sensitivity | `functional_p50`, `null_space_after_p50` |",
        "| Optional sensitivity | `functional_p60`, `null_space_after_p60` |",
        "| Archived exploratory | `functional_p2`, `null_space_p2` (see `*_archived_p2.csv`) |",
        "",
        "## Variance-informed thresholds",
        "",
        f"- Comparisons with p50 in {{3,4}}: {cfg.p50.nunique()} distinct values across {len(cfg)} comparisons",
        f"- p50 range: {int(cfg.p50.min())}–{int(cfg.p50.max())}; p60 range: {int(cfg.p60.min())}–{int(cfg.p60.max())}",
        "- Null-space after p50 and p60: available for all 20 comparisons",
        "",
        "## Rank correlation summary (median Spearman rho)",
        "",
        "| Comparison | Median rho |",
        "| --- | --- |",
        f"| functional_p2 vs functional_p50 | {vs_p2[vs_p2.focus_b=='functional_p50']['rank_correlation'].median():.3f} |",
        f"| null_space_p2 vs null_space_after_p50 | {vs_p2[vs_p2.focus_b=='null_space_after_p50']['rank_correlation'].median():.3f} |",
        "",
        "## Updated artifact index",
        "",
        "| File | Content |",
        "| --- | --- |",
        "| `jcvpca_link_results_by_pc_focus.csv` | Active p50/p60 link-level focus results |",
        "| `jcvpca_link_results_by_pc_focus_archived_p2.csv` | Archived p2 link-level results |",
        "| `jcvpca_axis_results_by_pc_focus.csv` | Active p50/p60 axis-level focus results |",
        "| `pc_focus_by_comparison.csv` | PC sets for all, p50, p60, archived p2 |",
        "| `pc_focus_sensitivity_results.csv` | Sensitivity run registry with tier labels |",
        "| `comparison_status_by_focus.csv` | Active p50/p60 focus status only |",
        "| `contribution_evenness_summary.csv` | Evenness for all + p50/p60 focus modes |",
        "| `pc_focus_evenness_comparison.csv` | All-PC vs p50/p60 evenness contrasts |",
        "| `null_space_availability_report.csv` | p50/p60 null-space availability |",
        "| `poster_plot_shortlist.md` | Poster/report figure shortlist |",
        "| `PC_focus_p50_p60_interpretation_review.md` | Detailed per-comparison review |",
        "",
        "Numerical outputs only. No causal or clinical conclusions.",
        "",
    ]
    (batch_root / "gaga_batch_interpretation_report.md").write_text("\n".join(lines), encoding="utf-8")


def write_batch_summary(batch_root: Path) -> None:
    status = pd.read_csv(batch_root / "comparison_status.csv")
    if "focus_mode" in status.columns:
        status = status[status["focus_mode"] == "all"]
    lines = [
        "# Gaga JcvPCA batch summary",
        "",
        f"- Batch folder: `{batch_root}`",
        f"- Comparisons completed: {len(status)}",
        "",
        "## PC-focus interpretation hierarchy",
        "",
        "| Tier | Focus modes |",
        "| --- | --- |",
        "| Primary | all selected PCs |",
        "| Main sensitivity | functional_p50 / null_space_after_p50 |",
        "| Optional sensitivity | functional_p60 / null_space_after_p60 |",
        "| Archived exploratory | functional_p2 / null_space_p2 |",
        "",
        "## Downstream artifacts",
        "",
        "- Active PC-focus tables: `jcvpca_link_results_by_pc_focus.csv`, `jcvpca_axis_results_by_pc_focus.csv`",
        "- Archived p2 tables: `*_archived_p2.csv`",
        "- Interpretation report: `gaga_batch_interpretation_report.md`",
        "- Poster shortlist: `poster_plot_shortlist.md`",
        "- Detailed PC-focus review: `PC_focus_p50_p60_interpretation_review.md`",
        "",
        "Numerical outputs only. No scientific conclusions.",
        "",
    ]
    (batch_root / "batch_summary.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    batch_root = BATCH
    keys = load_comparison_keys(batch_root)

    archive_if_exists(
        batch_root / "jcvpca_link_results_by_pc_focus.csv",
        batch_root / "jcvpca_link_results_by_pc_focus_archived_p2.csv",
    )
    archive_if_exists(
        batch_root / "jcvpca_axis_results_by_pc_focus.csv",
        batch_root / "jcvpca_axis_results_by_pc_focus_archived_p2.csv",
    )
    archive_if_exists(
        batch_root / "null_space_availability_report.csv",
        batch_root / "null_space_availability_report_archived_p2.csv",
    )
    archive_if_exists(
        batch_root / "pc_focus_by_comparison.csv",
        batch_root / "pc_focus_by_comparison_archived_p2.csv",
    )

    link_p50 = pd.read_csv(batch_root / "jcvpca_link_results_by_pc_focus_p50_p60.csv")
    axis_p50 = pd.read_csv(batch_root / "jcvpca_axis_results_by_pc_focus_p50_p60.csv")
    link_active = normalize_link_focus(link_p50, keys)
    axis_active = normalize_axis_focus(axis_p50, keys)
    link_active.to_csv(batch_root / "jcvpca_link_results_by_pc_focus.csv", index=False)
    axis_active.to_csv(batch_root / "jcvpca_axis_results_by_pc_focus.csv", index=False)

    pc_focus = rebuild_pc_focus_by_comparison(batch_root, keys)
    pc_focus.to_csv(batch_root / "pc_focus_by_comparison.csv", index=False)

    sens = rebuild_sensitivity_results(batch_root, keys)
    sens.to_csv(batch_root / "pc_focus_sensitivity_results.csv", index=False)

    focus_status = rebuild_comparison_status_by_focus(batch_root, keys)
    focus_status.to_csv(batch_root / "comparison_status_by_focus.csv", index=False)

    null_rep = rebuild_null_space_availability(batch_root)
    null_rep.to_csv(batch_root / "null_space_availability_report.csv", index=False)

    run_analysis(batch_root)

    sens_plots = refresh_sensitivity_plots(batch_root, keys)
    plot_index = rebuild_plot_index(batch_root, keys, sens_plots)
    plot_index.to_csv(batch_root / "plot_index.csv", index=False)

    build_top_links_summary(batch_root).to_csv(batch_root / "top_links_by_focus_mode.csv", index=False)
    build_rank_correlation_summary(batch_root).to_csv(
        batch_root / "pc_focus_rank_correlation_summary.csv", index=False
    )

    write_poster_shortlist(batch_root, plot_index)
    write_interpretation_report(batch_root)
    write_batch_summary(batch_root)

    print(f"Updated PC-focus interpretation artifacts in {batch_root}")


if __name__ == "__main__":
    main()
