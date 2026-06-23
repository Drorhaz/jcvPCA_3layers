"""Structural Bone Rotation XYZW population checks (Stage 01, pre–Stage 02)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from layer2_motive.parsing import ParsedMotiveHeader, bone_rotation_groups
from layer2_motive.validation import HardStopError

COMPONENT_ORDER = ("X", "Y", "Z", "W")


def _population_status(complete_pct: float, rotation_complete: bool) -> str:
    if not rotation_complete:
        return "fail"
    if complete_pct >= 100.0:
        return "pass"
    if complete_pct >= 99.0:
        return "warning"
    return "fail"


def compute_rotation_population_report(
    csv_path: Path,
    parsed: ParsedMotiveHeader,
    inventory: list[dict[str, Any]],
    *,
    warning_threshold_pct: float = 99.0,
) -> tuple[list[dict[str, Any]], int]:
    """Check raw numeric population of complete XYZW rows per bone (not norm QC)."""
    if parsed.data_start_line_number is None:
        raise HardStopError("Cannot run population check: data start row unknown")

    groups = bone_rotation_groups(parsed.columns)
    readable_groups: dict[str, dict[str, int]] = {}
    for bone in inventory:
        source_name = bone["source_bone_name"]
        if source_name not in groups:
            continue
        components = groups[source_name]
        if set(components) == set(COMPONENT_ORDER):
            readable_groups[source_name] = components

    if not readable_groups:
        return [], 0

    usecols = sorted({idx for comp in readable_groups.values() for idx in comp.values()})
    col_to_pos = {col_idx: pos for pos, col_idx in enumerate(usecols)}
    data = pd.read_csv(
        csv_path,
        skiprows=parsed.data_start_line_number - 1,
        header=None,
        usecols=usecols,
        dtype=str,
        low_memory=False,
    )
    numeric = data.apply(pd.to_numeric, errors="coerce")
    total_frames = len(numeric)

    rows: list[dict[str, Any]] = []
    for bone in inventory:
        source_name = bone["source_bone_name"]
        components = groups.get(source_name, {})
        rotation_complete = set(components) == set(COMPONENT_ORDER)
        indices = {label: components.get(label, "") for label in COMPONENT_ORDER}
        if not rotation_complete:
            rows.append(
                {
                    "source_bone_name": source_name,
                    "canonical_bone_name": bone["canonical_bone_name"],
                    "column_index_x": indices["X"],
                    "column_index_y": indices["Y"],
                    "column_index_z": indices["Z"],
                    "column_index_w": indices["W"],
                    "total_frames": total_frames,
                    "complete_xyzw_frame_count": 0,
                    "complete_xyzw_percent": 0.0,
                    "population_status": "fail",
                    "notes": "Incomplete XYZW column group in header",
                }
            )
            continue

        cols = [col_to_pos[components[label]] for label in COMPONENT_ORDER]
        subset = numeric.iloc[:, cols]
        complete_mask: pd.Series = subset.notna().all(axis=1)
        complete_count = int(complete_mask.sum())
        complete_pct = 100.0 * complete_count / total_frames if total_frames else 0.0
        if complete_pct >= 100.0:
            status = "pass"
        elif complete_pct >= warning_threshold_pct:
            status = "warning"
        else:
            status = "fail"

        rows.append(
            {
                "source_bone_name": source_name,
                "canonical_bone_name": bone["canonical_bone_name"],
                "column_index_x": components["X"],
                "column_index_y": components["Y"],
                "column_index_z": components["Z"],
                "column_index_w": components["W"],
                "total_frames": total_frames,
                "complete_xyzw_frame_count": complete_count,
                "complete_xyzw_percent": round(complete_pct, 6),
                "population_status": status,
                "notes": (
                    "Structural population check only; not quaternion norm or "
                    "component-order validation"
                ),
            }
        )

    return rows, total_frames
