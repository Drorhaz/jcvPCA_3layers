"""Tests for segmentation coverage and xlsx path resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def snapshot():
    from project_status import load_project_snapshot

    return load_project_snapshot(project_root=REPO_ROOT)


def test_exercise_segments_path_repo_root():
    sys_path_added = str(REPO_ROOT / "Layer2.5_Segmentation" / "src")
    import sys

    if sys_path_added not in sys.path:
        sys.path.insert(0, sys_path_added)
    from pre_jvcpca_review.exercise_segments import exercise_segments_path_for_participant

    path = exercise_segments_path_for_participant(REPO_ROOT, "671")
    assert path.is_file()
    assert "Layer2.5_Segmentation" in str(path)
    assert path.name == "671_ex_segmentatios_frames.xlsx"


def test_resolved_segments_include_frame_provenance(snapshot):
    from analysis_request import AnalysisRequestInput, build_analysis_request, comparison_spec_from_preset

    inp = AnalysisRequestInput(
        participant_id="671",
        p_phases=("P1", "P2"),
        repetitions=("R1",),
        comparisons=[comparison_spec_from_preset("L1_T1_vs_T2", ("R1",))],
    )
    req = build_analysis_request(snapshot, inp, request_id="seg_prov_test")
    seg = req["resolved_segments"][0]
    assert "start_frame" in seg
    assert "end_frame" in seg
    assert "exercise_id" in seg
    assert seg["segmentation_source"]
    assert seg["start_frame"] is not None


def test_all_in_sheet_selection_includes_non_gaga(snapshot):
    from analysis_request import (
        AnalysisRequestInput,
        build_analysis_request,
        comparison_spec_from_preset,
    )
    from segmentation_coverage import EXERCISE_SELECTION_ALL_IN_SHEET

    inp = AnalysisRequestInput(
        participant_id="671",
        p_phases=("P1",),
        repetitions=("R1",),
        comparisons=[comparison_spec_from_preset("L1_T1_vs_T2", ("R1",))],
        exercise_selection_mode=EXERCISE_SELECTION_ALL_IN_SHEET,
    )
    req = build_analysis_request(snapshot, inp, request_id="all_sheet_test")
    ids = {s["exercise_id"] for s in req["resolved_segments"]}
    assert 1 in ids
    assert 9 in ids


def test_coverage_rows_match_xlsx_frames(snapshot):
    from analysis_request import AnalysisRequestInput, comparison_spec_from_preset
    from segmentation_coverage import build_segmentation_coverage_rows, COVERAGE_EXPORTED

    inp = AnalysisRequestInput(
        participant_id="671",
        p_phases=("P1",),
        repetitions=("R1",),
        comparisons=[comparison_spec_from_preset("L1_T1_vs_T2", ("R1",))],
    )
    rows, seg_path = build_segmentation_coverage_rows(snapshot, inp)
    assert seg_path and seg_path.is_file()
    p1 = next(r for r in rows if r["exercise_export_label"] == "P1" and r["session_id"] == "671_T1_P1_R1")
    assert p1["start_frame"] == 14280
    assert p1["end_frame"] == 15240
    assert p1["coverage_status"] == COVERAGE_EXPORTED
