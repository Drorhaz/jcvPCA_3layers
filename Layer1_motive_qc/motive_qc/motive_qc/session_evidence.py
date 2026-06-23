"""Factual session-level evidence metrics (no usability verdicts)."""

from __future__ import annotations

from typing import Any

import pandas as pd

from motive_qc.marker_gap_evidence import dominant_gap_marker_fields

FLAG_COLUMNS = (
    "flag_gap_0p2",
    "flag_gap_0p5",
    "flag_artifact_sigma",
    "flag_segment_swap",
    "flag_edge_effect",
)

UNION_FLAG_RENAMES = {
    "flag_gap_0p2": "pct_frames_union_flag_gap_0p2",
    "flag_gap_0p5": "pct_frames_union_flag_gap_0p5",
    "flag_artifact_sigma": "pct_frames_union_flag_artifact_sigma",
    "flag_segment_swap": "pct_frames_union_flag_segment_swap",
    "flag_edge_effect": "pct_frames_union_flag_edge_effect",
}


def _pct(n: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(100.0 * float(n) / total, 6)


def _union_flag_percentages(qc_mask: pd.DataFrame) -> dict[str, float]:
    """Percent of frames where union qc_mask flags are set (any marker may trigger)."""
    if qc_mask.empty:
        out = {name: 0.0 for name in UNION_FLAG_RENAMES.values()}
        out["pct_frames_union_any_flag"] = 0.0
        return out
    n = len(qc_mask)
    out: dict[str, float] = {}
    any_flag = pd.Series(False, index=qc_mask.index)
    for col, out_name in UNION_FLAG_RENAMES.items():
        if col in qc_mask.columns:
            active = qc_mask[col].astype(bool)
        else:
            active = pd.Series(False, index=qc_mask.index)
        out[out_name] = _pct(int(active.sum()), n)
        any_flag = any_flag | active
    out["pct_frames_union_any_flag"] = _pct(int(any_flag.sum()), n)
    return out


def _dominant_criterion(qc_mask_intervals: pd.DataFrame) -> str:
    if qc_mask_intervals.empty or "criterion" not in qc_mask_intervals.columns:
        return ""
    crit = qc_mask_intervals["criterion"].astype(str)
    crit = crit[crit.str.len() > 0]
    if crit.empty:
        return ""
    return str(crit.value_counts().index[0])


def _markers_with_large_gaps(gaps_over_0p5s: pd.DataFrame) -> str:
    if gaps_over_0p5s.empty:
        return ""
    col = "marker_name_canonical" if "marker_name_canonical" in gaps_over_0p5s.columns else "marker_name"
    names = sorted({str(v) for v in gaps_over_0p5s[col].astype(str) if v and v.lower() != "nan"})
    return ";".join(names)


def compute_session_evidence(
    qc_mask: pd.DataFrame,
    qc_mask_intervals: pd.DataFrame,
    gaps_over_0p5s: pd.DataFrame,
    marker_gap_evidence: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Return additive factual fields for session_summary (no verdict labels)."""
    union_pcts = _union_flag_percentages(qc_mask)
    markers = _markers_with_large_gaps(gaps_over_0p5s)
    dominant = dominant_gap_marker_fields(marker_gap_evidence if marker_gap_evidence is not None else pd.DataFrame())
    return {
        **union_pcts,
        **dominant,
        "dominant_criterion": _dominant_criterion(qc_mask_intervals),
        "markers_with_gap_ge_0p5s": markers,
        "n_markers_with_gap_ge_0p5s": len([m for m in markers.split(";") if m]) if markers else 0,
    }


def append_evidence_to_session_summary(
    session_summary: pd.DataFrame,
    evidence_fields: dict[str, Any],
) -> pd.DataFrame:
    if session_summary.empty:
        return pd.DataFrame([evidence_fields])
    out = session_summary.copy()
    for key, value in evidence_fields.items():
        out[key] = value
    return out
