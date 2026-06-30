#!/usr/bin/env python3
"""Directional robustness of T1 vs T3 link-level JcvPCA across repetition pairings."""

from __future__ import annotations

import json
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from layer3_jcvpca.dataset_builder import (  # noqa: E402
    CONSTRUCTION_PASS,
    DatasetConstructionResult,
    REQUIRED_METADATA_COLUMNS,
    _build_side_preview,
    write_dataset_construction_artifacts,
)
from layer3_jcvpca.gaga_batch_runner import (  # noqa: E402
    STATUS_BLOCKED_PREFLIGHT,
    STATUS_COMPLETED,
    STATUS_SKIPPED_MISSING,
    TARGET_PARTICIPANTS,
    _run_focus_sensitivity_pipeline,
    _run_workbench_pipeline,
    block_label_for_id,
)
from layer3_jcvpca.step_runner import StepRunError  # noqa: E402
from layer3_jcvpca.workbench_preflight import (  # noqa: E402
    load_construction_artifacts,
    run_workbench_preflight,
    save_preflight_acknowledgment,
    write_workbench_preflight_artifacts,
)
from layer3_jcvpca.pc_focus import PC_FOCUS_FUNCTIONAL, PC_FOCUS_NULL_SPACE, PcFocusParameters  # noqa: E402

BATCH = ROOT / "outputs" / "gaga_batch_jcvpca_20260626_193319"
ANALYSIS_MODE = "longitudinal"

FOCUS_MODES = [
    "all",
    "functional_p50",
    "null_space_after_p50",
    "functional_p60",
    "null_space_after_p60",
]

POOLED_VARIANT = "T1_R1_R2_vs_T3_R1_R2"
POOLED_VARIANT_ID = "DR_pooled_T1_vs_T3"
POOLED_COMPARISON_LABEL = "T1_vs_T3"


def csv_path(path: Path | str) -> Path:
    p = Path(path)
    return p if p.suffix == ".csv" else Path(f"{p}.csv")


def read_csv(path: Path | str) -> pd.DataFrame:
    return pd.read_csv(csv_path(path))


@dataclass(frozen=True)
class VariantSpec:
    variant_id: str
    variant_label: str
    a_repetitions: tuple[str, ...]
    b_repetitions: tuple[str, ...]
    use_batch: bool = False


VARIANTS: list[VariantSpec] = [
    VariantSpec("DR_T1R1_vs_T3R1", "T1_R1_vs_T3_R1", ("R1",), ("R1",)),
    VariantSpec("DR_T1R2_vs_T3R2", "T1_R2_vs_T3_R2", ("R2",), ("R2",)),
    VariantSpec(POOLED_VARIANT_ID, POOLED_VARIANT, ("R1", "R2"), ("R1", "R2"), use_batch=True),
    VariantSpec("DR_T1R1_vs_T3R2", "T1_R1_vs_T3_R2", ("R1",), ("R2",)),
    VariantSpec("DR_T1R2_vs_T3R1", "T1_R2_vs_T3_R1", ("R2",), ("R1",)),
]


def f4(x) -> str:
    if x is None or (isinstance(x, float) and (np.isnan(x) or np.isinf(x))):
        return "NA"
    if pd.isna(x):
        return "NA"
    return f"{float(x):.4f}"


def md_table(headers: list[str], rows: list[list]) -> str:
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(out)


def p_at_threshold(cum: np.ndarray, threshold: float) -> int:
    hit = np.where(cum >= threshold)[0]
    return int(hit[0] + 1) if hit.size else int(len(cum))


def load_p_thresholds(run_dir: Path) -> tuple[int, int, int]:
    cum = pd.read_csv(run_dir / "pca_A_cumulative_variance.csv")["cumulative_explained_variance"].to_numpy()
    selected_m = int(json.loads((run_dir / "pca_A_selected_m.json").read_text(encoding="utf-8"))["selected_m"])
    p50 = p_at_threshold(cum, 0.50)
    p60 = p_at_threshold(cum, 0.60)
    return p50, p60, selected_m


def aggregate_link_csv(path: Path) -> pd.DataFrame:
    df = read_csv(path)
    return (
        df.groupby("link_id", as_index=False)
        .agg(
            JRW_A_link=("JRW_A_link", "mean"),
            JRW_B_link=("JRW_B_link", "mean"),
            JcvPCA_link=("JcvPCA_link", "mean"),
        )
        .sort_values("link_id")
    )


def enrich_link_table(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["delta_sign"] = np.sign(out["JcvPCA_link"]).astype(int)
    out["abs_delta"] = out["JcvPCA_link"].abs()
    out["rank_by_abs_delta"] = out["abs_delta"].rank(ascending=False, method="min").astype(int)
    return out


def load_pooled_from_batch(participant_id: str, block_label: str, focus_mode: str) -> pd.DataFrame:
    if focus_mode == "all":
        src = pd.read_csv(BATCH / "jcvpca_link_results.csv")
    else:
        src = pd.read_csv(BATCH / "jcvpca_link_results_by_pc_focus.csv")
    sub = src[
        (src.participant_id.astype(str) == participant_id)
        & (src.block_label == block_label)
        & (src.comparison_label == POOLED_COMPARISON_LABEL)
        & (src.focus_mode == focus_mode)
    ]
    if sub.empty:
        return pd.DataFrame()
    return aggregate_link_csv_from_long(sub)


def aggregate_link_csv_from_long(sub: pd.DataFrame) -> pd.DataFrame:
    return (
        sub.groupby("link_id", as_index=False)
        .agg(
            JRW_A_link=("JRW_A_link", "mean"),
            JRW_B_link=("JRW_B_link", "mean"),
            JcvPCA_link=("JcvPCA_link", "mean"),
        )
        .sort_values("link_id")
    )


def load_from_run(run_dir: Path, focus_mode: str) -> pd.DataFrame:
    if focus_mode == "all":
        path = run_dir / "link_level_jrw_rss.csv"
    else:
        path = run_dir.parent / f"run_{focus_mode}" / "link_level_jrw_rss.csv"
    if not path.is_file():
        return pd.DataFrame()
    return aggregate_link_csv(path)


def pooled_construction_dir(participant_id: str, block_id: str) -> Path:
    return BATCH / "comparisons" / f"{participant_id}_{block_id}_L2_T1_vs_T3" / "construction"


def build_variant_from_pooled_construction(
    participant_id: str,
    block_id: str,
    variant: VariantSpec,
) -> tuple[str, str]:
    """Build filtered datasets from pooled T1_vs_T3 construction and run JcvPCA workbench."""
    construction_src = pooled_construction_dir(participant_id, block_id)
    if not construction_src.is_dir():
        return "missing_pooled_construction", "Pooled construction artifacts not found"

    a_src = read_csv(construction_src / "dataset_A_sources")
    b_src = read_csv(construction_src / "dataset_B_sources")
    a_filt = a_src[a_src["repetition"].astype(str).isin(variant.a_repetitions)].copy()
    b_filt = b_src[b_src["repetition"].astype(str).isin(variant.b_repetitions)].copy()
    a_filt = a_filt.sort_values(["repetition", "gaga_exercise_label"]).reset_index(drop=True)
    b_filt = b_filt.sort_values(["repetition", "gaga_exercise_label"]).reset_index(drop=True)

    if a_filt.empty or b_filt.empty:
        return STATUS_SKIPPED_MISSING, (
            f"No sources after repetition filter A={variant.a_repetitions} "
            f"B={variant.b_repetitions}"
        )

    feat_df = read_csv(construction_src / "dataset_feature_columns")
    pca_feature_columns = feat_df.loc[feat_df["included_in_pca"] == True, "column_name"].tolist()
    metadata_columns = feat_df.loc[feat_df["column_role"] == "metadata", "column_name"].tolist()
    if not metadata_columns:
        metadata_columns = list(REQUIRED_METADATA_COLUMNS)

    blocking: list[dict] = []
    dataset_a = _build_side_preview(
        a_filt,
        dataset_side="A",
        pca_feature_columns=pca_feature_columns,
        metadata_columns=metadata_columns,
        blocking_records=blocking,
    )
    dataset_b = _build_side_preview(
        b_filt,
        dataset_side="B",
        pca_feature_columns=pca_feature_columns,
        metadata_columns=metadata_columns,
        blocking_records=blocking,
    )
    if blocking:
        msgs = [str(r.get("reason_message", "")) for r in blocking[:3]]
        return STATUS_SKIPPED_MISSING, "; ".join(msgs) or "Dataset construction blocked"

    plan = json.loads((construction_src / "dataset_construction_plan.json").read_text(encoding="utf-8"))
    summary = json.loads((construction_src / "dataset_construction_summary.json").read_text(encoding="utf-8"))
    summary.update(
        {
            "dataset_a_total_rows": dataset_a.total_rows,
            "dataset_b_total_rows": dataset_b.total_rows,
            "dataset_a_source_matrices": dataset_a.n_source_matrices,
            "dataset_b_source_matrices": dataset_b.n_source_matrices,
            "row_counts_equal": dataset_a.total_rows == dataset_b.total_rows,
            "construction_status": CONSTRUCTION_PASS,
            "n_blocking_errors": 0,
        }
    )

    preview = DatasetConstructionResult()
    preview.dataset_a = dataset_a
    preview.dataset_b = dataset_b
    preview.pca_feature_columns = pca_feature_columns
    preview.metadata_columns = metadata_columns
    preview.feature_columns = feat_df
    preview.plan = plan
    preview.summary = summary
    preview.construction_status = CONSTRUCTION_PASS
    preview.warnings = pd.DataFrame()
    preview.blocking_errors = pd.DataFrame()

    comp_root = BATCH / "comparisons" / f"{participant_id}_{block_id}_{variant.variant_id}"
    construction_dir = comp_root / "construction"
    preflight_dir = comp_root / "preflight"
    run_dir = comp_root / "run"

    write_dataset_construction_artifacts(preview, construction_dir)
    bundle = load_construction_artifacts(construction_dir)
    preflight = run_workbench_preflight(bundle, warnings_acknowledged=True)
    write_workbench_preflight_artifacts(preflight, preflight_dir)
    save_preflight_acknowledgment(
        preflight_dir, acknowledged=True, preflight_summary=preflight.summary
    )
    if preflight.summary.get("preflight_status") == "blocking":
        return STATUS_BLOCKED_PREFLIGHT, "; ".join(
            preflight.summary.get("messages") or ["Preflight blocking."]
        )

    try:
        run_dir.mkdir(parents=True, exist_ok=True)
        _run_workbench_pipeline(run_dir, construction_dir, preflight_dir)
    except StepRunError as exc:
        if not csv_path(run_dir / "link_level_jrw_rss").is_file():
            return "failed_error", f"{type(exc).__name__}: {exc}\n{traceback.format_exc()[:500]}"
    except Exception as exc:  # noqa: BLE001 — capture per-variant failures
        if not csv_path(run_dir / "link_level_jrw_rss").is_file():
            return "failed_error", f"{type(exc).__name__}: {exc}\n{traceback.format_exc()[:500]}"

    if not csv_path(run_dir / "link_level_jrw_rss").is_file():
        return "failed_error", "Workbench finished without link_level_jrw_rss output."

    return STATUS_COMPLETED, str(run_dir)


def run_p50_p60_focus(
    main_run: Path,
    construction: Path,
    preflight: Path,
) -> dict[str, Path]:
    p50, p60, selected_m = load_p_thresholds(main_run)
    out: dict[str, Path] = {"all": main_run}
    specs = [
        ("functional_p50", PC_FOCUS_FUNCTIONAL, p50),
        ("null_space_after_p50", PC_FOCUS_NULL_SPACE, p50),
        ("functional_p60", PC_FOCUS_FUNCTIONAL, p60),
        ("null_space_after_p60", PC_FOCUS_NULL_SPACE, p60),
    ]
    for label, mode, p in specs:
        if label.startswith("null_space") and p >= selected_m:
            continue
        focus_dir = main_run.parent / f"run_{label}"
        try:
            fr = _run_focus_sensitivity_pipeline(
                main_run,
                construction_dir=construction,
                preflight_dir=preflight,
                focus_label=label,
                pc_focus_params=PcFocusParameters(pc_focus_mode=mode, p=p),
            )
        except StepRunError:
            if csv_path(focus_dir / "link_level_jrw_rss").is_file():
                out[label] = focus_dir
            continue
        if fr.status == STATUS_COMPLETED and fr.run_dir:
            out[label] = Path(fr.run_dir)
        elif csv_path(focus_dir / "link_level_jrw_rss").is_file():
            out[label] = focus_dir
    return out


def ensure_variant_run(
    participant_id: str,
    block_id: str,
    variant: VariantSpec,
) -> tuple[str, dict[str, Path]]:
    if variant.use_batch:
        comp_key = f"{participant_id}_{block_id}_L2_T1_vs_T3"
        run_dir = BATCH / "comparisons" / comp_key / "run"
        paths = {"all": run_dir}
        if run_dir.is_dir() or (run_dir / "link_level_jrw_rss.csv").is_file():
            for fm in FOCUS_MODES[1:]:
                p = BATCH / "comparisons" / comp_key / f"run_{fm}"
                if (p / "link_level_jrw_rss.csv").is_file():
                    paths[fm] = p
            return STATUS_COMPLETED, paths
        return "missing_batch_run", {}

    comp_root = BATCH / "comparisons" / f"{participant_id}_{block_id}_{variant.variant_id}"
    run_dir = comp_root / "run"
    construction = comp_root / "construction"
    preflight = comp_root / "preflight"
    if csv_path(run_dir / "link_level_jrw_rss").is_file():
        paths = run_p50_p60_focus(run_dir, construction, preflight)
        return STATUS_COMPLETED, paths

    status, run_path = build_variant_from_pooled_construction(participant_id, block_id, variant)
    if status != STATUS_COMPLETED:
        return status, {}
    main_run = Path(run_path)
    paths = run_p50_p60_focus(main_run, construction, preflight)
    return status, paths


def get_variant_links(
    participant_id: str,
    block_label: str,
    variant: VariantSpec,
    focus_mode: str,
    run_paths: dict[str, Path],
) -> pd.DataFrame:
    if variant.use_batch:
        raw = load_pooled_from_batch(participant_id, block_label, focus_mode)
    else:
        run_dir = run_paths.get(focus_mode) or run_paths.get("all")
        raw = load_from_run(run_dir, focus_mode) if run_dir else pd.DataFrame()
    if raw.empty:
        return raw
    raw = enrich_link_table(raw)
    raw.insert(0, "focus_mode", focus_mode)
    raw.insert(0, "comparison_variant", variant.variant_label)
    raw.insert(0, "block_label", block_label)
    raw.insert(0, "participant_id", participant_id)
    return raw


def compare_variant_to_pooled(pooled: pd.DataFrame, variant: pd.DataFrame) -> pd.DataFrame:
    if pooled.empty or variant.empty:
        return pd.DataFrame()
    m = pooled.merge(variant, on="link_id", suffixes=("_pooled", "_variant"))
    m["sign_agreement"] = m["delta_sign_pooled"] == m["delta_sign_variant"]
    m["rank_shift"] = m["rank_by_abs_delta_variant"] - m["rank_by_abs_delta_pooled"]
    return m[
        [
            "link_id",
            "JcvPCA_link_pooled",
            "JcvPCA_link_variant",
            "delta_sign_pooled",
            "delta_sign_variant",
            "sign_agreement",
            "abs_delta_pooled",
            "abs_delta_variant",
            "rank_by_abs_delta_pooled",
            "rank_by_abs_delta_variant",
            "rank_shift",
        ]
    ]


def summarize_pair(pooled: pd.DataFrame, variant: pd.DataFrame, cmp: pd.DataFrame) -> dict:
    if pooled.empty or variant.empty or cmp.empty:
        return {
            "percent_sign_agreement_all_links": np.nan,
            "percent_sign_agreement_top5_pooled_links": np.nan,
            "spearman_rho_delta": np.nan,
            "spearman_rho_abs_rank": np.nan,
            "top5_pooled_same_sign_count": np.nan,
            "top5_pooled_in_variant_top5_count": np.nan,
            "n_links": 0,
        }
    n = len(cmp)
    top5 = pooled.nlargest(5, "abs_delta")["link_id"].tolist()
    cmp_top5 = cmp[cmp.link_id.isin(top5)]
    variant_top5 = set(variant.nlargest(5, "abs_delta").link_id.tolist())
    rho_delta = float(spearmanr(cmp.JcvPCA_link_pooled, cmp.JcvPCA_link_variant).correlation) if n >= 2 else np.nan
    rho_rank = float(spearmanr(cmp.rank_by_abs_delta_pooled, cmp.rank_by_abs_delta_variant).correlation) if n >= 2 else np.nan
    return {
        "percent_sign_agreement_all_links": 100.0 * float(cmp.sign_agreement.mean()),
        "percent_sign_agreement_top5_pooled_links": 100.0 * float(cmp_top5.sign_agreement.mean()) if len(cmp_top5) else np.nan,
        "spearman_rho_delta": rho_delta,
        "spearman_rho_abs_rank": rho_rank,
        "top5_pooled_same_sign_count": int(cmp_top5.sign_agreement.sum()) if len(cmp_top5) else 0,
        "top5_pooled_in_variant_top5_count": int(sum(l in variant_top5 for l in top5)),
        "n_links": n,
    }


def main() -> None:
    link_rows: list[pd.DataFrame] = []
    consistency_rows: list[pd.DataFrame] = []
    summary_rows: list[dict] = []
    run_log: list[dict] = []

    pooled_spec = next(v for v in VARIANTS if v.use_batch)

    for participant_id in TARGET_PARTICIPANTS:
        for block_id in ("A", "B"):
            block_label = block_label_for_id(block_id)
            pooled_paths: dict[str, Path] = {}
            pooled_by_focus: dict[str, pd.DataFrame] = {}

            status, paths = ensure_variant_run(participant_id, block_id, pooled_spec)
            run_log.append({"participant_id": participant_id, "block_id": block_id, "variant": pooled_spec.variant_label, "status": status})
            pooled_paths = paths

            for fm in FOCUS_MODES:
                pooled_by_focus[fm] = get_variant_links(participant_id, block_label, pooled_spec, fm, pooled_paths)

            for variant in VARIANTS:
                if variant.use_batch:
                    vpaths = pooled_paths
                    vstatus = status
                else:
                    vstatus, vpaths = ensure_variant_run(participant_id, block_id, variant)
                    run_log.append({"participant_id": participant_id, "block_id": block_id, "variant": variant.variant_label, "status": vstatus})

                for fm in FOCUS_MODES:
                    vdf = get_variant_links(participant_id, block_label, variant, fm, vpaths)
                    if not vdf.empty:
                        link_rows.append(vdf)

                    if variant.use_batch:
                        continue
                    pdf = pooled_by_focus.get(fm, pd.DataFrame())
                    if vdf.empty or pdf.empty:
                        continue
                    cmp = compare_variant_to_pooled(pdf, vdf)
                    if cmp.empty:
                        continue
                    cmp.insert(0, "focus_mode", fm)
                    cmp.insert(0, "comparison_variant", variant.variant_label)
                    cmp.insert(0, "reference_variant", POOLED_VARIANT)
                    cmp.insert(0, "block_label", block_label)
                    cmp.insert(0, "participant_id", participant_id)
                    consistency_rows.append(cmp)
                    summary_rows.append(
                        {
                            "participant_id": participant_id,
                            "block_label": block_label,
                            "comparison_variant": variant.variant_label,
                            "reference_variant": POOLED_VARIANT,
                            "focus_mode": fm,
                            "run_status": vstatus,
                            **summarize_pair(pdf, vdf, cmp),
                        }
                    )

    link_out = pd.concat(link_rows, ignore_index=True) if link_rows else pd.DataFrame()
    if not link_out.empty:
        link_out = link_out.rename(
            columns={
                "JRW_A_link": "JRW_A",
                "JRW_B_link": "JRW_B",
                "JcvPCA_link": "JcvPCA_link_delta",
                "delta_sign": "sign_of_delta",
            }
        )
        link_out.to_csv(BATCH / "directional_robustness_t1_t3_link_results.csv", index=False)

    summary = pd.DataFrame(summary_rows)
    if not summary.empty:
        summary.to_csv(BATCH / "directional_robustness_t1_t3_summary.csv", index=False)

    cons_out = pd.concat(consistency_rows, ignore_index=True) if consistency_rows else pd.DataFrame()

    top_rows: list[dict] = []
    if not link_out.empty and not cons_out.empty:
        for (pid, bl, fm), pooled_sub in link_out[
            link_out.comparison_variant == POOLED_VARIANT
        ].groupby(["participant_id", "block_label", "focus_mode"]):
            top5 = pooled_sub.nlargest(5, "abs_delta")
            for _, prow in top5.iterrows():
                row = {
                    "participant_id": pid,
                    "block_label": bl,
                    "focus_mode": fm,
                    "link_id": prow.link_id,
                    "pooled_delta": prow.JcvPCA_link_delta,
                    "pooled_sign": int(prow.sign_of_delta),
                    "pooled_rank_by_abs": int(prow.rank_by_abs_delta),
                }
                for variant in VARIANTS:
                    if variant.use_batch:
                        continue
                    vsub = link_out[
                        (link_out.participant_id == pid)
                        & (link_out.block_label == bl)
                        & (link_out.focus_mode == fm)
                        & (link_out.comparison_variant == variant.variant_label)
                        & (link_out.link_id == prow.link_id)
                    ]
                    csub = cons_out[
                        (cons_out.participant_id == pid)
                        & (cons_out.block_label == bl)
                        & (cons_out.focus_mode == fm)
                        & (cons_out.comparison_variant == variant.variant_label)
                        & (cons_out.link_id == prow.link_id)
                    ]
                    if not vsub.empty:
                        row[f"{variant.variant_label}_delta"] = float(vsub.iloc[0].JcvPCA_link_delta)
                        row[f"{variant.variant_label}_sign"] = int(vsub.iloc[0].sign_of_delta)
                    if not csub.empty:
                        row[f"{variant.variant_label}_sign_agreement"] = bool(csub.iloc[0].sign_agreement)
                        row[f"{variant.variant_label}_rank_shift"] = int(csub.iloc[0].rank_shift)
                top_rows.append(row)
    top = pd.DataFrame(top_rows)
    if not top.empty:
        top.to_csv(BATCH / "directional_robustness_t1_t3_top_links.csv", index=False)

    write_review(link_out, summary, cons_out, run_log)
    print(f"Directional robustness analysis complete: {BATCH}")


def write_review(
    links: pd.DataFrame,
    summary: pd.DataFrame,
    consistency: pd.DataFrame,
    run_log: list[dict],
) -> None:
    lines = [
        "# Directional robustness review — T1 vs T3 repetition pairings",
        "",
        f"Batch folder: `Layer3_JcvPCA/outputs/{BATCH.name}/`",
        "",
        "Link-level JcvPCA Delta direction compared across repetition-specific T1 vs T3 pairings.",
        "Reference comparison: pooled `T1_R1+R2` vs `T3_R1+R2` (batch `T1_vs_T3`).",
        "",
        "## Analysis hierarchy",
        "",
        md_table(
            ["Tier", "Focus modes"],
            [
                ["Primary", "all selected PCs"],
                ["Main sensitivity", "functional_p50 / null_space_after_p50"],
                ["Optional", "functional_p60 / null_space_after_p60"],
            ],
        ),
        "",
        "## Comparison variants",
        "",
        md_table(
            ["Variant label", "Dataset A repetitions", "Dataset B repetitions"],
            [[v.variant_label, ", ".join(v.a_repetitions), ", ".join(v.b_repetitions)] for v in VARIANTS],
        ),
        "",
        "## Run status",
        "",
        md_table(
            ["Participant", "Block", "Variant", "Status"],
            [[r["participant_id"], r["block_id"], r["variant"], r["status"]] for r in run_log],
        ),
        "",
    ]

    if not summary.empty:
        all_primary = summary[summary.focus_mode == "all"]
        if not all_primary.empty:
            med_sign = float(all_primary.percent_sign_agreement_all_links.median())
            med_rho = float(all_primary.spearman_rho_delta.median())
            lines += [
                "## Summary metrics (all-PC, primary)",
                "",
                md_table(
                    ["Participant", "Block", "Variant", "Sign agreement %", "Top5 sign agreement %", "Spearman rho (Delta)", "Spearman rho (rank)", "Top5 same sign", "Top5 in variant top5"],
                    [
                        [
                            r.participant_id, r.block_label, r.comparison_variant,
                            f4(r.percent_sign_agreement_all_links),
                            f4(r.percent_sign_agreement_top5_pooled_links),
                            f4(r.spearman_rho_delta),
                            f4(r.spearman_rho_abs_rank),
                            int(r.top5_pooled_same_sign_count) if pd.notna(r.top5_pooled_same_sign_count) else "NA",
                            int(r.top5_pooled_in_variant_top5_count) if pd.notna(r.top5_pooled_in_variant_top5_count) else "NA",
                        ]
                        for _, r in all_primary.sort_values(["participant_id", "block_label", "comparison_variant"]).iterrows()
                    ],
                ),
                "",
                f"Median all-link sign agreement vs pooled: **{f4(med_sign)}%**. Median Spearman rho (Delta): **{f4(med_rho)}**.",
                "",
            ]

    # Review questions
    stable_links: list[str] = []
    stable_by_participant: dict[str, list[str]] = {}
    flip_links: list[str] = []
    if not consistency.empty:
        all_cons = consistency[consistency.focus_mode == "all"]
        if not all_cons.empty:
            by_link = all_cons.groupby("link_id")["sign_agreement"].mean()
            stable_links = by_link[by_link == 1.0].index.tolist()
            flip_links = by_link[by_link < 1.0].index.tolist()
            for pid, sub in all_cons.groupby("participant_id"):
                per_link = sub.groupby("link_id")["sign_agreement"].all()
                stable_by_participant[str(pid)] = per_link[per_link].index.tolist()

    block_stability = {}
    part_stability = {}
    if not summary.empty:
        primary = summary[summary.focus_mode == "all"]
        block_stability = primary.groupby("block_label")["percent_sign_agreement_all_links"].mean().to_dict()
        part_stability = {
            str(k): float(v)
            for k, v in primary.groupby("participant_id")["percent_sign_agreement_all_links"].mean().items()
        }

    lines += [
        "## Review questions",
        "",
        "### 1. Is the direction of change preserved across repetition pairings?",
        "",
    ]
    if summary.empty:
        lines.append("Insufficient data to assess.")
    else:
        med = float(summary[summary.focus_mode == "all"].percent_sign_agreement_all_links.median())
        same_rep = summary[(summary.focus_mode == "all") & summary.comparison_variant.isin(["T1_R1_vs_T3_R1", "T1_R2_vs_T3_R2"])]
        cross_rep = summary[(summary.focus_mode == "all") & summary.comparison_variant.isin(["T1_R1_vs_T3_R2", "T1_R2_vs_T3_R1"])]
        same_mean = float(same_rep.percent_sign_agreement_all_links.mean()) if not same_rep.empty else float("nan")
        cross_mean = float(cross_rep.percent_sign_agreement_all_links.mean()) if not cross_rep.empty else float("nan")
        lines.append(
            f"Across all-PC variant comparisons, median link-level sign agreement with the pooled T1_vs_T3 reference is **{f4(med)}%** "
            f"(below 100%, so direction is not uniform across pairings). "
            f"Mean agreement: same-repetition pairings **{f4(same_mean)}%**, cross-repetition pairings **{f4(cross_mean)}%**; "
            "patterns vary by participant and block."
        )
    lines += [
        "",
        "### 2. Which links have stable direction across all pairings?",
        "",
    ]
    if stable_links:
        lines.append(", ".join(f"`{l}`" for l in stable_links[:20]) + (" ..." if len(stable_links) > 20 else ""))
    elif stable_by_participant:
        for pid, links in stable_by_participant.items():
            if links:
                lines.append(f"Participant {pid}: " + ", ".join(f"`{l}`" for l in links))
        if not any(stable_by_participant.values()):
            lines.append("No link matches the pooled sign in all four repetition pairings for either participant (all-PC).")
    else:
        lines.append("No link shows sign agreement in every variant under all-PC; see summary tables for link-specific detail.")
    lines += ["", "### 3. Which links change sign depending on pairing?", ""]
    if flip_links:
        lines.append(", ".join(f"`{l}`" for l in flip_links[:25]) + (" ..." if len(flip_links) > 25 else ""))
    else:
        lines.append("None identified in all-PC consistency output.")
    lines += [
        "",
        "### 4. Does the pooled T1_vs_T3 result reflect the individual repetition pairings?",
        "",
    ]
    if not summary.empty:
        same_rep = summary[(summary.focus_mode == "all") & summary.comparison_variant.isin(["T1_R1_vs_T3_R1", "T1_R2_vs_T3_R2"])]
        cross_rep = summary[(summary.focus_mode == "all") & summary.comparison_variant.isin(["T1_R1_vs_T3_R2", "T1_R2_vs_T3_R1"])]
        if not same_rep.empty and not cross_rep.empty:
            same_mean = float(same_rep.percent_sign_agreement_all_links.mean())
            cross_mean = float(cross_rep.percent_sign_agreement_all_links.mean())
            closer = "same-repetition" if same_mean >= cross_mean else "cross-repetition"
            lines.append(
                f"Same-repetition pairings: mean sign agreement **{f4(same_mean)}%**; "
                f"cross-repetition pairings: **{f4(cross_mean)}%**. "
                f"On average, pooled T1_vs_T3 link signs align more closely with **{closer}** pairings."
            )
    lines += [
        "",
        "### 5. Are results more stable in all_P1_P2_P3_P4_P5 or P3_P4_P5?",
        "",
    ]
    if block_stability:
        lines.append(
            f"Mean all-link sign agreement — all_P1_P2_P3_P4_P5: **{f4(block_stability.get('all_P1_P2_P3_P4_P5', np.nan))}%**; "
            f"P3_P4_P5: **{f4(block_stability.get('P3_P4_P5', np.nan))}%**."
        )
    lines += [
        "",
        "### 6. Are results more stable for participant 671 or 252?",
        "",
    ]
    if part_stability:
        lines.append(
            f"Mean all-link sign agreement — 671: **{f4(part_stability.get('671', np.nan))}%**; "
            f"252: **{f4(part_stability.get('252', np.nan))}%**."
        )
    lines += [
        "",
        "## Limitations",
        "",
        "- Directional robustness is descriptive; no causal or condition-specific claims.",
        "- Variant comparisons rerun JcvPCA with the same workbench method; pooled reference uses the existing batch T1_vs_T3 output.",
        "- Participants 671 and 252 use different link schemas.",
        "- Single-repetition variant runs stop after link-level RSS (step 14); NV baseline (step 16A) is skipped when only one repetition is present.",
        "- PC-focus modes depend on Dataset A cumulative variance thresholds per variant run.",
        "",
    ]
    (BATCH / "directional_robustness_t1_t3_review.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
