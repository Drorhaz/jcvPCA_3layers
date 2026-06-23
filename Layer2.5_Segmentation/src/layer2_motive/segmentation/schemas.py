"""Schema constants, enums, and typed bundles for segmentation V1."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import pandas as pd

# --- Layer 1 required files ---
LAYER1_REQUIRED_FILES = (
    "layer1_segmentation_notebook_manifest.json",
    "qc_mask.csv",
)

LAYER1_OPTIONAL_FILES = (
    "qc_mask_intervals.csv",
    "artifact_events.csv",
    "artifacts_by_segment.csv",
    "gaps_over_0p2s.csv",
    "gaps_over_0p5s.csv",
    "quarantined_markers.csv",
)

LAYER1_MANIFEST_REQUIRED_KEYS = (
    "run_key",
    "frame_rate_hz",
    "n_frames",
    "frame_index_column",
)

# --- Layer 2 required files ---
LAYER2_REQUIRED_FILES = (
    "layer2_session_filtered_rotvecs.parquet",
    "layer2_session_link_manifest.csv",
    "layer2_session_summary.json",
)

LAYER2_OPTIONAL_FILES = (
    "layer2_session_integrity_audit.csv",
    "layer2_session_report.md",
    "layer2_session_assumptions_and_limitations.md",
    "README.md",
)

# --- Layer 1 qc_mask columns ---
LAYER1_QC_MASK_REQUIRED_COLUMNS = ("frame", "time_s", "reason")

LAYER1_QC_MASK_EXPECTED_COLUMNS = (
    "flag_gap_0p2",
    "flag_gap_0p5",
    "flag_artifact_sigma",
    "flag_segment_swap",
    "flag_edge_effect",
)

# --- Layer 2 parquet columns ---
LAYER2_PARQUET_REQUIRED_COLUMNS = (
    "session_id",
    "run_label",
    "frame",
    "link_id",
    "parent_canonical",
    "child_canonical",
    "feature_scope",
    "included_in_v0",
    "requires_manual_review",
    "stage07_jump_status",
    "stage07_jump_magnitude_rad",
    "stage08_policy",
    "stage08_within_jump_context_window",
    "stage08_analysis_eligible",
    "stage08_mask_reason",
    "stage08_output_scope",
    "rx_filtered_native",
    "ry_filtered_native",
    "rz_filtered_native",
    "rotvec_norm_filtered_native",
    "rx_filtered_analysis",
    "ry_filtered_analysis",
    "rz_filtered_analysis",
    "rotvec_norm_filtered_analysis",
)

LAYER2_PARQUET_EXPECTED_COLUMNS = ("time_sec",)

# --- Layer 2 link manifest columns ---
LAYER2_LINK_MANIFEST_REQUIRED_COLUMNS = (
    "session_id",
    "run_label",
    "link_id",
    "parent_canonical",
    "child_canonical",
    "feature_scope",
    "included_in_v0",
    "requires_manual_review",
    "stage08_policy",
    "stage08_output_scope",
    "percent_analysis_eligible",
    "recommended_segmentation_default",
    "short_explanation",
)

# --- Allowed values ---
RECOMMENDATION_CLASSES = frozenset(
    {
        "candidate_include",
        "include_with_caution",
        "manual_review",
        "exclude_recommended",
        "excluded_by_policy",
        "blocked_needs_review",
    }
)

SEVERITY_CLASSES = frozenset(
    {
        "info",
        "caution",
        "exclude",
        "minor",
        "moderate",
        "severe",
    }
)

FEATURE_SCOPES = frozenset(
    {
        "core_candidate",
        "review_provisional",
        "excluded_distal",
        "excluded_toe",
    }
)

MAPPING_CONFIDENCE = frozenset(
    {
        "n/a",
        "body_region_only",
        "body_region_overlay",
        "unmapped",
        # Phase A+ mapping confidence values
        "attached_bone_observed_but_template_unverified",
        "medium",
        "low",
        "template_uncertain",
    }
)

MAPPING_SOURCE_VALUES = frozenset(
    {
        "session_datadescriptions_optional",
        "marker_name_heuristic",
        "body_region_group",
        "unmapped",
    }
)

TEMPLATE_MAPPING_STATUS_VALUES = frozenset(
    {
        "session_datadescriptions_used_unverified",
        "missing_datadescriptions_fallback_to_heuristic",
        "not_applicable",
    }
)

JOINT_FAMILIES = frozenset(
    {
        "head_neck",
        "trunk_chest",
        "pelvis_hip",
        "left_shoulder_arm",
        "left_elbow_forearm",
        "left_wrist_hand",
        "right_shoulder_arm",
        "right_elbow_forearm",
        "right_wrist_hand",
        "left_thigh_knee",
        "left_shank_ankle",
        "left_foot",
        "right_thigh_knee",
        "right_shank_ankle",
        "right_foot",
        "bilateral_upper_limb",
        "bilateral_lower_limb",
        "fingers_excluded",
        "toes_excluded",
        "unknown",
    }
)

GAP_POLICIES = frozenset({"strict", "relaxed"})

EXPORT_SCOPES = frozenset(
    {
        "core_candidate",
        "core_plus_review",
        "all_non_excluded",
        "all_links_audit",
    }
)

DEFAULT_L1_EVIDENCE_TYPES = frozenset(
    {
        "gap_0p5",
        "gap_0p2",
        "artifact_sigma",
        "segment_swap",
    }
)

DEFAULT_L2_EVIDENCE_TYPES = frozenset(
    {
        "stage07_jump",
        "stage08_masked",
        "stage08_eligibility",
        "block_filter",
        "manual_review",
    }
)

LAYER1_NORMALIZED_EVENT_COLUMNS = (
    "session_key",
    "source_layer",
    "source_file",
    "qc_type",
    "severity",
    "frame",
    "start_frame",
    "end_frame",
    "time_sec",
    "start_time_sec",
    "end_time_sec",
    "duration_frames",
    "duration_seconds",
    "entity_type",
    "entity_name",
    "marker_raw_name",
    "body_region_group",
    "reason",
    "notes",
    # Phase A+ marker-family overlay columns
    "normalized_marker_name",
    "attached_bone",
    "attached_bone_canonical",
    "related_joint_family",
    "adjacent_joint_family",
    "mapping_source",
    "mapping_confidence",
    "template_mapping_status",
)

COMBINED_QC_EVENT_COLUMNS = (
    "source_layer",
    "frame",
    "start_frame",
    "end_frame",
    "time_sec",
    "start_time_sec",
    "end_time_sec",
    "entity_type",
    "entity_id",
    "entity_name",
    "link_id",
    "parent_canonical",
    "child_canonical",
    "body_region_group",
    "qc_type",
    "severity",
    "reason",
    "mapping_confidence",
    "recommended_action",
    "duration_frames",
    "duration_seconds",
    # Phase A+ marker-family overlay columns
    "normalized_marker_name",
    "attached_bone",
    "attached_bone_canonical",
    "related_joint_family",
    "mapping_source",
    "mapping_version",
    "template_mapping_status",
)

WINDOW_QC_SUMMARY_DISPLAY_COLUMNS = (
    "session_key",
    "frame_start",
    "frame_end",
    "duration_frames",
    "duration_seconds",
    "gap_policy",
    "export_scope",
    "total_frames",
    "gap_0p5_percent",
    "gap_0p2_percent",
    "gap_0p2_counted_in_burden",
    "artifact_sigma_percent",
    "segment_swap_percent",
    "overall_raw_qc_status",
    "layer2_core_usable_percent",
    "layer2_review_usable_percent",
    "layer2_excluded_usable_percent",
    "n_layer1_display_events",
    "n_layer2_display_events",
    "n_unmapped_markers",
    "n_unmapped_events",
    "mapping_version",
    "mapping_source",
    "template_mapping_status",
)

QC_EVENT_DISPLAY_COLUMNS = (
    "frame_start",
    "frame_end",
    "duration_frames",
    "duration_seconds",
    "qc_type",
    "reason",
    "marker_or_region",
    "normalized_marker_name",
    "attached_bone",
    "attached_bone_canonical",
    "related_joint_family",
    "adjacent_joint_family",
    "mapping_source",
    "mapping_confidence",
    "template_mapping_status",
    "source_layer",
    "included_in_user_review",
    "recommendation_impact",
)

LAYER2_LINK_SCOPE_DISPLAY_COLUMNS = (
    "link_id",
    "link_or_joint",
    "parent_canonical",
    "child_canonical",
    "family",
    "feature_scope",
    "view_scope",
    "n_gap_0p5_related_frames",
    "gap_0p5_related_percent",
    "n_gap_0p2_related_frames",
    "gap_0p2_related_percent",
    "gap_0p2_counted_in_burden",
    "artifact_sigma_related_percent",
    "segment_swap_related_percent",
    "layer2_usable_percent",
    "layer2_masked_percent",
    "mapping_version",
    "template_mapping_status",
    "recommendation_placeholder",
    "export_scope",
    "included_by_export_scope",
    "selection_default",
    "user_override",
    "user_note",
)

LAYER1_MARKER_FAMILY_RISK_COLUMNS = (
    "session_id",
    "run_label",
    "marker_or_entity",
    "normalized_marker_name",
    "body_region_group",
    "side",
    "attached_bone",
    "attached_bone_canonical",
    "joint_family",
    "adjacent_joint_family",
    "mapping_source",
    "mapping_confidence",
    "mapping_version",
    "template_mapping_status",
    "n_events",
    "n_frames_affected",
    "gap_0p5_frames",
    "gap_0p2_frames",
    "artifact_sigma_frames",
    "segment_swap_frames",
    "severity_summary",
    "recommendation_impact",
    "notes",
)

COMBINED_QC_EVENT_SUMMARY_COLUMNS = (
    "source_layer",
    "qc_type",
    "severity",
    "reason",
    "joint_family",
    "mapping_source",
    "mapping_confidence",
    "template_mapping_status",
    "feature_scope",
    "n_events",
)

LAYER1_FLAG_QC_TYPES = {
    "flag_gap_0p2": "marker_gap_0p2",
    "flag_gap_0p5": "marker_gap_0p5",
    "flag_artifact_sigma": "artifact_sigma",
    "flag_segment_swap": "segment_swap",
    "flag_edge_effect": "edge_effect",
}

ENTITY_TYPES = frozenset(
    {
        "frame",
        "marker",
        "segment",
        "link",
        "interval",
    }
)

CheckStatus = Literal["pass", "warn", "fail"]

CANONICAL_JOIN_KEY = "frame"


@dataclass(frozen=True)
class RecommendationThresholds:
    include_min: float = 95.0
    caution_min: float = 90.0
    blocked_mask_frac: float = 0.5


@dataclass(frozen=True)
class GapPolicy:
    policy: str = "strict"

    @property
    def gap_0p2_counted_in_burden(self) -> bool:
        return self.policy == "strict"


@dataclass(frozen=True)
class QCEvidencePolicy:
    l1_evidence_types: frozenset[str] = DEFAULT_L1_EVIDENCE_TYPES
    l2_evidence_types: frozenset[str] = DEFAULT_L2_EVIDENCE_TYPES

    def l1_type_included(self, qc_type: str) -> bool:
        normalized = _normalize_qc_type_for_policy(qc_type)
        return normalized in self.l1_evidence_types

    def l2_type_included(self, qc_type: str, row: dict | None = None) -> bool:
        if row is None:
            return True
        if "stage07_jump" in self.l2_evidence_types:
            if row.get("stage07_jump_status") in ("warning", "fail"):
                return True
        if "stage08_masked" in self.l2_evidence_types:
            if not row.get("stage08_analysis_eligible"):
                return True
        if "stage08_eligibility" in self.l2_evidence_types:
            if row.get("stage08_within_jump_context_window"):
                return True
        if "block_filter" in self.l2_evidence_types:
            if row.get("stage08_policy") == "block_filter":
                return True
        if "manual_review" in self.l2_evidence_types:
            manual = row.get("requires_manual_review")
            provisional = row.get("feature_scope") == "review_provisional"
            if manual or provisional:
                return True
        return False


@dataclass(frozen=True)
class ExportScopePolicy:
    export_scope: str = "core_candidate"

    def link_included(self, feature_scope: str) -> bool:
        if self.export_scope == "core_candidate":
            return feature_scope == "core_candidate"
        if self.export_scope == "core_plus_review":
            return feature_scope in {"core_candidate", "review_provisional"}
        if self.export_scope == "all_non_excluded":
            return feature_scope not in {"excluded_distal", "excluded_toe"}
        if self.export_scope == "all_links_audit":
            return True
        return False


def _normalize_qc_type_for_policy(qc_type: str) -> str:
    mapping = {
        "gaps_over_0p5": "gap_0p5",
        "gaps_over_0p2": "gap_0p2",
        "marker_gap_0p2": "gap_0p2",
        "marker_gap_0p5": "gap_0p5",
        "artifact_sigma": "artifact_sigma",
        "segment_swap": "segment_swap",
        "edge_effect": "edge_effect",
        "frame_status": "frame_status",
        "interval_status": "interval_status",
    }
    return mapping.get(qc_type, qc_type)


@dataclass
class SessionIdentity:
    session_key: str
    layer1_run_key: str
    layer2_session_id: str
    layer2_run_label: str
    layer1_subject_id: str | None = None
    layer1_session_id: str | None = None
    skeleton_template: str | None = None
    identity_override: bool = False


@dataclass
class FrameRangeInfo:
    start_frame: int
    end_frame: int
    n_frames: int
    start_time_sec: float | None = None
    end_time_sec: float | None = None
    time_source: str = "observed"


@dataclass
class AlignmentInfo:
    canonical_join_key: str = CANONICAL_JOIN_KEY
    layer1_frame_range: FrameRangeInfo | None = None
    layer2_frame_range: FrameRangeInfo | None = None
    overlap_start_frame: int | None = None
    overlap_end_frame: int | None = None
    overlap_n_frames: int | None = None
    exact_frame_alignment: bool = False
    frame_range_mismatch: bool = False
    time_drift_warning: bool = False
    time_drift_seconds: float | None = None
    alignment_uncertainty: str | None = None


@dataclass
class ValidationCheck:
    check_name: str
    status: CheckStatus
    details: str


@dataclass
class ValidationResult:
    checks: list[ValidationCheck] = field(default_factory=list)
    blocking_errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    safe_to_open: bool = False
    identity: SessionIdentity | None = None
    alignment: AlignmentInfo | None = None
    input_fingerprints: dict[str, str] = field(default_factory=dict)

    def add_check(self, check: ValidationCheck) -> None:
        self.checks.append(check)
        if check.status == "fail":
            self.blocking_errors.append(f"{check.check_name}: {check.details}")
        elif check.status == "warn":
            self.warnings.append(f"{check.check_name}: {check.details}")

    def finalize(self) -> None:
        self.safe_to_open = len(self.blocking_errors) == 0


@dataclass
class Layer1Bundle:
    source_dir: Path
    manifest: dict[str, Any]
    qc_mask: pd.DataFrame
    qc_mask_intervals: pd.DataFrame | None = None
    artifact_events: pd.DataFrame | None = None
    artifacts_by_segment: pd.DataFrame | None = None
    gaps_over_0p2s: pd.DataFrame | None = None
    gaps_over_0p5s: pd.DataFrame | None = None
    quarantined_markers: pd.DataFrame | None = None
    warnings: list[str] = field(default_factory=list)
    source_paths: dict[str, Path] = field(default_factory=dict)


@dataclass
class Layer2Bundle:
    source_dir: Path
    summary: dict[str, Any]
    parquet_df: pd.DataFrame
    link_manifest: pd.DataFrame
    integrity_audit: pd.DataFrame | None = None
    warnings: list[str] = field(default_factory=list)
    source_paths: dict[str, Path] = field(default_factory=dict)


def missing_columns(df: pd.DataFrame, required: tuple[str, ...]) -> list[str]:
    """Return required column names absent from df."""
    present = set(df.columns)
    return [c for c in required if c not in present]


def validate_columns(df: pd.DataFrame, required: tuple[str, ...], label: str) -> list[str]:
    """Return error messages for missing required columns."""
    missing = missing_columns(df, required)
    if not missing:
        return []
    return [f"{label} missing required columns: {', '.join(missing)}"]
