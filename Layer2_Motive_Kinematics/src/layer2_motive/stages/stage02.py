"""Stage 02 — quaternion component-order / SciPy compatibility validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pandas as pd

from layer2_motive.io import stage_output_dir, write_csv, write_text
from layer2_motive.parsing import (
    MOTIVE_COMPONENT_ORDER,
    ParsedMotiveHeader,
    bone_rotation_groups,
)
from layer2_motive.quaternions import (
    MOTIVE_TO_SCIPY_MAPPING,
    SCIPY_QUAT_COMPONENT_ORDER,
    motive_labels_compatible_with_scipy,
    validate_bone_rotation_group,
)
from layer2_motive.reporting import append_assumptions_log, render_stage_report
from layer2_motive.validation import HardStopError

STAGE02_LIMITATIONS = [
    "This stage validates component-order / SciPy library compatibility only.",
    "Motive Bone Rotation columns are labeled X, Y, Z, W.",
    "SciPy Rotation.from_quat expects [x, y, z, w] (scalar-last).",
    f"Intended mapping: {MOTIVE_TO_SCIPY_MAPPING}.",
    "This does not validate quaternion norms, temporal continuity, gaps, "
    "or relative joint rotations.",
    "Alternative-order constructability ([w,x,y,z] fed to SciPy) is reported for comparison only; "
    "numerical constructability of both orders does not prove semantic correctness.",
    "This does not validate global quaternion quality or biomechanical correctness.",
]


def _render_assumptions_and_limitations() -> str:
    lines = [
        "# Stage 02 assumptions and limitations",
        "",
        "## Component-order decision",
        "",
        "- Motive Bone Rotation columns are labeled **X, Y, Z, W**.",
        "- SciPy `Rotation.from_quat` expects **[x, y, z, w]** (scalar-last).",
        f"- Therefore the intended mapping is **{MOTIVE_TO_SCIPY_MAPPING}**.",
        "- This is a **component-order / library-compatibility** decision, "
        "not a full convention proof.",
        "",
        "## Explicit limitations",
        "",
    ]
    lines.extend(f"- {item}" for item in STAGE02_LIMITATIONS[3:])
    lines.append("")
    return "\n".join(lines)


def _load_rotation_numeric_data(
    csv_path: Path,
    parsed: ParsedMotiveHeader,
    groups: dict[str, dict[str, int]],
) -> tuple[pd.DataFrame, dict[int, int]]:
    if parsed.data_start_line_number is None:
        raise HardStopError("Cannot run Stage 02: data start row unknown")

    complete_groups = {
        bone: components
        for bone, components in groups.items()
        if set(components) == set(MOTIVE_COMPONENT_ORDER)
    }
    incomplete_groups = {
        bone: components
        for bone, components in groups.items()
        if set(components) != set(MOTIVE_COMPONENT_ORDER)
    }

    if not complete_groups and not incomplete_groups:
        raise HardStopError("No Bone Rotation quaternion column groups detected")

    if complete_groups:
        usecols = sorted({idx for comp in complete_groups.values() for idx in comp.values()})
        data = pd.read_csv(
            csv_path,
            skiprows=parsed.data_start_line_number - 1,
            header=None,
            usecols=usecols,
            dtype=str,
            low_memory=False,
        )
        numeric = cast(pd.DataFrame, data.apply(pd.to_numeric, errors="coerce"))
        col_to_pos = {col_idx: pos for pos, col_idx in enumerate(usecols)}
        return numeric, col_to_pos

    return pd.DataFrame(), {}


def _bone_rows(
    groups: dict[str, dict[str, int]],
    numeric: pd.DataFrame,
    col_to_pos: dict[int, int],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_bone: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []

    for bone_name, components in sorted(groups.items()):
        complete = set(components) == set(MOTIVE_COMPONENT_ORDER)
        row_base = {
            "source_bone_name": bone_name,
            "column_index_x": components.get("X", ""),
            "column_index_y": components.get("Y", ""),
            "column_index_z": components.get("Z", ""),
            "column_index_w": components.get("W", ""),
            "has_complete_xyzw_columns": complete,
        }

        if not complete:
            missing = [label for label in MOTIVE_COMPONENT_ORDER if label not in components]
            result = {
                **row_base,
                "motive_component_labels": ",".join(MOTIVE_COMPONENT_ORDER),
                "scipy_component_order": ",".join(SCIPY_QUAT_COMPONENT_ORDER),
                "selected_scipy_order": "undetermined",
                "labels_compatible_with_scipy": False,
                "sample_size": 0,
                "constructible_count": 0,
                "construction_error_count": 0,
                "non_finite_row_count": 0,
                "constructability_status": "fail",
                "primary_constructibility_rate": 0.0,
                "alternative_order_label": "motive_xyzw_as_wxyz_alternative",
                "alternative_constructible_count": 0,
                "alternative_construction_error_count": 0,
                "alternative_constructibility_rate": 0.0,
                "first_construction_error": None,
                "missing_components": ",".join(missing),
                "stage03_may_proceed": False,
                "notes": "Incomplete XYZW column group; component-order validation blocked",
            }
            by_bone.append(result)
            summary_rows.append(
                {
                    "metric": f"bone:{bone_name}",
                    "value": "fail_incomplete_columns",
                }
            )
            continue

        cols = [col_to_pos[components[label]] for label in MOTIVE_COMPONENT_ORDER]
        subset = numeric.iloc[:, cols]
        validation = validate_bone_rotation_group(
            subset.iloc[:, 0],
            subset.iloc[:, 1],
            subset.iloc[:, 2],
            subset.iloc[:, 3],
        )
        stage03_ok = (
            validation["constructability_status"] == "pass"
            and validation["labels_compatible_with_scipy"]
            and validation["sample_size"] > 0
        )
        result = {
            **row_base,
            **validation,
            "stage03_may_proceed": stage03_ok,
            "notes": (
                "Component-order / SciPy constructability pass"
                if stage03_ok
                else "Component-order / SciPy constructability issue"
            ),
        }
        by_bone.append(result)

    return by_bone, summary_rows


def _build_summary(
    *,
    parsed: ParsedMotiveHeader,
    by_bone_df: pd.DataFrame,
    file_stage03_ok: bool,
) -> pd.DataFrame:
    total_groups = len(by_bone_df)
    complete_groups = int(by_bone_df["has_complete_xyzw_columns"].sum())
    passing = int((by_bone_df["constructability_status"] == "pass").sum())
    failing = int((by_bone_df["constructability_status"] == "fail").sum())
    non_finite_issues = int((by_bone_df["non_finite_row_count"] > 0).sum())
    incomplete = total_groups - complete_groups

    rotation_type = parsed.metadata.rotation_type if parsed.metadata else "unknown"
    coordinate_space = parsed.metadata.coordinate_space if parsed.metadata else "unknown"

    rows = [
        {"metric": "input_file", "value": str(parsed.csv_path)},
        {"metric": "rotation_type", "value": rotation_type},
        {"metric": "coordinate_space", "value": coordinate_space},
        {"metric": "bone_rotation_quaternion_groups_checked", "value": total_groups},
        {"metric": "groups_with_complete_xyzw_columns", "value": complete_groups},
        {"metric": "groups_with_incomplete_xyzw_columns", "value": incomplete},
        {"metric": "groups_passing_constructability", "value": passing},
        {"metric": "groups_failing_constructability", "value": failing},
        {"metric": "groups_with_non_finite_rows", "value": non_finite_issues},
        {
            "metric": "selected_scipy_component_order",
            "value": ",".join(SCIPY_QUAT_COMPONENT_ORDER),
        },
        {
            "metric": "motive_to_scipy_mapping",
            "value": MOTIVE_TO_SCIPY_MAPPING,
        },
        {
            "metric": "labels_compatible_with_scipy",
            "value": str(motive_labels_compatible_with_scipy()),
        },
        {"metric": "stage03_may_proceed_for_file", "value": str(file_stage03_ok)},
    ]
    return pd.DataFrame(rows)


def run_stage_02(
    input_csv: Path,
    output_dir: Path,
    parsed: ParsedMotiveHeader | None = None,
) -> dict[str, pd.DataFrame]:
    if parsed is None:
        from layer2_motive.stages.stage00 import run_stage_00

        parsed = run_stage_00(input_csv, output_dir)

    stage_dir = stage_output_dir(output_dir, "02")
    groups = bone_rotation_groups(parsed.columns)
    numeric, col_to_pos = _load_rotation_numeric_data(input_csv, parsed, groups)
    by_bone_rows, _ = _bone_rows(groups, numeric, col_to_pos)
    by_bone_df = pd.DataFrame(by_bone_rows)

    complete_df = by_bone_df[by_bone_df["has_complete_xyzw_columns"]]
    file_stage03_ok = (
        not by_bone_df.empty
        and (by_bone_df["has_complete_xyzw_columns"] == False).sum() == 0  # noqa: E712
        and (complete_df["constructability_status"] == "pass").all()
        and motive_labels_compatible_with_scipy()
    )

    summary_df = _build_summary(
        parsed=parsed,
        by_bone_df=by_bone_df,
        file_stage03_ok=bool(file_stage03_ok),
    )

    write_csv(summary_df, stage_dir / "component_order_summary.csv")
    write_csv(by_bone_df, stage_dir / "component_order_by_bone.csv")
    write_text(stage_dir / "assumptions_and_limitations.md", _render_assumptions_and_limitations())

    rotation_type = parsed.metadata.rotation_type if parsed.metadata else "unknown"
    coordinate_space = parsed.metadata.coordinate_space if parsed.metadata else "unknown"
    total_groups = len(by_bone_df)
    passing = int((by_bone_df["constructability_status"] == "pass").sum())
    failing = int((by_bone_df["constructability_status"] == "fail").sum())
    non_finite_bones = int((by_bone_df["non_finite_row_count"] > 0).sum())

    warnings: list[str] = []
    errors: list[str] = []
    if failing:
        warnings.append(f"{failing} bone rotation group(s) failed constructability checks")
    if non_finite_bones:
        warnings.append(f"{non_finite_bones} bone group(s) contain non-finite quaternion rows")
    incomplete = by_bone_df[~by_bone_df["has_complete_xyzw_columns"]]
    if not incomplete.empty:
        errors.append(
            f"{len(incomplete)} bone group(s) missing one or more X/Y/Z/W columns"
        )

    assumptions = [
        "Motive Bone Rotation labels X/Y/Z/W map to SciPy [x,y,z,w] by label semantics.",
        "Constructability uses scipy.spatial.transform.Rotation.from_quat on finite numeric rows.",
        "Alternative [w,x,y,z] comparison is diagnostic only and not used for selection.",
        *STAGE02_LIMITATIONS,
    ]

    detected = [
        f"Rotation Type: {rotation_type}",
        f"Coordinate Space: {coordinate_space}",
        f"Bone Rotation quaternion groups checked: {total_groups}",
        f"Groups passing constructability: {passing}",
        f"Groups failing constructability: {failing}",
        f"Groups with non-finite rows: {non_finite_bones}",
        f"Selected SciPy component order: {','.join(SCIPY_QUAT_COMPONENT_ORDER)}",
        f"Stage 03 may proceed for this file: {file_stage03_ok}",
    ]

    outputs = [
        str(stage_dir / "report.md"),
        str(stage_dir / "component_order_summary.csv"),
        str(stage_dir / "component_order_by_bone.csv"),
        str(stage_dir / "assumptions_and_limitations.md"),
    ]

    validation_status = (
        "PASS — component-order / SciPy compatibility validated for representative file"
        if file_stage03_ok
        else "REVIEW REQUIRED — see warnings/errors before Stage 03"
    )

    report = render_stage_report(
        stage_name="Stage 02 — Quaternion component-order / SciPy compatibility",
        input_files=[str(input_csv)],
        detected=detected,
        assumptions=assumptions,
        outputs=outputs,
        warnings=warnings,
        errors=errors,
        validation_status=validation_status,
        next_action=(
            "Review component-order report and assumptions. "
            "Continue to Stage 03 only if stage03_may_proceed_for_file is true "
            "and human reviewer accepts the component-order decision."
        ),
    )
    write_text(stage_dir / "report.md", report)
    append_assumptions_log(output_dir, assumptions)

    if incomplete.shape[0] == total_groups and total_groups > 0:
        raise HardStopError(
            "Stage 02 blocked: no bone rotation groups have complete X/Y/Z/W columns"
        )

    return {
        "summary": summary_df,
        "by_bone": by_bone_df,
    }
