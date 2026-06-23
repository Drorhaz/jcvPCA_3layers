"""Output writers for Layer 3 JcvPCA.

All writers emit neutral, auditable artifacts (JSON / CSV / a factual markdown
summary). Nothing here classifies a change as significant, robust, meaningful,
or beyond variability. Such judgements are made later, outside this package.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


def ensure_output_dir(output_dir: str | Path) -> Path:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: str | Path, payload: dict) -> None:
    Path(path).write_text(json.dumps(payload, indent=2, default=_json_default))


def write_csv(path: str | Path, df: pd.DataFrame) -> None:
    df.to_csv(path, index=False)


def write_validation_report(output_dir: str | Path, report: dict) -> Path:
    out = ensure_output_dir(output_dir) / "validation_report.json"
    write_json(out, report)
    return out


def write_analysis_metadata(output_dir: str | Path, metadata: dict) -> Path:
    out = ensure_output_dir(output_dir) / "analysis_metadata.json"
    write_json(out, metadata)
    return out


def build_analysis_metadata(
    *,
    subject_id: str,
    part_id: str,
    group_id: str,
    feature_names: list[str],
    joint_link_map: dict,
    selected_m: int,
    variance_threshold: float,
    repetitions_used: dict,
    comparison_timepoints: list[str],
    export_weighted: bool,
) -> dict:
    """Assemble the analysis_metadata.json payload.

    Records the fixed computational rules (centering, normalisation, sign
    convention, aggregation, natural-variability construction, timing caveat) so
    the run is fully auditable. These are descriptions of method, not claims.
    """
    return {
        "subject_id": subject_id,
        "reference_timepoint": "T1",
        "comparison_timepoints": comparison_timepoints,
        "part_id": part_id,
        "group_id": group_id,
        "analysis_level": "group_cross_repetition",
        "repetitions_used": repetitions_used,
        "feature_scope": "whole_body_parent_child_relative_rotation_vectors",
        "feature_names": feature_names,
        "joint_link_map": joint_link_map,
        "selected_m": selected_m,
        "variance_threshold": variance_threshold,
        "centering_rule": "each dataset centered independently per feature column",
        "normalization_rule": "no z-score, no variance-scaling, no range-normalization",
        "sign_convention": "JcvPCA = abs(B_reprojected_loading) - abs(A_loading)",
        "joint_link_aggregation": "root-sum-square over rx/ry/rz (RSS)",
        "natural_variability_rule": "T1 repetition-level: A_T1_R1 vs A_T1_R2 via the same compute_jcvpca",
        "weighted_outputs_exported": export_weighted,
        "timing_caveat": (
            "JcvPCA measures feature contribution structure. It does not measure "
            "temporal synchronization. JsvCRP/CRP is out of scope for V1."
        ),
        "interpretation_note": (
            "This package emits numbers only. It does not classify changes as "
            "significant, robust, meaningful, or beyond variability."
        ),
    }


def build_explained_variance_table(
    comparison: str,
    evr_table_A: pd.DataFrame,
    selected_m: int,
) -> pd.DataFrame:
    df = evr_table_A.copy()
    df.insert(0, "comparison", comparison)
    df.insert(1, "dataset", "A")
    df["selected_m"] = selected_m
    return df


def write_interpretation_summary(
    output_dir: str | Path,
    comparisons: list[str],
    metadata: dict,
    natural_variability_included: bool,
) -> Path:
    """Write a factual, neutral markdown summary.

    States what was computed and the method rules. Makes no claims about
    significance or whether any change exceeds variability.
    """
    lines: list[str] = []
    lines.append("# Layer 3 JcvPCA interpretation summary\n")
    lines.append(
        "JcvPCA-style comparison of Motive-derived parent-child relative "
        "rotation-vector contribution structure.\n"
    )
    lines.append("## Method (fixed, computational)\n")
    lines.append(f"- Reference timepoint: {metadata.get('reference_timepoint')}")
    lines.append(f"- Comparison timepoints: {metadata.get('comparison_timepoints')}")
    lines.append(f"- Group: {metadata.get('group_id')}; Part: {metadata.get('part_id')}")
    lines.append(f"- Analysis level: {metadata.get('analysis_level')}")
    lines.append(f"- selected_m: {metadata.get('selected_m')} (variance_threshold={metadata.get('variance_threshold')})")
    lines.append(f"- Centering: {metadata.get('centering_rule')}")
    lines.append(f"- Normalization: {metadata.get('normalization_rule')}")
    lines.append(f"- Sign convention: {metadata.get('sign_convention')}")
    lines.append(f"- Joint-link aggregation: {metadata.get('joint_link_aggregation')}")
    lines.append(f"- Natural variability: {metadata.get('natural_variability_rule')}\n")
    lines.append("## Comparisons computed\n")
    for comp in comparisons:
        lines.append(f"- {comp}")
    if natural_variability_included:
        lines.append("- NV_T1_R1_vs_R2 (natural-variability reference; not a statistical test)")
    lines.append("")
    lines.append("## Caveats\n")
    lines.append(f"- {metadata.get('timing_caveat')}")
    lines.append(f"- {metadata.get('interpretation_note')}")
    lines.append(
        "- Whether any observed change is meaningful or exceeds T1 "
        "repetition-level variability is decided later, outside this package."
    )
    lines.append("")

    out = ensure_output_dir(output_dir) / "interpretation_summary.md"
    out.write_text("\n".join(lines))
    return out


def write_analysis_validation_report(
    output_dir: str | Path,
    preflight,
) -> tuple[Path, Path]:
    """Write validation report as CSV and markdown."""
    out = ensure_output_dir(output_dir)
    checks_df = pd.DataFrame(
        [
            {
                "name": c.name,
                "status": c.status,
                "category": c.category,
                "message": c.message,
            }
            for c in preflight.checks
        ]
    )
    csv_path = out / "analysis_validation_report.csv"
    write_csv(csv_path, checks_df)

    lines = [
        "# Analysis validation report",
        "",
        f"Overall status: **{preflight.status}**",
        f"Blocking: {preflight.blocking_count}; Warnings: {preflight.warning_count}",
        "",
        "## Checks",
        "",
    ]
    for c in preflight.checks:
        lines.append(f"- [{c.status}] **{c.name}** ({c.category}): {c.message}")
    lines.extend(
        [
            "",
            "## Matrix Stability / PCA Readiness",
            "",
            "Matrix stability indicates numerical suitability for PCA/JcvPCA.",
            "It does not establish statistical significance or biological meaning.",
            "",
        ]
    )
    if preflight.stability:
        for role, stab in preflight.stability.items():
            label = "A/reference" if role == "A" else role
            lines.append(f"### {label}")
            for k, v in stab.metrics.items():
                if k not in ("pc_variance_profile",):
                    lines.append(f"- {k}: {v}")
            lines.append("")
    md_path = out / "analysis_validation_report.md"
    md_path.write_text("\n".join(lines))
    return csv_path, md_path


def write_matrix_stability_reports(output_dir: str | Path, preflight) -> None:
    out = ensure_output_dir(output_dir)
    if not preflight.stability:
        return
    from layer3_jcvpca.preflight import stability_summary_table

    summary = stability_summary_table(preflight.stability)
    write_csv(out / "matrix_stability_report.csv", summary)

    lines = [
        "# Matrix Stability / PCA Readiness Report",
        "",
        "Indicates whether selected windows are numerically suitable for PCA/JcvPCA.",
        "Does not prove scientific truth.",
        "",
    ]
    for role, stab in preflight.stability.items():
        label = "**A/reference**" if role == "A" else role
        lines.append(f"## {label} — {stab.status}")
        for f in stab.findings:
            lines.append(f"- [{f['severity']}] {f['message']}")
        lines.append("")
    (out / "matrix_stability_report.md").write_text("\n".join(lines))

    # Per-matrix tables (A emphasized; save all)
    for role, stab in preflight.stability.items():
        prefix = role.lower()
        if stab.feature_variance_table is not None and not stab.feature_variance_table.empty:
            if role == "A":
                write_csv(out / "feature_variance_table.csv", stab.feature_variance_table)
            else:
                write_csv(out / f"feature_variance_table_{prefix}.csv", stab.feature_variance_table)
        if stab.joint_variance_table is not None and not stab.joint_variance_table.empty:
            if role == "A":
                write_csv(out / "joint_variance_table.csv", stab.joint_variance_table)
            else:
                write_csv(out / f"joint_variance_table_{prefix}.csv", stab.joint_variance_table)
        if stab.singular_value_table is not None and not stab.singular_value_table.empty:
            if role == "A":
                write_csv(out / "singular_value_table.csv", stab.singular_value_table)
        if stab.split_half_table is not None and not stab.split_half_table.empty:
            write_csv(out / "split_half_stability_table.csv", stab.split_half_table)
            break


def write_analysis_summary(
    output_dir: str | Path,
    identity,
    selected_m: int,
    pc_selection_reason: str,
    preflight,
) -> Path:
    lines = [
        "# Layer 3 JcvPCA analysis summary",
        "",
        f"- analysis_id: {identity.analysis_id}",
        f"- participant_id: {identity.participant_id}",
        f"- analysis_type: {identity.analysis_type}",
        f"- selected PCs: {selected_m} ({pc_selection_reason})",
        f"- preflight status: {preflight.status}",
        "",
        "## Comparisons",
        "- Main: A (reference) vs B (comparison)",
        "- Natural variability: NV_A vs NV_B (descriptive baseline, not statistical proof)",
        "",
        "## Matrix Stability",
        "",
        "A/reference defines the PCA space. Review matrix_stability_report.md before interpreting.",
        "",
    ]
    path = ensure_output_dir(output_dir) / "analysis_summary.md"
    path.write_text("\n".join(lines))
    return path


def write_analysis_package(
    output_dir: str | Path,
    *,
    identity,
    paths: dict,
    preflight,
    params,
    selected_m: int,
    pc_selection_reason: str,
    tables: dict[str, pd.DataFrame],
    main_result: dict,
    nv_result: dict,
    distribution_metrics: dict,
) -> Path:
    out = ensure_output_dir(output_dir)
    plots_dir = out / "plots"
    plots_dir.mkdir(exist_ok=True)

    for name, df in tables.items():
        write_csv(out / name, df)

    write_analysis_validation_report(out, preflight)
    write_matrix_stability_reports(out, preflight)
    write_analysis_summary(out, identity, selected_m, pc_selection_reason, preflight)

    from layer3_jcvpca import viz

    viz.save_analysis_plots(
        plots_dir,
        preflight=preflight,
        main_result=main_result,
        nv_result=nv_result,
        tables=tables,
        distribution_metrics=distribution_metrics,
        feature_names=main_result.get("feature_names", []),
    )
    return out


def _json_default(obj: object):
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, Path):
        return str(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
