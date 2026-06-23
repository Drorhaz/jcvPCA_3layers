"""Stage 06 — parent→child relative quaternion computation and reconstruction validation."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from layer2_motive.config import load_config
from layer2_motive.io import stage_output_dir, write_csv, write_parquet, write_text
from layer2_motive.quaternion_continuity import (
    thresholds_from_config as sign_thresholds_from_config,
)
from layer2_motive.relative_rotation import (
    MULTIPLICATION_ORDER_DOC,
    FileRelativeRotationResult,
    ReconstructionThresholds,
    file_summary_row,
    link_reconstruction_to_row,
    load_stage01_joint_maps,
    load_stage05_global_quaternions,
    process_file_relative_rotations,
    sign_continuity_to_row,
    thresholds_from_config,
)
from layer2_motive.reporting import append_assumptions_log, render_stage_report
from layer2_motive.validation import HardStopError

STAGE06_LIMITATIONS = [
    "Stage 06 computes native relative quaternions from sign-continuous global quaternions.",
    "Stage 06 does not finalize analysis features.",
    "Stage 06 does not resolve skeleton-version mismatch.",
    "Stage 06 does not convert to rotation vectors.",
    "Stage 06 does not filter.",
    "Stage 06 does not make Layer 3 ready.",
    "Provisional joint selection from Stage 01 is preserved but not frozen.",
    "Root-anchor links are labeled and excluded from final-analysis status by default.",
]

STAGE06_RELATIVE_SIGN_CONTINUITY_NOTE = (
    "When raw relative quaternion sequences contain sign discontinuities, Stage 06 applies "
    "the same consecutive dot-product correction as Stage 05 (flip q[t] when "
    "dot(q[t], q[t-1]) < 0) with explicit logging. This is a documented second-pass "
    "sign continuity on relative quaternions, required before Stage 07 log-map."
)


def _thresholds_from_config_path(config_path: Path | None) -> ReconstructionThresholds:
    return thresholds_from_config(load_config(config_path))


def _assert_stage05_pass(output_dir: Path) -> pd.Series:
    summary_path = output_dir / "05_sign_continuity" / "sign_continuity_summary.csv"
    if not summary_path.exists():
        raise HardStopError(
            "Stage 06 blocked: Stage 05 outputs missing; run Stage 05 before Stage 06"
        )
    row = pd.read_csv(summary_path).iloc[0]
    post_correction_valid = str(row["post_correction_valid"]).lower() == "true"
    stage06_may_proceed = str(row["stage06_may_proceed"]).lower() == "true"
    if not post_correction_valid or not stage06_may_proceed:
        raise HardStopError(
            "Stage 06 blocked: Stage 05 sign-continuity did not pass "
            f"(post_correction_valid={post_correction_valid}, "
            f"stage06_may_proceed={stage06_may_proceed})"
        )
    return row


def _render_assumptions_and_limitations(
    reconstruction_thresholds: ReconstructionThresholds,
) -> str:
    lines = [
        "# Stage 06 assumptions and limitations",
        "",
        "## Purpose",
        "",
        "Compute parent→child relative joint quaternions from Stage 05 sign-continuous "
        "global Bone Rotation quaternions and validate reconstruction.",
        "",
        "## Multiplication order (SciPy Rotation)",
        "",
        f"- {MULTIPLICATION_ORDER_DOC}",
        "",
        "## Reconstruction validation thresholds",
        "",
        f"- **Pass:** max angular error ≤ {reconstruction_thresholds.pass_max_error_deg} degrees",
        f"- **Warning:** max angular error > {reconstruction_thresholds.pass_max_error_deg} "
        f"and ≤ {reconstruction_thresholds.warning_max_error_deg} degrees",
        f"- **Fail:** max angular error > "
        f"{reconstruction_thresholds.warning_max_error_deg} degrees",
        "",
        "## Relative quaternion sign continuity",
        "",
        f"- {STAGE06_RELATIVE_SIGN_CONTINUITY_NOTE}",
        "",
        "## Output format",
        "",
        "Primary deliverable: long-format `relative_quaternions.parquet` with columns "
        "`frame`, `time`, joint identifiers, provisional selection metadata, "
        "`qx`, `qy`, `qz`, `qw` (SciPy `[x,y,z,w]` order), and `relative_flip_applied`.",
        "CSV mirror written for inspection; parquet is primary for downstream stages.",
        "",
        "## Explicit limitations",
        "",
    ]
    lines.extend(f"- {item}" for item in STAGE06_LIMITATIONS)
    lines.append("")
    return "\n".join(lines)


def run_stage_06(
    input_csv: Path,
    output_dir: Path,
    *,
    config_path: Path | None = None,
    reconstruction_thresholds: ReconstructionThresholds | None = None,
) -> dict[str, pd.DataFrame | FileRelativeRotationResult]:
    _assert_stage05_pass(output_dir)

    reconstruction_thresholds = reconstruction_thresholds or _thresholds_from_config_path(
        config_path
    )
    config = load_config(config_path)
    sign_thresholds = sign_thresholds_from_config(config)

    stage05_dir = output_dir / "05_sign_continuity"
    stage01_dir = output_dir / "01_joint_mapping"
    stage_dir = stage_output_dir(output_dir, "06")

    global_quats = load_stage05_global_quaternions(stage05_dir)
    candidate_joints, selected_joints = load_stage01_joint_maps(stage01_dir)

    file_result, relative_table = process_file_relative_rotations(
        input_file=str(input_csv),
        global_quats=global_quats,
        candidate_joints=candidate_joints,
        selected_joints=selected_joints,
        reconstruction_thresholds=reconstruction_thresholds,
        sign_thresholds=sign_thresholds,
        apply_relative_sign_correction=True,
    )

    reconstruction_df = pd.DataFrame(
        [link_reconstruction_to_row(item) for item in file_result.link_results]
    )
    sign_df = pd.DataFrame(
        [sign_continuity_to_row(item) for item in file_result.sign_continuity_results]
    )
    missing_df = pd.DataFrame(file_result.missing_links)
    summary_df = pd.DataFrame([file_summary_row(file_result)])

    write_parquet(relative_table, stage_dir / "relative_quaternions.parquet")
    write_csv(relative_table, stage_dir / "relative_quaternions.csv")
    write_csv(summary_df, stage_dir / "relative_quaternion_summary.csv")
    write_csv(reconstruction_df, stage_dir / "reconstruction_validation_by_joint.csv")
    write_csv(sign_df, stage_dir / "relative_sign_continuity_report.csv")
    if not missing_df.empty:
        write_csv(missing_df, stage_dir / "missing_parent_child_links.csv")

    assumptions_md = _render_assumptions_and_limitations(reconstruction_thresholds)
    write_text(stage_dir / "assumptions_and_limitations.md", assumptions_md)

    assumptions = [
        MULTIPLICATION_ORDER_DOC,
        (
            "Reconstruction pass threshold: max error ≤ "
            f"{reconstruction_thresholds.pass_max_error_deg} deg"
        ),
        (
            "Reconstruction warning threshold: max error ≤ "
            f"{reconstruction_thresholds.warning_max_error_deg} deg"
        ),
        STAGE06_RELATIVE_SIGN_CONTINUITY_NOTE,
        "Parent-child links derived from Stage 01 candidate_joint_map (not a fixed joint list).",
        *STAGE06_LIMITATIONS,
    ]

    detected = [
        f"Parent-child links processed: {file_result.parent_child_links_processed}",
        f"Parent-child links missing/skipped: {file_result.parent_child_links_missing}",
        f"Total frames: {file_result.total_frames}",
        f"Global max reconstruction error (deg): {file_result.global_max_reconstruction_error_deg}",
        f"Links pass/warning/fail: {file_result.links_pass}/"
        f"{file_result.links_warning}/{file_result.links_fail}",
        f"Total raw relative sign flips: {file_result.total_relative_sign_flips_raw}",
        (
            "Total relative sign flips after correction: "
            f"{file_result.total_relative_sign_flips_corrected}"
        ),
        f"Relative sign continuity valid: {file_result.relative_sign_continuity_valid}",
        f"Stage 07 may proceed: {file_result.stage07_may_proceed}",
    ]

    outputs = [
        str(stage_dir / "report.md"),
        str(stage_dir / "relative_quaternions.parquet"),
        str(stage_dir / "relative_quaternions.csv"),
        str(stage_dir / "relative_quaternion_summary.csv"),
        str(stage_dir / "reconstruction_validation_by_joint.csv"),
        str(stage_dir / "relative_sign_continuity_report.csv"),
        str(stage_dir / "assumptions_and_limitations.md"),
    ]
    if not missing_df.empty:
        outputs.append(str(stage_dir / "missing_parent_child_links.csv"))

    if file_result.stage07_may_proceed:
        validation_status = (
            "PASS — relative quaternions computed, reconstruction validated, "
            "relative sign continuity OK"
        )
    elif file_result.links_fail > 0 or file_result.fail_reasons:
        validation_status = "FAIL — reconstruction or relative sign-continuity validation failed"
    else:
        validation_status = "WARNING — review reconstruction warnings before Stage 07"

    report = render_stage_report(
        stage_name="Stage 06 — Relative quaternion computation and reconstruction validation",
        input_files=[str(input_csv)],
        detected=detected,
        assumptions=assumptions,
        outputs=outputs,
        warnings=file_result.warning_reasons,
        errors=file_result.fail_reasons,
        validation_status=validation_status,
        next_action=(
            "Review relative quaternion summary and reconstruction validation. "
            "Continue to Stage 07 only if stage07_may_proceed is true. "
            "Stage 06 does not convert to rotation vectors, filter, or finalize features."
        ),
    )
    write_text(stage_dir / "report.md", report)
    append_assumptions_log(output_dir, assumptions)

    if not file_result.stage07_may_proceed:
        raise HardStopError(
            "Stage 06 relative quaternion validation failed: "
            + "; ".join(file_result.fail_reasons or ["see report for details"])
        )

    return {
        "summary": summary_df,
        "reconstruction": reconstruction_df,
        "sign_continuity": sign_df,
        "relative_quaternions": relative_table,
        "missing_links": missing_df,
        "validation_result": file_result,
    }
