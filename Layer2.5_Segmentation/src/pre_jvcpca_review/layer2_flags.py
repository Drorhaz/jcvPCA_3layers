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
