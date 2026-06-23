"""Marker-to-bone mapping, joint families, and candidate link lookup."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path

from pre_jvcpca_review.load_layer2 import LinkRecord

REGION_TO_FAMILY = {
    "elbow_forearm": "elbow_forearm",
    "shoulder_upper_arm": "shoulder_arm",
    "wrist_hand": "wrist_hand",
    "torso_chest_back": "trunk_chest",
    "pelvis_waist": "pelvis_hip",
    "head_neck": "head_neck",
    "thigh_knee": "thigh_knee",
    "shank_ankle": "shank_ankle",
    "foot": "foot",
}


@dataclass
class DataDescriptions:
    marker_to_bone: dict[str, str] = field(default_factory=dict)
    bone_index_to_id: dict[int, str] = field(default_factory=dict)
    bone_id_to_parent_index: dict[str, int | None] = field(default_factory=dict)
    labeled_markers: set[str] = field(default_factory=set)


@dataclass
class MappingEntry:
    raw_marker_or_region: str
    normalized_marker_or_region: str
    component_markers: str
    attached_bone: str
    attached_bone_canonical: str
    marker_family: str
    related_joint_family: str
    candidate_layer2_links: str
    candidate_layer2_link_ids: str
    mapping_source: str
    mapping_status: str
    candidate_mapping_level: str
    included_in_review: bool
    review_note: str
    candidate_link_ids: list[str] = field(default_factory=list)


def parse_datadescriptions(path: Path | None) -> DataDescriptions | None:
    if path is None or not path.is_file():
        return None
    dd = DataDescriptions()
    with path.open(encoding="utf-8") as handle:
        for row in csv.reader(handle):
            if len(row) >= 3 and row[0] == "Bone Marker":
                marker, bone = row[1], row[2]
                dd.marker_to_bone[marker] = bone
                dd.labeled_markers.add(marker)
            elif len(row) >= 4 and row[0] == "Bone":
                bone_id = row[1]
                bone_idx = int(row[2])
                parent_idx_raw = row[3]
                parent_idx = None if parent_idx_raw in ("", "-1") else int(parent_idx_raw)
                dd.bone_index_to_id[bone_idx] = bone_id
                dd.bone_id_to_parent_index[bone_id] = parent_idx
    return dd


def normalize_raw_name(name: str) -> str:
    return name.split(":", 1)[-1] if ":" in name else name


def is_unlabeled(name: str) -> bool:
    return bool(re.match(r"^Unlabeled\s+\d+", name, re.I))


def is_labeled_marker(name: str, dd: DataDescriptions | None) -> bool:
    if is_unlabeled(name):
        return False
    if "__" in name:
        left, right = name.split("__", 1)
        if dd is None:
            return True
        return left in dd.labeled_markers and right in dd.labeled_markers
    norm = normalize_raw_name(name)
    if dd is None:
        return name.startswith("671:")
    return norm in dd.labeled_markers


def canonical_bone(bone_id: str) -> str:
    if bone_id in ("unknown", "mixed", ""):
        return bone_id
    if bone_id.startswith("671_"):
        return bone_id[4:]
    return bone_id


def laterality_prefix(name: str) -> str | None:
    base = normalize_raw_name(name)
    if base.startswith("L") and not base.startswith("Left"):
        return "left"
    if base.startswith("R") and not base.startswith("Right"):
        return "right"
    if "Left" in base or base.startswith("BackLeft"):
        return "left"
    if "Right" in base or base.startswith("BackRight"):
        return "right"
    return None


def enrich_joint_family(region: str, marker_name: str) -> str:
    base = REGION_TO_FAMILY.get(region, region)
    if base in ("head_neck",):
        return base
    side = laterality_prefix(marker_name)
    if side and not base.startswith(side):
        return f"{side}_{base}"
    return base


def bone_adjacent_link_ids(bone_canonical: str, links: list[LinkRecord]) -> list[str]:
    ids: list[str] = []
    for link in links:
        if link.parent_canonical == bone_canonical or link.child_canonical == bone_canonical:
            ids.append(link.link_id)
    return sorted(set(ids))


def _ancestors(bone_id: str, dd: DataDescriptions) -> set[str]:
    path: set[str] = set()
    current: str | None = bone_id
    visited: set[str] = set()
    while current and current not in visited:
        visited.add(current)
        path.add(canonical_bone(current))
        parent_idx = dd.bone_id_to_parent_index.get(current)
        if parent_idx is None:
            break
        current = dd.bone_index_to_id.get(parent_idx)
    return path


def bone_path_links(bone_a: str, bone_b: str, dd: DataDescriptions, links: list[LinkRecord]) -> list[str]:
    """Links on skeletal path between two bones (regional segment-pair proxy)."""
    ca, cb = canonical_bone(bone_a), canonical_bone(bone_b)
    path_bones = _ancestors(bone_a, dd) | _ancestors(bone_b, dd)
    if not path_bones:
        return sorted(set(bone_adjacent_link_ids(ca, links) + bone_adjacent_link_ids(cb, links)))

    candidate_ids: set[str] = set()
    for link in links:
        if link.parent_canonical in path_bones or link.child_canonical in path_bones:
            candidate_ids.add(link.link_id)
    return sorted(candidate_ids)


def format_link_label(link_id: str, links: list[LinkRecord]) -> str:
    for link in links:
        if link.link_id == link_id:
            return f"{link_id} {link.display_name}"
    return link_id


def build_mapping_entry(
    raw_name: str,
    body_region: str,
    dd: DataDescriptions | None,
    links: list[LinkRecord],
) -> MappingEntry:
    norm = normalize_raw_name(raw_name)
    components = ""
    attached_bone = "unknown"
    attached_canonical = "unknown"
    mapping_source = "unmapped"
    mapping_status = "unmapped"
    mapping_level = "unmapped_unknown"
    review_note = ""
    marker_family = body_region or "unknown"
    joint_family = enrich_joint_family(body_region, raw_name) if body_region else "unknown"
    candidate_ids: list[str] = []

    if "__" in norm:
        parts = norm.split("__")
        components = "; ".join(parts)
        if dd and all(p in dd.labeled_markers for p in parts):
            bones = [dd.marker_to_bone[p] for p in parts]
            attached_bone = "mixed"
            attached_canonical = "mixed"
            fams = [enrich_joint_family(body_region, p) for p in parts]
            joint_family = "; ".join(dict.fromkeys(fams))
            for i, b in enumerate(bones):
                fams[i] = enrich_joint_family(body_region, parts[i])
            candidate_ids = bone_path_links(bones[0], bones[1], dd, links)
            mapping_source = "datadescriptions"
            mapping_status = "mapped"
            mapping_level = "segment_pair_regional"
            review_note = "regional pair, not exact link evidence"
        else:
            review_note = "retained labeled segment pair with incomplete bone mapping"
    else:
        bare = norm
        if dd and bare in dd.marker_to_bone:
            attached_bone = dd.marker_to_bone[bare]
            attached_canonical = canonical_bone(attached_bone)
            candidate_ids = bone_adjacent_link_ids(attached_canonical, links)
            mapping_source = "datadescriptions"
            mapping_status = "mapped"
            mapping_level = "bone_adjacency_candidate"
            joint_family = enrich_joint_family(body_region or "unknown", bare)
        elif dd is None and raw_name.startswith("671:"):
            mapping_source = "heuristic"
            mapping_status = "unmapped"
            mapping_level = "unmapped_unknown"
            review_note = "no DataDescriptions; heuristic only"
        else:
            review_note = "retained as unknown labeled marker"

    candidate_links_str = "; ".join(format_link_label(lid, links) for lid in candidate_ids)
    candidate_ids_str = "; ".join(candidate_ids)

    return MappingEntry(
        raw_marker_or_region=raw_name,
        normalized_marker_or_region=norm,
        component_markers=components,
        attached_bone=attached_bone,
        attached_bone_canonical=attached_canonical,
        marker_family=marker_family,
        related_joint_family=joint_family,
        candidate_layer2_links=candidate_links_str,
        candidate_layer2_link_ids=candidate_ids_str,
        mapping_source=mapping_source,
        mapping_status=mapping_status,
        candidate_mapping_level=mapping_level,
        included_in_review=True,
        review_note=review_note,
        candidate_link_ids=candidate_ids,
    )


def filter_mapping_by_selected_links(
    entries: list[MappingEntry],
    selected_link_ids: list[str],
) -> list[MappingEntry]:
    """Keep markers/regions whose candidate links overlap the user-selected joints."""
    selected = set(selected_link_ids)
    if not selected:
        return entries
    return [
        entry
        for entry in entries
        if entry.candidate_link_ids and set(entry.candidate_link_ids) & selected
    ]


def preferred_raw_marker_name(normalized: str) -> str:
    """Canonical display form for inventory rows."""
    return normalized if normalized.startswith("671:") else f"671:{normalized}"


def collect_marker_inventory(
    dd: DataDescriptions | None,
    event_marker_names: set[str],
) -> list[str]:
    names: set[str] = set()
    if dd:
        for marker in sorted(dd.labeled_markers):
            names.add(preferred_raw_marker_name(marker))
    for name in event_marker_names:
        if is_labeled_marker(name, dd):
            names.add(name if "__" in name or name.startswith("671:") else preferred_raw_marker_name(name))
    return sorted(names, key=lambda x: normalize_raw_name(x).lower())


def build_mapping_table(
    dd: DataDescriptions | None,
    links: list[LinkRecord],
    event_marker_names: set[str],
    marker_regions: dict[str, str],
) -> list[MappingEntry]:
    inventory = collect_marker_inventory(dd, event_marker_names)
    entries: list[MappingEntry] = []
    seen: set[str] = set()
    for raw in inventory:
        key = normalize_raw_name(raw)
        if key in seen:
            continue
        seen.add(key)
        region = marker_regions.get(raw) or marker_regions.get(key) or marker_regions.get(f"671:{key}") or ""
        entries.append(build_mapping_entry(raw, region, dd, links))
    return entries


def mapping_by_raw(entries: list[MappingEntry]) -> dict[str, MappingEntry]:
    out: dict[str, MappingEntry] = {}
    for entry in entries:
        out[entry.raw_marker_or_region] = entry
        bare = normalize_raw_name(entry.raw_marker_or_region)
        out.setdefault(bare, entry)
        out.setdefault(f"671:{bare}", entry)
    return out


def link_joint_family(link: LinkRecord) -> str:
    child = link.child_canonical
    parent = link.parent_canonical
    name = child if child.startswith(("L", "R")) else parent
    region_guess = {
        "LHand": "wrist_hand",
        "RHand": "wrist_hand",
        "LFArm": "elbow_forearm",
        "RFArm": "elbow_forearm",
        "LShin": "thigh_knee",
        "RShin": "thigh_knee",
        "Head": "head_neck",
        "Neck": "head_neck",
        "Chest": "trunk_chest",
        "Ab": "trunk_chest",
    }.get(child) or {
        "LUArm": "shoulder_arm",
        "RUArm": "shoulder_arm",
        "LThigh": "thigh_knee",
        "RThigh": "thigh_knee",
    }.get(parent, "unknown")
    return enrich_joint_family(region_guess, name)
