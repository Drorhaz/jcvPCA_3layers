"""Layer 2 jump_fail_rad and block_filter frame predicates."""

from __future__ import annotations

import pandas as pd

from pre_jvcpca_review.load_layer2 import LinkRecord


def jump_fail_rad_mask(df: pd.DataFrame, link: LinkRecord) -> pd.Series:
    """Frames counted as jump_fail_rad (link-level fail + jump context mask)."""
    if link.stage07_jump_status != "fail":
        return pd.Series(False, index=df.index)
    return df["stage08_mask_reason"].fillna("") == "stage07_jump_context"


def block_filter_mask(df: pd.DataFrame, link: LinkRecord) -> pd.Series:
    """Frames counted as block_filter policy impact."""
    if link.stage07_jump_status == "fail":
        return df["stage08_filter_status"] == "filtered_but_jump_context_masked"
    return ~df["stage08_analysis_eligible"].astype(bool)


def frame_percent(mask: pd.Series, duration_frames: int) -> float:
    if duration_frames <= 0:
        return 0.0
    return round(100.0 * mask.sum() / duration_frames, 2)


def stage08_review_stats(
    df: pd.DataFrame,
    link: LinkRecord,
    duration_frames: int,
) -> dict[str, object]:
    """Per-link Stage 07/08 evidence for review tables (flag-only policy aware)."""
    jump_context = (
        df["stage08_mask_reason"].fillna("") == "stage07_jump_context"
        if "stage08_mask_reason" in df.columns
        else pd.Series(False, index=df.index)
    )
    not_eligible = (
        ~df["stage08_analysis_eligible"].astype(bool)
        if "stage08_analysis_eligible" in df.columns
        else pd.Series(False, index=df.index)
    )
    block_mask = block_filter_mask(df, link)
    analysis_cols = [
        col
        for col in ("rx_filtered_analysis", "ry_filtered_analysis", "rz_filtered_analysis")
        if col in df.columns
    ]
    computational_nan = (
        df[analysis_cols].isna().any(axis=1) if analysis_cols else pd.Series(False, index=df.index)
    )
    max_jump = ""
    if "stage07_jump_magnitude_rad" in df.columns and len(df):
        try:
            max_jump = round(float(df["stage07_jump_magnitude_rad"].max()), 6)
        except (TypeError, ValueError):
            max_jump = ""
    filter_statuses = (
        sorted(df["stage08_filter_status"].dropna().astype(str).unique().tolist())
        if "stage08_filter_status" in df.columns
        else []
    )
    mask_reasons = (
        sorted(df["stage08_mask_reason"].dropna().astype(str).unique().tolist())
        if "stage08_mask_reason" in df.columns
        else []
    )
    return {
        "stage07_jump_status": link.stage07_jump_status,
        "stage07_jump_magnitude_rad_max": max_jump,
        "stage08_jump_context_frame_percent": frame_percent(jump_context, duration_frames),
        "stage08_not_analysis_eligible_frame_percent": frame_percent(not_eligible, duration_frames),
        "stage08_block_filter_frame_percent": frame_percent(block_mask, duration_frames),
        "stage08_computational_nan_frame_percent": frame_percent(computational_nan, duration_frames),
        "stage08_filter_status_values": "; ".join(filter_statuses),
        "stage08_mask_reason_values": "; ".join(mask_reasons),
    }


def problem_notes(
    jump_count: int,
    block_count: int,
    duration_frames: int,
    link: LinkRecord,
) -> str:
    parts: list[str] = []
    if block_count >= duration_frames and duration_frames > 0:
        parts.append("full-window block_filter")
    elif block_count > 0:
        parts.append(f"{block_count} block-filter frames")
    if jump_count > 0:
        parts.append(f"{jump_count} jump_fail_rad frames")
    if not parts:
        return "no Layer 2 problem flags in selected window"
    return "; ".join(parts)
