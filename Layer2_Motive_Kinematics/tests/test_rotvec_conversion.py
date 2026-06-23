"""Tests for Stage 07 rotation-vector log-map conversion and diagnostics."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy.spatial.transform import Rotation

from layer2_motive.parsing import parse_motive_header
from layer2_motive.rotvec import (
    DiagnosticStatus,
    RotVecThresholds,
    compute_link_rotvec_diagnostics,
    convert_relative_quaternions_table,
    evaluate_branch_cut_status,
    evaluate_jump_status,
    frame_to_frame_rotvec_jumps,
    process_file_rotvecs,
    quat_to_rotvec,
    thresholds_from_config,
)
from layer2_motive.stages.stage01 import run_stage_01
from layer2_motive.stages.stage03 import run_stage_03
from layer2_motive.stages.stage04 import run_stage_04
from layer2_motive.stages.stage05 import run_stage_05
from layer2_motive.stages.stage06 import run_stage_06
from layer2_motive.stages.stage07 import run_stage_07
from layer2_motive.validation import HardStopError

FIXTURES = Path(__file__).parent / "fixtures"
VALID = FIXTURES / "timing_valid_monotonic.csv"

DEFAULT_THRESHOLDS = RotVecThresholds(
    near_pi_threshold_rad=float(np.pi - 0.10),
    near_pi_warning_fraction=0.95,
    branch_cut_fail_tol_rad=1.0e-6,
    jump_warning_rad=0.5,
    jump_fail_rad=1.0,
)


def _identity_quat_table(frames: int = 5) -> pd.DataFrame:
    rows = []
    for frame in range(frames):
        rows.append(
            {
                "frame": frame,
                "time": frame * 0.008333,
                "joint_id": "J001",
                "source_parent_bone": "900:Parent",
                "source_child_bone": "900:Child",
                "parent_bone": "Parent",
                "child_bone": "Child",
                "is_root_anchor_link": False,
                "included_in_v0": True,
                "selection_status": "provisional_v0",
                "requires_manual_review": False,
                "qx": 0.0,
                "qy": 0.0,
                "qz": 0.0,
                "qw": 1.0,
                "relative_flip_applied": False,
            }
        )
    return pd.DataFrame(rows)


def test_identity_quaternion_converts_to_zero_rotvec() -> None:
    rx, ry, rz = quat_to_rotvec(0.0, 0.0, 0.0, 1.0)
    assert np.allclose([rx, ry, rz], [0.0, 0.0, 0.0], atol=1e-12)


def test_known_rotation_converts_to_expected_axis_angle_vector() -> None:
    angle_rad = np.deg2rad(90.0)
    quat = Rotation.from_rotvec([0.0, 0.0, angle_rad]).as_quat()
    rx, ry, rz = quat_to_rotvec(*quat)
    assert np.allclose([rx, ry, rz], [0.0, 0.0, angle_rad], atol=1e-10)


def test_near_pi_rotation_flagged_as_branch_cut_warning() -> None:
    angle = 0.96 * np.pi
    status = evaluate_branch_cut_status(angle, DEFAULT_THRESHOLDS)
    assert status == DiagnosticStatus.WARNING


def test_at_pi_branch_cut_fails() -> None:
    angle = np.pi - 1.0e-7
    status = evaluate_branch_cut_status(angle, DEFAULT_THRESHOLDS)
    assert status == DiagnosticStatus.FAIL


def test_artificial_jump_sequence_flagged() -> None:
    frames = 4
    rotvecs = np.zeros((frames, 3))
    rotvecs[2] = [0.8, 0.0, 0.0]
    jumps = frame_to_frame_rotvec_jumps(rotvecs)
    assert float(np.max(jumps)) > DEFAULT_THRESHOLDS.jump_warning_rad
    status = evaluate_jump_status(float(np.max(jumps)), DEFAULT_THRESHOLDS)
    assert status == DiagnosticStatus.WARNING


def test_core_vs_excluded_summary_separation() -> None:
    near_pi_quat = Rotation.from_rotvec([0.0, 0.0, 0.96 * np.pi]).as_quat()

    core_table = _identity_quat_table(frames=3)
    core_table["joint_id"] = "J_CORE"
    core_table["parent_bone"] = "671"
    core_table["child_bone"] = "LThigh"

    excluded_table = _identity_quat_table(frames=3)
    for idx in excluded_table.index:
        excluded_table.loc[idx, ["qx", "qy", "qz", "qw"]] = near_pi_quat
    excluded_table["joint_id"] = "J_EXCL"
    excluded_table["parent_bone"] = "LHand"
    excluded_table["child_bone"] = "LIndex1"

    combined = pd.concat([core_table, excluded_table], ignore_index=True)
    candidate = pd.DataFrame(
        [
            {
                "joint_id": "J_CORE",
                "parent_bone": "671",
                "child_bone": "LThigh",
                "exclusion_reason": "",
            },
            {
                "joint_id": "J_EXCL",
                "parent_bone": "LHand",
                "child_bone": "LIndex1",
                "exclusion_reason": "distal_keyword",
            },
        ]
    )

    result, _ = process_file_rotvecs(
        input_file="test.csv",
        relative_quats=combined,
        candidate_joints=candidate,
        thresholds=DEFAULT_THRESHOLDS,
    )

    assert result.core_links_processed == 1
    assert result.excluded_links_processed == 1
    assert result.core_failures == 0
    assert result.excluded_warnings >= 1 or result.excluded_failures >= 1


def test_stage07_refuses_missing_stage06(tmp_path: Path) -> None:
    out_dir = tmp_path / "run"
    out_dir.mkdir()
    with pytest.raises(HardStopError, match="Stage 06 outputs missing"):
        run_stage_07(VALID, out_dir)


def test_stage07_refuses_failed_stage06(tmp_path: Path) -> None:
    out_dir = tmp_path / "run"
    stage06 = out_dir / "06_relative_quaternions"
    stage06.mkdir(parents=True)
    pd.DataFrame(
        [{"stage07_may_proceed": False, "parent_child_links_processed": 0}]
    ).to_csv(stage06 / "relative_quaternion_summary.csv", index=False)
    with pytest.raises(HardStopError, match="Stage 06 relative quaternion validation did not pass"):
        run_stage_07(VALID, out_dir)


def test_stage07_report_and_outputs(tmp_path: Path) -> None:
    out_dir = tmp_path / "run"
    parsed = parse_motive_header(VALID)
    run_stage_01(VALID, out_dir)
    run_stage_03(VALID, out_dir, parsed=parsed)
    run_stage_04(VALID, out_dir, parsed=parsed)
    run_stage_05(VALID, out_dir, parsed=parsed)
    run_stage_06(VALID, out_dir)
    run_stage_07(VALID, out_dir)

    stage_dir = out_dir / "07_rotation_vectors"
    assert (stage_dir / "report.md").exists()
    assert (stage_dir / "relative_rotation_vectors.parquet").exists()
    assert (stage_dir / "relative_rotation_vectors.csv").exists()
    assert (stage_dir / "rotvec_summary_by_link.csv").exists()
    assert (stage_dir / "branch_cut_report.csv").exists()
    assert (stage_dir / "rotvec_jump_report.csv").exists()
    assert (stage_dir / "assumptions_and_limitations.md").exists()

    report = (stage_dir / "report.md").read_text(encoding="utf-8")
    assert "log-map" in report.lower() or "rotation-vector" in report.lower()
    assert "does not filter" in report


def test_batch_index_fields(tmp_path: Path) -> None:
    from layer2_motive.batch import summarize_stage07_output, write_stage07_index

    out_dir = tmp_path / "run"
    parsed = parse_motive_header(VALID)
    run_stage_01(VALID, out_dir)
    run_stage_03(VALID, out_dir, parsed=parsed)
    run_stage_04(VALID, out_dir, parsed=parsed)
    run_stage_05(VALID, out_dir, parsed=parsed)
    run_stage_06(VALID, out_dir)
    run_stage_07(VALID, out_dir)

    row = summarize_stage07_output(VALID, out_dir)
    required = {
        "links_processed",
        "core_links_processed",
        "review_links_processed",
        "excluded_links_processed",
        "max_rotvec_norm_core",
        "max_rotvec_norm_all",
        "max_jump_core",
        "max_jump_all",
        "core_warnings",
        "core_failures",
        "stage08_may_proceed",
    }
    assert required.issubset(row.keys())

    index_path = tmp_path / "stage07_index"
    write_stage07_index([row], index_path)
    assert index_path.with_suffix(".csv").exists()
    assert index_path.with_suffix(".md").exists()


def test_config_thresholds_loaded() -> None:
    thresholds = thresholds_from_config({"rotvec": {}})
    assert thresholds.jump_warning_rad == 0.5
    assert thresholds.jump_fail_rad == 1.0


def test_compute_link_diagnostics_near_pi_count() -> None:
    table = _identity_quat_table(frames=10)
    angle = DEFAULT_THRESHOLDS.near_pi_threshold_rad + 0.01
    rotvec = Rotation.from_rotvec([0.0, 0.0, angle]).as_quat()
    for idx in [2, 5]:
        table.loc[idx, ["qx", "qy", "qz", "qw"]] = rotvec
    converted = convert_relative_quaternions_table(table, input_file="test.csv")
    diag = compute_link_rotvec_diagnostics(
        joint_id="J001",
        group=converted,
        thresholds=DEFAULT_THRESHOLDS,
    )
    assert diag.near_pi_count == 2
    assert diag.near_pi_percent == pytest.approx(20.0)
