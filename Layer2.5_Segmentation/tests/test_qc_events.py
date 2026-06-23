"""Tests for Layer 1 QC event normalization."""

import pandas as pd

from layer2_motive.segmentation.load_inputs import load_layer1_qc_folder
from layer2_motive.segmentation.qc_events import (
    build_layer1_event_table,
    normalize_artifact_events,
    normalize_gap_summary_events,
    normalize_interval_events,
    normalize_qc_mask_events,
    parse_affected_markers,
    parse_gap_intervals_s,
    seconds_to_frame,
)


def test_qc_mask_normalization_uses_flags_only():
    qc_mask = pd.DataFrame(
        {
            "frame": [0, 1, 2],
            "time_s": [0.0, 0.008333, 0.016667],
            "flag_gap_0p2": [False, True, True],
            "flag_gap_0p5": [False, False, True],
            "flag_artifact_sigma": [False, False, False],
            "flag_segment_swap": [False, False, False],
            "flag_edge_effect": [False, False, False],
            "reason": ["", "GAP_GE_0P2", "GAP_GE_0P5"],
        }
    )
    events = normalize_qc_mask_events(qc_mask, "TEST_SESSION")
    assert not events.empty
    assert "frame_status" not in set(events["qc_type"])
    assert "marker_gap_0p2" in events["qc_type"].values
    assert events.loc[events["frame"] == 1, "severity"].iloc[0] == "flag"


def test_interval_normalization(fixture_layer1_dir):
    bundle = load_layer1_qc_folder(fixture_layer1_dir)
    assert bundle.qc_mask_intervals is not None
    events = normalize_interval_events(
        bundle.qc_mask_intervals.head(5),
        "671_T1_P1_R1",
        frame_rate_hz=float(bundle.manifest["frame_rate_hz"]),
    )
    assert not events.empty
    assert events["marker_raw_name"].notna().any()
    assert events["qc_type"].isin(
        {"marker_gap_0p5", "segment_swap", "edge_effect"}
    ).any()
    assert events.loc[events["marker_raw_name"].notna(), "entity_type"].isin(
        {"marker", "segment_pair"}
    ).all()


def test_parse_affected_markers_splits_semicolons():
    assert parse_affected_markers("671:LFArm;671:RFArm") == ["671:LFArm", "671:RFArm"]
    assert parse_affected_markers("") == []


def test_build_layer1_event_table_uses_interval_marker_attribution(fixture_layer1_dir):
    bundle = load_layer1_qc_folder(fixture_layer1_dir)
    events = build_layer1_event_table(bundle, "671_T1_P1_R1")
    interval_events = events.loc[events["source_file"] == "qc_mask_intervals.csv"]
    assert not interval_events.empty
    assert interval_events["marker_raw_name"].notna().any()
    mapped = interval_events.loc[
        interval_events["related_joint_family"].astype(str) != "unknown"
    ]
    assert not mapped.empty


def test_artifact_events_normalization(fixture_layer1_dir):
    bundle = load_layer1_qc_folder(fixture_layer1_dir)
    assert bundle.artifact_events is not None
    events = normalize_artifact_events(bundle.artifact_events.head(10), "671_T1_P1_R1")
    assert not events.empty
    assert set(events["qc_type"]).issubset({"artifact_sigma", "segment_swap"})
    assert events["marker_raw_name"].notna().all()
    assert "body_region_group" in events.columns


def test_parse_gap_intervals_s_and_seconds_to_frame():
    assert parse_gap_intervals_s("131.80-132.50; 152.22-152.74") == [
        (131.80, 132.50),
        (152.22, 152.74),
    ]
    assert seconds_to_frame(136.68, 120.0) == 16402
    assert seconds_to_frame(137.28, 120.0) == 16474


def test_normalize_gap_summary_events_uses_frame_durations(fixture_layer1_dir):
    bundle = load_layer1_qc_folder(fixture_layer1_dir)
    assert bundle.gaps_over_0p5s is not None
    events = normalize_gap_summary_events(
        bundle.gaps_over_0p5s,
        "671_T1_P1_R1",
        qc_type="marker_gap_0p5",
        source_file="gaps_over_0p5s.csv",
        frame_rate_hz=float(bundle.manifest["frame_rate_hz"]),
    )
    assert not events.empty
    rfarm = events.loc[events["marker_raw_name"] == "671:RFArm"].iloc[0]
    assert int(rfarm["duration_frames"]) >= 60
    assert rfarm["qc_type"] == "marker_gap_0p5"


def test_build_layer1_event_table_prefers_gap_files_over_interval_gaps(fixture_layer1_dir):
    bundle = load_layer1_qc_folder(fixture_layer1_dir)
    events = build_layer1_event_table(bundle, "671_T1_P1_R1")
    gap_file_events = events.loc[events["source_file"] == "gaps_over_0p5s.csv"]
    interval_gap_events = events.loc[
        (events["source_file"] == "qc_mask_intervals.csv")
        & (events["qc_type"].isin(["marker_gap_0p5", "marker_gap_0p2"]))
    ]
    assert not gap_file_events.empty
    assert interval_gap_events.empty
    artifact_events = events.loc[events["source_file"] == "artifact_events.csv"]
    assert set(artifact_events["qc_type"]).issubset({"artifact_sigma", "segment_swap"})


def test_build_layer1_event_table_from_fixture(fixture_layer1_dir):
    bundle = load_layer1_qc_folder(fixture_layer1_dir)
    events = build_layer1_event_table(bundle, "671_T1_P1_R1")
    assert not events.empty
    assert set(events["source_file"].unique()) >= {"qc_mask.csv"}
    assert events["session_key"].eq("671_T1_P1_R1").all()
    # No link assignment in Layer 1 events
    assert "link_id" not in events.columns
    # Phase A+ marker-family overlay columns
    assert "normalized_marker_name" in events.columns
    assert "related_joint_family" in events.columns
    assert "mapping_source" in events.columns
    assert "attached_bone" in events.columns
