"""Frame and time column validation helpers (Stage 03)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from layer2_motive.metadata import MotiveMetadata
from layer2_motive.parsing import FrameTimeDetection, ParsedMotiveHeader
from layer2_motive.validation import HardStopError


@dataclass(frozen=True)
class TimingThresholds:
    """Conservative provisional thresholds for Stage 03 timing validation."""

    metadata_rate_tolerance_pct: float = 0.5
    max_dt_median_multiplier: float = 1.5
    min_positive_dt_median_multiplier: float = 0.5


@dataclass
class FrameTimingMetrics:
    total_rows: int = 0
    frame_column_present: bool = False
    frame_unparseable_count: int = 0
    first_frame: int | None = None
    last_frame: int | None = None
    expected_frame_count: int | None = None
    observed_unique_frame_count: int = 0
    missing_frame_count: int = 0
    duplicate_frame_count: int = 0
    non_monotonic_frame_count: int = 0
    frame_gaps: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class TimeTimingMetrics:
    time_column_present: bool = False
    time_unparseable_count: int = 0
    first_time: float | None = None
    last_time: float | None = None
    duration_seconds: float | None = None
    median_dt: float | None = None
    mean_dt: float | None = None
    min_dt: float | None = None
    max_dt: float | None = None
    std_dt: float | None = None
    inferred_sampling_rate_hz: float | None = None
    metadata_sampling_rate_hz: float | None = None
    rate_abs_diff_hz: float | None = None
    rate_pct_diff: float | None = None
    non_positive_dt_count: int = 0
    unusually_large_dt_count: int = 0
    unusually_small_dt_count: int = 0
    time_step_rows: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class FrameTimeValidationResult:
    frame: FrameTimingMetrics
    time: TimeTimingMetrics
    timing_status: str
    fail_reasons: list[str] = field(default_factory=list)
    warning_reasons: list[str] = field(default_factory=list)
    stage04_may_proceed: bool = False


def parse_metadata_sampling_rate_hz(metadata: MotiveMetadata | None) -> float | None:
    """Parse metadata export/capture frame rate to Hz when available."""
    if metadata is None:
        return None
    for raw in (metadata.export_frame_rate, metadata.capture_frame_rate):
        if raw is None or str(raw).strip() == "":
            continue
        try:
            value = float(str(raw).strip())
        except ValueError:
            continue
        if value > 0:
            return value
    return None


def load_frame_time_columns(
    csv_path: Path,
    parsed: ParsedMotiveHeader,
) -> tuple[pd.Series, pd.Series]:
    """Load Frame and Time columns from the Motive data block."""
    if parsed.data_start_line_number is None:
        raise HardStopError("Cannot run Stage 03: data start row unknown")

    frame_idx = parsed.frame_time.frame_column_index
    time_idx = parsed.frame_time.time_column_index
    if frame_idx is None and time_idx is None:
        raise HardStopError("Cannot run Stage 03: Frame and Time columns not detected")

    usecols = sorted({idx for idx in (frame_idx, time_idx) if idx is not None})
    data = pd.read_csv(
        csv_path,
        skiprows=parsed.data_start_line_number - 1,
        header=None,
        usecols=usecols,
        dtype=str,
        low_memory=False,
    )
    col_pos = {col_idx: pos for pos, col_idx in enumerate(usecols)}

    if frame_idx is not None:
        frame_raw = data.iloc[:, col_pos[frame_idx]]
    else:
        frame_raw = pd.Series([pd.NA] * len(data), dtype="object")

    if time_idx is not None:
        time_raw = data.iloc[:, col_pos[time_idx]]
    else:
        time_raw = pd.Series([pd.NA] * len(data), dtype="object")

    return frame_raw, time_raw


def _analyze_frames(frames: pd.Series, *, column_present: bool) -> FrameTimingMetrics:
    metrics = FrameTimingMetrics(
        total_rows=len(frames),
        frame_column_present=column_present,
    )
    if not column_present:
        metrics.frame_unparseable_count = len(frames)
        return metrics

    numeric = pd.to_numeric(frames, errors="coerce")
    metrics.frame_unparseable_count = int(numeric.isna().sum())
    valid = numeric.dropna()
    if valid.empty:
        return metrics

    int_frames = valid.astype(np.int64)
    metrics.first_frame = int(int_frames.iloc[0])
    metrics.last_frame = int(int_frames.iloc[-1])
    metrics.observed_unique_frame_count = int(int_frames.nunique())

    diffs = int_frames.diff()
    non_monotonic_mask = diffs <= 0
    metrics.non_monotonic_frame_count = int(non_monotonic_mask.iloc[1:].sum())

    value_counts = int_frames.value_counts()
    metrics.duplicate_frame_count = int((value_counts - 1).clip(lower=0).sum())

    if metrics.first_frame is not None and metrics.last_frame is not None:
        expected = set(range(metrics.first_frame, metrics.last_frame + 1))
        observed = set(int_frames.astype(int).tolist())
        missing = sorted(expected - observed)
        metrics.expected_frame_count = metrics.last_frame - metrics.first_frame + 1
        metrics.missing_frame_count = len(missing)

        if missing:
            gap_start = missing[0]
            prev = gap_start
            for frame_id in missing[1:] + [None]:
                if frame_id is not None and frame_id == prev + 1:
                    prev = frame_id
                    continue
                metrics.frame_gaps.append(
                    {
                        "gap_start_frame": gap_start,
                        "gap_end_frame": prev,
                        "missing_frames_in_gap": prev - gap_start + 1,
                        "after_frame": gap_start - 1,
                        "before_frame": (frame_id if frame_id is not None else prev + 1),
                    }
                )
                if frame_id is not None:
                    gap_start = frame_id
                    prev = frame_id

    return metrics


def _analyze_time(
    times: pd.Series,
    *,
    column_present: bool,
    metadata_rate_hz: float | None,
    thresholds: TimingThresholds,
) -> TimeTimingMetrics:
    metrics = TimeTimingMetrics(time_column_present=column_present)
    if not column_present:
        metrics.time_unparseable_count = len(times)
        return metrics

    numeric = pd.to_numeric(times, errors="coerce")
    metrics.time_unparseable_count = int(numeric.isna().sum())
    valid = numeric.dropna()
    if valid.empty:
        return metrics

    metrics.first_time = float(valid.iloc[0])
    metrics.last_time = float(valid.iloc[-1])
    metrics.duration_seconds = metrics.last_time - metrics.first_time

    dt = valid.diff().iloc[1:]
    if dt.empty:
        return metrics

    metrics.min_dt = float(dt.min())
    metrics.max_dt = float(dt.max())
    metrics.mean_dt = float(dt.mean())
    metrics.median_dt = float(dt.median())
    metrics.std_dt = float(dt.std(ddof=0))

    positive_dt = dt[dt > 0]
    if not positive_dt.empty and metrics.median_dt and metrics.median_dt > 0:
        metrics.inferred_sampling_rate_hz = 1.0 / metrics.median_dt

    metrics.metadata_sampling_rate_hz = metadata_rate_hz
    if metrics.inferred_sampling_rate_hz is not None and metadata_rate_hz is not None:
        metrics.rate_abs_diff_hz = abs(metrics.inferred_sampling_rate_hz - metadata_rate_hz)
        metrics.rate_pct_diff = (
            100.0 * metrics.rate_abs_diff_hz / metadata_rate_hz if metadata_rate_hz > 0 else None
        )

    metrics.non_positive_dt_count = int((dt <= 0).sum())

    if metrics.median_dt is not None and metrics.median_dt > 0:
        large_threshold = thresholds.max_dt_median_multiplier * metrics.median_dt
        small_threshold = thresholds.min_positive_dt_median_multiplier * metrics.median_dt
        large_mask = dt > large_threshold
        small_mask = (dt > 0) & (dt < small_threshold)
        metrics.unusually_large_dt_count = int(large_mask.sum())
        metrics.unusually_small_dt_count = int(small_mask.sum())

        for idx in dt.index:
            row_idx = int(idx)
            dt_value = float(dt.loc[idx])
            issue = ""
            if dt_value <= 0:
                issue = "non_positive_dt"
            elif dt_value > large_threshold:
                issue = "unusually_large_dt"
            elif 0 < dt_value < small_threshold:
                issue = "unusually_small_dt"
            if issue:
                metrics.time_step_rows.append(
                    {
                        "row_index": row_idx,
                        "previous_time": float(valid.loc[row_idx - 1]),
                        "current_time": float(valid.loc[row_idx]),
                        "dt_seconds": dt_value,
                        "issue_type": issue,
                    }
                )

    return metrics


def evaluate_timing_status(
    frame_metrics: FrameTimingMetrics,
    time_metrics: TimeTimingMetrics,
    *,
    thresholds: TimingThresholds,
) -> FrameTimeValidationResult:
    """Apply conservative pass/warning/fail rules and assemble the result."""
    fail_reasons: list[str] = []
    warning_reasons: list[str] = []

    if not frame_metrics.frame_column_present:
        fail_reasons.append("Frame column missing or not detected")
    elif frame_metrics.frame_unparseable_count > 0:
        fail_reasons.append(
            f"Frame column has {frame_metrics.frame_unparseable_count} unparseable row(s)"
        )

    if not time_metrics.time_column_present:
        fail_reasons.append("Time column missing or not detected")
    elif time_metrics.time_unparseable_count > 0:
        fail_reasons.append(
            f"Time column has {time_metrics.time_unparseable_count} unparseable row(s)"
        )

    if frame_metrics.non_monotonic_frame_count > 0:
        fail_reasons.append(
            f"Frame index is not strictly monotonic increasing "
            f"({frame_metrics.non_monotonic_frame_count} non-monotonic transition(s))"
        )

    if time_metrics.non_positive_dt_count > 0:
        fail_reasons.append(
            f"Time has {time_metrics.non_positive_dt_count} non-positive dt interval(s)"
        )

    if frame_metrics.missing_frame_count > 0:
        warning_reasons.append(
            f"Isolated or contiguous frame gaps detected "
            f"({frame_metrics.missing_frame_count} missing frame index/indices)"
        )

    if frame_metrics.duplicate_frame_count > 0:
        warning_reasons.append(
            f"Duplicate frame indices detected ({frame_metrics.duplicate_frame_count} extra row(s))"
        )

    if (
        time_metrics.rate_pct_diff is not None
        and time_metrics.rate_pct_diff > thresholds.metadata_rate_tolerance_pct
    ):
        warning_reasons.append(
            f"Inferred sampling rate differs from metadata by "
            f"{time_metrics.rate_pct_diff:.4f}% "
            f"(threshold {thresholds.metadata_rate_tolerance_pct}%)"
        )

    if time_metrics.unusually_large_dt_count > 0:
        warning_reasons.append(
            f"{time_metrics.unusually_large_dt_count} unusually large dt interval(s) "
            f"(>{thresholds.max_dt_median_multiplier}× median dt)"
        )

    if time_metrics.unusually_small_dt_count > 0:
        warning_reasons.append(
            f"{time_metrics.unusually_small_dt_count} unusually small positive dt interval(s) "
            f"(<{thresholds.min_positive_dt_median_multiplier}× median dt)"
        )

    if fail_reasons:
        status = "fail"
    elif warning_reasons:
        status = "warning"
    else:
        status = "pass"

    return FrameTimeValidationResult(
        frame=frame_metrics,
        time=time_metrics,
        timing_status=status,
        fail_reasons=fail_reasons,
        warning_reasons=warning_reasons,
        stage04_may_proceed=status != "fail",
    )


def validate_frame_time(
    parsed: ParsedMotiveHeader,
    frame_series: pd.Series,
    time_series: pd.Series,
    *,
    thresholds: TimingThresholds | None = None,
) -> FrameTimeValidationResult:
    """Run full Stage 03 frame/time structural validation."""
    thresholds = thresholds or TimingThresholds()
    frame_present = parsed.frame_time.frame_column_index is not None
    time_present = parsed.frame_time.time_column_index is not None
    metadata_rate = parse_metadata_sampling_rate_hz(parsed.metadata)

    frame_metrics = _analyze_frames(frame_series, column_present=frame_present)
    time_metrics = _analyze_time(
        time_series,
        column_present=time_present,
        metadata_rate_hz=metadata_rate,
        thresholds=thresholds,
    )
    return evaluate_timing_status(frame_metrics, time_metrics, thresholds=thresholds)


def frame_time_summary_row(
    *,
    input_file: str,
    frame_time: FrameTimeDetection,
    result: FrameTimeValidationResult,
) -> dict[str, Any]:
    """Build one-row summary dict for ``frame_time_summary.csv``."""
    frame = result.frame
    time = result.time
    return {
        "input_file": input_file,
        "frame_column_index": frame_time.frame_column_index,
        "frame_column_label": frame_time.frame_label,
        "time_column_index": frame_time.time_column_index,
        "time_column_label": frame_time.time_label,
        "total_rows": frame.total_rows,
        "first_frame": frame.first_frame,
        "last_frame": frame.last_frame,
        "expected_frame_count": frame.expected_frame_count,
        "observed_unique_frame_count": frame.observed_unique_frame_count,
        "missing_frame_count": frame.missing_frame_count,
        "duplicate_frame_count": frame.duplicate_frame_count,
        "non_monotonic_frame_count": frame.non_monotonic_frame_count,
        "frame_unparseable_count": frame.frame_unparseable_count,
        "first_time": time.first_time,
        "last_time": time.last_time,
        "duration_seconds": time.duration_seconds,
        "median_dt": time.median_dt,
        "mean_dt": time.mean_dt,
        "min_dt": time.min_dt,
        "max_dt": time.max_dt,
        "std_dt": time.std_dt,
        "inferred_sampling_rate_hz": time.inferred_sampling_rate_hz,
        "metadata_sampling_rate_hz": time.metadata_sampling_rate_hz,
        "rate_abs_diff_hz": time.rate_abs_diff_hz,
        "rate_pct_diff": time.rate_pct_diff,
        "non_positive_dt_count": time.non_positive_dt_count,
        "unusually_large_dt_count": time.unusually_large_dt_count,
        "unusually_small_dt_count": time.unusually_small_dt_count,
        "time_unparseable_count": time.time_unparseable_count,
        "timing_status": result.timing_status,
        "stage04_may_proceed": result.stage04_may_proceed,
    }
