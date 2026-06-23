"""Tests for compact QC propagation schema (Stage 07 signal + manifests)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial.transform import Rotation

from layer2_motive.parsing import parse_motive_header
from layer2_motive.qc_propagation import (
    COMPACT_SIGNAL_COLUMNS,
    HEAVY_SIGNAL_COLUMNS,
    LINK_MANIFEST_COLUMNS,
    SESSION_MANIFEST_COLUMNS,
    build_compact_signal_table,
    build_link_qc_record,
    compute_stage08_policy,
    feature_scope_from_classification,
)
from layer2_motive.rotvec import (
    DiagnosticStatus,
    LinkRotVecDiagnostics,
    RotVecThresholds,
    compute_link_rotvec_diagnostics,
    convert_relative_quaternions_table,
)
from layer2_motive.stages.stage01 import run_stage_01
from layer2_motive.stages.stage03 import run_stage_03
from layer2_motive.stages.stage04 import run_stage_04
from layer2_motive.stages.stage05 import run_stage_05
from layer2_motive.stages.stage06 import run_stage_06
from layer2_motive.stages.stage07 import run_stage_07

FIXTURES = Path(__file__).parent / "fixtures"
VALID = FIXTURES / "timing_valid_monotonic.csv"

DEFAULT_THRESHOLDS = RotVecThresholds(
    near_pi_threshold_rad=float(np.pi - 0.10),
    near_pi_warning_fraction=0.95,
    branch_cut_fail_tol_rad=1.0e-6,
    jump_warning_rad=0.5,
    jump_fail_rad=1.0,
)


def _make_link_diag(**overrides: object) -> LinkRotVecDiagnostics:
    base = dict(
        joint_id="J001",
        parent_bone="LFArm",
        child_bone="LHand",
        source_parent_bone="671:LFArm",
        source_child_bone="671:LHand",
        included_in_v0=True,
        selection_status="provisional_v0",
        requires_manual_review=False,
        link_classification="hand",
        core_candidate=True,
        excluded_candidate=False,
        link_group="core_candidate",
        total_frames=3,
        finite_rotvec_rows=3,
        non_finite_rotvec_rows=0,
        min_rotvec_norm=0.0,
        mean_rotvec_norm=0.1,
        median_rotvec_norm=0.1,
        max_rotvec_norm=0.2,
        p95_rotvec_norm=0.2,
        p99_rotvec_norm=0.2,
        near_pi_count=0,
        near_pi_percent=0.0,
        max_frame_to_frame_jump=1.5,
        p95_frame_to_frame_jump=1.5,
        p99_frame_to_frame_jump=1.5,
        large_jump_count=1,
        large_jump_percent=50.0,
        first_large_jump_frame=2,
        branch_cut_status=DiagnosticStatus.PASS,
        jump_status=DiagnosticStatus.FAIL,
        stage08_may_proceed_for_link=False,
    )
    base.update(overrides)
    return LinkRotVecDiagnostics(**base)


def test_main_parquet_schema_has_compact_qc_columns(tmp_path: Path) -> None:
    out_dir = tmp_path / "run"
    parsed = parse_motive_header(VALID)
    run_stage_01(VALID, out_dir)
    run_stage_03(VALID, out_dir, parsed=parsed)
    run_stage_04(VALID, out_dir, parsed=parsed)
    run_stage_05(VALID, out_dir, parsed=parsed)
    run_stage_06(VALID, out_dir)
    run_stage_07(VALID, out_dir)

    df = pd.read_parquet(out_dir / "07_rotation_vectors" / "relative_rotation_vectors.parquet")
    assert list(df.columns) == list(COMPACT_SIGNAL_COLUMNS)
    for col in COMPACT_SIGNAL_COLUMNS:
        assert col in df.columns


def test_main_parquet_excludes_heavy_diagnostic_columns(tmp_path: Path) -> None:
    out_dir = tmp_path / "run"
    parsed = parse_motive_header(VALID)
    run_stage_01(VALID, out_dir)
    run_stage_03(VALID, out_dir, parsed=parsed)
    run_stage_04(VALID, out_dir, parsed=parsed)
    run_stage_05(VALID, out_dir, parsed=parsed)
    run_stage_06(VALID, out_dir)
    run_stage_07(VALID, out_dir)

    df = pd.read_parquet(out_dir / "07_rotation_vectors" / "relative_rotation_vectors.parquet")
    assert HEAVY_SIGNAL_COLUMNS.isdisjoint(set(df.columns))


def test_jump_fail_frame_gets_row_fail_status() -> None:
    frames = 4
    quats = np.tile(np.array([0.0, 0.0, 0.0, 1.0]), (frames, 1))
    quats[2] = Rotation.from_rotvec([1.2, 0.0, 0.0]).as_quat()
    table = pd.DataFrame(
        {
            "frame": list(range(frames)),
            "time": [i * 0.008333 for i in range(frames)],
            "joint_id": ["J001"] * frames,
            "source_parent_bone": ["671:LFArm"] * frames,
            "source_child_bone": ["671:LHand"] * frames,
            "parent_bone": ["LFArm"] * frames,
            "child_bone": ["LHand"] * frames,
            "is_root_anchor_link": [False] * frames,
            "included_in_v0": [True] * frames,
            "selection_status": ["provisional_v0"] * frames,
            "requires_manual_review": [False] * frames,
            "qx": quats[:, 0],
            "qy": quats[:, 1],
            "qz": quats[:, 2],
            "qw": quats[:, 3],
            "relative_flip_applied": [False] * frames,
        }
    )
    rotvec_table = convert_relative_quaternions_table(table, input_file="test.csv")
    diag = compute_link_rotvec_diagnostics(
        joint_id="J001",
        group=rotvec_table,
        thresholds=DEFAULT_THRESHOLDS,
    )
    record = build_link_qc_record(
        link_diag=diag,
        context=_minimal_context(),
        candidate_row=None,
    )
    compact = build_compact_signal_table(
        rotvec_table=rotvec_table,
        link_records={"J001": record},
        link_diagnostics=[diag],
        thresholds=DEFAULT_THRESHOLDS,
        session_id="671_T1_P1_R1",
        run_label="test_run",
    )
    fail_rows = compact[compact["stage07_row_qc_status"] == "fail"]
    assert not fail_rows.empty
    assert bool(fail_rows["stage07_jump_from_previous_frame"].any())


def test_core_jump_fail_link_gets_allow_filter_with_warning_policy() -> None:
    policy = compute_stage08_policy(
        feature_scope="core_candidate",
        branch_cut_status="pass",
        jump_status="fail",
        stage06_reconstruction_valid=True,
        stage06_sign_valid=True,
        stage04_valid=True,
        stage05_valid=True,
        requires_manual_review=False,
    )
    assert policy == "allow_filter_with_warning"


def test_core_branch_cut_fail_link_gets_allow_filter_with_warning_policy() -> None:
    policy = compute_stage08_policy(
        feature_scope="core_candidate",
        branch_cut_status="fail",
        jump_status="pass",
        stage06_reconstruction_valid=True,
        stage06_sign_valid=True,
        stage04_valid=True,
        stage05_valid=True,
        requires_manual_review=False,
    )
    assert policy == "allow_filter_with_warning"


def test_core_reconstruction_fail_still_blocks_whole_link() -> None:
    policy = compute_stage08_policy(
        feature_scope="core_candidate",
        branch_cut_status="pass",
        jump_status="pass",
        stage06_reconstruction_valid=False,
        stage06_sign_valid=True,
        stage04_valid=True,
        stage05_valid=True,
        requires_manual_review=False,
    )
    assert policy == "block_filter"


def test_excluded_distal_link_gets_excluded_policy() -> None:
    policy = compute_stage08_policy(
        feature_scope="excluded_distal",
        branch_cut_status="fail",
        jump_status="fail",
        stage06_reconstruction_valid=True,
        stage06_sign_valid=True,
        stage04_valid=True,
        stage05_valid=True,
        requires_manual_review=False,
    )
    assert policy == "excluded_from_analysis"


def test_review_trunk_link_gets_manual_review_policy() -> None:
    scope = feature_scope_from_classification(
        link_classification="trunk_spine",
        core_candidate=False,
        excluded_candidate=False,
        is_skipped=False,
        child_bone="Ab",
        exclusion_reason="",
    )
    assert scope == "review_provisional"
    policy = compute_stage08_policy(
        feature_scope=scope,
        branch_cut_status="pass",
        jump_status="pass",
        stage06_reconstruction_valid=True,
        stage06_sign_valid=True,
        stage04_valid=True,
        stage05_valid=True,
        requires_manual_review=True,
    )
    assert policy == "manual_review_required"


def test_link_manifest_has_richer_fields(tmp_path: Path) -> None:
    out_dir = tmp_path / "run"
    parsed = parse_motive_header(VALID)
    run_stage_01(VALID, out_dir)
    run_stage_03(VALID, out_dir, parsed=parsed)
    run_stage_04(VALID, out_dir, parsed=parsed)
    run_stage_05(VALID, out_dir, parsed=parsed)
    run_stage_06(VALID, out_dir)
    run_stage_07(VALID, out_dir)

    df = pd.read_csv(out_dir / "07_rotation_vectors" / "qc_link_manifest.csv")
    assert list(df.columns) == list(LINK_MANIFEST_COLUMNS)
    assert "stage06_max_reconstruction_error_deg" in df.columns
    assert "stage07_max_jump_rad" in df.columns


def test_session_manifest_has_per_session_statuses(tmp_path: Path) -> None:
    out_dir = tmp_path / "run"
    parsed = parse_motive_header(VALID)
    run_stage_01(VALID, out_dir)
    run_stage_03(VALID, out_dir, parsed=parsed)
    run_stage_04(VALID, out_dir, parsed=parsed)
    run_stage_05(VALID, out_dir, parsed=parsed)
    run_stage_06(VALID, out_dir)
    run_stage_07(VALID, out_dir)

    df = pd.read_csv(out_dir / "07_rotation_vectors" / "qc_session_manifest.csv")
    assert list(df.columns) == list(SESSION_MANIFEST_COLUMNS)
    row = df.iloc[0]
    assert row["stage04_file_status"] in {"pass", "warning", "fail"}
    assert row["stage08_authorization_status"] in {
        "authorized",
        "blocked",
        "review_required",
    }


def _minimal_context():
    """Minimal StageQCContext stand-in for unit tests without full pipeline dirs."""
    from layer2_motive.qc_propagation import StageQCContext

    empty_bone = pd.DataFrame(
        {
            "source_bone_name": ["671:LFArm", "671:LHand"],
            "qc_status": ["pass", "pass"],
            "post_correction_valid": [True, True],
        }
    ).set_index("source_bone_name", drop=False)
    empty_link = pd.DataFrame(
        {
            "joint_id": ["J001"],
            "reconstruction_status": ["pass"],
            "max_error_deg": [0.0],
            "post_correction_valid": [True],
        }
    ).set_index("joint_id", drop=False)
    return StageQCContext(
        stage04_by_bone=empty_bone,
        stage05_by_bone=empty_bone,
        stage06_recon_by_link=empty_link,
        stage06_sign_by_link=empty_link,
        stage03_timing_status="pass",
        stage04_file_status="pass",
        stage05_file_status="pass",
        stage06_file_status="pass",
        sampling_rate_hz=120.0,
        frame_count=4,
    )


def test_build_link_qc_record_core_jump_fail(tmp_path: Path) -> None:
    diag = _make_link_diag()
    record = build_link_qc_record(
        link_diag=diag,
        context=_minimal_context(),
        candidate_row=None,
    )
    assert record.stage08_policy == "allow_filter_with_warning"
    assert record.stage07_jump_status == "fail"
