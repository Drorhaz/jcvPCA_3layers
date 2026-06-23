"""Matrix Stability / PCA Readiness tests."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from layer3_jcvpca.matrix_stability import (
    MatrixStabilityParams,
    assess_matrix_stability,
    combined_stability_status,
)
from conftest import FEATURE_NAMES, make_matrix


def test_complete_numeric_matrix_passes():
    df = make_matrix(n_rows=200, seed=1)
    result = assess_matrix_stability(df, "A", is_reference=True)
    assert result.status in ("pass", "warning")
    assert result.metrics["nan_count"] == 0
    assert result.metrics["matrix_rank"] > 0


def test_nan_fails_blocking():
    df = make_matrix(n_rows=200, seed=1)
    df.loc[0, FEATURE_NAMES[0]] = np.nan
    result = assess_matrix_stability(df, "A")
    assert result.status == "blocking"


def test_inf_fails_blocking():
    df = make_matrix(n_rows=200, seed=1)
    df.loc[0, FEATURE_NAMES[0]] = np.inf
    result = assess_matrix_stability(df, "A")
    assert result.status == "blocking"


def test_zero_total_variance_blocking():
    df = make_matrix(n_rows=200, seed=1)
    for c in FEATURE_NAMES:
        df[c] = 0.0
    result = assess_matrix_stability(df, "A")
    assert result.status == "blocking"


def test_too_few_frames_blocking():
    df = make_matrix(n_rows=5, seed=1)
    params = MatrixStabilityParams(min_frames_required=10)
    result = assess_matrix_stability(df, "A", params=params)
    assert result.status == "blocking"


def test_near_zero_variance_warning():
    df = make_matrix(n_rows=200, seed=1)
    df[FEATURE_NAMES[0]] = 1e-12
    params = MatrixStabilityParams(near_zero_variance_threshold=1e-8)
    result = assess_matrix_stability(df, "A", params=params)
    assert result.status == "warning"
    assert result.metrics["near_zero_variance_feature_count"] >= 1


def test_dominant_pc_warning():
    df = make_matrix(n_rows=200, seed=1)
    # Make one feature dominate
    df[FEATURE_NAMES[0]] = df[FEATURE_NAMES[0]] * 100
    params = MatrixStabilityParams(pc_dominance_warning_threshold=0.50)
    result = assess_matrix_stability(df, "A", params=params)
    assert result.status == "warning"


def test_combined_status_blocking():
    from layer3_jcvpca.matrix_stability import MatrixStabilityResult

    r1 = MatrixStabilityResult(role="A", status="pass")
    r2 = MatrixStabilityResult(role="B", status="blocking")
    assert combined_stability_status({"A": r1, "B": r2}) == "blocking"


def test_split_half_skipped_when_few_frames():
    df = make_matrix(n_rows=15, seed=1)
    params = MatrixStabilityParams(min_frames_required=10, split_half_stability_check=True)
    result = assess_matrix_stability(df, "A", params=params)
    assert result.metrics.get("split_half_available") is False
