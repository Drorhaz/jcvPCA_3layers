"""Window subsetting and QC summarization for Layer 1 and Layer 2."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from layer2_motive.segmentation.marker_family import MarkerFamilyMapper
from layer2_motive.segmentation.qc_events import marker_identity_from_event_row
from layer2_motive.segmentation.schemas import (
    COMBINED_QC_EVENT_COLUMNS,
    COMBINED_QC_EVENT_SUMMARY_COLUMNS,
    DEFAULT_L1_EVIDENCE_TYPES,
    DEFAULT_L2_EVIDENCE_TYPES,
    LAYER1_MARKER_FAMILY_RISK_COLUMNS,
    LAYER2_LINK_SCOPE_DISPLAY_COLUMNS,
    QC_EVENT_DISPLAY_COLUMNS,
    WINDOW_QC_SUMMARY_DISPLAY_COLUMNS,
    ExportScopePolicy,
    GapPolicy,
    Layer1Bundle,
    Layer2Bundle,
    QCEvidencePolicy,
    SessionIdentity,
    ValidationResult,
    _normalize_qc_type_for_policy,
)

LAYER1_FLAG_COLUMNS = (
    "flag_gap_0p2",
    "flag_gap_0p5",
    "flag_artifact_sigma",
    "flag_segment_swap",
    "flag_edge_effect",
)

LAYER1_QC_TYPE_TO_FLAG = {
    "marker_gap_0p2": "flag_gap_0p2",
    "marker_gap_0p5": "flag_gap_0p5",
    "artifact_sigma": "flag_artifact_sigma",
    "segment_swap": "flag_segment_swap",
}


def _coerce_bool(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series
    return series.astype(str).str.lower().isin({"true", "1", "yes"})


def parse_l1_evidence_arg(value: str | None) -> frozenset[str]:
    if not value:
        return DEFAULT_L1_EVIDENCE_TYPES
    return frozenset(t.strip() for t in value.split(",") if t.strip())


def parse_l2_evidence_arg(value: str | None) -> frozenset[str]:
    if not value:
        return DEFAULT_L2_EVIDENCE_TYPES
    return frozenset(t.strip() for t in value.split(",") if t.strip())


def subset_layer1_events_to_window(
    events: pd.DataFrame,
    start_frame: int,
    end_frame: int,
) -> pd.DataFrame:
    """Subset Layer 1 events to inclusive frame window (point or interval overlap)."""
    if events.empty:
        return events.copy()

    start_frame = int(start_frame)
    end_frame = int(end_frame)

    def overlaps(row: pd.Series) -> bool:
        sf = row.get("start_frame")
        ef = row.get("end_frame")
        fr = row.get("frame")
        if pd.notna(sf) and pd.notna(ef):
            return int(sf) <= end_frame and int(ef) >= start_frame
        if pd.notna(fr):
            return start_frame <= int(fr) <= end_frame
        return False

    mask = events.apply(overlaps, axis=1)
    return events.loc[mask].copy()


def subset_layer2_to_window(
    layer2_df: pd.DataFrame,
    start_frame: int,
    end_frame: int,
) -> pd.DataFrame:
    """Subset Layer 2 parquet to inclusive frame window."""
    start_frame = int(start_frame)
    end_frame = int(end_frame)
    return layer2_df[(layer2_df["frame"] >= start_frame) & (layer2_df["frame"] <= end_frame)].copy()


def summarize_layer1_window(
    qc_mask_df: pd.DataFrame,
    layer1_events: pd.DataFrame,
    start_frame: int,
    end_frame: int,
    *,
    frame_col: str = "frame",
    gap_policy: GapPolicy | None = None,
) -> dict[str, Any]:
    """Summarize Layer 1 QC for the selected window."""
    gap_policy = gap_policy or GapPolicy()
    start_frame = int(start_frame)
    end_frame = int(end_frame)
    window_mask = qc_mask_df[frame_col].between(start_frame, end_frame)
    window = qc_mask_df.loc[window_mask]

    n_window_frames = int(len(window))
    any_flag = pd.Series(False, index=window.index)
    for col in LAYER1_FLAG_COLUMNS:
        if col in window.columns:
            any_flag = any_flag | _coerce_bool(window[col])
    n_clean = int((~any_flag).sum())
    n_flagged = int(any_flag.sum())

    flag_counts: dict[str, int] = {}
    for col in LAYER1_FLAG_COLUMNS:
        if col in window.columns:
            flag_counts[col] = int(_coerce_bool(window[col]).sum())
        else:
            flag_counts[col] = 0

    top_reasons: list[tuple[str, int]] = []
    if "reason" in window.columns:
        reasons = window["reason"].fillna("").astype(str)
        reasons = reasons[reasons != ""]
        if len(reasons):
            top_reasons = list(reasons.value_counts().head(10).items())

    top_markers: list[tuple[str, int]] = []
    top_regions: list[tuple[str, int]] = []
    if not layer1_events.empty:
        if "marker_raw_name" in layer1_events.columns:
            markers = layer1_events["marker_raw_name"].fillna("").astype(str)
            markers = markers[markers != ""]
            if len(markers):
                top_markers = list(markers.value_counts().head(10).items())
        if "body_region_group" in layer1_events.columns:
            regions = layer1_events["body_region_group"].fillna("").astype(str)
            regions = regions[regions != ""]
            if len(regions):
                top_regions = list(regions.value_counts().head(10).items())

    def pct(n: int) -> float:
        return round(100.0 * n / n_window_frames, 4) if n_window_frames else 0.0

    return {
        "start_frame": start_frame,
        "end_frame": end_frame,
        "n_window_frames": n_window_frames,
        "n_clean_frames": n_clean,
        "n_flagged_frames": n_flagged,
        "n_use_frames": n_clean,
        "n_caution_frames": int(flag_counts.get("flag_gap_0p2", 0)),
        "n_exclude_frames": int(flag_counts.get("flag_gap_0p5", 0)),
        "percent_use": pct(n_clean),
        "percent_caution": pct(int(flag_counts.get("flag_gap_0p2", 0))),
        "percent_exclude": pct(int(flag_counts.get("flag_gap_0p5", 0))),
        "flag_counts": flag_counts,
        "gap_0p5_percent": pct(flag_counts.get("flag_gap_0p5", 0)),
        "gap_0p2_percent": pct(flag_counts.get("flag_gap_0p2", 0)),
        "gap_0p2_counted_in_burden": gap_policy.gap_0p2_counted_in_burden,
        "artifact_sigma_percent": pct(flag_counts.get("flag_artifact_sigma", 0)),
        "segment_swap_percent": pct(flag_counts.get("flag_segment_swap", 0)),
        "top_reasons": top_reasons,
        "top_markers": top_markers,
        "top_body_regions": top_regions,
    }


def _summarize_layer2_per_link(
    window_df: pd.DataFrame, link_manifest: pd.DataFrame
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    link_ids = sorted(link_manifest["link_id"].unique())

    for link_id in link_ids:
        manifest_row = link_manifest.loc[link_manifest["link_id"] == link_id].iloc[0]
        link_df = window_df[window_df["link_id"] == link_id]
        n_window_frames = int(link_df["frame"].nunique()) if not link_df.empty else 0
        n_rows = int(len(link_df))
        n_eligible = int(link_df["stage08_analysis_eligible"].sum()) if n_rows else 0
        n_ineligible = n_rows - n_eligible
        n_nan = int(link_df["rx_filtered_analysis"].isna().sum()) if n_rows else 0
        n_jump_ctx = int(link_df["stage08_within_jump_context_window"].sum()) if n_rows else 0
        n_fail = int((link_df["stage07_jump_status"] == "fail").sum()) if n_rows else 0
        n_warn = int((link_df["stage07_jump_status"] == "warning").sum()) if n_rows else 0
        pct_eligible = round(100.0 * n_eligible / n_rows, 4) if n_rows else 0.0
        pct_masked = round(100.0 * n_ineligible / n_rows, 4) if n_rows else 0.0

        rows.append(
            {
                "link_id": link_id,
                "parent_canonical": manifest_row["parent_canonical"],
                "child_canonical": manifest_row["child_canonical"],
                "feature_scope": manifest_row["feature_scope"],
                "requires_manual_review": bool(manifest_row["requires_manual_review"]),
                "stage08_policy": manifest_row["stage08_policy"],
                "n_window_frames": n_window_frames,
                "n_rows": n_rows,
                "n_analysis_eligible_frames": n_eligible,
                "n_analysis_ineligible_frames": n_ineligible,
                "n_analysis_nan_frames": n_nan,
                "n_jump_context_frames": n_jump_ctx,
                "n_stage07_jump_fail_frames": n_fail,
                "n_stage07_jump_warn_frames": n_warn,
                "percent_analysis_eligible": pct_eligible,
                "percent_masked": pct_masked,
            }
        )

    return pd.DataFrame(rows)


def summarize_layer2_window(
    layer2_df: pd.DataFrame,
    link_manifest: pd.DataFrame,
    start_frame: int,
    end_frame: int,
) -> dict[str, Any]:
    """Summarize Layer 2 QC for the selected window (overall + per-link table)."""
    window_df = subset_layer2_to_window(layer2_df, start_frame, end_frame)
    start_frame = int(start_frame)
    end_frame = int(end_frame)

    n_window_frames = int(window_df["frame"].nunique()) if not window_df.empty else 0
    n_rows = int(len(window_df))
    n_links = int(window_df["link_id"].nunique()) if not window_df.empty else 0
    n_eligible = int(window_df["stage08_analysis_eligible"].sum()) if n_rows else 0
    n_ineligible = n_rows - n_eligible
    n_nan = int(window_df["rx_filtered_analysis"].isna().sum()) if n_rows else 0
    n_jump_ctx = int(window_df["stage08_within_jump_context_window"].sum()) if n_rows else 0
    n_fail = int((window_df["stage07_jump_status"] == "fail").sum()) if n_rows else 0
    n_warn = int((window_df["stage07_jump_status"] == "warning").sum()) if n_rows else 0

    feature_scope_counts = window_df["feature_scope"].value_counts().to_dict() if n_rows else {}
    policy_counts = window_df["stage08_policy"].value_counts().to_dict() if n_rows else {}

    per_link = _summarize_layer2_per_link(window_df, link_manifest)

    def scope_usable(scope: str) -> float:
        scoped = per_link[per_link["feature_scope"] == scope]
        if scoped.empty:
            return 0.0
        return round(float(scoped["percent_analysis_eligible"].mean()), 4)

    has_excluded = per_link["feature_scope"].isin(["excluded_distal", "excluded_toe"]).any()
    excluded_usable = (
        round((scope_usable("excluded_distal") + scope_usable("excluded_toe")) / 2.0, 4)
        if has_excluded
        else 0.0
    )

    return {
        "start_frame": start_frame,
        "end_frame": end_frame,
        "n_window_frames": n_window_frames,
        "n_links": n_links,
        "n_rows": n_rows,
        "n_analysis_eligible_rows": n_eligible,
        "n_analysis_ineligible_rows": n_ineligible,
        "n_analysis_nan_rows": n_nan,
        "percent_analysis_eligible": round(100.0 * n_eligible / n_rows, 4) if n_rows else 0.0,
        "n_stage08_jump_context_rows": n_jump_ctx,
        "n_stage07_jump_fail_rows": n_fail,
        "n_stage07_jump_warn_rows": n_warn,
        "feature_scope_counts": feature_scope_counts,
        "stage08_policy_counts": policy_counts,
        "per_link_summary": per_link,
        "layer2_core_usable_percent": scope_usable("core_candidate"),
        "layer2_review_usable_percent": scope_usable("review_provisional"),
        "layer2_excluded_usable_percent": excluded_usable,
    }


def _layer1_recommended_action(severity: str, qc_type: str) -> str:
    if severity == "exclude":
        return "review_exclude_frames"
    if qc_type == "frame_status":
        return "review_caution_frames"
    return "review_flagged_frames"


def _layer2_recommended_action(row: pd.Series) -> str:
    if row.get("stage08_analysis_eligible") is False or row.get("stage08_analysis_eligible") == 0:
        reason = str(row.get("stage08_mask_reason", "") or "")
        if reason:
            return f"masked:{reason}"
        return "masked_by_policy"
    if row.get("stage08_within_jump_context_window"):
        return "jump_context_review"
    status = str(row.get("stage07_jump_status", ""))
    if status == "fail":
        return "stage07_fail_review"
    if status == "warning":
        return "stage07_warning_review"
    return "review"


def _l1_event_included_in_review(
    qc_type: str,
    evidence_policy: QCEvidencePolicy,
    gap_policy: GapPolicy,
) -> bool:
    normalized = _normalize_qc_type_for_policy(str(qc_type))
    if normalized == "gap_0p2" and not gap_policy.gap_0p2_counted_in_burden:
        return normalized in evidence_policy.l1_evidence_types
    return evidence_policy.l1_type_included(str(qc_type))


def _recommendation_placeholder(
    feature_scope: str,
    stage08_policy: str,
    requires_manual_review: bool,
) -> str:
    if feature_scope in {"excluded_distal", "excluded_toe"}:
        return "excluded_by_policy"
    if stage08_policy == "block_filter":
        return "blocked_needs_review"
    if requires_manual_review or feature_scope == "review_provisional":
        return "manual_review"
    return "candidate_include"


def build_combined_qc_event_table(
    layer1_window_events: pd.DataFrame,
    layer2_window_df: pd.DataFrame,
    link_manifest: pd.DataFrame,  # noqa: ARG001 — reserved for future mapping phases
    *,
    mapper: MarkerFamilyMapper | None = None,
    mapping_version: str = "heuristic_v0",
) -> pd.DataFrame:
    """Build combined QC event table from Layer 1 events and qualifying Layer 2 rows."""
    mapper = mapper or MarkerFamilyMapper()
    rows: list[dict[str, Any]] = []

    for _, ev in layer1_window_events.iterrows():
        body_region = ev.get("body_region_group", "")
        has_region = pd.notna(body_region) and str(body_region) != ""
        marker = marker_identity_from_event_row(ev)

        rows.append(
            {
                "source_layer": "layer1",
                "frame": ev.get("frame"),
                "start_frame": ev.get("start_frame"),
                "end_frame": ev.get("end_frame"),
                "time_sec": ev.get("time_sec"),
                "start_time_sec": ev.get("start_time_sec"),
                "end_time_sec": ev.get("end_time_sec"),
                "entity_type": ev.get("entity_type"),
                "entity_id": marker,
                "entity_name": ev.get("entity_name"),
                "link_id": None,
                "parent_canonical": None,
                "child_canonical": None,
                "body_region_group": body_region if has_region else None,
                "qc_type": ev.get("qc_type"),
                "severity": ev.get("severity"),
                "reason": ev.get("reason"),
                "mapping_confidence": ev.get("mapping_confidence"),
                "recommended_action": _layer1_recommended_action(
                    str(ev.get("severity", "")), str(ev.get("qc_type", ""))
                ),
                "duration_frames": ev.get("duration_frames"),
                "duration_seconds": ev.get("duration_seconds"),
                "normalized_marker_name": ev.get("normalized_marker_name"),
                "attached_bone": ev.get("attached_bone"),
                "attached_bone_canonical": ev.get("attached_bone_canonical"),
                "related_joint_family": ev.get("related_joint_family"),
                "mapping_source": ev.get("mapping_source"),
                "mapping_version": mapping_version,
                "template_mapping_status": ev.get("template_mapping_status"),
            }
        )

    if not layer2_window_df.empty:
        mask_reason = layer2_window_df["stage08_mask_reason"].fillna("").astype(str)
        qualifying = (
            (~layer2_window_df["stage08_analysis_eligible"])
            | layer2_window_df["stage08_within_jump_context_window"]
            | layer2_window_df["stage07_jump_status"].isin(["warning", "fail"])
            | (mask_reason != "")
        )
        l2_events = layer2_window_df.loc[qualifying]

        for _, row in l2_events.iterrows():
            reason = str(row.get("stage08_mask_reason", "") or "")
            if not reason and row.get("stage07_jump_status") in ("warning", "fail"):
                reason = f"stage07_jump_status={row['stage07_jump_status']}"
            elif not reason and row.get("stage08_within_jump_context_window"):
                reason = "stage08_within_jump_context_window"

            rows.append(
                {
                    "source_layer": "layer2",
                    "frame": int(row["frame"]),
                    "start_frame": int(row["frame"]),
                    "end_frame": int(row["frame"]),
                    "time_sec": row.get("time_sec"),
                    "start_time_sec": row.get("time_sec"),
                    "end_time_sec": row.get("time_sec"),
                    "entity_type": "link",
                    "entity_id": row["link_id"],
                    "entity_name": f"{row['parent_canonical']}->{row['child_canonical']}",
                    "link_id": row["link_id"],
                    "parent_canonical": row["parent_canonical"],
                    "child_canonical": row["child_canonical"],
                    "body_region_group": None,
                    "qc_type": reason or "layer2_qc_row",
                    "severity": str(row.get("stage07_jump_status", "info")),
                    "reason": reason,
                    "mapping_confidence": "n/a",
                    "recommended_action": _layer2_recommended_action(row),
                    "duration_frames": 1,
                    "duration_seconds": None,
                    "normalized_marker_name": None,
                    "attached_bone": None,
                    "attached_bone_canonical": None,
                    "related_joint_family": None,
                    "mapping_source": "not_applicable",
                    "mapping_version": mapping_version,
                    "template_mapping_status": "not_applicable",
                }
            )

    if not rows:
        return pd.DataFrame(columns=list(COMBINED_QC_EVENT_COLUMNS))
    return pd.DataFrame(rows, columns=list(COMBINED_QC_EVENT_COLUMNS))


def build_qc_event_display(
    combined_events: pd.DataFrame,
    *,
    evidence_policy: QCEvidencePolicy,
    gap_policy: GapPolicy,
) -> pd.DataFrame:
    """Build compact QC Event Review Table."""
    if combined_events.empty:
        return pd.DataFrame(columns=list(QC_EVENT_DISPLAY_COLUMNS))

    rows: list[dict[str, Any]] = []
    for _, ev in combined_events.iterrows():
        source = str(ev.get("source_layer", ""))
        qc_type = str(ev.get("qc_type", ""))
        if source == "layer1":
            included = _l1_event_included_in_review(qc_type, evidence_policy, gap_policy)
            counted = included and (
                _normalize_qc_type_for_policy(qc_type) != "gap_0p2"
                or gap_policy.gap_0p2_counted_in_burden
            )
            recommendation_impact = "counted" if counted else "visible_not_counted"
        else:
            included = True
            recommendation_impact = "layer2_evidence"

        marker_or_region = (
            ev.get("entity_id")
            or ev.get("normalized_marker_name")
            or ev.get("entity_name")
            or ev.get("body_region_group")
            or ""
        )
        rows.append(
            {
                "frame_start": ev.get("start_frame"),
                "frame_end": ev.get("end_frame"),
                "duration_frames": ev.get("duration_frames"),
                "duration_seconds": ev.get("duration_seconds"),
                "qc_type": qc_type,
                "reason": ev.get("reason"),
                "marker_or_region": marker_or_region,
                "normalized_marker_name": ev.get("normalized_marker_name"),
                "attached_bone": ev.get("attached_bone"),
                "attached_bone_canonical": ev.get("attached_bone_canonical"),
                "related_joint_family": ev.get("related_joint_family"),
                "adjacent_joint_family": None,
                "mapping_source": ev.get("mapping_source"),
                "mapping_confidence": ev.get("mapping_confidence"),
                "template_mapping_status": ev.get("template_mapping_status"),
                "source_layer": source,
                "included_in_user_review": included,
                "recommendation_impact": recommendation_impact,
            }
        )

    display = pd.DataFrame(rows, columns=list(QC_EVENT_DISPLAY_COLUMNS))
    # Filter to user-selected evidence types for compact display
    if not display.empty:
        l1_mask = display["source_layer"] == "layer1"
        l1_types = display.loc[l1_mask, "qc_type"].apply(
            lambda t: _normalize_qc_type_for_policy(str(t)) in evidence_policy.l1_evidence_types
            or str(t) in evidence_policy.l1_evidence_types
        )
        keep_l1 = l1_mask & l1_types.astype(bool)
        keep_l2 = display["source_layer"] == "layer2"
        display = display.loc[keep_l1 | keep_l2].copy()
    return display


def _count_l1_risk_frames_for_family(
    layer1_events: pd.DataFrame,
    joint_family: str,
    qc_mask_window: pd.DataFrame,
    *,
    gap_policy: GapPolicy,
) -> dict[str, int]:
    """Count gap/artifact frames related to a joint family via marker mapping."""
    if layer1_events.empty or joint_family == "unknown":
        return {"gap_0p5": 0, "gap_0p2": 0, "artifact_sigma": 0, "segment_swap": 0}

    family_markers = layer1_events.loc[
        layer1_events["related_joint_family"] == joint_family, "normalized_marker_name"
    ].dropna()
    family_markers = set(family_markers.astype(str).unique())

    counts = {"gap_0p5": 0, "gap_0p2": 0, "artifact_sigma": 0, "segment_swap": 0}
    for _, ev in layer1_events.iterrows():
        if ev.get("related_joint_family") != joint_family:
            continue
        qc_type = str(ev.get("qc_type", ""))
        norm = _normalize_qc_type_for_policy(qc_type)
        if norm == "gap_0p5":
            counts["gap_0p5"] += int(ev.get("duration_frames") or 1)
        elif norm == "gap_0p2":
            counts["gap_0p2"] += int(ev.get("duration_frames") or 1)
        elif norm == "artifact_sigma":
            counts["artifact_sigma"] += int(ev.get("duration_frames") or 1)
        elif norm == "segment_swap":
            counts["segment_swap"] += int(ev.get("duration_frames") or 1)

    # Also count qc_mask flags for markers in family (frame-level events without marker name)
    _ = family_markers, qc_mask_window  # reserved for future marker-level join
    return counts


def build_layer2_link_scope_display(
    per_link_summary: pd.DataFrame,
    layer1_window_events: pd.DataFrame,
    qc_mask_window: pd.DataFrame,
    *,
    export_scope_policy: ExportScopePolicy,
    gap_policy: GapPolicy,
    mapping_version: str,
    template_mapping_status: str,
    n_window_frames: int,
) -> pd.DataFrame:
    """Build Link / Joint Decision Table filtered to export scope by default."""
    if per_link_summary.empty:
        return pd.DataFrame(columns=list(LAYER2_LINK_SCOPE_DISPLAY_COLUMNS))

    rows: list[dict[str, Any]] = []
    for _, link in per_link_summary.iterrows():
        feature_scope = str(link["feature_scope"])
        included = export_scope_policy.link_included(feature_scope)
        if not included and export_scope_policy.export_scope != "all_links_audit":
            continue

        family = _link_family_from_bones(
            str(link["parent_canonical"]), str(link["child_canonical"])
        )
        risk = _count_l1_risk_frames_for_family(
            layer1_window_events, family, qc_mask_window, gap_policy=gap_policy
        )
        n_frames = int(link.get("n_rows") or n_window_frames or 1)

        def pct(n: int) -> float:
            return round(100.0 * n / n_frames, 4) if n_frames else 0.0

        rows.append(
            {
                "link_id": link["link_id"],
                "link_or_joint": f"{link['parent_canonical']}->{link['child_canonical']}",
                "parent_canonical": link["parent_canonical"],
                "child_canonical": link["child_canonical"],
                "family": family,
                "feature_scope": feature_scope,
                "view_scope": export_scope_policy.export_scope,
                "n_gap_0p5_related_frames": risk["gap_0p5"],
                "gap_0p5_related_percent": pct(risk["gap_0p5"]),
                "n_gap_0p2_related_frames": risk["gap_0p2"],
                "gap_0p2_related_percent": pct(risk["gap_0p2"]),
                "gap_0p2_counted_in_burden": gap_policy.gap_0p2_counted_in_burden,
                "artifact_sigma_related_percent": pct(risk["artifact_sigma"]),
                "segment_swap_related_percent": pct(risk["segment_swap"]),
                "layer2_usable_percent": link.get("percent_analysis_eligible", 0.0),
                "layer2_masked_percent": link.get("percent_masked", 0.0),
                "mapping_version": mapping_version,
                "template_mapping_status": template_mapping_status,
                "recommendation_placeholder": _recommendation_placeholder(
                    feature_scope,
                    str(link.get("stage08_policy", "")),
                    bool(link.get("requires_manual_review", False)),
                ),
                "export_scope": export_scope_policy.export_scope,
                "included_by_export_scope": included,
                "selection_default": included,
                "user_override": None,
                "user_note": None,
            }
        )

    return pd.DataFrame(rows, columns=list(LAYER2_LINK_SCOPE_DISPLAY_COLUMNS))


def _link_family_from_bones(parent: str, child: str) -> str:
    """Derive a coarse joint family label from Layer 2 parent-child bones."""
    pairs = {
        ("Neck", "Head"): "head_neck",
        ("Ab", "Chest"): "trunk_chest",
        ("Chest", "Neck"): "trunk_chest",
        ("LShoulder", "LUArm"): "left_shoulder_arm",
        ("LUArm", "LFArm"): "left_elbow_forearm",
        ("LFArm", "LHand"): "left_wrist_hand",
        ("RShoulder", "RUArm"): "right_shoulder_arm",
        ("RUArm", "RFArm"): "right_elbow_forearm",
        ("RFArm", "RHand"): "right_wrist_hand",
        ("LThigh", "LShin"): "left_thigh_knee",
        ("LShin", "LFoot"): "left_shank_ankle",
        ("RThigh", "RShin"): "right_thigh_knee",
        ("RShin", "RFoot"): "right_shank_ankle",
    }
    return pairs.get((parent, child), "unknown")


def build_layer1_marker_family_risk(
    layer1_window_events: pd.DataFrame,
    *,
    session_id: str,
    run_label: str,
    mapping_version: str,
    template_mapping_status: str,
    gap_policy: GapPolicy,
) -> pd.DataFrame:
    """Aggregate Layer 1 marker-family risk per marker/entity."""
    if layer1_window_events.empty:
        return pd.DataFrame(columns=list(LAYER1_MARKER_FAMILY_RISK_COLUMNS))

    group_cols = ["marker_raw_name", "normalized_marker_name", "related_joint_family"]
    available = [c for c in group_cols if c in layer1_window_events.columns]
    if not available:
        return pd.DataFrame(columns=list(LAYER1_MARKER_FAMILY_RISK_COLUMNS))

    rows: list[dict[str, Any]] = []
    for key, group in layer1_window_events.groupby(available, dropna=False):
        if not isinstance(key, tuple):
            key = (key,)
        marker_raw = key[0] if len(key) > 0 else None
        normalized = key[1] if len(key) > 1 else None
        family = key[2] if len(key) > 2 else "unknown"
        first = group.iloc[0]

        def count_type(qc_type: str) -> int:
            norm = _normalize_qc_type_for_policy(qc_type)
            return int(
                group["qc_type"]
                .apply(lambda t: _normalize_qc_type_for_policy(str(t)) == norm)
                .sum()
            )

        rows.append(
            {
                "session_id": session_id,
                "run_label": run_label,
                "marker_or_entity": marker_raw or first.get("entity_name") or "unknown",
                "normalized_marker_name": normalized,
                "body_region_group": first.get("body_region_group"),
                "side": None,
                "attached_bone": first.get("attached_bone"),
                "attached_bone_canonical": first.get("attached_bone_canonical"),
                "joint_family": family,
                "adjacent_joint_family": first.get("adjacent_joint_family"),
                "mapping_source": first.get("mapping_source"),
                "mapping_confidence": first.get("mapping_confidence"),
                "mapping_version": mapping_version,
                "template_mapping_status": template_mapping_status,
                "n_events": len(group),
                "n_frames_affected": int(group["duration_frames"].fillna(1).sum()),
                "gap_0p5_frames": count_type("marker_gap_0p5"),
                "gap_0p2_frames": count_type("marker_gap_0p2"),
                "artifact_sigma_frames": count_type("artifact_sigma"),
                "segment_swap_frames": count_type("segment_swap"),
                "severity_summary": str(group["severity"].mode().iloc[0])
                if not group["severity"].mode().empty
                else "",
                "recommendation_impact": "regional_risk_overlay",
                "notes": "",
            }
        )

    return pd.DataFrame(rows, columns=list(LAYER1_MARKER_FAMILY_RISK_COLUMNS))


def build_combined_qc_event_summary(
    combined_events: pd.DataFrame,
    per_link_summary: pd.DataFrame,
) -> pd.DataFrame:
    """Grouped summary of combined QC events."""
    rows: list[dict[str, Any]] = []

    if not combined_events.empty:
        l1 = combined_events[combined_events["source_layer"] == "layer1"]
        if not l1.empty:
            group_cols = [
                "source_layer",
                "qc_type",
                "severity",
                "reason",
                "related_joint_family",
                "mapping_source",
                "mapping_confidence",
                "template_mapping_status",
            ]
            for keys, grp in l1.groupby(group_cols, dropna=False):
                if not isinstance(keys, tuple):
                    keys = (keys,)
                row = dict(zip(group_cols, keys, strict=False))
                row["feature_scope"] = None
                row["joint_family"] = row.pop("related_joint_family")
                row["n_events"] = len(grp)
                rows.append(row)

    if not per_link_summary.empty:
        for _, link in per_link_summary.iterrows():
            rows.append(
                {
                    "source_layer": "layer2",
                    "qc_type": "link_usability",
                    "severity": "info",
                    "reason": str(link.get("stage08_policy", "")),
                    "joint_family": _link_family_from_bones(
                        str(link["parent_canonical"]), str(link["child_canonical"])
                    ),
                    "mapping_source": "not_applicable",
                    "mapping_confidence": "n/a",
                    "template_mapping_status": "not_applicable",
                    "feature_scope": link["feature_scope"],
                    "n_events": int(link.get("n_rows", 0)),
                }
            )

    if not rows:
        return pd.DataFrame(columns=list(COMBINED_QC_EVENT_SUMMARY_COLUMNS))
    return pd.DataFrame(rows, columns=list(COMBINED_QC_EVENT_SUMMARY_COLUMNS))


def build_window_qc_summary_display(
    *,
    session_key: str,
    start_frame: int,
    end_frame: int,
    frame_rate_hz: float,
    layer1_summary: dict[str, Any],
    layer2_summary: dict[str, Any],
    qc_event_display: pd.DataFrame,
    layer1_marker_risk: pd.DataFrame,
    gap_policy: GapPolicy,
    export_scope_policy: ExportScopePolicy,
    mapping_version: str,
    mapping_source: str,
    template_mapping_status: str,
) -> pd.DataFrame:
    """Build window-level QC summary display row."""
    duration_frames = end_frame - start_frame + 1
    duration_seconds = duration_frames / frame_rate_hz

    n_unmapped_markers = 0
    n_unmapped_events = 0
    if not layer1_marker_risk.empty and "mapping_source" in layer1_marker_risk.columns:
        unmapped = layer1_marker_risk["mapping_source"] == "unmapped"
        n_unmapped_markers = int(layer1_marker_risk.loc[unmapped, "marker_or_entity"].nunique())
        n_unmapped_events = int(layer1_marker_risk.loc[unmapped, "n_events"].sum())

    if not qc_event_display.empty:
        n_l1_display = len(qc_event_display[qc_event_display["source_layer"] == "layer1"])
        n_l2_display = len(qc_event_display[qc_event_display["source_layer"] == "layer2"])
    else:
        n_l1_display = 0
        n_l2_display = 0

    exclude_pct = layer1_summary.get("percent_exclude", 0.0)
    caution_pct = layer1_summary.get("percent_caution", 0.0)
    if exclude_pct > 5:
        overall_status = "exclude_burden"
    elif caution_pct > 10:
        overall_status = "caution_burden"
    else:
        overall_status = "acceptable"

    row = {
        "session_key": session_key,
        "frame_start": start_frame,
        "frame_end": end_frame,
        "duration_frames": duration_frames,
        "duration_seconds": round(duration_seconds, 4),
        "gap_policy": gap_policy.policy,
        "export_scope": export_scope_policy.export_scope,
        "total_frames": layer1_summary.get("n_window_frames", duration_frames),
        "gap_0p5_percent": layer1_summary.get("gap_0p5_percent", 0.0),
        "gap_0p2_percent": layer1_summary.get("gap_0p2_percent", 0.0),
        "gap_0p2_counted_in_burden": gap_policy.gap_0p2_counted_in_burden,
        "artifact_sigma_percent": layer1_summary.get("artifact_sigma_percent", 0.0),
        "segment_swap_percent": layer1_summary.get("segment_swap_percent", 0.0),
        "overall_raw_qc_status": overall_status,
        "layer2_core_usable_percent": layer2_summary.get("layer2_core_usable_percent", 0.0),
        "layer2_review_usable_percent": layer2_summary.get("layer2_review_usable_percent", 0.0),
        "layer2_excluded_usable_percent": layer2_summary.get("layer2_excluded_usable_percent", 0.0),
        "n_layer1_display_events": n_l1_display,
        "n_layer2_display_events": n_l2_display,
        "n_unmapped_markers": n_unmapped_markers,
        "n_unmapped_events": n_unmapped_events,
        "mapping_version": mapping_version,
        "mapping_source": mapping_source,
        "template_mapping_status": template_mapping_status,
    }
    return pd.DataFrame([row], columns=list(WINDOW_QC_SUMMARY_DISPLAY_COLUMNS))


def write_window_review_outputs(
    out_dir: str | Path,
    *,
    validation_result: ValidationResult,
    identity: SessionIdentity,
    layer1_bundle: Layer1Bundle,
    layer2_bundle: Layer2Bundle,
    start_frame: int,
    end_frame: int,
    layer1_summary: dict[str, Any],
    layer2_summary: dict[str, Any],
    combined_events: pd.DataFrame,
    gap_status: dict[str, str] | None = None,
    gap_policy: GapPolicy | None = None,
    export_scope_policy: ExportScopePolicy | None = None,
    evidence_policy: QCEvidencePolicy | None = None,
    mapper: MarkerFamilyMapper | None = None,
    layer1_window_events: pd.DataFrame | None = None,
) -> Path:
    """Write window review CSV/JSON/MD outputs (Phase A+ display tables)."""
    gap_policy = gap_policy or GapPolicy()
    export_scope_policy = export_scope_policy or ExportScopePolicy()
    evidence_policy = evidence_policy or QCEvidencePolicy()
    mapper = mapper or MarkerFamilyMapper()

    mapping_version = mapper.mapping_version
    template_mapping_status = mapper.session_mapping_status
    mapping_source = (
        "session_datadescriptions_optional"
        if mapper.datadescriptions_used
        else "marker_name_heuristic"
    )

    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    frame_rate = float(layer1_bundle.manifest.get("frame_rate_hz", 120.0))
    qc_mask_window = layer1_bundle.qc_mask[
        layer1_bundle.qc_mask["frame"].between(start_frame, end_frame)
    ]

    qc_event_display = build_qc_event_display(
        combined_events,
        evidence_policy=evidence_policy,
        gap_policy=gap_policy,
    )
    link_scope_display = build_layer2_link_scope_display(
        layer2_summary["per_link_summary"],
        layer1_window_events if layer1_window_events is not None else pd.DataFrame(),
        qc_mask_window,
        export_scope_policy=export_scope_policy,
        gap_policy=gap_policy,
        mapping_version=mapping_version,
        template_mapping_status=template_mapping_status,
        n_window_frames=layer1_summary.get("n_window_frames", 0),
    )
    marker_family_risk = build_layer1_marker_family_risk(
        layer1_window_events if layer1_window_events is not None else pd.DataFrame(),
        session_id=identity.session_key,
        run_label=identity.layer2_run_label,
        mapping_version=mapping_version,
        template_mapping_status=template_mapping_status,
        gap_policy=gap_policy,
    )
    event_summary = build_combined_qc_event_summary(
        combined_events,
        layer2_summary["per_link_summary"],
    )
    window_summary_display = build_window_qc_summary_display(
        session_key=identity.session_key,
        start_frame=start_frame,
        end_frame=end_frame,
        frame_rate_hz=frame_rate,
        layer1_summary=layer1_summary,
        layer2_summary=layer2_summary,
        qc_event_display=qc_event_display,
        layer1_marker_risk=marker_family_risk,
        gap_policy=gap_policy,
        export_scope_policy=export_scope_policy,
        mapping_version=mapping_version,
        mapping_source=mapping_source,
        template_mapping_status=template_mapping_status,
    )

    validation_summary = {
        "safe_to_open": validation_result.safe_to_open,
        "blocking_errors": validation_result.blocking_errors,
        "warnings": validation_result.warnings,
        "identity": {
            "session_key": identity.session_key,
            "layer1_run_key": identity.layer1_run_key,
            "layer2_session_id": identity.layer2_session_id,
            "layer2_run_label": identity.layer2_run_label,
        },
        "alignment": {
            "exact_frame_alignment": (
                validation_result.alignment.exact_frame_alignment
                if validation_result.alignment
                else None
            ),
            "canonical_join_key": (
                validation_result.alignment.canonical_join_key
                if validation_result.alignment
                else "frame"
            ),
        },
        "window": {"start_frame": start_frame, "end_frame": end_frame},
        "gap_policy": gap_policy.policy,
        "qc_evidence_policy": {
            "l1_evidence_types": sorted(evidence_policy.l1_evidence_types),
            "l2_evidence_types": sorted(evidence_policy.l2_evidence_types),
        },
        "export_scope": export_scope_policy.export_scope,
        "mapping_version": mapping_version,
        "mapping_source": mapping_source,
        "datadescriptions_used": mapper.datadescriptions_used,
        "template_mapping_status": template_mapping_status,
        "n_unmapped_markers": int(window_summary_display["n_unmapped_markers"].iloc[0]),
        "gap_files_status": gap_status or {},
    }
    with (out_path / "window_validation_summary.json").open("w", encoding="utf-8") as fh:
        json.dump(validation_summary, fh, indent=2)

    window_summary_display.to_csv(out_path / "window_qc_summary_display.csv", index=False)
    qc_event_display.to_csv(out_path / "qc_event_display.csv", index=False)
    link_scope_display.to_csv(out_path / "layer2_link_scope_display.csv", index=False)
    marker_family_risk.to_csv(out_path / "layer1_marker_family_risk.csv", index=False)
    event_summary.to_csv(out_path / "combined_qc_event_summary.csv", index=False)
    combined_events.to_csv(out_path / "combined_qc_events.csv", index=False)

    duration_sec = (end_frame - start_frame + 1) / frame_rate
    n_unmapped = int(window_summary_display["n_unmapped_markers"].iloc[0])

    exact_align = (
        validation_result.alignment.exact_frame_alignment
        if validation_result.alignment
        else "unknown"
    )

    report_lines = [
        "# Window QC Review Report",
        "",
        "## Session identity",
        "",
        f"- Session key: `{identity.session_key}`",
        f"- Layer 1 run_key: `{identity.layer1_run_key}`",
        f"- Layer 2 session_id: `{identity.layer2_session_id}`",
        f"- Layer 2 run_label: `{identity.layer2_run_label}`",
        "",
        "## Input folders",
        "",
        f"- Layer 1: `{layer1_bundle.source_dir}`",
        f"- Layer 2: `{layer2_bundle.source_dir}`",
        "",
        "## Selected window",
        "",
        f"- Frames: {start_frame}..{end_frame} (inclusive)",
        f"- Duration (sec): {duration_sec:.4f}",
        f"- Window frames: {layer1_summary['n_window_frames']}",
        "",
        "## Review policies",
        "",
        f"- Gap policy: `{gap_policy.policy}`",
        f"- Export scope: `{export_scope_policy.export_scope}`",
        f"- Mapping version: `{mapping_version}`",
        f"- Mapping source: `{mapping_source}`",
        f"- Template mapping status: `{template_mapping_status}`",
        f"- DataDescriptions used: `{mapper.datadescriptions_used}`",
        "",
        "## Validation",
        "",
        f"- Safe to open: `{validation_result.safe_to_open}`",
        f"- Exact frame alignment: `{exact_align}`",
        "",
        "## Layer 1 summary",
        "",
        f"- Use frames: {layer1_summary['n_use_frames']} "
        f"({layer1_summary['percent_use']}%)",
        f"- Caution frames: {layer1_summary['n_caution_frames']} "
        f"({layer1_summary['percent_caution']}%)",
        f"- Exclude frames: {layer1_summary['n_exclude_frames']} "
        f"({layer1_summary['percent_exclude']}%)",
        f"- gap_0p2 counted in burden: `{gap_policy.gap_0p2_counted_in_burden}`",
        "",
        "### Flag counts",
        "",
    ]
    for col, count in layer1_summary.get("flag_counts", {}).items():
        report_lines.append(f"- {col}: {count}")

    report_lines.extend(
        [
            "",
            "## Layer 2 summary",
            "",
            f"- Rows: {layer2_summary['n_rows']}",
            f"- Links: {layer2_summary['n_links']}",
            f"- Analysis eligible rows: {layer2_summary['n_analysis_eligible_rows']} "
            f"({layer2_summary['percent_analysis_eligible']}%)",
            f"- Core usable %: {layer2_summary.get('layer2_core_usable_percent', 0.0)}",
            "",
            "## Display tables",
            "",
            f"- QC event display rows: {len(qc_event_display)}",
            f"- Link scope display rows: {len(link_scope_display)}",
            f"- Combined audit events: {len(combined_events)}",
            f"- Unmapped markers: {n_unmapped}",
            "",
            "## Limitations",
            "",
            "Layer 1 marker QC is regional risk evidence only. "
            "It is not mapped to specific Layer 2 links and does not invalidate joints.",
            "DataDescriptions improves marker-to-bone interpretation when provided; "
            "Layer 2 remains authoritative for kinematic parent-child links.",
            "",
        ]
    )

    if n_unmapped > 0:
        report_lines.extend(
            [
                "## Unmapped evidence",
                "",
                "Some Layer 1 QC evidence could not be assigned to a joint family. "
                "This does not automatically invalidate the window, but it should be reviewed.",
                "",
            ]
        )

    if gap_status:
        report_lines.extend(["## Optional gap files", ""])
        for name, status in gap_status.items():
            report_lines.append(f"- {name}: {status}")

    (out_path / "window_review_report.md").write_text("\n".join(report_lines), encoding="utf-8")
    return out_path
