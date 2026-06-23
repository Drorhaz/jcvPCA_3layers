"""Tests for structural rotation population reporting."""

from pathlib import Path

from layer2_motive.hierarchy import build_bone_inventory, summarize_skeleton_structure
from layer2_motive.parsing import parse_motive_header
from layer2_motive.population import compute_rotation_population_report

FIXTURE = Path(__file__).parent / "fixtures" / "minimal_motive_header.csv"


def test_rotation_population_report_on_fixture() -> None:
    parsed = parse_motive_header(FIXTURE)
    inventory = build_bone_inventory(parsed.columns)
    rows, total_frames = compute_rotation_population_report(FIXTURE, parsed, inventory)
    assert total_frames == 2
    assert rows
    complete_rows = [
        row for row in rows if row["notes"] != "Incomplete XYZW column group in header"
    ]
    assert complete_rows
    assert all(row["population_status"] == "pass" for row in complete_rows)
    assert all(row["complete_xyzw_percent"] == 100.0 for row in complete_rows)


def test_skeleton_summary_reports_root_anchor_without_pelvis_rename() -> None:
    parsed = parse_motive_header(FIXTURE)
    inventory = build_bone_inventory(parsed.columns)
    summary = summarize_skeleton_structure(inventory)
    assert summary["root_anchors"]
    anchor = summary["root_anchors"][0]
    assert anchor["canonical_bone_name"] == "900"
    assert "Pelvis" not in anchor["canonical_bone_name"]
