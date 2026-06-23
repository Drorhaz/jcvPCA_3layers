"""Stage 03 — frame and time structural validation."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from layer2_motive.config import load_config
from layer2_motive.io import stage_output_dir, write_csv, write_text
from layer2_motive.parsing import ParsedMotiveHeader
from layer2_motive.reporting import append_assumptions_log, render_stage_report
from layer2_motive.timing import (
    FrameTimeValidationResult,
    TimingThresholds,
    frame_time_summary_row,
    load_frame_time_columns,
    validate_frame_time,
)
from layer2_motive.validation import HardStopError

STAGE03_LIMITATIONS = [
    "This stage validates Frame and Time column structure only.",
    "No quaternion norm QC, gap repair, sign continuity, relative rotations, "
    "rotation vectors, filtering, or Layer 3 processing is performed.",
    "Missing frame indices are reported but not interpolated or repaired.",
    "Sampling rate is inferred from median positive dt; irregular intervals are flagged only.",
    "Joint sets are not frozen; this stage does not validate bone or joint selection.",
]


def _thresholds_from_config(config_path: Path | None) -> TimingThresholds:
    config = load_config(config_path)
    section = config.get("frame_time_validation", {})
    if not isinstance(section, dict):
        return TimingThresholds()
    return TimingThresholds(
        metadata_rate_tolerance_pct=float(
            section.get("metadata_rate_tolerance_pct", TimingThresholds.metadata_rate_tolerance_pct)
        ),
        max_dt_median_multiplier=float(
            section.get("max_dt_median_multiplier", TimingThresholds.max_dt_median_multiplier)
        ),
        min_positive_dt_median_multiplier=float(
            section.get(
                "min_positive_dt_median_multiplier",
                TimingThresholds.min_positive_dt_median_multiplier,
            )
        ),
    )


def _render_assumptions_and_limitations(thresholds: TimingThresholds) -> str:
    lines = [
        "# Stage 03 assumptions and limitations",
        "",
        "## Purpose",
        "",
        "Structural timing validation of Frame and Time columns before any "
        "time-dependent quaternion processing.",
        "",
        "## Thresholds (provisional, conservative)",
        "",
        "- Fail if Frame or Time column is missing or has unparseable rows.",
        "- Fail if Frame is not strictly monotonic increasing.",
        "- Fail if Time has non-positive dt intervals.",
        f"- Warning if inferred sampling rate differs from metadata by more than "
        f"{thresholds.metadata_rate_tolerance_pct}%.",
        "- Warning if frame index gaps exist (missing indices between first and last frame).",
        f"- Warning if max dt > {thresholds.max_dt_median_multiplier} × median dt.",
        (
            f"- Warning if min positive dt < {thresholds.min_positive_dt_median_multiplier} "
            "× median dt."
        ),
        "- Warning if duplicate frame indices are present.",
        "",
        "## Explicit limitations",
        "",
    ]
    lines.extend(f"- {item}" for item in STAGE03_LIMITATIONS)
    lines.append("")
    return "\n".join(lines)


def _empty_gap_report() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "gap_start_frame",
            "gap_end_frame",
            "missing_frames_in_gap",
            "after_frame",
            "before_frame",
        ]
    )


def _empty_time_step_report() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "row_index",
            "previous_time",
            "current_time",
            "dt_seconds",
            "issue_type",
        ]
    )


def run_stage_03(
    input_csv: Path,
    output_dir: Path,
    parsed: ParsedMotiveHeader | None = None,
    *,
    config_path: Path | None = None,
    thresholds: TimingThresholds | None = None,
) -> dict[str, pd.DataFrame | FrameTimeValidationResult]:
    if parsed is None:
        from layer2_motive.stages.stage00 import run_stage_00

        parsed = run_stage_00(input_csv, output_dir)

    thresholds = thresholds or _thresholds_from_config(config_path)
    stage_dir = stage_output_dir(output_dir, "03")

    frame_series, time_series = load_frame_time_columns(input_csv, parsed)
    result = validate_frame_time(parsed, frame_series, time_series, thresholds=thresholds)

    summary = frame_time_summary_row(
        input_file=str(input_csv),
        frame_time=parsed.frame_time,
        result=result,
    )
    summary_df = pd.DataFrame([summary])
    gap_df = (
        pd.DataFrame(result.frame.frame_gaps)
        if result.frame.frame_gaps
        else _empty_gap_report()
    )
    time_step_df = (
        pd.DataFrame(result.time.time_step_rows)
        if result.time.time_step_rows
        else _empty_time_step_report()
    )

    write_csv(summary_df, stage_dir / "frame_time_summary.csv")
    write_csv(gap_df, stage_dir / "frame_gap_report.csv")
    write_csv(time_step_df, stage_dir / "time_step_report.csv")
    assumptions_md = _render_assumptions_and_limitations(thresholds)
    write_text(stage_dir / "assumptions_and_limitations.md", assumptions_md)

    warnings = list(result.warning_reasons)
    errors = list(result.fail_reasons)

    assumptions = [
        (
            "Frame and Time columns are loaded using Stage 00 header detection "
            "and flat column indices."
        ),
        "Sampling rate is inferred as 1 / median positive dt from the Time column.",
        "Metadata sampling rate uses Export Frame Rate, falling back to Capture Frame Rate.",
        f"Provisional thresholds: metadata tolerance {thresholds.metadata_rate_tolerance_pct}%, "
        f"large dt > {thresholds.max_dt_median_multiplier}× median, "
        f"small dt < {thresholds.min_positive_dt_median_multiplier}× median.",
        *STAGE03_LIMITATIONS,
    ]

    detected = [
        f"Frame column: index={parsed.frame_time.frame_column_index}, "
        f"label={parsed.frame_time.frame_label!r}",
        f"Time column: index={parsed.frame_time.time_column_index}, "
        f"label={parsed.frame_time.time_label!r}",
        f"Total rows: {result.frame.total_rows}",
        f"First frame: {result.frame.first_frame}",
        f"Last frame: {result.frame.last_frame}",
        f"Expected frame count (index span): {result.frame.expected_frame_count}",
        f"Observed unique frame count: {result.frame.observed_unique_frame_count}",
        f"Missing frame count: {result.frame.missing_frame_count}",
        f"Duplicate frame count: {result.frame.duplicate_frame_count}",
        f"Non-monotonic frame transitions: {result.frame.non_monotonic_frame_count}",
        f"First time (s): {result.time.first_time}",
        f"Last time (s): {result.time.last_time}",
        f"Duration (s): {result.time.duration_seconds}",
        f"Median dt (s): {result.time.median_dt}",
        f"Inferred sampling rate (Hz): {result.time.inferred_sampling_rate_hz}",
        f"Metadata sampling rate (Hz): {result.time.metadata_sampling_rate_hz}",
        f"Rate difference (%): {result.time.rate_pct_diff}",
        f"Non-positive dt intervals: {result.time.non_positive_dt_count}",
        f"Unusually large dt intervals: {result.time.unusually_large_dt_count}",
        f"Unusually small dt intervals: {result.time.unusually_small_dt_count}",
        f"timing_status: {result.timing_status}",
        f"Stage 04 may proceed: {result.stage04_may_proceed}",
    ]

    outputs = [
        str(stage_dir / "report.md"),
        str(stage_dir / "frame_time_summary.csv"),
        str(stage_dir / "frame_gap_report.csv"),
        str(stage_dir / "time_step_report.csv"),
        str(stage_dir / "assumptions_and_limitations.md"),
    ]

    if result.timing_status == "pass":
        validation_status = "PASS — frame/time structure validated"
    elif result.timing_status == "warning":
        validation_status = "WARNING — frame/time issues detected; review before Stage 04"
    else:
        validation_status = "FAIL — frame/time structure invalid; Stage 04 blocked"

    report = render_stage_report(
        stage_name="Stage 03 — Frame and time validation",
        input_files=[str(input_csv)],
        detected=detected,
        assumptions=assumptions,
        outputs=outputs,
        warnings=warnings,
        errors=errors,
        validation_status=validation_status,
        next_action=(
            "Review frame/time summary, gap report, and time-step report. "
            "Continue to Stage 04 only if timing_status is pass or warning is accepted "
            "and stage04_may_proceed is true."
        ),
    )
    write_text(stage_dir / "report.md", report)
    append_assumptions_log(output_dir, assumptions)

    if result.timing_status == "fail":
        raise HardStopError(
            "Stage 03 frame/time validation failed: " + "; ".join(result.fail_reasons)
        )

    return {
        "summary": summary_df,
        "frame_gap_report": gap_df,
        "time_step_report": time_step_df,
        "validation_result": result,
    }
