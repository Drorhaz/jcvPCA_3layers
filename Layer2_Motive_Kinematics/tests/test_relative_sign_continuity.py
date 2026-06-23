"""Tests for relative quaternion sign continuity (Stage 06)."""

from __future__ import annotations

import numpy as np

from layer2_motive.quaternion_continuity import SignContinuityThresholds
from layer2_motive.relative_rotation import process_relative_sign_continuity


def test_relative_sign_flip_detected_and_corrected() -> None:
    relative = np.array(
        [
            [0.0, 0.0, 0.0, 1.0],
            [0.0, 0.0, 0.0, -1.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
    )
    corrected, flip_mask, result = process_relative_sign_continuity(
        joint_id="J001",
        source_parent_bone="P",
        source_child_bone="C",
        parent_bone="P",
        child_bone="C",
        relative_quats=relative,
        thresholds=SignContinuityThresholds(),
        apply_correction=True,
    )
    assert result.raw_sign_flip_count == 2
    assert result.corrected_sign_flip_count == 0
    assert result.post_correction_valid is True
    assert result.correction_applied is True
    assert flip_mask.tolist() == [False, True, False]
    assert np.allclose(corrected[1], [0.0, 0.0, 0.0, 1.0])


def test_relative_sign_continuity_reports_dot_statistics() -> None:
    relative = np.tile(np.array([1.0, 0.0, 0.0, 0.0]), (4, 1))
    _, _, result = process_relative_sign_continuity(
        joint_id="J002",
        source_parent_bone="P",
        source_child_bone="C",
        parent_bone="P",
        child_bone="C",
        relative_quats=relative,
        apply_correction=False,
    )
    assert result.raw_sign_flip_count == 0
    assert result.min_raw_consecutive_dot is not None
    assert result.min_raw_consecutive_dot >= 0.0
