"""Tests for G4 analysis request builder."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def snapshot():
    from project_status import load_project_snapshot

    return load_project_snapshot(project_root=REPO_ROOT)


def _input_671_l1():
    from analysis_request import AnalysisRequestInput, comparison_spec_from_preset

    return AnalysisRequestInput(
        participant_id="671",
        p_phases=("P1", "P2", "P3"),
        repetitions=("R1", "R2"),
        comparisons=[comparison_spec_from_preset("L1_T1_vs_T2")],
        segment_preset="only_P1_P3",
    )


def test_build_analysis_request_structure(snapshot):
    from analysis_request import STATUS_BLOCKED, build_analysis_request

    req = build_analysis_request(snapshot, _input_671_l1(), request_id="test_671_L1")
    assert req["version"] == 1
    assert req["request_id"] == "test_671_L1"
    assert req["status"] in {STATUS_BLOCKED, "validated", "ready_for_execution"}
    assert req["execution"]["allowed"] is False
    assert req["provenance"]["science_hash"]
    assert len(req["provenance"]["science_hash"]) == 64
    assert req["resolved_segments"]
    assert "validation" in req
    assert req["validation"]["comparison_results"]


def test_validation_has_errors_or_warnings(snapshot):
    from analysis_request import validate_analysis_request

    messages, payload = validate_analysis_request(snapshot, _input_671_l1())
    assert messages
    assert "errors" in payload
    assert "warnings" in payload
    assert "inclusion_summary" in payload


def test_comparison_preset_longitudinal():
    from analysis_request import comparison_spec_from_preset

    spec = comparison_spec_from_preset("L2_T1_vs_T3")
    assert spec.comparison_type == "longitudinal"
    assert spec.timepoint_a == "T1"
    assert spec.timepoint_b == "T3"


def test_comparison_preset_repetition():
    from analysis_request import comparison_spec_from_preset

    spec = comparison_spec_from_preset("I_T2_R1_vs_R2")
    assert spec.comparison_type == "within_timepoint_repetition"
    assert spec.timepoint == "T2"


def test_save_and_load_roundtrip(snapshot, tmp_path):
    from analysis_request import build_analysis_request, load_analysis_request, save_analysis_request

    req = build_analysis_request(snapshot, _input_671_l1(), request_id="roundtrip_test")
    path = save_analysis_request(REPO_ROOT, req, requests_dir=tmp_path / "requests")
    loaded = load_analysis_request(path)
    assert loaded["request_id"] == "roundtrip_test"
    assert loaded["execution"]["allowed"] is False
    assert yaml.safe_load(path.read_text(encoding="utf-8"))["request_id"] == "roundtrip_test"


def test_segment_id_format(snapshot):
    from analysis_request import build_analysis_request, segment_id_from_row

    req = build_analysis_request(snapshot, _input_671_l1(), request_id="seg_test")
    seg = req["resolved_segments"][0]
    assert "::" in seg["segment_id"]
    assert seg["segment_id"] == segment_id_from_row(
        {
            "session_id": seg["session_id"],
            "gaga_exercise_label": seg["p_phase"],
        }
    )


def test_repetition_comparison_readiness(snapshot):
    from comparison_readiness import RepetitionComparisonRequest, evaluate_repetition_comparison_readiness

    result = evaluate_repetition_comparison_readiness(
        snapshot,
        RepetitionComparisonRequest(
            participant_id="671",
            timepoint="T1",
            p_phases=("P1", "P2"),
        ),
    )
    assert result.verdict
    assert result.segment_rows_expected == 4
