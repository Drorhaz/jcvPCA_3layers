"""Stage 07 — relative quaternion to rotation-vector log-map conversion and diagnostics."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from layer2_motive.io import stage_output_dir, write_csv, write_parquet, write_text
from layer2_motive.qc_propagation import (
    COMPACT_SIGNAL_COLUMNS,
    build_qc_artifacts_for_run,
    rebuild_layer2_qc_manifests,
)
from layer2_motive.relative_rotation import load_stage01_joint_maps
from layer2_motive.reporting import append_assumptions_log, render_stage_report
from layer2_motive.rotvec import (
    FileRotVecResult,
    RotVecThresholds,
    diagnostics_to_branch_cut_row,
    diagnostics_to_jump_row,
    diagnostics_to_summary_row,
    file_summary_row,
    load_stage06_relative_quaternions,
    load_thresholds,
    process_file_rotvecs,
)
from layer2_motive.validation import HardStopError

STAGE07_LIMITATIONS = [
    "Stage 07 uses the log-map / rotation-vector representation (SciPy Rotation.as_rotvec).",
    "Stage 07 performs branch-cut and frame-to-frame jump diagnostics only.",
    "Stage 07 does not filter.",
    "Stage 07 does not finalize analysis features.",
    "Stage 07 does not resolve skeleton-version mismatch.",
    "Stage 07 does not make Layer 3 ready.",
    "Core and excluded link diagnostics are interpreted separately.",
    "Jump/branch-cut failures on core links are flagged for localized Stage 08 masking.",
    "Branch-cut/jump diagnostics are required before Stage 08 filtering.",
    "Provisional joint selection from Stage 01 / pre–Stage 07 gate is preserved but not frozen.",
]

LOG_MAP_DOC = (
    "Rotation vector conversion: "
    "scipy.spatial.transform.Rotation.from_quat([qx, qy, qz, qw]).as_rotvec()"
)


def _assert_stage06_pass(output_dir: Path) -> pd.Series:
    summary_path = output_dir / "06_relative_quaternions" / "relative_quaternion_summary.csv"
    if not summary_path.exists():
        raise HardStopError(
            "Stage 07 blocked: Stage 06 outputs missing; run Stage 06 before Stage 07"
        )
    row = pd.read_csv(summary_path).iloc[0]
    stage07_may_proceed = str(row["stage07_may_proceed"]).lower() == "true"
    if not stage07_may_proceed:
        raise HardStopError(
            "Stage 07 blocked: Stage 06 relative quaternion validation did not pass "
            f"(stage07_may_proceed={stage07_may_proceed})"
        )
    return row


def _render_assumptions_and_limitations(thresholds: RotVecThresholds) -> str:
    lines = [
        "# Stage 07 assumptions and limitations",
        "",
        "## Purpose",
        "",
        "Convert Stage 06 sign-continuous relative quaternions to rotation vectors via the "
        "log-map and diagnose branch-cut / frame-to-frame jump risks before filtering.",
        "",
        "## Conversion",
        "",
        f"- {LOG_MAP_DOC}",
        "- Output components: `rx`, `ry`, `rz`, `rotvec_norm`",
        "- Compact QC flags propagated into `relative_rotation_vectors.parquet`; "
        "full diagnostics remain in stage reports and `rotvec_summary_by_link.csv`.",
        "",
        "## Diagnostic thresholds (from config)",
        "",
        f"- Near-π count statistic: rotvec_norm ≥ {thresholds.near_pi_threshold_rad:.6g} rad",
        (
            f"- Branch-cut warning: rotvec_norm > {thresholds.branch_cut_warning_rad:.6g} rad "
            f"({thresholds.near_pi_warning_fraction} × π)"
        ),
        f"- Branch-cut fail: rotvec_norm ≥ {thresholds.branch_cut_fail_rad:.6g} rad",
        f"- Jump warning: frame-to-frame rotvec jump > {thresholds.jump_warning_rad} rad",
        f"- Jump fail: frame-to-frame rotvec jump > {thresholds.jump_fail_rad} rad",
        "",
        "## Link groups",
        "",
        "- **core_candidate:** trusted diagnostic group; jump/branch-cut failures are "
        "reported and masked locally in Stage 08 (non-finite rows still block).",
        "- **review_provisional:** trunk/spine/root/manual-review links; reported separately.",
        "- **excluded:** distal finger/toe links; warnings documented but non-blocking.",
        "",
        "## Explicit limitations",
        "",
    ]
    lines.extend(f"- {item}" for item in STAGE07_LIMITATIONS)
    lines.append("")
    return "\n".join(lines)


def _group_summary_lines(
    items: list,
    *,
    title: str,
) -> list[str]:
    lines = [f"### {title}", ""]
    if not items:
        lines.append("- None.")
        lines.append("")
        return lines
    fails = sum(
        1
        for item in items
        if item.branch_cut_status.value == "fail"
        or item.jump_status.value == "fail"
        or item.non_finite_rotvec_rows > 0
    )
    warnings = sum(
        1
        for item in items
        if item.branch_cut_status.value == "warning" or item.jump_status.value == "warning"
    )
    max_norm = max((item.max_rotvec_norm for item in items), default=0.0)
    max_jump = max((item.max_frame_to_frame_jump for item in items), default=0.0)
    lines.extend(
        [
            f"- Links: **{len(items)}**",
            f"- Warnings: **{warnings}**",
            f"- Failures: **{fails}**",
            f"- Max rotvec norm: **{max_norm:.6g} rad**",
            f"- Max frame-to-frame jump: **{max_jump:.6g} rad**",
            "",
        ]
    )
    for item in sorted(items, key=lambda x: x.joint_id):
        if (
            item.branch_cut_status.value != "pass"
            or item.jump_status.value != "pass"
            or item.near_pi_count > 0
            or item.large_jump_count > 0
        ):
            lines.append(
                f"- `{item.joint_id}` {item.parent_bone}→{item.child_bone}: "
                f"branch_cut={item.branch_cut_status.value}, jump={item.jump_status.value}, "
                f"max_norm={item.max_rotvec_norm:.4g}, "
                f"max_jump={item.max_frame_to_frame_jump:.4g}, "
                f"near_pi={item.near_pi_count}, large_jumps={item.large_jump_count}"
            )
    if len(lines) == 3:
        lines.append("- All links pass branch-cut and jump diagnostics.")
        lines.append("")
    else:
        lines.append("")
    return lines


def run_stage_07(
    input_csv: Path,
    output_dir: Path,
    *,
    config_path: Path | None = None,
    rotvec_thresholds: RotVecThresholds | None = None,
) -> dict[str, pd.DataFrame | FileRotVecResult]:
    _assert_stage06_pass(output_dir)

    rotvec_thresholds = rotvec_thresholds or load_thresholds(config_path)

    stage06_dir = output_dir / "06_relative_quaternions"
    stage01_dir = output_dir / "01_joint_mapping"
    stage_dir = stage_output_dir(output_dir, "07")

    relative_quats, input_format = load_stage06_relative_quaternions(stage06_dir)
    candidate_joints, _selected_joints = load_stage01_joint_maps(stage01_dir)

    input_file = str(input_csv)
    file_result, rotvec_table = process_file_rotvecs(
        input_file=input_file,
        relative_quats=relative_quats,
        candidate_joints=candidate_joints,
        thresholds=rotvec_thresholds,
    )
    file_result.input_format_note = (
        f"Loaded Stage 06 relative quaternions from {input_format}"
        + ("; parquet is primary deliverable" if input_format == "parquet" else " (CSV fallback)")
    )

    compact_table, link_manifest_df, session_manifest_row = build_qc_artifacts_for_run(
        input_csv=input_csv,
        output_dir=output_dir,
        rotvec_table=rotvec_table,
        file_result=file_result,
        candidate_joints=candidate_joints,
        thresholds=rotvec_thresholds,
    )

    summary_df = pd.DataFrame(
        [diagnostics_to_summary_row(item) for item in file_result.link_diagnostics]
    )
    branch_df = pd.DataFrame(
        [diagnostics_to_branch_cut_row(item) for item in file_result.link_diagnostics]
    )
    jump_df = pd.DataFrame([diagnostics_to_jump_row(item) for item in file_result.link_diagnostics])
    file_summary_df = pd.DataFrame([file_summary_row(file_result)])

    write_parquet(compact_table, stage_dir / "relative_rotation_vectors.parquet")
    write_csv(compact_table, stage_dir / "relative_rotation_vectors.csv")
    write_csv(link_manifest_df, stage_dir / "qc_link_manifest.csv")
    write_csv(pd.DataFrame([session_manifest_row]), stage_dir / "qc_session_manifest.csv")
    write_csv(summary_df, stage_dir / "rotvec_summary_by_link.csv")
    write_csv(branch_df, stage_dir / "branch_cut_report.csv")
    write_csv(jump_df, stage_dir / "rotvec_jump_report.csv")
    write_csv(file_summary_df, stage_dir / "rotvec_file_summary.csv")

    assumptions_md = _render_assumptions_and_limitations(rotvec_thresholds)
    write_text(stage_dir / "assumptions_and_limitations.md", assumptions_md)

    core_items = [item for item in file_result.link_diagnostics if item.core_candidate]
    review_items = [
        item for item in file_result.link_diagnostics if item.link_group == "review_provisional"
    ]
    excluded_items = [item for item in file_result.link_diagnostics if item.excluded_candidate]

    assumptions = [
        LOG_MAP_DOC,
        f"Near-π statistic threshold: {rotvec_thresholds.near_pi_threshold_rad:.6g} rad",
        (
            f"Branch-cut warning/fail: > {rotvec_thresholds.branch_cut_warning_rad:.6g} / "
            f"≥ {rotvec_thresholds.branch_cut_fail_rad:.6g} rad"
        ),
        (
            f"Jump warning/fail: > {rotvec_thresholds.jump_warning_rad} / "
            f"> {rotvec_thresholds.jump_fail_rad} rad"
        ),
        file_result.input_format_note,
        *STAGE07_LIMITATIONS,
    ]

    detected = [
        f"Stage 06 input format: {file_result.input_format_note}",
        f"Links processed: {file_result.links_processed}",
        f"Core / review / excluded links: {file_result.core_links_processed}/"
        f"{file_result.review_links_processed}/{file_result.excluded_links_processed}",
        f"Max rotvec norm (core / all): {file_result.max_rotvec_norm_core:.6g} / "
        f"{file_result.max_rotvec_norm_all:.6g} rad",
        f"Max frame-to-frame jump (core / all): {file_result.max_jump_core:.6g} / "
        f"{file_result.max_jump_all:.6g} rad",
        f"Core warnings/failures: {file_result.core_warnings}/{file_result.core_failures}",
        f"Review warnings/failures: {file_result.review_warnings}/{file_result.review_failures}",
        f"Excluded warnings/failures: {file_result.excluded_warnings}/"
        f"{file_result.excluded_failures}",
        f"Compact signal columns: {len(COMPACT_SIGNAL_COLUMNS)}",
        f"Stage 08 may proceed: {file_result.stage08_may_proceed}",
    ]

    outputs = [
        str(stage_dir / "report.md"),
        str(stage_dir / "relative_rotation_vectors.parquet"),
        str(stage_dir / "relative_rotation_vectors.csv"),
        str(stage_dir / "qc_link_manifest.csv"),
        str(stage_dir / "qc_session_manifest.csv"),
        str(stage_dir / "rotvec_summary_by_link.csv"),
        str(stage_dir / "branch_cut_report.csv"),
        str(stage_dir / "rotvec_jump_report.csv"),
        str(stage_dir / "assumptions_and_limitations.md"),
    ]

    if file_result.stage08_may_proceed:
        if file_result.core_failures > 0:
            validation_status = (
                "PASS WITH REVIEW — rotation vectors computed; jump/branch-cut diagnostics "
                "flagged for localized Stage 08 masking (see branch_cut_report and "
                "rotvec_jump_report)"
            )
        else:
            validation_status = (
                "PASS — rotation vectors computed; core link branch-cut and jump diagnostics OK"
            )
    elif file_result.fail_reasons:
        validation_status = (
            "FAIL — core link rotation-vector data integrity failed (non-finite rows; "
            "see branch_cut_report and rotvec_jump_report)"
        )
    else:
        validation_status = "WARNING — review diagnostics before Stage 08"

    report = render_stage_report(
        stage_name="Stage 07 — Rotation-vector log-map conversion and diagnostics",
        input_files=[str(input_csv), str(stage06_dir / "relative_quaternions.parquet")],
        detected=detected,
        assumptions=assumptions,
        outputs=outputs,
        warnings=file_result.warning_reasons,
        errors=file_result.fail_reasons,
        validation_status=validation_status,
        next_action=(
            "Review rotvec_summary_by_link.csv, branch_cut_report.csv, and rotvec_jump_report.csv. "
            "Core and excluded diagnostics are summarized separately. "
            "Continue to Stage 08 filtering only if stage08_may_proceed is true and human review "
            "accepts diagnostics. Stage 07 does not filter or finalize analysis features."
        ),
    )

    extra_lines = [
        "",
        "## Diagnostic summaries by link group",
        "",
        * _group_summary_lines(core_items, title="Core candidate links"),
        * _group_summary_lines(review_items, title="Review / provisional trunk-root links"),
        * _group_summary_lines(excluded_items, title="Excluded distal / finger / toe links"),
        "## Stage 07 scope reminder",
        "",
        "- Stage 07 uses the log-map / rotation-vector representation.",
        "- Stage 07 does not filter, finalize analysis features, "
        "resolve skeleton-version mismatch, or make Layer 3 ready.",
        "- Branch-cut/jump diagnostics are required before filtering.",
        "",
    ]
    write_text(stage_dir / "report.md", report + "\n".join(extra_lines))
    append_assumptions_log(output_dir, assumptions)

    rebuild_layer2_qc_manifests(output_dir.parent)

    if not file_result.stage08_may_proceed:
        blocking = [
            r
            for r in file_result.fail_reasons
            if "non-finite rotation-vector rows" in r
        ]
        if blocking:
            raise HardStopError(
                "Stage 07 rotation-vector diagnostics failed for core candidate links: "
                + "; ".join(blocking or file_result.fail_reasons or ["see report for details"])
            )

    return {
        "summary": summary_df,
        "branch_cut": branch_df,
        "jump": jump_df,
        "file_summary": file_summary_df,
        "relative_rotation_vectors": compact_table,
        "link_manifest": link_manifest_df,
        "session_manifest": pd.DataFrame([session_manifest_row]),
        "validation_result": file_result,
    }
