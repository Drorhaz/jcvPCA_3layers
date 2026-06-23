"""Stage 05 — global bone quaternion sign-continuity correction."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from layer2_motive.config import load_config
from layer2_motive.hierarchy import strip_subject_prefix
from layer2_motive.io import stage_output_dir, write_csv, write_parquet, write_text
from layer2_motive.parsing import MOTIVE_COMPONENT_ORDER, ParsedMotiveHeader, bone_rotation_groups
from layer2_motive.quaternion_continuity import (
    BoneSignContinuityResult,
    FileSignContinuityResult,
    SignContinuityThresholds,
    bone_result_to_row,
    build_long_format_table,
    file_summary_row,
    flip_frames_to_dataframe,
    process_bone_sign_continuity,
    thresholds_from_config,
)
from layer2_motive.quaternion_qc import load_bone_rotation_numeric_data
from layer2_motive.reporting import append_assumptions_log, render_stage_report
from layer2_motive.timing import load_frame_time_columns
from layer2_motive.validation import HardStopError

STAGE05_LIMITATIONS = [
    "Stage 05 corrects global quaternion signs only; it does not change represented rotations.",
    "Stage 05 does not interpolate missing data or repair failed Stage 04 QC data.",
    "Stage 05 does not perform anatomical validation.",
    "Stage 05 does not compute relative rotations.",
    "Stage 05 does not convert to rotation vectors or filter.",
    "Stage 05 does not make Layer 3 features ready.",
    "No quaternion normalization is applied; Stage 04-passed norms are preserved.",
]


def _thresholds_from_config_path(config_path: Path | None) -> SignContinuityThresholds:
    return thresholds_from_config(load_config(config_path))


def _assert_stage04_pass(output_dir: Path) -> pd.Series:
    summary_path = output_dir / "04_quaternion_qc" / "quaternion_qc_summary.csv"
    if not summary_path.exists():
        raise HardStopError(
            "Stage 05 blocked: Stage 04 outputs missing; run Stage 04 before Stage 05"
        )
    row = pd.read_csv(summary_path).iloc[0]
    file_qc_status = str(row["file_qc_status"])
    stage05_may_proceed = str(row["stage05_may_proceed"]).lower() == "true"
    if file_qc_status == "fail" or not stage05_may_proceed:
        raise HardStopError(
            "Stage 05 blocked: Stage 04 quaternion QC did not pass "
            f"(file_qc_status={file_qc_status}, stage05_may_proceed={stage05_may_proceed})"
        )
    return row


def _render_assumptions_and_limitations(thresholds: SignContinuityThresholds) -> str:
    lines = [
        "# Stage 05 assumptions and limitations",
        "",
        "## Purpose",
        "",
        "Enforce temporal sign continuity on global Bone Rotation quaternions before "
        "relative-rotation computation.",
        "",
        "## Algorithm",
        "",
        "- Read quaternions in SciPy order `[x, y, z, w]`.",
        "- For each frame `t > 0`, if `dot(q[t], q_corrected[t-1]) < 0`, multiply `q[t]` by -1.",
        "- Continue using corrected quaternions as the reference for subsequent frames.",
        "",
        "## Output format",
        "",
        "Primary deliverable: long-format table in "
        "`global_quaternions_sign_continuous.parquet` with columns:",
        "`frame`, `time`, `source_bone_name`, `canonical_bone_name`, `qx`, `qy`, `qz`, `qw`, "
        "`flip_applied`.",
        "A CSV mirror is also written for inspection; parquet is the primary artifact for "
        "downstream stages due to file size.",
        "",
        "## Validation",
        "",
        f"- Post-correction consecutive dot products must be >= {thresholds.min_consecutive_dot}.",
        "",
        "## Explicit limitations",
        "",
    ]
    lines.extend(f"- {item}" for item in STAGE05_LIMITATIONS)
    lines.append("")
    return "\n".join(lines)


def run_stage_05(
    input_csv: Path,
    output_dir: Path,
    parsed: ParsedMotiveHeader | None = None,
    *,
    config_path: Path | None = None,
    thresholds: SignContinuityThresholds | None = None,
) -> dict[str, pd.DataFrame | FileSignContinuityResult]:
    _assert_stage04_pass(output_dir)

    if parsed is None:
        from layer2_motive.stages.stage00 import run_stage_00

        parsed = run_stage_00(input_csv, output_dir)

    thresholds = thresholds or _thresholds_from_config_path(config_path)
    stage_dir = stage_output_dir(output_dir, "05")
    naming_cfg = load_config(config_path).get("naming", {})
    prefix_rule = str(
        naming_cfg.get("subject_prefix_rule", "colon_suffix")
        if isinstance(naming_cfg, dict)
        else "colon_suffix"
    )

    groups = bone_rotation_groups(parsed.columns)
    numeric, col_to_pos, frame_series = load_bone_rotation_numeric_data(
        input_csv, parsed, groups
    )
    frame_col, time_col = load_frame_time_columns(input_csv, parsed)
    if frame_series is None:
        frame_series = frame_col

    bone_results: list[BoneSignContinuityResult] = []
    bone_quaternions: dict[str, tuple[str, np.ndarray, np.ndarray]] = {}
    fail_reasons: list[str] = []
    warning_reasons: list[str] = []

    for bone_name, components in sorted(groups.items()):
        if set(components) != set(MOTIVE_COMPONENT_ORDER):
            fail_reasons.append(f"{bone_name}: incomplete XYZW columns")
            continue

        prefix = strip_subject_prefix(bone_name, rule=prefix_rule)
        cols = [col_to_pos[components[label]] for label in MOTIVE_COMPONENT_ORDER]
        subset = numeric.iloc[:, cols].to_numpy(dtype=float)
        corrected, flip_mask, bone_result = process_bone_sign_continuity(
            source_bone_name=bone_name,
            canonical_bone_name=prefix.canonical_name,
            quats=subset,
            frame_series=frame_series,
            thresholds=thresholds,
        )
        bone_quaternions[bone_name] = (prefix.canonical_name, corrected, flip_mask)
        bone_results.append(bone_result)
        if not bone_result.post_correction_valid:
            fail_reasons.append(
                f"{bone_name}: min consecutive dot {bone_result.min_consecutive_dot}"
            )

    if fail_reasons and not bone_results:
        raise HardStopError("Stage 05 blocked: no complete bone rotation groups to process")

    total_frames = int(len(frame_col))
    total_sign_flips = sum(item.sign_flip_count for item in bone_results)
    max_sign_flips = max((item.sign_flip_count for item in bone_results), default=0)
    zero_flip_bones = sum(1 for item in bone_results if item.sign_flip_count == 0)
    min_dots = [
        item.min_consecutive_dot
        for item in bone_results
        if item.min_consecutive_dot is not None
    ]
    min_dot_observed = min(min_dots) if min_dots else None
    post_correction_valid = (
        all(item.post_correction_valid for item in bone_results) and not fail_reasons
    )

    if total_sign_flips == 0:
        warning_reasons.append("No sign flips detected in any bone group")

    result = FileSignContinuityResult(
        input_file=str(input_csv),
        quaternion_group_count=len(bone_results),
        total_frames=total_frames,
        total_sign_flips=total_sign_flips,
        max_sign_flips_any_bone=max_sign_flips,
        bones_with_zero_flips=zero_flip_bones,
        min_consecutive_dot_observed=min_dot_observed,
        post_correction_valid=post_correction_valid,
        stage06_may_proceed=post_correction_valid,
        bone_results=bone_results,
        fail_reasons=fail_reasons,
        warning_reasons=warning_reasons,
    )

    long_df = build_long_format_table(
        frame_series=frame_series,
        time_series=time_col,
        bone_quaternions=bone_quaternions,
    )
    by_bone_df = pd.DataFrame([bone_result_to_row(item) for item in bone_results])
    summary_df = pd.DataFrame([file_summary_row(result)])
    flip_frames_df = flip_frames_to_dataframe(bone_results)

    write_csv(summary_df, stage_dir / "sign_continuity_summary.csv")
    write_csv(by_bone_df, stage_dir / "sign_flips_by_bone.csv")
    write_csv(flip_frames_df, stage_dir / "sign_flip_frames.csv")
    write_parquet(long_df, stage_dir / "global_quaternions_sign_continuous.parquet")
    write_csv(long_df, stage_dir / "global_quaternions_sign_continuous.csv")
    assumptions_md = _render_assumptions_and_limitations(thresholds)
    write_text(stage_dir / "assumptions_and_limitations.md", assumptions_md)

    assumptions = [
        "Sign continuity uses consecutive dot-product sign test on SciPy-order quaternions.",
        "Correction multiplies q[t] by -1 when dot(q[t], q_corrected[t-1]) < 0.",
        f"Post-correction validation requires consecutive dot >= {thresholds.min_consecutive_dot}.",
        "Output table uses long format (one row per frame per bone) with flip_applied flag.",
        *STAGE05_LIMITATIONS,
    ]

    detected = [
        f"Quaternion groups processed: {result.quaternion_group_count}",
        f"Total frames processed: {result.total_frames}",
        f"Total sign flips: {result.total_sign_flips}",
        f"Max sign flips (any bone): {result.max_sign_flips_any_bone}",
        f"Bones with zero flips: {result.bones_with_zero_flips}",
        f"Min consecutive dot observed: {result.min_consecutive_dot_observed}",
        f"Post-correction valid: {result.post_correction_valid}",
        f"Stage 06 may proceed: {result.stage06_may_proceed}",
    ]

    outputs = [
        str(stage_dir / "report.md"),
        str(stage_dir / "sign_continuity_summary.csv"),
        str(stage_dir / "sign_flips_by_bone.csv"),
        str(stage_dir / "sign_flip_frames.csv"),
        str(stage_dir / "global_quaternions_sign_continuous.parquet"),
        str(stage_dir / "global_quaternions_sign_continuous.csv"),
        str(stage_dir / "assumptions_and_limitations.md"),
    ]

    if result.post_correction_valid:
        validation_status = "PASS — global sign continuity corrected and validated"
    else:
        validation_status = "FAIL — post-correction sign continuity validation failed"

    report = render_stage_report(
        stage_name="Stage 05 — Global quaternion sign-continuity correction",
        input_files=[str(input_csv)],
        detected=detected,
        assumptions=assumptions,
        outputs=outputs,
        warnings=warning_reasons,
        errors=fail_reasons,
        validation_status=validation_status,
        next_action=(
            "Review sign-continuity summary and flip reports. Continue to Stage 06 only if "
            "post_correction_valid is true and stage06_may_proceed is true."
        ),
    )
    write_text(stage_dir / "report.md", report)
    append_assumptions_log(output_dir, assumptions)

    if not result.post_correction_valid:
        raise HardStopError(
            "Stage 05 sign-continuity validation failed: " + "; ".join(result.fail_reasons)
        )

    return {
        "summary": summary_df,
        "by_bone": by_bone_df,
        "flip_frames": flip_frames_df,
        "global_quaternions": long_df,
        "validation_result": result,
    }
