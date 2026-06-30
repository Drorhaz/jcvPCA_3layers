"""Dataset construction preview for Gaga JcvPCA workbench (Phase 4).

Builds transparent Dataset A / Dataset B construction plans from central manifest
rows and Phase 3 comparable-link selections. Does not run PCA, centering,
projection, RSS, NV, or any analysis execution.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from itertools import product
from pathlib import Path
from typing import Any

import pandas as pd

from layer3_jcvpca.comparable_links import matrix_label_from_row, select_manifest_rows
from layer3_jcvpca.data_contract import (
    GAGA_EXERCISE_LABELS,
    REQUIRED_METADATA_COLUMNS,
)
from layer3_jcvpca.io import build_joint_link_map, infer_feature_columns, load_matrix

ANALYSIS_MODE_LONGITUDINAL = "longitudinal"
ANALYSIS_MODE_EXPLORATORY = "exploratory"
ANALYSIS_MODES: tuple[str, str] = (ANALYSIS_MODE_LONGITUDINAL, ANALYSIS_MODE_EXPLORATORY)

CONSTRUCTION_PASS = "pass"
CONSTRUCTION_WARNING = "warning"
CONSTRUCTION_BLOCKING = "blocking"

PRESET_P1_P2 = "P1+P2"
PRESET_P3_P4_P5 = "P3+P4+P5"
PRESET_ALL_P1_P5 = "All P1-P5"
PRESET_CUSTOM = "Custom"
EXERCISE_PRESETS: dict[str, list[str]] = {
    PRESET_P1_P2: ["P1", "P2"],
    PRESET_P3_P4_P5: ["P3", "P4", "P5"],
    PRESET_ALL_P1_P5: list(GAGA_EXERCISE_LABELS),
    PRESET_CUSTOM: [],
}

REASON_MISSING_MATRIX = "missing_matrix"
REASON_MATRIX_LOAD_FAILED = "matrix_load_failed"
REASON_MISSING_REPETITION = "missing_repetition"
REASON_NO_SOURCES = "no_sources"
REASON_NO_LINKS = "no_links"
REASON_FEATURE_ORDER_MISMATCH = "feature_order_mismatch"
REASON_FEATURE_COLUMN_MISSING = "feature_column_missing"
REASON_UNEQUAL_ROW_COUNTS = "unequal_row_counts"

PREVIEW_TRACKING_COLUMNS: tuple[str, ...] = (
    "_source_concat_order",
    "_source_matrix_label",
    "_source_session_id",
    "_source_gaga_exercise_label",
)

WARNING_SEVERITY = "warning"
BLOCKING_SEVERITY = "blocking"

DATASET_A_SOURCES_COLUMNS: list[str] = [
    "concat_order",
    "participant_id",
    "timepoint",
    "repetition",
    "session_id",
    "gaga_exercise_label",
    "export_granularity",
    "matrix_path",
    "n_rows",
    "row_start_index",
    "row_end_index",
    "matrix_label",
]

DATASET_FEATURE_COLUMNS: list[str] = [
    "column_name",
    "column_role",
    "link_stem",
    "axis",
    "included_in_pca",
]

DATASET_WARNINGS_COLUMNS: list[str] = [
    "severity",
    "reason_code",
    "reason_message",
    "dataset_side",
    "participant_id",
    "timepoint",
    "repetition",
    "gaga_exercise_label",
]


@dataclass
class DatasetSideSpec:
    timepoints: list[str] = field(default_factory=list)
    repetitions: list[str] = field(default_factory=list)


@dataclass
class DatasetConstructionConfig:
    analysis_mode: str = ANALYSIS_MODE_LONGITUDINAL
    participant_ids: list[str] = field(default_factory=list)
    export_granularities: list[str] = field(default_factory=lambda: ["per_exercise"])
    exercise_preset: str = PRESET_CUSTOM
    exercises: list[str] = field(default_factory=list)
    dataset_a: DatasetSideSpec = field(default_factory=DatasetSideSpec)
    dataset_b: DatasetSideSpec = field(default_factory=DatasetSideSpec)
    exploratory_timepoint: str = ""
    exploratory_repetition_a: str = "R1"
    exploratory_repetition_b: str = "R2"
    selected_link_stems: list[str] = field(default_factory=list)
    acknowledge_missing_repetitions: bool = False


@dataclass
class DatasetSideResult:
    sources: pd.DataFrame = field(default_factory=pd.DataFrame)
    preview: pd.DataFrame = field(default_factory=pd.DataFrame)
    total_rows: int = 0
    n_source_matrices: int = 0


@dataclass
class DatasetConstructionResult:
    config: DatasetConstructionConfig = field(default_factory=DatasetConstructionConfig)
    dataset_a: DatasetSideResult = field(default_factory=DatasetSideResult)
    dataset_b: DatasetSideResult = field(default_factory=DatasetSideResult)
    feature_columns: pd.DataFrame = field(default_factory=pd.DataFrame)
    pca_feature_columns: list[str] = field(default_factory=list)
    metadata_columns: list[str] = field(default_factory=list)
    warnings: pd.DataFrame = field(default_factory=pd.DataFrame)
    blocking_errors: pd.DataFrame = field(default_factory=pd.DataFrame)
    plan: dict[str, Any] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)
    construction_status: str = CONSTRUCTION_BLOCKING


def resolve_exercise_labels(*, preset: str, custom_exercises: list[str] | None = None) -> list[str]:
    """Resolve exercise labels from a preset name or custom list."""
    if preset == PRESET_CUSTOM:
        return list(custom_exercises or [])
    if preset in EXERCISE_PRESETS:
        return list(EXERCISE_PRESETS[preset])
    raise ValueError(f"Unknown exercise preset: {preset}")


def _exercise_sort_key(label: str) -> tuple[int, str]:
    order = {name: idx for idx, name in enumerate(GAGA_EXERCISE_LABELS)}
    order["combined_group4"] = len(GAGA_EXERCISE_LABELS)
    return (order.get(label, 999), label)


def _manifest_sort_key(row: pd.Series) -> tuple[Any, ...]:
    return (
        str(row.get("participant_id") or ""),
        str(row.get("timepoint") or ""),
        str(row.get("repetition") or ""),
        *_exercise_sort_key(str(row.get("gaga_exercise_label") or "")),
    )


def order_manifest_rows(rows: pd.DataFrame) -> pd.DataFrame:
    """Sort manifest rows for stable row-wise concatenation."""
    if rows.empty:
        return rows.copy()
    out = rows.copy()
    out["_sort_key"] = out.apply(_manifest_sort_key, axis=1)
    out = out.sort_values("_sort_key").drop(columns="_sort_key").reset_index(drop=True)
    return out


def select_dataset_source_rows(
    manifest_df: pd.DataFrame,
    *,
    participant_ids: list[str],
    timepoints: list[str],
    repetitions: list[str],
    exercises: list[str],
    export_granularities: list[str] | None = None,
) -> pd.DataFrame:
    """Select and order manifest rows for one dataset side."""
    selected = select_manifest_rows(
        manifest_df,
        participant_ids=participant_ids,
        timepoints=timepoints or None,
        repetitions=repetitions or None,
        gaga_exercise_labels=exercises or None,
        export_granularities=export_granularities,
    )
    return order_manifest_rows(selected)


def feature_columns_for_links(
    link_stems: list[str],
    reference_feature_order: list[str],
) -> tuple[list[str], list[dict[str, str]]]:
    """Return ordered PCA feature columns (rx, ry, rz per link) and issue records."""
    link_map = build_joint_link_map(reference_feature_order)
    columns: list[str] = []
    issues: list[dict[str, str]] = []
    for stem in link_stems:
        axis_map = link_map.get(stem, {})
        missing_axes = [axis for axis in ("rx", "ry", "rz") if axis not in axis_map]
        if missing_axes:
            issues.append(
                {
                    "link_stem": stem,
                    "reason_code": REASON_FEATURE_COLUMN_MISSING,
                    "reason_message": f"Missing axes for link {stem}: {missing_axes}",
                }
            )
            continue
        for axis in ("rx", "ry", "rz"):
            columns.append(axis_map[axis])
    return columns, issues


def build_feature_columns_table(
    *,
    metadata_columns: list[str],
    pca_feature_columns: list[str],
    selected_link_stems: list[str],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for col in metadata_columns:
        rows.append(
            {
                "column_name": col,
                "column_role": "metadata",
                "link_stem": "",
                "axis": "",
                "included_in_pca": False,
            }
        )
    for col in PREVIEW_TRACKING_COLUMNS:
        rows.append(
            {
                "column_name": col,
                "column_role": "preview_tracking",
                "link_stem": "",
                "axis": "",
                "included_in_pca": False,
            }
        )
    for stem in selected_link_stems:
        for axis in ("rx", "ry", "rz"):
            col_name = f"{stem}_{axis}"
            if col_name not in pca_feature_columns:
                col_name = next(
                    (c for c in pca_feature_columns if c.endswith(f"_{axis}") and stem in c),
                    "",
                )
            rows.append(
                {
                    "column_name": col_name,
                    "column_role": "pca_feature",
                    "link_stem": stem,
                    "axis": axis,
                    "included_in_pca": bool(col_name),
                }
            )
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=DATASET_FEATURE_COLUMNS)
    return df[DATASET_FEATURE_COLUMNS]


def _expected_combinations(
    participant_ids: list[str],
    timepoints: list[str],
    repetitions: list[str],
    exercises: list[str],
) -> list[tuple[str, str, str, str]]:
    return list(product(participant_ids, timepoints, repetitions, exercises))


def _find_missing_combinations(
    manifest_df: pd.DataFrame,
    expected: list[tuple[str, str, str, str]],
) -> list[tuple[str, str, str, str]]:
    if not expected:
        return []
    present = set(
        zip(
            manifest_df["participant_id"].astype(str),
            manifest_df["timepoint"].astype(str),
            manifest_df["repetition"].astype(str),
            manifest_df["gaga_exercise_label"].astype(str),
        )
    )
    return [combo for combo in expected if combo not in present]


def _append_issue(
    records: list[dict[str, Any]],
    *,
    severity: str,
    reason_code: str,
    reason_message: str,
    dataset_side: str = "",
    participant_id: str = "",
    timepoint: str = "",
    repetition: str = "",
    gaga_exercise_label: str = "",
) -> None:
    records.append(
        {
            "severity": severity,
            "reason_code": reason_code,
            "reason_message": reason_message,
            "dataset_side": dataset_side,
            "participant_id": participant_id,
            "timepoint": timepoint,
            "repetition": repetition,
            "gaga_exercise_label": gaga_exercise_label,
        }
    )


def _resolve_reference_feature_order(source_rows: pd.DataFrame) -> tuple[list[str], list[dict[str, Any]]]:
    blocking: list[dict[str, Any]] = []
    for _, row in source_rows.iterrows():
        matrix_path = Path(str(row.get("matrix_path") or ""))
        if not matrix_path.is_file():
            continue
        try:
            df = load_matrix(matrix_path)
        except (OSError, ValueError) as exc:
            blocking.append(
                {
                    "severity": BLOCKING_SEVERITY,
                    "reason_code": REASON_MATRIX_LOAD_FAILED,
                    "reason_message": f"Failed to load reference matrix {matrix_path}: {exc}",
                    "dataset_side": "",
                    "participant_id": str(row.get("participant_id") or ""),
                    "timepoint": str(row.get("timepoint") or ""),
                    "repetition": str(row.get("repetition") or ""),
                    "gaga_exercise_label": str(row.get("gaga_exercise_label") or ""),
                }
            )
            continue
        return infer_feature_columns(df), blocking
    return [], blocking


def _verify_feature_order_across_sources(
    source_rows: pd.DataFrame,
    reference_order: list[str],
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    if not reference_order:
        return issues
    for _, row in source_rows.iterrows():
        matrix_path = Path(str(row.get("matrix_path") or ""))
        if not matrix_path.is_file():
            continue
        try:
            df = load_matrix(matrix_path)
        except (OSError, ValueError):
            continue
        order = infer_feature_columns(df)
        if order != reference_order:
            label = matrix_label_from_row(row)
            issues.append(
                {
                    "reason_code": REASON_FEATURE_ORDER_MISMATCH,
                    "reason_message": (
                        f"Feature column order differs from reference in {label}."
                    ),
                    "dataset_side": "",
                }
            )
    return issues


def _build_side_preview(
    source_rows: pd.DataFrame,
    *,
    dataset_side: str,
    pca_feature_columns: list[str],
    metadata_columns: list[str],
    blocking_records: list[dict[str, Any]],
) -> DatasetSideResult:
    result = DatasetSideResult()
    if source_rows.empty:
        _append_issue(
            blocking_records,
            severity=BLOCKING_SEVERITY,
            reason_code=REASON_NO_SOURCES,
            reason_message=f"No source matrices selected for Dataset {dataset_side}.",
            dataset_side=dataset_side,
        )
        return result

    preview_parts: list[pd.DataFrame] = []
    source_records: list[dict[str, Any]] = []
    row_offset = 0
    preview_columns = list(metadata_columns) + list(PREVIEW_TRACKING_COLUMNS) + list(pca_feature_columns)

    for concat_order, (_, row) in enumerate(source_rows.iterrows(), start=1):
        matrix_path = Path(str(row.get("matrix_path") or ""))
        label = matrix_label_from_row(row)
        base_record = {
            "concat_order": concat_order,
            "participant_id": str(row.get("participant_id") or ""),
            "timepoint": str(row.get("timepoint") or ""),
            "repetition": str(row.get("repetition") or ""),
            "session_id": str(row.get("session_id") or ""),
            "gaga_exercise_label": str(row.get("gaga_exercise_label") or ""),
            "export_granularity": str(row.get("export_granularity") or ""),
            "matrix_path": str(matrix_path),
            "matrix_label": label,
        }
        if not matrix_path.is_file():
            _append_issue(
                blocking_records,
                severity=BLOCKING_SEVERITY,
                reason_code=REASON_MISSING_MATRIX,
                reason_message=f"Matrix file not found: {matrix_path}",
                dataset_side=dataset_side,
                participant_id=base_record["participant_id"],
                timepoint=base_record["timepoint"],
                repetition=base_record["repetition"],
                gaga_exercise_label=base_record["gaga_exercise_label"],
            )
            continue

        try:
            df = load_matrix(matrix_path)
        except (OSError, ValueError) as exc:
            _append_issue(
                blocking_records,
                severity=BLOCKING_SEVERITY,
                reason_code=REASON_MATRIX_LOAD_FAILED,
                reason_message=f"Matrix load failed for {matrix_path}: {exc}",
                dataset_side=dataset_side,
                participant_id=base_record["participant_id"],
                timepoint=base_record["timepoint"],
                repetition=base_record["repetition"],
                gaga_exercise_label=base_record["gaga_exercise_label"],
            )
            continue

        missing_meta = [c for c in metadata_columns if c not in df.columns]
        if missing_meta:
            _append_issue(
                blocking_records,
                severity=BLOCKING_SEVERITY,
                reason_code=REASON_FEATURE_COLUMN_MISSING,
                reason_message=f"Missing metadata columns in {label}: {missing_meta}",
                dataset_side=dataset_side,
                participant_id=base_record["participant_id"],
                timepoint=base_record["timepoint"],
                repetition=base_record["repetition"],
                gaga_exercise_label=base_record["gaga_exercise_label"],
            )
            continue

        missing_features = [c for c in pca_feature_columns if c not in df.columns]
        if missing_features:
            _append_issue(
                blocking_records,
                severity=BLOCKING_SEVERITY,
                reason_code=REASON_FEATURE_COLUMN_MISSING,
                reason_message=(
                    f"Missing selected feature columns in {label}: "
                    f"{missing_features[:6]}{'...' if len(missing_features) > 6 else ''}"
                ),
                dataset_side=dataset_side,
                participant_id=base_record["participant_id"],
                timepoint=base_record["timepoint"],
                repetition=base_record["repetition"],
                gaga_exercise_label=base_record["gaga_exercise_label"],
            )
            continue

        n_rows = len(df)
        part = df[list(metadata_columns) + list(pca_feature_columns)].copy()
        part["_source_concat_order"] = concat_order
        part["_source_matrix_label"] = label
        part["_source_session_id"] = base_record["session_id"]
        part["_source_gaga_exercise_label"] = base_record["gaga_exercise_label"]
        preview_parts.append(part[preview_columns])

        source_records.append(
            {
                **base_record,
                "n_rows": n_rows,
                "row_start_index": row_offset,
                "row_end_index": row_offset + n_rows - 1 if n_rows else row_offset,
            }
        )
        row_offset += n_rows

    sources_df = pd.DataFrame(source_records)
    for col in DATASET_A_SOURCES_COLUMNS:
        if col not in sources_df.columns:
            sources_df[col] = ""
    if not sources_df.empty:
        sources_df = sources_df[DATASET_A_SOURCES_COLUMNS]

    result.sources = sources_df
    result.n_source_matrices = len(source_records)
    if preview_parts:
        result.preview = pd.concat(preview_parts, ignore_index=True)
        result.total_rows = len(result.preview)
    return result


def build_dataset_construction_preview(
    manifest_df: pd.DataFrame,
    config: DatasetConstructionConfig,
) -> DatasetConstructionResult:
    """Build Dataset A/B construction preview from manifest rows and config."""
    result = DatasetConstructionResult(config=config)
    warning_records: list[dict[str, Any]] = []
    blocking_records: list[dict[str, Any]] = []

    exercises = config.exercises or resolve_exercise_labels(
        preset=config.exercise_preset,
        custom_exercises=[],
    )
    if not exercises:
        _append_issue(
            blocking_records,
            severity=BLOCKING_SEVERITY,
            reason_code=REASON_NO_SOURCES,
            reason_message="No exercises selected for dataset construction.",
        )

    if not config.selected_link_stems:
        _append_issue(
            blocking_records,
            severity=BLOCKING_SEVERITY,
            reason_code=REASON_NO_LINKS,
            reason_message="No comparable links selected from Phase 3.",
        )

    participants = config.participant_ids
    granularity = config.export_granularities or None
    a_rows = pd.DataFrame()
    b_rows = pd.DataFrame()

    if config.analysis_mode == ANALYSIS_MODE_EXPLORATORY:
        if not config.exploratory_timepoint:
            _append_issue(
                blocking_records,
                severity=BLOCKING_SEVERITY,
                reason_code=REASON_NO_SOURCES,
                reason_message="Exploratory mode requires a timepoint.",
            )
        else:
            a_rows = select_dataset_source_rows(
                manifest_df,
                participant_ids=participants,
                timepoints=[config.exploratory_timepoint],
                repetitions=[config.exploratory_repetition_a],
                exercises=exercises,
                export_granularities=granularity,
            )
            b_rows = select_dataset_source_rows(
                manifest_df,
                participant_ids=participants,
                timepoints=[config.exploratory_timepoint],
                repetitions=[config.exploratory_repetition_b],
                exercises=exercises,
                export_granularities=granularity,
            )
            for participant_id in participants:
                for exercise in exercises:
                    for rep, side in (
                        (config.exploratory_repetition_a, "A"),
                        (config.exploratory_repetition_b, "B"),
                    ):
                        match = manifest_df[
                            (manifest_df["participant_id"].astype(str) == participant_id)
                            & (manifest_df["timepoint"].astype(str) == config.exploratory_timepoint)
                            & (manifest_df["repetition"].astype(str) == rep)
                            & (manifest_df["gaga_exercise_label"].astype(str) == exercise)
                        ]
                        if granularity:
                            match = match[match["export_granularity"].astype(str).isin(granularity)]
                        if match.empty:
                            _append_issue(
                                blocking_records,
                                severity=BLOCKING_SEVERITY,
                                reason_code=REASON_MISSING_REPETITION,
                                reason_message=(
                                    f"Exploratory construction blocked: missing repetition {rep} "
                                    f"for participant {participant_id}, {config.exploratory_timepoint}, "
                                    f"exercise {exercise}."
                                ),
                                dataset_side=side,
                                participant_id=participant_id,
                                timepoint=config.exploratory_timepoint,
                                repetition=rep,
                                gaga_exercise_label=exercise,
                            )
    else:
        a_rows = select_dataset_source_rows(
            manifest_df,
            participant_ids=participants,
            timepoints=config.dataset_a.timepoints,
            repetitions=config.dataset_a.repetitions,
            exercises=exercises,
            export_granularities=granularity,
        )
        b_rows = select_dataset_source_rows(
            manifest_df,
            participant_ids=participants,
            timepoints=config.dataset_b.timepoints,
            repetitions=config.dataset_b.repetitions,
            exercises=exercises,
            export_granularities=granularity,
        )
        expected_a = _expected_combinations(
            participants,
            config.dataset_a.timepoints,
            config.dataset_a.repetitions,
            exercises,
        )
        expected_b = _expected_combinations(
            participants,
            config.dataset_b.timepoints,
            config.dataset_b.repetitions,
            exercises,
        )
        for participant_id, timepoint, repetition, exercise in _find_missing_combinations(
            manifest_df, expected_a
        ):
            _append_issue(
                warning_records,
                severity=WARNING_SEVERITY,
                reason_code=REASON_MISSING_MATRIX,
                reason_message=(
                    f"Expected Dataset A source missing: participant {participant_id}, "
                    f"{timepoint} {repetition}, exercise {exercise}."
                ),
                dataset_side="A",
                participant_id=participant_id,
                timepoint=timepoint,
                repetition=repetition,
                gaga_exercise_label=exercise,
            )
        for participant_id, timepoint, repetition, exercise in _find_missing_combinations(
            manifest_df, expected_b
        ):
            _append_issue(
                warning_records,
                severity=WARNING_SEVERITY,
                reason_code=REASON_MISSING_MATRIX,
                reason_message=(
                    f"Expected Dataset B source missing: participant {participant_id}, "
                    f"{timepoint} {repetition}, exercise {exercise}."
                ),
                dataset_side="B",
                participant_id=participant_id,
                timepoint=timepoint,
                repetition=repetition,
                gaga_exercise_label=exercise,
            )

    if blocking_records and any(r["severity"] == BLOCKING_SEVERITY for r in blocking_records):
        result.blocking_errors = _issues_df(blocking_records)
        result.warnings = _issues_df(warning_records)
        result.summary = _build_summary(result, exercises)
        result.plan = _build_plan(result, exercises)
        result.construction_status = CONSTRUCTION_BLOCKING
        return result

    reference_rows = a_rows if not a_rows.empty else b_rows
    reference_order, ref_blocking = _resolve_reference_feature_order(reference_rows)
    blocking_records.extend(ref_blocking)

    pca_feature_columns, link_issues = feature_columns_for_links(
        config.selected_link_stems,
        reference_order,
    )
    for issue in link_issues:
        _append_issue(
            blocking_records,
            severity=BLOCKING_SEVERITY,
            reason_code=issue["reason_code"],
            reason_message=issue["reason_message"],
        )

    metadata_columns = list(REQUIRED_METADATA_COLUMNS)

    if blocking_records:
        result.blocking_errors = _issues_df(blocking_records)
        result.warnings = _issues_df(warning_records)
        result.summary = _build_summary(result, exercises)
        result.plan = _build_plan(result, exercises)
        result.construction_status = CONSTRUCTION_BLOCKING
        return result

    order_issues = _verify_feature_order_across_sources(
        pd.concat([a_rows, b_rows], ignore_index=True),
        reference_order,
    )
    for issue in order_issues:
        _append_issue(
            blocking_records,
            severity=BLOCKING_SEVERITY,
            reason_code=issue["reason_code"],
            reason_message=issue["reason_message"],
            dataset_side=issue.get("dataset_side", ""),
        )
    if blocking_records:
        result.blocking_errors = _issues_df(blocking_records)
        result.warnings = _issues_df(warning_records)
        result.summary = _build_summary(result, exercises)
        result.plan = _build_plan(result, exercises)
        result.construction_status = CONSTRUCTION_BLOCKING
        return result

    result.dataset_a = _build_side_preview(
        a_rows,
        dataset_side="A",
        pca_feature_columns=pca_feature_columns,
        metadata_columns=metadata_columns,
        blocking_records=blocking_records,
    )
    result.dataset_b = _build_side_preview(
        b_rows,
        dataset_side="B",
        pca_feature_columns=pca_feature_columns,
        metadata_columns=metadata_columns,
        blocking_records=blocking_records,
    )

    if blocking_records:
        result.blocking_errors = _issues_df(blocking_records)
        result.warnings = _issues_df(warning_records)
        result.summary = _build_summary(result, exercises)
        result.plan = _build_plan(result, exercises)
        result.construction_status = CONSTRUCTION_BLOCKING
        return result

    if result.dataset_a.total_rows != result.dataset_b.total_rows:
        _append_issue(
            warning_records,
            severity=WARNING_SEVERITY,
            reason_code=REASON_UNEQUAL_ROW_COUNTS,
            reason_message=(
                f"Dataset A has {result.dataset_a.total_rows} rows and Dataset B has "
                f"{result.dataset_b.total_rows} rows. Unequal row counts are allowed "
                "for preview but must be understood before analysis."
            ),
        )

    if warning_records and config.analysis_mode == ANALYSIS_MODE_LONGITUDINAL:
        if not config.acknowledge_missing_repetitions and any(
            r["reason_code"] == REASON_MISSING_MATRIX for r in warning_records
        ):
            _append_issue(
                blocking_records,
                severity=BLOCKING_SEVERITY,
                reason_code=REASON_MISSING_MATRIX,
                reason_message=(
                    "Expected source matrices are missing. Acknowledge missing repetitions "
                    "to continue with available data."
                ),
            )

    result.pca_feature_columns = pca_feature_columns
    result.metadata_columns = metadata_columns
    result.feature_columns = build_feature_columns_table(
        metadata_columns=metadata_columns,
        pca_feature_columns=pca_feature_columns,
        selected_link_stems=config.selected_link_stems,
    )
    result.warnings = _issues_df(warning_records)
    result.blocking_errors = _issues_df(blocking_records)

    if not result.blocking_errors.empty:
        result.construction_status = CONSTRUCTION_BLOCKING
    elif not result.warnings.empty:
        result.construction_status = CONSTRUCTION_WARNING
    else:
        result.construction_status = CONSTRUCTION_PASS

    result.summary = _build_summary(result, exercises)
    result.plan = _build_plan(result, exercises)
    return result


def _issues_df(records: list[dict[str, Any]]) -> pd.DataFrame:
    if not records:
        return pd.DataFrame(columns=DATASET_WARNINGS_COLUMNS)
    df = pd.DataFrame(records)
    for col in DATASET_WARNINGS_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df[DATASET_WARNINGS_COLUMNS]


def _build_summary(result: DatasetConstructionResult, exercises: list[str]) -> dict[str, Any]:
    cfg = result.config
    return {
        "construction_status": result.construction_status,
        "analysis_mode": cfg.analysis_mode,
        "participant_ids": cfg.participant_ids,
        "exercise_preset": cfg.exercise_preset,
        "exercises": exercises,
        "selected_link_stems": cfg.selected_link_stems,
        "n_selected_links": len(cfg.selected_link_stems),
        "n_pca_feature_columns": len(result.pca_feature_columns),
        "n_metadata_columns": len(result.metadata_columns),
        "metadata_columns_excluded_from_pca": result.metadata_columns,
        "preview_tracking_columns_excluded_from_pca": list(PREVIEW_TRACKING_COLUMNS),
        "dataset_a_total_rows": result.dataset_a.total_rows,
        "dataset_b_total_rows": result.dataset_b.total_rows,
        "dataset_a_source_matrices": result.dataset_a.n_source_matrices,
        "dataset_b_source_matrices": result.dataset_b.n_source_matrices,
        "n_warnings": len(result.warnings),
        "n_blocking_errors": len(result.blocking_errors),
        "row_counts_equal": result.dataset_a.total_rows == result.dataset_b.total_rows,
    }


def _build_plan(result: DatasetConstructionResult, exercises: list[str]) -> dict[str, Any]:
    cfg = result.config
    plan: dict[str, Any] = {
        "analysis_mode": cfg.analysis_mode,
        "participant_ids": cfg.participant_ids,
        "export_granularities": cfg.export_granularities,
        "exercise_preset": cfg.exercise_preset,
        "exercises": exercises,
        "selected_link_stems": cfg.selected_link_stems,
        "pca_feature_columns": result.pca_feature_columns,
        "metadata_columns_excluded_from_pca": result.metadata_columns,
        "preview_tracking_columns_excluded_from_pca": list(PREVIEW_TRACKING_COLUMNS),
        "construction_status": result.construction_status,
        "dataset_a": {
            "timepoints": cfg.dataset_a.timepoints,
            "repetitions": cfg.dataset_a.repetitions,
            "total_rows": result.dataset_a.total_rows,
            "source_concat_order": result.dataset_a.sources["matrix_label"].tolist()
            if not result.dataset_a.sources.empty
            else [],
        },
        "dataset_b": {
            "timepoints": cfg.dataset_b.timepoints,
            "repetitions": cfg.dataset_b.repetitions,
            "total_rows": result.dataset_b.total_rows,
            "source_concat_order": result.dataset_b.sources["matrix_label"].tolist()
            if not result.dataset_b.sources.empty
            else [],
        },
    }
    if cfg.analysis_mode == ANALYSIS_MODE_EXPLORATORY:
        plan["exploratory"] = {
            "timepoint": cfg.exploratory_timepoint,
            "repetition_a": cfg.exploratory_repetition_a,
            "repetition_b": cfg.exploratory_repetition_b,
        }
    return plan


def build_upstream_fingerprint(payload: dict[str, Any]) -> str:
    """Hash upstream workbench selections for preview invalidation."""
    import hashlib

    encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def write_dataset_construction_artifacts(
    result: DatasetConstructionResult,
    output_dir: Path | str,
) -> dict[str, Path]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "dataset_construction_plan": out / "dataset_construction_plan.json",
        "dataset_A_sources": out / "dataset_A_sources.csv",
        "dataset_B_sources": out / "dataset_B_sources.csv",
        "dataset_A_preview": out / "dataset_A_preview.csv",
        "dataset_B_preview": out / "dataset_B_preview.csv",
        "dataset_feature_columns": out / "dataset_feature_columns.csv",
        "dataset_construction_summary": out / "dataset_construction_summary.json",
        "dataset_construction_warnings": out / "dataset_construction_warnings.csv",
    }
    paths["dataset_construction_plan"].write_text(
        json.dumps(result.plan, indent=2),
        encoding="utf-8",
    )
    result.dataset_a.sources.to_csv(paths["dataset_A_sources"], index=False)
    result.dataset_b.sources.to_csv(paths["dataset_B_sources"], index=False)
    result.dataset_a.preview.to_csv(paths["dataset_A_preview"], index=False)
    result.dataset_b.preview.to_csv(paths["dataset_B_preview"], index=False)
    result.feature_columns.to_csv(paths["dataset_feature_columns"], index=False)
    paths["dataset_construction_summary"].write_text(
        json.dumps(result.summary, indent=2),
        encoding="utf-8",
    )
    warnings = pd.concat([result.warnings, result.blocking_errors], ignore_index=True)
    if warnings.empty:
        warnings = pd.DataFrame(columns=DATASET_WARNINGS_COLUMNS)
    warnings.to_csv(paths["dataset_construction_warnings"], index=False)
    return paths
