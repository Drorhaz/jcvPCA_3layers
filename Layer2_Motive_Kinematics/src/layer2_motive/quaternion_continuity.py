"""Global quaternion sign-continuity correction helpers (Stage 05)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

DEFAULT_MIN_CONSECUTIVE_DOT = -1e-12


@dataclass(frozen=True)
class SignContinuityThresholds:
    """Validation thresholds for post-correction sign continuity."""

    min_consecutive_dot: float = DEFAULT_MIN_CONSECUTIVE_DOT


@dataclass
class BoneSignContinuityResult:
    source_bone_name: str
    canonical_bone_name: str
    total_frames: int
    sign_flip_count: int
    bones_with_zero_flips: bool
    min_consecutive_dot: float | None
    post_correction_valid: bool
    flip_frame_indices: list[int] = field(default_factory=list)
    flip_frames: list[int | None] = field(default_factory=list)


@dataclass
class FileSignContinuityResult:
    input_file: str
    quaternion_group_count: int
    total_frames: int
    total_sign_flips: int
    max_sign_flips_any_bone: int
    bones_with_zero_flips: int
    min_consecutive_dot_observed: float | None
    post_correction_valid: bool
    stage06_may_proceed: bool
    bone_results: list[BoneSignContinuityResult]
    fail_reasons: list[str] = field(default_factory=list)
    warning_reasons: list[str] = field(default_factory=list)


def apply_sign_continuity(quats: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Correct quaternion sign flips along time; returns corrected quats and flip mask."""
    if quats.ndim != 2 or quats.shape[1] != 4:
        raise ValueError("quats must have shape (n, 4)")

    corrected = quats.copy()
    flip_mask = np.zeros(len(quats), dtype=bool)
    for index in range(1, len(quats)):
        dot = float(np.dot(corrected[index], corrected[index - 1]))
        if dot < 0.0:
            corrected[index] = -corrected[index]
            flip_mask[index] = True
    return corrected, flip_mask


def consecutive_dot_products(quats: np.ndarray) -> np.ndarray:
    """Dot products between consecutive corrected quaternion rows."""
    if len(quats) < 2:
        return np.array([], dtype=float)
    return np.sum(quats[1:] * quats[:-1], axis=1)


def validate_post_correction_dots(
    quats: np.ndarray,
    *,
    thresholds: SignContinuityThresholds | None = None,
) -> tuple[bool, float | None]:
    thresholds = thresholds or SignContinuityThresholds()
    dots = consecutive_dot_products(quats)
    if dots.size == 0:
        return True, None
    min_dot = float(np.min(dots))
    return min_dot >= thresholds.min_consecutive_dot, min_dot


def process_bone_sign_continuity(
    *,
    source_bone_name: str,
    canonical_bone_name: str,
    quats: np.ndarray,
    frame_series: pd.Series | None,
    thresholds: SignContinuityThresholds | None = None,
) -> tuple[np.ndarray, np.ndarray, BoneSignContinuityResult]:
    thresholds = thresholds or SignContinuityThresholds()
    corrected, flip_mask = apply_sign_continuity(quats)
    valid, min_dot = validate_post_correction_dots(corrected, thresholds=thresholds)
    flip_indices = np.flatnonzero(flip_mask).astype(int).tolist()
    flip_frames: list[int | None] = []
    if frame_series is not None:
        for idx in flip_indices:
            value = frame_series.iloc[idx]
            flip_frames.append(int(value) if pd.notna(value) else None)
    else:
        flip_frames = [None] * len(flip_indices)

    bone_result = BoneSignContinuityResult(
        source_bone_name=source_bone_name,
        canonical_bone_name=canonical_bone_name,
        total_frames=len(quats),
        sign_flip_count=len(flip_indices),
        bones_with_zero_flips=len(flip_indices) == 0,
        min_consecutive_dot=min_dot,
        post_correction_valid=valid,
        flip_frame_indices=flip_indices,
        flip_frames=flip_frames,
    )
    return corrected, flip_mask, bone_result


def bone_result_to_row(result: BoneSignContinuityResult) -> dict[str, Any]:
    return {
        "source_bone_name": result.source_bone_name,
        "canonical_bone_name": result.canonical_bone_name,
        "total_frames": result.total_frames,
        "sign_flip_count": result.sign_flip_count,
        "min_consecutive_dot": result.min_consecutive_dot,
        "post_correction_valid": result.post_correction_valid,
    }


def file_summary_row(result: FileSignContinuityResult) -> dict[str, Any]:
    return {
        "input_file": result.input_file,
        "quaternion_group_count": result.quaternion_group_count,
        "total_frames": result.total_frames,
        "total_sign_flips": result.total_sign_flips,
        "max_sign_flips_any_bone": result.max_sign_flips_any_bone,
        "bones_with_zero_flips": result.bones_with_zero_flips,
        "min_consecutive_dot_observed": result.min_consecutive_dot_observed,
        "post_correction_valid": result.post_correction_valid,
        "stage06_may_proceed": result.stage06_may_proceed,
        "fail_reasons": "; ".join(result.fail_reasons),
        "warning_reasons": "; ".join(result.warning_reasons),
    }


def flip_frames_to_dataframe(bone_results: list[BoneSignContinuityResult]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for bone in bone_results:
        for row_index, frame in zip(bone.flip_frame_indices, bone.flip_frames, strict=True):
            rows.append(
                {
                    "source_bone_name": bone.source_bone_name,
                    "canonical_bone_name": bone.canonical_bone_name,
                    "row_index": row_index,
                    "frame": frame,
                }
            )
    if not rows:
        return pd.DataFrame(
            columns=["source_bone_name", "canonical_bone_name", "row_index", "frame"]
        )
    return pd.DataFrame(rows)


def build_long_format_table(
    *,
    frame_series: pd.Series,
    time_series: pd.Series,
    bone_quaternions: dict[str, tuple[str, np.ndarray, np.ndarray]],
) -> pd.DataFrame:
    """Build long-format sign-continuous quaternion table."""
    chunks: list[pd.DataFrame] = []
    for source_bone_name, (canonical_name, corrected, flip_mask) in sorted(
        bone_quaternions.items()
    ):
        chunk = pd.DataFrame(
            {
                "frame": frame_series.to_numpy(),
                "time": time_series.to_numpy(),
                "source_bone_name": source_bone_name,
                "canonical_bone_name": canonical_name,
                "qx": corrected[:, 0],
                "qy": corrected[:, 1],
                "qz": corrected[:, 2],
                "qw": corrected[:, 3],
                "flip_applied": flip_mask.astype(bool),
            }
        )
        chunks.append(chunk)
    if not chunks:
        return pd.DataFrame(
            columns=[
                "frame",
                "time",
                "source_bone_name",
                "canonical_bone_name",
                "qx",
                "qy",
                "qz",
                "qw",
                "flip_applied",
            ]
        )
    return pd.concat(chunks, ignore_index=True)


def thresholds_from_config(config: dict[str, Any]) -> SignContinuityThresholds:
    section = config.get("sign_continuity", {})
    if not isinstance(section, dict):
        return SignContinuityThresholds()
    return SignContinuityThresholds(
        min_consecutive_dot=float(
            section.get("min_consecutive_dot", DEFAULT_MIN_CONSECUTIVE_DOT)
        )
    )
