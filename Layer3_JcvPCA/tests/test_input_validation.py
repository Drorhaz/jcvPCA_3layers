"""Validation-gate tests."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from layer3_jcvpca.io import infer_feature_columns, load_analysis_manifest
from layer3_jcvpca.validation import (
    ValidationError,
    validate_jcvpca_matrix,
    validate_manifest_roles,
    validate_selected_m,
)

from conftest import METADATA_COLS, make_matrix


def test_valid_matrix_passes(metadata_cols):
    df = make_matrix(n_rows=100, seed=1)
    report = validate_jcvpca_matrix(df, metadata_cols)
    assert report["status"] == "passed"
    assert report["n_features"] == 6


def test_nan_fails(metadata_cols):
    df = make_matrix(n_rows=100, seed=1)
    feats = infer_feature_columns(df)
    df.loc[3, feats[0]] = np.nan
    with pytest.raises(ValidationError) as exc:
        validate_jcvpca_matrix(df, metadata_cols)
    assert exc.value.report["nan_count"] >= 1


def test_inf_fails(metadata_cols):
    df = make_matrix(n_rows=100, seed=1)
    feats = infer_feature_columns(df)
    df.loc[5, feats[1]] = np.inf
    with pytest.raises(ValidationError):
        validate_jcvpca_matrix(df, metadata_cols)


def test_constant_column_fails(metadata_cols):
    df = make_matrix(n_rows=100, seed=1)
    feats = infer_feature_columns(df)
    df[feats[2]] = 0.5
    with pytest.raises(ValidationError) as exc:
        validate_jcvpca_matrix(df, metadata_cols)
    assert feats[2] in exc.value.report["constant_columns"]


def test_missing_metadata_fails(metadata_cols):
    df = make_matrix(n_rows=100, seed=1).drop(columns=["run_label"])
    with pytest.raises(ValidationError) as exc:
        validate_jcvpca_matrix(df, metadata_cols)
    assert "run_label" in exc.value.report["missing_metadata_columns"]


def test_metadata_excluded_from_features(metadata_cols):
    df = make_matrix(n_rows=100, seed=1)
    feats = infer_feature_columns(df)
    for meta in METADATA_COLS:
        assert meta not in feats


def test_too_few_rows_fails(metadata_cols):
    df = make_matrix(n_rows=4, seed=1)
    with pytest.raises(ValidationError):
        validate_jcvpca_matrix(df, metadata_cols, min_rows_for_pca=10)


def test_selected_m_validation_against_A_and_B():
    # selected_m must not exceed B rows (B projected into A space).
    with pytest.raises(ValidationError):
        validate_selected_m(selected_m=50, n_features_A=6, n_rows_A=200, n_rows_B=20)
    # selected_m must not exceed feature count.
    with pytest.raises(ValidationError):
        validate_selected_m(selected_m=7, n_features_A=6, n_rows_A=200, n_rows_B=200)
    # valid case
    validate_selected_m(selected_m=3, n_features_A=6, n_rows_A=200, n_rows_B=200)


def _manifest_df(rows):
    cols = [
        "subject_id", "timepoint", "part_id", "repetition_id",
        "group_id", "matrix_path", "include_in_analysis", "analysis_role",
    ]
    return pd.DataFrame(rows, columns=cols)


def test_manifest_missing_role_fails(tmp_path):
    f = tmp_path / "m.parquet"
    f.write_text("x")
    required = ["A_T1_R1", "A_T1_R2"]
    df = _manifest_df([
        ["671", "T1", "P1", "R1", "Group4", str(f), True, "A_T1_R1"],
    ])
    with pytest.raises(ValidationError) as exc:
        validate_manifest_roles(df, required)
    assert "A_T1_R2" in exc.value.report["missing_roles"]


def test_manifest_duplicate_role_fails(tmp_path):
    f = tmp_path / "m.parquet"
    f.write_text("x")
    required = ["A_T1_R1"]
    df = _manifest_df([
        ["671", "T1", "P1", "R1", "Group4", str(f), True, "A_T1_R1"],
        ["671", "T1", "P1", "R1", "Group4", str(f), True, "A_T1_R1"],
    ])
    with pytest.raises(ValidationError) as exc:
        validate_manifest_roles(df, required)
    assert "A_T1_R1" in exc.value.report["duplicate_roles"]


def test_manifest_missing_file_fails(tmp_path):
    required = ["A_T1_R1"]
    df = _manifest_df([
        ["671", "T1", "P1", "R1", "Group4", str(tmp_path / "nope.parquet"), True, "A_T1_R1"],
    ])
    with pytest.raises(ValidationError) as exc:
        validate_manifest_roles(df, required)
    assert exc.value.report["missing_files"]
