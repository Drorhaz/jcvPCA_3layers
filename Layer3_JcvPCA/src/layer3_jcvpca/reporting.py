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
