"""Metadata detection from Motive CSV exports."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MotiveMetadata:
    raw_fields: dict[str, str] = field(default_factory=dict)
    rotation_type: str | None = None
    coordinate_space: str | None = None
    capture_frame_rate: str | None = None
    export_frame_rate: str | None = None
    total_frames: str | None = None
    length_units: str | None = None
    take_name: str | None = None
    format_version: str | None = None


def parse_metadata_fields(cells: list[str]) -> MotiveMetadata:
    """Parse key-value metadata from the first CSV row."""
    pairs: dict[str, str] = {}
    idx = 0
    while idx < len(cells) - 1:
        key = cells[idx].strip()
        value = cells[idx + 1].strip()
        if key:
            pairs[key] = value
        idx += 2

    return MotiveMetadata(
        raw_fields=pairs,
        format_version=pairs.get("Format Version"),
        take_name=pairs.get("Take Name"),
        rotation_type=pairs.get("Rotation Type"),
        coordinate_space=pairs.get("Coordinate Space"),
        capture_frame_rate=pairs.get("Capture Frame Rate"),
        export_frame_rate=pairs.get("Export Frame Rate"),
        total_frames=pairs.get("Total Exported Frames") or pairs.get("Total Frames in Take"),
        length_units=pairs.get("Length Units"),
    )


def metadata_rows(metadata: MotiveMetadata) -> list[dict[str, str]]:
    """Flatten metadata for CSV reporting."""
    rows = [
        {"field": "Format Version", "value": metadata.format_version or ""},
        {"field": "Take Name", "value": metadata.take_name or ""},
        {"field": "Rotation Type", "value": metadata.rotation_type or ""},
        {"field": "Coordinate Space", "value": metadata.coordinate_space or ""},
        {"field": "Capture Frame Rate", "value": metadata.capture_frame_rate or ""},
        {"field": "Export Frame Rate", "value": metadata.export_frame_rate or ""},
        {"field": "Total Frames", "value": metadata.total_frames or ""},
        {"field": "Length Units", "value": metadata.length_units or ""},
    ]
    known = {row["field"] for row in rows}
    for key, value in metadata.raw_fields.items():
        if key not in known:
            rows.append({"field": key, "value": value})
    return rows
