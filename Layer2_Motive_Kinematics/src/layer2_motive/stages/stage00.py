"""Stage 00 — CSV structure audit."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from layer2_motive.io import stage_output_dir, write_csv, write_text
from layer2_motive.metadata import metadata_rows
from layer2_motive.parsing import ParsedMotiveHeader, parse_motive_header
from layer2_motive.reporting import append_assumptions_log, render_stage_report
from layer2_motive.validation import HardStopError


def run_stage_00(input_csv: Path, output_dir: Path) -> ParsedMotiveHeader:
    stage_dir = stage_output_dir(output_dir, "00")
    parsed = parse_motive_header(input_csv)

    header_detection = pd.DataFrame(
        [
            {
                "line_number": row.line_number,
                "role": row.role,
                "is_blank": row.is_blank,
                "num_columns": len(row.cells),
                "first_cells": "|".join(row.cells[:6]),
            }
            for row in parsed.header_rows
        ]
    )
    write_csv(header_detection, stage_dir / "header_row_detection.csv")

    detected_columns = pd.DataFrame(
        [
            {
                "column_index": col.column_index,
                "flat_name": col.flat_name,
                "type": col.type_label,
                "source_name": col.source_name,
                "source_id": col.source_id,
                "source_parent": col.source_parent,
                "property": col.property_label,
                "component": col.component_label,
                "layer2_role": col.layer2_role,
                "layer2_used": col.layer2_used,
                "notes": col.notes,
            }
            for col in parsed.columns
        ]
    )
    write_csv(detected_columns, stage_dir / "detected_columns.csv")

    used = detected_columns[detected_columns["layer2_used"]].copy()
    ignored = detected_columns[~detected_columns["layer2_used"]].copy()
    unmatched = detected_columns[
        (detected_columns["type"] == "")
        & (~detected_columns["layer2_role"].isin(["frame", "time"]))
    ].copy()

    write_csv(used, stage_dir / "columns_used_for_layer2.csv")
    write_csv(ignored, stage_dir / "columns_ignored_for_layer2.csv")
    write_csv(unmatched, stage_dir / "unmatched_columns.csv")

    metadata_df = pd.DataFrame(metadata_rows(parsed.metadata) if parsed.metadata else [])
    write_csv(metadata_df, stage_dir / "metadata_detected.csv")

    errors: list[str] = []
    if parsed.metadata is None:
        errors.append("Metadata row not detected")
    else:
        if not parsed.metadata.rotation_type:
            errors.append("Rotation Type not found in metadata")
        elif parsed.metadata.rotation_type.lower() != "quaternion":
            errors.append(
                f"Rotation Type is {parsed.metadata.rotation_type!r}, expected Quaternion"
            )
        if not parsed.metadata.coordinate_space:
            errors.append("Coordinate Space not found in metadata")
        elif parsed.metadata.coordinate_space.lower() != "global":
            errors.append(
                f"Coordinate Space is {parsed.metadata.coordinate_space!r}, expected Global"
            )

    if parsed.frame_time.frame_column_index is None:
        errors.append("Frame column not detected")
    if parsed.frame_time.time_column_index is None:
        errors.append("Time column not detected")
    if parsed.data_start_line_number is None:
        errors.append("Data start row not detected in scanned header block")

    rotation_cols = used[used["layer2_role"] == "bone_rotation_quaternion"]
    if rotation_cols.empty:
        errors.append("No Bone Rotation quaternion columns detected")

    assumptions = [
        "Header block parsed manually without pandas MultiIndex headers.",
        "Flat column names generated for future numeric loading "
        "with pd.read_csv(skiprows=..., names=...).",
    ]
    if parsed.metadata and parsed.metadata.rotation_type:
        assumptions.append(
            f"Rotation Type detected as {parsed.metadata.rotation_type} from metadata row."
        )
    if parsed.metadata and parsed.metadata.coordinate_space:
        assumptions.append(
            f"Coordinate Space detected as {parsed.metadata.coordinate_space} from metadata row."
        )

    detected = [
        f"Metadata line: {parsed.metadata_line_number}",
        f"Data start line: {parsed.data_start_line_number}",
        f"Role line numbers: {parsed.role_line_numbers}",
        f"Frame column index {parsed.frame_time.frame_column_index} "
        f"({parsed.frame_time.frame_label})",
        f"Time column index {parsed.frame_time.time_column_index} ({parsed.frame_time.time_label})",
        f"Total columns mapped: {len(parsed.columns)}",
        f"Bone rotation quaternion columns: {len(rotation_cols)}",
        f"Distinct source bones with rotation columns: {rotation_cols['source_name'].nunique()}",
    ]

    outputs = [
        str(stage_dir / "report.md"),
        str(stage_dir / "header_row_detection.csv"),
        str(stage_dir / "detected_columns.csv"),
        str(stage_dir / "unmatched_columns.csv"),
        str(stage_dir / "columns_used_for_layer2.csv"),
        str(stage_dir / "columns_ignored_for_layer2.csv"),
        str(stage_dir / "metadata_detected.csv"),
    ]

    validation_status = (
        "PASS — ready for human review" if not errors else "REVIEW REQUIRED — see errors"
    )
    report = render_stage_report(
        stage_name="Stage 00 — CSV structure audit",
        input_files=[str(input_csv)],
        detected=detected,
        assumptions=assumptions,
        outputs=outputs,
        warnings=parsed.warnings,
        errors=errors,
        validation_status=validation_status,
        next_action=(
            "Human reviewer should validate detected header roles, metadata, "
            "Frame/Time columns, and bone rotation quaternion inventory before Stage 01."
        ),
    )
    write_text(stage_dir / "report.md", report)
    append_assumptions_log(output_dir, assumptions)

    if errors:
        raise HardStopError("Stage 00 detected blocking issues: " + "; ".join(errors))

    return parsed
