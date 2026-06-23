"""Tests for Stage 04 quaternion norm / missingness / validity QC."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from layer2_motive.parsing import parse_motive_header
from layer2_motive.quaternion_qc import (
    QuaternionQCThresholds,
    evaluate_bone_quaternion_qc,
)
from layer2_motive.stages.stage04 import run_stage_04
from layer2_motive.validation import HardStopError

FIXTURES = Path(__file__).parent / "fixtures"
VALID = FIXTURES / "qc_valid_unit_quaternion.csv"
NON_UNIT_WARN = FIXTURES / "qc_non_unit_warning.csv"
ZERO_NORM = FIXTURES / "qc_zero_norm_fail.csv"
NON_FINITE = FIXTURES / "qc_non_finite_fail.csv"
SHORT_GAP = FIXTURES / "qc_short_gap_warning.csv"
LONG_GAP = FIXTURES / "qc_long_gap_fail.csv"

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


def _write_qc_fixture(path: Path, rows: list[tuple[int, float, str]]) -> None:
    lines = [_HEADER]
    for frame, time_val, quat in rows:
        lines.append(f"{frame},{time_val:.6f},{quat}\n")
    path.write_text("".join(lines), encoding="utf-8")


def _series(values: list[list[float]]) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    arr = np.asarray(values, dtype=float)
    return (
        pd.Series(arr[:, 0]),
        pd.Series(arr[:, 1]),
        pd.Series(arr[:, 2]),
        pd.Series(arr[:, 3]),
    )


@pytest.fixture(scope="module", autouse=True)
def _build_fixtures() -> None:
    dt = 1.0 / 120.0
    unit = "0,0,0,1"
    _write_qc_fixture(VALID, [(i, i * dt, unit) for i in range(10)])

    warn_quat = "0,0,0,1.005"
    _write_qc_fixture(NON_UNIT_WARN, [(i, i * dt, warn_quat) for i in range(10)])

    _write_qc_fixture(ZERO_NORM, [(0, 0.0, "0,0,0,0")] + [(i, i * dt, unit) for i in range(1, 10)])

    _write_qc_fixture(
        NON_FINITE,
        [(0, 0.0, "0,0,0,1"), (1, dt, "nan,0,0,1")] + [(i, i * dt, unit) for i in range(2, 10)],
    )

    short_gap_rows: list[tuple[int, float, str]] = []
    for i in range(10):
        quat = ",,," if 2 <= i <= 4 else unit
        short_gap_rows.append((i, i * dt, quat))
    _write_qc_fixture(SHORT_GAP, short_gap_rows)

    long_gap_rows: list[tuple[int, float, str]] = []
    for i in range(12):
        quat = ",,," if 1 <= i <= 7 else unit
        long_gap_rows.append((i, i * dt, quat))
    _write_qc_fixture(LONG_GAP, long_gap_rows)


def test_valid_unit_quaternion_passes() -> None:
    x, y, z, w = _series([[0, 0, 0, 1]] * 5)
    result = evaluate_bone_quaternion_qc(
        bone_name="Ab",
        x=x,
        y=y,
        z=z,
        w=w,
        has_complete_xyzw_columns=True,
        frame_series=pd.Series(range(5)),
    )
    assert result.qc_status == "pass"
    assert result.stage05_may_proceed is True
    assert result.zero_norm_count == 0
    assert result.max_abs_norm_error == pytest.approx(0.0)


def test_non_unit_quaternion_warning() -> None:
    x, y, z, w = _series([[0, 0, 0, 1.005]] * 5)
    result = evaluate_bone_quaternion_qc(
        bone_name="Ab",
        x=x,
        y=y,
        z=z,
        w=w,
        has_complete_xyzw_columns=True,
        frame_series=pd.Series(range(5)),
    )
    assert result.qc_status == "warning"
    assert result.stage05_may_proceed is True
    assert result.max_abs_norm_error == pytest.approx(0.005, abs=1e-6)


def test_non_unit_quaternion_fail_above_warning_threshold() -> None:
    x, y, z, w = _series([[0, 0, 0, 1.05]] * 5)
    result = evaluate_bone_quaternion_qc(
        bone_name="Ab",
        x=x,
        y=y,
        z=z,
        w=w,
        has_complete_xyzw_columns=True,
        frame_series=pd.Series(range(5)),
    )
    assert result.qc_status == "fail"
    assert result.stage05_may_proceed is False


def test_zero_norm_quaternion_fails() -> None:
    x, y, z, w = _series([[0, 0, 0, 0]])
    result = evaluate_bone_quaternion_qc(
        bone_name="Ab",
        x=x,
        y=y,
        z=z,
        w=w,
        has_complete_xyzw_columns=True,
        frame_series=pd.Series([0]),
    )
    assert result.qc_status == "fail"
    assert result.zero_norm_count == 1
    assert result.stage05_may_proceed is False


def test_non_finite_component_fails() -> None:
    x = pd.Series([np.inf])
    y, z, w = pd.Series([0.0]), pd.Series([0.0]), pd.Series([1.0])
    result = evaluate_bone_quaternion_qc(
        bone_name="Ab",
        x=x,
        y=y,
        z=z,
        w=w,
        has_complete_xyzw_columns=True,
        frame_series=pd.Series([0]),
    )
    assert result.qc_status == "fail"
    assert result.non_finite_row_count >= 1
    assert result.stage05_may_proceed is False


def test_short_invalid_gap_warning() -> None:
    x = pd.Series([0.0, 0.0, np.nan, np.nan, np.nan, 0.0, 0.0, 0.0, 0.0, 0.0])
    y = pd.Series([0.0, 0.0, np.nan, np.nan, np.nan, 0.0, 0.0, 0.0, 0.0, 0.0])
    z = pd.Series([0.0, 0.0, np.nan, np.nan, np.nan, 0.0, 0.0, 0.0, 0.0, 0.0])
    w = pd.Series([1.0, 1.0, np.nan, np.nan, np.nan, 1.0, 1.0, 1.0, 1.0, 1.0])
    result = evaluate_bone_quaternion_qc(
        bone_name="Ab",
        x=x,
        y=y,
        z=z,
        w=w,
        has_complete_xyzw_columns=True,
        frame_series=pd.Series(range(10)),
        thresholds=QuaternionQCThresholds(min_complete_xyzw_percent=50.0),
    )
    assert result.longest_invalid_gap_length == 3
    assert result.qc_status == "warning"
    assert result.stage05_may_proceed is True


def test_long_invalid_gap_fails() -> None:
    head = [[0.0, 0.0, 0.0, 1.0]]
    gap = [[np.nan, np.nan, np.nan, np.nan]] * 6
    tail = [[0.0, 0.0, 0.0, 1.0]]
    values = head + gap + tail
    x, y, z, w = _series(values)
    result = evaluate_bone_quaternion_qc(
        bone_name="Ab",
        x=x,
        y=y,
        z=z,
        w=w,
        has_complete_xyzw_columns=True,
        frame_series=pd.Series(range(len(values))),
        thresholds=QuaternionQCThresholds(min_complete_xyzw_percent=50.0),
    )
    assert result.longest_invalid_gap_length == 6
    assert result.qc_status == "fail"
    assert result.stage05_may_proceed is False


def test_stage04_report_outputs_valid_fixture(tmp_path: Path) -> None:
    parsed = parse_motive_header(VALID)
    run_stage_04(VALID, tmp_path, parsed=parsed)
    stage_dir = tmp_path / "04_quaternion_qc"
    assert (stage_dir / "report.md").exists()
    assert (stage_dir / "quaternion_qc_summary.csv").exists()
    assert (stage_dir / "quaternion_qc_by_bone.csv").exists()
    assert (stage_dir / "quaternion_invalid_gap_report.csv").exists()
    assert (stage_dir / "assumptions_and_limitations.md").exists()
    summary = pd.read_csv(stage_dir / "quaternion_qc_summary.csv")
    assert summary.iloc[0]["file_qc_status"] == "pass"
    assert str(summary.iloc[0]["stage05_may_proceed"]).lower() == "true"
    report = (stage_dir / "report.md").read_text(encoding="utf-8")
    assert "Stage 04 does not perform sign-continuity" in report


def test_stage04_hard_stop_on_zero_norm(tmp_path: Path) -> None:
    parsed = parse_motive_header(ZERO_NORM)
    with pytest.raises(HardStopError):
        run_stage_04(ZERO_NORM, tmp_path, parsed=parsed)
    assert (tmp_path / "04_quaternion_qc" / "report.md").exists()


def test_stage04_fixture_non_unit_warning(tmp_path: Path) -> None:
    parsed = parse_motive_header(NON_UNIT_WARN)
    run_stage_04(NON_UNIT_WARN, tmp_path, parsed=parsed)
    summary = pd.read_csv(tmp_path / "04_quaternion_qc" / "quaternion_qc_summary.csv")
    assert summary.iloc[0]["file_qc_status"] == "warning"


def test_stage04_fixture_short_gap_warning(tmp_path: Path) -> None:
    parsed = parse_motive_header(SHORT_GAP)
    run_stage_04(
        SHORT_GAP,
        tmp_path,
        parsed=parsed,
        thresholds=QuaternionQCThresholds(min_complete_xyzw_percent=50.0),
    )
    summary = pd.read_csv(tmp_path / "04_quaternion_qc" / "quaternion_qc_summary.csv")
    assert summary.iloc[0]["file_qc_status"] == "warning"
    gaps = pd.read_csv(tmp_path / "04_quaternion_qc" / "quaternion_invalid_gap_report.csv")
    assert len(gaps) == 1
    assert gaps.iloc[0]["gap_length_frames"] == 3
