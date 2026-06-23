"""Butterworth filtering, jump-context flagging, and analysis eligibility (Stage 08 V1)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.signal import butter, sosfiltfilt

from layer2_motive.config import load_config
from layer2_motive.rotvec import RotVecThresholds, load_thresholds
from layer2_motive.validation import HardStopError


class FilterLinkStatus(str, Enum):
    PASS = "pass"
    PASS_WITH_WARNING = "pass_with_warning"
    FILTERED_BUT_JUMP_CONTEXT_FLAGGED = "filtered_but_jump_context_flagged"
    # Backward-compatible alias for readers expecting the pre-contract-revision name.
    FILTERED_BUT_JUMP_CONTEXT_MASKED = "filtered_but_jump_context_flagged"
    PROVISIONAL_MANUAL_REVIEW = "provisional_manual_review"
    EXCLUDED_FROM_ANALYSIS = "excluded_from_analysis"
    BLOCKED_NEEDS_REVIEW = "blocked_needs_review"
    FAIL = "fail"


class OutputScope(str, Enum):
    NATIVE_FILTERED_ARCHIVE = "native_filtered_archive"
    ANALYSIS_CLEAN_CORE = "analysis_clean_core"
    REVIEW_PROVISIONAL = "review_provisional"
    EXCLUDED_FROM_ANALYSIS = "excluded_from_analysis"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class FilteringConfig:
    cutoff_hz: float
    filter_order: int
    filter_type: str
    nyquist_safety_factor: float
    jump_context_window_frames: int

    @property
    def max_cutoff_hz(self) -> float:
        raise RuntimeError("max_cutoff_hz requires sampling_rate_hz")


def filtering_config_from_dict(section: dict[str, Any]) -> FilteringConfig:
    return FilteringConfig(
        cutoff_hz=float(section.get("cutoff_hz", 10.0)),
        filter_order=int(section.get("filter_order", 4)),
        filter_type=str(section.get("filter_type", "butterworth")),
        nyquist_safety_factor=float(section.get("nyquist_safety_factor", 0.45)),
        jump_context_window_frames=int(section.get("jump_context_window_frames", 30)),
    )


def load_filtering_config(config_path: Path | None = None) -> FilteringConfig:
    config = load_config(config_path)
    section = config.get("filtering", {})
    return filtering_config_from_dict(section)


def validate_cutoff_hz(
    cutoff_hz: float,
    sampling_rate_hz: float,
    *,
    nyquist_safety_factor: float = 0.45,
) -> None:
    max_cutoff = nyquist_safety_factor * sampling_rate_hz
    if cutoff_hz >= max_cutoff:
        raise HardStopError(
            f"Filter cutoff {cutoff_hz} Hz must be < {nyquist_safety_factor} * "
            f"sampling_rate ({max_cutoff} Hz at {sampling_rate_hz} Hz)"
        )
    if cutoff_hz <= 0:
        raise HardStopError(f"Filter cutoff must be positive, got {cutoff_hz}")


def min_filtfilt_length(sos: np.ndarray) -> int:
    """Minimum signal length required by scipy.signal.sosfiltfilt."""
    n_sections = sos.shape[0]
    padlen = 3 * (2 * n_sections - 1)
    return padlen + 1


def design_butterworth_sos(
    cutoff_hz: float,
    sampling_rate_hz: float,
    order: int,
) -> np.ndarray:
    if order < 1:
        raise HardStopError(f"Filter order must be >= 1, got {order}")
    wn = cutoff_hz / (sampling_rate_hz / 2.0)
    sos = butter(order, wn, btype="low", output="sos")
    return np.asarray(sos, dtype=float)


def _contiguous_true_segments(mask: np.ndarray) -> list[tuple[int, int]]:
    segments: list[tuple[int, int]] = []
    start: int | None = None
    for idx, value in enumerate(mask):
        if value and start is None:
            start = idx
        elif not value and start is not None:
            segments.append((start, idx))
            start = None
    if start is not None:
        segments.append((start, len(mask)))
    return segments


def filter_axis_sos_no_nans(signal: np.ndarray, sos: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Apply sosfiltfilt on finite contiguous segments; never pass NaNs to sosfiltfilt."""
    signal = np.asarray(signal, dtype=float)
    out = np.full(signal.shape, np.nan, dtype=float)
    applied = np.zeros(signal.shape, dtype=bool)
    finite = np.isfinite(signal)
    min_len = min_filtfilt_length(sos)

    for start, end in _contiguous_true_segments(finite):
        segment = signal[start:end]
        if np.any(~np.isfinite(segment)):
            continue
        if len(segment) < min_len:
            continue
        filtered = sosfiltfilt(sos, segment)
        out[start:end] = filtered
        applied[start:end] = True

    return out, applied


def filter_rotvec_components(
    components: np.ndarray,
    sos: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Filter rx/ry/rz columns; return filtered array and per-row applied mask."""
    components = np.asarray(components, dtype=float)
    if components.ndim != 2 or components.shape[1] != 3:
        raise ValueError("components must have shape (n_frames, 3)")

    row_finite = np.all(np.isfinite(components), axis=1)
    out = np.full_like(components, np.nan)
    applied = np.zeros(len(components), dtype=bool)
    min_len = min_filtfilt_length(sos)

    for start, end in _contiguous_true_segments(row_finite):
        segment = components[start:end]
        if segment.shape[0] < min_len:
            continue
        for axis in range(3):
            axis_signal = segment[:, axis]
            if np.any(~np.isfinite(axis_signal)):
                continue
            out[start:end, axis] = sosfiltfilt(sos, axis_signal)
        applied[start:end] = True

    return out, applied


def identify_stage07_jump_event_frames(
    frames: np.ndarray,
    jump_magnitude: np.ndarray,
    jump_from_previous: np.ndarray,
    thresholds: RotVecThresholds,
) -> np.ndarray:
    """Return frame indices where Stage 07 jump warning/fail transitions occur."""
    event_mask = jump_from_previous & (jump_magnitude > thresholds.jump_warning_rad)
    return frames[event_mask]


def identify_branch_cut_near_pi_frames(
    frames: np.ndarray,
    rotvec_norm: np.ndarray,
    thresholds: RotVecThresholds,
) -> np.ndarray:
    """Return frames where rotvec_norm exceeds the Stage 07 branch-cut warning threshold."""
    finite = np.isfinite(rotvec_norm)
    event_mask = finite & (rotvec_norm > thresholds.branch_cut_warning_rad)
    return frames[event_mask]


def compute_qc_context_arrays(
    frames: np.ndarray,
    event_frames: np.ndarray,
    *,
    context_window: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return event-frame flag, within-context flag, and distance to nearest event frame."""
    n = len(frames)
    is_event_frame = np.zeros(n, dtype=bool)
    within_context = np.zeros(n, dtype=bool)
    distance = np.full(n, np.inf, dtype=float)

    if event_frames.size == 0:
        return is_event_frame, within_context, distance

    for event_frame in event_frames:
        is_event_frame |= frames == event_frame

    for event_frame in event_frames:
        delta = np.abs(frames.astype(float) - float(event_frame))
        distance = np.minimum(distance, delta)
        within_context |= delta <= float(context_window)

    return is_event_frame, within_context, distance


def compute_jump_context_arrays(
    frames: np.ndarray,
    jump_event_frames: np.ndarray,
    *,
    context_window: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return jump-frame flag, within-context flag, and distance to nearest jump frame."""
    return compute_qc_context_arrays(
        frames,
        jump_event_frames,
        context_window=context_window,
    )


def _mask_reason_for_row(
    *,
    filter_applied: bool,
    in_jump_context: bool,
    in_branch_cut_context: bool,
    feature_scope: str,
    stage08_policy: str,
    requires_manual_review: bool,
) -> tuple[bool, str]:
    if in_jump_context:
        return False, "stage07_jump_context"
    if in_branch_cut_context:
        return False, "stage07_branch_cut_context"
    if feature_scope in {"excluded_distal", "excluded_toe"}:
        return False, "excluded_feature_scope"
    if stage08_policy == "excluded_from_analysis":
        return False, "excluded_from_analysis_policy"
    if stage08_policy == "block_filter":
        return False, "blocked_needs_review"
    if stage08_policy == "manual_review_required" or requires_manual_review:
        return False, "manual_review_provisional"
    if feature_scope == "review_provisional":
        return False, "manual_review_provisional"
    if not filter_applied:
        return False, "filter_not_applied"
    return True, ""


def _output_scope_for_row(
    *,
    analysis_eligible: bool,
    feature_scope: str,
    stage08_policy: str,
) -> str:
    if feature_scope in {"excluded_distal", "excluded_toe", "skipped"}:
        return OutputScope.EXCLUDED_FROM_ANALYSIS.value
    if stage08_policy in {"excluded_from_analysis"}:
        return OutputScope.EXCLUDED_FROM_ANALYSIS.value
    if stage08_policy == "block_filter":
        return OutputScope.BLOCKED.value
    if feature_scope == "review_provisional" or stage08_policy == "manual_review_required":
        return OutputScope.REVIEW_PROVISIONAL.value
    if analysis_eligible:
        return OutputScope.ANALYSIS_CLEAN_CORE.value
    if stage08_policy == "allow_filter_with_warning":
        return OutputScope.REVIEW_PROVISIONAL.value
    return OutputScope.NATIVE_FILTERED_ARCHIVE.value


def _link_filter_status(
    *,
    filter_applied_any: bool,
    filter_failed: bool,
    jump_context_rows: int,
    branch_cut_context_rows: int,
    feature_scope: str,
    stage08_policy: str,
    requires_manual_review: bool,
    stage07_jump_status: str,
    stage07_branch_cut_status: str,
) -> str:
    if filter_failed:
        return FilterLinkStatus.FAIL.value
    if feature_scope in {"excluded_distal", "excluded_toe", "skipped"}:
        return FilterLinkStatus.EXCLUDED_FROM_ANALYSIS.value
    if stage08_policy == "excluded_from_analysis":
        return FilterLinkStatus.EXCLUDED_FROM_ANALYSIS.value
    if stage08_policy == "block_filter":
        return FilterLinkStatus.BLOCKED_NEEDS_REVIEW.value
    if feature_scope == "review_provisional" or requires_manual_review:
        status = FilterLinkStatus.PROVISIONAL_MANUAL_REVIEW.value
    elif jump_context_rows > 0 or branch_cut_context_rows > 0:
        status = FilterLinkStatus.FILTERED_BUT_JUMP_CONTEXT_FLAGGED.value
    elif (
        stage07_jump_status == "warning"
        or stage07_branch_cut_status == "warning"
        or stage07_jump_status == "fail"
        or stage07_branch_cut_status == "fail"
        or stage08_policy == "allow_filter_with_warning"
    ):
        status = FilterLinkStatus.PASS_WITH_WARNING.value
    elif filter_applied_any:
        status = FilterLinkStatus.PASS.value
    else:
        status = FilterLinkStatus.FAIL.value
    return status


@dataclass
class LinkFilterResult:
    joint_id: str
    parent_canonical: str
    child_canonical: str
    feature_scope: str
    stage08_policy: str
    stage07_jump_status: str
    stage07_branch_cut_status: str
    total_frames: int
    filter_applied_frames: int
    jump_event_frames: int
    jump_context_frames: int
    branch_cut_event_frames: int
    branch_cut_context_frames: int
    analysis_eligible_frames: int
    filter_status: str
    cutoff_hz: float
    filter_order: int
    sampling_rate_hz: float
    min_filtfilt_length: int
    notes: str


def process_link_filtering(
    link_df: pd.DataFrame,
    *,
    sos: np.ndarray,
    filtering_config: FilteringConfig,
    rotvec_thresholds: RotVecThresholds,
    sampling_rate_hz: float,
) -> tuple[pd.DataFrame, LinkFilterResult, list[dict[str, Any]], list[dict[str, Any]]]:
    ordered = link_df.sort_values("frame").reset_index(drop=True)
    frames = ordered["frame"].to_numpy(dtype=int)
    raw = ordered[["rx", "ry", "rz"]].to_numpy(dtype=float)

    filtered, applied = filter_rotvec_components(raw, sos)
    filtered_norm = np.linalg.norm(filtered, axis=1)

    jump_events = identify_stage07_jump_event_frames(
        frames=frames,
        jump_magnitude=ordered["stage07_jump_magnitude_rad"].to_numpy(dtype=float),
        jump_from_previous=ordered["stage07_jump_from_previous_frame"].to_numpy(dtype=bool),
        thresholds=rotvec_thresholds,
    )
    is_jump, in_jump_context, jump_distance = compute_jump_context_arrays(
        frames,
        jump_events,
        context_window=filtering_config.jump_context_window_frames,
    )

    rotvec_norm_raw = ordered["rotvec_norm"].to_numpy(dtype=float)
    branch_cut_events = identify_branch_cut_near_pi_frames(
        frames=frames,
        rotvec_norm=rotvec_norm_raw,
        thresholds=rotvec_thresholds,
    )
    is_branch_cut, in_branch_cut_context, branch_cut_distance = compute_qc_context_arrays(
        frames,
        branch_cut_events,
        context_window=filtering_config.jump_context_window_frames,
    )

    joint_id = str(ordered["link_id"].iloc[0])
    feature_scope = str(ordered["feature_scope"].iloc[0])
    stage08_policy = str(ordered["stage08_policy"].iloc[0])
    requires_manual_review = bool(ordered["requires_manual_review"].iloc[0])
    stage07_jump_status = str(ordered["stage07_jump_status"].iloc[0])
    stage07_branch_cut_status = str(ordered["stage07_branch_cut_status"].iloc[0])

    analysis_eligible = np.zeros(len(ordered), dtype=bool)
    mask_reasons: list[str] = []
    output_scopes: list[str] = []

    for idx in range(len(ordered)):
        eligible, reason = _mask_reason_for_row(
            filter_applied=bool(applied[idx]),
            in_jump_context=bool(in_jump_context[idx]),
            in_branch_cut_context=bool(in_branch_cut_context[idx]),
            feature_scope=feature_scope,
            stage08_policy=stage08_policy,
            requires_manual_review=requires_manual_review,
        )
        analysis_eligible[idx] = eligible
        mask_reasons.append(reason)
        output_scopes.append(
            _output_scope_for_row(
                analysis_eligible=eligible,
                feature_scope=feature_scope,
                stage08_policy=stage08_policy,
            )
        )

    # Analysis columns mirror native filtered values. QC/risk is expressed via flags and
    # reports; NaNs appear only when filtering genuinely failed (filter_not_applied).
    analysis_filtered = filtered.copy()
    analysis_norm = filtered_norm.copy()

    filter_failed = bool(np.all(~applied) and np.any(np.all(np.isfinite(raw), axis=1)))
    link_status = _link_filter_status(
        filter_applied_any=bool(applied.any()),
        filter_failed=filter_failed,
        jump_context_rows=int(in_jump_context.sum()),
        branch_cut_context_rows=int(in_branch_cut_context.sum()),
        feature_scope=feature_scope,
        stage08_policy=stage08_policy,
        requires_manual_review=requires_manual_review,
        stage07_jump_status=stage07_jump_status,
        stage07_branch_cut_status=stage07_branch_cut_status,
    )

    out = ordered.copy()
    out = out.rename(
        columns={
            "rx": "rx_raw",
            "ry": "ry_raw",
            "rz": "rz_raw",
            "rotvec_norm": "rotvec_norm_raw",
        }
    )
    out["rx_filtered_native"] = filtered[:, 0]
    out["ry_filtered_native"] = filtered[:, 1]
    out["rz_filtered_native"] = filtered[:, 2]
    out["rotvec_norm_filtered_native"] = filtered_norm
    out["rx_filtered_analysis"] = analysis_filtered[:, 0]
    out["ry_filtered_analysis"] = analysis_filtered[:, 1]
    out["rz_filtered_analysis"] = analysis_filtered[:, 2]
    out["rotvec_norm_filtered_analysis"] = analysis_norm
    out["stage08_filter_applied"] = applied
    out["stage08_filter_status"] = link_status
    out["stage08_stage07_jump_frame"] = is_jump
    out["stage08_within_jump_context_window"] = in_jump_context
    out["stage08_distance_to_nearest_stage07_jump_frame"] = jump_distance
    out["stage08_branch_cut_event_frame"] = is_branch_cut
    out["stage08_within_branch_cut_context_window"] = in_branch_cut_context
    out["stage08_distance_to_nearest_branch_cut_frame"] = branch_cut_distance
    out["stage08_analysis_eligible"] = analysis_eligible
    out["stage08_mask_reason"] = mask_reasons
    out["stage08_output_scope"] = output_scopes

    jump_report_rows: list[dict[str, Any]] = []
    for jump_frame in jump_events:
        jump_report_rows.append(
            {
                "link_id": joint_id,
                "parent_canonical": str(ordered["parent_canonical"].iloc[0]),
                "child_canonical": str(ordered["child_canonical"].iloc[0]),
                "jump_event_frame": int(jump_frame),
                "context_window_frames": filtering_config.jump_context_window_frames,
                "context_start_frame": int(
                    jump_frame - filtering_config.jump_context_window_frames
                ),
                "context_end_frame": int(jump_frame + filtering_config.jump_context_window_frames),
                "stage07_jump_magnitude_rad": float(
                    ordered.loc[ordered["frame"] == jump_frame, "stage07_jump_magnitude_rad"].iloc[
                        0
                    ]
                ),
                "stage07_row_qc_status": str(
                    ordered.loc[ordered["frame"] == jump_frame, "stage07_row_qc_status"].iloc[0]
                ),
            }
        )

    branch_cut_report_rows: list[dict[str, Any]] = []
    for event_frame in branch_cut_events:
        branch_cut_report_rows.append(
            {
                "link_id": joint_id,
                "parent_canonical": str(ordered["parent_canonical"].iloc[0]),
                "child_canonical": str(ordered["child_canonical"].iloc[0]),
                "branch_cut_event_frame": int(event_frame),
                "context_window_frames": filtering_config.jump_context_window_frames,
                "context_start_frame": int(
                    event_frame - filtering_config.jump_context_window_frames
                ),
                "context_end_frame": int(
                    event_frame + filtering_config.jump_context_window_frames
                ),
                "rotvec_norm_raw": float(
                    ordered.loc[ordered["frame"] == event_frame, "rotvec_norm"].iloc[0]
                ),
                "stage07_branch_cut_status": stage07_branch_cut_status,
            }
        )

    link_result = LinkFilterResult(
        joint_id=joint_id,
        parent_canonical=str(ordered["parent_canonical"].iloc[0]),
        child_canonical=str(ordered["child_canonical"].iloc[0]),
        feature_scope=feature_scope,
        stage08_policy=stage08_policy,
        stage07_jump_status=stage07_jump_status,
        stage07_branch_cut_status=stage07_branch_cut_status,
        total_frames=len(ordered),
        filter_applied_frames=int(applied.sum()),
        jump_event_frames=int(len(jump_events)),
        jump_context_frames=int(in_jump_context.sum()),
        branch_cut_event_frames=int(len(branch_cut_events)),
        branch_cut_context_frames=int(in_branch_cut_context.sum()),
        analysis_eligible_frames=int(analysis_eligible.sum()),
        filter_status=link_status,
        cutoff_hz=filtering_config.cutoff_hz,
        filter_order=filtering_config.filter_order,
        sampling_rate_hz=sampling_rate_hz,
        min_filtfilt_length=min_filtfilt_length(sos),
        notes="",
    )
    return out, link_result, jump_report_rows, branch_cut_report_rows


@dataclass
class FileFilterResult:
    links_processed: int
    links_pass: int
    links_with_jump_context: int
    links_excluded: int
    links_blocked: int
    links_review: int
    total_jump_event_frames: int
    total_jump_context_frames: int
    total_branch_cut_event_frames: int
    total_branch_cut_context_frames: int
    total_analysis_eligible_frames: int
    cutoff_hz: float
    filter_order: float
    sampling_rate_hz: float
    filter_type: str
    jump_context_window_frames: int
    interpolation_applied: bool


def load_stage07_rotation_vectors(stage07_dir: Path) -> pd.DataFrame:
    parquet_path = stage07_dir / "relative_rotation_vectors.parquet"
    csv_path = stage07_dir / "relative_rotation_vectors.csv"
    if parquet_path.exists():
        return pd.read_parquet(parquet_path)
    if csv_path.exists():
        return pd.read_csv(csv_path)
    raise HardStopError(
        f"Stage 08 blocked: Stage 07 rotation vectors missing in {stage07_dir}"
    )


def process_file_filtering(
    *,
    stage07_table: pd.DataFrame,
    sampling_rate_hz: float,
    filtering_config: FilteringConfig | None = None,
    rotvec_thresholds: RotVecThresholds | None = None,
    config_path: Path | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, FileFilterResult]:
    filtering_config = filtering_config or load_filtering_config(config_path)
    rotvec_thresholds = rotvec_thresholds or load_thresholds(config_path)

    validate_cutoff_hz(
        filtering_config.cutoff_hz,
        sampling_rate_hz,
        nyquist_safety_factor=filtering_config.nyquist_safety_factor,
    )

    if filtering_config.filter_type.lower() != "butterworth":
        raise HardStopError(
            f"Stage 08 V1 supports butterworth filters only, got {filtering_config.filter_type!r}"
        )

    sos = design_butterworth_sos(
        filtering_config.cutoff_hz,
        sampling_rate_hz,
        filtering_config.filter_order,
    )

    filtered_frames: list[pd.DataFrame] = []
    summary_rows: list[dict[str, Any]] = []
    jump_rows: list[dict[str, Any]] = []
    branch_cut_rows: list[dict[str, Any]] = []
    diagnostic_rows: list[dict[str, Any]] = []

    for _link_id, group in stage07_table.groupby("link_id", sort=True):
        filtered_link, link_result, link_jump_rows, link_branch_cut_rows = process_link_filtering(
            group,
            sos=sos,
            filtering_config=filtering_config,
            rotvec_thresholds=rotvec_thresholds,
            sampling_rate_hz=sampling_rate_hz,
        )
        filtered_frames.append(filtered_link)
        summary_rows.append(
            {
                "link_id": link_result.joint_id,
                "parent_canonical": link_result.parent_canonical,
                "child_canonical": link_result.child_canonical,
                "feature_scope": link_result.feature_scope,
                "stage08_policy": link_result.stage08_policy,
                "stage07_jump_status": link_result.stage07_jump_status,
                "stage07_branch_cut_status": link_result.stage07_branch_cut_status,
                "total_frames": link_result.total_frames,
                "filter_applied_frames": link_result.filter_applied_frames,
                "jump_event_frames": link_result.jump_event_frames,
                "jump_context_frames": link_result.jump_context_frames,
                "branch_cut_event_frames": link_result.branch_cut_event_frames,
                "branch_cut_context_frames": link_result.branch_cut_context_frames,
                "analysis_eligible_frames": link_result.analysis_eligible_frames,
                "stage08_filter_status": link_result.filter_status,
                "cutoff_hz": link_result.cutoff_hz,
                "filter_order": link_result.filter_order,
                "sampling_rate_hz": link_result.sampling_rate_hz,
                "min_filtfilt_length": link_result.min_filtfilt_length,
            }
        )
        jump_rows.extend(link_jump_rows)
        branch_cut_rows.extend(link_branch_cut_rows)
        diagnostic_rows.append(
            {
                "link_id": link_result.joint_id,
                "finite_raw_frames": int(
                    np.sum(np.all(np.isfinite(group[["rx", "ry", "rz"]].to_numpy()), axis=1))
                ),
                "filter_applied_frames": link_result.filter_applied_frames,
                "native_finite_filtered_frames": int(
                    np.isfinite(filtered_link["rx_filtered_native"]).sum()
                ),
                "analysis_finite_filtered_frames": int(
                    np.isfinite(filtered_link["rx_filtered_analysis"]).sum()
                ),
                "jump_context_frames": link_result.jump_context_frames,
                "branch_cut_context_frames": link_result.branch_cut_context_frames,
                "analysis_eligible_frames": link_result.analysis_eligible_frames,
                "stage08_filter_status": link_result.filter_status,
            }
        )

    filtered_table = pd.concat(filtered_frames, ignore_index=True)
    summary_df = pd.DataFrame(summary_rows)
    jump_df = pd.DataFrame(jump_rows)
    branch_cut_df = pd.DataFrame(branch_cut_rows)
    diagnostics_df = pd.DataFrame(diagnostic_rows)

    links_pass = int(
        summary_df["stage08_filter_status"]
        .isin(
            [
                FilterLinkStatus.PASS.value,
                FilterLinkStatus.PASS_WITH_WARNING.value,
                FilterLinkStatus.FILTERED_BUT_JUMP_CONTEXT_FLAGGED.value,
            ]
        )
        .to_numpy()
        .sum()
    )
    file_result = FileFilterResult(
        links_processed=len(summary_df),
        links_pass=links_pass,
        links_with_jump_context=int(
            (
                (summary_df["jump_context_frames"] > 0)
                | (summary_df["branch_cut_context_frames"] > 0)
            )
            .to_numpy()
            .sum()
        ),
        links_excluded=int(
            (
                summary_df["stage08_filter_status"]
                == FilterLinkStatus.EXCLUDED_FROM_ANALYSIS.value
            )
            .to_numpy()
            .sum()
        ),
        links_blocked=int(
            (
                summary_df["stage08_filter_status"]
                == FilterLinkStatus.BLOCKED_NEEDS_REVIEW.value
            )
            .to_numpy()
            .sum()
        ),
        links_review=int(
            (
                summary_df["stage08_filter_status"]
                == FilterLinkStatus.PROVISIONAL_MANUAL_REVIEW.value
            )
            .to_numpy()
            .sum()
        ),
        total_jump_event_frames=int(summary_df["jump_event_frames"].to_numpy().sum()),
        total_jump_context_frames=int(summary_df["jump_context_frames"].to_numpy().sum()),
        total_branch_cut_event_frames=int(
            summary_df["branch_cut_event_frames"].to_numpy().sum()
        ),
        total_branch_cut_context_frames=int(
            summary_df["branch_cut_context_frames"].to_numpy().sum()
        ),
        total_analysis_eligible_frames=int(
            summary_df["analysis_eligible_frames"].to_numpy().sum()
        ),
        cutoff_hz=filtering_config.cutoff_hz,
        filter_order=float(filtering_config.filter_order),
        sampling_rate_hz=sampling_rate_hz,
        filter_type=filtering_config.filter_type,
        jump_context_window_frames=filtering_config.jump_context_window_frames,
        interpolation_applied=False,
    )

    return filtered_table, summary_df, jump_df, branch_cut_df, diagnostics_df, file_result


QC_MASK_REASONS = {
    "stage07_jump_context",
    "stage07_branch_cut_context",
    "excluded_feature_scope",
    "excluded_from_analysis_policy",
    "blocked_needs_review",
    "manual_review_provisional",
}

COMPUTATIONAL_NAN_REASONS = {
    "filter_not_applied",
}


def _report_base_columns(filtered_table: pd.DataFrame) -> list[str]:
    candidates = [
        "session_id",
        "run_label",
        "frame",
        "time_sec",
        "link_id",
        "parent_canonical",
        "child_canonical",
        "stage07_jump_status",
        "stage07_jump_magnitude_rad",
        "stage08_analysis_eligible",
        "stage08_filter_status",
        "stage08_mask_reason",
    ]
    return [col for col in candidates if col in filtered_table.columns]


def build_stage08_flag_report(
    filtered_table: pd.DataFrame,
    *,
    jump_df: pd.DataFrame | None = None,
    branch_cut_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Rows flagged for downstream review; numeric values are preserved."""
    base_columns = [
        *_report_base_columns(filtered_table),
        "reason",
        "context_start_frame",
        "context_end_frame",
    ]
    if filtered_table.empty:
        return pd.DataFrame(columns=base_columns)

    flagged = filtered_table.loc[~filtered_table["stage08_analysis_eligible"].astype(bool)].copy()
    if flagged.empty:
        return pd.DataFrame(columns=base_columns)

    flagged["reason"] = flagged["stage08_mask_reason"].fillna("").astype(str)
    flagged["reason"] = flagged["reason"].where(
        flagged["reason"].ne(""),
        "flagged_for_downstream_review",
    )
    flagged["context_start_frame"] = np.nan
    flagged["context_end_frame"] = np.nan

    if jump_df is not None and not jump_df.empty:
        for _, event in jump_df.iterrows():
            in_context = (
                (flagged["link_id"] == event["link_id"])
                & (flagged["frame"] >= event["context_start_frame"])
                & (flagged["frame"] <= event["context_end_frame"])
            )
            flagged.loc[in_context, "context_start_frame"] = int(event["context_start_frame"])
            flagged.loc[in_context, "context_end_frame"] = int(event["context_end_frame"])

    if branch_cut_df is not None and not branch_cut_df.empty:
        for _, event in branch_cut_df.iterrows():
            in_context = (
                (flagged["link_id"] == event["link_id"])
                & (flagged["frame"] >= event["context_start_frame"])
                & (flagged["frame"] <= event["context_end_frame"])
            )
            flagged.loc[in_context, "context_start_frame"] = int(event["context_start_frame"])
            flagged.loc[in_context, "context_end_frame"] = int(event["context_end_frame"])

    return flagged[base_columns].sort_values(["link_id", "frame"]).reset_index(drop=True)


def build_stage08_ineligible_rows_report(
    filtered_table: pd.DataFrame,
    *,
    jump_df: pd.DataFrame | None = None,
    branch_cut_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Ineligible frame×link rows with explicit note that values remain numeric when computed."""
    report = build_stage08_flag_report(
        filtered_table,
        jump_df=jump_df,
        branch_cut_df=branch_cut_df,
    )
    if report.empty:
        report["value_kept_numeric"] = pd.Series(dtype=bool)
        return report

    analysis_cols = ["rx_filtered_analysis", "ry_filtered_analysis", "rz_filtered_analysis"]
    present_cols = [col for col in analysis_cols if col in filtered_table.columns]
    if not present_cols:
        report["value_kept_numeric"] = True
        return report

    values = filtered_table[["frame", "link_id", *present_cols]]
    report = report.merge(values, on=["frame", "link_id"], how="left")
    report["value_kept_numeric"] = np.all(
        np.isfinite(report[present_cols].to_numpy(dtype=float)),
        axis=1,
    )
    return report.drop(columns=present_cols)


def build_stage08_nan_report(filtered_table: pd.DataFrame) -> pd.DataFrame:
    """True computational NaNs in analysis columns, distinct from QC-flagged rows."""
    if filtered_table.empty:
        return pd.DataFrame(
            columns=[
                *_report_base_columns(filtered_table),
                "nan_classification",
                "reason",
            ]
        )

    analysis_cols = ["rx_filtered_analysis", "ry_filtered_analysis", "rz_filtered_analysis"]
    if not all(col in filtered_table.columns for col in analysis_cols):
        return pd.DataFrame(
            columns=[
                *_report_base_columns(filtered_table),
                "nan_classification",
                "reason",
            ]
        )

    analysis_finite = np.all(
        np.isfinite(filtered_table[analysis_cols].to_numpy(dtype=float)),
        axis=1,
    )
    nan_rows = filtered_table.loc[~analysis_finite].copy()
    if nan_rows.empty:
        return pd.DataFrame(
            columns=[
                *_report_base_columns(filtered_table),
                "nan_classification",
                "reason",
            ]
        )

    mask_reason = nan_rows["stage08_mask_reason"].fillna("").astype(str)
    is_computational = mask_reason.isin(COMPUTATIONAL_NAN_REASONS) | ~np.all(
        np.isfinite(nan_rows[["rx_raw", "ry_raw", "rz_raw"]].to_numpy(dtype=float)),
        axis=1,
    )
    nan_rows["nan_classification"] = np.where(
        is_computational.to_numpy(),
        "computational_failure",
        "unexpected_nan",
    )
    nan_rows["reason"] = mask_reason.where(mask_reason.ne(""), "analysis_value_not_computed")
    columns = [
        *_report_base_columns(filtered_table),
        "nan_classification",
        "reason",
    ]
    return nan_rows[columns].sort_values(["link_id", "frame"]).reset_index(drop=True)


def enrich_jump_context_report(
    jump_df: pd.DataFrame,
    filtered_table: pd.DataFrame,
) -> pd.DataFrame:
    """Add eligibility/flag columns to the per-event jump context report."""
    if jump_df.empty:
        return jump_df

    enriched = jump_df.copy()
    for col in (
        "session_id",
        "run_label",
        "stage08_analysis_eligible",
        "stage08_filter_status",
        "stage08_mask_reason",
    ):
        if col in filtered_table.columns and col not in enriched.columns:
            link_values = (
                filtered_table.groupby("link_id", sort=True)[col]
                .first()
                .to_dict()
            )
            enriched[col] = enriched["link_id"].map(link_values)

    enriched["reason"] = "value_kept_numeric_row_flagged_for_downstream_review"
    return enriched
