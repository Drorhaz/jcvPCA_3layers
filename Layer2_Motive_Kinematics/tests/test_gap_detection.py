"""Tests for invalid quaternion gap detection (Stage 04)."""

import numpy as np
import pandas as pd

from layer2_motive.quaternion_qc import find_contiguous_invalid_gaps


def test_find_contiguous_invalid_gaps() -> None:
    mask = np.array([False, True, True, False, True, False])
    gaps = find_contiguous_invalid_gaps(
        mask,
        bone_name="Ab",
        frame_series=pd.Series([10, 11, 12, 13, 14, 15]),
    )
    assert len(gaps) == 2
    assert gaps[0].gap_length_frames == 2
    assert gaps[0].gap_start_frame == 11
    assert gaps[1].gap_length_frames == 1
    assert gaps[1].gap_start_frame == 14
