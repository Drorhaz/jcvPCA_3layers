"""Stage 08 — Butterworth filtering with jump-context masking (V1, no interpolation)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from layer2_motive.filtering import (
    FileFilterResult,
    load_filtering_config,
    load_stage07_rotation_vectors,
    process_file_filtering,
)
from layer2_motive.io import stage_output_dir, write_csv, write_parquet, write_text
from layer2_motive.qc_propagation import load_stage_qc_context
from layer2_motive.reporting import append_assumptions_log, render_stage_report
from layer2_motive.rotvec import load_thresholds
from layer2_motive.validation import HardStopError

STAGE08_LIMITATIONS = [
    "Stage 08 V1 does not interpolate or repair Stage 07 jump frames.",
    "Stage 07 jump and branch-cut failures use localized context masking, not whole-link blocks.",
    "Native filtered values may exist inside QC context windows but are not analysis-clean.",
    "Analysis-clean columns are NaN/masked in jump and branch-cut context windows.",
    "Final inclusion/exclusion remains deferred to post–Layer 2 / pre–Layer 3 feature selection.",
    "Stage 08 does not implement Layer 3.",
    "Stage 08 does not overwrite Stage 07 outputs or modify Stage 07 thresholds.",
    "Pipeline-integrity failures (quaternion/sign/reconstruction) still block entire links.",
]


def _assert_stage07_available(output_dir: Path) -> None:
    stage07_dir = output_dir / "07_rotation_vectors"
    parquet = stage07_dir / "relative_rotation_vectors.parquet"
    csv = stage07_dir / "relative_rotation_vectors.csv"
    if not parquet.exists() and not csv.exists():
        raise HardStopError(
            "Stage 08 blocked: Stage 07 rotation vectors missing; run Stage 07 before Stage 08"
        )


def _render_assumptions_and_limitations(
    *,
    cutoff_hz: float,
    filter_order: int,
    sampling_rate_hz: float,
    jump_context_window_frames: int,
    branch_cut_warning_rad: float,
    jump_warning_rad: float,
) -> str:
    lines = [
        "# Stage 08 assumptions and limitations",
        "",
        "## Purpose",
        "",
        "Apply zero-phase Butterworth low-pass filtering to Stage 07 rotation-vector components "
        "while preserving QC lineage and producing an analysis-clean mask.",
        "",
        "## Filtering parameters",
        "",
        "- Filter type: Butterworth (SOS), scipy.signal.sosfiltfilt",
        f"- Cutoff: {cutoff_hz} Hz",
        f"- Order: {filter_order}",
        f"- Sampling rate: {sampling_rate_hz} Hz (from Stage 03 session manifest)",
        "- Cutoff validation: cutoff < 0.45 × sampling_rate",
        f"- QC context window: ±{jump_context_window_frames} frames (jumps and branch-cut events)",
        "",
        "## Stage 08 QC policy (V1)",
        "",
        "| Stage 07 outcome | Stage 08 policy | Stage 08 masking |",
        "|---|---|---|",
        "| Jump warning or fail | `allow_filter_with_warning` | Jump event ± context → "
        "`stage07_jump_context` |",
        "| Branch-cut warning or fail | `allow_filter_with_warning` | "
        f"`rotvec_norm` > {branch_cut_warning_rad:.6g} rad ± context → "
        "`stage07_branch_cut_context` |",
        "| Quaternion / sign / reconstruction fail | `block_filter` | Whole link |",
        "",
        "## Mask reasons",
        "",
        f"- `stage07_jump_context`: within ±{jump_context_window_frames} frames of a Stage 07 jump "
        f"event (frame-to-frame magnitude > {jump_warning_rad} rad; warning and fail levels).",
        f"- `stage07_branch_cut_context`: within ±{jump_context_window_frames} frames of a frame "
        f"where `rotvec_norm` exceeds the branch-cut warning threshold "
        f"({branch_cut_warning_rad:.6g} rad). Jump context takes priority when both apply.",
        "- `blocked_needs_review`: whole-link block from pipeline-integrity QC only.",
        "",
        "## Jump / branch-cut context rules",
        "",
        "- **No interpolation** of masked rows.",
        "- Jump events: row-level `stage07_jump_magnitude_rad` on frame-to-frame transitions.",
        "- Branch-cut events: row-level `rotvec_norm` above branch-cut warning threshold.",
        "- Rows inside a context window: `stage08_analysis_eligible = false`; analysis-clean "
        "columns set to NaN.",
        "- Native filtered columns may retain values inside context windows.",
        "- Stage 07 link-level `fail` labels are preserved for reporting; they do not imply "
        "whole-link analysis exclusion in Stage 08.",
        "",
        "## Output columns",
        "",
        "- Native archive: `rx_filtered_native`, `ry_filtered_native`, `rz_filtered_native`, "
        "`rotvec_norm_filtered_native`",
        "- Analysis-clean: `rx_filtered_analysis`, `ry_filtered_analysis`, `rz_filtered_analysis`, "
        "`rotvec_norm_filtered_analysis`",
        "- Raw preserved: `rx_raw`, `ry_raw`, `rz_raw`, `rotvec_norm_raw`",
        "- Jump QC: `stage08_stage07_jump_frame`, `stage08_within_jump_context_window`, "
        "`stage08_distance_to_nearest_stage07_jump_frame`",
        "- Branch-cut QC: `stage08_branch_cut_event_frame`, "
        "`stage08_within_branch_cut_context_window`, "
        "`stage08_distance_to_nearest_branch_cut_frame`",
        "",
        "## Explicit limitations",
        "",
    ]
    lines.extend(f"- {item}" for item in STAGE08_LIMITATIONS)
    lines.append("")
    return "\n".join(lines)


def run_stage_08(
    input_csv: Path,
    output_dir: Path,
    *,
    config_path: Path | None = None,
    cutoff_hz: float | None = None,
    filter_order: int | None = None,
) -> dict[str, pd.DataFrame | FileFilterResult]:
    _assert_stage07_available(output_dir)

    stage07_dir = output_dir / "07_rotation_vectors"
    stage_dir = stage_output_dir(output_dir, "08")

    filtering_config = load_filtering_config(config_path)
    if cutoff_hz is not None or filter_order is not None:
        from dataclasses import replace

        filtering_config = replace(
            filtering_config,
            cutoff_hz=cutoff_hz if cutoff_hz is not None else filtering_config.cutoff_hz,
            filter_order=filter_order
            if filter_order is not None
            else filtering_config.filter_order,
        )

    rotvec_thresholds = load_thresholds(config_path)
    qc_context = load_stage_qc_context(output_dir)
    sampling_rate_hz = qc_context.sampling_rate_hz

    stage07_table = load_stage07_rotation_vectors(stage07_dir)
    (
        filtered_table,
        summary_df,
        jump_df,
        branch_cut_df,
        diagnostics_df,
        file_result,
    ) = process_file_filtering(
        stage07_table=stage07_table,
        sampling_rate_hz=sampling_rate_hz,
        filtering_config=filtering_config,
        rotvec_thresholds=rotvec_thresholds,
        config_path=config_path,
    )

    write_parquet(filtered_table, stage_dir / "filtered_relative_rotation_vectors.parquet")
    write_csv(filtered_table, stage_dir / "filtered_relative_rotation_vectors.csv")
    write_csv(summary_df, stage_dir / "filtering_summary_by_link.csv")
    write_csv(jump_df, stage_dir / "stage08_jump_context_report.csv")
    write_csv(branch_cut_df, stage_dir / "stage08_branch_cut_context_report.csv")
    write_csv(diagnostics_df, stage_dir / "filter_diagnostics.csv")

    assumptions_md = _render_assumptions_and_limitations(
        cutoff_hz=file_result.cutoff_hz,
        filter_order=int(file_result.filter_order),
        sampling_rate_hz=file_result.sampling_rate_hz,
        jump_context_window_frames=file_result.jump_context_window_frames,
        branch_cut_warning_rad=rotvec_thresholds.branch_cut_warning_rad,
        jump_warning_rad=rotvec_thresholds.jump_warning_rad,
    )
    write_text(stage_dir / "assumptions_and_limitations.md", assumptions_md)

    assumptions = [
        (
            f"Butterworth sosfiltfilt: cutoff={file_result.cutoff_hz} Hz, "
            f"order={int(file_result.filter_order)}"
        ),
        f"Sampling rate from Stage 03: {file_result.sampling_rate_hz} Hz",
        f"QC context window: ±{file_result.jump_context_window_frames} frames "
        "(jump and branch-cut events)",
        "Stage 08 V1 does not interpolate Stage 07 jump frames.",
        *STAGE08_LIMITATIONS,
    ]

    detected = [
        f"Links processed: {file_result.links_processed}",
        f"Links pass / QC-context masked / excluded / blocked / review: "
        f"{file_result.links_pass} / {file_result.links_with_jump_context} / "
        f"{file_result.links_excluded} / {file_result.links_blocked} / "
        f"{file_result.links_review}",
        f"Total Stage 07 jump event frames: {file_result.total_jump_event_frames}",
        f"Total jump-context frames (may overlap): {file_result.total_jump_context_frames}",
        f"Total branch-cut event frames: {file_result.total_branch_cut_event_frames}",
        f"Total branch-cut context frames (may overlap): "
        f"{file_result.total_branch_cut_context_frames}",
        f"Total analysis-eligible frames: {file_result.total_analysis_eligible_frames}",
        f"Interpolation applied: {file_result.interpolation_applied}",
        "Native filtered columns retain values where filtering succeeded.",
        "Analysis-clean columns are NaN outside eligibility "
        "(QC context, excluded, blocked, review).",
    ]

    outputs = [
        str(stage_dir / "report.md"),
        str(stage_dir / "filtered_relative_rotation_vectors.parquet"),
        str(stage_dir / "filtered_relative_rotation_vectors.csv"),
        str(stage_dir / "filtering_summary_by_link.csv"),
        str(stage_dir / "stage08_jump_context_report.csv"),
        str(stage_dir / "stage08_branch_cut_context_report.csv"),
        str(stage_dir / "filter_diagnostics.csv"),
        str(stage_dir / "assumptions_and_limitations.md"),
    ]

    if file_result.links_pass == file_result.links_processed:
        validation_status = (
            "PASS — filtered rotation vectors produced; localized QC masking applied where needed"
        )
    elif file_result.links_blocked > 0:
        validation_status = (
            "WARNING — filtering completed; some links blocked from analysis-clean core "
            "(see filtering_summary_by_link.csv)"
        )
    else:
        validation_status = "PASS WITH REVIEW — filtering completed; review link summaries"

    report = render_stage_report(
        stage_name="Stage 08 — Filtered relative rotation vectors (V1, no interpolation)",
        input_files=[
            str(input_csv),
            str(stage07_dir / "relative_rotation_vectors.parquet"),
            str(output_dir / "03_frame_time_validation" / "frame_time_summary.csv"),
        ],
        detected=detected,
        assumptions=assumptions,
        outputs=outputs,
        warnings=[],
        errors=[],
        validation_status=validation_status,
        next_action=(
            "Review filtering_summary_by_link.csv, stage08_jump_context_report.csv, and "
            "stage08_branch_cut_context_report.csv. Use analysis-clean columns for downstream "
            "feature work; native columns are archival. Final Layer 2 export/manifest can be "
            "prepared next; Layer 3 remains out of scope."
        ),
    )

    extra_lines = [
        "",
        "## Stage 08 V1 policy reminder",
        "",
        "- Stage 08 V1 does **not** interpolate or repair Stage 07 jump frames.",
        "- Jump and branch-cut Stage 07 failures are **localized** (event ± context window).",
        "- Native filtered values may exist inside QC context windows but are "
        "**not** analysis-clean.",
        "- Analysis-clean columns are NaN/masked in jump and branch-cut context windows.",
        "- Whole-link blocks apply only to pipeline-integrity QC (`block_filter`).",
        "- Final inclusion/exclusion remains deferred to post–Layer 2 / "
        "pre–Layer 3 feature selection.",
        "- Stage 08 does not implement Layer 3.",
        "",
        "## QC context summary",
        "",
        f"- Jump event frames (total across links): **{file_result.total_jump_event_frames}**",
        f"- Jump-context frames (total, overlapping): **{file_result.total_jump_context_frames}**",
        f"- Branch-cut event frames (total): **{file_result.total_branch_cut_event_frames}**",
        f"- Branch-cut context frames (total, overlapping): "
        f"**{file_result.total_branch_cut_context_frames}**",
        f"- Links with QC context masking: **{file_result.links_with_jump_context}**",
        "",
    ]
    write_text(stage_dir / "report.md", report + "\n".join(extra_lines))
    append_assumptions_log(output_dir, assumptions)

    return {
        "filtered_table": filtered_table,
        "summary": summary_df,
        "jump_context": jump_df,
        "branch_cut_context": branch_cut_df,
        "diagnostics": diagnostics_df,
        "file_result": file_result,
    }
