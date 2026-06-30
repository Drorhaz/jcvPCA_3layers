"""Tests for exercise segmentation spreadsheet parsing."""

from __future__ import annotations

from pathlib import Path

import pytest

from pre_jvcpca_review.exercise_segments import (
    GAGA_EXERCISE_ID_TO_LABEL,
    GAGA_EXERCISE_LABELS,
    GROUP4_LABEL,
    default_exercise_segments_path,
    exercise_choice_label,
    gaga_label_for_exercise_id,
    group4_window,
    load_exercise_segments,
    make_window_label,
    sheet_name_to_session_id,
)

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_XLSX = ROOT / "segmentation" / "671_ex_segmentatios_frames.xlsx"


def test_sheet_name_to_session_id() -> None:
    assert sheet_name_to_session_id("671 - T1P1R2") == "671_T1_P1_R2"
    assert sheet_name_to_session_id("671 - T3P1R1") == "671_T3_P1_R1"
    assert sheet_name_to_session_id("bad sheet") is None


def test_make_window_label() -> None:
    assert make_window_label("671_T1_P1_R2", 14040, 20880) == "671_T1_P1_R2_s14040_e20880"
    assert (
        make_window_label("671_T1_P1_R2", 14040, 20880, tag="g4")
        == "671_T1_P1_R2_g4_s14040_e20880"
    )


@pytest.mark.skipif(not EXAMPLE_XLSX.is_file(), reason="example workbook not present")
def test_load_example_workbook_sessions() -> None:
    catalog = load_exercise_segments(EXAMPLE_XLSX)
    assert "671_T1_P1_R2" in catalog
    assert "671_T3_P1_R1" in catalog
    assert len(catalog["671_T1_P1_R2"]) >= 15


@pytest.mark.skipif(not EXAMPLE_XLSX.is_file(), reason="example workbook not present")
def test_group4_window_matches_known_export() -> None:
    catalog = load_exercise_segments(EXAMPLE_XLSX)
    start, end = group4_window(catalog["671_T1_P1_R2"])
    assert start == 14040
    assert end == 20880
    label = make_window_label("671_T1_P1_R2", start, end, tag="g4")
    assert label == "671_T1_P1_R2_g4_s14040_e20880"


@pytest.mark.skipif(not EXAMPLE_XLSX.is_file(), reason="example workbook not present")
def test_exercise_choice_label_includes_frames() -> None:
    catalog = load_exercise_segments(EXAMPLE_XLSX)
    segment = next(seg for seg in catalog["671_T1_P1_R2"] if seg.exercise_id == 13)
    label = exercise_choice_label(segment)
    assert "Whole body curves" in label
    assert "19320" in label
    assert "20880" in label


def test_group4_label_constant() -> None:
    assert "Group 4" in GROUP4_LABEL


def test_default_exercise_segments_path_points_to_segmentation_dir() -> None:
    root = ROOT
    path = default_exercise_segments_path(root)
    assert path.parent.name == "segmentation"
    assert path.name == "671_ex_segmentatios_frames.xlsx"


@pytest.mark.parametrize("exercise_id,label", list(GAGA_EXERCISE_ID_TO_LABEL.items()))
def test_gaga_label_for_exercise_id(exercise_id: int, label: str) -> None:
    assert gaga_label_for_exercise_id(exercise_id) == label
    assert label in GAGA_EXERCISE_LABELS
