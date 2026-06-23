"""Parent-child hierarchy, prefix stripping, joint selection heuristics (Stage 01)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from layer2_motive.parsing import QUAT_COMPONENTS, ColumnRecord, bone_rotation_groups

ROOT_LABEL = "Root"
TRUNK_REVIEW_KEYWORDS = ("Pelvis", "Hips", "Ab", "Abdomen", "Spine", "Chest")
TRUNK_CHAIN_KEYWORDS = TRUNK_REVIEW_KEYWORDS + ("Neck",)


@dataclass
class PrefixMapping:
    source_name: str
    canonical_name: str
    subject_prefix: str
    prefix_rule: str


def strip_subject_prefix(source_name: str, rule: str = "colon_suffix") -> PrefixMapping:
    """Strip subject prefixes in a documented, reversible way."""
    if rule != "colon_suffix":
        raise ValueError(f"Unsupported prefix rule: {rule}")
    if ":" in source_name:
        prefix, canonical = source_name.rsplit(":", 1)
        return PrefixMapping(
            source_name=source_name,
            canonical_name=canonical,
            subject_prefix=prefix,
            prefix_rule=rule,
        )
    return PrefixMapping(
        source_name=source_name,
        canonical_name=source_name,
        subject_prefix="",
        prefix_rule=rule,
    )


def restore_subject_prefix(mapping: PrefixMapping) -> str:
    if mapping.subject_prefix:
        return f"{mapping.subject_prefix}:{mapping.canonical_name}"
    return mapping.source_name


def _contains_keyword(name: str, keyword: str) -> bool:
    return keyword.lower() in name.lower()


def classify_bone_exclusion(
    canonical_name: str,
    config: dict[str, Any],
) -> tuple[str | None, str, bool]:
    """Return exclusion_reason, selection_rule, requires_manual_review."""
    distal_cfg = config.get("distal_exclusion", {})
    keywords: list[str] = list(distal_cfg.get("keywords", []))
    cautious_keywords: list[str] = list(distal_cfg.get("cautious_keywords", []))
    include_hand = bool(distal_cfg.get("include_hand", True))
    include_toes = bool(distal_cfg.get("include_toes", False))

    if canonical_name in {ROOT_LABEL}:
        return "root_label_not_a_bone", "root_label", False

    if not include_hand and canonical_name in {"LHand", "RHand", "Hand"}:
        return "hand_excluded_by_config", "config_include_hand_false", True

    for keyword in keywords:
        if _contains_keyword(canonical_name, keyword):
            if include_hand and canonical_name in {"LHand", "RHand"}:
                continue
            return f"distal_keyword:{keyword}", "distal_exclusion.keywords", False

    for keyword in cautious_keywords:
        if _contains_keyword(canonical_name, keyword):
            if include_toes:
                return None, "cautious_keyword_included_by_config", True
            return f"cautious_keyword:{keyword}", "distal_exclusion.cautious_keywords", True

    for keyword in TRUNK_REVIEW_KEYWORDS:
        if _contains_keyword(canonical_name, keyword):
            return None, "trunk_or_root_candidate", True

    return None, "default_include", False


def build_bone_inventory(
    columns: list[ColumnRecord],
    prefix_rule: str = "colon_suffix",
) -> list[dict[str, Any]]:
    groups = bone_rotation_groups(columns)
    inventory: list[dict[str, Any]] = []
    for source_name in sorted(groups):
        components = groups[source_name]
        name_map = strip_subject_prefix(source_name, rule=prefix_rule)
        parent_source = _parent_for_bone(columns, source_name)
        parent_map = (
            strip_subject_prefix(parent_source, rule=prefix_rule) if parent_source else None
        )
        inventory.append(
            {
                "source_bone_name": source_name,
                "canonical_bone_name": name_map.canonical_name,
                "source_parent_name": parent_source or "",
                "canonical_parent_name": parent_map.canonical_name if parent_map else "",
                "subject_prefix": name_map.subject_prefix,
                "prefix_rule": prefix_rule,
                "rotation_components_present": ",".join(sorted(components)),
                "rotation_complete": set(components) == set(QUAT_COMPONENTS),
                "is_root_bone": parent_source == ROOT_LABEL,
                "parent_is_root": parent_source == ROOT_LABEL,
            }
        )
    return inventory


def _parent_for_bone(columns: list[ColumnRecord], source_name: str) -> str:
    for col in columns:
        if (
            col.source_name == source_name
            and col.component_label == "X"
            and col.property_label == "Rotation"
        ):
            return col.source_parent
    for col in columns:
        if col.source_name == source_name and col.source_parent:
            return col.source_parent
    return ""


def build_joint_channel_map(columns: list[ColumnRecord]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for col in columns:
        if col.layer2_role != "bone_rotation_quaternion":
            continue
        prefix = strip_subject_prefix(col.source_name)
        rows.append(
            {
                "source_bone_name": col.source_name,
                "canonical_bone_name": prefix.canonical_name,
                "component": col.component_label,
                "column_index": col.column_index,
                "flat_name": col.flat_name,
            }
        )
    return rows


def build_candidate_joint_map(
    bone_inventory: list[dict[str, Any]],
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    """Build all parent-child candidate joints without freezing the final set."""
    canonical_to_source = {
        row["canonical_bone_name"]: row["source_bone_name"] for row in bone_inventory
    }
    joints: list[dict[str, Any]] = []
    joint_counter = 0

    for bone in bone_inventory:
        child_canonical = bone["canonical_bone_name"]
        parent_canonical = bone["canonical_parent_name"]
        parent_source = bone["source_parent_name"]
        child_source = bone["source_bone_name"]

        if not bone["rotation_complete"]:
            joints.append(
                _joint_row(
                    joint_counter := joint_counter + 1,
                    parent_canonical,
                    child_canonical,
                    parent_source,
                    child_source,
                    included=False,
                    exclusion_reason="incomplete_rotation_components",
                    selection_rule="require_complete_XYZW",
                    requires_manual_review=True,
                )
            )
            continue

        if parent_source == ROOT_LABEL or parent_canonical == ROOT_LABEL:
            joints.append(
                _joint_row(
                    joint_counter := joint_counter + 1,
                    parent_canonical or ROOT_LABEL,
                    child_canonical,
                    parent_source or ROOT_LABEL,
                    child_source,
                    included=False,
                    exclusion_reason="parent_is_root",
                    selection_rule="exclude_root_children_by_default",
                    requires_manual_review=True,
                )
            )
            continue

        if parent_canonical not in canonical_to_source and parent_canonical:
            joints.append(
                _joint_row(
                    joint_counter := joint_counter + 1,
                    parent_canonical,
                    child_canonical,
                    parent_source,
                    child_source,
                    included=False,
                    exclusion_reason="parent_bone_not_found_in_inventory",
                    selection_rule="hierarchy_integrity",
                    requires_manual_review=True,
                )
            )
            continue

        exclusion_reason, selection_rule, requires_review = classify_bone_exclusion(
            child_canonical, config
        )
        included = exclusion_reason is None and not requires_review
        if exclusion_reason is None and requires_review:
            included = False

        joints.append(
            _joint_row(
                joint_counter := joint_counter + 1,
                parent_canonical,
                child_canonical,
                parent_source,
                child_source,
                included=included,
                exclusion_reason=exclusion_reason or "",
                selection_rule=selection_rule,
                requires_manual_review=requires_review,
            )
        )
    return joints


def _joint_row(
    joint_id: int,
    parent_canonical: str,
    child_canonical: str,
    parent_source: str,
    child_source: str,
    *,
    included: bool,
    exclusion_reason: str,
    selection_rule: str,
    requires_manual_review: bool,
) -> dict[str, Any]:
    return {
        "joint_id": f"J{joint_id:03d}",
        "source_parent_bone": parent_source,
        "source_child_bone": child_source,
        "parent_bone": parent_canonical,
        "child_bone": child_canonical,
        "included": included,
        "exclusion_reason": exclusion_reason,
        "selection_rule": selection_rule,
        "requires_manual_review": requires_manual_review,
    }


def build_selected_joint_map_v0(candidate_joint_map: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Provisional selected map — not frozen; only heuristic auto-includes."""
    selected: list[dict[str, Any]] = []
    for row in candidate_joint_map:
        selected.append(
            {
                **row,
                "selection_status": "provisional_v0",
                "frozen": False,
                "included_in_v0": bool(row["included"]),
            }
        )
    return selected


def build_excluded_distal_bones(candidate_joint_map: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in candidate_joint_map:
        reason = row["exclusion_reason"]
        if not reason:
            continue
        if reason.startswith(("distal_keyword", "cautious_keyword", "hand_excluded")):
            rows.append(
                {
                    "parent_bone": row["parent_bone"],
                    "child_bone": row["child_bone"],
                    "source_parent_bone": row["source_parent_bone"],
                    "source_child_bone": row["source_child_bone"],
                    "exclusion_reason": reason,
                    "selection_rule": row["selection_rule"],
                    "requires_manual_review": row["requires_manual_review"],
                }
            )
    return rows


def build_hierarchy_mapping(bone_inventory: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "source_bone_name": row["source_bone_name"],
            "canonical_bone_name": row["canonical_bone_name"],
            "source_parent_name": row["source_parent_name"],
            "canonical_parent_name": row["canonical_parent_name"],
            "subject_prefix": row["subject_prefix"],
            "is_root_bone": row["is_root_bone"],
            "parent_is_root": row["parent_is_root"],
        }
        for row in bone_inventory
    ]


def build_parent_child_joint_map(candidate_joint_map: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "joint_id": row["joint_id"],
            "parent_bone": row["parent_bone"],
            "child_bone": row["child_bone"],
            "source_parent_bone": row["source_parent_bone"],
            "source_child_bone": row["source_child_bone"],
            "included": row["included"],
            "requires_manual_review": row["requires_manual_review"],
        }
        for row in candidate_joint_map
    ]


def _is_trunk_name(canonical_name: str, keywords: tuple[str, ...] = TRUNK_CHAIN_KEYWORDS) -> bool:
    return any(_contains_keyword(canonical_name, keyword) for keyword in keywords)


def summarize_skeleton_structure(
    inventory: list[dict[str, Any]],
) -> dict[str, Any]:
    """Summarize root/asset anchor and main trunk chain without renaming bones."""
    root_anchors = [
        {
            "source_bone_name": row["source_bone_name"],
            "canonical_bone_name": row["canonical_bone_name"],
            "source_parent_name": row["source_parent_name"],
        }
        for row in inventory
        if row["parent_is_root"]
    ]

    children_by_parent: dict[str, list[str]] = {}
    for row in inventory:
        parent = row["canonical_parent_name"]
        if parent and parent != ROOT_LABEL:
            children_by_parent.setdefault(parent, []).append(row["canonical_bone_name"])

    trunk_chains: list[list[str]] = []
    for anchor in root_anchors:
        chain = [anchor["canonical_bone_name"]]
        current = anchor["canonical_bone_name"]
        while True:
            children = children_by_parent.get(current, [])
            trunk_children = [name for name in children if _is_trunk_name(name)]
            if len(trunk_children) == 1:
                chain.append(trunk_children[0])
                current = trunk_children[0]
            else:
                break
        trunk_chains.append(chain)

    hierarchy_edges = [
        f"{row['canonical_parent_name']} → {row['canonical_bone_name']}"
        for row in inventory
        if row["canonical_parent_name"] and row["canonical_parent_name"] != ROOT_LABEL
    ]

    return {
        "root_anchors": root_anchors,
        "trunk_chains": trunk_chains,
        "hierarchy_edge_count": len(hierarchy_edges),
    }

