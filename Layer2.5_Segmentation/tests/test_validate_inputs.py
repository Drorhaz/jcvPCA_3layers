"""Tests for validation logic."""

from __future__ import annotations

import json

import pandas as pd

from layer2_motive.segmentation.load_inputs import load_layer1_qc_folder, load_layer2_export_folder
from layer2_motive.segmentation.validate_inputs import (
    detect_layer1_frame_range,
    detect_layer2_frame_range,
    resolve_session_identity,
    run_all_validations,
    validate_frame_alignment,
    validate_link_manifest_join,
    write_validation_outputs,
)


def test_identity_pass_case(fixture_layer1_dir, fixture_layer2_dir):
    l1 = load_layer1_qc_folder(fixture_layer1_dir)
    l2 = load_layer2_export_folder(fixture_layer2_dir)
    identity, checks = resolve_session_identity(l1, l2)
    assert identity.layer1_run_key == identity.layer2_session_id == "671_T1_P1_R1"
    assert not identity.identity_override
    identity_check = next(
        c for c in checks if c.check_name == "session_identity_run_key_equals_session_id"
    )
    assert identity_check.status == "pass"


def test_identity_mismatch_blocks(fixture_layer1_dir, fixture_layer2_dir):
    l1 = load_layer1_qc_folder(fixture_layer1_dir)
    l2 = load_layer2_export_folder(fixture_layer2_dir)
    l1.manifest = dict(l1.manifest)
    l1.manifest["run_key"] = "WRONG_SESSION"
    result = run_all_validations(l1, l2, force=False)
    assert not result.safe_to_open
    assert any("session_identity" in e for e in result.blocking_errors)


def test_identity_mismatch_force_override(fixture_layer1_dir, fixture_layer2_dir):
    l1 = load_layer1_qc_folder(fixture_layer1_dir)
    l2 = load_layer2_export_folder(fixture_layer2_dir)
    l1.manifest = dict(l1.manifest)
    l1.manifest["run_key"] = "WRONG_SESSION"
    result = run_all_validations(l1, l2, force=True)
    assert result.safe_to_open
    assert result.identity is not None
    assert result.identity.identity_override


def test_run_label_mismatch_does_not_block_when_session_id_matches(
    fixture_layer1_dir, fixture_layer2_dir
):
    l1 = load_layer1_qc_folder(fixture_layer1_dir)
    l2 = load_layer2_export_folder(fixture_layer2_dir)
    assert l1.manifest["run_key"] != l2.summary["run_label"]
    result = run_all_validations(l1, l2)
    assert result.safe_to_open


def test_missing_required_parquet_column_fails(fixture_layer1_dir, fixture_layer2_dir):
    l1 = load_layer1_qc_folder(fixture_layer1_dir)
    l2 = load_layer2_export_folder(fixture_layer2_dir)
    l2.parquet_df = l2.parquet_df.drop(columns=["stage08_analysis_eligible"])
    result = run_all_validations(l1, l2)
    assert not result.safe_to_open
    assert any("layer2_parquet_required_columns" in e for e in result.blocking_errors)


def test_frame_alignment_exact_pass(fixture_layer1_dir, fixture_layer2_dir):
    l1 = load_layer1_qc_folder(fixture_layer1_dir)
    l2 = load_layer2_export_folder(fixture_layer2_dir)
    l1_range = detect_layer1_frame_range(l1)
    l2_range = detect_layer2_frame_range(l2)
    assert l1_range.start_frame == 0
    assert l1_range.end_frame == 30603
    assert l1_range.n_frames == 30604
    assert l2_range.start_frame == 0
    assert l2_range.end_frame == 30603
    alignment, checks = validate_frame_alignment(l1_range, l2_range)
    assert alignment.exact_frame_alignment
    exact_check = next(c for c in checks if c.check_name == "exact_frame_alignment")
    assert exact_check.status == "pass"


def test_frame_mismatch_overlap_warning():
    from layer2_motive.segmentation.schemas import FrameRangeInfo

    l1_range = FrameRangeInfo(start_frame=0, end_frame=100, n_frames=101)
    l2_range = FrameRangeInfo(start_frame=50, end_frame=150, n_frames=101)
    alignment, checks = validate_frame_alignment(l1_range, l2_range)
    assert not alignment.exact_frame_alignment
    assert alignment.overlap_start_frame == 50
    assert alignment.overlap_end_frame == 100
    overlap_check = next(c for c in checks if c.check_name == "frame_range_overlap")
    assert overlap_check.status == "warn"


def test_duplicate_frame_link_rows_fail(fixture_layer1_dir, fixture_layer2_dir):
    l1 = load_layer1_qc_folder(fixture_layer1_dir)
    l2 = load_layer2_export_folder(fixture_layer2_dir)
    dup_row = l2.parquet_df.iloc[[0]].copy()
    l2.parquet_df = pd.concat([l2.parquet_df, dup_row], ignore_index=True)
    result = run_all_validations(l1, l2)
    assert not result.safe_to_open
    assert any("duplicate" in e.lower() for e in result.blocking_errors)


def test_link_manifest_join_pass(fixture_layer2_dir):
    l2 = load_layer2_export_folder(fixture_layer2_dir)
    checks = validate_link_manifest_join(l2)
    join_check = next(
        c for c in checks if c.check_name == "layer2_link_manifest_join_run_label_link_id"
    )
    assert join_check.status == "pass"


def test_link_manifest_join_fail(fixture_layer2_dir):
    l2 = load_layer2_export_folder(fixture_layer2_dir)
    l2.link_manifest = l2.link_manifest.iloc[:-1].copy()
    checks = validate_link_manifest_join(l2)
    join_check = next(
        c for c in checks if c.check_name == "layer2_link_manifest_join_run_label_link_id"
    )
    assert join_check.status == "fail"


def test_full_validation_passes_on_fixture(fixture_layer1_dir, fixture_layer2_dir):
    l1 = load_layer1_qc_folder(fixture_layer1_dir)
    l2 = load_layer2_export_folder(fixture_layer2_dir)
    result = run_all_validations(l1, l2)
    assert result.safe_to_open
    assert result.alignment is not None
    assert result.alignment.exact_frame_alignment
    assert result.alignment.canonical_join_key == "frame"


def test_validation_outputs_written(fixture_layer1_dir, fixture_layer2_dir, tmp_path):
    l1 = load_layer1_qc_folder(fixture_layer1_dir)
    l2 = load_layer2_export_folder(fixture_layer2_dir)
    result = run_all_validations(l1, l2)
    out = write_validation_outputs(result, tmp_path / "validation_out")
    assert (out / "validation_report.md").exists()
    assert (out / "validation_summary.json").exists()
    assert (out / "validation_checks.csv").exists()
    summary = json.loads((out / "validation_summary.json").read_text())
    assert summary["safe_to_open"] is True
    assert summary["alignment"]["exact_frame_alignment"] is True


def test_missing_time_column_still_validates_frame_based(fixture_layer1_dir, fixture_layer2_dir):
    l1 = load_layer1_qc_folder(fixture_layer1_dir)
    l2 = load_layer2_export_folder(fixture_layer2_dir)
    l1.qc_mask = l1.qc_mask.drop(columns=["time_s"])
    l2.parquet_df = l2.parquet_df.drop(columns=["time_sec"])
    result = run_all_validations(l1, l2)
    assert result.safe_to_open
    assert result.alignment.layer1_frame_range.time_source == "reconstructed"
    assert result.alignment.layer2_frame_range.time_source == "reconstructed"


def test_input_files_not_modified(fixture_layer1_dir, fixture_layer2_dir):
    l1 = load_layer1_qc_folder(fixture_layer1_dir)
    l2 = load_layer2_export_folder(fixture_layer2_dir)
    result = run_all_validations(l1, l2)
    mutation_check = next(c for c in result.checks if c.check_name == "input_files_not_modified")
    assert mutation_check.status == "pass"
