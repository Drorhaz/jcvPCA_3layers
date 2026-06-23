"""Tests for quaternion norm QC thresholds (Stage 04)."""

import pandas as pd

from layer2_motive.quaternion_qc import evaluate_bone_quaternion_qc


def test_quaternion_normalization_not_applied_in_qc() -> None:
    """Stage 04 reports norm error without repairing quaternions."""
    x = pd.Series([0.0, 0.0])
    y = pd.Series([0.0, 0.0])
    z = pd.Series([0.0, 0.0])
    w = pd.Series([2.0, 0.5])
    result = evaluate_bone_quaternion_qc(
        bone_name="Ab",
        x=x,
        y=y,
        z=z,
        w=w,
        has_complete_xyzw_columns=True,
        frame_series=pd.Series([0, 1]),
    )
    assert result.mean_norm == 1.25
    assert result.max_abs_norm_error == 1.0
