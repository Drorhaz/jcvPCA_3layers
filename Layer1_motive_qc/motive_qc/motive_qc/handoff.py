"""Layer 1 downstream QC handoff table for Layer 2.5."""

from __future__ import annotations

from typing import Any

import pandas as pd

from motive_qc.marker_set import prefix_change_flag
from motive_qc.session_identity import session_identity_from_metadata


def _affected_marker_count(affected_markers: str) -> int:
    if not affected_markers or str(affected_markers).lower() == "nan":
        return 0
    return len([m for m in str(affected_markers).split(";") if m.strip()])


def build_layer1_qc_handoff(
    qc_mask_intervals: pd.DataFrame,
    marker_set_row: pd.Series | dict[str, Any],
    session_metadata: dict[str, Any],
    config: dict[str, Any],
    unlabeled_summary: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Event/interval-level handoff rows (frame mask remains ``qc_mask.csv``)."""
    identity = session_identity_from_metadata(session_metadata, config)
    if isinstance(marker_set_row, pd.Series):
        ms = marker_set_row.to_dict()
    else:
        ms = marker_set_row

    marker_set_id = str(ms.get("marker_set_id_or_hash") or "")
    prefixes = [
        p
        for p in str(ms.get("asset_prefixes_observed") or "").split(";")
        if p.strip()
    ]
    prefix_flag = prefix_change_flag(identity["participant_id"], prefixes)

    unlabeled_burden = False
    if unlabeled_summary is not None and not unlabeled_summary.empty:
        pct = float(unlabeled_summary.iloc[0].get("percent_frames_with_any_unlabeled", 0.0))
        unlabeled_burden = pct >= 10.0

    cols = [
        "participant_id",
        "session_id",
        "timepoint",
        "part_id",
        "repetition_id",
        "source_file",
        "start_frame",
        "end_frame",
        "time_sec",
        "end_time_sec",
        "gap_flag",
        "jump_flag",
        "swap_candidate_flag",
        "artifact_flag",
        "unlabeled_burden_flag",
        "marker_set_id",
        "marker_set_mismatch_or_prefix_change_flag",
        "dominant_reason",
        "affected_markers",
        "affected_marker_count",
    ]
    if qc_mask_intervals.empty:
        return pd.DataFrame(columns=cols)

    rows: list[dict[str, Any]] = []
    for _, interval in qc_mask_intervals.iterrows():
        reason = str(interval.get("reason") or "")
        rows.append(
            {
                **identity,
                "start_frame": int(interval["start_frame"]),
                "end_frame": int(interval["end_frame"]),
                "time_sec": float(interval.get("start_s", interval.get("start_time_s", 0.0))),
                "end_time_sec": float(interval.get("end_s", interval.get("end_time_s", 0.0))),
                "gap_flag": bool(interval.get("has_gap_ge_0p5", False) or interval.get("has_gap_0p2", False)),
                "jump_flag": "ARTIFACT_SIGMA" in reason and "SPIKE" in reason.upper(),
                "swap_candidate_flag": bool(interval.get("has_segment_swap", False)),
                "artifact_flag": bool(interval.get("has_artifact_sigma", False)),
                "unlabeled_burden_flag": unlabeled_burden,
                "marker_set_id": marker_set_id,
                "marker_set_mismatch_or_prefix_change_flag": prefix_flag,
                "dominant_reason": str(interval.get("criterion") or reason.split(";")[0] if reason else ""),
                "affected_markers": str(interval.get("affected_markers") or ""),
                "affected_marker_count": _affected_marker_count(interval.get("affected_markers", "")),
            }
        )
    return pd.DataFrame(rows, columns=cols)
