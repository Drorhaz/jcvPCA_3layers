"""Per-marker gap frame/time evidence (distinct from union qc_mask flags)."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from motive_qc.analysis_scope import filter_gap_events_for_analysis
from motive_qc.marker_names import add_marker_name_columns, inventory_lookup


def _pct(n: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(100.0 * float(n) / total, 6)


def build_layer1_marker_gap_evidence(
    gap_events: pd.DataFrame,
    gaps_over_0p5s: pd.DataFrame,
    inventory: pd.DataFrame,
    config: dict[str, Any],
    *,
    n_frames: int,
    min_frame: int = 0,
) -> pd.DataFrame:
    """One row per marker with gap >=0.5 s: per-marker frame % and gap durations."""
    large = float(config["gaps"]["thresholds_seconds"]["large_gap"])
    cols = [
        "marker_name",
        "marker_name_raw",
        "marker_name_canonical",
        "asset_prefix",
        "body_region_group",
        "n_gaps_ge_0p5",
        "total_gap_seconds_ge_0p5",
        "longest_gap_seconds",
        "n_frames_in_gap_ge_0p5",
        "pct_frames_in_gap_ge_0p5",
        "pct_session_time_in_gap_ge_0p5",
    ]
    if gaps_over_0p5s.empty and gap_events.empty:
        return pd.DataFrame(columns=cols)

    summary_by_marker: dict[str, dict[str, Any]] = {}
    if not gaps_over_0p5s.empty:
        for _, row in gaps_over_0p5s.iterrows():
            raw = str(row["marker_name"])
            summary_by_marker[raw] = {
                "body_region_group": row.get("body_region_group", ""),
                "n_gaps_ge_0p5": int(row.get("n_gaps", 0)),
                "total_gap_seconds_ge_0p5": float(row.get("total_gap_seconds", 0.0)),
                "longest_gap_seconds": float(row.get("longest_gap_seconds", 0.0)),
            }

    labeled = filter_gap_events_for_analysis(gap_events, config)
    if "is_labeled" in labeled.columns:
        labeled = labeled[labeled["is_labeled"]]
    labeled = labeled[labeled["duration_seconds"].astype(float) >= large] if not labeled.empty else labeled

    marker_names = sorted(summary_by_marker.keys())
    if not marker_names and not labeled.empty:
        marker_names = sorted(labeled["marker_name"].astype(str).unique().tolist())

    duration_s = float(config.get("_session_duration_seconds") or 0.0)
    rows: list[dict[str, Any]] = []
    for raw in marker_names:
        meta = summary_by_marker.get(raw, {})
        marker_gaps = labeled[labeled["marker_name"].astype(str) == raw] if not labeled.empty else pd.DataFrame()
        n_frames_in_gap = 0
        if not marker_gaps.empty and n_frames > 0:
            frame_flags = np.zeros(n_frames, dtype=bool)
            for _, gap in marker_gaps.iterrows():
                start = int(gap["gap_start_frame"]) - min_frame
                end = int(gap["gap_end_frame"]) - min_frame
                start = max(0, start)
                end = min(n_frames - 1, end)
                if end >= start:
                    frame_flags[start : end + 1] = True
            n_frames_in_gap = int(frame_flags.sum())
        total_gap_s = float(meta.get("total_gap_seconds_ge_0p5", 0.0))
        if not marker_gaps.empty and total_gap_s == 0.0:
            total_gap_s = float(marker_gaps["duration_seconds"].sum())
        rows.append(
            {
                "marker_name": raw,
                "body_region_group": meta.get("body_region_group", ""),
                "n_gaps_ge_0p5": int(meta.get("n_gaps_ge_0p5", len(marker_gaps))),
                "total_gap_seconds_ge_0p5": round(total_gap_s, 6),
                "longest_gap_seconds": round(
                    float(meta.get("longest_gap_seconds", marker_gaps["duration_seconds"].max() if not marker_gaps.empty else 0.0)),
                    6,
                ),
                "n_frames_in_gap_ge_0p5": n_frames_in_gap,
                "pct_frames_in_gap_ge_0p5": _pct(n_frames_in_gap, n_frames),
                "pct_session_time_in_gap_ge_0p5": round(100.0 * total_gap_s / duration_s, 6) if duration_s > 0 else 0.0,
            }
        )

    out = pd.DataFrame(rows)
    if out.empty:
        return pd.DataFrame(columns=cols)
    lookup = inventory_lookup(inventory)
    out = add_marker_name_columns(out, lookup, marker_col="marker_name")
    return out[cols]


def dominant_gap_marker_fields(marker_gap_evidence: pd.DataFrame) -> dict[str, Any]:
    """Summary fields for session_summary from per-marker gap table."""
    if marker_gap_evidence.empty:
        return {
            "dominant_gap_marker_canonical": "",
            "dominant_gap_marker_raw": "",
            "pct_frames_dominant_marker_in_gap_ge_0p5": "",
            "pct_session_time_dominant_marker_in_gap_ge_0p5": "",
        }
    ranked = marker_gap_evidence.sort_values(
        ["pct_frames_in_gap_ge_0p5", "total_gap_seconds_ge_0p5"],
        ascending=[False, False],
    )
    top = ranked.iloc[0]
    return {
        "dominant_gap_marker_canonical": str(top.get("marker_name_canonical", "")),
        "dominant_gap_marker_raw": str(top.get("marker_name_raw", top.get("marker_name", ""))),
        "pct_frames_dominant_marker_in_gap_ge_0p5": float(top.get("pct_frames_in_gap_ge_0p5", 0.0)),
        "pct_session_time_dominant_marker_in_gap_ge_0p5": float(top.get("pct_session_time_in_gap_ge_0p5", 0.0)),
    }
