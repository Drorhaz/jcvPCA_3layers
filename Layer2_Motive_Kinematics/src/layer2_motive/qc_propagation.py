"""Compact QC propagation from Stages 04–07 into signal parquet and Layer 2 manifests."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from layer2_motive.pre_stage07_gate import (
    MOTIVE_TEMPLATE_BY_SESSION,
    classify_link_for_gate,
    is_finger_child_bone,
    is_toe_child_bone,
)
from layer2_motive.rotvec import (
    DiagnosticStatus,
    FileRotVecResult,
    LinkRotVecDiagnostics,
    RotVecThresholds,
    evaluate_branch_cut_status,
    evaluate_jump_status,
    frame_to_frame_rotvec_jumps,
)

COMPACT_SIGNAL_COLUMNS: tuple[str, ...] = (
    "session_id",
    "run_label",
    "frame",
    "time_sec",
    "link_id",
    "parent_canonical",
    "child_canonical",
    "rx",
    "ry",
    "rz",
    "rotvec_norm",
    "feature_scope",
    "included_in_v0",
    "requires_manual_review",
    "stage04_quaternion_valid",
    "stage05_global_sign_continuity_valid",
    "stage06_relative_reconstruction_valid",
    "stage06_relative_sign_continuity_valid",
    "stage07_branch_cut_status",
    "stage07_jump_status",
    "stage07_jump_from_previous_frame",
    "stage07_jump_magnitude_rad",
    "stage07_row_qc_status",
    "stage07_link_qc_status",
    "stage08_policy",
)

HEAVY_SIGNAL_COLUMNS: frozenset[str] = frozenset(
    {
        "qx",
        "qy",
        "qz",
        "qw",
        "relative_flip_applied",
        "source_parent_bone",
        "source_child_bone",
        "input_file",
        "p95_rotvec_norm",
        "p99_rotvec_norm",
        "near_pi_count",
        "large_jump_count",
        "mean_rotvec_norm",
        "max_rotvec_norm",
        "sign_flip_count",
        "reconstruction_p99_error_deg",
        "terminology_note",
    }
)

LINK_MANIFEST_COLUMNS: tuple[str, ...] = (
    "session_id",
    "run_label",
    "template_name",
    "link_id",
    "parent_canonical",
    "child_canonical",
    "feature_scope",
    "stage04_parent_qc_status",
    "stage04_child_qc_status",
    "stage05_parent_sign_status",
    "stage05_child_sign_status",
    "stage06_reconstruction_status",
    "stage06_max_reconstruction_error_deg",
    "stage06_relative_sign_status",
    "stage07_branch_cut_status",
    "stage07_max_rotvec_norm",
    "stage07_jump_status",
    "stage07_max_jump_rad",
    "stage08_policy",
    "notes",
)

SESSION_MANIFEST_COLUMNS: tuple[str, ...] = (
    "session_id",
    "run_label",
    "skeleton_template",
    "frame_count",
    "sampling_rate_hz",
    "stage03_timing_status",
    "stage04_file_status",
    "stage05_file_status",
    "stage06_file_status",
    "stage07_file_status",
    "stage08_authorization_status",
    "notes",
)

SESSION_ID_RE = re.compile(r"^(671_T\d_P1_R\d)")


def session_id_from_run_label(run_label: str) -> str:
    match = SESSION_ID_RE.match(run_label)
    return match.group(1) if match else run_label


def session_id_from_input_csv(input_csv: Path) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", input_csv.stem)
    safe = re.sub(r"_+", "_", safe).strip("_")
    return session_id_from_run_label(safe or "motive_session")


def template_name_for_session(session_id: str) -> str:
    session = "unknown"
    for token in ("T1", "T2", "T3"):
        if f"_{token}_" in session_id or session_id.endswith(f"_{token}"):
            session = token
            break
    return MOTIVE_TEMPLATE_BY_SESSION.get(session, "unknown")


def feature_scope_from_classification(
    *,
    link_classification: str,
    core_candidate: bool,
    excluded_candidate: bool,
    is_skipped: bool,
    child_bone: str,
    exclusion_reason: str,
) -> str:
    if is_skipped:
        return "skipped"
    if link_classification == "toe" or is_toe_child_bone(child_bone):
        return "excluded_toe"
    if (
        link_classification == "finger"
        or (excluded_candidate and is_finger_child_bone(child_bone))
        or exclusion_reason.startswith("distal_keyword")
    ):
        return "excluded_distal"
    if core_candidate:
        return "core_candidate"
    if link_classification in {"trunk_spine", "other_provisional", "virtual_root_parent_skip"}:
        return "review_provisional"
    if excluded_candidate:
        return "excluded_distal"
    return "review_provisional"


def compute_stage08_policy(
    *,
    feature_scope: str,
    branch_cut_status: str,
    jump_status: str,
    stage06_reconstruction_valid: bool,
    stage06_sign_valid: bool,
    stage04_valid: bool,
    stage05_valid: bool,
    requires_manual_review: bool,
) -> str:
    if feature_scope in {"excluded_distal", "excluded_toe", "skipped"}:
        return "excluded_from_analysis"
    if feature_scope == "review_provisional" or requires_manual_review:
        if branch_cut_status == "fail" or jump_status == "fail":
            return "manual_review_required"
        if branch_cut_status == "warning" or jump_status == "warning":
            return "allow_filter_with_warning"
        return "manual_review_required"
    if not stage04_valid or not stage05_valid or not stage06_reconstruction_valid:
        return "block_filter"
    if not stage06_sign_valid:
        return "block_filter"
    if branch_cut_status in {"fail", "warning"} or jump_status in {"fail", "warning"}:
        return "allow_filter_with_warning"
    return "allow_filter"


def _row_qc_from_frame(
    rotvec_norm: float,
    jump_mag: float,
    thresholds: RotVecThresholds,
) -> str:
    if not np.isfinite(rotvec_norm) or not np.isfinite(jump_mag):
        return DiagnosticStatus.FAIL.value
    branch = evaluate_branch_cut_status(float(rotvec_norm), thresholds)
    if branch == DiagnosticStatus.FAIL:
        return DiagnosticStatus.FAIL.value
    jump = (
        evaluate_jump_status(float(jump_mag), thresholds)
        if jump_mag > 0
        else DiagnosticStatus.PASS
    )
    if jump == DiagnosticStatus.FAIL or branch == DiagnosticStatus.FAIL:
        return DiagnosticStatus.FAIL.value
    if jump == DiagnosticStatus.WARNING or branch == DiagnosticStatus.WARNING:
        return DiagnosticStatus.WARNING.value
    return DiagnosticStatus.PASS


def _link_qc_status(item: LinkRotVecDiagnostics) -> str:
    if item.non_finite_rotvec_rows > 0:
        return DiagnosticStatus.FAIL.value
    if (
        item.branch_cut_status == DiagnosticStatus.FAIL
        or item.jump_status == DiagnosticStatus.FAIL
    ):
        return DiagnosticStatus.FAIL.value
    if (
        item.branch_cut_status == DiagnosticStatus.WARNING
        or item.jump_status == DiagnosticStatus.WARNING
    ):
        return DiagnosticStatus.WARNING.value
    return DiagnosticStatus.PASS.value


@dataclass
class StageQCContext:
    stage04_by_bone: pd.DataFrame
    stage05_by_bone: pd.DataFrame
    stage06_recon_by_link: pd.DataFrame
    stage06_sign_by_link: pd.DataFrame
    stage03_timing_status: str
    stage04_file_status: str
    stage05_file_status: str
    stage06_file_status: str
    sampling_rate_hz: float
    frame_count: int


def _read_csv_or_empty(path: Path, columns: list[str]) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=columns)
    try:
        df = pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame(columns=columns)
    if df.empty:
        return pd.DataFrame(columns=columns)
    return df


def load_stage_qc_context(output_dir: Path) -> StageQCContext:
    stage04_bone = pd.read_csv(output_dir / "04_quaternion_qc" / "quaternion_qc_by_bone.csv")
    stage05_bone = pd.read_csv(output_dir / "05_sign_continuity" / "sign_flips_by_bone.csv")
    stage06_dir = output_dir / "06_relative_quaternions"
    recon = _read_csv_or_empty(
        stage06_dir / "reconstruction_validation_by_joint.csv",
        ["joint_id", "reconstruction_status", "max_error_deg"],
    )
    sign = _read_csv_or_empty(
        stage06_dir / "relative_sign_continuity_report.csv",
        ["joint_id", "post_correction_valid"],
    )
    timing = pd.read_csv(output_dir / "03_frame_time_validation" / "frame_time_summary.csv").iloc[
        0
    ]
    qc_summary = pd.read_csv(
        output_dir / "04_quaternion_qc" / "quaternion_qc_summary.csv"
    ).iloc[0]
    sign_summary = pd.read_csv(
        output_dir / "05_sign_continuity" / "sign_continuity_summary.csv"
    ).iloc[0]
    rel_summary = pd.read_csv(stage06_dir / "relative_quaternion_summary.csv").iloc[0]

    stage06_status = "pass"
    if int(rel_summary.get("links_fail", 0)) > 0:
        stage06_status = "fail"
    elif int(rel_summary.get("links_warning", 0)) > 0:
        stage06_status = "warning"

    return StageQCContext(
        stage04_by_bone=stage04_bone.set_index("source_bone_name", drop=False)
        if not stage04_bone.empty
        else stage04_bone,
        stage05_by_bone=stage05_bone.set_index("source_bone_name", drop=False)
        if not stage05_bone.empty
        else stage05_bone,
        stage06_recon_by_link=recon.set_index("joint_id", drop=False) if not recon.empty else recon,
        stage06_sign_by_link=sign.set_index("joint_id", drop=False) if not sign.empty else sign,
        stage03_timing_status=str(timing["timing_status"]),
        stage04_file_status=str(qc_summary["file_qc_status"]),
        stage05_file_status="pass"
        if str(sign_summary["post_correction_valid"]).lower() == "true"
        else "fail",
        stage06_file_status=stage06_status,
        sampling_rate_hz=float(timing["inferred_sampling_rate_hz"]),
        frame_count=int(timing["observed_unique_frame_count"]),
    )


def _bone_qc_status(context: StageQCContext, source_bone: str) -> str:
    if context.stage04_by_bone.empty or source_bone not in context.stage04_by_bone.index:
        return "missing"
    return str(context.stage04_by_bone.loc[source_bone, "qc_status"])


def _bone_sign_status(context: StageQCContext, source_bone: str) -> str:
    if context.stage05_by_bone.empty or source_bone not in context.stage05_by_bone.index:
        return "missing"
    valid = bool(context.stage05_by_bone.loc[source_bone, "post_correction_valid"])
    return "pass" if valid else "fail"


def _bones_qc_valid(context: StageQCContext, parent_source: str, child_source: str) -> bool:
    return _bone_qc_status(context, parent_source) == "pass" and _bone_qc_status(
        context, child_source
    ) == "pass"


def _bones_sign_valid(context: StageQCContext, parent_source: str, child_source: str) -> bool:
    return _bone_sign_status(context, parent_source) == "pass" and _bone_sign_status(
        context, child_source
    ) == "pass"


@dataclass
class LinkQCRecord:
    link_id: str
    parent_canonical: str
    child_canonical: str
    source_parent_bone: str
    source_child_bone: str
    feature_scope: str
    included_in_v0: bool
    requires_manual_review: bool
    stage04_parent_qc_status: str
    stage04_child_qc_status: str
    stage05_parent_sign_status: str
    stage05_child_sign_status: str
    stage04_quaternion_valid: bool
    stage05_global_sign_continuity_valid: bool
    stage06_reconstruction_status: str
    stage06_max_reconstruction_error_deg: float
    stage06_relative_reconstruction_valid: bool
    stage06_relative_sign_status: str
    stage06_relative_sign_continuity_valid: bool
    stage07_branch_cut_status: str
    stage07_max_rotvec_norm: float
    stage07_jump_status: str
    stage07_max_jump_rad: float
    stage07_link_qc_status: str
    stage08_policy: str
    notes: str


def build_link_qc_record(
    *,
    link_diag: LinkRotVecDiagnostics | None,
    context: StageQCContext,
    candidate_row: pd.Series | None,
    exclusion_reason: str = "",
    is_skipped: bool = False,
    skip_note: str = "",
) -> LinkQCRecord:
    if link_diag is not None:
        joint_id = link_diag.joint_id
        parent = link_diag.parent_bone
        child = link_diag.child_bone
        source_parent = link_diag.source_parent_bone
        source_child = link_diag.source_child_bone
        included = link_diag.included_in_v0
        requires_review = link_diag.requires_manual_review
        classification = classify_link_for_gate(
            parent_bone=parent,
            child_bone=child,
            is_root_anchor_link=False,
            exclusion_reason=exclusion_reason,
        )
        feature_scope = feature_scope_from_classification(
            link_classification=classification.link_classification,
            core_candidate=link_diag.core_candidate,
            excluded_candidate=link_diag.excluded_candidate,
            is_skipped=False,
            child_bone=child,
            exclusion_reason=exclusion_reason,
        )
        branch = link_diag.branch_cut_status.value
        jump = link_diag.jump_status.value
        max_norm = link_diag.max_rotvec_norm
        max_jump = link_diag.max_frame_to_frame_jump
        link_qc = _link_qc_status(link_diag)
    else:
        joint_id = str(candidate_row["joint_id"]) if candidate_row is not None else ""
        parent = str(candidate_row["parent_bone"]) if candidate_row is not None else ""
        child = str(candidate_row["child_bone"]) if candidate_row is not None else ""
        source_parent = (
            str(candidate_row["source_parent_bone"]) if candidate_row is not None else ""
        )
        source_child = str(candidate_row["source_child_bone"]) if candidate_row is not None else ""
        included = (
            bool(candidate_row.get("included_in_v0", False))
            if candidate_row is not None
            else False
        )
        requires_review = (
            bool(candidate_row.get("requires_manual_review", False))
            if candidate_row is not None
            else False
        )
        classification = classify_link_for_gate(
            parent_bone=parent,
            child_bone=child,
            is_root_anchor_link=True,
            exclusion_reason=exclusion_reason or "parent_is_root",
        )
        feature_scope = "skipped" if is_skipped else feature_scope_from_classification(
            link_classification=classification.link_classification,
            core_candidate=False,
            excluded_candidate=classification.excluded_candidate,
            is_skipped=is_skipped,
            child_bone=child,
            exclusion_reason=exclusion_reason,
        )
        branch = jump = link_qc = "skipped"
        max_norm = max_jump = float("nan")

    parent_qc = _bone_qc_status(context, source_parent)
    child_qc = _bone_qc_status(context, source_child)
    parent_sign = _bone_sign_status(context, source_parent)
    child_sign = _bone_sign_status(context, source_child)
    stage04_valid = _bones_qc_valid(context, source_parent, source_child)
    stage05_valid = _bones_sign_valid(context, source_parent, source_child)

    recon_status = "missing"
    recon_max = float("nan")
    sign_status = "missing"
    recon_valid = False
    sign_valid = False
    if (
        not context.stage06_recon_by_link.empty
        and joint_id in context.stage06_recon_by_link.index
    ):
        recon_row = context.stage06_recon_by_link.loc[joint_id]
        recon_status = str(recon_row["reconstruction_status"])
        recon_max = float(recon_row["max_error_deg"])
        recon_valid = recon_status != "fail"
    if (
        not context.stage06_sign_by_link.empty
        and joint_id in context.stage06_sign_by_link.index
    ):
        sign_row = context.stage06_sign_by_link.loc[joint_id]
        sign_valid = bool(sign_row["post_correction_valid"])
        sign_status = "pass" if sign_valid else "fail"

    policy = compute_stage08_policy(
        feature_scope=feature_scope,
        branch_cut_status=branch,
        jump_status=jump,
        stage06_reconstruction_valid=recon_valid,
        stage06_sign_valid=sign_valid,
        stage04_valid=stage04_valid,
        stage05_valid=stage05_valid,
        requires_manual_review=requires_review,
    )

    notes = classification.terminology_note if link_diag is not None else skip_note
    if is_skipped and skip_note:
        notes = skip_note

    return LinkQCRecord(
        link_id=joint_id,
        parent_canonical=parent,
        child_canonical=child,
        source_parent_bone=source_parent,
        source_child_bone=source_child,
        feature_scope=feature_scope,
        included_in_v0=included,
        requires_manual_review=requires_review,
        stage04_parent_qc_status=parent_qc,
        stage04_child_qc_status=child_qc,
        stage05_parent_sign_status=parent_sign,
        stage05_child_sign_status=child_sign,
        stage04_quaternion_valid=stage04_valid,
        stage05_global_sign_continuity_valid=stage05_valid,
        stage06_reconstruction_status=recon_status,
        stage06_max_reconstruction_error_deg=recon_max,
        stage06_relative_reconstruction_valid=recon_valid,
        stage06_relative_sign_status=sign_status,
        stage06_relative_sign_continuity_valid=sign_valid,
        stage07_branch_cut_status=branch,
        stage07_max_rotvec_norm=max_norm,
        stage07_jump_status=jump,
        stage07_max_jump_rad=max_jump,
        stage07_link_qc_status=link_qc,
        stage08_policy=policy,
        notes=notes,
    )


def build_compact_signal_table(
    *,
    rotvec_table: pd.DataFrame,
    link_records: dict[str, LinkQCRecord],
    link_diagnostics: list[LinkRotVecDiagnostics],
    thresholds: RotVecThresholds,
    session_id: str,
    run_label: str,
) -> pd.DataFrame:
    diag_by_id = {item.joint_id: item for item in link_diagnostics}
    rows: list[dict[str, Any]] = []

    for link_id, group in rotvec_table.groupby("joint_id", sort=True):
        record = link_records[str(link_id)]
        diag = diag_by_id[str(link_id)]
        ordered = group.sort_values("frame")
        rotvecs = ordered[["rx", "ry", "rz"]].to_numpy(dtype=float)
        norms = ordered["rotvec_norm"].to_numpy(dtype=float)
        jumps = frame_to_frame_rotvec_jumps(rotvecs)
        frames = ordered["frame"].to_numpy()
        times = ordered["time"].to_numpy(dtype=float)

        for idx in range(len(ordered)):
            if idx == 0:
                jump_from_prev = False
                jump_mag = 0.0
            else:
                jump_from_prev = True
                jump_mag = float(jumps[idx - 1])

            row_qc = _row_qc_from_frame(float(norms[idx]), jump_mag, thresholds)
            if not np.isfinite(norms[idx]):
                row_qc = DiagnosticStatus.FAIL.value

            rows.append(
                {
                    "session_id": session_id,
                    "run_label": run_label,
                    "frame": int(frames[idx]),
                    "time_sec": float(times[idx]),
                    "link_id": str(link_id),
                    "parent_canonical": record.parent_canonical,
                    "child_canonical": record.child_canonical,
                    "rx": float(rotvecs[idx, 0]),
                    "ry": float(rotvecs[idx, 1]),
                    "rz": float(rotvecs[idx, 2]),
                    "rotvec_norm": float(norms[idx]),
                    "feature_scope": record.feature_scope,
                    "included_in_v0": record.included_in_v0,
                    "requires_manual_review": record.requires_manual_review,
                    "stage04_quaternion_valid": record.stage04_quaternion_valid,
                    "stage05_global_sign_continuity_valid": (
                        record.stage05_global_sign_continuity_valid
                    ),
                    "stage06_relative_reconstruction_valid": (
                        record.stage06_relative_reconstruction_valid
                    ),
                    "stage06_relative_sign_continuity_valid": (
                        record.stage06_relative_sign_continuity_valid
                    ),
                    "stage07_branch_cut_status": diag.branch_cut_status.value,
                    "stage07_jump_status": diag.jump_status.value,
                    "stage07_jump_from_previous_frame": jump_from_prev,
                    "stage07_jump_magnitude_rad": jump_mag,
                    "stage07_row_qc_status": row_qc,
                    "stage07_link_qc_status": record.stage07_link_qc_status,
                    "stage08_policy": record.stage08_policy,
                }
            )

    return pd.DataFrame(rows, columns=list(COMPACT_SIGNAL_COLUMNS))


def link_record_to_manifest_row(
    record: LinkQCRecord,
    *,
    session_id: str,
    run_label: str,
    template_name: str,
) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "run_label": run_label,
        "template_name": template_name,
        "link_id": record.link_id,
        "parent_canonical": record.parent_canonical,
        "child_canonical": record.child_canonical,
        "feature_scope": record.feature_scope,
        "stage04_parent_qc_status": record.stage04_parent_qc_status,
        "stage04_child_qc_status": record.stage04_child_qc_status,
        "stage05_parent_sign_status": record.stage05_parent_sign_status,
        "stage05_child_sign_status": record.stage05_child_sign_status,
        "stage06_reconstruction_status": record.stage06_reconstruction_status,
        "stage06_max_reconstruction_error_deg": record.stage06_max_reconstruction_error_deg,
        "stage06_relative_sign_status": record.stage06_relative_sign_status,
        "stage07_branch_cut_status": record.stage07_branch_cut_status,
        "stage07_max_rotvec_norm": record.stage07_max_rotvec_norm,
        "stage07_jump_status": record.stage07_jump_status,
        "stage07_max_jump_rad": record.stage07_max_jump_rad,
        "stage08_policy": record.stage08_policy,
        "notes": record.notes,
    }


def build_session_manifest_row(
    *,
    session_id: str,
    run_label: str,
    context: StageQCContext,
    file_result: FileRotVecResult,
) -> dict[str, Any]:
    if file_result.core_failures > 0:
        stage07_status = "fail"
    elif file_result.core_warnings > 0:
        stage07_status = "warning"
    else:
        stage07_status = "pass"

    if file_result.stage08_may_proceed:
        stage08_auth = (
            "review_required" if file_result.core_failures > 0 else "authorized"
        )
    else:
        stage08_auth = "blocked"

    notes = "; ".join(file_result.fail_reasons[:3])
    if file_result.warning_reasons:
        notes = (notes + "; " if notes else "") + "; ".join(file_result.warning_reasons[:2])

    return {
        "session_id": session_id,
        "run_label": run_label,
        "skeleton_template": template_name_for_session(session_id),
        "frame_count": context.frame_count,
        "sampling_rate_hz": context.sampling_rate_hz,
        "stage03_timing_status": context.stage03_timing_status,
        "stage04_file_status": context.stage04_file_status,
        "stage05_file_status": context.stage05_file_status,
        "stage06_file_status": context.stage06_file_status,
        "stage07_file_status": stage07_status,
        "stage08_authorization_status": stage08_auth,
        "notes": notes,
    }


def build_qc_artifacts_for_run(
    *,
    input_csv: Path,
    output_dir: Path,
    rotvec_table: pd.DataFrame,
    file_result: FileRotVecResult,
    candidate_joints: pd.DataFrame,
    thresholds: RotVecThresholds,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Build compact signal table, per-run link manifest, and session manifest row."""
    context = load_stage_qc_context(output_dir)
    run_label = output_dir.name
    session_id = session_id_from_run_label(run_label)
    template_name = template_name_for_session(session_id)
    candidate_lookup = candidate_joints.set_index("joint_id", drop=False)

    link_records: dict[str, LinkQCRecord] = {}
    manifest_rows: list[dict[str, Any]] = []

    for item in file_result.link_diagnostics:
        cand = (
            candidate_lookup.loc[item.joint_id]
            if item.joint_id in candidate_lookup.index
            else None
        )
        exclusion_reason = ""
        if cand is not None:
            raw = str(cand.get("exclusion_reason", ""))
            exclusion_reason = "" if raw == "nan" else raw
        record = build_link_qc_record(
            link_diag=item,
            context=context,
            candidate_row=cand,
            exclusion_reason=exclusion_reason,
        )
        link_records[item.joint_id] = record
        manifest_rows.append(
            link_record_to_manifest_row(
                record,
                session_id=session_id,
                run_label=run_label,
                template_name=template_name,
            )
        )

    missing_path = output_dir / "06_relative_quaternions" / "missing_parent_child_links.csv"
    if missing_path.exists():
        missing = pd.read_csv(missing_path)
        for _, row in missing.iterrows():
            joint_id = str(row["joint_id"])
            cand = candidate_lookup.loc[joint_id] if joint_id in candidate_lookup.index else row
            record = build_link_qc_record(
                link_diag=None,
                context=context,
                candidate_row=cand,
                exclusion_reason="parent_is_root",
                is_skipped=True,
                skip_note=str(row.get("missing_reason", "skipped in Stage 06")),
            )
            manifest_rows.append(
                link_record_to_manifest_row(
                    record,
                    session_id=session_id,
                    run_label=run_label,
                    template_name=template_name,
                )
            )

    compact = build_compact_signal_table(
        rotvec_table=rotvec_table,
        link_records=link_records,
        link_diagnostics=file_result.link_diagnostics,
        thresholds=thresholds,
        session_id=session_id,
        run_label=run_label,
    )
    session_row = build_session_manifest_row(
        session_id=session_id,
        run_label=run_label,
        context=context,
        file_result=file_result,
    )
    link_manifest = pd.DataFrame(manifest_rows, columns=list(LINK_MANIFEST_COLUMNS))
    return compact, link_manifest, session_row


def rebuild_layer2_qc_manifests(output_root: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Aggregate per-run QC manifests from completed Stage 07 outputs."""
    link_rows: list[dict[str, Any]] = []
    session_rows: list[dict[str, Any]] = []

    for run_dir in sorted(output_root.glob("671_*")):
        stage07 = run_dir / "07_rotation_vectors"
        link_path = stage07 / "qc_link_manifest.csv"
        session_path = stage07 / "qc_session_manifest.csv"
        if link_path.exists():
            link_rows.extend(pd.read_csv(link_path).to_dict(orient="records"))
        if session_path.exists():
            session_rows.extend(pd.read_csv(session_path).to_dict(orient="records"))

    link_df = pd.DataFrame(link_rows, columns=list(LINK_MANIFEST_COLUMNS))
    session_df = pd.DataFrame(session_rows, columns=list(SESSION_MANIFEST_COLUMNS))

    if not link_df.empty:
        link_df.to_csv(output_root / "layer2_qc_link_manifest.csv", index=False)
    if not session_df.empty:
        session_df.to_csv(output_root / "layer2_qc_session_manifest.csv", index=False)

    return link_df, session_df
