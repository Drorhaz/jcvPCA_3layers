"""Tests for Motive header role detection (Stage 00)."""

from pathlib import Path

from layer2_motive.parsing import parse_motive_header

FIXTURE = Path(__file__).parent / "fixtures" / "minimal_motive_header.csv"


def test_header_detection_roles() -> None:
    parsed = parse_motive_header(FIXTURE)
    assert parsed.metadata is not None
    assert parsed.metadata.rotation_type == "Quaternion"
    assert parsed.metadata.coordinate_space == "Global"
    assert parsed.role_line_numbers["type"] == 3
    assert parsed.role_line_numbers["component"] == 8
    assert parsed.data_start_line_number == 9
    assert parsed.frame_time.frame_column_index == 0
    assert parsed.frame_time.time_column_index == 1


def test_bone_rotation_columns_detected() -> None:
    parsed = parse_motive_header(FIXTURE)
    used = [col for col in parsed.columns if col.layer2_used]
    assert len(used) > 0
    components = {col.component_label for col in used}
    assert components == {"X", "Y", "Z", "W"}


def test_no_pandas_multiindex_required() -> None:
    parsed = parse_motive_header(FIXTURE)
    assert len(parsed.flat_column_names) == len(parsed.columns)
    assert parsed.flat_column_names[0] == "frame"
    assert parsed.flat_column_names[1] == "time_seconds"
