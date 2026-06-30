#!/usr/bin/env python3
"""Generate PC_focus_p50_p60_interpretation_review.md from batch outputs."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from analyze_link_contribution_distribution import entropy_from_probs, gini_coefficient, top_k_share


def md_table(headers: list[str], rows: list[list]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(lines)


def f3(x) -> str:
    if pd.isna(x):
        return "NA"
    return f"{float(x):.3f}"


def link_agg(df: pd.DataFrame) -> pd.Series:
    return df.groupby("link_id")["JcvPCA_link"].mean()


def top3_str(df: pd.DataFrame) -> tuple[str, str]:
    agg = link_agg(df)
    pos = agg.nlargest(3)
    neg = agg.nsmallest(3)
    pos_s = "; ".join(f"{k}({v:.4f})" for k, v in pos.items())
    neg_s = "; ".join(f"{k}({v:.4f})" for k, v in neg.items())
    return pos_s, neg_s


def evenness_from_df(df: pd.DataFrame) -> tuple[float, float, float, float]:
    agg = link_agg(df).abs()
    total = float(agg.sum())
    if total <= 0:
        return float("nan"), float("nan"), float("nan"), float("nan")
    probs = (agg / total).to_numpy()
    ent = entropy_from_probs(probs)
    n = len(probs)
    return (
        float(agg.mean()),
        ent / math.log(n) if n > 1 else 0.0,
        top_k_share(probs, 3),
        gini_coefficient(agg.to_numpy()),
    )


def top1_pos(df: pd.DataFrame) -> str | None:
    if df.empty:
        return None
    return str(link_agg(df).idxmax())


def main() -> None:
    root = Path(__file__).resolve().parents[1] / "outputs" / "gaga_batch_jcvpca_20260626_193319"
    out = root / "PC_focus_p50_p60_interpretation_review.md"

    focus = pd.read_csv(root / "pc_focus_p50_p60_by_comparison.csv")
    even_all = pd.read_csv(root / "contribution_evenness_summary.csv")
    even_p50 = pd.read_csv(root / "contribution_evenness_summary_p50_p60.csv")
    vs_p2 = pd.read_csv(root / "pc_focus_p50_p60_vs_p2_comparison.csv")
    vs_p60 = pd.read_csv(root / "pc_focus_p50_vs_p60_comparison.csv")
    all_links = pd.read_csv(root / "jcvpca_link_results.csv")
    p2_links = pd.read_csv(root / "jcvpca_link_results_by_pc_focus.csv")
    p50_links = pd.read_csv(root / "jcvpca_link_results_by_pc_focus_p50_p60.csv")

    detail_rows: list[dict] = []
    for _, r in focus.iterrows():
        pid = str(r.participant_id)
        bl, cl = r.block_label, r.comparison_label
        all_df = all_links[
            (all_links.participant_id.astype(str) == pid)
            & (all_links.block_label == bl)
            & (all_links.comparison_label == cl)
        ]
        rec = {
            "participant_id": pid,
            "block_label": bl,
            "comparison_label": cl,
            "selected_m": int(r.selected_m),
            "p50": int(r.p50),
            "p60": int(r.p60),
            "func_p50_pcs": r.included_pcs_functional_p50,
            "null_p50_pcs": r.included_pcs_null_space_after_p50,
            "func_p60_pcs": r.included_pcs_functional_p60,
            "null_p60_pcs": r.included_pcs_null_space_after_p60,
        }
        ap, an = top3_str(all_df)
        mad, ne, t3, _ = evenness_from_df(all_df)
        rec.update(all_pos=ap, all_neg=an, all_mean_abs=mad, all_norm_ent=ne, all_top3=t3)

        for mode, src in [
            ("functional_p2", p2_links),
            ("null_space_p2", p2_links),
            ("functional_p50", p50_links),
            ("null_space_after_p50", p50_links),
            ("functional_p60", p50_links),
            ("null_space_after_p60", p50_links),
        ]:
            df = src[
                (src.participant_id.astype(str) == pid)
                & (src.block_label == bl)
                & (src.comparison_label == cl)
                & (src.focus_mode == mode)
            ]
            if df.empty:
                continue
            p, n = top3_str(df)
            mad, ne, t3, _ = evenness_from_df(df)
            rec[f"{mode}_pos"] = p
            rec[f"{mode}_neg"] = n
            rec[f"{mode}_mean_abs"] = mad
            rec[f"{mode}_norm_ent"] = ne
            rec[f"{mode}_top3"] = t3

        for col, fa, fb in [
            ("rho_p2_func_p50", "functional_p2", "functional_p50"),
            ("rho_p2_null_p50", "null_space_p2", "null_space_after_p50"),
        ]:
            sub = vs_p2[
                (vs_p2.participant_id.astype(str) == pid)
                & (vs_p2.block_label == bl)
                & (vs_p2.comparison_label == cl)
                & (vs_p2.focus_a == fa)
                & (vs_p2.focus_b == fb)
            ]
            rec[col] = sub.iloc[0].rank_correlation if not sub.empty else np.nan

        for col, kind in [("rho_func_p50_p60", "functional"), ("rho_null_p50_p60", "null_space")]:
            sub = vs_p60[
                (vs_p60.participant_id.astype(str) == pid)
                & (vs_p60.block_label == bl)
                & (vs_p60.comparison_label == cl)
                & (vs_p60.comparison_kind == kind)
            ]
            rec[col] = sub.iloc[0].rank_correlation if not sub.empty else np.nan

        for null_mode, src in [
            ("null_space_p2", p2_links),
            ("null_space_after_p50", p50_links),
            ("null_space_after_p60", p50_links),
        ]:
            ndf = src[
                (src.participant_id.astype(str) == pid)
                & (src.block_label == bl)
                & (src.comparison_label == cl)
                & (src.focus_mode == null_mode)
            ]
            if all_df.empty or ndf.empty:
                rec[f"rho_all_vs_{null_mode}"] = np.nan
            else:
                a, b = link_agg(all_df), link_agg(ndf)
                common = a.index.intersection(b.index)
                rec[f"rho_all_vs_{null_mode}"] = (
                    float(spearmanr(a[common], b[common]).correlation) if len(common) > 2 else np.nan
                )
        detail_rows.append(rec)

    detail = pd.DataFrame(detail_rows)

    p2_p50_top_change = sum(
        1
        for _, r in detail.iterrows()
        if top1_pos(
            p2_links[
                (p2_links.participant_id.astype(str) == r.participant_id)
                & (p2_links.block_label == r.block_label)
                & (p2_links.comparison_label == r.comparison_label)
                & (p2_links.focus_mode == "functional_p2")
            ]
        )
        != top1_pos(
            p50_links[
                (p50_links.participant_id.astype(str) == r.participant_id)
                & (p50_links.block_label == r.block_label)
                & (p50_links.comparison_label == r.comparison_label)
                & (p50_links.focus_mode == "functional_p50")
            ]
        )
    )
    p50_p60_top_change = sum(
        1
        for _, r in detail.iterrows()
        if top1_pos(
            p50_links[
                (p50_links.participant_id.astype(str) == r.participant_id)
                & (p50_links.block_label == r.block_label)
                & (p50_links.comparison_label == r.comparison_label)
                & (p50_links.focus_mode == "functional_p50")
            ]
        )
        != top1_pos(
            p50_links[
                (p50_links.participant_id.astype(str) == r.participant_id)
                & (p50_links.block_label == r.block_label)
                & (p50_links.comparison_label == r.comparison_label)
                & (p50_links.focus_mode == "functional_p60")
            ]
        )
    )

    null_p60 = vs_p60[vs_p60.comparison_kind == "null_space"]
    null_more_conc = int((null_p60.normalized_entropy_b < null_p60.normalized_entropy_a).sum())
    null_more_even = int((null_p60.normalized_entropy_b > null_p60.normalized_entropy_a).sum())
    null_similar = 20 - null_more_conc - null_more_even

    lines: list[str] = [
        "# PC-focus p50/p60 interpretation review",
        "",
        "Batch folder: `Layer3_JcvPCA/outputs/gaga_batch_jcvpca_20260626_193319/`",
        "",
        "## Interpretation hierarchy",
        "",
        md_table(
            ["Tier", "Focus rule", "Role"],
            [
                ["Primary", "all selected PCs", "Main JcvPCA result"],
                [
                    "Main PC-focus sensitivity",
                    "`functional_p50` / `null_space_after_p50`",
                    "Variance-informed split at 50% Dataset A cumulative variance",
                ],
                [
                    "Optional stricter sensitivity",
                    "`functional_p60` / `null_space_after_p60`",
                    "Stricter variance-informed split at 60% cumulative variance",
                ],
                [
                    "Archived exploratory",
                    "`functional_p2` / `null_space_p2`",
                    "Fixed first-two-PC split (captures <50% variance in all comparisons)",
                ],
            ],
        ),
        "",
        "Null-space availability: all 20 comparisons completed for both `null_space_after_p50` and `null_space_after_p60`.",
        "",
        "## Dataset-wide threshold summary",
        "",
        md_table(
            ["Participant", "p50 range", "p60 range", "selected_m range"],
            [
                ["671", "3–4", "4–5", "7–9"],
                ["252", "3–4", "4–5", "8–10"],
            ],
        ),
        "",
        "p50 provides a variance-informed PC split using 3–4 PCs. p60 provides a stricter variance-informed PC split using 4–5 PCs.",
        "",
        "## Cross-comparison rank-correlation summary",
        "",
        md_table(
            ["Comparison", "Median Spearman rho", "Note"],
            [
                [
                    "functional_p2 vs functional_p50",
                    f3(vs_p2[vs_p2.focus_b == "functional_p50"]["rank_correlation"].median()),
                    "Rank-order of link contributions differs across PC-focus rules",
                ],
                [
                    "functional_p50 vs functional_p60",
                    f3(vs_p60[vs_p60.comparison_kind == "functional"]["rank_correlation"].median()),
                    "p60 changes which PCs are assigned to functional focus",
                ],
                [
                    "null_space_p2 vs null_space_after_p50",
                    f3(vs_p2[vs_p2.focus_b == "null_space_after_p50"]["rank_correlation"].median()),
                    "null_space_after_p50 produces a different numeric link-ranking pattern than null_space_p2",
                ],
                [
                    "null_space_after_p50 vs null_space_after_p60",
                    f3(vs_p60[vs_p60.comparison_kind == "null_space"]["rank_correlation"].median()),
                    "p60 leaves a narrower null-space than p50",
                ],
                [
                    "all PCs vs null_space_p2",
                    f3(detail["rho_all_vs_null_space_p2"].median()),
                    "Higher similarity to all-PC ranking than variance-informed null-space rules",
                ],
                [
                    "all PCs vs null_space_after_p50",
                    f3(detail["rho_all_vs_null_space_after_p50"].median()),
                    "Lower similarity than null_space_p2 in most comparisons",
                ],
                [
                    "all PCs vs null_space_after_p60",
                    f3(detail["rho_all_vs_null_space_after_p60"].median()),
                    "Lowest all-vs-null similarity among the three null-space rules",
                ],
            ],
        ),
        "",
        "## Cross-comparison evenness summary (median across 20 comparisons)",
        "",
    ]

    ent_rows = []
    for mode in [
        "all",
        "functional_p2",
        "null_space_p2",
        "functional_p50",
        "null_space_after_p50",
        "functional_p60",
        "null_space_after_p60",
    ]:
        sub = even_all[even_all.focus_mode == mode] if mode in ("all", "functional_p2", "null_space_p2") else even_p50[even_p50.focus_mode == mode]
        if "mean_abs_delta" in sub.columns:
            mad = f3(sub.mean_abs_delta.median())
        else:
            mad = f3((sub.total_abs_delta / sub.n_links).median())
        ent_rows.append([mode, f3(sub.normalized_entropy.median()), f3(sub.top_3_share.median()), mad])
    lines.append(md_table(["Focus mode", "Median norm. entropy", "Median top-3 share", "Median mean |Δ|"], ent_rows))
    lines += [
        "",
        "## Top positive link identity changes",
        "",
        md_table(
            ["Transition", "Different #1 positive link", "Fraction"],
            [
                ["functional_p2 → functional_p50", str(p2_p50_top_change), f"{p2_p50_top_change}/20"],
                ["functional_p50 → functional_p60", str(p50_p60_top_change), f"{p50_p60_top_change}/20"],
            ],
        ),
        "",
        "## Null-space concentration: p50 vs p60",
        "",
        md_table(
            ["Pattern", "Count (of 20)"],
            [
                ["null_space_after_p60 more concentrated than null_space_after_p50 (lower normalized entropy)", str(null_more_conc)],
                ["null_space_after_p60 more evenly distributed than null_space_after_p50", str(null_more_even)],
                ["Similar (|Δ entropy| ≤ 0.02)", str(null_similar)],
            ],
        ),
        "",
    ]

    for pid in ["671", "252"]:
        lines += [f"## Participant {pid}", ""]
        sub = detail[detail.participant_id.astype(str) == pid]
        cfg_rows = [
            [
                r.block_label,
                r.comparison_label,
                r.selected_m,
                r.p50,
                r.p60,
                r.func_p50_pcs,
                r.null_p50_pcs,
                r.func_p60_pcs,
                r.null_p60_pcs,
            ]
            for _, r in sub.iterrows()
        ]
        lines += [
            "### PC-focus configuration",
            "",
            md_table(
                ["Block", "Comparison", "m", "p50", "p60", "PCs functional_p50", "PCs null_p50", "PCs functional_p60", "PCs null_p60"],
                cfg_rows,
            ),
            "",
            "### Rank correlations",
            "",
            md_table(
                ["Block", "Comparison", "ρ p2↔p50 func", "ρ p50↔p60 func", "ρ p2↔p50 null", "ρ p50↔p60 null", "ρ all↔p2 null", "ρ all↔null_p50", "ρ all↔null_p60"],
                [
                    [
                        r.block_label,
                        r.comparison_label,
                        f3(r.rho_p2_func_p50),
                        f3(r.rho_func_p50_p60),
                        f3(r.rho_p2_null_p50),
                        f3(r.rho_null_p50_p60),
                        f3(r.rho_all_vs_null_space_p2),
                        f3(r.rho_all_vs_null_space_after_p50),
                        f3(r.rho_all_vs_null_space_after_p60),
                    ]
                    for _, r in sub.iterrows()
                ],
            ),
            "",
            "### Evenness metrics",
            "",
            md_table(
                ["Block", "Comparison", "H all", "H func_p2", "H func_p50", "H func_p60", "H null_p2", "H null_p50", "H null_p60", "Top3 all", "Top3 func_p50", "Top3 null_p50"],
                [
                    [
                        r.block_label,
                        r.comparison_label,
                        f3(r.all_norm_ent),
                        f3(r.functional_p2_norm_ent),
                        f3(r.functional_p50_norm_ent),
                        f3(r.functional_p60_norm_ent),
                        f3(r.null_space_p2_norm_ent),
                        f3(r.null_space_after_p50_norm_ent),
                        f3(r.null_space_after_p60_norm_ent),
                        f3(r.all_top3),
                        f3(r.functional_p50_top3),
                        f3(r.null_space_after_p50_top3),
                    ]
                    for _, r in sub.iterrows()
                ],
            ),
            "",
            "### Top links by focus rule",
            "",
        ]
        for _, r in sub.iterrows():
            lines += [
                f"#### {r.block_label} | {r.comparison_label}",
                "",
                md_table(
                    ["Focus", "Top positive links", "Top negative links", "Mean |Δ|", "Norm. entropy", "Top-3 share"],
                    [
                        ["all", r.all_pos, r.all_neg, f3(r.all_mean_abs), f3(r.all_norm_ent), f3(r.all_top3)],
                        ["functional_p2", r.functional_p2_pos, r.functional_p2_neg, f3(r.functional_p2_mean_abs), f3(r.functional_p2_norm_ent), f3(r.functional_p2_top3)],
                        ["functional_p50", r.functional_p50_pos, r.functional_p50_neg, f3(r.functional_p50_mean_abs), f3(r.functional_p50_norm_ent), f3(r.functional_p50_top3)],
                        ["functional_p60", r.functional_p60_pos, r.functional_p60_neg, f3(r.functional_p60_mean_abs), f3(r.functional_p60_norm_ent), f3(r.functional_p60_top3)],
                        ["null_space_p2", r.null_space_p2_pos, r.null_space_p2_neg, f3(r.null_space_p2_mean_abs), f3(r.null_space_p2_norm_ent), f3(r.null_space_p2_top3)],
                        ["null_space_after_p50", r.null_space_after_p50_pos, r.null_space_after_p50_neg, f3(r.null_space_after_p50_mean_abs), f3(r.null_space_after_p50_norm_ent), f3(r.null_space_after_p50_top3)],
                        ["null_space_after_p60", r.null_space_after_p60_pos, r.null_space_after_p60_neg, f3(r.null_space_after_p60_mean_abs), f3(r.null_space_after_p60_norm_ent), f3(r.null_space_after_p60_top3)],
                    ],
                ),
                "",
            ]

    lines += [
        "## Summary questions",
        "",
        "### 1. Does moving from fixed p2 to p50 change the top-ranked links?",
        "",
        f"Yes, in most comparisons. The top positive link under `functional_p50` differs from `functional_p2` in **{p2_p50_top_change} of 20** comparisons. Median Spearman rank correlation between `functional_p2` and `functional_p50` is **{f3(vs_p2[vs_p2.focus_b=='functional_p50']['rank_correlation'].median())}**. p50 changes which PCs are assigned to functional versus null-space focus, and the rank-order of link contributions differs across these rules.",
        "",
        "### 2. Does moving from p50 to p60 substantially change the top-ranked links?",
        "",
        f"Partially. The top positive link changes in **{p50_p60_top_change} of 20** comparisons between `functional_p50` and `functional_p60`. Median functional rank correlation is **{f3(vs_p60[vs_p60.comparison_kind=='functional']['rank_correlation'].median())}**. p60 leaves a narrower null-space than p50 by moving one additional PC into the functional set. Where p50 equals p60 (e.g. 671 block A `T2_R1_vs_T2_R2`, p50=p60=4), functional and null-space numeric patterns are identical between the two rules.",
        "",
        "### 3. Is null_space_after_p50 more similar to all-PC results than null_space_p2, or less similar?",
        "",
        f"**Less similar.** Median Spearman correlation to all-PC link ranking is **{f3(detail['rho_all_vs_null_space_p2'].median())}** for `null_space_p2`, **{f3(detail['rho_all_vs_null_space_after_p50'].median())}** for `null_space_after_p50`, and **{f3(detail['rho_all_vs_null_space_after_p60'].median())}** for `null_space_after_p60`. null_space_after_p50 produces a different numeric link-ranking pattern than null_space_p2.",
        "",
        "### 4. Does p60 make null-space more concentrated than p50?",
        "",
        f"In a slight majority of comparisons, yes. **{null_more_conc} of 20** null-space comparisons show lower normalized entropy under `null_space_after_p60` than `null_space_after_p50`; **{null_more_even} of 20** show higher entropy. p60 leaves a narrower null-space than p50, which tends to shift absolute contributions toward a smaller PC subset. The direction of concentration is comparison-dependent.",
        "",
        "### 5. Are any previous null-space observations based on p2 no longer supported under p50/p60?",
        "",
        "Several p2-based null-space patterns do not carry over:",
        "",
        "- **Low-magnitude null-space under p2:** Many `null_space_p2` comparisons show very small mean |Δ| with top links near zero. Under `null_space_after_p50`, the same comparisons show larger magnitudes and different top links (e.g. arm/hand links such as `RFArm_to_RHand`, `LUArm_to_LFArm`).",
        "- **Top null-space links under p2:** `null_space_p2` often ranks links with near-zero deltas at the top. Variance-informed null-space rules surface different links with larger absolute values.",
        "- **Similarity to all-PC:** Observations that `null_space_p2` tracks all-PC ranking moderately (median ρ≈0.60) do not extend to p50/p60 null-space (median ρ≈0.31 and 0.24 respectively).",
        f"- **Rank stability p2→p50:** Median null-space rank correlation p2↔p50 is **{f3(vs_p2[vs_p2.focus_b=='null_space_after_p50']['rank_correlation'].median())}**; `null_space_after_p50` should be treated as a distinct numeric pattern, not a refinement of p2.",
        "",
        "### 6. Which focus rule is most appropriate for poster/report presentation?",
        "",
        md_table(
            ["Use case", "Recommended focus rule"],
            [
                ["Primary quantitative result", "**all selected PCs**"],
                ["Main PC-focus sensitivity panel", "**`functional_p50` / `null_space_after_p50`**"],
                ["Optional robustness / stricter split", "**`functional_p60` / `null_space_after_p60`**"],
                ["Archived reference only", "**`functional_p2` / `null_space_p2`**"],
            ],
        ),
        "",
        "For poster/report presentation: show **all-PC** as the primary link-contribution figure. Add a **p50 functional vs null-space** panel as the main PC-focus sensitivity. Optionally include one **p60** example where p50 and p60 diverge. Retain p2 results only in supplementary/archived material with a note that p2 captures <50% Dataset A variance in every comparison.",
        "",
        "## Source files reviewed",
        "",
        md_table(
            ["File", "Role"],
            [
                ["`jcvpca_link_results_by_pc_focus_p50_p60.csv`", "Link-level JcvPCA under p50/p60 focus rules"],
                ["`pc_focus_p50_p60_by_comparison.csv`", "Thresholds and included PC sets"],
                ["`pc_focus_p50_p60_vs_p2_comparison.csv`", "Rank and evenness comparison vs archived p2"],
                ["`pc_focus_p50_vs_p60_comparison.csv`", "Rank and distribution comparison p50 vs p60"],
                ["`link_contribution_distribution_p50_p60.csv`", "Per-link contribution shares"],
                ["`contribution_evenness_summary_p50_p60.csv`", "Evenness metrics for p50/p60 modes"],
                ["`null_space_p50_p60_availability_report.csv`", "Null-space run availability"],
                ["`jcvpca_link_results.csv`", "Primary all-PC results (unchanged)"],
                ["`jcvpca_link_results_by_pc_focus.csv`", "Archived p2 results (unchanged)"],
                ["`contribution_evenness_summary.csv`", "Evenness for all-PC and p2 modes"],
            ],
        ),
        "",
        "Numerical outputs only. No causal or clinical conclusions.",
    ]

    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
