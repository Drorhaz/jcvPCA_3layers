#!/usr/bin/env python3
"""Add variance-informed p50/p60 PC-focus sensitivity to an existing Gaga batch output."""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from layer3_jcvpca.gaga_batch_runner import (
    STATUS_COMPLETED,
    FocusRunResult,
    _run_focus_sensitivity_pipeline,
)
from layer3_jcvpca.pc_focus import PC_FOCUS_FUNCTIONAL, PC_FOCUS_NULL_SPACE, PcFocusParameters

BLOCK_LABELS = {"A": "all_P1_P2_P3_P4_P5", "B": "P3_P4_P5"}
FOCUS_SPECS = (
    ("functional_p50", PC_FOCUS_FUNCTIONAL, "p50"),
    ("null_space_after_p50", PC_FOCUS_NULL_SPACE, "p50"),
    ("functional_p60", PC_FOCUS_FUNCTIONAL, "p60"),
    ("null_space_after_p60", PC_FOCUS_NULL_SPACE, "p60"),
)
P2_LABELS = ("functional_p2", "null_space_p2")


def _load_distribution_helpers():
    script_dir = Path(__file__).resolve().parent
    path = script_dir / "analyze_link_contribution_distribution.py"
    spec = importlib.util.spec_from_file_location("link_dist", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["link_dist"] = mod
    spec.loader.exec_module(mod)
    return mod


def p_at_threshold(cum: np.ndarray, threshold: float) -> int:
    hit = np.where(cum >= threshold)[0]
    return int(hit[0] + 1) if hit.size else int(len(cum))


def load_p_thresholds(run_dir: Path) -> tuple[int, int, float, float, int]:
    cum_path = run_dir / "pca_A_cumulative_variance.csv"
    sel_path = run_dir / "pca_A_selected_m.json"
    cum = pd.read_csv(cum_path)["cumulative_explained_variance"].to_numpy()
    selected_m = int(json.loads(sel_path.read_text(encoding="utf-8"))["selected_m"])
    p50 = p_at_threshold(cum, 0.50)
    p60 = p_at_threshold(cum, 0.60)
    cum_p50 = float(cum[p50 - 1])
    cum_p60 = float(cum[p60 - 1])
    return p50, p60, cum_p50, cum_p60, selected_m


def _save_fig(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def link_agg(df: pd.DataFrame) -> pd.Series:
    return df.groupby("link_id")["JcvPCA_link"].mean()


def evenness_metrics(link_df: pd.DataFrame, helpers) -> dict[str, float]:
    agg = link_df.groupby("link_id")["JcvPCA_link"].mean().abs()
    total = float(agg.sum())
    if total <= 0:
        return {
            "mean_abs_delta": float("nan"),
            "normalized_entropy": float("nan"),
            "gini_concentration": float("nan"),
            "top_3_share": float("nan"),
        }
    probs = (agg / total).to_numpy()
    n = len(probs)
    ent = helpers.entropy_from_probs(probs)
    return {
        "mean_abs_delta": float(agg.mean()),
        "normalized_entropy": ent / math.log(n) if n > 1 else 0.0,
        "gini_concentration": helpers.gini_coefficient(agg.to_numpy()),
        "top_3_share": helpers.top_k_share(probs, 3),
    }


def top_links(link_df: pd.DataFrame, n: int = 3) -> tuple[str, str]:
    agg = link_df.groupby("link_id")["JcvPCA_link"].mean()
    pos = agg.nlargest(n)
    neg = agg.nsmallest(n)
    pos_s = "; ".join(f"{k}({v:.4f})" for k, v in pos.items())
    neg_s = "; ".join(f"{k}({v:.4f})" for k, v in neg.items())
    return pos_s, neg_s


def run_sensitivity(batch_root: Path, *, only_key: str | None = None) -> None:
    helpers = _load_distribution_helpers()
    status = pd.read_csv(batch_root / "comparison_status.csv")
    if "focus_mode" in status.columns:
        status = status[status["focus_mode"].astype(str) == "all"].reset_index(drop=True)
    p2_links = pd.read_csv(batch_root / "jcvpca_link_results_by_pc_focus.csv")
    all_links = pd.read_csv(batch_root / "jcvpca_link_results.csv")

    link_rows: list[pd.DataFrame] = []
    axis_rows: list[pd.DataFrame] = []
    focus_summary_rows: list[dict] = []
    availability_rows: list[dict] = []
    dist_rows: list[dict] = []
    evenness_rows: list[dict] = []
    run_results: dict[str, dict[str, FocusRunResult]] = {}

    for _, row in status.iterrows():
        pid = str(row.participant_id)
        bid = str(row.block_id)
        cid = str(row.comparison_id)
        blabel = str(row.block_label)
        clabel = str(row.comparison_label)
        key = f"{pid}_{bid}_{cid}"
        if only_key and key != only_key:
            continue
        comp_root = batch_root / "comparisons" / key
        main_run = comp_root / "run"
        construction = comp_root / "construction"
        preflight = comp_root / "preflight"

        p50, p60, cum_p50, cum_p60, selected_m = load_p_thresholds(main_run)
        p_map = {"p50": p50, "p60": p60}
        null_p50_ok = p50 < selected_m
        null_p60_ok = p60 < selected_m

        included = {
            "functional_p50": list(range(1, p50 + 1)),
            "null_space_after_p50": list(range(p50 + 1, selected_m + 1)) if null_p50_ok else [],
            "functional_p60": list(range(1, p60 + 1)),
            "null_space_after_p60": list(range(p60 + 1, selected_m + 1)) if null_p60_ok else [],
        }

        focus_summary_rows.append(
            {
                "participant_id": pid,
                "block_id": bid,
                "block_label": blabel,
                "comparison_id": cid,
                "comparison_label": clabel,
                "selected_m": selected_m,
                "p50": p50,
                "cumulative_variance_at_p50": cum_p50,
                "p60": p60,
                "cumulative_variance_at_p60": cum_p60,
                "included_pcs_functional_p50": ",".join(str(x) for x in included["functional_p50"]),
                "included_pcs_null_space_after_p50": ",".join(str(x) for x in included["null_space_after_p50"]),
                "included_pcs_functional_p60": ",".join(str(x) for x in included["functional_p60"]),
                "included_pcs_null_space_after_p60": ",".join(str(x) for x in included["null_space_after_p60"]),
                "null_space_p50_available": null_p50_ok,
                "null_space_p60_available": null_p60_ok,
                "null_space_p50_n_pcs": len(included["null_space_after_p50"]),
                "null_space_p60_n_pcs": len(included["null_space_after_p60"]),
            }
        )
        availability_rows.append(
            {
                "participant_id": pid,
                "block_label": blabel,
                "comparison_label": clabel,
                "selected_m": selected_m,
                "p50": p50,
                "p60": p60,
                "null_space_after_p50_status": "completed" if null_p50_ok else "unavailable_p_ge_selected_m",
                "null_space_after_p60_status": "completed" if null_p60_ok else "unavailable_p_ge_selected_m",
            }
        )

        run_results[key] = {}
        for focus_label, mode, p_key in FOCUS_SPECS:
            p_val = p_map[p_key]
            if focus_label.startswith("null_space") and p_val >= selected_m:
                run_results[key][focus_label] = FocusRunResult(
                    focus_mode=mode,
                    focus_label=focus_label,
                    status="skipped",
                    reason="null_space_unavailable_p_ge_selected_m",
                    p=p_val,
                )
                continue
            try:
                fr = _run_focus_sensitivity_pipeline(
                    main_run,
                    construction_dir=construction,
                    preflight_dir=preflight,
                    focus_label=focus_label,
                    pc_focus_params=PcFocusParameters(pc_focus_mode=mode, p=p_val),
                )
            except Exception as exc:  # noqa: BLE001
                fr = FocusRunResult(
                    focus_mode=mode,
                    focus_label=focus_label,
                    status="failed_error",
                    reason=str(exc),
                    p=p_val,
                )
            run_results[key][focus_label] = fr
            if fr.status != STATUS_COMPLETED or not fr.run_dir:
                continue
            fr_dir = Path(fr.run_dir)
            lp = fr_dir / "link_level_jcvpca_unweighted.csv"
            ap = fr_dir / "axis_level_jcvpca_unweighted.csv"
            if lp.is_file():
                ldf = pd.read_csv(lp)
                ldf.insert(0, "focus_mode", focus_label)
                ldf.insert(0, "p", p_val)
                ldf.insert(0, "comparison_label", clabel)
                ldf.insert(0, "block_label", blabel)
                ldf.insert(0, "participant_id", pid)
                ldf.insert(0, "comparison_id", cid)
                ldf.insert(0, "block_id", bid)
                link_rows.append(ldf)
                ev = evenness_metrics(ldf, helpers)
                pos, neg = top_links(ldf)
                evenness_rows.append(
                    {
                        "participant_id": pid,
                        "block_label": blabel,
                        "comparison_label": clabel,
                        "focus_mode": focus_label,
                        "p": p_val,
                        "top_positive_links": pos,
                        "top_negative_links": neg,
                        **ev,
                    }
                )
                agg = ldf.groupby("link_id")["JcvPCA_link"].mean().abs()
                total = float(agg.sum())
                p25 = float((agg / total).quantile(0.25)) if total > 0 else 0.0
                for stem, val in agg.items():
                    p_link = float(val / total) if total > 0 else 0.0
                    dist_rows.append(
                        {
                            "participant_id": pid,
                            "block_label": blabel,
                            "comparison_label": clabel,
                            "focus_mode": focus_label,
                            "link_id": stem,
                            "abs_delta": float(val),
                            "p_link": p_link,
                            "low_relative_contribution": bool(p_link < p25 or p_link < 0.02),
                        }
                    )
            if ap.is_file():
                adf = pd.read_csv(ap)
                adf.insert(0, "focus_mode", focus_label)
                adf.insert(0, "p", p_val)
                adf.insert(0, "comparison_label", clabel)
                adf.insert(0, "block_label", blabel)
                adf.insert(0, "participant_id", pid)
                axis_rows.append(adf)

    link_out = pd.concat(link_rows, ignore_index=True) if link_rows else pd.DataFrame()
    axis_out = pd.concat(axis_rows, ignore_index=True) if axis_rows else pd.DataFrame()
    focus_df = pd.DataFrame(focus_summary_rows)
    evenness_df = pd.DataFrame(evenness_rows)
    dist_df = pd.DataFrame(dist_rows)

    link_out.to_csv(batch_root / "jcvpca_link_results_by_pc_focus_p50_p60.csv", index=False)
    axis_out.to_csv(batch_root / "jcvpca_axis_results_by_pc_focus_p50_p60.csv", index=False)
    focus_df.to_csv(batch_root / "pc_focus_p50_p60_by_comparison.csv", index=False)
    pd.DataFrame(availability_rows).to_csv(batch_root / "null_space_p50_p60_availability_report.csv", index=False)
    dist_df.to_csv(batch_root / "link_contribution_distribution_p50_p60.csv", index=False)
    evenness_df.to_csv(batch_root / "contribution_evenness_summary_p50_p60.csv", index=False)

    _write_p2_comparisons(batch_root, p2_links, link_out, evenness_df, helpers)
    _write_p50_vs_p60(batch_root, link_out, evenness_df)
    _write_plots(batch_root, status, all_links, link_out, p2_links, evenness_df)

    print(f"p50/p60 PC-focus sensitivity complete: {batch_root}")


def _write_p2_comparisons(
    batch_root: Path,
    p2_links: pd.DataFrame,
    new_links: pd.DataFrame,
    evenness_df: pd.DataFrame,
    helpers,
) -> None:
    rows: list[dict] = []
    pairs = (
        ("functional_p2", "functional_p50"),
        ("functional_p2", "functional_p60"),
        ("null_space_p2", "null_space_after_p50"),
        ("null_space_p2", "null_space_after_p60"),
    )
    groups = new_links.groupby(["participant_id", "block_label", "comparison_label"]).groups
    if groups:
        iter_groups = groups.keys()
    else:
        iter_groups = p2_links.groupby(["participant_id", "block_label", "comparison_label"]).groups.keys()
    for pid, blabel, clabel in iter_groups:
        for old_f, new_f in pairs:
            old_df = p2_links[
                (p2_links.participant_id.astype(str) == str(pid))
                & (p2_links.block_label == blabel)
                & (p2_links.comparison_label == clabel)
                & (p2_links.focus_mode == old_f)
            ]
            new_df = new_links[
                (new_links.participant_id.astype(str) == str(pid))
                & (new_links.block_label == blabel)
                & (new_links.comparison_label == clabel)
                & (new_links.focus_mode == new_f)
            ]
            if old_df.empty or new_df.empty:
                rho = float("nan")
            else:
                a = link_agg(old_df)
                b = link_agg(new_df)
                common = a.index.intersection(b.index)
                rho = float(spearmanr(a[common], b[common]).correlation) if len(common) > 2 else float("nan")
            ev_old = evenness_metrics(old_df, helpers) if not old_df.empty else {}
            ev_new = evenness_metrics(new_df, helpers) if not new_df.empty else {}
            pos_a, neg_a = top_links(old_df) if not old_df.empty else ("", "")
            pos_b, neg_b = top_links(new_df) if not new_df.empty else ("", "")
            rows.append(
                {
                    "participant_id": pid,
                    "block_label": blabel,
                    "comparison_label": clabel,
                    "focus_a": old_f,
                    "focus_b": new_f,
                    "rank_correlation": rho,
                    "mean_abs_delta_a": ev_old.get("mean_abs_delta", float("nan")),
                    "mean_abs_delta_b": ev_new.get("mean_abs_delta", float("nan")),
                    "normalized_entropy_a": ev_old.get("normalized_entropy", float("nan")),
                    "normalized_entropy_b": ev_new.get("normalized_entropy", float("nan")),
                    "top_3_share_a": ev_old.get("top_3_share", float("nan")),
                    "top_3_share_b": ev_new.get("top_3_share", float("nan")),
                    "top_positive_links_a": pos_a,
                    "top_negative_links_a": neg_a,
                    "top_positive_links_b": pos_b,
                    "top_negative_links_b": neg_b,
                }
            )
    pd.DataFrame(rows).to_csv(batch_root / "pc_focus_p50_p60_vs_p2_comparison.csv", index=False)


def _write_p50_vs_p60(batch_root: Path, new_links: pd.DataFrame, evenness_df: pd.DataFrame) -> None:
    rows: list[dict] = []
    for (pid, blabel, clabel), _ in new_links.groupby(["participant_id", "block_label", "comparison_label"]):
        for kind, fa, fb in (
            ("functional", "functional_p50", "functional_p60"),
            ("null_space", "null_space_after_p50", "null_space_after_p60"),
        ):
            a_df = new_links[
                (new_links.participant_id.astype(str) == str(pid))
                & (new_links.block_label == blabel)
                & (new_links.comparison_label == clabel)
                & (new_links.focus_mode == fa)
            ]
            b_df = new_links[
                (new_links.participant_id.astype(str) == str(pid))
                & (new_links.block_label == blabel)
                & (new_links.comparison_label == clabel)
                & (new_links.focus_mode == fb)
            ]
            if a_df.empty or b_df.empty:
                continue
            sa = link_agg(a_df)
            sb = link_agg(b_df)
            common = sa.index.intersection(sb.index)
            rho = float(spearmanr(sa[common], sb[common]).correlation) if len(common) > 2 else float("nan")
            rank_shift = (sa[common].rank() - sb[common].rank()).abs()
            substantial = rank_shift[rank_shift >= 3].sort_values(ascending=False)
            substantial_links = "; ".join(f"{k}(shift={int(v)})" for k, v in substantial.head(5).items())
            ev_a = evenness_df[
                (evenness_df.participant_id.astype(str) == str(pid))
                & (evenness_df.block_label == blabel)
                & (evenness_df.comparison_label == clabel)
                & (evenness_df.focus_mode == fa)
            ].iloc[0]
            ev_b = evenness_df[
                (evenness_df.participant_id.astype(str) == str(pid))
                & (evenness_df.block_label == blabel)
                & (evenness_df.comparison_label == clabel)
                & (evenness_df.focus_mode == fb)
            ].iloc[0]
            note = []
            if kind == "functional":
                if ev_b["normalized_entropy"] < ev_a["normalized_entropy"] - 0.02:
                    note.append("p60 leaves a narrower functional PC set than p50; link contribution is more concentrated")
                elif ev_b["normalized_entropy"] > ev_a["normalized_entropy"] + 0.02:
                    note.append("p60 leaves a narrower functional PC set than p50; link contribution is more evenly distributed")
            else:
                if ev_b["normalized_entropy"] < ev_a["normalized_entropy"] - 0.02:
                    note.append("p60 null-space is narrower than p50; link contribution is more concentrated")
                elif ev_b["normalized_entropy"] > ev_a["normalized_entropy"] + 0.02:
                    note.append("p60 null-space is narrower than p50; link contribution is more evenly distributed")

            func_p50 = new_links[
                (new_links.participant_id.astype(str) == str(pid))
                & (new_links.block_label == blabel)
                & (new_links.comparison_label == clabel)
                & (new_links.focus_mode == "functional_p50")
            ]
            null_p50 = new_links[
                (new_links.participant_id.astype(str) == str(pid))
                & (new_links.block_label == blabel)
                & (new_links.comparison_label == clabel)
                & (new_links.focus_mode == "null_space_after_p50")
            ]
            func_p60 = new_links[
                (new_links.participant_id.astype(str) == str(pid))
                & (new_links.block_label == blabel)
                & (new_links.comparison_label == clabel)
                & (new_links.focus_mode == "functional_p60")
            ]
            null_p60 = new_links[
                (new_links.participant_id.astype(str) == str(pid))
                & (new_links.block_label == blabel)
                & (new_links.comparison_label == clabel)
                & (new_links.focus_mode == "null_space_after_p60")
            ]
            migration = ""
            if not func_p50.empty and not null_p50.empty and not func_p60.empty and not null_p60.empty:
                fp50 = link_agg(func_p50).abs()
                np50 = link_agg(null_p50).abs()
                fp60 = link_agg(func_p60).abs()
                np60 = link_agg(null_p60).abs()
                dom_p50 = (fp50 > np50).astype(int)
                dom_p60 = (fp60 > np60).astype(int)
                switched = dom_p50.index[(dom_p50 != dom_p60)]
                if len(switched):
                    migration = "; ".join(str(x) for x in switched[:8])

            rows.append(
                {
                    "participant_id": pid,
                    "block_label": blabel,
                    "comparison_label": clabel,
                    "comparison_kind": kind,
                    "focus_a": fa,
                    "focus_b": fb,
                    "rank_correlation": rho,
                    "mean_abs_rank_shift": float(rank_shift.mean()),
                    "substantial_rank_shift_links": substantial_links,
                    "links_switching_functional_vs_null_dominance_p50_to_p60": migration,
                    "normalized_entropy_a": ev_a["normalized_entropy"],
                    "normalized_entropy_b": ev_b["normalized_entropy"],
                    "top_3_share_a": ev_a["top_3_share"],
                    "top_3_share_b": ev_b["top_3_share"],
                    "distribution_note": "; ".join(note) if note else "rank-order of link contributions differs modestly between p50 and p60 focus",
                }
            )
    pd.DataFrame(rows).to_csv(batch_root / "pc_focus_p50_vs_p60_comparison.csv", index=False)


def _write_plots(
    batch_root: Path,
    status: pd.DataFrame,
    all_links: pd.DataFrame,
    new_links: pd.DataFrame,
    p2_links: pd.DataFrame,
    evenness_df: pd.DataFrame,
) -> None:
    for _, row in status.iterrows():
        pid, bid, cid = str(row.participant_id), str(row.block_id), str(row.comparison_id)
        blabel, clabel = str(row.block_label), str(row.comparison_label)
        main = all_links[
            (all_links.participant_id.astype(str) == pid)
            & (all_links.block_id == bid)
            & (all_links.comparison_id == cid)
        ]
        if main.empty:
            continue

        for plot_subdir, func_label, null_label in (
            ("all_vs_functional_p50_vs_nullspace_p50", "functional_p50", "null_space_after_p50"),
            ("all_vs_functional_p60_vs_nullspace_p60", "functional_p60", "null_space_after_p60"),
        ):
            panels: dict[str, pd.DataFrame] = {"all": main}
            for lab in (func_label, null_label):
                sub = new_links[
                    (new_links.participant_id.astype(str) == pid)
                    & (new_links.block_id == bid)
                    & (new_links.comparison_id == cid)
                    & (new_links.focus_mode == lab)
                ]
                if not sub.empty:
                    panels[lab] = sub
            if len(panels) < 2:
                continue
            out_dir = batch_root / "plots" / plot_subdir / pid / bid / cid
            out_dir.mkdir(parents=True, exist_ok=True)
            labels = [k for k in ("all", func_label, null_label) if k in panels]
            fig, axes = plt.subplots(1, len(labels), figsize=(5 * len(labels), 5), sharey=True)
            if len(labels) == 1:
                axes = [axes]
            for ax, lab in zip(axes, labels):
                agg = panels[lab].groupby("link_id")["JcvPCA_link"].mean().sort_values()
                ax.barh(agg.index, agg.values, color="steelblue")
                ax.set_title(lab)
            fig.suptitle(f"{pid} | {blabel} | {clabel}")
            _save_fig(fig, out_dir / f"all_vs_{func_label}_vs_{null_label}.png")

        # p50 vs p60 functional
        p50f = new_links[
            (new_links.participant_id.astype(str) == pid)
            & (new_links.comparison_id == cid)
            & (new_links.focus_mode == "functional_p50")
        ]
        p60f = new_links[
            (new_links.participant_id.astype(str) == pid)
            & (new_links.comparison_id == cid)
            & (new_links.focus_mode == "functional_p60")
        ]
        if not p50f.empty and not p60f.empty:
            fig, axes = plt.subplots(1, 2, figsize=(10, 5), sharey=True)
            for ax, df, title in (
                (axes[0], p50f, "functional_p50"),
                (axes[1], p60f, "functional_p60"),
            ):
                agg = df.groupby("link_id")["JcvPCA_link"].mean().sort_values()
                ax.barh(agg.index, agg.values, color="teal")
                ax.set_title(title)
            fig.suptitle(f"p50 vs p60 functional | {pid} | {clabel}")
            _save_fig(
                fig,
                batch_root / "plots" / "p50_vs_p60_sensitivity" / pid / bid / cid / "functional_p50_vs_p60.png",
            )

        # p2 vs p50 functional
        p2f = p2_links[
            (p2_links.participant_id.astype(str) == pid)
            & (p2_links.comparison_id == cid)
            & (p2_links.focus_mode == "functional_p2")
        ]
        p50f = new_links[
            (new_links.participant_id.astype(str) == pid)
            & (new_links.comparison_id == cid)
            & (new_links.focus_mode == "functional_p50")
        ]
        if not p2f.empty and not p50f.empty:
            fig, axes = plt.subplots(1, 2, figsize=(10, 5), sharey=True)
            for ax, df, title in ((axes[0], p2f, "functional_p2"), (axes[1], p50f, "functional_p50")):
                agg = df.groupby("link_id")["JcvPCA_link"].mean().sort_values()
                ax.barh(agg.index, agg.values, color="purple")
                ax.set_title(title)
            fig.suptitle(f"p2 vs p50 functional | {pid} | {clabel}")
            _save_fig(
                fig,
                batch_root / "plots" / "p50_p60_vs_p2_sensitivity" / pid / bid / cid / "functional_p2_vs_p50.png",
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--batch-root",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "outputs"
        / "gaga_batch_jcvpca_20260626_193319",
    )
    parser.add_argument(
        "--only-comparison",
        type=str,
        default=None,
        help="Run a single comparison key, e.g. 671_A_L1_T1_vs_T2",
    )
    args = parser.parse_args()
    run_sensitivity(args.batch_root, only_key=args.only_comparison)


if __name__ == "__main__":
    main()
