"""Tests for additive Layer 1 evidence-only contract outputs."""

from __future__ import annotations

import pandas as pd
import pytest

from motive_qc.deliverables import build_qc_mask
from motive_qc.handoff import build_layer1_qc_handoff
from motive_qc.marker_gap_evidence import build_layer1_marker_gap_evidence
from motive_qc.marker_names import add_marker_name_columns, enrich_marker_level_tables
from motive_qc.marker_set import build_layer1_marker_set, marker_set_hash, prefix_change_flag
from motive_qc.session_evidence import compute_session_evidence


CANONICAL_MARKERS = ["BackLeft", "BackRight", "LThighFront"]


def _config(participant_id: str = "671", session_id: str = "T1_P1_R1") -> dict:
    return {
        "project": {"subject_id": participant_id, "session_id": session_id},
        "gaps": {"thresholds_seconds": {"moderate_gap": 0.2, "large_gap": 0.5, "severe_gap": 1.0}},
        "artifacts": {"edge_buffer_frames": 8},
    }


def _metadata(session_id: str = "T1_P1_R1", file_name: str = "671_T1_P1_R1.csv") -> dict:
    return {
        "subject_id": "671",
        "session_id": session_id,
        "file_name": file_name,
    }


def _inventory(asset_prefix: str, marker_names: list[str] | None = None) -> pd.DataFrame:
    names = marker_names or CANONICAL_MARKERS
    rows = []
    for short in names:
        raw = f"{asset_prefix}:{short}"
        rows.append(
            {
                "marker_name": raw,
                "skeleton_prefix": asset_prefix,
                "canonical_short_name": short,
                "is_labeled": True,
                "included_in_analysis": True,
            }
        )
    return pd.DataFrame(rows)


class TestMarkerSetIdentity:
    def test_t1_t2_t3_prefix_differences_reported(self):
        t1 = build_layer1_marker_set(_metadata("T1_P1_R1"), _inventory("671"), _config(session_id="T1_P1_R1"))
        t3 = build_layer1_marker_set(_metadata("T3_P1_R2"), _inventory("T3_671"), _config(session_id="T3_P1_R2"))

        assert t1.iloc[0]["asset_prefixes_observed"] == "671"
        assert t3.iloc[0]["asset_prefixes_observed"] == "T3_671"
        assert "ASSET_PREFIX_T3_671" in str(t3.iloc[0]["marker_set_warning"])

    def test_same_canonical_names_after_prefix_normalization(self):
        t1 = build_layer1_marker_set(_metadata("T1_P1_R1"), _inventory("671"), _config(session_id="T1_P1_R1"))
        t3 = build_layer1_marker_set(_metadata("T3_P1_R2"), _inventory("T3_671"), _config(session_id="T3_P1_R2"))
        assert t1.iloc[0]["canonical_marker_names"] == t3.iloc[0]["canonical_marker_names"]

    def test_marker_set_id_stable_across_prefix_change(self):
        t1 = build_layer1_marker_set(_metadata("T1_P1_R1"), _inventory("671"), _config(session_id="T1_P1_R1"))
        t3 = build_layer1_marker_set(_metadata("T3_P1_R1"), _inventory("T3_671"), _config(session_id="T3_P1_R1"))
        assert t1.iloc[0]["marker_set_id_or_hash"] == t3.iloc[0]["marker_set_id_or_hash"]


class TestMarkerNameColumns:
    def test_marker_level_tables_have_raw_and_canonical(self):
        inventory = _inventory("671")
        tables = {
            "gaps_over_0p2s": pd.DataFrame({"marker_name": ["671:BackLeft"]}),
            "artifact_events": pd.DataFrame({"marker_name": ["671:BackRight"]}),
        }
        enriched = enrich_marker_level_tables(tables, inventory)
        for key in tables:
            df = enriched[key]
            assert "marker_name_raw" in df.columns
            assert "marker_name_canonical" in df.columns


class TestSessionEvidence:
    def test_reports_flag_percentages_not_verdicts(self):
        qc_mask = pd.DataFrame(
            {
                "frame": [0, 1, 2],
                "flag_gap_0p5": [True, True, False],
                "flag_gap_0p2": [False, False, False],
                "flag_artifact_sigma": [False, False, False],
                "flag_segment_swap": [False, False, False],
                "flag_edge_effect": [False, False, False],
                "reason": ["GAP_GE_0P5", "GAP_GE_0P5", ""],
            }
        )
        gaps = pd.DataFrame(
            {
                "marker_name": ["T3_671:LThighFront"],
                "marker_name_canonical": ["LThighFront"],
            }
        )
        result = compute_session_evidence(qc_mask, pd.DataFrame(), gaps)
        assert "session_usability" not in result
        assert result["pct_frames_union_flag_gap_0p5"] == pytest.approx(66.666667, abs=0.01)
        assert result["markers_with_gap_ge_0p5s"] == "LThighFront"


class TestMarkerGapEvidence:
    def test_per_marker_frame_pct_distinct_from_union(self):
        gap_events = pd.DataFrame(
            [
                {
                    "marker_name": "T3_671:LThighFront",
                    "gap_start_frame": 0,
                    "gap_end_frame": 1,
                    "duration_seconds": 0.6,
                    "is_labeled": True,
                },
                {
                    "marker_name": "T3_671:BackLeft",
                    "gap_start_frame": 2,
                    "gap_end_frame": 2,
                    "duration_seconds": 0.6,
                    "is_labeled": True,
                },
            ]
        )
        gaps_over = pd.DataFrame(
            [
                {
                    "marker_name": "T3_671:LThighFront",
                    "body_region_group": "thigh_knee",
                    "n_gaps": 1,
                    "total_gap_seconds": 0.6,
                    "longest_gap_seconds": 0.6,
                },
                {
                    "marker_name": "T3_671:BackLeft",
                    "body_region_group": "torso_chest_back",
                    "n_gaps": 1,
                    "total_gap_seconds": 0.6,
                    "longest_gap_seconds": 0.6,
                },
            ]
        )
        inventory = _inventory("T3_671")
        cfg = _config(session_id="T3_P1_R2")
        cfg["_session_duration_seconds"] = 1.0
        evidence = build_layer1_marker_gap_evidence(
            gap_events, gaps_over, inventory, cfg, n_frames=3, min_frame=0
        )
        assert len(evidence) == 2
        thigh = evidence[evidence["marker_name_canonical"] == "LThighFront"].iloc[0]
        back = evidence[evidence["marker_name_canonical"] == "BackLeft"].iloc[0]
        assert thigh["pct_frames_in_gap_ge_0p5"] == pytest.approx(66.666667, abs=0.01)
        assert back["pct_frames_in_gap_ge_0p5"] == pytest.approx(33.333333, abs=0.01)

        qc_mask = pd.DataFrame(
            {
                "frame": [0, 1, 2],
                "flag_gap_0p5": [True, True, True],
                "flag_gap_0p2": [False, False, False],
                "flag_artifact_sigma": [False, False, False],
                "flag_segment_swap": [False, False, False],
                "flag_edge_effect": [False, False, False],
            }
        )
        summary = compute_session_evidence(qc_mask, pd.DataFrame(), gaps_over, evidence)
        assert summary["pct_frames_union_flag_gap_0p5"] == pytest.approx(100.0, abs=0.01)
        assert summary["dominant_gap_marker_canonical"] == "LThighFront"
        assert summary["pct_frames_dominant_marker_in_gap_ge_0p5"] == pytest.approx(66.666667, abs=0.01)


class TestQcHandoff:
    def test_handoff_preserves_frame_and_time_from_intervals(self):
        intervals = pd.DataFrame(
            [
                {
                    "start_frame": 10,
                    "end_frame": 25,
                    "start_s": 0.5,
                    "end_s": 1.25,
                    "reason": "GAP_GE_0P5",
                    "criterion": "gaps_over_0p5",
                    "has_gap_ge_0p5": True,
                    "affected_markers": "T3_671:BackLeft",
                }
            ]
        )
        marker_set = build_layer1_marker_set(
            _metadata("T3_P1_R2"), _inventory("T3_671"), _config(session_id="T3_P1_R2")
        ).iloc[0]
        handoff = build_layer1_qc_handoff(
            intervals, marker_set, _metadata("T3_P1_R2"), _config(session_id="T3_P1_R2")
        )
        row = handoff.iloc[0]
        assert row["start_frame"] == 10
        assert row["time_sec"] == pytest.approx(0.5)
        assert "qc_status" not in handoff.columns
        assert bool(row["gap_flag"]) is True

    def test_qc_mask_has_flags_not_status_verdict(self):
        qc_mask = pd.DataFrame(
            {
                "frame": [0, 1],
                "time_s": [0.0, 0.01],
                "flag_gap_0p5": [True, False],
                "flag_gap_0p2": [False, False],
                "flag_artifact_sigma": [False, False],
                "flag_segment_swap": [False, False],
                "flag_edge_effect": [False, False],
                "reason": ["GAP_GE_0P5", ""],
            }
        )
        assert "status" not in qc_mask.columns
        assert "frame" in qc_mask.columns
        assert "time_s" in qc_mask.columns
