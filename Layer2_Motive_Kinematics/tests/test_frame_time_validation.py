"""Tests for Stage 03 frame/time validation."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from layer2_motive.parsing import parse_motive_header
from layer2_motive.stages.stage03 import run_stage_03
from layer2_motive.timing import (
    TimingThresholds,
    evaluate_timing_status,
    load_frame_time_columns,
    validate_frame_time,
)
from layer2_motive.validation import HardStopError

FIXTURES = Path(__file__).parent / "fixtures"
VALID = FIXTURES / "timing_valid_monotonic.csv"
DUPLICATE = FIXTURES / "timing_duplicate_frame.csv"
MISSING = FIXTURES / "timing_missing_frame.csv"
NON_INCREASING_TIME = FIXTURES / "timing_non_increasing_time.csv"
RATE_120 = FIXTURES / "timing_sampling_rate_120hz.csv"

_HEADER = (
    "Format Version,1.25,Take Name,TestTake,Take Notes,,Capture Frame Rate,120.000000,"
    "Export Frame Rate,120.000000,Total Exported Frames,10,Rotation Type,Quaternion,"
    "Length Units,Millimeters,Coordinate Space,Global\n"
    "\n"
    ",Type,Bone,Bone,Bone,Bone\n"
    ",Name,900:Ab,900:Ab,900:Ab,900:Ab\n"
    ",ID,id0,id0,id0,id0\n"
    ",Parent,Root,Root,Root,Root\n"
    ",,Rotation,Rotation,Rotation,Rotation\n"
    "Frame,Time (Seconds),X,Y,Z,W\n"
)


def _write_timing_fixture(path: Path, rows: list[tuple[int, float]]) -> None:
    lines = [_HEADER]
    quat = "0,0,0,1"
    for frame, time_val in rows:
        lines.append(f"{frame},{time_val:.6f},{quat}\n")
    path.write_text("".join(lines), encoding="utf-8")


@pytest.fixture(scope="module", autouse=True)
def _build_fixtures() -> None:
    dt = 1.0 / 120.0
    _write_timing_fixture(VALID, [(0, 0.0), (1, dt), (2, 2 * dt), (3, 3 * dt)])
    _write_timing_fixture(DUPLICATE, [(0, 0.0), (1, dt), (1, 2 * dt), (2, 3 * dt)])
    _write_timing_fixture(MISSING, [(0, 0.0), (1, dt), (3, 2 * dt), (4, 3 * dt)])
    _write_timing_fixture(NON_INCREASING_TIME, [(0, 0.0), (1, dt), (2, dt), (3, 2 * dt)])
    _write_timing_fixture(RATE_120, [(i, i * dt) for i in range(10)])


def test_valid_monotonic_frame_time_passes() -> None:
    parsed = parse_motive_header(VALID)
    frame, time = load_frame_time_columns(VALID, parsed)
    result = validate_frame_time(parsed, frame, time)
    assert result.timing_status == "pass"
    assert result.frame.missing_frame_count == 0
    assert result.frame.duplicate_frame_count == 0
    assert result.frame.non_monotonic_frame_count == 0
    assert result.time.non_positive_dt_count == 0
    assert result.stage04_may_proceed is True


def test_duplicate_frame_warning() -> None:
    parsed = parse_motive_header(DUPLICATE)
    frame, time = load_frame_time_columns(DUPLICATE, parsed)
    result = validate_frame_time(parsed, frame, time)
    assert result.frame.duplicate_frame_count == 1
    assert result.frame.non_monotonic_frame_count >= 1
    assert result.timing_status == "fail"


def test_missing_frame_warning() -> None:
    parsed = parse_motive_header(MISSING)
    frame, time = load_frame_time_columns(MISSING, parsed)
    result = validate_frame_time(parsed, frame, time)
    assert result.frame.missing_frame_count == 1
    assert len(result.frame.frame_gaps) == 1
    assert result.timing_status == "warning"
    assert result.stage04_may_proceed is True


def test_non_increasing_time_fails() -> None:
    parsed = parse_motive_header(NON_INCREASING_TIME)
    frame, time = load_frame_time_columns(NON_INCREASING_TIME, parsed)
    result = validate_frame_time(parsed, frame, time)
    assert result.time.non_positive_dt_count >= 1
    assert result.timing_status == "fail"
    assert result.stage04_may_proceed is False


def test_inferred_sampling_rate_120hz() -> None:
    parsed = parse_motive_header(RATE_120)
    frame, time = load_frame_time_columns(RATE_120, parsed)
    result = validate_frame_time(parsed, frame, time)
    assert result.time.inferred_sampling_rate_hz == pytest.approx(120.0, rel=1e-3)
    assert result.time.metadata_sampling_rate_hz == pytest.approx(120.0)
    assert result.time.rate_pct_diff == pytest.approx(0.0, abs=0.01)
    assert result.timing_status == "pass"


def test_sampling_rate_metadata_mismatch_warning() -> None:
    parsed = parse_motive_header(RATE_120)
    frame, time = load_frame_time_columns(RATE_120, parsed)
    thresholds = TimingThresholds(metadata_rate_tolerance_pct=0.01)
    result = validate_frame_time(parsed, frame, time, thresholds=thresholds)
    result.time.rate_pct_diff = 1.0
    evaluated = evaluate_timing_status(result.frame, result.time, thresholds=thresholds)
    assert evaluated.timing_status == "warning"


def test_stage03_report_outputs(tmp_path: Path) -> None:
    parsed = parse_motive_header(VALID)
    run_stage_03(VALID, tmp_path, parsed=parsed)
    stage_dir = tmp_path / "03_frame_time_validation"
    assert (stage_dir / "report.md").exists()
    assert (stage_dir / "frame_time_summary.csv").exists()
    assert (stage_dir / "frame_gap_report.csv").exists()
    assert (stage_dir / "time_step_report.csv").exists()
    assert (stage_dir / "assumptions_and_limitations.md").exists()
    summary = pd.read_csv(stage_dir / "frame_time_summary.csv")
    assert summary.iloc[0]["timing_status"] == "pass"


def test_stage03_hard_stop_on_fail(tmp_path: Path) -> None:
    parsed = parse_motive_header(NON_INCREASING_TIME)
    with pytest.raises(HardStopError):
        run_stage_03(NON_INCREASING_TIME, tmp_path, parsed=parsed)
    assert (tmp_path / "03_frame_time_validation" / "report.md").exists()
