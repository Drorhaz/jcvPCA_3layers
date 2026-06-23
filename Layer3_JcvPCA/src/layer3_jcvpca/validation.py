"""Validation gates for Layer 3 JcvPCA.

All validators are fail-fast and non-destructive. They never repair, fill,
interpolate, drop, or zero-replace data. On failure they raise
``ValidationError`` (carrying a structured report) so the caller can write a
validation report and stop.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from layer3_jcvpca.io import (
    AXIS_SUFFIXES,
    build_joint_link_map,
    infer_feature_columns,
)

REQUIRED_AXES: tuple[str, str, str] = ("rx", "ry", "rz")


class ValidationError(Exception):
    """Raised when a Layer 3 validation gate fails.

    ``report`` holds a structured, serialisable description of the failure.
    """

    def __init__(self, message: str, report: dict | None = None):
        super().__init__(message)
        self.report = report or {}


def validate_jcvpca_matrix(
    df: pd.DataFrame,
    required_metadata_cols: list[str],
    min_rows_for_pca: int = 10,
) -> dict:
    """Validate a single JcvPCA-ready matrix.

    Checks (all must pass):
      - all required metadata columns present;
      - at least one feature column (``*_rx``/``*_ry``/``*_rz``);
      - every feature column is numeric;
      - no NaN values in feature columns;
      - no infinite values in feature columns;
      - no constant feature columns;
      - every joint-link has a complete rx/ry/rz triplet;
      - enough rows for PCA (>= min_rows_for_pca).

    Returns a structured report dict on success. Raises ``ValidationError`` on
    the first hard failure (the report is attached to the exception).
    """
    feature_cols = infer_feature_columns(df)
    report: dict = {
        "n_rows": int(len(df)),
        "metadata_columns_found": [c for c in required_metadata_cols if c in df.columns],
        "feature_columns_found": feature_cols,
        "n_features": len(feature_cols),
        "nan_count": 0,
        "inf_count": 0,
        "constant_columns": [],
        "triplet_completeness": True,
        "non_numeric_feature_columns": [],
        "missing_metadata_columns": [],
        "status": "passed",
        "errors": [],
    }

    missing_meta = [c for c in required_metadata_cols if c not in df.columns]
    report["missing_metadata_columns"] = missing_meta
    if missing_meta:
        return _fail(report, f"Missing required metadata columns: {missing_meta}")

    if not feature_cols:
        return _fail(report, "No feature columns ending in _rx/_ry/_rz were found.")

    non_numeric = [
        c for c in feature_cols if not pd.api.types.is_numeric_dtype(df[c])
    ]
    report["non_numeric_feature_columns"] = non_numeric
    if non_numeric:
        return _fail(report, f"Non-numeric feature columns: {non_numeric}")

    features = df[feature_cols]
    nan_count = int(features.isna().to_numpy().sum())
    report["nan_count"] = nan_count
    if nan_count > 0:
        return _fail(report, f"Feature columns contain {nan_count} NaN value(s).")

    inf_count = int(np.isinf(features.to_numpy()).sum())
    report["inf_count"] = inf_count
    if inf_count > 0:
        return _fail(report, f"Feature columns contain {inf_count} infinite value(s).")

    constant_cols = [c for c in feature_cols if features[c].nunique(dropna=False) <= 1]
    report["constant_columns"] = constant_cols
    if constant_cols:
        return _fail(report, f"Constant feature columns: {constant_cols}")

    link_map = build_joint_link_map(feature_cols)
    incomplete = {
        link: sorted(set(REQUIRED_AXES) - set(axes))
        for link, axes in link_map.items()
        if set(axes) != set(REQUIRED_AXES)
    }
    report["triplet_completeness"] = not incomplete
    report["incomplete_links"] = incomplete
    if incomplete:
        return _fail(report, f"Joint-links with incomplete rx/ry/rz triplets: {incomplete}")

    if len(df) < min_rows_for_pca:
        return _fail(
            report,
            f"Too few rows for PCA: {len(df)} < min_rows_for_pca={min_rows_for_pca}.",
        )

    return report


def validate_feature_schema_match(
    matrices: dict[str, pd.DataFrame],
    feature_names: list[str],
) -> None:
    """Ensure every matrix exposes identical feature names AND order.

    ``feature_names`` is the reference order. Raises ``ValidationError`` on any
    name or order mismatch.
    """
    for label, df in matrices.items():
        found = infer_feature_columns(df)
        if found != feature_names:
            report = {
                "status": "failed",
                "matrix": label,
                "expected_feature_order": feature_names,
                "found_feature_order": found,
            }
            if set(found) != set(feature_names):
                msg = (
                    f"Feature name mismatch in matrix '{label}': "
                    f"missing={sorted(set(feature_names) - set(found))}, "
                    f"unexpected={sorted(set(found) - set(feature_names))}"
                )
            else:
                msg = f"Feature order mismatch in matrix '{label}'."
            raise ValidationError(msg, report)


def validate_selected_m(
    selected_m: int,
    n_features_A: int,
    n_rows_A: int,
    n_rows_B: int,
    min_rows_for_pca: int = 10,
) -> None:
    """Validate ``selected_m`` against both A and B dimensions before PCA.

    Requirements:
      - selected_m is a positive integer;
      - selected_m <= number of A features (PCA-A component bound);
      - selected_m <= number of A rows (PCA-A sample bound);
      - selected_m <= number of B rows (PCA-B is fit on B projected into the
        selected_m-dimensional A space, so it needs >= selected_m samples);
      - A and B both satisfy min_rows_for_pca.
    """
    if not isinstance(selected_m, (int, np.integer)) or selected_m < 1:
        raise ValidationError(f"selected_m must be a positive integer, got {selected_m!r}.")
    if selected_m > n_features_A:
        raise ValidationError(
            f"selected_m={selected_m} exceeds number of features={n_features_A}."
        )
    if selected_m > n_rows_A:
        raise ValidationError(
            f"selected_m={selected_m} exceeds number of A rows={n_rows_A}."
        )
    if selected_m > n_rows_B:
        raise ValidationError(
            f"selected_m={selected_m} exceeds number of B rows={n_rows_B} "
            f"(B is projected into the selected_m-dimensional A space)."
        )
    if n_rows_A < min_rows_for_pca or n_rows_B < min_rows_for_pca:
        raise ValidationError(
            f"Too few rows for PCA: A={n_rows_A}, B={n_rows_B}, "
            f"min_rows_for_pca={min_rows_for_pca}."
        )


def validate_manifest_roles(
    manifest: pd.DataFrame,
    required_roles: list[str],
) -> dict:
    """Validate manifest analysis roles for a V1 run.

    Considers only rows with ``include_in_analysis == True``. Checks:
      - each required role present exactly once;
      - no duplicate required roles;
      - every referenced matrix_path exists on disk.

    Returns a structured report on success; raises ``ValidationError`` otherwise.
    """
    included = manifest[manifest["include_in_analysis"]]
    roles = list(included["analysis_role"])
    report: dict = {
        "required_roles": required_roles,
        "roles_present": roles,
        "missing_roles": [],
        "duplicate_roles": [],
        "missing_files": [],
        "status": "passed",
    }

    counts = {r: roles.count(r) for r in required_roles}
    report["missing_roles"] = [r for r, n in counts.items() if n == 0]
    report["duplicate_roles"] = [r for r, n in counts.items() if n > 1]

    for _, row in included.iterrows():
        if row["analysis_role"] in required_roles:
            if not Path(row["matrix_path"]).exists():
                report["missing_files"].append(str(row["matrix_path"]))

    if report["missing_roles"] or report["duplicate_roles"] or report["missing_files"]:
        report["status"] = "failed"
        raise ValidationError(
            "Manifest role validation failed: "
            f"missing_roles={report['missing_roles']}, "
            f"duplicate_roles={report['duplicate_roles']}, "
            f"missing_files={report['missing_files']}.",
            report,
        )
    return report


def _fail(report: dict, message: str) -> dict:
    report["status"] = "failed"
    report["errors"].append(message)
    raise ValidationError(message, report)
