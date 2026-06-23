"""Tests that the core function reproduces the paper's JcvPCA sequence."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA

from layer3_jcvpca.core import compute_jcvpca, select_selected_m_from_A

from conftest import make_matrix


def _paper_reference(A, B, feature_names, selected_m):
    """Independent re-implementation of the paper sequence for comparison."""
    A_centered = A[feature_names] - A[feature_names].mean()
    pca_A = PCA(n_components=selected_m)
    pca_A.fit(A_centered)
    pca_A_frame = pca_A.components_

    B_centered = B[feature_names] - B[feature_names].mean()
    B_projected = np.matmul(B_centered.to_numpy(), pca_A_frame.transpose())
    pca_B = PCA(n_components=selected_m)
    pca_B.fit(B_projected)
    pca_B_frame = pca_B.components_

    result_B = np.abs(np.matmul(pca_B_frame, pca_A_frame))
    sub = result_B - np.abs(pca_A_frame)
    return np.abs(pca_A_frame), result_B, sub


def test_core_matches_paper_sequence(feature_names):
    A = make_matrix(n_rows=300, seed=11)
    B = make_matrix(n_rows=300, seed=22)
    selected_m = len(feature_names)

    result = compute_jcvpca(A, B, feature_names, selected_m=selected_m)
    A_abs, B_abs, sub = _paper_reference(A, B, feature_names, selected_m)

    np.testing.assert_allclose(result["A_abs_loadings"], A_abs, atol=1e-10)
    np.testing.assert_allclose(result["B_abs_loadings"], B_abs, atol=1e-10)
    np.testing.assert_allclose(result["jcvpca_axis"], sub, atol=1e-10)


def test_jcvpca_axis_is_abs_b_minus_abs_a(feature_names):
    A = make_matrix(n_rows=150, seed=3)
    B = make_matrix(n_rows=150, seed=4)
    result = compute_jcvpca(A, B, feature_names, selected_m=len(feature_names))
    expected = result["B_abs_loadings"] - result["A_abs_loadings"]
    np.testing.assert_allclose(result["jcvpca_axis"], expected, atol=1e-12)


def test_B_centered_independently_not_with_A_mean(feature_names):
    """Adding a constant offset to all of B's features must not change results.

    B is centered by its own mean, so a global shift cancels out. If B were
    centered with A's mean (the forbidden behavior), the result would change.
    """
    A = make_matrix(n_rows=200, seed=5)
    B = make_matrix(n_rows=200, seed=6)
    B_shifted = B.copy()
    B_shifted[feature_names] = B_shifted[feature_names] + 7.0

    r1 = compute_jcvpca(A, B, feature_names, selected_m=len(feature_names))
    r2 = compute_jcvpca(A, B_shifted, feature_names, selected_m=len(feature_names))
    np.testing.assert_allclose(r1["jcvpca_axis"], r2["jcvpca_axis"], atol=1e-9)


def test_not_using_pca_a_transform_b_raw(feature_names):
    """PCA_A.transform(B_raw) applies A's mean to B; our projection must differ
    whenever A and B means differ."""
    A = make_matrix(n_rows=200, seed=7)
    B = make_matrix(n_rows=200, seed=8)
    B[feature_names] = B[feature_names] + 3.0  # ensure different means
    selected_m = len(feature_names)

    A_centered = A[feature_names] - A[feature_names].mean()
    pca_A = PCA(n_components=selected_m).fit(A_centered)

    forbidden_scores = pca_A.transform(B[feature_names].to_numpy())
    B_centered = B[feature_names] - B[feature_names].mean()
    manual_scores = np.matmul(B_centered.to_numpy(), pca_A.components_.transpose())

    assert not np.allclose(forbidden_scores, manual_scores, atol=1e-6)


def test_selected_m_from_A_only(feature_names):
    """selected_m must depend only on A; changing B must not change it."""
    A = make_matrix(n_rows=400, seed=9)
    B1 = make_matrix(n_rows=400, seed=10)
    B2 = make_matrix(n_rows=400, seed=99, scale=50.0)

    m_from_helper, _ = select_selected_m_from_A(A, feature_names, 0.90)
    r1 = compute_jcvpca(A, B1, feature_names, variance_threshold=0.90)
    r2 = compute_jcvpca(A, B2, feature_names, variance_threshold=0.90)

    assert r1["selected_m"] == m_from_helper
    assert r2["selected_m"] == m_from_helper


def test_natural_variability_uses_same_function(feature_names):
    """NV is just compute_jcvpca applied to R1 vs R2."""
    R1 = make_matrix(n_rows=200, seed=13, session_id="671_T1_P1_R1")
    R2 = make_matrix(n_rows=200, seed=14, session_id="671_T1_P1_R2")
    result = compute_jcvpca(R1, R2, feature_names, selected_m=len(feature_names))
    assert result["jcvpca_axis"].shape == (len(feature_names), len(feature_names))
