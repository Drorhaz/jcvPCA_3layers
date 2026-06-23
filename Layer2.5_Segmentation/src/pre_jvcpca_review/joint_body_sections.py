"""Body-region helpers for joint filtering in the review UI."""

from __future__ import annotations

from pre_jvcpca_review.load_layer2 import LinkRecord

BODY_SECTION_ALL = "all"
BODY_SECTION_UPPER = "upper_body"
BODY_SECTION_LOWER = "lower_body"
BODY_SECTION_TRUNK = "trunk_spine"
BODY_SECTION_LEFT_ARM = "left_arm"
BODY_SECTION_RIGHT_ARM = "right_arm"
BODY_SECTION_LEFT_LEG = "left_leg"
BODY_SECTION_RIGHT_LEG = "right_leg"
BODY_SECTION_PILOT_CORE = "pilot_core"

BODY_SECTION_LABELS: dict[str, str] = {
    BODY_SECTION_ALL: "All",
    BODY_SECTION_UPPER: "Upper body",
    BODY_SECTION_LOWER: "Lower body",
    BODY_SECTION_TRUNK: "Trunk / spine",
    BODY_SECTION_LEFT_ARM: "Left arm",
    BODY_SECTION_RIGHT_ARM: "Right arm",
    BODY_SECTION_LEFT_LEG: "Left leg",
    BODY_SECTION_RIGHT_LEG: "Right leg",
    BODY_SECTION_PILOT_CORE: "Pilot core (Group 4 manifest)",
}

# Parent filters include their child sections (e.g. upper body = trunk + arms).
BODY_SECTION_INCLUDES: dict[str, frozenset[str]] = {
    BODY_SECTION_UPPER: frozenset(
        {
            BODY_SECTION_UPPER,
            BODY_SECTION_TRUNK,
            BODY_SECTION_LEFT_ARM,
            BODY_SECTION_RIGHT_ARM,
        }
    ),
    BODY_SECTION_LOWER: frozenset(
        {
            BODY_SECTION_LOWER,
            BODY_SECTION_LEFT_LEG,
            BODY_SECTION_RIGHT_LEG,
        }
    ),
}

UPPER_BONE_TOKENS = (
    "Head",
    "Neck",
    "Chest",
    "Spine",
    "Shoulder",
    "UArm",
    "FArm",
    "Hand",
    "Clavicle",
)
LOWER_BONE_TOKENS = (
    "Thigh",
    "Shin",
    "Foot",
    "Toe",
    "Pelvis",
    "Waist",
    "Hip",
    "Knee",
    "Ankle",
    "Femur",
    "Tibia",
)


def _bone_matches(bone: str, tokens: tuple[str, ...]) -> bool:
    return any(token in bone for token in tokens)


def _is_left(bone: str) -> bool:
    return bone.startswith("L") and not bone.startswith("LP")


def _is_right(bone: str) -> bool:
    return bone.startswith("R") and not bone.startswith("RP")


def classify_link_body_section(link: LinkRecord) -> str:
    parent, child = link.parent_canonical, link.child_canonical

    if _bone_matches(parent, LOWER_BONE_TOKENS) or _bone_matches(child, LOWER_BONE_TOKENS):
        if _is_left(parent) or _is_left(child):
            return BODY_SECTION_LEFT_LEG
        if _is_right(parent) or _is_right(child):
            return BODY_SECTION_RIGHT_LEG
        return BODY_SECTION_LOWER

    if (_is_left(parent) or _is_left(child)) and (
        _bone_matches(parent, UPPER_BONE_TOKENS) or _bone_matches(child, UPPER_BONE_TOKENS)
    ):
        if "Hand" in parent or "Hand" in child or "UArm" in parent or "UArm" in child:
            return BODY_SECTION_LEFT_ARM
        if "Shoulder" in parent or "Shoulder" in child:
            return BODY_SECTION_LEFT_ARM
        if "FArm" in parent or "FArm" in child:
            return BODY_SECTION_LEFT_ARM

    if (_is_right(parent) or _is_right(child)) and (
        _bone_matches(parent, UPPER_BONE_TOKENS) or _bone_matches(child, UPPER_BONE_TOKENS)
    ):
        if "Hand" in parent or "Hand" in child or "UArm" in parent or "UArm" in child:
            return BODY_SECTION_RIGHT_ARM
        if "Shoulder" in parent or "Shoulder" in child:
            return BODY_SECTION_RIGHT_ARM
        if "FArm" in parent or "FArm" in child:
            return BODY_SECTION_RIGHT_ARM

    if _bone_matches(parent, UPPER_BONE_TOKENS) or _bone_matches(child, UPPER_BONE_TOKENS):
        if (
            "Spine" in parent
            or "Spine" in child
            or parent.startswith("T3")
            or child.startswith("T3")
        ):
            return BODY_SECTION_TRUNK
        if "Chest" in parent or "Chest" in child or "Neck" in parent or "Neck" in child:
            return BODY_SECTION_TRUNK
        return BODY_SECTION_UPPER

    return BODY_SECTION_TRUNK


def link_matches_body_section(
    link: LinkRecord,
    section: str,
    *,
    pilot_link_ids: set[str] | None = None,
) -> bool:
    if section in ("", BODY_SECTION_ALL):
        return True
    if section == BODY_SECTION_PILOT_CORE:
        return pilot_link_ids is not None and link.link_id in pilot_link_ids
    link_section = classify_link_body_section(link)
    included = BODY_SECTION_INCLUDES.get(section)
    if included is not None:
        return link_section in included
    return link_section == section
