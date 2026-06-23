"""V1 manifest-driven runner for Layer 3 JcvPCA.

Two modes:
  - ``dry_validate``: load every included matrix, run per-matrix schema
    validation and cross-matrix feature-schema-match validation, and write a
    validation report. No A/B comparisons, no PCA, no interpretation.
  - ``full``: build the V1 datasets from manifest roles, run the three
    ``compute_jcvpca`` comparisons, and write all neutral outputs.

The runner never fabricates a B matrix, never duplicates a matrix as B, and
never makes scientific interpretations.
"""

from __future__ import annotations

import argparse
import datetime as _dt
from pathlib import Path

import pandas as pd
import yaml

from layer3_jcvpca import aggregation, reporting
from layer3_jcvpca.core import compute_jcvpca, select_selected_m_from_A
from layer3_jcvpca.io import (
    build_joint_link_map,
    infer_feature_columns,
    load_analysis_manifest,
    load_matrix,
)
from layer3_jcvpca.validation import (
    ValidationError,
    validate_feature_schema_match,
    validate_jcvpca_matrix,
    validate_manifest_roles,
)

REQUIRED_ROLES: list[str] = [
    "A_T1_R1",
    "A_T1_R2",
    "B_T2_R1",
    "B_T2_R2",
    "B_T3_R1",
    "B_T3_R2",
]

# Mapping from final comparison/dataset to the manifest roles that compose it.
DATASET_ROLES: dict[str, list[str]] = {
    "A_T1": ["A_T1_R1", "A_T1_R2"],
    "B_T2": ["B_T2_R1", "B_T2_R2"],
    "B_T3": ["B_T3_R1", "B_T3_R2"],
}

COMPARISONS: list[tuple[str, str, str]] = [
    # (comparison_label, A_dataset, B_dataset)
    ("A_T1_vs_B_T2", "A_T1", "B_T2"),
    ("A_T1_vs_B_T3", "A_T1", "B_T3"),
]

NATURAL_VARIABILITY = ("NV_T1_R1_vs_R2", "A_T1_R1", "A_T1_R2")


def load_config(config_path: str | Path) -> dict:
    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with open(config_path) as fh:
        config = yaml.safe_load(fh)
    return config or {}


def build_v1_comparisons_from_manifest(
    manifest: pd.DataFrame,
) -> dict[str, str]:
    """Map each required role to its matrix_path (included rows only).

    Validates roles first (presence, duplicates, file existence) and returns a
    role -> matrix_path dict. Does not load the matrices.
    """
    validate_manifest_roles(manifest, REQUIRED_ROLES)
    included = manifest[manifest["include_in_analysis"]]
    role_to_path: dict[str, str] = {}
    for _, row in included.iterrows():
        role = row["analysis_role"]
        if role in REQUIRED_ROLES:
            role_to_path[role] = str(row["matrix_path"])
    return role_to_path


def run_dry_validate(config: dict) -> dict:
    """Schema-only validation of every included matrix.

    Each included row's matrix is loaded and validated independently. If two or
    more matrices are present, cross-matrix feature-schema match is also checked.
    No comparisons are constructed.
    """
    manifest_path = config["manifest_path"]
    output_dir = config["output_dir"]
    required_metadata_cols = config["required_metadata_cols"]
    min_rows = int(config.get("min_rows_for_pca", 10))

    manifest = load_analysis_manifest(manifest_path)
    included = manifest[manifest["include_in_analysis"]]

    report: dict = {
        "mode": "dry_validate",
        "manifest_path": str(manifest_path),
        "required_metadata_cols": required_metadata_cols,
        "n_included_rows": int(len(included)),
        "input_files": [],
        "per_matrix": {},
        "feature_schema_match": None,
        "status": "passed",
        "errors": [],
        "warnings": [],
        "created_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
    }

    if included.empty:
        report["status"] = "failed"
        report["errors"].append("No rows with include_in_analysis=true in manifest.")
        reporting.write_validation_report(output_dir, report)
        raise ValidationError("No included matrices to validate.", report)

    loaded: dict[str, pd.DataFrame] = {}
    feature_names_by_role: dict[str, list[str]] = {}

    for _, row in included.iterrows():
        role = str(row["analysis_role"])
        path = str(row["matrix_path"])
        report["input_files"].append({"analysis_role": role, "matrix_path": path})
        try:
            df = load_matrix(path)
        except FileNotFoundError as exc:
            report["status"] = "failed"
            report["errors"].append(str(exc))
            report["per_matrix"][role] = {"status": "failed", "errors": [str(exc)]}
            continue

        try:
            matrix_report = validate_jcvpca_matrix(df, required_metadata_cols, min_rows)
            report["per_matrix"][role] = matrix_report
            loaded[role] = df
            feature_names_by_role[role] = infer_feature_columns(df)
        except ValidationError as exc:
            report["status"] = "failed"
            report["errors"].append(f"[{role}] {exc}")
            report["per_matrix"][role] = exc.report

    # Cross-matrix feature schema match (only when >= 2 matrices loaded cleanly).
    if len(loaded) >= 2:
        reference_role = next(iter(loaded))
        reference_features = feature_names_by_role[reference_role]
        try:
            validate_feature_schema_match(loaded, reference_features)
            report["feature_schema_match"] = True
        except ValidationError as exc:
            report["status"] = "failed"
            report["feature_schema_match"] = False
            report["errors"].append(str(exc))
            report["schema_match_detail"] = exc.report
    elif len(loaded) == 1:
        report["feature_schema_match"] = "single_matrix_no_cross_check"
        report["warnings"].append(
            "Only one valid matrix available; cross-matrix feature-schema match "
            "was not performed. Full V1 analysis requires all six Group 4 matrices."
        )

    out = reporting.write_validation_report(output_dir, report)
    report["validation_report_path"] = str(out)
    if report["status"] == "failed":
        raise ValidationError("Dry validation failed; see validation_report.json.", report)
    return report


def run_layer3_v1(config_path: str | Path) -> dict:
    """Run Layer 3 V1 according to config mode."""
    config = load_config(config_path)
    mode = str(config.get("mode", "dry_validate")).lower()

    if mode == "dry_validate":
        return run_dry_validate(config)
    if mode == "full":
        return run_full(config)
    raise ValueError(f"Unknown mode: {mode!r}. Use 'dry_validate' or 'full'.")


def run_full(config: dict) -> dict:
    """Full V1 analysis: requires all six Group 4 matrices.

    Builds A_T1/B_T2/B_T3/NV_T1, runs three comparisons, writes all outputs.
    """
    manifest_path = config["manifest_path"]
    output_dir = config["output_dir"]
    required_metadata_cols = config["required_metadata_cols"]
    variance_threshold = float(config.get("variance_threshold", 0.90))
    selected_m_override = config.get("selected_m_override")
    min_rows = int(config.get("min_rows_for_pca", 10))
    export_weighted = bool(config.get("export_weighted", False))

    manifest = load_analysis_manifest(manifest_path)
    role_to_path = build_v1_comparisons_from_manifest(manifest)

    # Load and validate every role matrix.
    role_dfs: dict[str, pd.DataFrame] = {}
    validation_report: dict = {
        "mode": "full",
        "per_matrix": {},
        "status": "passed",
        "errors": [],
        "created_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
    }
    for role, path in role_to_path.items():
        df = load_matrix(path)
        validation_report["per_matrix"][role] = validate_jcvpca_matrix(
            df, required_metadata_cols, min_rows
        )
        role_dfs[role] = df

    reference_features = infer_feature_columns(role_dfs["A_T1_R1"])
    validate_feature_schema_match(role_dfs, reference_features)
    validation_report["feature_schema_match"] = True
    reporting.write_validation_report(output_dir, validation_report)

    # Build datasets by row-wise concatenation.
    datasets: dict[str, pd.DataFrame] = {
        name: pd.concat([role_dfs[r] for r in roles], axis=0, ignore_index=True)
        for name, roles in DATASET_ROLES.items()
    }

    feature_names = reference_features
    joint_link_map = build_joint_link_map(feature_names)

    # selected_m derived from the primary reference A_T1 (A only), or override.
    if selected_m_override is None:
        selected_m, _ = select_selected_m_from_A(
            datasets["A_T1"], feature_names, variance_threshold
        )
    else:
        selected_m = int(selected_m_override)

    axis_frames: list[pd.DataFrame] = []
    link_frames: list[pd.DataFrame] = []
    evr_frames: list[pd.DataFrame] = []

    def _run_one(comparison: str, A_df: pd.DataFrame, B_df: pd.DataFrame) -> None:
        result = compute_jcvpca(
            A_df,
            B_df,
            feature_names,
            variance_threshold=variance_threshold,
            selected_m=selected_m,
            min_rows_for_pca=min_rows,
        )
        axis_df = aggregation.build_axis_table(
            result["A_abs_loadings"],
            result["B_abs_loadings"],
            result["jcvpca_axis"],
            feature_names,
            result["pca_A_variance_ratio"],
            result["pca_B_variance_ratio"],
            export_weighted=export_weighted,
        )
        axis_df.insert(0, "comparison", comparison)
        link_df = aggregation.aggregate_axis_to_link_rss(
            result["A_abs_loadings"],
            result["B_abs_loadings"],
            feature_names,
            joint_link_map,
            pca_A_variance_ratio=result["pca_A_variance_ratio"],
            export_weighted=export_weighted,
        )
        link_df.insert(0, "comparison", comparison)
        link_df["explained_variance_A"] = link_df["pc"].map(
            {i + 1: float(v) for i, v in enumerate(result["pca_A_variance_ratio"])}
        )
        evr_df = reporting.build_explained_variance_table(
            comparison, result["explained_variance_table_A"], selected_m
        )
        axis_frames.append(axis_df)
        link_frames.append(link_df)
        evr_frames.append(evr_df)

    for comparison, a_name, b_name in COMPARISONS:
        _run_one(comparison, datasets[a_name], datasets[b_name])

    # Natural variability uses the same compute_jcvpca on T1 R1 vs R2.
    nv_label, nv_a_role, nv_b_role = NATURAL_VARIABILITY
    nv_result = compute_jcvpca(
        role_dfs[nv_a_role],
        role_dfs[nv_b_role],
        feature_names,
        variance_threshold=variance_threshold,
        selected_m=selected_m,
        min_rows_for_pca=min_rows,
    )
    nv_axis = aggregation.build_axis_table(
        nv_result["A_abs_loadings"],
        nv_result["B_abs_loadings"],
        nv_result["jcvpca_axis"],
        feature_names,
        nv_result["pca_A_variance_ratio"],
        nv_result["pca_B_variance_ratio"],
        export_weighted=export_weighted,
    )
    nv_axis.insert(0, "comparison", nv_label)
    nv_link = aggregation.aggregate_axis_to_link_rss(
        nv_result["A_abs_loadings"],
        nv_result["B_abs_loadings"],
        feature_names,
        joint_link_map,
        pca_A_variance_ratio=nv_result["pca_A_variance_ratio"],
        export_weighted=export_weighted,
    )
    nv_link.insert(0, "comparison", nv_label)
    nv_link["explained_variance_A"] = nv_link["pc"].map(
        {i + 1: float(v) for i, v in enumerate(nv_result["pca_A_variance_ratio"])}
    )

    out_dir = reporting.ensure_output_dir(output_dir)

    axis_all = pd.concat(axis_frames, axis=0, ignore_index=True)
    link_all = pd.concat(link_frames, axis=0, ignore_index=True)
    evr_all = pd.concat(evr_frames, axis=0, ignore_index=True)

    reporting.write_csv(out_dir / "jcvpca_axis.csv", axis_all)
    reporting.write_csv(out_dir / "jrw_axis.csv", _jrw_axis_view(axis_all))
    reporting.write_csv(out_dir / "jcvpca_link.csv", link_all)
    reporting.write_csv(out_dir / "jrw_link.csv", _jrw_link_view(link_all))
    reporting.write_csv(out_dir / "explained_variance.csv", evr_all)
    reporting.write_csv(out_dir / "natural_variability_t1.csv", nv_link)
    reporting.write_csv(out_dir / "natural_variability_t1_axis.csv", nv_axis)

    subject_id = str(manifest.iloc[0]["subject_id"]) if not manifest.empty else ""
    group_id = str(manifest.iloc[0]["group_id"]) if not manifest.empty else ""
    part_id = str(manifest.iloc[0]["part_id"]) if not manifest.empty else ""
    metadata = reporting.build_analysis_metadata(
        subject_id=subject_id,
        part_id=part_id,
        group_id=group_id,
        feature_names=feature_names,
        joint_link_map=joint_link_map,
        selected_m=selected_m,
        variance_threshold=variance_threshold,
        repetitions_used={name: roles for name, roles in DATASET_ROLES.items()},
        comparison_timepoints=["T2", "T3"],
        export_weighted=export_weighted,
    )
    reporting.write_analysis_metadata(out_dir, metadata)
    reporting.write_interpretation_summary(
        out_dir,
        [c[0] for c in COMPARISONS],
        metadata,
        natural_variability_included=True,
    )

    return {
        "mode": "full",
        "status": "completed",
        "selected_m": selected_m,
        "output_dir": str(out_dir),
    }


def _jrw_axis_view(axis_all: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "comparison",
        "pc",
        "feature",
        "link_id",
        "axis",
        "loading_A_abs",
        "loading_B_reprojected_abs",
    ]
    if "weighted_jcvpca_axis" in axis_all.columns:
        cols.append("weighted_jcvpca_axis")
    return axis_all[cols].copy()


def _jrw_link_view(link_all: pd.DataFrame) -> pd.DataFrame:
    cols = ["comparison", "pc", "link_id", "JRW_A_link", "JRW_B_link"]
    if "weighted_JcvPCA_link" in link_all.columns:
        cols.append("weighted_JcvPCA_link")
    return link_all[cols].copy()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run Layer 3 JcvPCA (V1, Group 4 cross-repetition)."
    )
    parser.add_argument(
        "--config",
        required=True,
        help="Path to layer3_config.yaml.",
    )
    args = parser.parse_args(argv)
    try:
        result = run_layer3_v1(args.config)
    except ValidationError as exc:
        print(f"VALIDATION FAILED: {exc}")
        return 1
    print(f"Layer 3 finished: {result.get('mode')} -> status={result.get('status')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
