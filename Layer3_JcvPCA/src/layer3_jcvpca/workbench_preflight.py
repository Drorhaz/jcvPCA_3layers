"""Workbench preflight for Phase 4 dataset construction plans (Phase 5).

Consumes dataset construction artifacts and runs preflight validation before any
computational step. Does not run PCA, centering, projection, RSS, NV, or analysis.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from layer3_jcvpca.data_contract import REQUIRED_METADATA_COLUMNS
from layer3_jcvpca.dataset_builder import (
    PREVIEW_TRACKING_COLUMNS,
    DatasetConstructionResult,
)
from layer3_jcvpca.io import build_joint_link_map, infer_feature_columns
from layer3_jcvpca.validation import REQUIRED_AXES

PREFLIGHT_PASS = "pass"
PREFLIGHT_WARNING = "warning"
PREFLIGHT_BLOCKING = "blocking"

ROWS_TO_FEATURES_PASS_THRESHOLD = 5.0
DEFAULT_MIN_ROWS_FOR_PCA = 10

REASON_FEATURE_ORDER_MISMATCH = "feature_order_mismatch"
REASON_FEATURE_NAME_MISMATCH = "feature_name_mismatch"
REASON_MISSING_SELECTED_FEATURE = "missing_selected_feature"
REASON_INCOMPLETE_TRIPLET = "incomplete_triplet"
REASON_NON_NUMERIC = "non_numeric"
REASON_NAN = "nan_values"
REASON_INF = "inf_values"
REASON_ZERO_VARIANCE = "zero_variance"
REASON_NOT_LAYER3_SAFE = "not_layer3_safe"
REASON_QC_BLOCKING = "qc_status_blocking"
REASON_QC_WARNING = "qc_status_warning"
REASON_NO_LINKS = "no_selected_links"
REASON_MATRIX_LOAD_FAILED = "matrix_load_failed"
REASON_TOO_FEW_ROWS = "too_few_rows"
REASON_UNEQUAL_ROW_COUNTS = "unequal_row_counts"
REASON_ROWS_TO_FEATURES_LOW = "rows_to_features_ratio_low"
REASON_PARTIAL_DATASET = "partial_dataset_coverage"
REASON_MISSING_REPETITIONS_ACK = "missing_repetitions_acknowledged"
REASON_METADATA_IN_PCA = "metadata_in_pca_matrix"
REASON_NO_PREVIEW = "no_dataset_preview"
REASON_CONSTRUCTION_BLOCKING = "construction_blocking"

PREFLIGHT_REPORT_COLUMNS = [
    "check_id",
    "dataset_side",
    "severity",
    "reason_code",
    "message",
    "category",
]

FEATURE_ALIGNMENT_COLUMNS = [
    "feature_column",
    "order_index",
    "in_dataset_a",
    "in_dataset_b",
    "aligned",
    "link_stem",
    "axis",
]

ROWS_TO_FEATURES_COLUMNS = [
    "dataset_side",
    "n_rows",
    "n_selected_features",
    "rows_to_features_ratio",
    "status",
]

SOURCE_QC_COLUMNS = [
    "dataset_side",
    "concat_order",
    "matrix_label",
    "session_id",
    "matrix_path",
    "layer3_safe",
    "qc_status",
    "n_rows",
]

ISSUE_COLUMNS = [
    "severity",
    "reason_code",
    "message",
    "dataset_side",
    "category",
]


@dataclass
class ConstructionArtifactBundle:
    artifact_dir: Path
    plan: dict[str, Any] = field(default_factory=dict)
    feature_columns: pd.DataFrame = field(default_factory=pd.DataFrame)
    dataset_a_sources: pd.DataFrame = field(default_factory=pd.DataFrame)
    dataset_b_sources: pd.DataFrame = field(default_factory=pd.DataFrame)
    dataset_a_preview: pd.DataFrame = field(default_factory=pd.DataFrame)
    dataset_b_preview: pd.DataFrame = field(default_factory=pd.DataFrame)
    construction_summary: dict[str, Any] = field(default_factory=dict)
    construction_warnings: pd.DataFrame = field(default_factory=pd.DataFrame)


@dataclass
class WorkbenchPreflightReport:
    preflight_status: str = PREFLIGHT_BLOCKING
    can_continue_to_phase6: bool = False
    warnings_acknowledged: bool = False
    dataset_a_status: str = PREFLIGHT_BLOCKING
    dataset_b_status: str = PREFLIGHT_BLOCKING
    feature_alignment: pd.DataFrame = field(default_factory=pd.DataFrame)
    rows_to_features: pd.DataFrame = field(default_factory=pd.DataFrame)
    source_qc: pd.DataFrame = field(default_factory=pd.DataFrame)
    checks: pd.DataFrame = field(default_factory=pd.DataFrame)
    warnings: pd.DataFrame = field(default_factory=pd.DataFrame)
    blocking_errors: pd.DataFrame = field(default_factory=pd.DataFrame)
    summary: dict[str, Any] = field(default_factory=dict)
    pca_feature_columns: list[str] = field(default_factory=list)
    feature_order_a: list[str] = field(default_factory=list)
    feature_order_b: list[str] = field(default_factory=list)


def load_construction_artifacts(artifact_dir: Path | str) -> ConstructionArtifactBundle:
    """Load Phase 4 dataset construction artifacts from disk."""
    root = Path(artifact_dir)
    bundle = ConstructionArtifactBundle(artifact_dir=root)

    plan_path = root / "dataset_construction_plan.json"
    if plan_path.is_file():
        bundle.plan = json.loads(plan_path.read_text(encoding="utf-8"))

    for name, attr in (
        ("dataset_feature_columns.csv", "feature_columns"),
        ("dataset_A_sources.csv", "dataset_a_sources"),
        ("dataset_B_sources.csv", "dataset_b_sources"),
        ("dataset_A_preview.csv", "dataset_a_preview"),
        ("dataset_B_preview.csv", "dataset_b_preview"),
    ):
        path = root / name
        if path.is_file():
            setattr(bundle, attr, pd.read_csv(path))

    summary_path = root / "dataset_construction_summary.json"
    if summary_path.is_file():
        bundle.construction_summary = json.loads(summary_path.read_text(encoding="utf-8"))

    warnings_path = root / "dataset_construction_warnings.csv"
    if warnings_path.is_file():
        bundle.construction_warnings = pd.read_csv(warnings_path)

    return bundle


def bundle_from_construction_result(
    result: DatasetConstructionResult,
    artifact_dir: Path | str,
) -> ConstructionArtifactBundle:
    """Build artifact bundle from in-memory Phase 4 result."""
    warnings = pd.concat([result.warnings, result.blocking_errors], ignore_index=True)
    if warnings.empty:
        warnings = pd.DataFrame(columns=ISSUE_COLUMNS)
    return ConstructionArtifactBundle(
        artifact_dir=Path(artifact_dir),
        plan=result.plan,
        feature_columns=result.feature_columns,
        dataset_a_sources=result.dataset_a.sources,
        dataset_b_sources=result.dataset_b.sources,
        dataset_a_preview=result.dataset_a.preview,
        dataset_b_preview=result.dataset_b.preview,
        construction_summary=result.summary,
        construction_warnings=warnings,
    )


def _append_check(
    checks: list[dict[str, Any]],
    *,
    check_id: str,
    severity: str,
    reason_code: str,
    message: str,
    dataset_side: str = "",
    category: str = "validation",
) -> None:
    checks.append(
        {
            "check_id": check_id,
            "dataset_side": dataset_side,
            "severity": severity,
            "reason_code": reason_code,
            "message": message,
            "category": category,
        }
    )


def _checks_to_issues(checks: list[dict[str, Any]]) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not checks:
        empty = pd.DataFrame(columns=ISSUE_COLUMNS)
        return empty, empty
    df = pd.DataFrame(checks)
    for col in PREFLIGHT_REPORT_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    report = df[PREFLIGHT_REPORT_COLUMNS]
    warnings = report[report["severity"] == PREFLIGHT_WARNING][
        ["severity", "reason_code", "message", "dataset_side", "category"]
    ].copy()
    blocking = report[report["severity"] == PREFLIGHT_BLOCKING][
        ["severity", "reason_code", "message", "dataset_side", "category"]
    ].copy()
    for frame in (warnings, blocking):
        for col in ISSUE_COLUMNS:
            if col not in frame.columns:
                frame[col] = ""
    return warnings[ISSUE_COLUMNS], blocking[ISSUE_COLUMNS]


def _side_status(checks: list[dict[str, Any]], side: str) -> str:
    side_checks = [c for c in checks if c.get("dataset_side") in {side, ""}]
    if any(c["severity"] == PREFLIGHT_BLOCKING for c in side_checks):
        return PREFLIGHT_BLOCKING
    if any(c["severity"] == PREFLIGHT_WARNING for c in side_checks):
        return PREFLIGHT_WARNING
    return PREFLIGHT_PASS


def _validate_pca_matrix_side(
    preview: pd.DataFrame,
    *,
    side: str,
    pca_columns: list[str],
    metadata_columns: list[str],
    min_rows_for_pca: int,
    checks: list[dict[str, Any]],
) -> None:
    if preview.empty:
        _append_check(
            checks,
            check_id=f"{side}_preview_missing",
            severity=PREFLIGHT_BLOCKING,
            reason_code=REASON_NO_PREVIEW,
            message=f"Dataset {side} preview is empty.",
            dataset_side=side,
        )
        return

    for meta in metadata_columns:
        if meta in pca_columns:
            _append_check(
                checks,
                check_id=f"{side}_metadata_in_pca_{meta}",
                severity=PREFLIGHT_BLOCKING,
                reason_code=REASON_METADATA_IN_PCA,
                message=f"Metadata column {meta} incorrectly included in PCA feature list.",
                dataset_side=side,
                category="feature_alignment",
            )

    missing = [c for c in pca_columns if c not in preview.columns]
    if missing:
        _append_check(
            checks,
            check_id=f"{side}_missing_features",
            severity=PREFLIGHT_BLOCKING,
            reason_code=REASON_MISSING_SELECTED_FEATURE,
            message=(
                f"Dataset {side} missing selected features: "
                f"{missing[:6]}{'...' if len(missing) > 6 else ''}"
            ),
            dataset_side=side,
            category="feature_alignment",
        )
        return

    features = preview[pca_columns]
    non_numeric = [c for c in pca_columns if not pd.api.types.is_numeric_dtype(features[c])]
    if non_numeric:
        _append_check(
            checks,
            check_id=f"{side}_non_numeric",
            severity=PREFLIGHT_BLOCKING,
            reason_code=REASON_NON_NUMERIC,
            message=f"Dataset {side} non-numeric PCA columns: {non_numeric}",
            dataset_side=side,
        )

    nan_count = int(features.isna().to_numpy().sum())
    if nan_count > 0:
        _append_check(
            checks,
            check_id=f"{side}_nan",
            severity=PREFLIGHT_BLOCKING,
            reason_code=REASON_NAN,
            message=f"Dataset {side} PCA columns contain {nan_count} NaN value(s).",
            dataset_side=side,
        )

    inf_count = int(np.isinf(features.to_numpy()).sum())
    if inf_count > 0:
        _append_check(
            checks,
            check_id=f"{side}_inf",
            severity=PREFLIGHT_BLOCKING,
            reason_code=REASON_INF,
            message=f"Dataset {side} PCA columns contain {inf_count} infinite value(s).",
            dataset_side=side,
        )

    zero_var = [c for c in pca_columns if features[c].nunique(dropna=False) <= 1]
    if zero_var:
        _append_check(
            checks,
            check_id=f"{side}_zero_variance",
            severity=PREFLIGHT_BLOCKING,
            reason_code=REASON_ZERO_VARIANCE,
            message=f"Dataset {side} zero-variance PCA columns: {zero_var}",
            dataset_side=side,
        )

    n_rows = len(preview)
    if n_rows < min_rows_for_pca:
        _append_check(
            checks,
            check_id=f"{side}_too_few_rows",
            severity=PREFLIGHT_BLOCKING,
            reason_code=REASON_TOO_FEW_ROWS,
            message=f"Dataset {side} has {n_rows} rows; minimum for PCA is {min_rows_for_pca}.",
            dataset_side=side,
        )


def _build_feature_alignment_table(
    pca_columns: list[str],
    preview_a: pd.DataFrame,
    preview_b: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for idx, col in enumerate(pca_columns):
        in_a = col in preview_a.columns
        in_b = col in preview_b.columns
        link_stem = ""
        axis = ""
        if col.endswith("_rx"):
            axis = "rx"
            link_stem = col[:-3]
        elif col.endswith("_ry"):
            axis = "ry"
            link_stem = col[:-3]
        elif col.endswith("_rz"):
            axis = "rz"
            link_stem = col[:-3]
        rows.append(
            {
                "feature_column": col,
                "order_index": idx + 1,
                "in_dataset_a": in_a,
                "in_dataset_b": in_b,
                "aligned": in_a and in_b,
                "link_stem": link_stem,
                "axis": axis,
            }
        )
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=FEATURE_ALIGNMENT_COLUMNS)
    return df[FEATURE_ALIGNMENT_COLUMNS]


def _build_rows_to_features_table(
    n_rows_a: int,
    n_rows_b: int,
    n_features: int,
    checks: list[dict[str, Any]],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for side, n_rows in (("A", n_rows_a), ("B", n_rows_b)):
        ratio = n_rows / n_features if n_features > 0 else 0.0
        status = PREFLIGHT_PASS if ratio >= ROWS_TO_FEATURES_PASS_THRESHOLD else PREFLIGHT_WARNING
        if n_features == 0:
            status = PREFLIGHT_BLOCKING
        rows.append(
            {
                "dataset_side": side,
                "n_rows": n_rows,
                "n_selected_features": n_features,
                "rows_to_features_ratio": round(ratio, 4),
                "status": status,
            }
        )
        if status == PREFLIGHT_WARNING:
            _append_check(
                checks,
                check_id=f"{side}_rows_to_features",
                severity=PREFLIGHT_WARNING,
                reason_code=REASON_ROWS_TO_FEATURES_LOW,
                message=(
                    f"Dataset {side} rows-to-features ratio {ratio:.2f} < "
                    f"{ROWS_TO_FEATURES_PASS_THRESHOLD:.0f}."
                ),
                dataset_side=side,
                category="adequacy",
            )
    return pd.DataFrame(rows)[ROWS_TO_FEATURES_COLUMNS]


def _build_source_qc_table(
    bundle: ConstructionArtifactBundle,
    manifest_df: pd.DataFrame | None,
    checks: list[dict[str, Any]],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    manifest_lookup: dict[str, pd.Series] = {}
    if manifest_df is not None and not manifest_df.empty:
        for _, row in manifest_df.iterrows():
            manifest_lookup[str(row.get("matrix_path") or "")] = row

    for side, sources in (("A", bundle.dataset_a_sources), ("B", bundle.dataset_b_sources)):
        for _, src in sources.iterrows():
            matrix_path = str(src.get("matrix_path") or "")
            manifest_row = manifest_lookup.get(matrix_path)
            layer3_safe = str(src.get("layer3_safe") or "")
            qc_status = str(src.get("qc_status") or "")
            if manifest_row is not None:
                layer3_safe = str(manifest_row.get("layer3_safe") or layer3_safe)
                qc_status = str(manifest_row.get("qc_status") or qc_status)

            record = {
                "dataset_side": side,
                "concat_order": src.get("concat_order", ""),
                "matrix_label": src.get("matrix_label", ""),
                "session_id": src.get("session_id", ""),
                "matrix_path": matrix_path,
                "layer3_safe": layer3_safe,
                "qc_status": qc_status,
                "n_rows": src.get("n_rows", ""),
            }
            rows.append(record)

            safe_val = layer3_safe.lower()
            if safe_val in {"false", "0", "no"}:
                _append_check(
                    checks,
                    check_id=f"{side}_layer3_safe_{record['matrix_label']}",
                    severity=PREFLIGHT_BLOCKING,
                    reason_code=REASON_NOT_LAYER3_SAFE,
                    message=f"Source matrix {record['matrix_label']} is not layer3_safe.",
                    dataset_side=side,
                    category="qc",
                )
            elif qc_status.lower() == "blocking":
                _append_check(
                    checks,
                    check_id=f"{side}_qc_blocking_{record['matrix_label']}",
                    severity=PREFLIGHT_BLOCKING,
                    reason_code=REASON_QC_BLOCKING,
                    message=f"Source matrix {record['matrix_label']} has qc_status=blocking.",
                    dataset_side=side,
                    category="qc",
                )
            elif qc_status.lower() == "warning":
                _append_check(
                    checks,
                    check_id=f"{side}_qc_warning_{record['matrix_label']}",
                    severity=PREFLIGHT_WARNING,
                    reason_code=REASON_QC_WARNING,
                    message=f"Source matrix {record['matrix_label']} has qc_status=warning.",
                    dataset_side=side,
                    category="qc",
                )

    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=SOURCE_QC_COLUMNS)
    return df[SOURCE_QC_COLUMNS]


def run_workbench_preflight(
    bundle: ConstructionArtifactBundle,
    *,
    manifest_df: pd.DataFrame | None = None,
    min_rows_for_pca: int = DEFAULT_MIN_ROWS_FOR_PCA,
    warnings_acknowledged: bool = False,
) -> WorkbenchPreflightReport:
    """Run workbench preflight on Phase 4 construction artifacts."""
    report = WorkbenchPreflightReport(warnings_acknowledged=warnings_acknowledged)
    checks: list[dict[str, Any]] = []

    plan = bundle.plan
    pca_columns = list(plan.get("pca_feature_columns") or [])
    selected_links = list(plan.get("selected_link_stems") or [])
    metadata_columns = list(
        plan.get("metadata_columns_excluded_from_pca") or list(REQUIRED_METADATA_COLUMNS)
    )

    report.pca_feature_columns = pca_columns
    report.feature_order_a = pca_columns
    report.feature_order_b = pca_columns

    construction_status = str(plan.get("construction_status") or "")
    if construction_status == PREFLIGHT_BLOCKING:
        _append_check(
            checks,
            check_id="construction_blocking",
            severity=PREFLIGHT_BLOCKING,
            reason_code=REASON_CONSTRUCTION_BLOCKING,
            message="Phase 4 dataset construction ended in blocking status.",
            category="construction",
        )

    if not selected_links:
        _append_check(
            checks,
            check_id="no_selected_links",
            severity=PREFLIGHT_BLOCKING,
            reason_code=REASON_NO_LINKS,
            message="No selected comparable links in construction plan.",
            category="feature_alignment",
        )

    if not pca_columns:
        _append_check(
            checks,
            check_id="no_pca_features",
            severity=PREFLIGHT_BLOCKING,
            reason_code=REASON_MISSING_SELECTED_FEATURE,
            message="Construction plan has no PCA feature columns.",
            category="feature_alignment",
        )

    excluded = set(metadata_columns) | set(PREVIEW_TRACKING_COLUMNS)
    leaked = [c for c in pca_columns if c in excluded]
    if leaked:
        _append_check(
            checks,
            check_id="metadata_leak",
            severity=PREFLIGHT_BLOCKING,
            reason_code=REASON_METADATA_IN_PCA,
            message=f"Metadata/tracking columns incorrectly listed as PCA features: {leaked}",
            category="feature_alignment",
        )

    link_map = build_joint_link_map(pca_columns)
    for stem in selected_links:
        axis_map = link_map.get(stem, {})
        missing_axes = sorted(set(REQUIRED_AXES) - set(axis_map.keys()))
        if missing_axes:
            _append_check(
                checks,
                check_id=f"incomplete_triplet_{stem}",
                severity=PREFLIGHT_BLOCKING,
                reason_code=REASON_INCOMPLETE_TRIPLET,
                message=f"Selected link {stem} missing axes: {missing_axes}",
                category="feature_alignment",
            )

    preview_a = bundle.dataset_a_preview
    preview_b = bundle.dataset_b_preview

    if pca_columns and not preview_a.empty and not preview_b.empty:
        a_present = [c for c in pca_columns if c in preview_a.columns]
        b_present = [c for c in pca_columns if c in preview_b.columns]
        a_order_in_preview = [c for c in infer_feature_columns(preview_a) if c in pca_columns]
        b_order_in_preview = [c for c in infer_feature_columns(preview_b) if c in pca_columns]
        if set(a_present) != set(pca_columns) or set(b_present) != set(pca_columns):
            _append_check(
                checks,
                check_id="feature_name_mismatch",
                severity=PREFLIGHT_BLOCKING,
                reason_code=REASON_FEATURE_NAME_MISMATCH,
                message="Dataset A and B do not share identical selected PCA feature names.",
                category="feature_alignment",
            )
        elif a_order_in_preview != pca_columns or b_order_in_preview != pca_columns:
            _append_check(
                checks,
                check_id="feature_order_mismatch",
                severity=PREFLIGHT_BLOCKING,
                reason_code=REASON_FEATURE_ORDER_MISMATCH,
                message="Selected PCA feature order differs from the construction plan or across A/B.",
                category="feature_alignment",
            )
        elif a_order_in_preview != b_order_in_preview:
            _append_check(
                checks,
                check_id="feature_order_ab_mismatch",
                severity=PREFLIGHT_BLOCKING,
                reason_code=REASON_FEATURE_ORDER_MISMATCH,
                message="Dataset A and B PCA feature column order differs.",
                category="feature_alignment",
            )

    _validate_pca_matrix_side(
        preview_a,
        side="A",
        pca_columns=pca_columns,
        metadata_columns=metadata_columns,
        min_rows_for_pca=min_rows_for_pca,
        checks=checks,
    )
    _validate_pca_matrix_side(
        preview_b,
        side="B",
        pca_columns=pca_columns,
        metadata_columns=metadata_columns,
        min_rows_for_pca=min_rows_for_pca,
        checks=checks,
    )

    n_rows_a = len(preview_a)
    n_rows_b = len(preview_b)
    if n_rows_a != n_rows_b:
        _append_check(
            checks,
            check_id="unequal_row_counts",
            severity=PREFLIGHT_WARNING,
            reason_code=REASON_UNEQUAL_ROW_COUNTS,
            message=f"Dataset A ({n_rows_a} rows) and B ({n_rows_b} rows) have unequal row counts.",
            category="adequacy",
        )

    report.rows_to_features = _build_rows_to_features_table(
        n_rows_a,
        n_rows_b,
        len(pca_columns),
        checks,
    )
    report.source_qc = _build_source_qc_table(bundle, manifest_df, checks)

    if not bundle.construction_warnings.empty:
        for _, row in bundle.construction_warnings.iterrows():
            sev = str(row.get("severity") or PREFLIGHT_WARNING)
            if sev == "blocking":
                sev = PREFLIGHT_BLOCKING
            elif sev not in {PREFLIGHT_PASS, PREFLIGHT_WARNING, PREFLIGHT_BLOCKING}:
                sev = PREFLIGHT_WARNING
            _append_check(
                checks,
                check_id=f"construction_{row.get('reason_code', 'warning')}",
                severity=sev,
                reason_code=str(row.get("reason_code") or "construction_warning"),
                message=str(row.get("reason_message") or row.get("message") or ""),
                dataset_side=str(row.get("dataset_side") or ""),
                category="construction",
            )

    if construction_status == PREFLIGHT_WARNING:
        _append_check(
            checks,
            check_id="partial_dataset_coverage",
            severity=PREFLIGHT_WARNING,
            reason_code=REASON_PARTIAL_DATASET,
            message="Phase 4 construction completed with warnings (partial dataset coverage).",
            category="construction",
        )

    report.feature_alignment = _build_feature_alignment_table(pca_columns, preview_a, preview_b)
    report.checks = pd.DataFrame(checks) if checks else pd.DataFrame(columns=PREFLIGHT_REPORT_COLUMNS)
    if not report.checks.empty:
        for col in PREFLIGHT_REPORT_COLUMNS:
            if col not in report.checks.columns:
                report.checks[col] = ""
        report.checks = report.checks[PREFLIGHT_REPORT_COLUMNS]

    report.warnings, report.blocking_errors = _checks_to_issues(checks)
    report.dataset_a_status = _side_status(checks, "A")
    report.dataset_b_status = _side_status(checks, "B")

    if report.blocking_errors.empty and report.warnings.empty:
        report.preflight_status = PREFLIGHT_PASS
    elif report.blocking_errors.empty:
        report.preflight_status = PREFLIGHT_WARNING
    else:
        report.preflight_status = PREFLIGHT_BLOCKING

    report.can_continue_to_phase6 = report.preflight_status == PREFLIGHT_PASS or (
        report.preflight_status == PREFLIGHT_WARNING and warnings_acknowledged
    )

    blocking_codes = report.blocking_errors["reason_code"].tolist() if not report.blocking_errors.empty else []
    report.summary = {
        "preflight_status": report.preflight_status,
        "can_continue_to_phase6": report.can_continue_to_phase6,
        "warnings_acknowledged": warnings_acknowledged,
        "dataset_a_status": report.dataset_a_status,
        "dataset_b_status": report.dataset_b_status,
        "n_pca_feature_columns": len(pca_columns),
        "n_selected_links": len(selected_links),
        "feature_order_match": REASON_FEATURE_ORDER_MISMATCH not in blocking_codes,
        "feature_names_match": REASON_FEATURE_NAME_MISMATCH not in blocking_codes,
        "dataset_a_rows": n_rows_a,
        "dataset_b_rows": n_rows_b,
        "rows_to_features_a": float(
            report.rows_to_features.loc[
                report.rows_to_features["dataset_side"] == "A", "rows_to_features_ratio"
            ].iloc[0]
        )
        if not report.rows_to_features.empty
        else 0.0,
        "rows_to_features_b": float(
            report.rows_to_features.loc[
                report.rows_to_features["dataset_side"] == "B", "rows_to_features_ratio"
            ].iloc[0]
        )
        if not report.rows_to_features.empty
        else 0.0,
        "n_warnings": len(report.warnings),
        "n_blocking_errors": len(report.blocking_errors),
        "artifact_dir": str(bundle.artifact_dir),
    }
    return report


def save_preflight_acknowledgment(
    artifact_dir: Path | str,
    *,
    acknowledged: bool,
    preflight_summary: dict[str, Any] | None = None,
) -> Path:
    """Persist user acknowledgment of preflight warnings."""
    root = Path(artifact_dir)
    root.mkdir(parents=True, exist_ok=True)
    path = root / "preflight_acknowledgment.json"
    payload = {
        "warnings_acknowledged": acknowledged,
        "acknowledged_at": datetime.now(timezone.utc).isoformat(),
    }
    if preflight_summary is not None:
        payload["preflight_status"] = preflight_summary.get("preflight_status")
        payload["n_warnings"] = preflight_summary.get("n_warnings")
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    summary_path = root / "preflight_summary.json"
    if summary_path.is_file():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    else:
        summary = dict(preflight_summary or {})
    summary["warnings_acknowledged"] = acknowledged
    summary["acknowledged_at"] = payload["acknowledged_at"]
    summary["can_continue_to_phase6"] = (
        acknowledged and summary.get("preflight_status") != PREFLIGHT_BLOCKING
    )
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return path


def write_workbench_preflight_artifacts(
    report: WorkbenchPreflightReport,
    output_dir: Path | str,
) -> dict[str, Path]:
    """Write Phase 5 preflight artifacts."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "preflight_report": out / "preflight_report.csv",
        "preflight_summary": out / "preflight_summary.json",
        "feature_alignment_report": out / "feature_alignment_report.csv",
        "rows_to_features_report": out / "rows_to_features_report.csv",
        "source_matrix_qc_report": out / "source_matrix_qc_report.csv",
        "preflight_warnings": out / "preflight_warnings.csv",
        "preflight_blocking_errors": out / "preflight_blocking_errors.csv",
    }
    report.checks.to_csv(paths["preflight_report"], index=False)
    paths["preflight_summary"].write_text(
        json.dumps(report.summary, indent=2),
        encoding="utf-8",
    )
    report.feature_alignment.to_csv(paths["feature_alignment_report"], index=False)
    report.rows_to_features.to_csv(paths["rows_to_features_report"], index=False)
    report.source_qc.to_csv(paths["source_matrix_qc_report"], index=False)
    report.warnings.to_csv(paths["preflight_warnings"], index=False)
    report.blocking_errors.to_csv(paths["preflight_blocking_errors"], index=False)
    return paths
