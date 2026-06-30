"""Tests for workbench PCA stability / readiness (Phase 7 correction)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from layer3_jcvpca.jcvpca_trace import PcaAParameters, fit_pca_on_centered_a
from layer3_jcvpca.matrix_stability import MatrixStabilityParams
from layer3_jcvpca.workbench_pca_stability import (
    assess_workbench_centered_stability,
    assess_workbench_pca_stability_pair,
    build_stability_report_rows,
)


def _synthetic_centered(n_rows: int = 100, n_features: int = 10, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    cols = [f"Link{i}_to_Head_{ax}" for i in range(n_features // 3 + 1) for ax in ("rx", "ry", "rz")][
        :n_features
    ]
    data = rng.normal(size=(n_rows, len(cols)))
    data -= data.mean(axis=0)
    return pd.DataFrame(data, columns=cols)


def test_centered_a_stability_metrics_present() -> None:
    centered = _synthetic_centered()
    cols = list(centered.columns)
    result = assess_workbench_centered_stability(centered, cols, "A", is_reference=True)
    assert result.metrics["n_rows"] == 100
    assert result.metrics["n_features"] == 10
    assert result.metrics["rows_to_features_ratio"] == pytest.approx(10.0)
    assert result.metrics["pca_fit_success"] is True
    assert result.metrics["matrix_rank"] > 0
    assert "rank_deficiency" in result.metrics
    assert not result.singular_values.empty


def test_b_stability_diagnostic_only_no_selected_m() -> None:
    centered = _synthetic_centered()
    cols = list(centered.columns)
    result = assess_workbench_centered_stability(centered, cols, "B", is_reference=False)
    assert "selected_m" not in result.metrics
    assert result.metrics["is_reference"] is False


def test_nan_values_block_stability() -> None:
    centered = _synthetic_centered()
    cols = list(centered.columns)
    centered.iloc[0, 0] = np.nan
    result = assess_workbench_centered_stability(centered, cols, "A", is_reference=True)
    assert result.status == "blocking"
    assert any(f["code"] == "nan_in_features" for f in result.findings)


def test_a_reference_includes_selected_m_from_trace() -> None:
    centered = _synthetic_centered(n_rows=200, n_features=15)
    cols = list(centered.columns)
    trace = fit_pca_on_centered_a(centered, cols, PcaAParameters())
    result = assess_workbench_centered_stability(
        centered,
        cols,
        "A",
        is_reference=True,
        pca_trace=trace,
    )
    assert result.metrics["selected_m"] == trace.selected_m
    assert result.metrics["selected_m_reason"] == trace.selected_m_reason


def test_stability_report_rows_include_findings() -> None:
    centered = _synthetic_centered()
    cols = list(centered.columns)
    params = MatrixStabilityParams(min_frames_per_feature_ratio=1000.0)
    result = assess_workbench_centered_stability(centered, cols, "A", params=params, is_reference=True)
    report = build_stability_report_rows(result)
    assert not report.empty
    assert (report["severity"] == "warning").any()


def test_pair_assessment_combined_status() -> None:
    a = _synthetic_centered(seed=1)
    b = _synthetic_centered(n_rows=80, seed=2)
    cols = list(a.columns)
    trace = fit_pca_on_centered_a(a, cols, PcaAParameters())
    bundle = assess_workbench_pca_stability_pair(a, b, cols, trace)
    assert bundle.a.role == "A"
    assert bundle.b.role == "B"
    assert bundle.combined_status in {"pass", "warning", "blocking"}
