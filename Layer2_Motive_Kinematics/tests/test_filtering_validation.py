"""Tests for Stage 08 Butterworth filtering and jump-context masking (V1)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
from scipy.signal import sosfiltfilt

from layer2_motive.filtering import (
    FilteringConfig,
    build_stage08_flag_report,
    build_stage08_ineligible_rows_report,
    build_stage08_nan_report,
    design_butterworth_sos,
    filter_rotvec_components,
    load_filtering_config,
    process_file_filtering,
    process_link_filtering,
    validate_cutoff_hz,
)
from layer2_motive.rotvec import RotVecThresholds
from layer2_motive.stages.stage08 import run_stage_08
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

DEFAULT_FILTERING = FilteringConfig(
    cutoff_hz=10.0,
    filter_order=4,
    filter_type="butterworth",
    nyquist_safety_factor=0.45,
    jump_context_window_frames=30,
)

SAMPLING_RATE_HZ = 120.0


def _smooth_rotvec_table(frames: int = 200, joint_id: str = "J001") -> pd.DataFrame:
    t = np.linspace(0, 2 * np.pi, frames)
    rx = 0.1 * np.sin(t)
    ry = 0.05 * np.cos(t)
    rz = 0.02 * np.sin(2 * t)
    return pd.DataFrame(
        {
            "session_id": ["671_T1_P1_R1"] * frames,
            "run_label": ["test_run"] * frames,
            "frame": np.arange(frames),
            "time_sec": np.arange(frames) / SAMPLING_RATE_HZ,
            "link_id": [joint_id] * frames,
            "parent_canonical": ["LFArm"] * frames,
            "child_canonical": ["LHand"] * frames,
            "rx": rx,
            "ry": ry,
            "rz": rz,
            "rotvec_norm": np.linalg.norm(np.column_stack([rx, ry, rz]), axis=1),
            "feature_scope": ["core_candidate"] * frames,
            "included_in_v0": [True] * frames,
            "requires_manual_review": [False] * frames,
            "stage04_quaternion_valid": [True] * frames,
            "stage05_global_sign_continuity_valid": [True] * frames,
            "stage06_relative_reconstruction_valid": [True] * frames,
            "stage06_relative_sign_continuity_valid": [True] * frames,
            "stage07_branch_cut_status": ["pass"] * frames,
            "stage07_jump_status": ["pass"] * frames,
            "stage07_jump_from_previous_frame": [False] + [True] * (frames - 1),
            "stage07_jump_magnitude_rad": [0.0]
            + list(np.linalg.norm(np.diff(np.column_stack([rx, ry, rz]), axis=0), axis=1)),
            "stage07_row_qc_status": ["pass"] * frames,
            "stage07_link_qc_status": ["pass"] * frames,
            "stage08_policy": ["allow_filter"] * frames,
        }
    )


def _jump_rotvec_table(frames: int = 100, jump_at: int = 50) -> pd.DataFrame:
    table = _smooth_rotvec_table(frames=frames)
    table.loc[jump_at, "rx"] = 1.2
    diffs = np.linalg.norm(
        np.diff(table[["rx", "ry", "rz"]].to_numpy(), axis=0),
        axis=1,
    )
    table.loc[1:, "stage07_jump_magnitude_rad"] = diffs
    table.loc[jump_at, "stage07_row_qc_status"] = "fail"
    table["stage07_jump_status"] = "fail"
    table["stage08_policy"] = "allow_filter_with_warning"
    return table


def test_sosfiltfilt_not_given_nans() -> None:
    sos = design_butterworth_sos(10.0, SAMPLING_RATE_HZ, 4)
    min_len = 60
    clean = np.linspace(0.0, 1.0, min_len)
    signal = np.concatenate([clean, [np.nan], clean])
    components = np.column_stack([signal, signal, signal])

    captured: list[np.ndarray] = []
    original = sosfiltfilt

    def _spy(sos_in, x, *args, **kwargs):
        captured.append(np.asarray(x))
        return original(sos_in, x, *args, **kwargs)

    with patch("layer2_motive.filtering.sosfiltfilt", side_effect=_spy):
        filter_rotvec_components(components, sos)

    assert captured
    for segment in captured:
        assert np.all(np.isfinite(segment))


def test_filtering_produces_finite_native_output_on_clean_data() -> None:
    table = _smooth_rotvec_table()
    filtered, summary, _, _, _, file_result = process_file_filtering(
        stage07_table=table,
        sampling_rate_hz=SAMPLING_RATE_HZ,
        filtering_config=DEFAULT_FILTERING,
        rotvec_thresholds=DEFAULT_THRESHOLDS,
    )
    assert file_result.interpolation_applied is False
    assert bool(filtered["rx_filtered_native"].notna().all())
    assert bool(np.isfinite(filtered["rx_filtered_native"]).all())
    assert int(summary.iloc[0]["filter_applied_frames"]) == len(table)


def test_stage07_jump_frame_marked() -> None:
    table = _jump_rotvec_table(jump_at=50)
    filtered, summary, jump_report, _, _, _ = process_file_filtering(
        stage07_table=table,
        sampling_rate_hz=SAMPLING_RATE_HZ,
        filtering_config=DEFAULT_FILTERING,
        rotvec_thresholds=DEFAULT_THRESHOLDS,
    )
    jump_rows = filtered[filtered["stage08_stage07_jump_frame"]]
    assert not jump_rows.empty
    assert 50 in set(jump_rows["frame"].astype(int))
    assert int(summary.iloc[0]["jump_event_frames"]) >= 1
    assert not jump_report.empty


def test_jump_context_window_marked() -> None:
    table = _jump_rotvec_table(jump_at=50)
    config = FilteringConfig(
        cutoff_hz=10.0,
        filter_order=4,
        filter_type="butterworth",
        nyquist_safety_factor=0.45,
        jump_context_window_frames=5,
    )
    filtered, _, _, _, _, _ = process_file_filtering(
        stage07_table=table,
        sampling_rate_hz=SAMPLING_RATE_HZ,
        filtering_config=config,
        rotvec_thresholds=DEFAULT_THRESHOLDS,
    )
    context_rows = filtered[filtered["stage08_within_jump_context_window"]]
    context_frames = set(context_rows["frame"].astype(int))
    assert 50 in context_frames
    assert 45 in context_frames
    assert 55 in context_frames
    assert 40 not in context_frames


def test_jump_context_frames_keep_numeric_analysis_values() -> None:
    table = _jump_rotvec_table(jump_at=50)
    filtered, _, _, _, _, _ = process_file_filtering(
        stage07_table=table,
        sampling_rate_hz=SAMPLING_RATE_HZ,
        filtering_config=DEFAULT_FILTERING,
        rotvec_thresholds=DEFAULT_THRESHOLDS,
    )
    context = filtered[filtered["stage08_within_jump_context_window"]]
    applied = context[context["stage08_filter_applied"]]
    assert not applied.empty
    assert bool(np.isfinite(applied["rx_filtered_analysis"]).all())
    assert bool(np.isfinite(applied["ry_filtered_analysis"]).all())
    assert bool(np.isfinite(applied["rz_filtered_analysis"]).all())
    assert context["stage08_analysis_eligible"].eq(False).all()
    assert context["stage08_mask_reason"].eq("stage07_jump_context").all()


def test_jump_context_no_qc_mask_nan_in_analysis_columns() -> None:
    table = _jump_rotvec_table(jump_at=50)
    filtered, _, _, _, _, _ = process_file_filtering(
        stage07_table=table,
        sampling_rate_hz=SAMPLING_RATE_HZ,
        filtering_config=DEFAULT_FILTERING,
        rotvec_thresholds=DEFAULT_THRESHOLDS,
    )
    jump_context = filtered.loc[
        filtered["stage08_mask_reason"].eq("stage07_jump_context")
    ]
    assert not jump_context.empty
    for col in ("rx_filtered_analysis", "ry_filtered_analysis", "rz_filtered_analysis"):
        assert jump_context[col].notna().all()


def test_native_filtered_finite_where_filter_succeeds_in_jump_context() -> None:
    table = _jump_rotvec_table(jump_at=50)
    filtered, _, _, _, _, _ = process_file_filtering(
        stage07_table=table,
        sampling_rate_hz=SAMPLING_RATE_HZ,
        filtering_config=DEFAULT_FILTERING,
        rotvec_thresholds=DEFAULT_THRESHOLDS,
    )
    context = filtered[filtered["stage08_within_jump_context_window"]]
    applied = context[context["stage08_filter_applied"]]
    assert not applied.empty
    assert bool(np.isfinite(applied["rx_filtered_native"]).all())


def test_excluded_links_flagged_but_numeric_when_filtered() -> None:
    table = _smooth_rotvec_table()
    table["feature_scope"] = "excluded_distal"
    table["stage08_policy"] = "excluded_from_analysis"
    filtered, summary, _, _, _, _ = process_file_filtering(
        stage07_table=table,
        sampling_rate_hz=SAMPLING_RATE_HZ,
        filtering_config=DEFAULT_FILTERING,
        rotvec_thresholds=DEFAULT_THRESHOLDS,
    )
    assert filtered["stage08_analysis_eligible"].eq(False).all()
    assert filtered["rx_filtered_analysis"].notna().all()
    assert summary.iloc[0]["stage08_filter_status"] == "excluded_from_analysis"
    assert bool((filtered["stage08_output_scope"] == "excluded_from_analysis").all())


def test_review_links_not_silently_analysis_clean_core() -> None:
    table = _smooth_rotvec_table()
    table["feature_scope"] = "review_provisional"
    table["requires_manual_review"] = True
    table["stage08_policy"] = "manual_review_required"
    filtered, summary, _, _, _, _ = process_file_filtering(
        stage07_table=table,
        sampling_rate_hz=SAMPLING_RATE_HZ,
        filtering_config=DEFAULT_FILTERING,
        rotvec_thresholds=DEFAULT_THRESHOLDS,
    )
    assert filtered["stage08_analysis_eligible"].eq(False).all()
    assert summary.iloc[0]["stage08_filter_status"] == "provisional_manual_review"
    assert not bool((filtered["stage08_output_scope"] == "analysis_clean_core").any())


def test_stage07_outputs_not_overwritten(tmp_path: Path) -> None:
    out_dir = tmp_path / "run"
    stage07_dir = out_dir / "07_rotation_vectors"
    stage07_dir.mkdir(parents=True)
    timing_dir = out_dir / "03_frame_time_validation"
    timing_dir.mkdir(parents=True)

    stage07_table = _smooth_rotvec_table(frames=200)
    stage07_parquet = stage07_dir / "relative_rotation_vectors.parquet"
    stage07_table.to_parquet(stage07_parquet, index=False)

    pd.DataFrame(
        [
            {
                "inferred_sampling_rate_hz": SAMPLING_RATE_HZ,
                "observed_unique_frame_count": 200,
                "timing_status": "pass",
            }
        ]
    ).to_csv(timing_dir / "frame_time_summary.csv", index=False)

    for sub in ("04_quaternion_qc", "05_sign_continuity", "06_relative_quaternions"):
        (out_dir / sub).mkdir(parents=True)
    pd.DataFrame([{"file_qc_status": "pass"}]).to_csv(
        out_dir / "04_quaternion_qc" / "quaternion_qc_summary.csv", index=False
    )
    pd.DataFrame([{"post_correction_valid": True}]).to_csv(
        out_dir / "05_sign_continuity" / "sign_continuity_summary.csv", index=False
    )
    pd.DataFrame([{"links_fail": 0, "links_warning": 0}]).to_csv(
        out_dir / "06_relative_quaternions" / "relative_quaternion_summary.csv", index=False
    )
    pd.DataFrame(columns=["source_bone_name", "qc_status"]).to_csv(
        out_dir / "04_quaternion_qc" / "quaternion_qc_by_bone.csv", index=False
    )
    pd.DataFrame(columns=["source_bone_name", "post_correction_valid"]).to_csv(
        out_dir / "05_sign_continuity" / "sign_flips_by_bone.csv", index=False
    )

    before = stage07_parquet.read_bytes()
    before_mtime = stage07_parquet.stat().st_mtime

    run_stage_08(VALID, out_dir)

    after = stage07_parquet.read_bytes()
    after_mtime = stage07_parquet.stat().st_mtime
    assert before == after
    assert before_mtime == after_mtime
    assert (out_dir / "08_filtered_rotvecs" / "filtered_relative_rotation_vectors.parquet").exists()


def test_cutoff_validation_rejects_too_high_cutoff() -> None:
    with pytest.raises(HardStopError, match="cutoff"):
        validate_cutoff_hz(60.0, SAMPLING_RATE_HZ, nyquist_safety_factor=0.45)


def test_load_filtering_config_includes_jump_context_window() -> None:
    config = load_filtering_config()
    assert config.jump_context_window_frames == 30


def test_process_link_filtering_distance_to_nearest_jump() -> None:
    table = _jump_rotvec_table(jump_at=50, frames=100)
    sos = design_butterworth_sos(10.0, SAMPLING_RATE_HZ, 4)
    filtered, _, _, _ = process_link_filtering(
        table,
        sos=sos,
        filtering_config=FilteringConfig(
            cutoff_hz=10.0,
            filter_order=4,
            filter_type="butterworth",
            nyquist_safety_factor=0.45,
            jump_context_window_frames=10,
        ),
        rotvec_thresholds=DEFAULT_THRESHOLDS,
        sampling_rate_hz=SAMPLING_RATE_HZ,
    )
    row_at_53 = filtered.loc[filtered["frame"] == 53].iloc[0]
    assert row_at_53["stage08_distance_to_nearest_stage07_jump_frame"] <= 3.0
    assert bool(row_at_53["stage08_within_jump_context_window"])


def test_jump_fail_link_mostly_analysis_eligible_outside_context() -> None:
    table = _jump_rotvec_table(jump_at=50, frames=100)
    filtered, summary, _, _, _, _ = process_file_filtering(
        stage07_table=table,
        sampling_rate_hz=SAMPLING_RATE_HZ,
        filtering_config=DEFAULT_FILTERING,
        rotvec_thresholds=DEFAULT_THRESHOLDS,
    )
    assert summary.iloc[0]["stage08_filter_status"] == "filtered_but_jump_context_flagged"
    n_eligible = int(summary.iloc[0]["analysis_eligible_frames"])
    n_context = int(summary.iloc[0]["jump_context_frames"])
    assert n_eligible + n_context == 100 or n_eligible + n_context >= 95
    outside = filtered[~filtered["stage08_within_jump_context_window"]]
    assert outside["stage08_analysis_eligible"].all()
    assert outside["rx_filtered_analysis"].notna().all()


def test_block_filter_still_flags_whole_link() -> None:
    table = _smooth_rotvec_table(frames=100)
    table["stage08_policy"] = "block_filter"
    filtered, summary, _, _, _, _ = process_file_filtering(
        stage07_table=table,
        sampling_rate_hz=SAMPLING_RATE_HZ,
        filtering_config=DEFAULT_FILTERING,
        rotvec_thresholds=DEFAULT_THRESHOLDS,
    )
    assert filtered["stage08_analysis_eligible"].sum() == 0
    assert filtered["stage08_mask_reason"].eq("blocked_needs_review").all()
    assert filtered["rx_filtered_analysis"].notna().all()
    assert summary.iloc[0]["stage08_filter_status"] == "blocked_needs_review"


def test_branch_cut_context_flagging() -> None:
    table = _smooth_rotvec_table(frames=100)
    near_pi = float(DEFAULT_THRESHOLDS.branch_cut_warning_rad + 0.01)
    table.loc[50, "rotvec_norm"] = near_pi
    table["stage07_branch_cut_status"] = "warning"
    table["stage08_policy"] = "allow_filter_with_warning"
    config = FilteringConfig(
        cutoff_hz=10.0,
        filter_order=4,
        filter_type="butterworth",
        nyquist_safety_factor=0.45,
        jump_context_window_frames=5,
    )
    filtered, _, _, branch_report, _, _ = process_file_filtering(
        stage07_table=table,
        sampling_rate_hz=SAMPLING_RATE_HZ,
        filtering_config=config,
        rotvec_thresholds=DEFAULT_THRESHOLDS,
    )
    assert not branch_report.empty
    context = filtered[filtered["stage08_within_branch_cut_context_window"]]
    assert 50 in set(context["frame"].astype(int))
    assert context["stage08_mask_reason"].eq("stage07_branch_cut_context").all()
    assert context["rx_filtered_analysis"].notna().all()
    outside = filtered[~filtered["stage08_within_branch_cut_context_window"]]
    assert outside["stage08_analysis_eligible"].all()


def test_native_and_analysis_filtered_match_when_filter_applied() -> None:
    table = _jump_rotvec_table(jump_at=50)
    filtered, _, _, _, _, _ = process_file_filtering(
        stage07_table=table,
        sampling_rate_hz=SAMPLING_RATE_HZ,
        filtering_config=DEFAULT_FILTERING,
        rotvec_thresholds=DEFAULT_THRESHOLDS,
    )
    applied = filtered[filtered["stage08_filter_applied"]]
    for native_col, analysis_col in (
        ("rx_filtered_native", "rx_filtered_analysis"),
        ("ry_filtered_native", "ry_filtered_analysis"),
        ("rz_filtered_native", "rz_filtered_analysis"),
    ):
        assert np.allclose(
            applied[native_col].to_numpy(dtype=float),
            applied[analysis_col].to_numpy(dtype=float),
            equal_nan=True,
        )


def test_computational_nan_only_when_filter_not_applied() -> None:
    table = _smooth_rotvec_table(frames=200)
    table.loc[100, ["rx", "ry", "rz"]] = np.nan
    filtered, _, _, _, _, _ = process_file_filtering(
        stage07_table=table,
        sampling_rate_hz=SAMPLING_RATE_HZ,
        filtering_config=DEFAULT_FILTERING,
        rotvec_thresholds=DEFAULT_THRESHOLDS,
    )
    nan_row = filtered.loc[filtered["frame"] == 100].iloc[0]
    assert not np.isfinite(nan_row["rx_filtered_analysis"])
    assert nan_row["stage08_mask_reason"] == "filter_not_applied"


def test_stage08_nan_report_distinguishes_computational_from_qc_flagged() -> None:
    table = _jump_rotvec_table(jump_at=50, frames=100)
    table.loc[95, ["rx", "ry", "rz"]] = np.nan
    filtered, _, _, _, _, _ = process_file_filtering(
        stage07_table=table,
        sampling_rate_hz=SAMPLING_RATE_HZ,
        filtering_config=DEFAULT_FILTERING,
        rotvec_thresholds=DEFAULT_THRESHOLDS,
    )
    nan_report = build_stage08_nan_report(filtered)
    flag_report = build_stage08_flag_report(filtered)
    assert not nan_report.empty
    assert (nan_report["nan_classification"] == "computational_failure").any()
    assert flag_report["stage08_mask_reason"].eq("stage07_jump_context").any()
    assert not flag_report.loc[flag_report["frame"] == 95, "stage08_mask_reason"].eq(
        "stage07_jump_context"
    ).any()


def test_stage08_reports_include_flagged_rows(tmp_path: Path) -> None:
    out_dir = tmp_path / "run"
    stage07_dir = out_dir / "07_rotation_vectors"
    stage07_dir.mkdir(parents=True)
    timing_dir = out_dir / "03_frame_time_validation"
    timing_dir.mkdir(parents=True)

    stage07_table = _jump_rotvec_table(jump_at=50, frames=100)
    stage07_table.to_parquet(stage07_dir / "relative_rotation_vectors.parquet", index=False)
    pd.DataFrame(
        [
            {
                "inferred_sampling_rate_hz": SAMPLING_RATE_HZ,
                "observed_unique_frame_count": 100,
                "timing_status": "pass",
            }
        ]
    ).to_csv(timing_dir / "frame_time_summary.csv", index=False)

    for sub in ("04_quaternion_qc", "05_sign_continuity", "06_relative_quaternions"):
        (out_dir / sub).mkdir(parents=True)
    pd.DataFrame([{"file_qc_status": "pass"}]).to_csv(
        out_dir / "04_quaternion_qc" / "quaternion_qc_summary.csv", index=False
    )
    pd.DataFrame([{"post_correction_valid": True}]).to_csv(
        out_dir / "05_sign_continuity" / "sign_continuity_summary.csv", index=False
    )
    pd.DataFrame([{"links_fail": 0, "links_warning": 0}]).to_csv(
        out_dir / "06_relative_quaternions" / "relative_quaternion_summary.csv", index=False
    )
    pd.DataFrame(columns=["source_bone_name", "qc_status"]).to_csv(
        out_dir / "04_quaternion_qc" / "quaternion_qc_by_bone.csv", index=False
    )
    pd.DataFrame(columns=["source_bone_name", "post_correction_valid"]).to_csv(
        out_dir / "05_sign_continuity" / "sign_flips_by_bone.csv", index=False
    )

    run_stage_08(VALID, out_dir)
    stage_dir = out_dir / "08_filtered_rotvecs"
    parquet_df = pd.read_parquet(stage_dir / "filtered_relative_rotation_vectors.parquet")
    flag_report = pd.read_csv(stage_dir / "stage08_flag_report.csv")
    ineligible_report = pd.read_csv(stage_dir / "stage08_ineligible_rows_report.csv")
    nan_report = pd.read_csv(stage_dir / "stage08_nan_report.csv")

    assert not flag_report.empty
    assert flag_report["stage08_mask_reason"].eq("stage07_jump_context").any()
    assert ineligible_report["value_kept_numeric"].astype(bool).any()
    jump_context = parquet_df.loc[parquet_df["stage08_mask_reason"] == "stage07_jump_context"]
    assert jump_context["rx_filtered_analysis"].notna().all()
    assert nan_report.empty or (
        nan_report["nan_classification"] == "computational_failure"
    ).all()


def test_jump_detection_thresholds_unchanged() -> None:
    table = _jump_rotvec_table(jump_at=50)
    table.loc[50, "stage07_jump_magnitude_rad"] = DEFAULT_THRESHOLDS.jump_warning_rad + 0.01
    _, summary, jump_report, _, _, _ = process_file_filtering(
        stage07_table=table,
        sampling_rate_hz=SAMPLING_RATE_HZ,
        filtering_config=DEFAULT_FILTERING,
        rotvec_thresholds=DEFAULT_THRESHOLDS,
    )
    assert int(summary.iloc[0]["jump_event_frames"]) >= 1
    assert 50 in set(jump_report["jump_event_frame"].astype(int))

    below_threshold = table.copy()
    below_threshold["stage07_jump_magnitude_rad"] = DEFAULT_THRESHOLDS.jump_warning_rad - 0.01
    below_threshold["stage07_jump_from_previous_frame"] = False
    _, summary_below, jump_below, _, _, _ = process_file_filtering(
        stage07_table=below_threshold,
        sampling_rate_hz=SAMPLING_RATE_HZ,
        filtering_config=DEFAULT_FILTERING,
        rotvec_thresholds=DEFAULT_THRESHOLDS,
    )
    assert int(summary_below.iloc[0]["jump_event_frames"]) == 0
    assert jump_below.empty


def test_filter_parameters_unchanged() -> None:
    config = load_filtering_config()
    assert config.cutoff_hz == 10.0
    assert config.filter_order == 4
    assert config.jump_context_window_frames == 30
    assert config.filter_type == "butterworth"
