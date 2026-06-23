"""Link-level RSS aggregation tests."""

from __future__ import annotations

import numpy as np
import pytest

from layer3_jcvpca.aggregation import aggregate_axis_to_link_rss
from layer3_jcvpca.io import build_joint_link_map
from layer3_jcvpca.validation import ValidationError, validate_jcvpca_matrix

from conftest import FEATURE_NAMES, make_matrix


def test_rss_matches_hand_computation():
    # One PC, six features (2 links x 3 axes), known absolute loadings.
    feature_names = FEATURE_NAMES
    A_abs = np.array([[0.1, 0.2, 0.2, 0.3, 0.0, 0.4]])
    B_abs = np.array([[0.2, 0.2, 0.1, 0.5, 0.0, 0.0]])
    link_map = build_joint_link_map(feature_names)

    df = aggregate_axis_to_link_rss(A_abs, B_abs, feature_names, link_map)

    link0 = df[df["link_id"] == "J004_Neck_to_Head"].iloc[0]
    expected_a0 = np.sqrt(0.1**2 + 0.2**2 + 0.2**2)
    expected_b0 = np.sqrt(0.2**2 + 0.2**2 + 0.1**2)
    assert link0["JRW_A_link"] == pytest.approx(expected_a0)
    assert link0["JRW_B_link"] == pytest.approx(expected_b0)
    assert link0["JcvPCA_link"] == pytest.approx(expected_b0 - expected_a0)

    link1 = df[df["link_id"] == "J028_Chest_to_Neck"].iloc[0]
    expected_a1 = np.sqrt(0.3**2 + 0.0**2 + 0.4**2)
    assert link1["JRW_A_link"] == pytest.approx(expected_a1)


def test_rss_is_not_simple_sum():
    feature_names = FEATURE_NAMES
    A_abs = np.array([[0.3, 0.4, 0.0, 0.0, 0.0, 0.0]])
    B_abs = np.array([[0.0, 0.0, 0.0, 0.0, 0.0, 0.0]])
    link_map = build_joint_link_map(feature_names)
    df = aggregate_axis_to_link_rss(A_abs, B_abs, feature_names, link_map)
    link0 = df[df["link_id"] == "J004_Neck_to_Head"].iloc[0]
    # RSS = 0.5, simple sum would be 0.7.
    assert link0["JRW_A_link"] == pytest.approx(0.5)
    assert link0["JRW_A_link"] != pytest.approx(0.7)


def test_weighted_requires_variance_ratio():
    feature_names = FEATURE_NAMES
    A_abs = np.zeros((1, 6))
    B_abs = np.zeros((1, 6))
    link_map = build_joint_link_map(feature_names)
    with pytest.raises(ValueError):
        aggregate_axis_to_link_rss(
            A_abs, B_abs, feature_names, link_map, export_weighted=True
        )


def test_incomplete_triplet_fails_validation(metadata_cols):
    # Drop one axis column -> link has incomplete rx/ry/rz triplet.
    df = make_matrix(n_rows=100, seed=1)
    df = df.drop(columns=["J004_Neck_to_Head_rz"])
    with pytest.raises(ValidationError) as exc:
        validate_jcvpca_matrix(df, metadata_cols)
    assert "J004_Neck_to_Head" in exc.value.report.get("incomplete_links", {})
