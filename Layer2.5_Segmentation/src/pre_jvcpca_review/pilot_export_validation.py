"""Hard validation gate for Layer 3 pilot matrix exports."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from pre_jvcpca_review.canonical_manifest import (
    CANONICAL_NAMING_POLICY,
    DEFAULT_PILOT_MANIFEST,
    ManifestError,
    expected_pilot_feature_order,
    load_pilot_manifest,
    pilot_feature_order,
    resolve_session_links_from_manifest,
)
from pre_jvcpca_review.export_constants import (
    FEATURE_AXES,
    MATRIX_IDENTITY_COLUMNS,
    MATRIX_SOURCE_COLUMNS,
)
from pre_jvcpca_review.load_layer2 import LinkRecord, load_link_manifest


@dataclass
class ValidationIssue:
    check: str
    severity: str
    message: str


class PilotExportValidationError(Exception):
    """Validation failed; see validation report path if written."""

    def __init__(self, issues: list[ValidationIssue], report_path: Path | None = None):
        self.issues = issues
        self.report_path = report_path
        summary = "; ".join(f"{issue.check}: {issue.message}" for issue in issues[:5])
        super().__init__(f"Pilot export validation failed ({len(issues)} issue(s)): {summary}")


def _write_validation_report(
    path: Path,
    issues: list[ValidationIssue],
    *,
    context: dict[str, object],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "fail" if any(i.severity == "error" for i in issues) else "pass",
        "issue_count": len(issues),
        "issues": [
            {"check": i.check, "severity": i.severity, "message": i.message} for i in issues
        ],
        "context": context,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def validate_single_pilot_matrix(
    matrix_df: pd.DataFrame,
    manifest_path: Path,
    session_links: list[LinkRecord],
    *,
    allow_nan: bool = False,
    report_path: Path | None = None,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    manifest = load_pilot_manifest(manifest_path)
    _, links_by_canonical = resolve_session_links_from_manifest(manifest, session_links)
    expected_order = expected_pilot_feature_order(manifest, links_by_canonical)
    expected_features = pilot_feature_order(manifest)

    # Metadata columns stable and present
    for col in MATRIX_IDENTITY_COLUMNS:
        if col not in matrix_df.columns:
            issues.append(
                ValidationIssue("metadata_columns", "error", f"Missing metadata column: {col}")
            )
        elif matrix_df[col].isna().any():
            issues.append(
                ValidationIssue("metadata_columns", "error", f"Null values in metadata column {col}")
            )

    actual_features = [col for col in matrix_df.columns if col not in MATRIX_IDENTITY_COLUMNS]

    if actual_features != expected_order:
        issues.append(
            ValidationIssue(
                "feature_order",
                "error",
                "Feature column order does not match pilot manifest",
            )
        )

    if set(actual_features) != set(expected_features):
        missing = sorted(set(expected_features) - set(actual_features))
        extra = sorted(set(actual_features) - set(expected_features))
        if missing:
            issues.append(
                ValidationIssue(
                    "feature_presence",
                    "error",
                    f"Missing required pilot features: {missing}",
                )
            )
        if extra:
            issues.append(
                ValidationIssue(
                    "feature_presence",
                    "error",
                    f"Unapproved extra features: {extra}",
                )
            )

    if len(actual_features) != len(expected_features):
        issues.append(
            ValidationIssue(
                "feature_count",
                "error",
                f"Expected {len(expected_features)} features, found {len(actual_features)}",
            )
        )

    # Axes per link
    for (parent, child), link in links_by_canonical.items():
        link_cols = [
            feature
            for feature in expected_order
            if feature.startswith(f"{parent}_to_{child}_")
        ]
        if len(link_cols) != 3:
            issues.append(
                ValidationIssue(
                    "axes_per_link",
                    "error",
                    f"Link {parent}->{child} must have rx/ry/rz triplet; got {link_cols}",
                )
            )

    # NaN/inf in analysis values
    for col in expected_order:
        if col not in matrix_df.columns:
            continue
        values = matrix_df[col].to_numpy(dtype=float)
        if np.isinf(values).any():
            issues.append(
                ValidationIssue("analysis_values", "error", f"Infinite values in column {col}")
            )
        nan_count = int(np.isnan(values).sum())
        if nan_count and not allow_nan:
            issues.append(
                ValidationIssue(
                    "analysis_values",
                    "error",
                    f"NaN values in column {col} ({nan_count} rows)",
                )
            )

    errors = [issue for issue in issues if issue.severity == "error"]
    if errors and report_path is not None:
        _write_validation_report(
            report_path,
            issues,
            context={
                "manifest_path": str(manifest_path.resolve()),
                "naming_policy": CANONICAL_NAMING_POLICY,
                "expected_feature_order": expected_order,
                "actual_features": actual_features,
            },
        )

    if errors:
        raise PilotExportValidationError(issues, report_path)

    return issues


def validate_cross_session_pilot_exports(
    export_dirs: list[Path],
    manifest_path: Path | None = None,
    *,
    report_path: Path | None = None,
) -> None:
    """Ensure all pilot exports share identical canonical feature list and order."""
    manifest_path = manifest_path or DEFAULT_PILOT_MANIFEST
    manifest = load_pilot_manifest(manifest_path)
    reference_order = pilot_feature_order(manifest)
    issues: list[ValidationIssue] = []

    for export_dir in export_dirs:
        matrix_path = export_dir / "window_jvcpca_matrix.parquet"
        manifest_json = export_dir / "window_export_manifest.json"
        if not matrix_path.exists():
            issues.append(
                ValidationIssue(
                    "export_presence",
                    "error",
                    f"Missing matrix in {export_dir}",
                )
            )
            continue

        matrix_df = pd.read_parquet(matrix_path)
        feature_cols = [col for col in matrix_df.columns if col not in MATRIX_IDENTITY_COLUMNS]
        if feature_cols != reference_order:
            issues.append(
                ValidationIssue(
                    "cross_session_order",
                    "error",
                    f"{export_dir.name}: feature order mismatch vs pilot manifest",
                )
            )

        if manifest_json.exists():
            exported = json.loads(manifest_json.read_text(encoding="utf-8"))
            if exported.get("feature_naming_policy") != CANONICAL_NAMING_POLICY:
                issues.append(
                    ValidationIssue(
                        "naming_policy",
                        "error",
                        f"{export_dir.name}: export not using canonical naming policy",
                    )
                )
            if exported.get("feature_order") != reference_order:
                issues.append(
                    ValidationIssue(
                        "manifest_recorded_order",
                        "error",
                        f"{export_dir.name}: recorded feature_order differs from pilot manifest",
                    )
                )

    errors = [issue for issue in issues if issue.severity == "error"]
    if report_path and errors:
        _write_validation_report(
            report_path,
            issues,
            context={
                "manifest_path": str(manifest_path.resolve()),
                "export_dirs": [str(path) for path in export_dirs],
                "reference_feature_order": reference_order,
            },
        )

    if errors:
        raise PilotExportValidationError(issues, report_path)


def validate_before_write(
    matrix_df: pd.DataFrame,
    feature_order: list[str],
    manifest_path: Path,
    session_links: list[LinkRecord],
    *,
    allow_nan: bool,
    out_dir: Path,
) -> None:
    """Run validation gate; write error report and raise on failure."""
    report_path = out_dir / "pilot_export_validation_report.json"
    validate_single_pilot_matrix(
        matrix_df,
        manifest_path,
        session_links,
        allow_nan=allow_nan,
        report_path=report_path,
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(
            {
                "status": "pass",
                "manifest_path": str(manifest_path.resolve()),
                "feature_naming_policy": CANONICAL_NAMING_POLICY,
                "feature_order": feature_order,
                "n_features": len(feature_order),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
