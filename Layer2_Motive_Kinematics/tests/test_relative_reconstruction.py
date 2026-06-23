"""Tests for Stage 06 relative quaternion computation and reconstruction validation."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.spatial.transform import Rotation

from layer2_motive.parsing import parse_motive_header
from layer2_motive.relative_rotation import (
    ReconstructionThresholds,
    angular_error_degrees,
    compute_relative_quaternions,
    compute_relative_quaternions_wrong_order,
    process_file_relative_rotations,
    reconstruct_child_global,
    validate_link_reconstruction,
)
from layer2_motive.stages.stage01 import run_stage_01
from layer2_motive.stages.stage04 import run_stage_04
from layer2_motive.stages.stage05 import run_stage_05
from layer2_motive.stages.stage06 import run_stage_06
from layer2_motive.validation import HardStopError

FIXTURES = Path(__file__).parent / "fixtures"
VALID = FIXTURES / "timing_valid_monotonic.csv"


def test_identity_parent_child_gives_identity_relative() -> None:
    identity = np.tile(np.array([0.0, 0.0, 0.0, 1.0]), (3, 1))
    relative = compute_relative_quaternions(identity, identity)
    assert np.allclose(relative, identity, atol=1e-12)


def test_known_rotations_reconstruct_correctly() -> None:
    parent = Rotation.from_euler("xyz", [10, 20, 30], degrees=True).as_quat()
    child = Rotation.from_euler("xyz", [15, 25, 40], degrees=True).as_quat()
    parent_rows = np.tile(parent, (5, 1))
    child_rows = np.tile(child, (5, 1))

    relative = compute_relative_quaternions(parent_rows, child_rows)
    reconstructed = reconstruct_child_global(parent_rows, relative)
    errors = angular_error_degrees(child_rows, reconstructed)
    assert float(np.max(errors)) <= 1e-10


def test_wrong_multiplication_order_shows_large_reconstruction_error() -> None:
    parent = Rotation.from_euler("x", 45, degrees=True).as_quat()
    child = Rotation.from_euler("y", 30, degrees=True).as_quat()
    parent_rows = np.tile(parent, (4, 1))
    child_rows = np.tile(child, (4, 1))

    wrong_relative = compute_relative_quaternions_wrong_order(parent_rows, child_rows)
    reconstructed = reconstruct_child_global(parent_rows, wrong_relative)
    errors = angular_error_degrees(child_rows, reconstructed)
    assert float(np.max(errors)) > 1.0


def test_missing_parent_child_link_reported_not_ignored() -> None:
    global_quats = pd.DataFrame(
        {
            "frame": [0, 1],
            "time": [0.0, 0.008333],
            "source_bone_name": ["900:Child", "900:Child"],
            "canonical_bone_name": ["Child", "Child"],
            "qx": [0.0, 0.0],
            "qy": [0.0, 0.0],
            "qz": [0.0, 0.0],
            "qw": [1.0, 1.0],
            "flip_applied": [False, False],
        }
    )
    candidate = pd.DataFrame(
        [
            {
                "joint_id": "J001",
                "source_parent_bone": "900:MissingParent",
                "source_child_bone": "900:Child",
                "parent_bone": "MissingParent",
                "child_bone": "Child",
                "included": True,
                "exclusion_reason": "",
                "selection_rule": "default_include",
                "requires_manual_review": False,
            }
        ]
    )
    selected = candidate.copy()
    selected["selection_status"] = "provisional_v0"
    selected["frozen"] = False
    selected["included_in_v0"] = True

    result, _ = process_file_relative_rotations(
        input_file="test.csv",
        global_quats=global_quats,
        candidate_joints=candidate,
        selected_joints=selected,
        reconstruction_thresholds=ReconstructionThresholds(),
        sign_thresholds=__import__(
            "layer2_motive.quaternion_continuity", fromlist=["SignContinuityThresholds"]
        ).SignContinuityThresholds(),
    )
    assert result.parent_child_links_processed == 0
    assert result.parent_child_links_missing == 1
    assert "parent quaternion missing" in result.missing_links[0]["missing_reason"]


def test_reconstruction_validation_report_output(tmp_path: Path) -> None:
    parent = np.tile(Rotation.from_euler("z", 10, degrees=True).as_quat(), (6, 1))
    child = np.tile(Rotation.from_euler("z", 25, degrees=True).as_quat(), (6, 1))
    thresholds = ReconstructionThresholds()
    result, _ = validate_link_reconstruction(
        joint_id="J001",
        source_parent_bone="P",
        source_child_bone="C",
        parent_bone="P",
        child_bone="C",
        is_root_anchor_link=False,
        included_in_v0=True,
        selection_status="provisional_v0",
        requires_manual_review=False,
        parent_quats=parent,
        child_quats=child,
        thresholds=thresholds,
    )
    assert result.reconstruction_status.value == "pass"
    assert result.max_error_deg <= thresholds.pass_max_error_deg


def _write_stage05_pass_summary(output_dir: Path, *, may_proceed: bool = True) -> None:
    stage05_dir = output_dir / "05_sign_continuity"
    stage05_dir.mkdir(parents=True)
    pd.DataFrame(
        [
            {
                "input_file": "x.csv",
                "quaternion_group_count": 1,
                "total_frames": 10,
                "total_sign_flips": 0,
                "max_sign_flips_any_bone": 0,
                "bones_with_zero_flips": 1,
                "min_consecutive_dot_observed": 1.0,
                "post_correction_valid": may_proceed,
                "stage06_may_proceed": may_proceed,
                "fail_reasons": "",
                "warning_reasons": "",
            }
        ]
    ).to_csv(stage05_dir / "sign_continuity_summary.csv", index=False)


def test_stage06_refuses_without_stage05_pass(tmp_path: Path) -> None:
    with pytest.raises(HardStopError, match="Stage 05"):
        run_stage_06(VALID, tmp_path)


def test_stage06_refuses_when_stage05_failed(tmp_path: Path) -> None:
    _write_stage05_pass_summary(tmp_path, may_proceed=False)
    with pytest.raises(HardStopError, match="Stage 05 sign-continuity did not pass"):
        run_stage_06(VALID, tmp_path)


def test_stage06_report_outputs(tmp_path: Path) -> None:
    parsed = parse_motive_header(VALID)
    run_stage_01(VALID, tmp_path, parsed=parsed)
    run_stage_04(VALID, tmp_path, parsed=parsed)
    run_stage_05(VALID, tmp_path, parsed=parsed)
    run_stage_06(VALID, tmp_path)

    stage_dir = tmp_path / "06_relative_quaternions"
    assert (stage_dir / "report.md").exists()
    assert (stage_dir / "relative_quaternions.parquet").exists()
    assert (stage_dir / "relative_quaternions.csv").exists()
    assert (stage_dir / "relative_quaternion_summary.csv").exists()
    assert (stage_dir / "reconstruction_validation_by_joint.csv").exists()
    assert (stage_dir / "relative_sign_continuity_report.csv").exists()
    assert (stage_dir / "assumptions_and_limitations.md").exists()

    report = (stage_dir / "report.md").read_text(encoding="utf-8")
    assert "Stage 06 does not convert to rotation vectors" in report
    assert "Stage 06 does not finalize analysis features" in report

    summary = pd.read_csv(stage_dir / "relative_quaternion_summary.csv")
    assert str(summary.iloc[0]["stage07_may_proceed"]).lower() == "true"
