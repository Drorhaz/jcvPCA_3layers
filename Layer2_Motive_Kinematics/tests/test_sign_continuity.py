"""Tests for Stage 05 global quaternion sign-continuity correction."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from layer2_motive.parsing import parse_motive_header
from layer2_motive.quaternion_continuity import (
    apply_sign_continuity,
    consecutive_dot_products,
    process_bone_sign_continuity,
    validate_post_correction_dots,
)
from layer2_motive.stages.stage04 import run_stage_04
from layer2_motive.stages.stage05 import run_stage_05
from layer2_motive.validation import HardStopError

FIXTURES = Path(__file__).parent / "fixtures"
VALID = FIXTURES / "timing_valid_monotonic.csv"


def test_no_flip_sequence_unchanged() -> None:
    quats = np.tile(np.array([0.0, 0.0, 0.0, 1.0]), (5, 1))
    corrected, flip_mask = apply_sign_continuity(quats)
    assert np.allclose(corrected, quats)
    assert flip_mask.sum() == 0


def test_single_flip_corrected() -> None:
    quats = np.array(
        [
            [0.0, 0.0, 0.0, 1.0],
            [0.0, 0.0, 0.0, -1.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
    )
    corrected, flip_mask = apply_sign_continuity(quats)
    assert corrected[1].tolist() == [0.0, 0.0, 0.0, 1.0]
    assert flip_mask.tolist() == [False, True, False]


def test_multiple_flips_corrected() -> None:
    quats = np.array(
        [
            [1.0, 0.0, 0.0, 0.0],
            [-1.0, 0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0, 0.0],
            [-1.0, 0.0, 0.0, 0.0],
        ]
    )
    corrected, flip_mask = apply_sign_continuity(quats)
    assert np.allclose(corrected, np.tile([1.0, 0.0, 0.0, 0.0], (4, 1)))
    assert flip_mask.sum() == 2


def test_post_correction_dots_non_negative() -> None:
    quats = np.array(
        [
            [0.0, 0.0, 0.0, 1.0],
            [0.0, 0.0, 0.0, -1.0],
            [0.0, 0.0, 0.0, -1.0],
        ]
    )
    corrected, _ = apply_sign_continuity(quats)
    valid, min_dot = validate_post_correction_dots(corrected)
    assert valid is True
    assert min_dot is not None
    assert min_dot >= 0.0
    assert np.all(consecutive_dot_products(corrected) >= 0.0)


def test_process_bone_sign_continuity_reports_flip_frames() -> None:
    quats = np.array([[0.0, 0.0, 0.0, 1.0], [0.0, 0.0, 0.0, -1.0]])
    _, _, result = process_bone_sign_continuity(
        source_bone_name="671:Ab",
        canonical_bone_name="Ab",
        quats=quats,
        frame_series=pd.Series([10, 11]),
    )
    assert result.sign_flip_count == 1
    assert result.flip_frame_indices == [1]
    assert result.flip_frames == [11]


def test_stage05_report_outputs(tmp_path: Path) -> None:
    parsed = parse_motive_header(VALID)
    run_stage_04(VALID, tmp_path, parsed=parsed)
    run_stage_05(VALID, tmp_path, parsed=parsed)
    stage_dir = tmp_path / "05_sign_continuity"
    assert (stage_dir / "report.md").exists()
    assert (stage_dir / "sign_continuity_summary.csv").exists()
    assert (stage_dir / "sign_flips_by_bone.csv").exists()
    assert (stage_dir / "sign_flip_frames.csv").exists()
    assert (stage_dir / "global_quaternions_sign_continuous.parquet").exists()
    assert (stage_dir / "global_quaternions_sign_continuous.csv").exists()
    assert (stage_dir / "assumptions_and_limitations.md").exists()
    summary = pd.read_csv(stage_dir / "sign_continuity_summary.csv")
    assert str(summary.iloc[0]["post_correction_valid"]).lower() == "true"
    long_df = pd.read_parquet(stage_dir / "global_quaternions_sign_continuous.parquet")
    expected_cols = {
        "frame",
        "time",
        "source_bone_name",
        "canonical_bone_name",
        "qx",
        "qy",
        "qz",
        "qw",
        "flip_applied",
    }
    assert expected_cols.issubset(long_df.columns)


def test_stage05_refuses_without_stage04_pass(tmp_path: Path) -> None:
    parsed = parse_motive_header(VALID)
    with pytest.raises(HardStopError, match="Stage 04"):
        run_stage_05(VALID, tmp_path, parsed=parsed)


def test_stage05_refuses_when_stage04_failed(tmp_path: Path) -> None:
    stage04_dir = tmp_path / "04_quaternion_qc"
    stage04_dir.mkdir(parents=True)
    pd.DataFrame(
        [
            {
                "input_file": "x.csv",
                "quaternion_group_count": 1,
                "groups_pass": 0,
                "groups_warning": 0,
                "groups_fail": 1,
                "total_zero_norm_count": 1,
                "total_near_zero_norm_count": 0,
                "total_non_finite_count": 0,
                "max_abs_norm_error_observed": 1.0,
                "longest_invalid_gap_observed": 0,
                "file_qc_status": "fail",
                "stage05_may_proceed": False,
                "fail_reasons": "test",
                "warning_reasons": "",
            }
        ]
    ).to_csv(stage04_dir / "quaternion_qc_summary.csv", index=False)
    parsed = parse_motive_header(VALID)
    with pytest.raises(HardStopError, match="Stage 04 quaternion QC did not pass"):
        run_stage_05(VALID, tmp_path, parsed=parsed)
