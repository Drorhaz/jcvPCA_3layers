"""Stage 04 — quaternion norm / missingness / validity QC (reporting only)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from layer2_motive.config import load_config
from layer2_motive.io import stage_output_dir, write_csv, write_text
from layer2_motive.parsing import MOTIVE_COMPONENT_ORDER, ParsedMotiveHeader, bone_rotation_groups
from layer2_motive.quaternion_qc import (
    FileQuaternionQCResult,
    QuaternionQCThresholds,
    bone_qc_to_row,
    evaluate_file_quaternion_qc,
    file_qc_summary_row,
    invalid_gaps_to_dataframe,
    load_bone_rotation_numeric_data,
    thresholds_from_config,
)
from layer2_motive.reporting import append_assumptions_log, render_stage_report
from layer2_motive.validation import HardStopError

STAGE04_LIMITATIONS = [
    "Stage 04 validates numeric quaternion quality only.",
    "Stage 04 does not validate anatomical correctness.",
    "Stage 04 does not perform sign-continuity.",
    "Stage 04 does not compute relative rotations.",
    "Stage 04 does not filter.",
    "Stage 04 does not make Layer 3 features ready.",
    "No quaternion normalization, interpolation, or silent repair is performed in Stage 04.",
    "v5 spec Stage 04 also describes normalization/mitigation outputs; this milestone "
    "implements QC/reporting only per approved plan.",
]


def _thresholds_from_config_path(config_path: Path | None) -> QuaternionQCThresholds:
    config = load_config(config_path)
    return thresholds_from_config(config)


def _render_assumptions_and_limitations(thresholds: QuaternionQCThresholds) -> str:
    lines = [
        "# Stage 04 assumptions and limitations",
        "",
        "## Purpose",
        "",
        "Numeric quaternion QC on global Bone Rotation XYZW groups before any "
        "sign-continuity correction or relative-rotation computation.",
        "",
        "## Thresholds (provisional, conservative)",
        "",
        f"- Expected unit norm: {thresholds.expected_unit_norm}",
        f"- Pass if max abs norm error <= {thresholds.pass_max_abs_norm_error} and no "
        "missing/non-finite/zero-norm rows.",
        f"- Warning if max abs norm error > {thresholds.pass_max_abs_norm_error} and "
        f"<= {thresholds.warning_max_abs_norm_error}, or isolated invalid gaps of "
        f"1–{thresholds.max_warning_gap_frames} frames.",
        f"- Fail if any zero-norm or near-zero-norm quaternion "
        f"(near-zero threshold {thresholds.near_zero_norm_threshold}).",
        "- Fail if any infinite quaternion component exists.",
        f"- Fail if any contiguous invalid gap exceeds {thresholds.max_fail_gap_frames} frames.",
        f"- Fail if complete XYZW percent < {thresholds.min_complete_xyzw_percent}%.",
        "",
        "## Spec note",
        "",
        "The v5 Stage 04 spec also lists normalization, mitigation logs, and optional "
        "interpolation. This implementation follows the approved Stage 04 QC-only scope: "
        "detect/report only; no repair.",
        "",
        "## Explicit limitations",
        "",
    ]
    lines.extend(f"- {item}" for item in STAGE04_LIMITATIONS)
    lines.append("")
    return "\n".join(lines)


def run_stage_04(
    input_csv: Path,
    output_dir: Path,
    parsed: ParsedMotiveHeader | None = None,
    *,
    config_path: Path | None = None,
    thresholds: QuaternionQCThresholds | None = None,
) -> dict[str, pd.DataFrame | FileQuaternionQCResult]:
    if parsed is None:
        from layer2_motive.stages.stage00 import run_stage_00

        parsed = run_stage_00(input_csv, output_dir)

    thresholds = thresholds or _thresholds_from_config_path(config_path)
    stage_dir = stage_output_dir(output_dir, "04")
    groups = bone_rotation_groups(parsed.columns)
    numeric, col_to_pos, frame_series = load_bone_rotation_numeric_data(
        input_csv, parsed, groups
    )

    result = evaluate_file_quaternion_qc(
        input_file=str(input_csv),
        parsed=parsed,
        numeric=numeric,
        col_to_pos=col_to_pos,
        groups=groups,
        frame_series=frame_series,
        thresholds=thresholds,
    )

    by_bone_df = pd.DataFrame([bone_qc_to_row(item) for item in result.bone_results])
    summary_df = pd.DataFrame([file_qc_summary_row(result)])
    gap_df = invalid_gaps_to_dataframe(result.bone_results)

    write_csv(summary_df, stage_dir / "quaternion_qc_summary.csv")
    write_csv(by_bone_df, stage_dir / "quaternion_qc_by_bone.csv")
    write_csv(gap_df, stage_dir / "quaternion_invalid_gap_report.csv")
    assumptions_md = _render_assumptions_and_limitations(thresholds)
    write_text(stage_dir / "assumptions_and_limitations.md", assumptions_md)

    warnings = list(result.warning_reasons)
    errors = list(result.fail_reasons)
    for bone in result.bone_results:
        if bone.qc_status == "warning":
            warnings.extend(
                f"{bone.source_bone_name}: {reason}" for reason in bone.qc_warning_reasons
            )
        if bone.qc_status == "fail":
            errors.extend(f"{bone.source_bone_name}: {reason}" for reason in bone.qc_fail_reasons)

    assumptions = [
        "Bone Rotation groups are loaded using Stage 00 column detection (X/Y/Z/W per bone).",
        "Quaternion norms are computed on complete finite XYZW rows only; "
        "no normalization applied.",
        f"Provisional thresholds: pass norm error <= {thresholds.pass_max_abs_norm_error}, "
        f"warning <= {thresholds.warning_max_abs_norm_error}, "
        f"near-zero norm < {thresholds.near_zero_norm_threshold}.",
        *STAGE04_LIMITATIONS,
    ]

    detected = [
        f"Quaternion groups checked: {result.quaternion_group_count}",
        f"Groups pass/warning/fail: {result.groups_pass}/{result.groups_warning}/"
        f"{result.groups_fail}",
        f"Total zero-norm quaternions: {result.total_zero_norm_count}",
        f"Total near-zero-norm quaternions: {result.total_near_zero_norm_count}",
        f"Total non-finite quaternion rows: {result.total_non_finite_count}",
        f"Max abs norm error observed: {result.max_abs_norm_error_observed}",
        f"Longest invalid gap observed: {result.longest_invalid_gap_observed} frame(s)",
        f"file_qc_status: {result.file_qc_status}",
        f"Stage 05 may proceed: {result.stage05_may_proceed}",
    ]

    outputs = [
        str(stage_dir / "report.md"),
        str(stage_dir / "quaternion_qc_summary.csv"),
        str(stage_dir / "quaternion_qc_by_bone.csv"),
        str(stage_dir / "quaternion_invalid_gap_report.csv"),
        str(stage_dir / "assumptions_and_limitations.md"),
    ]

    if result.file_qc_status == "pass":
        validation_status = "PASS — quaternion numeric QC validated"
    elif result.file_qc_status == "warning":
        validation_status = "WARNING — quaternion QC issues detected; review before Stage 05"
    else:
        validation_status = "FAIL — quaternion QC failed; Stage 05 blocked"

    report = render_stage_report(
        stage_name="Stage 04 — Quaternion norm / missingness / validity QC",
        input_files=[str(input_csv)],
        detected=detected,
        assumptions=assumptions,
        outputs=outputs,
        warnings=warnings,
        errors=errors,
        validation_status=validation_status,
        next_action=(
            "Review quaternion QC summary, per-bone table, and invalid-gap report. "
            "Continue to Stage 05 only if file_qc_status is pass or warning is accepted "
            "and stage05_may_proceed is true."
        ),
    )
    write_text(stage_dir / "report.md", report)
    append_assumptions_log(output_dir, assumptions)

    incomplete_groups = [
        name
        for name, components in groups.items()
        if set(components) != set(MOTIVE_COMPONENT_ORDER)
    ]
    if incomplete_groups and len(incomplete_groups) == len(groups):
        raise HardStopError(
            "Stage 04 blocked: no bone rotation groups have complete X/Y/Z/W columns"
        )

    if result.file_qc_status == "fail":
        raise HardStopError(
            "Stage 04 quaternion QC failed: " + "; ".join(result.fail_reasons)
        )

    return {
        "summary": summary_df,
        "by_bone": by_bone_df,
        "invalid_gap_report": gap_df,
        "validation_result": result,
    }
