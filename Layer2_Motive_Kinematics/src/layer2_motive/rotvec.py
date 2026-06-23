"""Rotation-vector log-map, jump and branch-cut diagnostics (Stage 07)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.spatial.transform import Rotation

from layer2_motive.config import load_config
from layer2_motive.pre_stage07_gate import classify_link_for_gate

PI = float(np.pi)


class DiagnosticStatus(str, Enum):
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"


@dataclass(frozen=True)
class RotVecThresholds:
    near_pi_threshold_rad: float
    near_pi_warning_fraction: float
    branch_cut_fail_tol_rad: float
    jump_warning_rad: float
    jump_fail_rad: float

    @property
    def branch_cut_warning_rad(self) -> float:
        return self.near_pi_warning_fraction * PI

    @property
    def branch_cut_fail_rad(self) -> float:
        return PI - self.branch_cut_fail_tol_rad


def thresholds_from_config(config: dict[str, Any]) -> RotVecThresholds:
    section = config.get("rotvec", {})
    return RotVecThresholds(
        near_pi_threshold_rad=float(section.get("near_pi_threshold_rad", PI - 0.10)),
        near_pi_warning_fraction=float(section.get("near_pi_warning_fraction", 0.95)),
        branch_cut_fail_tol_rad=float(section.get("branch_cut_fail_tol_rad", 1.0e-6)),
        jump_warning_rad=float(section.get("jump_warning_rad", 0.5)),
        jump_fail_rad=float(section.get("jump_fail_rad", 1.0)),
    )


def quat_rows_to_rotvec(quats: np.ndarray) -> np.ndarray:
    """Convert SciPy-order quaternion rows [x,y,z,w] to rotation vectors."""
    return Rotation.from_quat(np.asarray(quats, dtype=float).copy()).as_rotvec()


def quat_to_rotvec(qx: float, qy: float, qz: float, qw: float) -> tuple[float, float, float]:
    rotvec = Rotation.from_quat([qx, qy, qz, qw]).as_rotvec()
    return float(rotvec[0]), float(rotvec[1]), float(rotvec[2])


def rotvec_norm(rx: float, ry: float, rz: float) -> float:
    return float(np.linalg.norm([rx, ry, rz]))


def frame_to_frame_rotvec_jumps(rotvecs: np.ndarray) -> np.ndarray:
    """Euclidean norm of consecutive rotation-vector differences (length n-1)."""
    if len(rotvecs) < 2:
        return np.array([], dtype=float)
    diffs = np.diff(rotvecs, axis=0)
    return np.linalg.norm(diffs, axis=1)


def evaluate_branch_cut_status(
    max_rotvec_norm: float,
    thresholds: RotVecThresholds,
) -> DiagnosticStatus:
    if max_rotvec_norm >= thresholds.branch_cut_fail_rad:
        return DiagnosticStatus.FAIL
    if max_rotvec_norm > thresholds.branch_cut_warning_rad:
        return DiagnosticStatus.WARNING
    return DiagnosticStatus.PASS


def evaluate_jump_status(
    max_jump: float,
    thresholds: RotVecThresholds,
) -> DiagnosticStatus:
    if max_jump > thresholds.jump_fail_rad:
        return DiagnosticStatus.FAIL
    if max_jump > thresholds.jump_warning_rad:
        return DiagnosticStatus.WARNING
    return DiagnosticStatus.PASS


def _percentile(values: np.ndarray, pct: float) -> float:
    if values.size == 0:
        return 0.0
    return float(np.percentile(values, pct))


def _link_classification_row(
    *,
    parent_bone: str,
    child_bone: str,
    is_root_anchor_link: bool,
    exclusion_reason: str,
) -> dict[str, Any]:
    classification = classify_link_for_gate(
        parent_bone=parent_bone,
        child_bone=child_bone,
        is_root_anchor_link=is_root_anchor_link,
        exclusion_reason=exclusion_reason,
    )
    if classification.core_candidate:
        link_group = "core_candidate"
    elif classification.excluded_candidate:
        link_group = "excluded"
    else:
        link_group = "review_provisional"
    return {
        "link_classification": classification.link_classification,
        "core_candidate": classification.core_candidate,
        "excluded_candidate": classification.excluded_candidate,
        "link_group": link_group,
        "parent_segment_role": classification.parent_segment_role,
        "child_segment_role": classification.child_segment_role,
        "terminology_note": classification.terminology_note,
    }


@dataclass
class LinkRotVecDiagnostics:
    joint_id: str
    parent_bone: str
    child_bone: str
    source_parent_bone: str
    source_child_bone: str
    included_in_v0: bool
    selection_status: str
    requires_manual_review: bool
    link_classification: str
    core_candidate: bool
    excluded_candidate: bool
    link_group: str
    total_frames: int
    finite_rotvec_rows: int
    non_finite_rotvec_rows: int
    min_rotvec_norm: float
    mean_rotvec_norm: float
    median_rotvec_norm: float
    max_rotvec_norm: float
    p95_rotvec_norm: float
    p99_rotvec_norm: float
    near_pi_count: int
    near_pi_percent: float
    max_frame_to_frame_jump: float
    p95_frame_to_frame_jump: float
    p99_frame_to_frame_jump: float
    large_jump_count: int
    large_jump_percent: float
    first_large_jump_frame: int | None
    branch_cut_status: DiagnosticStatus
    jump_status: DiagnosticStatus
    stage08_may_proceed_for_link: bool


def compute_link_rotvec_diagnostics(
    *,
    joint_id: str,
    group: pd.DataFrame,
    thresholds: RotVecThresholds,
    exclusion_reason: str = "",
) -> LinkRotVecDiagnostics:
    parent_bone = str(group["parent_bone"].iloc[0])
    child_bone = str(group["child_bone"].iloc[0])
    source_parent = str(group["source_parent_bone"].iloc[0])
    source_child = str(group["source_child_bone"].iloc[0])
    is_root_anchor = bool(group["is_root_anchor_link"].iloc[0])
    included_in_v0 = bool(group["included_in_v0"].iloc[0])
    selection_status = str(group["selection_status"].iloc[0])
    requires_review = bool(group["requires_manual_review"].iloc[0])

    class_row = _link_classification_row(
        parent_bone=parent_bone,
        child_bone=child_bone,
        is_root_anchor_link=is_root_anchor,
        exclusion_reason=exclusion_reason,
    )

    rotvecs = group.sort_values("frame")[["rx", "ry", "rz"]].to_numpy(dtype=float)
    frames = group.sort_values("frame")["frame"].to_numpy()
    norms = group.sort_values("frame")["rotvec_norm"].to_numpy(dtype=float)
    total_frames = len(group)
    finite_mask = np.isfinite(rotvecs).all(axis=1) & np.isfinite(norms)
    finite_rows = int(finite_mask.sum())
    non_finite_rows = total_frames - finite_rows

    finite_norms = norms[finite_mask]
    finite_rotvecs = rotvecs[finite_mask]

    if finite_norms.size:
        min_norm = float(np.min(finite_norms))
        mean_norm = float(np.mean(finite_norms))
        median_norm = float(np.median(finite_norms))
        max_norm = float(np.max(finite_norms))
        p95_norm = _percentile(finite_norms, 95)
        p99_norm = _percentile(finite_norms, 99)
        near_pi_count = int((finite_norms >= thresholds.near_pi_threshold_rad).sum())
    else:
        min_norm = mean_norm = median_norm = max_norm = p95_norm = p99_norm = float("nan")
        near_pi_count = 0

    near_pi_percent = (100.0 * near_pi_count / total_frames) if total_frames else 0.0

    jumps = frame_to_frame_rotvec_jumps(finite_rotvecs)
    if jumps.size:
        max_jump = float(np.max(jumps))
        p95_jump = _percentile(jumps, 95)
        p99_jump = _percentile(jumps, 99)
        large_jump_mask = jumps > thresholds.jump_warning_rad
        large_jump_count = int(large_jump_mask.sum())
        if large_jump_mask.any():
            first_jump_idx = int(np.argmax(large_jump_mask))
            first_large_jump_frame = int(frames[first_jump_idx + 1])
        else:
            first_large_jump_frame = None
    else:
        max_jump = p95_jump = p99_jump = 0.0
        large_jump_count = 0
        first_large_jump_frame = None

    large_jump_percent = (100.0 * large_jump_count / max(len(jumps), 1)) if jumps.size else 0.0

    branch_status = evaluate_branch_cut_status(
        max_norm if finite_norms.size else float("inf"), thresholds
    )
    jump_status = evaluate_jump_status(max_jump, thresholds)

    if non_finite_rows > 0:
        branch_status = DiagnosticStatus.FAIL
        jump_status = DiagnosticStatus.FAIL

    stage08_ok = non_finite_rows == 0

    return LinkRotVecDiagnostics(
        joint_id=joint_id,
        parent_bone=parent_bone,
        child_bone=child_bone,
        source_parent_bone=source_parent,
        source_child_bone=source_child,
        included_in_v0=included_in_v0,
        selection_status=selection_status,
        requires_manual_review=requires_review,
        link_classification=str(class_row["link_classification"]),
        core_candidate=bool(class_row["core_candidate"]),
        excluded_candidate=bool(class_row["excluded_candidate"]),
        link_group=str(class_row["link_group"]),
        total_frames=total_frames,
        finite_rotvec_rows=finite_rows,
        non_finite_rotvec_rows=non_finite_rows,
        min_rotvec_norm=min_norm,
        mean_rotvec_norm=mean_norm,
        median_rotvec_norm=median_norm,
        max_rotvec_norm=max_norm,
        p95_rotvec_norm=p95_norm,
        p99_rotvec_norm=p99_norm,
        near_pi_count=near_pi_count,
        near_pi_percent=near_pi_percent,
        max_frame_to_frame_jump=max_jump,
        p95_frame_to_frame_jump=p95_jump,
        p99_frame_to_frame_jump=p99_jump,
        large_jump_count=large_jump_count,
        large_jump_percent=large_jump_percent,
        first_large_jump_frame=first_large_jump_frame,
        branch_cut_status=branch_status,
        jump_status=jump_status,
        stage08_may_proceed_for_link=stage08_ok,
    )


def diagnostics_to_summary_row(item: LinkRotVecDiagnostics) -> dict[str, Any]:
    return {
        "joint_id": item.joint_id,
        "parent_bone": item.parent_bone,
        "child_bone": item.child_bone,
        "source_parent_bone": item.source_parent_bone,
        "source_child_bone": item.source_child_bone,
        "included_in_v0": item.included_in_v0,
        "selection_status": item.selection_status,
        "requires_manual_review": item.requires_manual_review,
        "link_classification": item.link_classification,
        "core_candidate": item.core_candidate,
        "excluded_candidate": item.excluded_candidate,
        "link_group": item.link_group,
        "total_frames": item.total_frames,
        "finite_rotvec_rows": item.finite_rotvec_rows,
        "non_finite_rotvec_rows": item.non_finite_rotvec_rows,
        "min_rotvec_norm": item.min_rotvec_norm,
        "mean_rotvec_norm": item.mean_rotvec_norm,
        "median_rotvec_norm": item.median_rotvec_norm,
        "max_rotvec_norm": item.max_rotvec_norm,
        "p95_rotvec_norm": item.p95_rotvec_norm,
        "p99_rotvec_norm": item.p99_rotvec_norm,
        "near_pi_count": item.near_pi_count,
        "near_pi_percent": item.near_pi_percent,
        "max_frame_to_frame_jump": item.max_frame_to_frame_jump,
        "p95_frame_to_frame_jump": item.p95_frame_to_frame_jump,
        "p99_frame_to_frame_jump": item.p99_frame_to_frame_jump,
        "large_jump_count": item.large_jump_count,
        "large_jump_percent": item.large_jump_percent,
        "first_large_jump_frame": item.first_large_jump_frame,
        "branch_cut_status": item.branch_cut_status.value,
        "jump_status": item.jump_status.value,
        "stage08_may_proceed_for_link": item.stage08_may_proceed_for_link,
    }


def diagnostics_to_branch_cut_row(item: LinkRotVecDiagnostics) -> dict[str, Any]:
    return {
        "joint_id": item.joint_id,
        "parent_bone": item.parent_bone,
        "child_bone": item.child_bone,
        "link_group": item.link_group,
        "core_candidate": item.core_candidate,
        "excluded_candidate": item.excluded_candidate,
        "total_frames": item.total_frames,
        "non_finite_rotvec_rows": item.non_finite_rotvec_rows,
        "max_rotvec_norm": item.max_rotvec_norm,
        "p95_rotvec_norm": item.p95_rotvec_norm,
        "p99_rotvec_norm": item.p99_rotvec_norm,
        "near_pi_count": item.near_pi_count,
        "near_pi_percent": item.near_pi_percent,
        "branch_cut_status": item.branch_cut_status.value,
        "stage08_may_proceed_for_link": item.stage08_may_proceed_for_link,
    }


def diagnostics_to_jump_row(item: LinkRotVecDiagnostics) -> dict[str, Any]:
    return {
        "joint_id": item.joint_id,
        "parent_bone": item.parent_bone,
        "child_bone": item.child_bone,
        "link_group": item.link_group,
        "core_candidate": item.core_candidate,
        "excluded_candidate": item.excluded_candidate,
        "total_frames": item.total_frames,
        "max_frame_to_frame_jump": item.max_frame_to_frame_jump,
        "p95_frame_to_frame_jump": item.p95_frame_to_frame_jump,
        "p99_frame_to_frame_jump": item.p99_frame_to_frame_jump,
        "large_jump_count": item.large_jump_count,
        "large_jump_percent": item.large_jump_percent,
        "first_large_jump_frame": item.first_large_jump_frame,
        "jump_status": item.jump_status.value,
        "stage08_may_proceed_for_link": item.stage08_may_proceed_for_link,
    }


@dataclass
class FileRotVecResult:
    input_file: str
    links_processed: int
    core_links_processed: int
    review_links_processed: int
    excluded_links_processed: int
    max_rotvec_norm_core: float
    max_rotvec_norm_all: float
    max_jump_core: float
    max_jump_all: float
    core_warnings: int
    core_failures: int
    review_warnings: int
    review_failures: int
    excluded_warnings: int
    excluded_failures: int
    stage08_may_proceed: bool
    link_diagnostics: list[LinkRotVecDiagnostics]
    fail_reasons: list[str]
    warning_reasons: list[str]
    input_format_note: str


def load_stage06_relative_quaternions(stage06_dir: Path) -> tuple[pd.DataFrame, str]:
    parquet_path = stage06_dir / "relative_quaternions.parquet"
    csv_path = stage06_dir / "relative_quaternions.csv"
    if parquet_path.exists():
        return pd.read_parquet(parquet_path), "parquet"
    if csv_path.exists():
        return pd.read_csv(csv_path), "csv_fallback"
    raise FileNotFoundError(
        f"Stage 06 relative quaternion output missing in {stage06_dir}; "
        "expected relative_quaternions.parquet (or CSV fallback)"
    )


def convert_relative_quaternions_table(
    relative_quats: pd.DataFrame,
    *,
    input_file: str,
) -> pd.DataFrame:
    """Apply log-map to Stage 06 relative quaternions; preserve metadata columns."""
    quats = relative_quats[["qx", "qy", "qz", "qw"]].to_numpy(dtype=float)
    rotvecs = quat_rows_to_rotvec(quats)
    norms = np.linalg.norm(rotvecs, axis=1)

    preserve_cols = [
        "frame",
        "time",
        "joint_id",
        "source_parent_bone",
        "source_child_bone",
        "parent_bone",
        "child_bone",
        "is_root_anchor_link",
        "included_in_v0",
        "selection_status",
        "requires_manual_review",
        "qx",
        "qy",
        "qz",
        "qw",
        "relative_flip_applied",
    ]
    out = relative_quats.loc[:, [c for c in preserve_cols if c in relative_quats.columns]].copy()
    out.insert(0, "input_file", input_file)
    out["rx"] = rotvecs[:, 0]
    out["ry"] = rotvecs[:, 1]
    out["rz"] = rotvecs[:, 2]
    out["rotvec_norm"] = norms
    return out


def process_file_rotvecs(
    *,
    input_file: str,
    relative_quats: pd.DataFrame,
    candidate_joints: pd.DataFrame,
    thresholds: RotVecThresholds,
) -> tuple[FileRotVecResult, pd.DataFrame]:
    rotvec_table = convert_relative_quaternions_table(relative_quats, input_file=input_file)
    exclusion_lookup = candidate_joints.set_index("joint_id", drop=False)

    link_diagnostics: list[LinkRotVecDiagnostics] = []
    for joint_id, group in rotvec_table.groupby("joint_id", sort=True):
        cand = exclusion_lookup.loc[joint_id] if joint_id in exclusion_lookup.index else None
        exclusion_reason = ""
        if cand is not None:
            raw_reason = str(cand.get("exclusion_reason", ""))
            exclusion_reason = "" if raw_reason == "nan" else raw_reason
        link_diagnostics.append(
            compute_link_rotvec_diagnostics(
                joint_id=str(joint_id),
                group=group.sort_values("frame"),
                thresholds=thresholds,
                exclusion_reason=exclusion_reason,
            )
        )

    core_items = [item for item in link_diagnostics if item.core_candidate]
    review_items = [item for item in link_diagnostics if item.link_group == "review_provisional"]
    excluded_items = [item for item in link_diagnostics if item.excluded_candidate]

    def _max_norm(items: list[LinkRotVecDiagnostics]) -> float:
        if not items:
            return 0.0
        return max(item.max_rotvec_norm for item in items if np.isfinite(item.max_rotvec_norm))

    def _max_jump(items: list[LinkRotVecDiagnostics]) -> float:
        if not items:
            return 0.0
        return max(item.max_frame_to_frame_jump for item in items)

    def _count_status(items: list[LinkRotVecDiagnostics], status: DiagnosticStatus) -> int:
        return sum(
            1
            for item in items
            if item.branch_cut_status == status
            or item.jump_status == status
            or (status == DiagnosticStatus.FAIL and item.non_finite_rotvec_rows > 0)
        )

    fail_reasons: list[str] = []
    warning_reasons: list[str] = []

    for item in core_items:
        label = f"{item.joint_id} ({item.parent_bone}→{item.child_bone})"
        if item.non_finite_rotvec_rows > 0:
            fail_reasons.append(
                f"{label}: {item.non_finite_rotvec_rows} non-finite rotation-vector rows"
            )
        if item.branch_cut_status == DiagnosticStatus.FAIL:
            fail_reasons.append(
                f"{label}: branch-cut fail (max rotvec_norm={item.max_rotvec_norm:.6g} rad)"
            )
        elif item.branch_cut_status == DiagnosticStatus.WARNING:
            warning_reasons.append(
                f"{label}: branch-cut warning (max rotvec_norm={item.max_rotvec_norm:.6g} rad)"
            )
        if item.jump_status == DiagnosticStatus.FAIL:
            fail_reasons.append(
                f"{label}: jump fail (max jump={item.max_frame_to_frame_jump:.6g} rad)"
            )
        elif item.jump_status == DiagnosticStatus.WARNING:
            warning_reasons.append(
                f"{label}: jump warning (max jump={item.max_frame_to_frame_jump:.6g} rad)"
            )

    for item in review_items + excluded_items:
        label = f"{item.joint_id} ({item.parent_bone}→{item.child_bone})"
        if item.branch_cut_status == DiagnosticStatus.FAIL:
            warning_reasons.append(
                f"{label} [{item.link_group}]: branch-cut fail "
                f"(max rotvec_norm={item.max_rotvec_norm:.6g} rad; "
                "non-blocking for Stage 07 file pass)"
            )
        elif item.branch_cut_status == DiagnosticStatus.WARNING:
            warning_reasons.append(
                f"{label} [{item.link_group}]: branch-cut warning "
                f"(max rotvec_norm={item.max_rotvec_norm:.6g} rad)"
            )
        if item.jump_status == DiagnosticStatus.FAIL:
            warning_reasons.append(
                f"{label} [{item.link_group}]: jump fail "
                f"(max jump={item.max_frame_to_frame_jump:.6g} rad; non-blocking unless core)"
            )
        elif item.jump_status == DiagnosticStatus.WARNING:
            warning_reasons.append(
                f"{label} [{item.link_group}]: jump warning "
                f"(max jump={item.max_frame_to_frame_jump:.6g} rad)"
            )

    core_failures = sum(
        1
        for item in core_items
        if item.non_finite_rotvec_rows > 0
        or item.branch_cut_status == DiagnosticStatus.FAIL
        or item.jump_status == DiagnosticStatus.FAIL
    )
    core_warnings = sum(
        1
        for item in core_items
        if item.branch_cut_status == DiagnosticStatus.WARNING
        or item.jump_status == DiagnosticStatus.WARNING
    )
    review_failures = sum(
        1
        for item in review_items
        if item.branch_cut_status == DiagnosticStatus.FAIL
        or item.jump_status == DiagnosticStatus.FAIL
        or item.non_finite_rotvec_rows > 0
    )
    review_warnings = sum(
        1
        for item in review_items
        if item.branch_cut_status == DiagnosticStatus.WARNING
        or item.jump_status == DiagnosticStatus.WARNING
    )
    excluded_failures = sum(
        1
        for item in excluded_items
        if item.branch_cut_status == DiagnosticStatus.FAIL
        or item.jump_status == DiagnosticStatus.FAIL
        or item.non_finite_rotvec_rows > 0
    )
    excluded_warnings = sum(
        1
        for item in excluded_items
        if item.branch_cut_status == DiagnosticStatus.WARNING
        or item.jump_status == DiagnosticStatus.WARNING
    )

    core_blocking_failures = sum(
        1 for item in core_items if item.non_finite_rotvec_rows > 0
    )
    stage08_may_proceed = core_blocking_failures == 0

    file_result = FileRotVecResult(
        input_file=input_file,
        links_processed=len(link_diagnostics),
        core_links_processed=len(core_items),
        review_links_processed=len(review_items),
        excluded_links_processed=len(excluded_items),
        max_rotvec_norm_core=_max_norm(core_items),
        max_rotvec_norm_all=_max_norm(link_diagnostics),
        max_jump_core=_max_jump(core_items),
        max_jump_all=_max_jump(link_diagnostics),
        core_warnings=core_warnings,
        core_failures=core_failures,
        review_warnings=review_warnings,
        review_failures=review_failures,
        excluded_warnings=excluded_warnings,
        excluded_failures=excluded_failures,
        stage08_may_proceed=stage08_may_proceed,
        link_diagnostics=link_diagnostics,
        fail_reasons=fail_reasons,
        warning_reasons=warning_reasons,
        input_format_note="",
    )
    return file_result, rotvec_table


def file_summary_row(result: FileRotVecResult) -> dict[str, Any]:
    return {
        "input_file": result.input_file,
        "links_processed": result.links_processed,
        "core_links_processed": result.core_links_processed,
        "review_links_processed": result.review_links_processed,
        "excluded_links_processed": result.excluded_links_processed,
        "max_rotvec_norm_core": result.max_rotvec_norm_core,
        "max_rotvec_norm_all": result.max_rotvec_norm_all,
        "max_jump_core": result.max_jump_core,
        "max_jump_all": result.max_jump_all,
        "core_warnings": result.core_warnings,
        "core_failures": result.core_failures,
        "review_warnings": result.review_warnings,
        "review_failures": result.review_failures,
        "excluded_warnings": result.excluded_warnings,
        "excluded_failures": result.excluded_failures,
        "stage08_may_proceed": result.stage08_may_proceed,
        "fail_reasons": "; ".join(result.fail_reasons),
        "warning_reasons": "; ".join(result.warning_reasons),
    }


def load_thresholds(config_path: Path | None = None) -> RotVecThresholds:
    return thresholds_from_config(load_config(config_path))
