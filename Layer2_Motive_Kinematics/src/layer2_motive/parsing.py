"""Motive CSV header parsing and column discovery (Stages 00–01)."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path

from layer2_motive.metadata import MotiveMetadata, parse_metadata_fields

ROLE_LABELS = {"Type", "Name", "ID", "Parent"}
FRAME_LABELS = {"Frame"}
TIME_LABELS = {"Time", "Time (Seconds)", "Seconds"}
QUAT_COMPONENTS = {"X", "Y", "Z", "W"}
MOTIVE_COMPONENT_ORDER = ("X", "Y", "Z", "W")


@dataclass
class HeaderRow:
    line_number: int
    role: str
    cells: list[str]
    is_blank: bool = False


@dataclass
class ColumnRecord:
    column_index: int
    flat_name: str
    type_label: str
    source_name: str
    source_id: str
    source_parent: str
    property_label: str
    component_label: str
    layer2_role: str
    layer2_used: bool
    notes: str = ""


@dataclass
class FrameTimeDetection:
    frame_column_index: int | None
    frame_label: str | None
    time_column_index: int | None
    time_label: str | None
    detection_source: str


@dataclass
class ParsedMotiveHeader:
    csv_path: Path
    header_rows: list[HeaderRow]
    metadata: MotiveMetadata | None
    metadata_line_number: int | None
    data_start_line_number: int | None
    role_line_numbers: dict[str, int]
    columns: list[ColumnRecord]
    flat_column_names: list[str]
    frame_time: FrameTimeDetection
    warnings: list[str] = field(default_factory=list)


def read_header_block(csv_path: Path, max_lines: int = 20) -> list[HeaderRow]:
    """Read the first ``max_lines`` lines manually, preserving absolute line numbers."""
    rows: list[HeaderRow] = []
    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        for line_number in range(1, max_lines + 1):
            line = handle.readline()
            if not line:
                break
            stripped = line.rstrip("\r\n")
            if stripped.strip() == "":
                rows.append(HeaderRow(line_number, "blank", [], is_blank=True))
                continue
            cells = next(csv.reader([stripped]))
            role = detect_row_role(cells, line_number, rows)
            rows.append(HeaderRow(line_number, role, cells))
    return rows


def detect_row_role(cells: list[str], line_number: int, prior_rows: list[HeaderRow]) -> str:
    if not cells:
        return "blank"
    first = cells[0].strip()
    second = cells[1].strip() if len(cells) > 1 else ""

    if first == "Format Version" or "Format Version" in first:
        return "metadata"
    if second in ROLE_LABELS:
        return second.lower()
    if first in FRAME_LABELS or first.startswith("Frame"):
        return "component"
    if first.isdigit():
        return "data"
    if first == "" and second == "" and any(cell.strip() == "Rotation" for cell in cells[2:12]):
        return "property"
    has_quat_component = any(cell.strip() in QUAT_COMPONENTS for cell in cells[2:12])
    if first == "" and second == "" and has_quat_component:
        return "property"
    if any(label in cells for label in TIME_LABELS) and first in FRAME_LABELS.union(TIME_LABELS):
        return "component"
    return "unknown"


def _row_by_role(header_rows: list[HeaderRow], role: str) -> list[str] | None:
    for row in header_rows:
        if row.role == role and not row.is_blank:
            return row.cells
    return None


def detect_data_start_line(header_rows: list[HeaderRow]) -> int | None:
    for row in header_rows:
        if row.role == "data":
            return row.line_number
    return None


def detect_frame_time_columns(
    header_rows: list[HeaderRow],
    component_row: list[str] | None,
) -> FrameTimeDetection:
    """Detect Frame/Time columns by scanning the full header block."""
    candidates: list[tuple[int, str, str]] = []

    rows_to_scan: list[list[str]] = []
    if component_row is not None:
        rows_to_scan.append(component_row)
    for row in header_rows:
        if row.cells and row is not None and row.cells not in rows_to_scan:
            rows_to_scan.append(row.cells)

    for row in rows_to_scan:
        for idx, cell in enumerate(row):
            label = cell.strip()
            if label in FRAME_LABELS:
                candidates.append((idx, label, "frame"))
            elif label in TIME_LABELS:
                candidates.append((idx, label, "time"))

    frame_idx = next((idx for idx, label, kind in candidates if kind == "frame"), None)
    frame_label = next((label for idx, label, kind in candidates if kind == "frame"), None)
    time_idx = next((idx for idx, label, kind in candidates if kind == "time"), None)
    time_label = next((label for idx, label, kind in candidates if kind == "time"), None)

    source = "component_row" if component_row is not None else "header_scan"
    return FrameTimeDetection(
        frame_column_index=frame_idx,
        frame_label=frame_label,
        time_column_index=time_idx,
        time_label=time_label,
        detection_source=source,
    )


def _sanitize_flat_token(value: str) -> str:
    token = re.sub(r"[^A-Za-z0-9]+", "_", value.strip())
    token = re.sub(r"_+", "_", token).strip("_")
    return token or "empty"


def make_flat_column_name(
    column_index: int,
    type_label: str,
    source_name: str,
    property_label: str,
    component_label: str,
    frame_time: FrameTimeDetection,
) -> str:
    if frame_time.frame_column_index == column_index:
        return "frame"
    if frame_time.time_column_index == column_index:
        return "time_seconds"
    parts = [
        f"col{column_index:04d}",
        _sanitize_flat_token(type_label),
        _sanitize_flat_token(source_name),
        _sanitize_flat_token(property_label),
        _sanitize_flat_token(component_label),
    ]
    return "__".join(part for part in parts if part)


def classify_layer2_role(
    type_label: str,
    property_label: str,
    component_label: str,
    frame_time: FrameTimeDetection,
    column_index: int,
) -> tuple[str, bool, str]:
    if column_index == frame_time.frame_column_index:
        return "frame", False, "Frame index column"
    if column_index == frame_time.time_column_index:
        return "time", False, "Time column"
    if type_label == "Bone" and property_label == "Rotation" and component_label in QUAT_COMPONENTS:
        return "bone_rotation_quaternion", True, "Bone rotation quaternion component"
    if type_label == "Bone" and property_label == "Position":
        return "bone_position", False, "Bone position ignored for Layer 2"
    if type_label == "Bone Marker":
        return "bone_marker", False, "Bone Marker column ignored for Layer 2"
    if type_label == "Marker":
        return "marker", False, "Marker column ignored for Layer 2"
    if type_label == "Bone" and property_label not in {"", "Rotation", "Position"}:
        return "bone_other_property", False, f"Bone property {property_label!r} ignored"
    if (
        type_label == "Bone"
        and property_label == "Rotation"
        and component_label not in QUAT_COMPONENTS
    ):
        return "bone_rotation_incomplete", False, "Bone rotation column missing X/Y/Z/W label"
    if not type_label and not property_label and not component_label:
        return "empty", False, "Empty header cell"
    return "other", False, "Column not used for Layer 2"


def build_column_map(
    header_rows: list[HeaderRow],
    frame_time: FrameTimeDetection,
) -> list[ColumnRecord]:
    type_row = _row_by_role(header_rows, "type") or []
    name_row = _row_by_role(header_rows, "name") or []
    id_row = _row_by_role(header_rows, "id") or []
    parent_row = _row_by_role(header_rows, "parent") or []
    property_row = _row_by_role(header_rows, "property") or []
    component_row = _row_by_role(header_rows, "component") or []

    max_len = max(
        len(type_row),
        len(name_row),
        len(id_row),
        len(parent_row),
        len(property_row),
        len(component_row),
        (frame_time.frame_column_index or -1) + 1,
        (frame_time.time_column_index or -1) + 1,
    )

    columns: list[ColumnRecord] = []
    for idx in range(max_len):
        type_label = type_row[idx].strip() if idx < len(type_row) else ""
        source_name = name_row[idx].strip() if idx < len(name_row) else ""
        source_id = id_row[idx].strip() if idx < len(id_row) else ""
        source_parent = parent_row[idx].strip() if idx < len(parent_row) else ""
        property_label = property_row[idx].strip() if idx < len(property_row) else ""
        component_label = component_row[idx].strip() if idx < len(component_row) else ""

        if idx == frame_time.frame_column_index and not component_label:
            component_label = frame_time.frame_label or "Frame"
        if idx == frame_time.time_column_index and not component_label:
            component_label = frame_time.time_label or "Time"

        layer2_role, layer2_used, notes = classify_layer2_role(
            type_label,
            property_label,
            component_label,
            frame_time,
            idx,
        )
        flat_name = make_flat_column_name(
            idx,
            type_label,
            source_name,
            property_label,
            component_label,
            frame_time,
        )
        columns.append(
            ColumnRecord(
                column_index=idx,
                flat_name=flat_name,
                type_label=type_label,
                source_name=source_name,
                source_id=source_id,
                source_parent=source_parent,
                property_label=property_label,
                component_label=component_label,
                layer2_role=layer2_role,
                layer2_used=layer2_used,
                notes=notes,
            )
        )
    return columns


def parse_motive_header(csv_path: Path, max_lines: int = 20) -> ParsedMotiveHeader:
    header_rows = read_header_block(csv_path, max_lines=max_lines)
    metadata_row = next((row for row in header_rows if row.role == "metadata"), None)
    metadata = parse_metadata_fields(metadata_row.cells) if metadata_row else None
    component_row = _row_by_role(header_rows, "component")
    frame_time = detect_frame_time_columns(header_rows, component_row)
    columns = build_column_map(header_rows, frame_time)
    flat_names = [col.flat_name for col in columns]
    role_line_numbers: dict[str, int] = {}
    for row in header_rows:
        if row.role in {"blank", "unknown", "data"}:
            continue
        role_line_numbers[row.role] = row.line_number
    warnings: list[str] = []
    if frame_time.frame_column_index is None:
        warnings.append("Frame column not detected in header block")
    if frame_time.time_column_index is None:
        warnings.append("Time column not detected in header block")
    data_start = detect_data_start_line(header_rows)
    if data_start is None:
        warnings.append("Data start row not detected in first 20 lines")

    return ParsedMotiveHeader(
        csv_path=csv_path,
        header_rows=header_rows,
        metadata=metadata,
        metadata_line_number=metadata_row.line_number if metadata_row else None,
        data_start_line_number=data_start,
        role_line_numbers=role_line_numbers,
        columns=columns,
        flat_column_names=flat_names,
        frame_time=frame_time,
        warnings=warnings,
    )


def bone_rotation_groups(columns: list[ColumnRecord]) -> dict[str, dict[str, int]]:
    """Group Bone Rotation X/Y/Z/W columns by source bone name."""
    groups: dict[str, dict[str, int]] = {}
    for col in columns:
        if col.layer2_role != "bone_rotation_quaternion":
            continue
        groups.setdefault(col.source_name, {})[col.component_label] = col.column_index
    return groups
