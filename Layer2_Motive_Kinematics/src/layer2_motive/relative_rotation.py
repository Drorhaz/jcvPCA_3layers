"""Relative quaternion computation, reconstruction validation, sign-continuity (Stage 06)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.spatial.transform import Rotation

from layer2_motive.quaternion_continuity import (
    SignContinuityThresholds,
    apply_sign_continuity,
    consecutive_dot_products,
    validate_post_correction_dots,
)

# SciPy Rotation composition: r_parent.inv() * r_child implements
# q_relative = inverse(q_parent_global) * q_child_global
# Reconstruction: r_parent * r_relative == r_child (same rotation as q_child_global)
MULTIPLICATION_ORDER_DOC = (
    "Relative quaternion: q_rel = inv(q_parent) * q_child via SciPy "
    "Rotation.from_quat(parent).inv() * Rotation.from_quat(child). "
    "Reconstruction: q_child ≈ q_parent * q_rel via parent * relative."
)

DEFAULT_PASS_MAX_ERROR_DEG = 1.0e-5
DEFAULT_WARNING_MAX_ERROR_DEG = 1.0e-3


class ReconstructionStatus(str, Enum):
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"


@dataclass(frozen=True)
class ReconstructionThresholds:
    """Angular error thresholds for parent→child reconstruction validation."""

    pass_max_error_deg: float = DEFAULT_PASS_MAX_ERROR_DEG
    warning_max_error_deg: float = DEFAULT_WARNING_MAX_ERROR_DEG

    def classify_max_error(self, max_error_deg: float) -> ReconstructionStatus:
        if max_error_deg <= self.pass_max_error_deg:
            return ReconstructionStatus.PASS
        if max_error_deg <= self.warning_max_error_deg:
            return ReconstructionStatus.WARNING
        return ReconstructionStatus.FAIL


@dataclass
class LinkReconstructionResult:
    joint_id: str
    source_parent_bone: str
    source_child_bone: str
    parent_bone: str
    child_bone: str
    is_root_anchor_link: bool
    included_in_v0: bool
    selection_status: str
    requires_manual_review: bool
    frame_count: int
    mean_error_deg: float
    median_error_deg: float
    max_error_deg: float
    p99_error_deg: float
    reconstruction_status: ReconstructionStatus
    missing_reason: str = ""


@dataclass
class RelativeSignContinuityResult:
    joint_id: str
    source_parent_bone: str
    source_child_bone: str
    parent_bone: str
    child_bone: str
    total_frames: int
    raw_sign_flip_count: int
    corrected_sign_flip_count: int
    min_raw_consecutive_dot: float | None
    min_corrected_consecutive_dot: float | None
    post_correction_valid: bool
    correction_applied: bool


@dataclass
class FileRelativeRotationResult:
    input_file: str
    parent_child_links_processed: int
    parent_child_links_missing: int
    total_frames: int
    global_max_reconstruction_error_deg: float
    links_pass: int
    links_warning: int
    links_fail: int
    total_relative_sign_flips_raw: int
    total_relative_sign_flips_corrected: int
    relative_sign_continuity_valid: bool
    stage07_may_proceed: bool
    link_results: list[LinkReconstructionResult] = field(default_factory=list)
    sign_continuity_results: list[RelativeSignContinuityResult] = field(default_factory=list)
    missing_links: list[dict[str, Any]] = field(default_factory=list)
    fail_reasons: list[str] = field(default_factory=list)
    warning_reasons: list[str] = field(default_factory=list)


def thresholds_from_config(config: dict[str, Any]) -> ReconstructionThresholds:
    section = config.get("relative_rotation", {})
    if not isinstance(section, dict):
        return ReconstructionThresholds()
    return ReconstructionThresholds(
        pass_max_error_deg=float(
            section.get("reconstruction_max_error_deg", DEFAULT_PASS_MAX_ERROR_DEG)
        ),
        warning_max_error_deg=float(
            section.get("reconstruction_warning_max_error_deg", DEFAULT_WARNING_MAX_ERROR_DEG)
        ),
    )


def compute_relative_quaternions(
    parent_quats: np.ndarray,
    child_quats: np.ndarray,
) -> np.ndarray:
    """Compute q_rel = inv(q_parent) * q_child for aligned (n, 4) SciPy-order arrays."""
    if (
        parent_quats.shape != child_quats.shape
        or parent_quats.ndim != 2
        or parent_quats.shape[1] != 4
    ):
        raise ValueError("parent_quats and child_quats must both have shape (n, 4)")

    r_parent = Rotation.from_quat(parent_quats)
    r_child = Rotation.from_quat(child_quats)
    r_relative = r_parent.inv() * r_child
    return r_relative.as_quat()


def compute_relative_quaternions_wrong_order(
    parent_quats: np.ndarray,
    child_quats: np.ndarray,
) -> np.ndarray:
    """Wrong order q_child * inv(q_parent) — for negative testing only."""
    r_parent = Rotation.from_quat(parent_quats)
    r_child = Rotation.from_quat(child_quats)
    r_wrong = r_child * r_parent.inv()
    return r_wrong.as_quat()


def reconstruct_child_global(
    parent_quats: np.ndarray,
    relative_quats: np.ndarray,
) -> np.ndarray:
    """Reconstruct q_child ≈ q_parent * q_rel."""
    r_parent = Rotation.from_quat(parent_quats)
    r_relative = Rotation.from_quat(relative_quats)
    r_child = r_parent * r_relative
    return r_child.as_quat()


def angular_error_degrees(q_reference: np.ndarray, q_compare: np.ndarray) -> np.ndarray:
    """Angular error in degrees between quaternion rows (handles double cover)."""
    r_ref = Rotation.from_quat(q_reference)
    r_cmp = Rotation.from_quat(q_compare)
    return (r_ref.inv() * r_cmp).magnitude() * 180.0 / np.pi


def summarize_reconstruction_errors(errors_deg: np.ndarray) -> dict[str, float]:
    if errors_deg.size == 0:
        return {
            "mean_error_deg": 0.0,
            "median_error_deg": 0.0,
            "max_error_deg": 0.0,
            "p99_error_deg": 0.0,
        }
    return {
        "mean_error_deg": float(np.mean(errors_deg)),
        "median_error_deg": float(np.median(errors_deg)),
        "max_error_deg": float(np.max(errors_deg)),
        "p99_error_deg": float(np.percentile(errors_deg, 99)),
    }


def validate_link_reconstruction(
    *,
    joint_id: str,
    source_parent_bone: str,
    source_child_bone: str,
    parent_bone: str,
    child_bone: str,
    is_root_anchor_link: bool,
    included_in_v0: bool,
    selection_status: str,
    requires_manual_review: bool,
    parent_quats: np.ndarray,
    child_quats: np.ndarray,
    thresholds: ReconstructionThresholds,
) -> tuple[LinkReconstructionResult, np.ndarray]:
    relative = compute_relative_quaternions(parent_quats, child_quats)
    reconstructed = reconstruct_child_global(parent_quats, relative)
    errors = angular_error_degrees(child_quats, reconstructed)
    stats = summarize_reconstruction_errors(errors)
    status = thresholds.classify_max_error(stats["max_error_deg"])
    result = LinkReconstructionResult(
        joint_id=joint_id,
        source_parent_bone=source_parent_bone,
        source_child_bone=source_child_bone,
        parent_bone=parent_bone,
        child_bone=child_bone,
        is_root_anchor_link=is_root_anchor_link,
        included_in_v0=included_in_v0,
        selection_status=selection_status,
        requires_manual_review=requires_manual_review,
        frame_count=len(errors),
        mean_error_deg=stats["mean_error_deg"],
        median_error_deg=stats["median_error_deg"],
        max_error_deg=stats["max_error_deg"],
        p99_error_deg=stats["p99_error_deg"],
        reconstruction_status=status,
    )
    return result, relative


def process_relative_sign_continuity(
    *,
    joint_id: str,
    source_parent_bone: str,
    source_child_bone: str,
    parent_bone: str,
    child_bone: str,
    relative_quats: np.ndarray,
    thresholds: SignContinuityThresholds | None = None,
    apply_correction: bool = True,
) -> tuple[np.ndarray, np.ndarray, RelativeSignContinuityResult]:
    """Analyze (and optionally correct) relative quaternion sign continuity per link."""
    thresholds = thresholds or SignContinuityThresholds()
    raw_dots = consecutive_dot_products(relative_quats)
    raw_flip_count = int(np.sum(raw_dots < 0.0)) if raw_dots.size else 0
    min_raw_dot = float(np.min(raw_dots)) if raw_dots.size else None

    corrected = relative_quats.copy()
    flip_mask = np.zeros(len(relative_quats), dtype=bool)
    if apply_correction:
        corrected, flip_mask = apply_sign_continuity(relative_quats)

    corrected_dots = consecutive_dot_products(corrected)
    corrected_flip_count = int(np.sum(corrected_dots < 0.0)) if corrected_dots.size else 0
    valid, min_corrected_dot = validate_post_correction_dots(corrected, thresholds=thresholds)

    result = RelativeSignContinuityResult(
        joint_id=joint_id,
        source_parent_bone=source_parent_bone,
        source_child_bone=source_child_bone,
        parent_bone=parent_bone,
        child_bone=child_bone,
        total_frames=len(relative_quats),
        raw_sign_flip_count=raw_flip_count,
        corrected_sign_flip_count=corrected_flip_count,
        min_raw_consecutive_dot=min_raw_dot,
        min_corrected_consecutive_dot=min_corrected_dot,
        post_correction_valid=valid,
        correction_applied=apply_correction and raw_flip_count > 0,
    )
    return corrected, flip_mask, result


def load_stage05_global_quaternions(stage05_dir: Path) -> pd.DataFrame:
    parquet_path = stage05_dir / "global_quaternions_sign_continuous.parquet"
    csv_path = stage05_dir / "global_quaternions_sign_continuous.csv"
    if parquet_path.exists():
        return pd.read_parquet(parquet_path)
    if csv_path.exists():
        return pd.read_csv(csv_path)
    raise FileNotFoundError(
        "Stage 05 sign-continuous global quaternion table not found "
        f"(expected {parquet_path} or {csv_path})"
    )


def load_stage01_joint_maps(stage01_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    candidate_path = stage01_dir / "candidate_joint_map.csv"
    selected_path = stage01_dir / "selected_joint_map_v0.csv"
    if not candidate_path.exists():
        raise FileNotFoundError(f"Stage 01 candidate_joint_map.csv not found at {candidate_path}")
    candidate = pd.read_csv(candidate_path)
    if selected_path.exists():
        selected = pd.read_csv(selected_path)
    else:
        selected = candidate.copy()
        selected["selection_status"] = "provisional_v0"
        selected["frozen"] = False
        selected["included_in_v0"] = candidate["included"]
    return candidate, selected


def _is_root_anchor_link(row: pd.Series) -> bool:
    if str(row.get("exclusion_reason", "")) == "parent_is_root":
        return True
    parent = str(row.get("parent_bone", ""))
    source_parent = str(row.get("source_parent_bone", ""))
    return parent == "Root" or source_parent == "Root"


def link_reconstruction_to_row(result: LinkReconstructionResult) -> dict[str, Any]:
    return {
        "joint_id": result.joint_id,
        "source_parent_bone": result.source_parent_bone,
        "source_child_bone": result.source_child_bone,
        "parent_bone": result.parent_bone,
        "child_bone": result.child_bone,
        "is_root_anchor_link": result.is_root_anchor_link,
        "included_in_v0": result.included_in_v0,
        "selection_status": result.selection_status,
        "requires_manual_review": result.requires_manual_review,
        "frame_count": result.frame_count,
        "mean_error_deg": result.mean_error_deg,
        "median_error_deg": result.median_error_deg,
        "max_error_deg": result.max_error_deg,
        "p99_error_deg": result.p99_error_deg,
        "reconstruction_status": result.reconstruction_status.value,
        "missing_reason": result.missing_reason,
    }


def sign_continuity_to_row(result: RelativeSignContinuityResult) -> dict[str, Any]:
    return {
        "joint_id": result.joint_id,
        "source_parent_bone": result.source_parent_bone,
        "source_child_bone": result.source_child_bone,
        "parent_bone": result.parent_bone,
        "child_bone": result.child_bone,
        "total_frames": result.total_frames,
        "raw_sign_flip_count": result.raw_sign_flip_count,
        "corrected_sign_flip_count": result.corrected_sign_flip_count,
        "min_raw_consecutive_dot": result.min_raw_consecutive_dot,
        "min_corrected_consecutive_dot": result.min_corrected_consecutive_dot,
        "post_correction_valid": result.post_correction_valid,
        "correction_applied": result.correction_applied,
    }


def file_summary_row(result: FileRelativeRotationResult) -> dict[str, Any]:
    return {
        "input_file": result.input_file,
        "parent_child_links_processed": result.parent_child_links_processed,
        "parent_child_links_missing": result.parent_child_links_missing,
        "total_frames": result.total_frames,
        "global_max_reconstruction_error_deg": result.global_max_reconstruction_error_deg,
        "links_pass": result.links_pass,
        "links_warning": result.links_warning,
        "links_fail": result.links_fail,
        "total_relative_sign_flips_raw": result.total_relative_sign_flips_raw,
        "total_relative_sign_flips_corrected": result.total_relative_sign_flips_corrected,
        "relative_sign_continuity_valid": result.relative_sign_continuity_valid,
        "stage07_may_proceed": result.stage07_may_proceed,
        "fail_reasons": "; ".join(result.fail_reasons),
        "warning_reasons": "; ".join(result.warning_reasons),
    }


def build_relative_quaternion_table(
    *,
    frame_series: np.ndarray,
    time_series: np.ndarray,
    link_rows: list[dict[str, Any]],
) -> pd.DataFrame:
    if not link_rows:
        return pd.DataFrame(
            columns=[
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
        )
    return pd.DataFrame(link_rows)


def process_file_relative_rotations(
    *,
    input_file: str,
    global_quats: pd.DataFrame,
    candidate_joints: pd.DataFrame,
    selected_joints: pd.DataFrame,
    reconstruction_thresholds: ReconstructionThresholds,
    sign_thresholds: SignContinuityThresholds,
    apply_relative_sign_correction: bool = True,
) -> tuple[FileRelativeRotationResult, pd.DataFrame]:
    """Compute relative quaternions for all native parent-child links with available data."""
    selected_lookup = selected_joints.set_index("joint_id", drop=False)
    bones_available = set(global_quats["source_bone_name"].unique())

    frame_time = global_quats.loc[:, ["frame", "time"]].copy()
    pivot_frames = (
        frame_time.drop_duplicates(subset=["frame"])
        .sort_values("frame")
        .reset_index(drop=True)
    )
    frame_series = pivot_frames["frame"].to_numpy()
    time_series = pivot_frames["time"].to_numpy()
    total_frames = len(frame_series)

    quat_by_bone: dict[str, pd.DataFrame] = {}
    for source_bone, group in global_quats.groupby("source_bone_name", sort=True):
        bone_key = str(source_bone)
        ordered = group.sort_values("frame").reset_index(drop=True)
        quat_by_bone[bone_key] = ordered

    link_results: list[LinkReconstructionResult] = []
    sign_results: list[RelativeSignContinuityResult] = []
    missing_links: list[dict[str, Any]] = []
    table_rows: list[dict[str, Any]] = []
    fail_reasons: list[str] = []
    warning_reasons: list[str] = []

    for _, row in candidate_joints.iterrows():
        joint_id = str(row["joint_id"])
        source_parent = str(row["source_parent_bone"])
        source_child = str(row["source_child_bone"])
        parent_bone = str(row["parent_bone"])
        child_bone = str(row["child_bone"])
        is_root_anchor = _is_root_anchor_link(row)

        sel = selected_lookup.loc[joint_id] if joint_id in selected_lookup.index else row
        included_in_v0 = bool(sel.get("included_in_v0", row.get("included", False)))
        selection_status = str(sel.get("selection_status", "provisional_v0"))
        requires_review = bool(
            sel.get("requires_manual_review", row.get("requires_manual_review", False))
        )

        missing_parts: list[str] = []
        if source_parent not in bones_available and source_parent != "Root":
            missing_parts.append(f"parent quaternion missing ({source_parent})")
        if source_child not in bones_available:
            missing_parts.append(f"child quaternion missing ({source_child})")
        if source_parent == "Root" or parent_bone == "Root":
            missing_parts.append("parent is Root anchor (no global quaternion expected)")

        if missing_parts:
            missing_links.append(
                {
                    "joint_id": joint_id,
                    "source_parent_bone": source_parent,
                    "source_child_bone": source_child,
                    "parent_bone": parent_bone,
                    "child_bone": child_bone,
                    "is_root_anchor_link": is_root_anchor,
                    "missing_reason": "; ".join(missing_parts),
                }
            )
            continue

        parent_df = quat_by_bone[source_parent]
        child_df = quat_by_bone[source_child]
        if len(parent_df) != total_frames or len(child_df) != total_frames:
            missing_links.append(
                {
                    "joint_id": joint_id,
                    "source_parent_bone": source_parent,
                    "source_child_bone": source_child,
                    "parent_bone": parent_bone,
                    "child_bone": child_bone,
                    "is_root_anchor_link": is_root_anchor,
                    "missing_reason": "frame count mismatch between parent and child",
                }
            )
            continue

        parent_quats = parent_df[["qx", "qy", "qz", "qw"]].to_numpy(dtype=float)
        child_quats = child_df[["qx", "qy", "qz", "qw"]].to_numpy(dtype=float)

        link_result, relative_raw = validate_link_reconstruction(
            joint_id=joint_id,
            source_parent_bone=source_parent,
            source_child_bone=source_child,
            parent_bone=parent_bone,
            child_bone=child_bone,
            is_root_anchor_link=is_root_anchor,
            included_in_v0=included_in_v0,
            selection_status=selection_status,
            requires_manual_review=requires_review,
            parent_quats=parent_quats,
            child_quats=child_quats,
            thresholds=reconstruction_thresholds,
        )
        link_results.append(link_result)

        if link_result.reconstruction_status == ReconstructionStatus.FAIL:
            fail_reasons.append(
                f"{joint_id} ({parent_bone}→{child_bone}): max error "
                f"{link_result.max_error_deg:.6g} deg"
            )
        elif link_result.reconstruction_status == ReconstructionStatus.WARNING:
            warning_reasons.append(
                f"{joint_id} ({parent_bone}→{child_bone}): max error "
                f"{link_result.max_error_deg:.6g} deg"
            )

        corrected, flip_mask, sign_result = process_relative_sign_continuity(
            joint_id=joint_id,
            source_parent_bone=source_parent,
            source_child_bone=source_child,
            parent_bone=parent_bone,
            child_bone=child_bone,
            relative_quats=relative_raw,
            thresholds=sign_thresholds,
            apply_correction=apply_relative_sign_correction,
        )
        sign_results.append(sign_result)
        if sign_result.raw_sign_flip_count > 0 and apply_relative_sign_correction:
            warning_reasons.append(
                f"{joint_id}: {sign_result.raw_sign_flip_count} raw relative sign flips "
                "corrected (documented second-pass sign continuity)"
            )
        if not sign_result.post_correction_valid:
            fail_reasons.append(
                f"{joint_id}: relative sign continuity invalid after correction "
                f"(min dot={sign_result.min_corrected_consecutive_dot})"
            )

        for frame_idx in range(total_frames):
            table_rows.append(
                {
                    "frame": int(frame_series[frame_idx]),
                    "time": float(time_series[frame_idx]),
                    "joint_id": joint_id,
                    "source_parent_bone": source_parent,
                    "source_child_bone": source_child,
                    "parent_bone": parent_bone,
                    "child_bone": child_bone,
                    "is_root_anchor_link": is_root_anchor,
                    "included_in_v0": included_in_v0,
                    "selection_status": selection_status,
                    "requires_manual_review": requires_review,
                    "qx": corrected[frame_idx, 0],
                    "qy": corrected[frame_idx, 1],
                    "qz": corrected[frame_idx, 2],
                    "qw": corrected[frame_idx, 3],
                    "relative_flip_applied": bool(flip_mask[frame_idx]),
                }
            )

    if not link_results and candidate_joints.empty:
        fail_reasons.append("No candidate parent-child links found in Stage 01 map")

    global_max_error = max((item.max_error_deg for item in link_results), default=0.0)
    links_pass = sum(
        1 for item in link_results if item.reconstruction_status == ReconstructionStatus.PASS
    )
    links_warning = sum(
        1 for item in link_results if item.reconstruction_status == ReconstructionStatus.WARNING
    )
    links_fail = sum(
        1 for item in link_results if item.reconstruction_status == ReconstructionStatus.FAIL
    )
    total_raw_flips = sum(item.raw_sign_flip_count for item in sign_results)
    total_corrected_flips = sum(item.corrected_sign_flip_count for item in sign_results)
    sign_valid = all(item.post_correction_valid for item in sign_results) if sign_results else True

    reconstruction_ok = global_max_error <= reconstruction_thresholds.warning_max_error_deg
    stage07_may_proceed = reconstruction_ok and sign_valid and not fail_reasons

    file_result = FileRelativeRotationResult(
        input_file=input_file,
        parent_child_links_processed=len(link_results),
        parent_child_links_missing=len(missing_links),
        total_frames=total_frames,
        global_max_reconstruction_error_deg=global_max_error,
        links_pass=links_pass,
        links_warning=links_warning,
        links_fail=links_fail,
        total_relative_sign_flips_raw=total_raw_flips,
        total_relative_sign_flips_corrected=total_corrected_flips,
        relative_sign_continuity_valid=sign_valid,
        stage07_may_proceed=stage07_may_proceed,
        link_results=link_results,
        sign_continuity_results=sign_results,
        missing_links=missing_links,
        fail_reasons=fail_reasons,
        warning_reasons=warning_reasons,
    )

    relative_table = build_relative_quaternion_table(
        frame_series=frame_series,
        time_series=time_series,
        link_rows=table_rows,
    )
    return file_result, relative_table
