"""Quaternion norm, missingness, and validity QC helpers (Stage 04)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd

from layer2_motive.parsing import MOTIVE_COMPONENT_ORDER, ParsedMotiveHeader
from layer2_motive.validation import HardStopError

QCStatus = str  # "pass" | "warning" | "fail"


@dataclass(frozen=True)
class QuaternionQCThresholds:
    """Provisional conservative thresholds for Stage 04 numeric quaternion QC."""

    expected_unit_norm: float = 1.0
    pass_max_abs_norm_error: float = 1e-3
    warning_max_abs_norm_error: float = 1e-2
    near_zero_norm_threshold: float = 1e-8
    min_complete_xyzw_percent: float = 99.0
    max_warning_gap_frames: int = 5
    max_fail_gap_frames: int = 5


@dataclass
class InvalidGapRecord:
    source_bone_name: str
    gap_start_row_index: int
    gap_end_row_index: int
    gap_length_frames: int
    gap_start_frame: int | None
    gap_end_frame: int | None


@dataclass
class BoneQuaternionQCResult:
    source_bone_name: str
    has_complete_xyzw_columns: bool
    total_frames: int
    finite_row_count: int
    non_finite_row_count: int
    missing_x_count: int
    missing_y_count: int
    missing_z_count: int
    missing_w_count: int
    complete_xyzw_row_count: int
    complete_xyzw_percent: float
    min_norm: float | None
    max_norm: float | None
    mean_norm: float | None
    median_norm: float | None
    std_norm: float | None
    max_abs_norm_error: float | None
    norm_outside_tolerance_count: int
    norm_outside_tolerance_percent: float
    zero_norm_count: int
    near_zero_norm_count: int
    invalid_row_count: int
    first_invalid_row_index: int | None
    last_invalid_row_index: int | None
    first_invalid_frame: int | None
    last_invalid_frame: int | None
    invalid_gap_count: int
    longest_invalid_gap_length: int
    qc_status: QCStatus
    qc_fail_reasons: list[str] = field(default_factory=list)
    qc_warning_reasons: list[str] = field(default_factory=list)
    stage05_may_proceed: bool = False
    invalid_gaps: list[InvalidGapRecord] = field(default_factory=list)


@dataclass
class FileQuaternionQCResult:
    input_file: str
    quaternion_group_count: int
    groups_pass: int
    groups_warning: int
    groups_fail: int
    total_zero_norm_count: int
    total_near_zero_norm_count: int
    total_non_finite_count: int
    max_abs_norm_error_observed: float | None
    longest_invalid_gap_observed: int
    file_qc_status: QCStatus
    stage05_may_proceed: bool
    bone_results: list[BoneQuaternionQCResult]
    fail_reasons: list[str] = field(default_factory=list)
    warning_reasons: list[str] = field(default_factory=list)


def load_bone_rotation_numeric_data(
    csv_path: Path,
    parsed: ParsedMotiveHeader,
    groups: dict[str, dict[str, int]],
) -> tuple[pd.DataFrame, dict[int, int], pd.Series | None]:
    """Load numeric bone rotation columns and optional Frame series."""
    if parsed.data_start_line_number is None:
        raise HardStopError("Cannot run Stage 04: data start row unknown")

    usecols: set[int] = set()
    for components in groups.values():
        usecols.update(components.values())
    frame_series: pd.Series | None = None
    if parsed.frame_time.frame_column_index is not None:
        usecols.add(parsed.frame_time.frame_column_index)

    if not usecols:
        raise HardStopError("No Bone Rotation quaternion column groups detected")

    sorted_usecols = sorted(usecols)
    data = pd.read_csv(
        csv_path,
        skiprows=parsed.data_start_line_number - 1,
        header=None,
        usecols=sorted_usecols,
        dtype=str,
        low_memory=False,
    )
    numeric = cast(pd.DataFrame, data.apply(pd.to_numeric, errors="coerce"))
    col_to_pos = {col_idx: pos for pos, col_idx in enumerate(sorted_usecols)}

    rotation_usecols = list(sorted_usecols)
    if parsed.frame_time.frame_column_index is not None:
        frame_pos = col_to_pos[parsed.frame_time.frame_column_index]
        frame_series = numeric.iloc[:, frame_pos].astype("Int64")
        rotation_usecols = [
            col_idx
            for col_idx in sorted_usecols
            if col_idx != parsed.frame_time.frame_column_index
        ]

    rotation_numeric = numeric.iloc[:, [col_to_pos[col_idx] for col_idx in rotation_usecols]]
    rotation_col_to_pos = {col_idx: pos for pos, col_idx in enumerate(rotation_usecols)}
    return rotation_numeric, rotation_col_to_pos, frame_series


def _compute_norms(components: pd.DataFrame) -> np.ndarray:
    arr = components.to_numpy(dtype=float)
    return np.linalg.norm(arr, axis=1)


def find_contiguous_invalid_gaps(
    invalid_mask: np.ndarray,
    *,
    bone_name: str,
    frame_series: pd.Series | None,
) -> list[InvalidGapRecord]:
    gaps: list[InvalidGapRecord] = []
    index = 0
    total = len(invalid_mask)
    while index < total:
        if not invalid_mask[index]:
            index += 1
            continue
        start = index
        while index < total and invalid_mask[index]:
            index += 1
        end = index - 1
        start_frame = None
        end_frame = None
        if frame_series is not None:
            start_frame_val = frame_series.iloc[start]
            end_frame_val = frame_series.iloc[end]
            if pd.notna(start_frame_val):
                start_frame = int(start_frame_val)
            if pd.notna(end_frame_val):
                end_frame = int(end_frame_val)
        gaps.append(
            InvalidGapRecord(
                source_bone_name=bone_name,
                gap_start_row_index=start,
                gap_end_row_index=end,
                gap_length_frames=end - start + 1,
                gap_start_frame=start_frame,
                gap_end_frame=end_frame,
            )
        )
    return gaps


def _determine_qc_status(
    *,
    thresholds: QuaternionQCThresholds,
    has_complete_xyzw_columns: bool,
    complete_xyzw_percent: float,
    inf_row_count: int,
    zero_norm_count: int,
    near_zero_norm_count: int,
    max_abs_norm_error: float | None,
    longest_invalid_gap_length: int,
    invalid_row_count: int,
) -> tuple[QCStatus, list[str], list[str], bool]:
    fail_reasons: list[str] = []
    warning_reasons: list[str] = []

    if not has_complete_xyzw_columns:
        fail_reasons.append("Incomplete XYZW column group")

    if inf_row_count > 0:
        fail_reasons.append(f"Infinite quaternion components in {inf_row_count} row(s)")

    if zero_norm_count > 0:
        fail_reasons.append(f"Zero-norm quaternions: {zero_norm_count}")

    if near_zero_norm_count > 0:
        fail_reasons.append(f"Near-zero-norm quaternions: {near_zero_norm_count}")

    if complete_xyzw_percent < thresholds.min_complete_xyzw_percent:
        fail_reasons.append(
            f"Complete XYZW rows {complete_xyzw_percent:.4f}% "
            f"< {thresholds.min_complete_xyzw_percent}%"
        )

    if longest_invalid_gap_length > thresholds.max_fail_gap_frames:
        fail_reasons.append(
            f"Longest invalid gap {longest_invalid_gap_length} frames "
            f"> {thresholds.max_fail_gap_frames}"
        )

    if fail_reasons:
        return "fail", fail_reasons, warning_reasons, False

    if max_abs_norm_error is not None:
        if max_abs_norm_error > thresholds.warning_max_abs_norm_error:
            fail_reasons.append(
                f"Max abs norm error {max_abs_norm_error:.6g} "
                f"> {thresholds.warning_max_abs_norm_error}"
            )
            return "fail", fail_reasons, warning_reasons, False
        if max_abs_norm_error > thresholds.pass_max_abs_norm_error:
            warning_reasons.append(
                f"Max abs norm error {max_abs_norm_error:.6g} "
                f"> {thresholds.pass_max_abs_norm_error} "
                f"and <= {thresholds.warning_max_abs_norm_error}"
            )

    if 0 < longest_invalid_gap_length <= thresholds.max_warning_gap_frames:
        warning_reasons.append(
            f"Invalid gap length {longest_invalid_gap_length} frame(s) "
            f"(1–{thresholds.max_warning_gap_frames})"
        )

    if invalid_row_count > 0 and not warning_reasons:
        warning_reasons.append(f"Isolated invalid quaternion row(s): {invalid_row_count}")

    if warning_reasons:
        return "warning", fail_reasons, warning_reasons, True

    return "pass", fail_reasons, warning_reasons, True


def evaluate_bone_quaternion_qc(
    *,
    bone_name: str,
    x: pd.Series,
    y: pd.Series,
    z: pd.Series,
    w: pd.Series,
    has_complete_xyzw_columns: bool,
    frame_series: pd.Series | None,
    thresholds: QuaternionQCThresholds | None = None,
) -> BoneQuaternionQCResult:
    """Evaluate numeric quaternion QC for one bone rotation group."""
    thresholds = thresholds or QuaternionQCThresholds()
    components = pd.concat([x, y, z, w], axis=1)
    components.columns = list(MOTIVE_COMPONENT_ORDER)
    total_frames = len(components)

    missing_counts = {
        label: int(components[label].isna().sum()) for label in MOTIVE_COMPONENT_ORDER
    }
    finite_mask = components.apply(np.isfinite).all(axis=1)
    finite_row_count = int(finite_mask.sum())
    non_finite_row_count = int((~finite_mask).sum())
    inf_row_count = int(components.apply(np.isinf).any(axis=1).sum())
    complete_xyzw_row_count = finite_row_count
    complete_xyzw_percent = (
        100.0 * complete_xyzw_row_count / total_frames if total_frames else 0.0
    )

    norms = _compute_norms(components.loc[finite_mask]) if finite_row_count else np.array([])
    zero_norm_count = int(np.sum(norms == 0.0)) if norms.size else 0
    near_zero_norm_count = (
        int(np.sum((norms > 0.0) & (norms < thresholds.near_zero_norm_threshold)))
        if norms.size
        else 0
    )

    if norms.size:
        norm_errors = np.abs(norms - thresholds.expected_unit_norm)
        max_abs_norm_error = float(np.max(norm_errors))
        outside = norm_errors > thresholds.pass_max_abs_norm_error
        norm_outside_tolerance_count = int(outside.sum())
        norm_outside_tolerance_percent = 100.0 * norm_outside_tolerance_count / norms.size
        min_norm = float(np.min(norms))
        max_norm = float(np.max(norms))
        mean_norm = float(np.mean(norms))
        median_norm = float(np.median(norms))
        std_norm = float(np.std(norms))
    else:
        max_abs_norm_error = None
        norm_outside_tolerance_count = 0
        norm_outside_tolerance_percent = 0.0
        min_norm = max_norm = mean_norm = median_norm = std_norm = None

    invalid_mask = np.zeros(total_frames, dtype=bool)
    if total_frames:
        row_finite = components.apply(np.isfinite, axis=1).all(axis=1).to_numpy()
        row_complete = components.notna().all(axis=1).to_numpy()
        invalid_mask = ~row_complete | ~row_finite
        if finite_row_count:
            full_norms = np.full(total_frames, np.nan)
            valid_rows = components.loc[row_complete & row_finite]
            full_norms[row_complete & row_finite] = _compute_norms(valid_rows)
            zero_or_near = (full_norms == 0.0) | (
                (full_norms > 0.0) & (full_norms < thresholds.near_zero_norm_threshold)
            )
            invalid_mask |= zero_or_near

    invalid_row_count = int(invalid_mask.sum())
    invalid_gaps = find_contiguous_invalid_gaps(
        invalid_mask, bone_name=bone_name, frame_series=frame_series
    )
    longest_invalid_gap_length = max((gap.gap_length_frames for gap in invalid_gaps), default=0)

    first_invalid_row_index = None
    last_invalid_row_index = None
    first_invalid_frame = None
    last_invalid_frame = None
    if invalid_row_count:
        invalid_indices = np.flatnonzero(invalid_mask)
        first_invalid_row_index = int(invalid_indices[0])
        last_invalid_row_index = int(invalid_indices[-1])
        if frame_series is not None:
            first_val = frame_series.iloc[first_invalid_row_index]
            last_val = frame_series.iloc[last_invalid_row_index]
            if pd.notna(first_val):
                first_invalid_frame = int(first_val)
            if pd.notna(last_val):
                last_invalid_frame = int(last_val)

    qc_status, fail_reasons, warning_reasons, stage05_may_proceed = _determine_qc_status(
        thresholds=thresholds,
        has_complete_xyzw_columns=has_complete_xyzw_columns,
        complete_xyzw_percent=complete_xyzw_percent,
        inf_row_count=inf_row_count,
        zero_norm_count=zero_norm_count,
        near_zero_norm_count=near_zero_norm_count,
        max_abs_norm_error=max_abs_norm_error,
        longest_invalid_gap_length=longest_invalid_gap_length,
        invalid_row_count=invalid_row_count,
    )

    return BoneQuaternionQCResult(
        source_bone_name=bone_name,
        has_complete_xyzw_columns=has_complete_xyzw_columns,
        total_frames=total_frames,
        finite_row_count=finite_row_count,
        non_finite_row_count=non_finite_row_count,
        missing_x_count=missing_counts["X"],
        missing_y_count=missing_counts["Y"],
        missing_z_count=missing_counts["Z"],
        missing_w_count=missing_counts["W"],
        complete_xyzw_row_count=complete_xyzw_row_count,
        complete_xyzw_percent=round(complete_xyzw_percent, 6),
        min_norm=min_norm,
        max_norm=max_norm,
        mean_norm=mean_norm,
        median_norm=median_norm,
        std_norm=std_norm,
        max_abs_norm_error=max_abs_norm_error,
        norm_outside_tolerance_count=norm_outside_tolerance_count,
        norm_outside_tolerance_percent=round(norm_outside_tolerance_percent, 6),
        zero_norm_count=zero_norm_count,
        near_zero_norm_count=near_zero_norm_count,
        invalid_row_count=invalid_row_count,
        first_invalid_row_index=first_invalid_row_index,
        last_invalid_row_index=last_invalid_row_index,
        first_invalid_frame=first_invalid_frame,
        last_invalid_frame=last_invalid_frame,
        invalid_gap_count=len(invalid_gaps),
        longest_invalid_gap_length=longest_invalid_gap_length,
        qc_status=qc_status,
        qc_fail_reasons=fail_reasons,
        qc_warning_reasons=warning_reasons,
        stage05_may_proceed=stage05_may_proceed,
        invalid_gaps=invalid_gaps,
    )


def evaluate_file_quaternion_qc(
    *,
    input_file: str,
    parsed: ParsedMotiveHeader,
    numeric: pd.DataFrame,
    col_to_pos: dict[int, int],
    groups: dict[str, dict[str, int]],
    frame_series: pd.Series | None,
    thresholds: QuaternionQCThresholds | None = None,
) -> FileQuaternionQCResult:
    """Evaluate quaternion QC for all bone rotation groups in one file."""
    thresholds = thresholds or QuaternionQCThresholds()
    bone_results: list[BoneQuaternionQCResult] = []

    for bone_name, components in sorted(groups.items()):
        complete = set(components) == set(MOTIVE_COMPONENT_ORDER)
        if complete:
            cols = [col_to_pos[components[label]] for label in MOTIVE_COMPONENT_ORDER]
            subset = numeric.iloc[:, cols]
            result = evaluate_bone_quaternion_qc(
                bone_name=bone_name,
                x=subset.iloc[:, 0],
                y=subset.iloc[:, 1],
                z=subset.iloc[:, 2],
                w=subset.iloc[:, 3],
                has_complete_xyzw_columns=True,
                frame_series=frame_series,
                thresholds=thresholds,
            )
        else:
            empty = pd.Series(dtype=float)
            result = evaluate_bone_quaternion_qc(
                bone_name=bone_name,
                x=empty,
                y=empty,
                z=empty,
                w=empty,
                has_complete_xyzw_columns=False,
                frame_series=frame_series,
                thresholds=thresholds,
            )
        bone_results.append(result)

    groups_pass = sum(1 for item in bone_results if item.qc_status == "pass")
    groups_warning = sum(1 for item in bone_results if item.qc_status == "warning")
    groups_fail = sum(1 for item in bone_results if item.qc_status == "fail")
    total_zero_norm = sum(item.zero_norm_count for item in bone_results)
    total_near_zero = sum(item.near_zero_norm_count for item in bone_results)
    total_non_finite = sum(item.non_finite_row_count for item in bone_results)
    norm_errors = [
        item.max_abs_norm_error
        for item in bone_results
        if item.max_abs_norm_error is not None
    ]
    max_abs_norm_error_observed = max(norm_errors) if norm_errors else None
    longest_invalid_gap_observed = max(
        (item.longest_invalid_gap_length for item in bone_results), default=0
    )

    fail_reasons: list[str] = []
    warning_reasons: list[str] = []
    if groups_fail:
        fail_reasons.append(f"{groups_fail} bone group(s) failed quaternion QC")
    if total_zero_norm:
        fail_reasons.append(f"Total zero-norm quaternions: {total_zero_norm}")
    if total_near_zero:
        fail_reasons.append(f"Total near-zero-norm quaternions: {total_near_zero}")
    if total_non_finite:
        warning_reasons.append(f"Total non-finite/missing quaternion rows: {total_non_finite}")
    if longest_invalid_gap_observed > thresholds.max_fail_gap_frames:
        fail_reasons.append(
            f"Longest invalid gap {longest_invalid_gap_observed} frames "
            f"> {thresholds.max_fail_gap_frames}"
        )
    if groups_warning:
        warning_reasons.append(f"{groups_warning} bone group(s) have quaternion QC warnings")

    if groups_fail or fail_reasons:
        file_qc_status: QCStatus = "fail"
        stage05_may_proceed = False
    elif groups_warning or warning_reasons:
        file_qc_status = "warning"
        stage05_may_proceed = True
    else:
        file_qc_status = "pass"
        stage05_may_proceed = True

    return FileQuaternionQCResult(
        input_file=input_file,
        quaternion_group_count=len(bone_results),
        groups_pass=groups_pass,
        groups_warning=groups_warning,
        groups_fail=groups_fail,
        total_zero_norm_count=total_zero_norm,
        total_near_zero_norm_count=total_near_zero,
        total_non_finite_count=total_non_finite,
        max_abs_norm_error_observed=max_abs_norm_error_observed,
        longest_invalid_gap_observed=longest_invalid_gap_observed,
        file_qc_status=file_qc_status,
        stage05_may_proceed=stage05_may_proceed,
        bone_results=bone_results,
        fail_reasons=fail_reasons,
        warning_reasons=warning_reasons,
    )


def bone_qc_to_row(result: BoneQuaternionQCResult) -> dict[str, Any]:
    return {
        "source_bone_name": result.source_bone_name,
        "has_complete_xyzw_columns": result.has_complete_xyzw_columns,
        "total_frames": result.total_frames,
        "finite_row_count": result.finite_row_count,
        "non_finite_row_count": result.non_finite_row_count,
        "missing_x_count": result.missing_x_count,
        "missing_y_count": result.missing_y_count,
        "missing_z_count": result.missing_z_count,
        "missing_w_count": result.missing_w_count,
        "complete_xyzw_row_count": result.complete_xyzw_row_count,
        "complete_xyzw_percent": result.complete_xyzw_percent,
        "min_norm": result.min_norm,
        "max_norm": result.max_norm,
        "mean_norm": result.mean_norm,
        "median_norm": result.median_norm,
        "std_norm": result.std_norm,
        "max_abs_norm_error": result.max_abs_norm_error,
        "norm_outside_tolerance_count": result.norm_outside_tolerance_count,
        "norm_outside_tolerance_percent": result.norm_outside_tolerance_percent,
        "zero_norm_count": result.zero_norm_count,
        "near_zero_norm_count": result.near_zero_norm_count,
        "invalid_row_count": result.invalid_row_count,
        "first_invalid_row_index": result.first_invalid_row_index,
        "last_invalid_row_index": result.last_invalid_row_index,
        "first_invalid_frame": result.first_invalid_frame,
        "last_invalid_frame": result.last_invalid_frame,
        "invalid_gap_count": result.invalid_gap_count,
        "longest_invalid_gap_length": result.longest_invalid_gap_length,
        "qc_status": result.qc_status,
        "qc_fail_reasons": "; ".join(result.qc_fail_reasons),
        "qc_warning_reasons": "; ".join(result.qc_warning_reasons),
        "stage05_may_proceed": result.stage05_may_proceed,
    }


def file_qc_summary_row(result: FileQuaternionQCResult) -> dict[str, Any]:
    return {
        "input_file": result.input_file,
        "quaternion_group_count": result.quaternion_group_count,
        "groups_pass": result.groups_pass,
        "groups_warning": result.groups_warning,
        "groups_fail": result.groups_fail,
        "total_zero_norm_count": result.total_zero_norm_count,
        "total_near_zero_norm_count": result.total_near_zero_norm_count,
        "total_non_finite_count": result.total_non_finite_count,
        "max_abs_norm_error_observed": result.max_abs_norm_error_observed,
        "longest_invalid_gap_observed": result.longest_invalid_gap_observed,
        "file_qc_status": result.file_qc_status,
        "stage05_may_proceed": result.stage05_may_proceed,
        "fail_reasons": "; ".join(result.fail_reasons),
        "warning_reasons": "; ".join(result.warning_reasons),
    }


def invalid_gaps_to_dataframe(bone_results: list[BoneQuaternionQCResult]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for bone in bone_results:
        for gap in bone.invalid_gaps:
            rows.append(
                {
                    "source_bone_name": gap.source_bone_name,
                    "gap_start_row_index": gap.gap_start_row_index,
                    "gap_end_row_index": gap.gap_end_row_index,
                    "gap_length_frames": gap.gap_length_frames,
                    "gap_start_frame": gap.gap_start_frame,
                    "gap_end_frame": gap.gap_end_frame,
                }
            )
    if not rows:
        return pd.DataFrame(
            columns=[
                "source_bone_name",
                "gap_start_row_index",
                "gap_end_row_index",
                "gap_length_frames",
                "gap_start_frame",
                "gap_end_frame",
            ]
        )
    return pd.DataFrame(rows)


def thresholds_from_config(config: dict[str, Any]) -> QuaternionQCThresholds:
    section = config.get("quaternion_qc", {})
    if not isinstance(section, dict):
        return QuaternionQCThresholds()
    return QuaternionQCThresholds(
        expected_unit_norm=float(section.get("expected_unit_norm", 1.0)),
        pass_max_abs_norm_error=float(section.get("pass_max_abs_norm_error", 1e-3)),
        warning_max_abs_norm_error=float(section.get("warning_max_abs_norm_error", 1e-2)),
        near_zero_norm_threshold=float(section.get("near_zero_norm_threshold", 1e-8)),
        min_complete_xyzw_percent=float(section.get("min_complete_xyzw_percent", 99.0)),
        max_warning_gap_frames=int(section.get("max_gap_frames_before_stop", 5)),
        max_fail_gap_frames=int(section.get("max_gap_frames_before_stop", 5)),
    )
