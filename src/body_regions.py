"""Body-region tagging for link-level G3 recommendations (stdlib-only subset)."""

from __future__ import annotations

UPPER_TOKENS = ("Head", "Neck", "Chest", "Spine", "Shoulder", "UArm", "FArm", "Hand", "Clavicle")
LOWER_TOKENS = ("Thigh", "Shin", "Foot", "Toe", "Pelvis", "Waist", "Hip", "Knee", "Ankle", "Femur", "Tibia")


def infer_body_region(parent: str, child: str, link_label: str = "") -> str:
    """Return a coarse body region label for a link."""
    bones = f"{parent} {child} {link_label}"
    is_upper = any(t in bones for t in UPPER_TOKENS)
    is_lower = any(t in bones for t in LOWER_TOKENS)
    if parent.startswith("L") or child.startswith("L") or "LShoulder" in bones or "LUArm" in bones:
        if is_upper and not is_lower:
            return "left_arm"
        if is_lower and not is_upper:
            return "left_leg"
    if parent.startswith("R") or child.startswith("R") or "RShoulder" in bones or "RUArm" in bones:
        if is_upper and not is_lower:
            return "right_arm"
        if is_lower and not is_upper:
            return "right_leg"
    if "Neck" in bones or "Head" in bones or "Chest" in bones or "Spine" in bones:
        return "trunk_spine"
    if is_upper:
        return "upper_body"
    if is_lower:
        return "lower_body"
    return "other"
