"""Tests for Stage 02 quaternion component-order / SciPy compatibility."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from layer2_motive.quaternions import (
    construct_identity_rotation,
    evaluate_component_order,
    motive_labels_compatible_with_scipy,
    validate_bone_rotation_group,
)
from layer2_motive.stages.stage02 import run_stage_02

FIXTURE = Path(__file__).parent / "fixtures" / "minimal_motive_header.csv"


def test_scipy_identity_quaternion_constructible() -> None:
    rotation = construct_identity_rotation()
    quat = rotation.as_quat()
    np.testing.assert_allclose(quat, [0.0, 0.0, 0.0, 1.0], atol=1e-12)


def test_motive_labels_compatible_with_scipy_order() -> None:
    assert motive_labels_compatible_with_scipy() is True


def test_validate_bone_rotation_group_on_identity_rows() -> None:
    n = 5
    x = pd.Series([0.0] * n)
    y = pd.Series([0.0] * n)
    z = pd.Series([0.0] * n)
    w = pd.Series([1.0] * n)
    result = validate_bone_rotation_group(x, y, z, w)
    assert result["constructability_status"] == "pass"
    assert result["sample_size"] == n
    assert result["constructible_count"] == n
    assert result["selected_scipy_order"] == "x,y,z,w"
    assert result["labels_compatible_with_scipy"] is True


def test_missing_component_columns_reported() -> None:
    groups = {
        "900:900": {"X": 2, "Y": 3, "Z": 4},
        "900:Ab": {"X": 8, "Y": 9, "Z": 10, "W": 11},
    }
    x = pd.Series([0.0, 1.0])
    y = pd.Series([0.0, 0.0])
    z = pd.Series([0.0, 0.0])
    w = pd.Series([np.nan, 1.0])
    result = validate_bone_rotation_group(x, y, z, w)
    assert result["non_finite_row_count"] == 1
    assert result["sample_size"] == 1
    assert "W" not in result["missing_components"]

    incomplete = [bone for bone, comps in groups.items() if "W" not in comps]
    assert incomplete == ["900:900"]


def test_zero_norm_quaternion_reported_as_construction_error() -> None:
    x = pd.Series([0.0])
    y = pd.Series([0.0])
    z = pd.Series([0.0])
    w = pd.Series([0.0])
    result = validate_bone_rotation_group(x, y, z, w)
    assert result["constructability_status"] == "fail"
    assert result["construction_error_count"] == 1
    assert result["first_construction_error"] is not None


def test_alternative_order_comparison_does_not_override_primary() -> None:
    x = pd.Series([0.0, 0.1])
    y = pd.Series([0.0, 0.0])
    z = pd.Series([0.0, 0.0])
    w = pd.Series([1.0, 0.995])
    primary = evaluate_component_order(
        x, y, z, w, order_label="primary", scipy_order=(0, 1, 2, 3)
    )
    alternative = evaluate_component_order(
        x, y, z, w, order_label="alt", scipy_order=(3, 0, 1, 2)
    )
    assert primary.constructible
    assert alternative.constructible
    assert primary.order_label == "primary"


def test_stage02_report_generation_on_minimal_fixture(tmp_path: Path) -> None:
    output_dir = tmp_path / "run"
    result = run_stage_02(FIXTURE, output_dir)
    stage_dir = output_dir / "02_component_order"

    assert (stage_dir / "report.md").exists()
    assert (stage_dir / "component_order_summary.csv").exists()
    assert (stage_dir / "component_order_by_bone.csv").exists()
    assert (stage_dir / "assumptions_and_limitations.md").exists()

    summary = result["summary"]
    by_bone = result["by_bone"]
    assert not summary.empty
    assert not by_bone.empty
    complete = by_bone[by_bone["has_complete_xyzw_columns"]]
    assert not complete.empty
    assert (complete["constructability_status"] == "pass").all()

    report_text = (stage_dir / "report.md").read_text(encoding="utf-8")
    assert "Stage 02" in report_text
    assert "x,y,z,w" in report_text or "x, y, z, w" in report_text

    assumptions_text = (stage_dir / "assumptions_and_limitations.md").read_text(encoding="utf-8")
    assert "component-order / library-compatibility" in assumptions_text
    assert "does not validate quaternion norms" in assumptions_text
