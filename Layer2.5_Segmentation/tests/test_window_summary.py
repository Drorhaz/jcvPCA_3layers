"""Tests for window summarization and combined QC tables."""

import subprocess
import sys

from layer2_motive.segmentation.load_inputs import load_layer1_qc_folder, load_layer2_export_folder
from layer2_motive.segmentation.qc_events import build_layer1_event_table
from layer2_motive.segmentation.validate_inputs import run_all_validations
from layer2_motive.segmentation.window_summary import (
    build_combined_qc_event_table,
    subset_layer1_events_to_window,
    subset_layer2_to_window,
    summarize_layer1_window,
    summarize_layer2_window,
    write_window_review_outputs,
)


def test_window_subset_inclusive_boundaries(fixture_layer1_dir, fixture_layer2_dir):
    l1 = load_layer1_qc_folder(fixture_layer1_dir)
    l2 = load_layer2_export_folder(fixture_layer2_dir)
    events = build_layer1_event_table(l1, "671_T1_P1_R1")

    start, end = 16000, 17000
    l1_win = subset_layer1_events_to_window(events, start, end)
    l2_win = subset_layer2_to_window(l2.parquet_df, start, end)

    assert l2_win["frame"].min() == start
    assert l2_win["frame"].max() == end
    assert len(l2_win) == (end - start + 1) * 50

    # Interval overlapping boundary should be included
    if not l1_win.empty:
        assert l1_win["start_frame"].min() <= end
        assert l1_win["end_frame"].max() >= start


def test_layer1_summary_matches_brute_force(fixture_layer1_dir):
    l1 = load_layer1_qc_folder(fixture_layer1_dir)
    events = build_layer1_event_table(l1, "671_T1_P1_R1")
    start, end = 16000, 17000
    l1_win_events = subset_layer1_events_to_window(events, start, end)

    summary = summarize_layer1_window(l1.qc_mask, l1_win_events, start, end)
    window = l1.qc_mask[l1.qc_mask["frame"].between(start, end)]

    assert summary["n_window_frames"] == len(window)
    any_flag = pd.Series(False, index=window.index)
    for col in ("flag_gap_0p2", "flag_gap_0p5", "flag_artifact_sigma", "flag_segment_swap", "flag_edge_effect"):
        if col in window.columns:
            any_flag = any_flag | window[col].astype(bool)
    assert summary["n_use_frames"] == int((~any_flag).sum())
    assert summary["flag_counts"]["flag_gap_0p2"] == int(window["flag_gap_0p2"].astype(bool).sum())


def test_layer2_summary_matches_brute_force(fixture_layer2_dir):
    l2 = load_layer2_export_folder(fixture_layer2_dir)
    start, end = 16000, 17000
    window = subset_layer2_to_window(l2.parquet_df, start, end)
    summary = summarize_layer2_window(l2.parquet_df, l2.link_manifest, start, end)

    assert summary["n_rows"] == len(window)
    assert summary["n_analysis_eligible_rows"] == int(window["stage08_analysis_eligible"].sum())
    assert summary["n_analysis_ineligible_rows"] == len(window) - int(
        window["stage08_analysis_eligible"].sum()
    )
    assert summary["n_stage08_jump_context_rows"] == int(
        window["stage08_within_jump_context_window"].sum()
    )


def test_per_link_summary_has_50_links_full_session(fixture_layer2_dir):
    l2 = load_layer2_export_folder(fixture_layer2_dir)
    summary = summarize_layer2_window(l2.parquet_df, l2.link_manifest, 0, 30603)
    per_link = summary["per_link_summary"]
    assert len(per_link) == 50
    assert set(per_link["link_id"]) == set(l2.link_manifest["link_id"])


def test_combined_table_has_layer1_and_layer2_events(fixture_layer1_dir, fixture_layer2_dir):
    l1 = load_layer1_qc_folder(fixture_layer1_dir)
    l2 = load_layer2_export_folder(fixture_layer2_dir)
    start, end = 16000, 17000

    events = build_layer1_event_table(l1, "671_T1_P1_R1")
    l1_win = subset_layer1_events_to_window(events, start, end)
    l2_win = subset_layer2_to_window(l2.parquet_df, start, end)

    combined = build_combined_qc_event_table(l1_win, l2_win, l2.link_manifest)
    assert not combined.empty
    assert (combined["source_layer"] == "layer1").any()
    assert (combined["source_layer"] == "layer2").any()
    assert combined.loc[combined["source_layer"] == "layer1", "link_id"].isna().all()
    assert combined.loc[combined["source_layer"] == "layer2", "mapping_confidence"].eq("n/a").all()
    # Layer 1 events must not claim link invalidation
    assert combined.loc[combined["source_layer"] == "layer1", "parent_canonical"].isna().all()
    assert "normalized_marker_name" in combined.columns
    assert "related_joint_family" in combined.columns


def test_write_window_review_outputs(fixture_layer1_dir, fixture_layer2_dir, tmp_path):
    l1 = load_layer1_qc_folder(fixture_layer1_dir)
    l2 = load_layer2_export_folder(fixture_layer2_dir)
    validation = run_all_validations(l1, l2)
    events = build_layer1_event_table(l1, "671_T1_P1_R1")
    start, end = 100, 200
    l1_win = subset_layer1_events_to_window(events, start, end)
    l1_summary = summarize_layer1_window(l1.qc_mask, l1_win, start, end)
    l2_summary = summarize_layer2_window(l2.parquet_df, l2.link_manifest, start, end)
    l2_win = subset_layer2_to_window(l2.parquet_df, start, end)
    combined = build_combined_qc_event_table(l1_win, l2_win, l2.link_manifest)

    out = write_window_review_outputs(
        tmp_path / "window_out",
        validation_result=validation,
        identity=validation.identity,
        layer1_bundle=l1,
        layer2_bundle=l2,
        start_frame=start,
        end_frame=end,
        layer1_summary=l1_summary,
        layer2_summary=l2_summary,
        combined_events=combined,
        layer1_window_events=l1_win,
    )

    expected = [
        "window_validation_summary.json",
        "window_qc_summary_display.csv",
        "qc_event_display.csv",
        "layer2_link_scope_display.csv",
        "layer1_marker_family_risk.csv",
        "combined_qc_event_summary.csv",
        "combined_qc_events.csv",
        "window_review_report.md",
    ]
    for name in expected:
        assert (out / name).exists()


def test_cli_writes_all_outputs(repo_root, fixture_layer1_dir, fixture_layer2_dir, tmp_path):
    out_dir = tmp_path / "cli_window"
    script = repo_root / "scripts" / "review_segmentation_window.py"
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
            str(out_dir),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert (out_dir / "combined_qc_events.csv").exists()
    assert (out_dir / "window_qc_summary_display.csv").exists()
    assert (out_dir / "qc_event_display.csv").exists()
    assert (out_dir / "layer2_link_scope_display.csv").exists()
    assert (out_dir / "window_review_report.md").exists()
    report = (out_dir / "window_review_report.md").read_text()
    assert "regional risk evidence" in report


def test_cli_refuses_invalid_validation(
    repo_root, fixture_layer1_dir, fixture_layer2_dir, tmp_path
):
    script = repo_root / "scripts" / "review_segmentation_window.py"
    # Use wrong layer2 path to trigger load/validation failure
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--layer1-dir",
            str(fixture_layer1_dir),
            "--layer2-dir",
            str(fixture_layer1_dir),  # wrong folder
            "--start-frame",
            "0",
            "--end-frame",
            "100",
            "--out",
            str(tmp_path / "bad"),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2


def test_no_input_modification_after_window_review(fixture_layer1_dir, fixture_layer2_dir):
    from layer2_motive.segmentation.validate_inputs import capture_input_fingerprints

    l1 = load_layer1_qc_folder(fixture_layer1_dir)
    l2 = load_layer2_export_folder(fixture_layer2_dir)
    before = capture_input_fingerprints(l1, l2)

    events = build_layer1_event_table(l1, "671_T1_P1_R1")
    l1_win = subset_layer1_events_to_window(events, 0, 100)
    l2_win = subset_layer2_to_window(l2.parquet_df, 0, 100)
    summarize_layer1_window(l1.qc_mask, l1_win, 0, 100)
    summarize_layer2_window(l2.parquet_df, l2.link_manifest, 0, 100)
    build_combined_qc_event_table(l1_win, l2_win, l2.link_manifest)

    after = capture_input_fingerprints(l1, l2)
    assert before == after
