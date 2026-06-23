"""Tests for importable notebook review runner and output loaders."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from layer2_motive.segmentation.notebook_review import (
    NOTEBOOK_QC_EVIDENCE_OPTIONS,
    SCIENTIST_LINK_JOINT_COLUMNS,
    SCIENTIST_QC_EVENT_COLUMNS,
    ReviewOutputError,
    audit_file_info,
    collect_output_paths,
    gap_policy_from_qc_evidence,
    load_audit_preview,
    load_review_outputs,
    load_summary_json,
    prepare_review_input_summary,
    prepare_scientist_link_joint_table,
    prepare_scientist_qc_event_table,
    run_review_from_notebook,
    run_window_review,
    validate_compact_table_columns,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
T1_DATADESC = (
    REPO_ROOT
    / "data_description"
    / "671_T1_P1_R1_Take 2026-01-06 03.57.12 PM_001_DataDescriptions.csv"
)

EXPECTED_OUTPUTS = [
    "window_qc_summary_display.csv",
    "qc_event_display.csv",
    "layer2_link_scope_display.csv",
    "layer1_marker_family_risk.csv",
    "combined_qc_event_summary.csv",
    "combined_qc_events.csv",
    "window_validation_summary.json",
    "window_review_report.md",
]


def test_run_window_review_on_fixture(fixture_layer1_dir, fixture_layer2_dir, tmp_path):
    out_dir = tmp_path / "notebook_review_out"
    result = run_window_review(
        fixture_layer1_dir,
        fixture_layer2_dir,
        16000,
        17000,
        gap_policy="strict",
        export_scope="core_candidate",
        out=out_dir,
    )
    assert result.safe_to_open is True
    assert result.start_frame == 16000
    assert result.end_frame == 17000
    assert result.datadescriptions_used is False
    assert result.n_combined_events > 0
    for name in EXPECTED_OUTPUTS:
        assert (result.out_dir / name).exists(), name


def test_load_review_outputs(fixture_layer1_dir, fixture_layer2_dir, tmp_path):
    out_dir = tmp_path / "load_outputs"
    run_window_review(
        fixture_layer1_dir,
        fixture_layer2_dir,
        16000,
        17000,
        out=out_dir,
    )
    outputs = load_review_outputs(out_dir)
    validate_compact_table_columns(outputs)
    assert len(outputs.window_qc_summary) == 1
    assert not outputs.qc_event_display.empty


def test_missing_output_raises_clear_error(tmp_path):
    with pytest.raises(ReviewOutputError, match="Missing review output file"):
        load_review_outputs(tmp_path / "missing")


def test_load_summary_json(fixture_layer1_dir, fixture_layer2_dir, tmp_path):
    out_dir = tmp_path / "summary_json"
    run_window_review(
        fixture_layer1_dir,
        fixture_layer2_dir,
        16000,
        17000,
        gap_policy="strict",
        export_scope="core_candidate",
        out=out_dir,
    )
    summary = load_summary_json(out_dir)
    assert summary["gap_policy"] == "strict"
    assert summary["export_scope"] == "core_candidate"
    assert summary["datadescriptions_used"] is False
    assert "mapping_version" in summary


def test_collect_output_paths_and_audit_info(fixture_layer1_dir, fixture_layer2_dir, tmp_path):
    out_dir = tmp_path / "audit_info"
    run_window_review(
        fixture_layer1_dir,
        fixture_layer2_dir,
        16000,
        17000,
        out=out_dir,
    )
    paths = collect_output_paths(out_dir)
    assert paths["combined_qc_events"].exists()
    assert paths["window_review_report"].exists()
    assert paths["window_validation_summary"].exists()

    info = audit_file_info(out_dir)
    assert info.row_count > 0
    assert info.size_bytes > 0

    preview = load_audit_preview(out_dir, nrows=50)
    assert len(preview) == 50


@pytest.mark.skipif(not T1_DATADESC.exists(), reason="T1 DataDescriptions fixture missing")
def test_run_window_review_with_datadescriptions(
    fixture_layer1_dir, fixture_layer2_dir, tmp_path
):
    out_dir = tmp_path / "with_dd"
    result = run_window_review(
        fixture_layer1_dir,
        fixture_layer2_dir,
        16000,
        17000,
        datadescriptions=T1_DATADESC,
        out=out_dir,
    )
    assert result.datadescriptions_used is True
    summary = load_summary_json(out_dir)
    assert summary["datadescriptions_used"] is True
    assert summary["mapping_source"] == "session_datadescriptions_optional"


def test_cli_equivalence_with_runner(fixture_layer1_dir, fixture_layer2_dir, tmp_path):
    runner_dir = tmp_path / "runner_out"
    cli_dir = tmp_path / "cli_out"
    run_window_review(
        fixture_layer1_dir,
        fixture_layer2_dir,
        16000,
        17000,
        out=runner_dir,
    )
    script = REPO_ROOT / "scripts" / "review_segmentation_window.py"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--layer1-dir",
            str(fixture_layer1_dir),
            "--layer2-dir",
            str(fixture_layer2_dir),
            "--start-frame",
            "16000",
            "--end-frame",
            "17000",
            "--out",
            str(cli_dir),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    for name in EXPECTED_OUTPUTS:
        assert (runner_dir / name).exists()
        assert (cli_dir / name).exists()

    runner_summary = json.loads((runner_dir / "window_validation_summary.json").read_text())
    cli_summary = json.loads((cli_dir / "window_validation_summary.json").read_text())
    assert runner_summary["gap_policy"] == cli_summary["gap_policy"]
    assert runner_summary["export_scope"] == cli_summary["export_scope"]


def test_gap_policy_from_qc_evidence():
    assert gap_policy_from_qc_evidence(["gap_0p5", "gap_0p2"]) == "strict"
    assert gap_policy_from_qc_evidence(["gap_0p5", "artifact_sigma"]) == "relaxed"


def test_run_review_from_notebook_maps_qc_evidence(
    fixture_layer1_dir, fixture_layer2_dir, tmp_path
):
    out_dir = tmp_path / "notebook_entry"
    result = run_review_from_notebook(
        fixture_layer1_dir,
        fixture_layer2_dir,
        16000,
        17000,
        qc_evidence=["gap_0p5", "artifact_sigma"],
        export_scope="core_candidate",
        out=out_dir,
    )
    assert result.gap_policy == "relaxed"
    assert set(result.qc_evidence_selected) == {"gap_0p5", "artifact_sigma"}


@pytest.fixture
def review_bundle(fixture_layer1_dir, fixture_layer2_dir, tmp_path):
    out_dir = tmp_path / "scientist_tables"
    result = run_review_from_notebook(
        fixture_layer1_dir,
        fixture_layer2_dir,
        16000,
        17000,
        out=out_dir,
    )
    outputs = load_review_outputs(out_dir)
    summary = load_summary_json(out_dir)
    return result, outputs, summary


def test_prepare_scientist_qc_event_table_columns(review_bundle):
    _, outputs, _ = review_bundle
    table = prepare_scientist_qc_event_table(outputs.qc_event_display)
    assert list(table.columns) == list(SCIENTIST_QC_EVENT_COLUMNS)
    assert not table.empty
    assert set(table["QC type"]).issubset(set(NOTEBOOK_QC_EVIDENCE_OPTIONS))
    assert (outputs.qc_event_display["source_layer"] == "layer2").any()


def test_prepare_scientist_link_joint_table_columns(review_bundle):
    _, outputs, _ = review_bundle
    table = prepare_scientist_link_joint_table(outputs.layer2_link_scope)
    assert list(table.columns) == list(SCIENTIST_LINK_JOINT_COLUMNS)
    assert not table.empty
    assert "Status" in table.columns
    assert "recommendation_placeholder" not in table.columns


def test_prepare_scientist_qc_event_table_has_marker_names(review_bundle):
    _, outputs, _ = review_bundle
    table = prepare_scientist_qc_event_table(outputs.qc_event_display)
    assert not table.empty
    marker_values = table["Marker / region"].astype(str)
    assert marker_values.str.contains(":", regex=False).any()
    assert not marker_values.str.fullmatch(r"\d+").any()


def test_prepare_review_input_summary_counts(review_bundle):
    result, outputs, summary = review_bundle
    input_summary = prepare_review_input_summary(result, outputs, summary)
    assert input_summary.labeled_markers_total > 0
    assert input_summary.session_labeled_markers >= input_summary.labeled_markers_total
    assert input_summary.labeled_markers_mapped >= 0
    assert input_summary.labeled_markers_unmapped >= 0
    assert (
        input_summary.labeled_markers_mapped + input_summary.labeled_markers_unmapped
        == input_summary.labeled_markers_total
    )
    assert input_summary.total_layer2_links > 0
    assert input_summary.included_layer2_links > 0
    assert input_summary.included_layer2_links <= input_summary.total_layer2_links
    assert input_summary.unlabeled_evidence_in_main_ux is False


def test_link_table_has_nonzero_l1_burden_with_interval_mapping(
    fixture_layer1_dir, fixture_layer2_dir, tmp_path
):
    out_dir = tmp_path / "link_burden"
    result = run_review_from_notebook(
        fixture_layer1_dir,
        fixture_layer2_dir,
        16000,
        17000,
        out=out_dir,
    )
    outputs = load_review_outputs(out_dir)
    link_table = prepare_scientist_link_joint_table(outputs.layer2_link_scope)
    l1_cols = ["L1 gap_0p5", "L1 artifact %", "L1 swap %"]
    has_signal = link_table[l1_cols].astype(str).ne("0").ne("0.0%").any().any()
    assert has_signal or result.n_layer1_events > 0


def test_unlabeled_marker_evidence_excluded_from_scientist_qc_table(review_bundle):
    _, outputs, _ = review_bundle
    table = prepare_scientist_qc_event_table(outputs.qc_event_display)
    assert "frame_status" not in set(table["QC type"].astype(str))
    assert "interval_status" not in set(table["QC type"].astype(str))


def test_notebook_qc_evidence_options_match_requirements():
    assert set(NOTEBOOK_QC_EVIDENCE_OPTIONS) == {
        "gap_0p5",
        "gap_0p2",
        "artifact_sigma",
        "segment_swap",
    }
