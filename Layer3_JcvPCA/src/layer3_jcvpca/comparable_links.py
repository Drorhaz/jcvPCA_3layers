"""Comparable link / joint detection across selected Layer 2.5 export matrices."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from layer3_jcvpca.data_contract import CENTRAL_MANIFEST_NAME, REQUIRED_METADATA_COLUMNS
from layer3_jcvpca.io import (
    AXIS_SUFFIXES,
    build_joint_link_map,
    infer_feature_columns,
    link_id_of,
    load_matrix,
)

REQUIRED_AXES: tuple[str, str, str] = ("rx", "ry", "rz")

COMPARABILITY_PASS = "pass"
COMPARABILITY_WARNING = "warning"
COMPARABILITY_BLOCKING = "blocking"

REASON_COMPARABLE = "comparable"
REASON_INCOMPLETE_TRIPLET = "incomplete_triplet"
REASON_MISSING_LINK = "missing_link"
REASON_FEATURE_ORDER_MISMATCH = "feature_order_mismatch"
REASON_FEATURE_SCHEMA_MISMATCH = "feature_schema_mismatch"
REASON_NON_NUMERIC = "non_numeric"
REASON_NAN_INF = "nan_or_inf"
REASON_ZERO_VARIANCE = "zero_variance"
REASON_NOT_LAYER3_SAFE = "not_layer3_safe"
REASON_MATRIX_LOAD_FAILED = "matrix_load_failed"
REASON_HARMONIZATION_REQUIRED = "harmonization_required"
REASON_LINK_STEM_MISMATCH = "link_stem_mismatch"

# Session-native export stems mapped to manifest canonical stems (Layer 2.5 policy).
LINK_STEM_ALIASES: dict[str, str] = {
    "Neck2_to_Head": "Neck_to_Head",
}

COMPARABLE_LINKS_COLUMNS: list[str] = [
    "link_stem",
    "display_label",
    "rx_column",
    "ry_column",
    "rz_column",
    "comparable",
    "n_selected_matrices",
    "exclusion_reason",
]

EXCLUDED_LINKS_COLUMNS: list[str] = [
    "link_stem",
    "reason_code",
    "reason_message",
    "missing_in_matrices",
    "missing_axes",
    "affected_matrices",
]

FEATURE_TRIPLET_COLUMNS: list[str] = [
    "matrix_label",
    "session_id",
    "gaga_exercise_label",
    "link_stem",
    "axis",
    "feature_column",
    "present",
    "triplet_complete",
    "numeric_ok",
    "nan_count",
    "inf_count",
    "zero_variance",
]

SELECTED_MATRICES_COLUMNS: list[str] = [
    "matrix_label",
    "participant_id",
    "timepoint",
    "repetition",
    "session_id",
    "gaga_exercise_label",
    "export_granularity",
    "matrix_path",
    "manifest_path",
    "layer3_safe",
    "qc_status",
    "n_frames",
    "n_features",
    "feature_schema_id",
    "matrix_load_ok",
    "matrix_issue",
]


@dataclass
class ComparableLinksReport:
    comparable_links: pd.DataFrame = field(default_factory=pd.DataFrame)
    excluded_links: pd.DataFrame = field(default_factory=pd.DataFrame)
    feature_triplet_report: pd.DataFrame = field(default_factory=pd.DataFrame)
    selected_matrices: pd.DataFrame = field(default_factory=pd.DataFrame)
    summary: dict[str, Any] = field(default_factory=dict)
    comparable_link_stems: list[str] = field(default_factory=list)


def central_manifest_path_for_root(layer25_root: Path | str) -> Path:
    return Path(layer25_root) / CENTRAL_MANIFEST_NAME


def load_central_manifest(layer25_root: Path | str) -> pd.DataFrame:
    path = central_manifest_path_for_root(layer25_root)
    if not path.is_file():
        return pd.DataFrame()
    return pd.read_csv(path)


def matrix_label_from_row(row: pd.Series) -> str:
    exercise = str(row.get("gaga_exercise_label") or "unknown")
    session_id = str(row.get("session_id") or "")
    return f"{session_id}_{exercise}"


def select_manifest_rows(
    manifest_df: pd.DataFrame,
    *,
    participant_ids: list[str] | None = None,
    timepoints: list[str] | None = None,
    repetitions: list[str] | None = None,
    gaga_exercise_labels: list[str] | None = None,
    export_granularities: list[str] | None = None,
    layer3_safe_only: bool = True,
) -> pd.DataFrame:
    """Filter central manifest rows for comparability analysis."""
    if manifest_df.empty:
        return manifest_df.copy()

    out = manifest_df.copy()
    if participant_ids:
        out = out[out["participant_id"].astype(str).isin([str(p) for p in participant_ids])]
    if timepoints:
        out = out[out["timepoint"].astype(str).isin([str(t) for t in timepoints])]
    if repetitions:
        out = out[out["repetition"].astype(str).isin([str(r) for r in repetitions])]
    if gaga_exercise_labels:
        out = out[out["gaga_exercise_label"].astype(str).isin(gaga_exercise_labels)]
    if export_granularities:
        out = out[out["export_granularity"].astype(str).isin(export_granularities)]
    if layer3_safe_only:
        out = out[out["layer3_safe"].astype(str).str.lower().isin({"true", "1", "yes"})]
    out = out[out["matrix_path"].astype(str).str.len().gt(0)]
    return out.reset_index(drop=True)


def _display_label(link_stem: str) -> str:
    parts = link_stem.split("_to_")
    if len(parts) == 2:
        return f"{parts[0]}->{parts[1]}"
    return link_stem.replace("_", " ")


def _normalized_link_stem(link_stem: str) -> str:
    return LINK_STEM_ALIASES.get(link_stem, link_stem)


def _inspect_matrix_row(row: pd.Series) -> tuple[dict[str, Any], pd.DataFrame | None, list[str]]:
    """Load one matrix and return metadata, dataframe, feature order."""
    label = matrix_label_from_row(row)
    base = {
        "matrix_label": label,
        "participant_id": str(row.get("participant_id") or ""),
        "timepoint": str(row.get("timepoint") or ""),
        "repetition": str(row.get("repetition") or ""),
        "session_id": str(row.get("session_id") or ""),
        "gaga_exercise_label": str(row.get("gaga_exercise_label") or ""),
        "export_granularity": str(row.get("export_granularity") or ""),
        "matrix_path": str(row.get("matrix_path") or ""),
        "manifest_path": str(row.get("manifest_path") or ""),
        "layer3_safe": str(row.get("layer3_safe") or ""),
        "qc_status": str(row.get("qc_status") or ""),
        "n_frames": row.get("n_frames"),
        "n_features": row.get("n_features"),
        "feature_schema_id": str(row.get("feature_schema_id") or ""),
        "matrix_load_ok": False,
        "matrix_issue": "",
    }
    matrix_path = Path(str(row.get("matrix_path") or ""))
    if not matrix_path.is_file():
        base["matrix_issue"] = f"Matrix file not found: {matrix_path}"
        return base, None, []

    try:
        df = load_matrix(matrix_path)
    except (OSError, ValueError) as exc:
        base["matrix_issue"] = f"Matrix load failed: {exc}"
        return base, None, []

    feature_order = infer_feature_columns(df)
    base["matrix_load_ok"] = True
    base["n_features"] = len(feature_order)
    return base, df, feature_order


def _matrix_level_issues(selected_rows: pd.DataFrame) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    if selected_rows.empty:
        issues.append(
            {
                "reason_code": REASON_MATRIX_LOAD_FAILED,
                "reason_message": "No matrices selected.",
            }
        )
        return issues

    schema_ids = sorted(set(selected_rows["feature_schema_id"].astype(str).tolist()))
    if len(schema_ids) > 1:
        issues.append(
            {
                "reason_code": REASON_FEATURE_SCHEMA_MISMATCH,
                "reason_message": f"Selected matrices have different feature_schema_id values: {schema_ids}",
            }
        )

    n_features_vals = selected_rows["n_features"].dropna().unique().tolist()
    if len(n_features_vals) > 1:
        issues.append(
            {
                "reason_code": REASON_FEATURE_SCHEMA_MISMATCH,
                "reason_message": f"Selected matrices report different n_features: {n_features_vals}",
            }
        )

    unsafe = selected_rows[
        ~selected_rows["layer3_safe"].astype(str).str.lower().isin({"true", "1", "yes"})
    ]
    for _, row in unsafe.iterrows():
        issues.append(
            {
                "reason_code": REASON_NOT_LAYER3_SAFE,
                "reason_message": f"Matrix not layer3_safe: {matrix_label_from_row(row)}",
            }
        )
    return issues


def detect_comparable_links(
    selected_rows: pd.DataFrame,
    *,
    min_rows: int = 1,
) -> ComparableLinksReport:
    """Detect links comparable across all selected matrices."""
    report = ComparableLinksReport()

    matrix_records: list[dict[str, Any]] = []
    loaded: dict[str, pd.DataFrame] = {}
    feature_orders: dict[str, list[str]] = {}

    for _, row in selected_rows.iterrows():
        meta, df, feature_order = _inspect_matrix_row(row)
        matrix_records.append(meta)
        label = meta["matrix_label"]
        if df is not None:
            loaded[label] = df
            feature_orders[label] = feature_order

    selected_matrices_df = pd.DataFrame(matrix_records)
    for col in SELECTED_MATRICES_COLUMNS:
        if col not in selected_matrices_df.columns:
            selected_matrices_df[col] = ""
    report.selected_matrices = selected_matrices_df[SELECTED_MATRICES_COLUMNS]

    matrix_issues = _matrix_level_issues(selected_matrices_df)
    labels = list(loaded.keys())

    if len(labels) < 1:
        report.summary = _build_summary(
            selected_matrices_df,
            comparable=[],
            excluded=[{"link_stem": "", **issue} for issue in matrix_issues],
            comparability_status=COMPARABILITY_BLOCKING,
            feature_order_match=False,
        )
        report.excluded_links = pd.DataFrame(
            [
                {
                    "link_stem": "",
                    "reason_code": issue["reason_code"],
                    "reason_message": issue["reason_message"],
                    "missing_in_matrices": "",
                    "missing_axes": "",
                    "affected_matrices": "",
                }
                for issue in matrix_issues
            ]
        )
        return report

    reference_label = labels[0]
    reference_order = feature_orders[reference_label]
    feature_order_match = True
    order_mismatches: list[str] = []
    for label in labels[1:]:
        if feature_orders[label] != reference_order:
            feature_order_match = False
            order_mismatches.append(label)

    all_link_stems: set[str] = set()
    per_matrix_links: dict[str, set[str]] = {}
    per_matrix_maps: dict[str, dict[str, dict[str, str]]] = {}
    triplet_rows: list[dict[str, Any]] = []

    for label, df in loaded.items():
        features = feature_orders[label]
        link_map = build_joint_link_map(features)
        per_matrix_maps[label] = link_map
        stems = set(link_map.keys())
        per_matrix_links[label] = stems
        all_link_stems.update(stems)

        row_meta = selected_matrices_df[
            selected_matrices_df["matrix_label"] == label
        ].iloc[0]
        for link_stem, axis_map in link_map.items():
            triplet_complete = set(axis_map.keys()) == set(REQUIRED_AXES)
            for axis in REQUIRED_AXES:
                col = axis_map.get(axis, "")
                present = bool(col)
                numeric_ok = True
                nan_count = 0
                inf_count = 0
                zero_variance = False
                if present and col in df.columns:
                    series = df[col]
                    numeric_ok = pd.api.types.is_numeric_dtype(series)
                    if numeric_ok:
                        nan_count = int(series.isna().sum())
                        inf_count = int(np.isinf(series.to_numpy()).sum())
                        zero_variance = series.nunique(dropna=False) <= 1
                triplet_rows.append(
                    {
                        "matrix_label": label,
                        "session_id": row_meta["session_id"],
                        "gaga_exercise_label": row_meta["gaga_exercise_label"],
                        "link_stem": link_stem,
                        "axis": axis,
                        "feature_column": col,
                        "present": present,
                        "triplet_complete": triplet_complete,
                        "numeric_ok": numeric_ok,
                        "nan_count": nan_count,
                        "inf_count": inf_count,
                        "zero_variance": zero_variance,
                    }
                )

    feature_triplet_df = pd.DataFrame(triplet_rows)
    for col in FEATURE_TRIPLET_COLUMNS:
        if col not in feature_triplet_df.columns:
            feature_triplet_df[col] = ""
    report.feature_triplet_report = feature_triplet_df[FEATURE_TRIPLET_COLUMNS]

    comparable_records: list[dict[str, Any]] = []
    excluded_records: list[dict[str, Any]] = []

    if not feature_order_match:
        excluded_records.append(
            {
                "link_stem": "",
                "reason_code": REASON_FEATURE_ORDER_MISMATCH,
                "reason_message": (
                    "Feature column order differs across selected matrices. "
                    f"Mismatched matrices: {', '.join(order_mismatches)}"
                ),
                "missing_in_matrices": "",
                "missing_axes": "",
                "affected_matrices": ",".join(order_mismatches),
            }
        )

    for issue in matrix_issues:
        excluded_records.append(
            {
                "link_stem": "",
                "reason_code": issue["reason_code"],
                "reason_message": issue["reason_message"],
                "missing_in_matrices": "",
                "missing_axes": "",
                "affected_matrices": "",
            }
        )

    for link_stem in sorted(all_link_stems):
        missing_in = [label for label in labels if link_stem not in per_matrix_links[label]]
        reasons: list[str] = []
        reason_code = REASON_COMPARABLE
        affected: list[str] = []
        missing_axes_by_matrix: list[str] = []

        if missing_in:
            reason_code = REASON_MISSING_LINK
            reasons.append(f"Missing in matrices: {', '.join(missing_in)}")

        for label in labels:
            if link_stem not in per_matrix_links[label]:
                continue
            axis_map = per_matrix_maps[label][link_stem]
            missing_axes = sorted(set(REQUIRED_AXES) - set(axis_map.keys()))
            if missing_axes:
                reason_code = REASON_INCOMPLETE_TRIPLET
                missing_axes_by_matrix.append(f"{label}:{','.join(missing_axes)}")
                reasons.append(f"Incomplete triplet in {label}: missing {missing_axes}")

        link_triplet = feature_triplet_df[
            (feature_triplet_df["link_stem"] == link_stem) & feature_triplet_df["present"]
        ]
        if not link_triplet.empty:
            bad_numeric = link_triplet[~link_triplet["numeric_ok"]]
            if not bad_numeric.empty:
                reason_code = REASON_NON_NUMERIC
                mats = sorted(bad_numeric["matrix_label"].unique().tolist())
                affected.extend(mats)
                reasons.append(f"Non-numeric axis columns in: {', '.join(mats)}")

            bad_nan = link_triplet[(link_triplet["nan_count"] > 0) | (link_triplet["inf_count"] > 0)]
            if not bad_nan.empty:
                reason_code = REASON_NAN_INF
                mats = sorted(bad_nan["matrix_label"].unique().tolist())
                affected.extend(mats)
                reasons.append(f"NaN/inf values in: {', '.join(mats)}")

            bad_var = link_triplet[link_triplet["zero_variance"]]
            if not bad_var.empty:
                reason_code = REASON_ZERO_VARIANCE
                mats = sorted(bad_var["matrix_label"].unique().tolist())
                affected.extend(mats)
                reasons.append(f"Zero-variance axis columns in: {', '.join(mats)}")

        # Detect harmonization-required cases: same display label but different stems.
        competing_stems = {
            other
            for other in all_link_stems
            if other != link_stem and _display_label(other) == _display_label(link_stem)
        }
        if competing_stems and all(
            _normalized_link_stem(other) == _normalized_link_stem(link_stem)
            for other in competing_stems
        ):
            competing_stems = set()
        if competing_stems:
            reason_code = REASON_HARMONIZATION_REQUIRED
            reasons.append(
                "Link stem differs across matrices without harmonization mapping "
                f"(e.g. {link_stem} vs {', '.join(sorted(competing_stems))})."
            )

        comparable = (
            not missing_in
            and reason_code == REASON_COMPARABLE
            and feature_order_match
            and not matrix_issues
        )

        ref_axes = per_matrix_maps[reference_label].get(link_stem, {})
        record = {
            "link_stem": link_stem,
            "display_label": _display_label(link_stem),
            "rx_column": ref_axes.get("rx", ""),
            "ry_column": ref_axes.get("ry", ""),
            "rz_column": ref_axes.get("rz", ""),
            "comparable": comparable,
            "n_selected_matrices": len(labels),
            "exclusion_reason": "" if comparable else "; ".join(reasons),
        }
        comparable_records.append(record)
        if not comparable:
            excluded_records.append(
                {
                    "link_stem": link_stem,
                    "reason_code": reason_code,
                    "reason_message": "; ".join(reasons) if reasons else "Not comparable.",
                    "missing_in_matrices": ",".join(missing_in),
                    "missing_axes": "; ".join(missing_axes_by_matrix),
                    "affected_matrices": ",".join(sorted(set(affected))),
                }
            )

    comparable_df = pd.DataFrame(comparable_records)
    if comparable_df.empty:
        comparable_df = pd.DataFrame(columns=COMPARABLE_LINKS_COLUMNS)
    else:
        comparable_df = comparable_df[COMPARABLE_LINKS_COLUMNS]

    excluded_df = pd.DataFrame(excluded_records)
    if excluded_df.empty:
        excluded_df = pd.DataFrame(columns=EXCLUDED_LINKS_COLUMNS)
    else:
        excluded_df = excluded_df[EXCLUDED_LINKS_COLUMNS]

    comparable_stems = comparable_df[comparable_df["comparable"]]["link_stem"].tolist()

    comparability_status = COMPARABILITY_PASS
    if matrix_issues or not feature_order_match:
        comparability_status = COMPARABILITY_BLOCKING
    elif len(comparable_stems) < len(comparable_df):
        comparability_status = COMPARABILITY_WARNING

    report.comparable_links = comparable_df
    report.excluded_links = excluded_df
    report.comparable_link_stems = comparable_stems
    report.summary = _build_summary(
        selected_matrices_df,
        comparable=comparable_stems,
        excluded=excluded_records,
        comparability_status=comparability_status,
        feature_order_match=feature_order_match,
        reference_feature_order=reference_order,
    )
    return report


def _build_summary(
    selected_matrices: pd.DataFrame,
    *,
    comparable: list[str],
    excluded: list[dict[str, Any]],
    comparability_status: str,
    feature_order_match: bool,
    reference_feature_order: list[str] | None = None,
) -> dict[str, Any]:
    schema_ids = (
        sorted(set(selected_matrices["feature_schema_id"].astype(str).tolist()))
        if not selected_matrices.empty
        else []
    )
    return {
        "n_selected_matrices": int(len(selected_matrices)),
        "n_comparable_links": len(comparable),
        "n_excluded_links": len([e for e in excluded if e.get("link_stem")]),
        "comparability_status": comparability_status,
        "feature_schema_ids": schema_ids,
        "feature_schema_consistent": len(schema_ids) <= 1,
        "feature_order_match": feature_order_match,
        "reference_feature_order": reference_feature_order or [],
        "comparable_link_stems": comparable,
        "matrix_labels": selected_matrices["matrix_label"].tolist()
        if not selected_matrices.empty
        else [],
    }


def write_comparability_artifacts(
    report: ComparableLinksReport,
    output_dir: Path | str,
) -> dict[str, Path]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "comparable_links": out / "comparable_links.csv",
        "excluded_links": out / "excluded_links.csv",
        "feature_triplet_report": out / "feature_triplet_report.csv",
        "selected_matrices_for_comparability": out / "selected_matrices_for_comparability.csv",
        "comparability_summary": out / "comparability_summary.json",
    }
    report.comparable_links.to_csv(paths["comparable_links"], index=False)
    report.excluded_links.to_csv(paths["excluded_links"], index=False)
    report.feature_triplet_report.to_csv(paths["feature_triplet_report"], index=False)
    report.selected_matrices.to_csv(paths["selected_matrices_for_comparability"], index=False)
    paths["comparability_summary"].write_text(
        json.dumps(report.summary, indent=2),
        encoding="utf-8",
    )
    return paths


def validate_manual_link_selection(
    selected_link_stems: list[str],
    comparable_link_stems: list[str],
) -> None:
    """Raise ValueError if any selected link is not in the comparable set."""
    excluded = [stem for stem in selected_link_stems if stem not in comparable_link_stems]
    if excluded:
        raise ValueError(
            "Manual link selection includes non-comparable links: "
            f"{', '.join(excluded)}"
        )
