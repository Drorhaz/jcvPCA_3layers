"""Marker-family mapping with optional DataDescriptions enrichment and heuristic fallback."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Heuristic marker name -> (attached_bone, joint_family, adjacent_joint_family, confidence)
_HEURISTIC_MARKER_TABLE: dict[str, tuple[str, str, str | None, str]] = {
    # Left arm
    "LWristOut": ("LFArm", "left_elbow_forearm", "left_wrist_hand", "medium"),
    "LFArm": ("LFArm", "left_elbow_forearm", "left_wrist_hand", "medium"),
    "LElbowOut": ("LUArm", "left_shoulder_arm", "left_elbow_forearm", "medium"),
    "LUArmHigh": ("LUArm", "left_shoulder_arm", "left_elbow_forearm", "medium"),
    "LHandIn": ("LHand", "left_wrist_hand", None, "medium"),
    "LHandOut": ("LHand", "left_wrist_hand", None, "medium"),
    "LShoulderBack": ("LShoulder", "left_shoulder_arm", None, "medium"),
    "LShoulderTop": ("LShoulder", "left_shoulder_arm", None, "medium"),
    # Right arm
    "RWristOut": ("RFArm", "right_elbow_forearm", "right_wrist_hand", "medium"),
    "RFArm": ("RFArm", "right_elbow_forearm", "right_wrist_hand", "medium"),
    "RElbowOut": ("RUArm", "right_shoulder_arm", "right_elbow_forearm", "medium"),
    "RUArmHigh": ("RUArm", "right_shoulder_arm", "right_elbow_forearm", "medium"),
    "RHandIn": ("RHand", "right_wrist_hand", None, "medium"),
    "RHandOut": ("RHand", "right_wrist_hand", None, "medium"),
    "RShoulderBack": ("RShoulder", "right_shoulder_arm", None, "medium"),
    "RShoulderTop": ("RShoulder", "right_shoulder_arm", None, "medium"),
    # Trunk / chest
    "ChestTop": ("Chest", "trunk_chest", None, "medium"),
    "ChestLow": ("Chest", "trunk_chest", None, "medium"),
    "BackTop": ("Chest", "trunk_chest", None, "medium"),
    "BackLeft": ("Chest", "trunk_chest", None, "medium"),
    "BackRight": ("Chest", "trunk_chest", None, "medium"),
    # Waist / pelvis — template_uncertain
    "WaistLFront": ("671", "pelvis_hip", "trunk_chest", "template_uncertain"),
    "WaistRFront": ("671", "pelvis_hip", "trunk_chest", "template_uncertain"),
    "WaistLBack": ("671", "pelvis_hip", "trunk_chest", "template_uncertain"),
    "WaistRBack": ("671", "pelvis_hip", "trunk_chest", "template_uncertain"),
    "WaistCBack": ("671", "pelvis_hip", "trunk_chest", "template_uncertain"),
    # Head / neck
    "HeadTop": ("Head", "head_neck", None, "medium"),
    "HeadFront": ("Head", "head_neck", None, "medium"),
    "HeadLeft": ("Head", "head_neck", None, "medium"),
    "HeadRight": ("Head", "head_neck", None, "medium"),
    # Left leg
    "LThighFront": ("LThigh", "left_thigh_knee", None, "medium"),
    "LThighSide": ("LThigh", "left_thigh_knee", None, "medium"),
    "LKneeOut": ("LThigh", "left_thigh_knee", "left_shank_ankle", "medium"),
    "LShin": ("LShin", "left_shank_ankle", "left_foot", "medium"),
    "LAnkleOut": ("LShin", "left_shank_ankle", "left_foot", "medium"),
    "LHeel": ("LFoot", "left_foot", None, "medium"),
    "LToeIn": ("LFoot", "left_foot", None, "medium"),
    "LToeOut": ("LFoot", "left_foot", None, "medium"),
    "LToeTip": ("LToe", "toes_excluded", None, "low"),
    # Right leg
    "RThighFront": ("RThigh", "right_thigh_knee", None, "medium"),
    "RThighSide": ("RThigh", "right_thigh_knee", None, "medium"),
    "RKneeOut": ("RThigh", "right_thigh_knee", "right_shank_ankle", "medium"),
    "RShin": ("RShin", "right_shank_ankle", "right_foot", "medium"),
    "RAnkleOut": ("RShin", "right_shank_ankle", "right_foot", "medium"),
    "RHeel": ("RFoot", "right_foot", None, "medium"),
    "RToeIn": ("RFoot", "right_foot", None, "medium"),
    "RToeOut": ("RFoot", "right_foot", None, "medium"),
    "RToeTip": ("RToe", "toes_excluded", None, "low"),
    # Fingers
    "LThumb": ("LThumb2", "fingers_excluded", None, "low"),
    "LIndex": ("LIndex1", "fingers_excluded", None, "low"),
    "LPinky": ("LPinky1", "fingers_excluded", None, "low"),
    "RThumb": ("RThumb2", "fingers_excluded", None, "low"),
    "RIndex": ("RIndex1", "fingers_excluded", None, "low"),
    "RPinky": ("RPinky1", "fingers_excluded", None, "low"),
}

# Body region group -> joint family fallback
_BODY_REGION_TO_FAMILY: dict[str, str] = {
    "head": "head_neck",
    "neck": "head_neck",
    "trunk": "trunk_chest",
    "chest": "trunk_chest",
    "pelvis": "pelvis_hip",
    "hip": "pelvis_hip",
    "left_upper_arm": "left_shoulder_arm",
    "left_forearm": "left_elbow_forearm",
    "left_hand": "left_wrist_hand",
    "right_upper_arm": "right_shoulder_arm",
    "right_forearm": "right_elbow_forearm",
    "right_hand": "right_wrist_hand",
    "left_thigh": "left_thigh_knee",
    "left_shank": "left_shank_ankle",
    "left_foot": "left_foot",
    "right_thigh": "right_thigh_knee",
    "right_shank": "right_shank_ankle",
    "right_foot": "right_foot",
}

# Bone canonical -> joint family (for DataDescriptions path)
_BONE_TO_FAMILY: dict[str, tuple[str, str | None, str]] = {
    "Head": ("head_neck", None, "medium"),
    "Neck": ("head_neck", None, "medium"),
    "Chest": ("trunk_chest", None, "medium"),
    "Ab": ("trunk_chest", "pelvis_hip", "template_uncertain"),
    "671": ("pelvis_hip", "trunk_chest", "template_uncertain"),
    "LShoulder": ("left_shoulder_arm", None, "medium"),
    "LUArm": ("left_shoulder_arm", "left_elbow_forearm", "medium"),
    "LFArm": ("left_elbow_forearm", "left_wrist_hand", "medium"),
    "LHand": ("left_wrist_hand", None, "medium"),
    "RShoulder": ("right_shoulder_arm", None, "medium"),
    "RUArm": ("right_shoulder_arm", "right_elbow_forearm", "medium"),
    "RFArm": ("right_elbow_forearm", "right_wrist_hand", "medium"),
    "RHand": ("right_wrist_hand", None, "medium"),
    "LThigh": ("left_thigh_knee", None, "medium"),
    "LShin": ("left_shank_ankle", "left_foot", "medium"),
    "LFoot": ("left_foot", None, "medium"),
    "LToe": ("toes_excluded", None, "low"),
    "RThigh": ("right_thigh_knee", None, "medium"),
    "RShin": ("right_shank_ankle", "right_foot", "medium"),
    "RFoot": ("right_foot", None, "medium"),
    "RToe": ("toes_excluded", None, "low"),
    "LThumb1": ("fingers_excluded", None, "low"),
    "LThumb2": ("fingers_excluded", None, "low"),
    "LIndex1": ("fingers_excluded", None, "low"),
    "LPinky1": ("fingers_excluded", None, "low"),
    "RThumb1": ("fingers_excluded", None, "low"),
    "RThumb2": ("fingers_excluded", None, "low"),
    "RIndex1": ("fingers_excluded", None, "low"),
    "RPinky1": ("fingers_excluded", None, "low"),
    "Bone52": ("trunk_chest", "pelvis_hip", "template_uncertain"),
    "Bone53": ("trunk_chest", "pelvis_hip", "template_uncertain"),
    "Bone54": ("trunk_chest", None, "template_uncertain"),
    "Bone58": ("head_neck", None, "template_uncertain"),
}

_ASSET_PREFIX_RE = re.compile(r"^(?:T3_)?671[_:]?")


@dataclass(frozen=True)
class MarkerFamilyResult:
    normalized_marker_name: str | None
    side: str | None
    attached_bone: str | None
    attached_bone_canonical: str | None
    joint_family: str
    adjacent_joint_family: str | None
    mapping_source: str
    mapping_confidence: str
    template_mapping_status: str


def normalize_marker_name(name: str | None) -> str | None:
    """Strip asset prefix and return bare marker token."""
    if name is None or (isinstance(name, float) and str(name) == "nan"):
        return None
    raw = str(name).strip()
    if not raw:
        return None
    if ":" in raw:
        raw = raw.split(":", 1)[-1]
    raw = _ASSET_PREFIX_RE.sub("", raw)
    return raw or None


def canonicalize_bone_name(bone: str | None) -> str | None:
    """Strip asset prefix from attached bone name."""
    if bone is None:
        return None
    raw = str(bone).strip()
    if not raw:
        return None
    return _ASSET_PREFIX_RE.sub("", raw) or raw


def infer_side(marker_name: str | None) -> str | None:
    """Infer left/right from marker name prefix."""
    if not marker_name:
        return None
    if marker_name.startswith("L") and len(marker_name) > 1 and marker_name[1].isupper():
        return "left"
    if marker_name.startswith("R") and len(marker_name) > 1 and marker_name[1].isupper():
        return "right"
    return None


def load_session_datadescriptions_marker_map(
    path: str | Path,
) -> tuple[dict[str, str], dict[str, Any]]:
    """Parse session DataDescriptions CSV and return marker->bone map + metadata."""
    path = Path(path)
    marker_map: dict[str, str] = {}
    metadata: dict[str, Any] = {"skeleton_label": None, "n_bone_markers": 0, "n_bones": 0}

    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        for row in reader:
            if not row:
                continue
            row_type = row[0].strip() if row else ""
            if row_type == "Skeleton" and len(row) >= 2:
                metadata["skeleton_label"] = row[1].strip()
            elif row_type == "Bone":
                metadata["n_bones"] += 1
            elif row_type == "Bone Marker" and len(row) >= 3:
                marker_name = row[1].strip()
                attached_bone = row[2].strip()
                normalized = normalize_marker_name(marker_name)
                if normalized and attached_bone:
                    marker_map[normalized] = attached_bone
                    metadata["n_bone_markers"] += 1

    return marker_map, metadata


def _family_from_bone(
    bone_canonical: str,
) -> tuple[str, str | None, str]:
    """Derive joint family from canonical bone name."""
    if bone_canonical in _BONE_TO_FAMILY:
        return _BONE_TO_FAMILY[bone_canonical]
    # Waist/trunk bones with asset prefix stripped
    if bone_canonical in {"671", "Ab"}:
        return ("pelvis_hip", "trunk_chest", "template_uncertain")
    return ("unknown", None, "low")


def _family_from_heuristic(marker: str) -> MarkerFamilyResult | None:
    """Look up heuristic table for a normalized marker name."""
    if marker not in _HEURISTIC_MARKER_TABLE:
        return None
    bone, family, adjacent, confidence = _HEURISTIC_MARKER_TABLE[marker]
    return MarkerFamilyResult(
        normalized_marker_name=marker,
        side=infer_side(marker),
        attached_bone=bone,
        attached_bone_canonical=canonicalize_bone_name(bone),
        joint_family=family,
        adjacent_joint_family=adjacent,
        mapping_source="marker_name_heuristic",
        mapping_confidence=confidence,
        template_mapping_status="missing_datadescriptions_fallback_to_heuristic",
    )


def _family_from_body_region(body_region: str | None) -> MarkerFamilyResult | None:
    """Fallback to body_region_group when marker name is unknown."""
    if not body_region or str(body_region).strip() == "":
        return None
    region = str(body_region).strip().lower().replace(" ", "_")
    family = _BODY_REGION_TO_FAMILY.get(region)
    if not family:
        return None
    return MarkerFamilyResult(
        normalized_marker_name=None,
        side=None,
        attached_bone=None,
        attached_bone_canonical=None,
        joint_family=family,
        adjacent_joint_family=None,
        mapping_source="body_region_group",
        mapping_confidence="low",
        template_mapping_status="missing_datadescriptions_fallback_to_heuristic",
    )


def _unmapped_result(marker: str | None = None) -> MarkerFamilyResult:
    return MarkerFamilyResult(
        normalized_marker_name=marker,
        side=infer_side(marker) if marker else None,
        attached_bone=None,
        attached_bone_canonical=None,
        joint_family="unknown",
        adjacent_joint_family=None,
        mapping_source="unmapped",
        mapping_confidence="unmapped",
        template_mapping_status="missing_datadescriptions_fallback_to_heuristic",
    )


class MarkerFamilyMapper:
    """Map markers to joint families using DataDescriptions-first, heuristic fallback."""

    def __init__(
        self,
        optional_marker_to_bone_map: dict[str, str] | None = None,
        *,
        datadescriptions_used: bool = False,
    ) -> None:
        self._marker_to_bone = optional_marker_to_bone_map or {}
        self._datadescriptions_used = datadescriptions_used and bool(self._marker_to_bone)
        self._cache: dict[str, MarkerFamilyResult] = {}

    @property
    def datadescriptions_used(self) -> bool:
        return self._datadescriptions_used

    @property
    def mapping_version(self) -> str:
        if self._datadescriptions_used:
            return "session_datadescriptions_unverified_v0"
        return "heuristic_v0"

    @property
    def session_mapping_status(self) -> str:
        if self._datadescriptions_used:
            return "session_datadescriptions_used_unverified"
        return "missing_datadescriptions_fallback_to_heuristic"

    def map_marker_to_family(
        self,
        raw_marker_name: str | None = None,
        *,
        body_region_group: str | None = None,
    ) -> MarkerFamilyResult:
        """Resolve marker to joint family. Never returns a Layer 2 link_id."""
        normalized = normalize_marker_name(raw_marker_name)
        cache_key = f"{normalized}|{body_region_group}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        result: MarkerFamilyResult

        # 1. DataDescriptions map if available
        if normalized and self._datadescriptions_used and normalized in self._marker_to_bone:
            attached_bone = self._marker_to_bone[normalized]
            bone_canonical = canonicalize_bone_name(attached_bone)
            family, adjacent, confidence = _family_from_bone(bone_canonical or "")
            result = MarkerFamilyResult(
                normalized_marker_name=normalized,
                side=infer_side(normalized),
                attached_bone=attached_bone,
                attached_bone_canonical=bone_canonical,
                joint_family=family,
                adjacent_joint_family=adjacent,
                mapping_source="session_datadescriptions_optional",
                mapping_confidence="attached_bone_observed_but_template_unverified",
                template_mapping_status="session_datadescriptions_used_unverified",
            )
        # 2. Heuristic marker-name table
        elif normalized and (heuristic := _family_from_heuristic(normalized)):
            result = heuristic
        # 3. Body region group
        elif region_result := _family_from_body_region(body_region_group):
            result = region_result
            if normalized:
                result = MarkerFamilyResult(
                    normalized_marker_name=normalized,
                    side=infer_side(normalized),
                    attached_bone=result.attached_bone,
                    attached_bone_canonical=result.attached_bone_canonical,
                    joint_family=result.joint_family,
                    adjacent_joint_family=result.adjacent_joint_family,
                    mapping_source=result.mapping_source,
                    mapping_confidence=result.mapping_confidence,
                    template_mapping_status=result.template_mapping_status,
                )
        # 4. Unmapped
        else:
            result = _unmapped_result(normalized)

        self._cache[cache_key] = result
        return result


def build_mapper_from_datadescriptions(
    path: str | Path | None,
    warnings: list[str] | None = None,
) -> MarkerFamilyMapper:
    """Build a MarkerFamilyMapper, optionally loading DataDescriptions."""
    if path is None:
        return MarkerFamilyMapper()
    try:
        marker_map, _meta = load_session_datadescriptions_marker_map(path)
        if not marker_map:
            if warnings is not None:
                warnings.append(
                    f"DataDescriptions file {path} parsed but no Bone Marker rows found; "
                    "falling back to heuristic."
                )
            return MarkerFamilyMapper()
        return MarkerFamilyMapper(marker_map, datadescriptions_used=True)
    except OSError as exc:
        if warnings is not None:
            warnings.append(f"Could not read DataDescriptions {path}: {exc}; falling back.")
        return MarkerFamilyMapper()
    except (csv.Error, ValueError) as exc:
        if warnings is not None:
            warnings.append(f"Could not parse DataDescriptions {path}: {exc}; falling back.")
        return MarkerFamilyMapper()
